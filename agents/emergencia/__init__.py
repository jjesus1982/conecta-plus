"""
Agente de Emergência - Conecta Plus
Protocolos de emergência e segurança
"""

from .agent_v2 import (
    AgenteEmergencia,
    create_emergency_agent,
    TipoEmergencia,
    GravidadeEmergencia,
    StatusEmergencia,
    TipoProtocolo,
    Emergencia,
    Protocolo,
    ContatoEmergencia,
    SimulacaoEmergencia,
    AlertaPreventivo
)

__all__ = [
    "AgenteEmergencia",
    "create_emergency_agent",
    "TipoEmergencia",
    "GravidadeEmergencia",
    "StatusEmergencia",
    "TipoProtocolo",
    "Emergencia",
    "Protocolo",
    "ContatoEmergencia",
    "SimulacaoEmergencia",
    "AlertaPreventivo"
]
