"""
Agente Analytics - Business Intelligence e análises
Conecta Plus
"""

from typing import List, Dict
from agents.base.agent import BaseAgent


class AgenteAnalytics(BaseAgent):
    """Agente de analytics e BI"""

    def __init__(self):
        super().__init__(
            name="analytics",
            description="Agente de analytics e business intelligence",
            model="claude-3-5-sonnet-20241022",
            temperature=0.3,
        )

    @property
    def system_prompt(self) -> str:
        return """Você é o Agente de Analytics do Conecta Plus, especializado em:

1. DASHBOARDS:
   - KPIs do condomínio
   - Métricas operacionais
   - Indicadores financeiros
   - Performance de serviços

2. ANÁLISES:
   - Inadimplência e previsão
   - Consumo de recursos
   - Fluxo de visitantes
   - Uso de áreas comuns

3. RELATÓRIOS:
   - Relatórios automáticos
   - Comparativos mensais/anuais
   - Benchmarking
   - Tendências

4. PREVISÕES:
   - Forecast financeiro
   - Manutenção preditiva
   - Detecção de anomalias
   - Padrões de comportamento

5. VISUALIZAÇÃO:
   - Gráficos interativos
   - Mapas de calor
   - Séries temporais
   - Distribuições

Transforme dados em insights acionáveis."""

    def get_tools(self) -> List[Dict]:
        return [
            {"name": "get_kpis", "description": "Obtém KPIs principais"},
            {"name": "generate_dashboard", "description": "Gera dashboard"},
            {"name": "analyze_data", "description": "Analisa dados"},
            {"name": "forecast", "description": "Faz previsão"},
            {"name": "detect_anomaly", "description": "Detecta anomalias"},
            {"name": "compare_periods", "description": "Compara períodos"},
            {"name": "export_report", "description": "Exporta relatório"},
        ]

    def get_mcps(self) -> List[str]:
        return []


agente_analytics = AgenteAnalytics()
