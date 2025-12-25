"""
Conecta Plus - Health Check Unificado
Endpoint de saúde com status de todos os componentes
"""

from fastapi import APIRouter, Response
from datetime import datetime
import time
import asyncio
from typing import Dict, Any, Optional

from ..services.observability import logger
from ..services.resilience import get_all_circuit_breaker_stats

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


@router.get("/health")
async def health_check():
    """
    Health check detalhado de todos os componentes.

    Retorna:
    - status: "healthy" | "degraded" | "unhealthy"
    - components: status individual de cada componente
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

    components = {
        "api": {"status": "healthy"},
        "database": db_check,
        "redis": redis_check,
        "event_stream": event_check
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
        "circuit_breakers": get_all_circuit_breaker_stats()
    }

    logger.info(
        "Health check completed",
        status=overall_status,
        duration_ms=round(duration_ms, 2)
    )

    return Response(
        content=__import__('json').dumps(response_data),
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


# Tempo de inicialização
_startup_time = time.time()
