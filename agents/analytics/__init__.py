"""
Conecta Plus - Agente Analytics
Sistema de análise de dados e BI inteligente
"""

from .agent_v2 import (
    AgenteAnalytics,
    create_analytics_agent,
    TipoRelatorio,
    FormatoRelatorio,
    TipoMetrica,
    Metrica,
    Insight,
)

__all__ = [
    "AgenteAnalytics",
    "create_analytics_agent",
    "TipoRelatorio",
    "FormatoRelatorio",
    "TipoMetrica",
    "Metrica",
    "Insight",
]
