"""
Conecta Plus - Health Check Unificado
Endpoint de saúde com status de todos os componentes
Inclui monitoramento de Circuit Breakers e métricas de sistema
"""

from fastapi import APIRouter, Response
from datetime import datetime
import time
import asyncio
import json
import psutil
from typing import Dict, Any, Optional

from ..services.observability import logger
from ..services.resilience import (
    get_all_circuit_breaker_stats,
    get_all_resilience_stats,
    CircuitState,
)
from ..config import settings

router = APIRouter(tags=["Health"])


async def check_database() -> Dict[str, Any]:
    """Verifica saúde do banco de dados."""
    start = time.time()
    try:
        from ..database import SessionLocal
        from sqlalchemy import text

        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            duration_ms = (time.time() - start) * 1000
            return {
                "status": "healthy",
                "latency_ms": round(duration_ms, 2)
            }
        finally:
            db.close()
    except Exception as e:
        duration_ms = (time.time() - start) * 1000
        logger.error("Database health check failed", exc=e)
        return {
            "status": "unhealthy",
            "error": str(e),
            "latency_ms": round(duration_ms, 2)
        }


async def check_redis() -> Dict[str, Any]:
    """Verifica saúde do Redis."""
    start = time.time()
    try:
        import redis
        import os

        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        client = redis.from_url(redis_url, socket_timeout=2)
        client.ping()
        duration_ms = (time.time() - start) * 1000

        return {
            "status": "healthy",
            "latency_ms": round(duration_ms, 2)
        }
    except Exception as e:
        duration_ms = (time.time() - start) * 1000
        return {
            "status": "unhealthy",
            "error": str(e),
            "latency_ms": round(duration_ms, 2)
        }


