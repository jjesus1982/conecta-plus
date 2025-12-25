"""
Conecta Plus - Sistema de Eventos
Event Bus para comunicação real-time
"""

from .event_bus import (
    SystemEventBus,
    SystemEvent,
    EventType,
    get_event_bus,
    create_event,
)

__all__ = [
    'SystemEventBus',
    'SystemEvent',
    'EventType',
    'get_event_bus',
    'create_event',
]
