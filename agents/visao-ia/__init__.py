"""
Conecta Plus - Agente Visão IA
Sistema de visão computacional inteligente
"""

from .agent_v2 import (
    AgenteVisaoIA,
    create_vision_ai_agent,
    TipoDeteccao,
    TipoEvento,
    NivelConfianca,
    Deteccao,
    EventoVisual,
)

__all__ = [
    "AgenteVisaoIA",
    "create_vision_ai_agent",
    "TipoDeteccao",
    "TipoEvento",
    "NivelConfianca",
    "Deteccao",
    "EventoVisual",
]
