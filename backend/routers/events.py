"""
Conecta Plus - Server-Sent Events Router
Endpoint SSE para streaming de eventos em tempo real
"""

from fastapi import APIRouter, Request, Response
from fastapi.responses import StreamingResponse
import asyncio
from datetime import datetime
from typing import AsyncGenerator

from ..services.events import get_event_bus, SystemEvent
from ..services.observability import logger, LogContext

router = APIRouter(prefix="/events", tags=["Events"])


async def event_generator(request: Request) -> AsyncGenerator[str, None]:
    """
    Gerador assíncrono de eventos SSE.

    Mantém a conexão aberta e envia eventos conforme ocorrem.
    """
    event_bus = get_event_bus()

    # Enviar evento de conexão
    connection_event = {
        "type": "connected",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "message": "Connected to event stream"
    }
    yield f"event: connected\ndata: {__import__('json').dumps(connection_event)}\n\n"

    logger.info("SSE client connected", client_ip=request.client.host if request.client else "unknown")

    try:
        async with event_bus.subscribe() as queue:
            # Heartbeat task
            async def heartbeat():
                while True:
                    await asyncio.sleep(30)
                    yield ": heartbeat\n\n"

            # Iniciar heartbeat em background
            heartbeat_task = asyncio.create_task(heartbeat().__anext__())

            while True:
                # Verificar se cliente desconectou
                if await request.is_disconnected():
                    logger.info("SSE client disconnected")
                    break

                try:
                    # Aguardar evento com timeout para permitir heartbeat
                    event: SystemEvent = await asyncio.wait_for(queue.get(), timeout=30)
                    yield event.to_sse()

                except asyncio.TimeoutError:
                    # Enviar heartbeat
                    yield ": heartbeat\n\n"

    except asyncio.CancelledError:
        logger.info("SSE stream cancelled")
    except Exception as e:
        logger.error("SSE stream error", exc=e)
    finally:
        logger.info("SSE stream closed")


@router.get("/stream")
async def event_stream(request: Request):
    """
    Stream de eventos em tempo real via Server-Sent Events.

    Retorna um stream contínuo de eventos do sistema.
    Os clientes podem usar EventSource para se conectar.

    Eventos disponíveis:
    - OCORRENCIA_CREATED/UPDATED/RESOLVED
    - VISITANTE_ARRIVED/AUTORIZADO/NEGADO/SAIU
    - ALARME_ARMADO/DESARMADO/DISPARADO
    - ENCOMENDA_RECEIVED/RETIRADA
    - ACESSO_LIBERADO/NEGADO
    - SYSTEM_STATE_UPDATED

    Headers importantes:
    - Cache-Control: no-cache
    - Connection: keep-alive
    - Content-Type: text/event-stream
    """
    return StreamingResponse(
        event_generator(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Desabilita buffering do nginx
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )


@router.get("/stats")
async def event_stats():
    """
    Estatísticas do sistema de eventos.
    """
    event_bus = get_event_bus()

    return {
        "active_subscribers": event_bus.subscriber_count,
        "events_emitted": event_bus.events_emitted,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


@router.post("/test")
async def emit_test_event():
    """
    Emite um evento de teste (apenas para desenvolvimento).
    """
    from ..services.events import EventType, create_event

    event_bus = get_event_bus()
    event = create_event(
        event_type=EventType.SYSTEM_STATE_UPDATED,
        entity="system",
        entity_id="test",
        data={
            "message": "Test event",
            "timestamp": datetime.utcnow().isoformat()
        }
    )

    await event_bus.emit(event)

    return {
        "success": True,
        "event_id": event.id,
        "message": "Test event emitted"
    }
