"""
Conecta Plus - Agente Assembleias
Sistema de gestão de assembleias inteligente
"""

from .agent_v2 import (
    AgenteAssembleias,
    create_assembly_agent,
    TipoAssembleia,
    StatusAssembleia,
    TipoVotacao,
    ResultadoVoto,
    ItemPauta,
    Assembleia,
    Voto,
)

__all__ = [
    "AgenteAssembleias",
    "create_assembly_agent",
    "TipoAssembleia",
    "StatusAssembleia",
    "TipoVotacao",
    "ResultadoVoto",
    "ItemPauta",
    "Assembleia",
    "Voto",
]
