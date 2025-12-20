"""
Conecta Plus - Agente Síndico
Assistente inteligente do síndico
"""

from .agent_v2 import (
    AgenteSindico,
    create_sindico_agent,
    TipoRelatorio,
    StatusTarefa,
    TipoDecisao,
    TarefaSindico,
    Decisao,
    ResumoCondominio,
)

__all__ = [
    "AgenteSindico",
    "create_sindico_agent",
    "TipoRelatorio",
    "StatusTarefa",
    "TipoDecisao",
    "TarefaSindico",
    "Decisao",
    "ResumoCondominio",
]