def check_event_stream() -> Dict[str, Any]:
    """Verifica saúde do Event Stream."""
    from ..services.events import get_event_bus

    try:
        event_bus = get_event_bus()
        return {
            "status": "healthy",
            "subscribers": event_bus.subscriber_count,
            "events_emitted": event_bus.events_emitted
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


def check_circuit_breakers() -> Dict[str, Any]:
    """Verifica estado dos circuit breakers."""
    try:
        stats = get_all_circuit_breaker_stats()
        total = len(stats)
        open_count = sum(1 for s in stats.values() if s.get("state") == "OPEN")
        half_open_count = sum(1 for s in stats.values() if s.get("state") == "HALF_OPEN")
        closed_count = total - open_count - half_open_count

        # Se mais de 50% dos circuits estao abertos, considerar degradado
        if total > 0 and (open_count / total) > 0.5:
            status = "degraded"
        elif open_count > 0:
            status = "warning"
        else:
            status = "healthy"

        return {
            "status": status,
            "total": total,
            "closed": closed_count,
            "open": open_count,
            "half_open": half_open_count,
            "circuits": stats
        }
    except Exception as e:
        return {
            "status": "unknown",
            "error": str(e)
        }


def check_memory() -> Dict[str, Any]:
    """Verifica uso de memória do processo e do sistema."""
    try:
        # Memória do processo atual
        process = psutil.Process()
        process_memory = process.memory_info()

        # Memória do sistema
        system_memory = psutil.virtual_memory()

        return {
            "status": "healthy",
            "process": {
                "used_mb": round(process_memory.rss / (1024 * 1024), 2),
                "percent": round(process_memory.rss / system_memory.total * 100, 2)
            },
            "system": {
                "total_mb": round(system_memory.total / (1024 * 1024), 2),
                "available_mb": round(system_memory.available / (1024 * 1024), 2),
                "used_mb": round(system_memory.used / (1024 * 1024), 2),
                "percent": round(system_memory.percent, 2)
            }
        }
    except Exception as e:
        return {
            "status": "unknown",
            "error": str(e)
        }


@router.get("/health")
async def health_check():
    """
    Health check detalhado de todos os componentes.

    Retorna:
    - status: "healthy" | "degraded" | "unhealthy"
    - timestamp: momento da verificação (ISO8601)
    - version: versão da aplicação
    - uptime_seconds: tempo desde o início
    - components: status individual de cada componente
    - memory: uso de memória do processo e sistema
    - circuit_breakers: estado de todos os circuit breakers
    """
    start = time.time()

    # Executar checks em paralelo
    db_check, redis_check = await asyncio.gather(
        check_database(),
        check_redis(),
        return_exceptions=True
    )

    # Tratar exceções
    if isinstance(db_check, Exception):
        db_check = {"status": "unhealthy", "error": str(db_check)}
    if isinstance(redis_check, Exception):
        redis_check = {"status": "unhealthy", "error": str(redis_check)}

    event_check = check_event_stream()
    circuit_check = check_circuit_breakers()
    memory_check = check_memory()

    # Componentes principais com latência
    components = {
        "database": {
            "status": db_check.get("status", "unknown"),
            "latency_ms": db_check.get("latency_ms", 0)
        },
        "redis": {
            "status": redis_check.get("status", "unknown"),
            "latency_ms": redis_check.get("latency_ms", 0)
        },
        "api": {"status": "healthy"},
        "event_stream": {
            "status": event_check.get("status", "unknown"),
            "subscribers": event_check.get("subscribers", 0)
        },
        "circuit_breakers": {
            "status": circuit_check["status"],
            "summary": {
                "total": circuit_check.get("total", 0),
                "open": circuit_check.get("open", 0),
                "half_open": circuit_check.get("half_open", 0),
                "closed": circuit_check.get("closed", 0),
            }
        }
    }

    # Adicionar erros se existirem
    if "error" in db_check:
        components["database"]["error"] = db_check["error"]
    if "error" in redis_check:
        components["redis"]["error"] = redis_check["error"]

    # Determinar status geral baseado em componentes críticos
    db_status = components["database"]["status"]
    redis_status = components["redis"]["status"]
    circuit_status = circuit_check["status"]

    if db_status == "unhealthy":
        overall_status = "unhealthy"
        status_code = 503
    elif redis_status == "unhealthy":
        overall_status = "degraded"
        status_code = 200
    elif circuit_status in ["degraded", "warning"]:
        overall_status = "degraded"
        status_code = 200
    elif all(c.get("status") == "healthy" for c in [
        components["database"],
        components["redis"],
        components["api"]
    ]):
        overall_status = "healthy"
        status_code = 200
    else:
        overall_status = "degraded"
        status_code = 200

    duration_ms = (time.time() - start) * 1000

    # Formato de memória simplificado no nível raiz
    memory_simplified = {
        "used_mb": memory_check.get("process", {}).get("used_mb", 0),
        "percent": memory_check.get("process", {}).get("percent", 0)
    }

    response_data = {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "version": settings.APP_VERSION,
        "uptime_seconds": int(time.time() - _startup_time),
        "components": components,
        "memory": memory_simplified,
        "check_duration_ms": round(duration_ms, 2),
        "circuit_breakers": circuit_check.get("circuits", {})
    }

    logger.info(
        "Health check completed",
        status=overall_status,
        duration_ms=round(duration_ms, 2),
        circuits_open=circuit_check.get("open", 0),
        memory_mb=memory_simplified["used_mb"]
    )

    return Response(
        content=json.dumps(response_data),
        media_type="application/json",
        status_code=status_code
    )


@router.get("/health/live")
async def liveness_probe():
    """
    Liveness probe simples (para Kubernetes).
    Retorna 200 se a API está respondendo.
    """
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat() + "Z"}


