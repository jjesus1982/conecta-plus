"""
Agente de Sustentabilidade - Conecta Plus
Gestão ambiental, energia e recursos
"""

from .agent_v2 import (
    AgenteSustentabilidade,
    create_sustainability_agent,
    TipoRecurso,
    TipoResiduo,
    StatusMeta,
    NivelEficiencia,
    ConsumoRecurso,
    MetaSustentabilidade,
    ColetaSeletiva,
    SistemaFotovoltaico,
    AlertaAmbiental
)

__all__ = [
    "AgenteSustentabilidade",
    "create_sustainability_agent",
    "TipoRecurso",
    "TipoResiduo",
    "StatusMeta",
    "NivelEficiencia",
    "ConsumoRecurso",
    "MetaSustentabilidade",
    "ColetaSeletiva",
    "SistemaFotovoltaico",
    "AlertaAmbiental"
]
