"""
Conecta Plus - Agente CFTV
Monitoramento inteligente por câmeras
"""

from .agent_v2 import (
    AgenteCFTV,
    create_cftv_agent,
    TipoCamera,
    StatusCamera,
    TipoEvento,
    NivelRisco,
    Camera,
    EventoDetectado,
    AnaliseComportamental,
    PadraoAprendido,
)

__all__ = [
    "AgenteCFTV",
    "create_cftv_agent",
    "TipoCamera",
    "StatusCamera",
    "TipoEvento",
    "NivelRisco",
    "Camera",
    "EventoDetectado",
    "AnaliseComportamental",
    "PadraoAprendido",
]
