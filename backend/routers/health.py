"""
Conecta Plus - Health Check Unificado
Endpoint de saúde com status de todos os componentes
Inclui monitoramento de Circuit Breakers
"""

from fastapi import APIRouter, Response
from datetime import datetime
import time
import asyncio
import json
from typing import Dict, Any, Optional

from ..services.observability import logger
from ..services.resilience import (
    get_all_circuit_breaker_stats,
    get_all_resilience_stats,
    CircuitState,
)

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


@router.get("/health")
async def health_check():
    """
    Health check detalhado de todos os componentes.

    Retorna:
    - status: "healthy" | "degraded" | "unhealthy"
    - components: status individual de cada componente
    - circuit_breakers: estado de todos os circuit breakers
    - timestamp: momento da verificação
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

    components = {
        "api": {"status": "healthy"},
        "database": db_check,
        "redis": redis_check,
        "event_stream": event_check,
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

    # Determinar status geral
    statuses = [c.get("status", "unknown") for c in components.values()]

    if all(s == "healthy" for s in statuses):
        overall_status = "healthy"
        status_code = 200
    elif any(s == "unhealthy" for s in ["database", "api"]):
        # Componentes críticos
        overall_status = "unhealthy"
        status_code = 503
    elif any(s in ["degraded", "warning"] for s in statuses):
        overall_status = "degraded"
        status_code = 200
    else:
        overall_status = "degraded"
        status_code = 200

    duration_ms = (time.time() - start) * 1000

    response_data = {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "version": "2.0.0",
        "uptime_seconds": int(time.time() - _startup_time),
        "check_duration_ms": round(duration_ms, 2),
        "components": components,
        "circuit_breakers": circuit_check.get("circuits", {})
    }

    logger.info(
        "Health check completed",
        status=overall_status,
        duration_ms=round(duration_ms, 2),
        circuits_open=circuit_check.get("open", 0)
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


# Tempo de inicialização
_startup_time = time.time()
