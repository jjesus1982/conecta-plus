"""
Conecta Plus - Event Bus
Sistema de eventos para sincronização real-time
"""

import asyncio
import json
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, Set, Callable, Awaitable
from contextlib import asynccontextmanager
import uuid

from ..observability import logger, LogContext


class EventType(str, Enum):
    """Tipos de eventos do sistema."""
    # Ocorrências
    OCORRENCIA_CREATED = "OCORRENCIA_CREATED"
    OCORRENCIA_UPDATED = "OCORRENCIA_UPDATED"
    OCORRENCIA_RESOLVED = "OCORRENCIA_RESOLVED"

    # Visitantes
    VISITANTE_ARRIVED = "VISITANTE_ARRIVED"
    VISITANTE_AUTORIZADO = "VISITANTE_AUTORIZADO"
    VISITANTE_NEGADO = "VISITANTE_NEGADO"
    VISITANTE_SAIU = "VISITANTE_SAIU"

    # Alarmes
    ALARME_ARMADO = "ALARME_ARMADO"
    ALARME_DESARMADO = "ALARME_DESARMADO"
    ALARME_DISPARADO = "ALARME_DISPARADO"

    # Encomendas
    ENCOMENDA_RECEIVED = "ENCOMENDA_RECEIVED"
    ENCOMENDA_RETIRADA = "ENCOMENDA_RETIRADA"

    # Acesso
    ACESSO_LIBERADO = "ACESSO_LIBERADO"
    ACESSO_NEGADO = "ACESSO_NEGADO"

    # Sistema
    SYSTEM_STATE_UPDATED = "SYSTEM_STATE_UPDATED"
    SYSTEM_HEALTH_CHANGED = "SYSTEM_HEALTH_CHANGED"


@dataclass
class SystemEvent:
    """Evento do sistema."""
    id: str
    type: EventType
    entity: str
    entity_id: str
    timestamp: str
    data: Dict[str, Any]
    correlation_id: Optional[str] = None
    user_id: Optional[str] = None

    def to_json(self) -> str:
        """Serializa o evento para JSON."""
        return json.dumps(asdict(self), ensure_ascii=False, default=str)

    def to_sse(self) -> str:
        """Formata o evento para SSE."""
        return f"event: {self.type.value}\ndata: {self.to_json()}\n\n"


class SystemEventBus:
    """
    Event Bus central para eventos do sistema.

    Features:
    - Pub/Sub assíncrono
    - SSE streaming para clientes
    - Persistência de eventos (audit trail)
    - Filtragem por tipo de evento
    """

    def __init__(self):
        self._subscribers: Set[asyncio.Queue] = set()
        self._event_handlers: Dict[EventType, Set[Callable[[SystemEvent], Awaitable[None]]]] = {}
        self._events_emitted = 0
        self._lock = asyncio.Lock()

    @property
    def subscriber_count(self) -> int:
        """Número de subscribers ativos."""
        return len(self._subscribers)

    @property
    def events_emitted(self) -> int:
        """Total de eventos emitidos."""
        return self._events_emitted

    async def emit(self, event: SystemEvent) -> None:
        """
        Emite um evento para todos os subscribers.

        Args:
            event: Evento a ser emitido
        """
        self._events_emitted += 1

        # Adicionar correlation ID se não existir
        if not event.correlation_id:
            event.correlation_id = LogContext.get_correlation_id() or str(uuid.uuid4())

        logger.domain_event(
            event_type=event.type.value,
            aggregate_id=event.entity_id,
            entity=event.entity,
            data=event.data
        )

        # Notificar subscribers SSE
        async with self._lock:
            dead_queues = set()
            for queue in self._subscribers:
                try:
                    # Non-blocking put
                    queue.put_nowait(event)
                except asyncio.QueueFull:
                    logger.warning("Event queue full, dropping event for subscriber")
                except Exception as e:
                    logger.error(f"Failed to send event to subscriber: {e}")
                    dead_queues.add(queue)

            # Remover subscribers mortos
            self._subscribers -= dead_queues

        # Chamar handlers registrados
        if event.type in self._event_handlers:
            for handler in self._event_handlers[event.type]:
                try:
                    await handler(event)
                except Exception as e:
                    logger.error(f"Event handler failed", exc=e, event_type=event.type.value)

    def emit_sync(
        self,
        event_type: EventType,
        entity: str,
        entity_id: str,
        data: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> SystemEvent:
        """
        Cria e agenda emissão de evento (versão síncrona).

        Útil para chamar de contextos não-async.
        """
        event = SystemEvent(
            id=str(uuid.uuid4()),
            type=event_type,
            entity=entity,
            entity_id=entity_id,
            timestamp=datetime.utcnow().isoformat() + "Z",
            data=data,
            correlation_id=LogContext.get_correlation_id(),
            user_id=user_id
        )

        # Agendar emissão
        asyncio.create_task(self.emit(event))

        return event

    @asynccontextmanager
    async def subscribe(self, max_size: int = 100):
        """
        Context manager para subscrever ao stream de eventos.

        Uso:
            async with event_bus.subscribe() as queue:
                async for event in queue:
                    process(event)
        """
        queue: asyncio.Queue[SystemEvent] = asyncio.Queue(maxsize=max_size)

        async with self._lock:
            self._subscribers.add(queue)

        try:
            yield queue
        finally:
            async with self._lock:
                self._subscribers.discard(queue)

    def register_handler(
        self,
        event_type: EventType,
        handler: Callable[[SystemEvent], Awaitable[None]]
    ) -> None:
        """Registra um handler para um tipo de evento."""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = set()
        self._event_handlers[event_type].add(handler)

    def unregister_handler(
        self,
        event_type: EventType,
        handler: Callable[[SystemEvent], Awaitable[None]]
    ) -> None:
        """Remove um handler."""
        if event_type in self._event_handlers:
            self._event_handlers[event_type].discard(handler)


# === Helper functions ===

def create_event(
    event_type: EventType,
    entity: str,
    entity_id: str,
    data: Dict[str, Any],
    user_id: Optional[str] = None
) -> SystemEvent:
    """Cria um novo evento."""
    return SystemEvent(
        id=str(uuid.uuid4()),
        type=event_type,
        entity=entity,
        entity_id=entity_id,
        timestamp=datetime.utcnow().isoformat() + "Z",
        data=data,
        correlation_id=LogContext.get_correlation_id(),
        user_id=user_id
    )


# === Singleton ===

_event_bus: Optional[SystemEventBus] = None


def get_event_bus() -> SystemEventBus:
    """Obtém a instância singleton do Event Bus."""
    global _event_bus
    if _event_bus is None:
        _event_bus = SystemEventBus()
    return _event_bus
