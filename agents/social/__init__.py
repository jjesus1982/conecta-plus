"""
Agente Social - Conecta Plus
Comunidade, eventos e marketplace
"""

from .agent_v2 import (
    AgenteSocial,
    create_social_agent,
    TipoEvento,
    StatusEvento,
    TipoGrupo,
    TipoAnuncio,
    EventoComunidade,
    GrupoComunidade,
    AnuncioMarketplace,
    PerfilMorador
)

__all__ = [
    "AgenteSocial",
    "create_social_agent",
    "TipoEvento",
    "StatusEvento",
    "TipoGrupo",
    "TipoAnuncio",
    "EventoComunidade",
    "GrupoComunidade",
    "AnuncioMarketplace",
    "PerfilMorador"
]
