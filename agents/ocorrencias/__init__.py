"""
Conecta Plus - Agente Ocorrências
Sistema de gestão de ocorrências inteligente
"""

from .agent_v2 import (
    AgenteOcorrencias,
    create_incidents_agent,
    TipoOcorrencia,
    StatusOcorrencia,
    PrioridadeOcorrencia,
    Ocorrencia,
)

__all__ = [
    "AgenteOcorrencias",
    "create_incidents_agent",
    "TipoOcorrencia",
    "StatusOcorrencia",
    "PrioridadeOcorrencia",
    "Ocorrencia",
]
