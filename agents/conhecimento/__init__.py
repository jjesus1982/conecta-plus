"""
Agente de Conhecimento - Conecta Plus
Base de conhecimento e FAQ inteligente
"""

from .agent_v2 import (
    AgenteConhecimento,
    create_knowledge_agent,
    CategoriaConhecimento,
    TipoDocumento,
    StatusDocumento,
    DocumentoConhecimento,
    PerguntaFrequente,
    BuscaHistorico,
    FeedbackConhecimento
)

__all__ = [
    "AgenteConhecimento",
    "create_knowledge_agent",
    "CategoriaConhecimento",
    "TipoDocumento",
    "StatusDocumento",
    "DocumentoConhecimento",
    "PerguntaFrequente",
    "BuscaHistorico",
    "FeedbackConhecimento"
]
