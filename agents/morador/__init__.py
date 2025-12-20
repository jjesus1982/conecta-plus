"""
Conecta Plus - Agente Morador
Assistente pessoal inteligente do morador
"""

from .agent_v2 import (
    AgenteMorador,
    create_resident_agent,
    TipoMorador,
    StatusCadastro,
    Morador,
    Preferencia,
)

__all__ = [
    "AgenteMorador",
    "create_resident_agent",
    "TipoMorador",
    "StatusCadastro",
    "Morador",
    "Preferencia",
]
