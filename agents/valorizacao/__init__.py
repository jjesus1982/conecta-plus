"""
Agente de Valorização - Conecta Plus
Gestão de patrimônio, valor de mercado e ROI de melhorias
"""

from .agent_v2 import (
    PropertyValueAgent,
    create_property_value_agent,
    TipoImovel,
    CategoriaCondominio,
    StatusMelhoria,
    TipoMelhoria,
    TipoBenchmark,
    AvaliacaoMercado,
    ProjetoMelhoria,
    IndicadorValorizacao,
    PerfilCondominio,
    CampanhaMarketing,
    ComparativoMercado,
)

__all__ = [
    "PropertyValueAgent",
    "create_property_value_agent",
    "TipoImovel",
    "CategoriaCondominio",
    "StatusMelhoria",
    "TipoMelhoria",
    "TipoBenchmark",
    "AvaliacaoMercado",
    "ProjetoMelhoria",
    "IndicadorValorizacao",
    "PerfilCondominio",
    "CampanhaMarketing",
    "ComparativoMercado",
]