@router.get("/health/ready")
async def readiness_probe():
    """
    Readiness probe (para Kubernetes).
    Verifica se a API está pronta para receber tráfego.
    """
    # Verificar apenas componentes críticos
    db_check = await check_database()

    if db_check.get("status") == "healthy":
        return {
            "status": "ready",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

    return Response(
        content=__import__('json').dumps({
            "status": "not_ready",
            "reason": "database_unavailable",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }),
        media_type="application/json",
        status_code=503
    )


@router.get("/health/circuits")
async def circuit_breakers_status():
    """
    Status detalhado de todos os circuit breakers.

    Retorna informacoes completas sobre cada circuit breaker:
    - Estado atual (CLOSED, OPEN, HALF_OPEN)
    - Contadores de falha/sucesso
    - Estatisticas de chamadas
    """
    circuit_check = check_circuit_breakers()

    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "summary": {
            "status": circuit_check["status"],
            "total": circuit_check.get("total", 0),
            "closed": circuit_check.get("closed", 0),
            "open": circuit_check.get("open", 0),
            "half_open": circuit_check.get("half_open", 0),
        },
        "circuits": circuit_check.get("circuits", {})
    }


@router.get("/health/circuits/{circuit_name}")
async def circuit_breaker_detail(circuit_name: str):
    """
    Detalhes de um circuit breaker especifico.
    """
    from ..services.resilience import get_circuit_breaker

    try:
        # Buscar nas estatisticas globais
        all_stats = get_all_circuit_breaker_stats()

        if circuit_name in all_stats:
            return {
                "name": circuit_name,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                **all_stats[circuit_name]
            }

        return Response(
            content=json.dumps({
                "error": "Circuit breaker not found",
                "name": circuit_name,
                "available": list(all_stats.keys())
            }),
            media_type="application/json",
            status_code=404
        )
    except Exception as e:
        return Response(
            content=json.dumps({"error": str(e)}),
            media_type="application/json",
            status_code=500
        )


@router.post("/health/circuits/{circuit_name}/reset")
async def reset_circuit_breaker(circuit_name: str):
    """
    Reset manual de um circuit breaker.
    CUIDADO: Use apenas quando tiver certeza que o servico esta saudavel.
    """
    from ..services.resilience import get_circuit_breaker

    try:
        all_stats = get_all_circuit_breaker_stats()

        if circuit_name not in all_stats:
            return Response(
                content=json.dumps({
                    "error": "Circuit breaker not found",
                    "name": circuit_name
                }),
                media_type="application/json",
                status_code=404
            )

        # Obter o circuit breaker e resetar
        circuit = get_circuit_breaker(circuit_name)
        old_state = circuit.state.value
        circuit.reset()

        logger.warning(
            f"Circuit breaker reset manualmente",
            circuit=circuit_name,
            old_state=old_state
        )

        return {
            "success": True,
            "circuit": circuit_name,
            "old_state": old_state,
            "new_state": "CLOSED",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        logger.error(f"Erro ao resetar circuit breaker {circuit_name}", exc=e)
        return Response(
            content=json.dumps({"error": str(e)}),
            media_type="application/json",
            status_code=500
        )


@router.get("/health/memory")
async def memory_status():
    """
    Status detalhado de uso de memória.

    Retorna métricas do processo atual e do sistema:
    - Memória RSS do processo
    - Memória total/disponível do sistema
    - Percentuais de uso
    """
    memory_check = check_memory()

    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "status": memory_check.get("status", "unknown"),
        "process": memory_check.get("process", {}),
        "system": memory_check.get("system", {})
    }


@router.get("/health/warmup")
async def warmup_status():
    """
    Status do ultimo warmup executado.

    Retorna informacoes sobre o warmup de startup:
    - Timestamp de execucao
    - Duracao total
    - Status de cada componente (database, redis, cache)
    """
    try:
        from ..services.warmup import get_last_warmup_report

        report = get_last_warmup_report()
        if report:
            return {
                "status": "available",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "warmup": report
            }
        else:
            return {
                "status": "not_executed",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "message": "Nenhum warmup executado ainda"
            }
    except Exception as e:
        return {
            "status": "error",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "error": str(e)
        }


# Tempo de inicialização
_startup_time = time.time()
