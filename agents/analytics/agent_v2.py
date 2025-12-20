"""
Conecta Plus - Agente de Analytics (Nível 7)
Sistema inteligente de análise de dados e BI

Capacidades:
1. REATIVO: Gerar relatórios, responder consultas
2. PROATIVO: Alertar anomalias, enviar insights
3. PREDITIVO: Prever tendências, modelar cenários
4. AUTÔNOMO: Gerar dashboards, automatizar análises
5. EVOLUTIVO: Aprender padrões de uso de dados
6. COLABORATIVO: Integrar todos os agentes para coleta
7. TRANSCENDENTE: Business Intelligence cognitivo
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta, date
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

from ..core.base_agent import (
    BaseAgent, EvolutionLevel, Priority, AgentCapability,
    AgentContext, AgentAction, AgentPrediction,
)
from ..core.memory_store import UnifiedMemorySystem
from ..core.llm_client import UnifiedLLMClient
from ..core.tools import ToolRegistry

logger = logging.getLogger(__name__)


class TipoRelatorio(Enum):
    FINANCEIRO = "financeiro"
    OPERACIONAL = "operacional"
    SEGURANCA = "seguranca"
    MANUTENCAO = "manutencao"
    OCUPACAO = "ocupacao"
    CONSUMO = "consumo"
    COMPARATIVO = "comparativo"
    EXECUTIVO = "executivo"


class FormatoRelatorio(Enum):
    JSON = "json"
    PDF = "pdf"
    EXCEL = "excel"
    DASHBOARD = "dashboard"


class TipoMetrica(Enum):
    KPI = "kpi"
    TENDENCIA = "tendencia"
    ANOMALIA = "anomalia"
    BENCHMARK = "benchmark"


@dataclass
class Metrica:
    nome: str
    valor: float
    unidade: str
    periodo: str
    variacao: Optional[float] = None
    meta: Optional[float] = None


@dataclass
class Insight:
    id: str
    tipo: str
    titulo: str
    descricao: str
    impacto: str
    acao_sugerida: str
    confianca: float
    data_geracao: datetime = field(default_factory=datetime.now)


class AgenteAnalytics(BaseAgent):
    """Agente de Analytics - Nível 7"""

    def __init__(
        self,
        condominio_id: str,
        llm_client: UnifiedLLMClient = None,
        memory: UnifiedMemorySystem = None,
        tools: ToolRegistry = None,
        evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT,
    ):
        super().__init__(
            agent_id=f"analytics_{condominio_id}",
            agent_type="analytics",
            condominio_id=condominio_id,
            evolution_level=evolution_level,
            llm_client=llm_client,
            memory_store=memory,
        )
        self.tools = tools
        self._metricas_cache: Dict[str, Metrica] = {}
        self._insights: List[Insight] = []
        self._relatorios_agendados: List[Dict] = []

        self.config = {
            "atualizar_metricas_minutos": 15,
            "enviar_insights_automaticos": True,
            "threshold_anomalia": 2.0,  # desvios padrão
            "relatorio_semanal": True,
        }

    def _register_capabilities(self) -> None:
        self._capabilities["relatorios"] = AgentCapability(
            name="relatorios", description="Gerar relatórios",
            level=EvolutionLevel.REACTIVE
        )
        self._capabilities["alertas_anomalias"] = AgentCapability(
            name="alertas_anomalias", description="Alertar anomalias nos dados",
            level=EvolutionLevel.PROACTIVE
        )
        self._capabilities["previsoes"] = AgentCapability(
            name="previsoes", description="Prever tendências",
            level=EvolutionLevel.PREDICTIVE
        )
        self._capabilities["dashboards_autonomos"] = AgentCapability(
            name="dashboards_autonomos", description="Gerar dashboards automaticamente",
            level=EvolutionLevel.AUTONOMOUS
        )
        self._capabilities["bi_cognitivo"] = AgentCapability(
            name="bi_cognitivo", description="Business Intelligence cognitivo",
            level=EvolutionLevel.TRANSCENDENT
        )

    def get_system_prompt(self) -> str:
        return f"""Você é o Agente de Analytics do Conecta Plus.
ID: {self.agent_id} | Condomínio: {self.condominio_id} | Nível: {self.evolution_level.name}

Responsabilidades:
- Coletar e consolidar dados de todos os agentes
- Gerar relatórios e dashboards
- Identificar padrões e anomalias
- Prever tendências futuras
- Fornecer insights acionáveis

Configurações:
- Atualização: a cada {self.config['atualizar_metricas_minutos']} min
- Insights automáticos: {self.config['enviar_insights_automaticos']}
"""

    async def process(self, input_data: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        action = input_data.get("action", "")
        params = input_data.get("params", {})

        if action == "gerar_relatorio":
            return await self._gerar_relatorio(params, context)
        elif action == "metricas":
            return await self._obter_metricas(params, context)
        elif action == "kpis":
            return await self._obter_kpis(params, context)
        elif action == "tendencias":
            return await self._analisar_tendencias(params, context)
        elif action == "anomalias":
            return await self._detectar_anomalias(params, context)
        elif action == "insights":
            return await self._gerar_insights(params, context)
        elif action == "comparativo":
            return await self._analise_comparativa(params, context)
        elif action == "dashboard":
            return await self._gerar_dashboard(params, context)
        elif action == "previsao":
            return await self._previsao(params, context)
        elif action == "chat":
            return await self._chat(params, context)
        else:
            return {"error": f"Ação '{action}' não reconhecida"}

    async def _coletar_dados_agentes(self) -> Dict[str, Any]:
        """Coleta dados de todos os agentes colaboradores"""
        dados = {}

        if self.has_capability("agent_collaboration"):
            # Financeiro
            try:
                dados["financeiro"] = await self.send_message(
                    f"financeiro_{self.condominio_id}",
                    {"action": "resumo_financeiro", "params": {}}
                )
            except:
                dados["financeiro"] = {}

            # Manutenção
            try:
                dados["manutencao"] = await self.send_message(
                    f"manutencao_{self.condominio_id}",
                    {"action": "dashboard", "params": {}}
                )
            except:
                dados["manutencao"] = {}

            # Ocorrências
            try:
                dados["ocorrencias"] = await self.send_message(
                    f"ocorrencias_{self.condominio_id}",
                    {"action": "estatisticas", "params": {}}
                )
            except:
                dados["ocorrencias"] = {}

        return dados

    async def _gerar_relatorio(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        tipo = TipoRelatorio(params.get("tipo", "executivo"))
        formato = FormatoRelatorio(params.get("formato", "json"))
        periodo = params.get("periodo", "mes")

        dados = await self._coletar_dados_agentes()

        if self.llm:
            prompt = f"""Gere um relatório {tipo.value} do condomínio:
Dados coletados: {json.dumps(dados, indent=2)}
Período: {periodo}
Formato: {formato.value}

Estruture o relatório com:
1. Resumo executivo
2. Indicadores principais
3. Destaques do período
4. Pontos de atenção
5. Recomendações
"""
            response = await self.llm.generate(self.get_system_prompt(), prompt)
            return {
                "success": True,
                "tipo": tipo.value,
                "periodo": periodo,
                "conteudo": response
            }

        return {
            "success": True,
            "tipo": tipo.value,
            "periodo": periodo,
            "dados": dados
        }

    async def _obter_metricas(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        categoria = params.get("categoria")
        periodo = params.get("periodo", "mes")

        metricas = []

        # Métricas financeiras
        if not categoria or categoria == "financeiro":
            metricas.extend([
                Metrica("taxa_inadimplencia", 3.5, "%", periodo, variacao=-0.5, meta=2.0),
                Metrica("receita_mensal", 125000, "R$", periodo, variacao=2.3),
                Metrica("despesas_operacionais", 98000, "R$", periodo, variacao=1.2),
            ])

        # Métricas operacionais
        if not categoria or categoria == "operacional":
            metricas.extend([
                Metrica("chamados_abertos", 12, "un", periodo, variacao=-3),
                Metrica("tempo_medio_resolucao", 48, "horas", periodo, variacao=-5, meta=24),
                Metrica("ocupacao_areas_comuns", 65, "%", periodo, variacao=10),
            ])

        # Métricas de segurança
        if not categoria or categoria == "seguranca":
            metricas.extend([
                Metrica("acessos_diarios", 450, "un", periodo, variacao=5),
                Metrica("ocorrencias_seguranca", 2, "un", periodo, variacao=-1),
                Metrica("uptime_cameras", 99.5, "%", periodo, variacao=0.2),
            ])

        return {
            "success": True,
            "metricas": [
                {
                    "nome": m.nome,
                    "valor": m.valor,
                    "unidade": m.unidade,
                    "variacao": m.variacao,
                    "meta": m.meta
                }
                for m in metricas
            ]
        }

    async def _obter_kpis(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """KPIs principais do condomínio"""
        kpis = {
            "saude_financeira": {
                "valor": 85,
                "status": "bom",
                "componentes": ["inadimplencia", "fundo_reserva", "receita_vs_despesa"]
            },
            "satisfacao_moradores": {
                "valor": 78,
                "status": "bom",
                "componentes": ["tempo_resposta", "resolucao_ocorrencias", "comunicacao"]
            },
            "eficiencia_operacional": {
                "valor": 72,
                "status": "regular",
                "componentes": ["manutencao_preventiva", "consumo_energia", "produtividade"]
            },
            "seguranca": {
                "valor": 92,
                "status": "excelente",
                "componentes": ["disponibilidade_sistemas", "tempo_resposta_alarme", "incidentes"]
            }
        }

        return {"success": True, "kpis": kpis}

    async def _analisar_tendencias(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        if not self.has_capability("previsoes"):
            return {"error": "Capacidade preditiva não disponível"}

        metrica = params.get("metrica", "inadimplencia")
        meses = params.get("meses", 6)

        if self.llm:
            prompt = f"""Analise a tendência da métrica '{metrica}' nos próximos {meses} meses.
Considere:
- Sazonalidade
- Histórico do condomínio
- Fatores externos

Forneça:
1. Projeção mês a mês
2. Fatores de influência
3. Cenários (otimista, realista, pessimista)
4. Recomendações
"""
            response = await self.llm.generate(self.get_system_prompt(), prompt)
            return {"success": True, "tendencia": response}

        return {
            "success": True,
            "metrica": metrica,
            "tendencia": "estável",
            "projecao": [3.5, 3.4, 3.3, 3.2, 3.1, 3.0]
        }

    async def _detectar_anomalias(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        if not self.has_capability("alertas_anomalias"):
            return {"error": "Capacidade proativa não disponível"}

        # Simular detecção de anomalias
        anomalias = [
            {
                "metrica": "consumo_agua",
                "valor_atual": 2500,
                "valor_esperado": 1800,
                "desvio": 38.9,
                "severidade": "alta",
                "possivel_causa": "Vazamento ou uso irregular"
            }
        ]

        if self.llm and anomalias:
            prompt = f"""Analise as anomalias detectadas:
{json.dumps(anomalias, indent=2)}

Para cada anomalia:
1. Valide a significância
2. Identifique possíveis causas
3. Sugira ações corretivas
4. Estime impacto se não tratada
"""
            response = await self.llm.generate(self.get_system_prompt(), prompt)
            return {
                "success": True,
                "anomalias": anomalias,
                "analise": response
            }

        return {"success": True, "anomalias": anomalias}

    async def _gerar_insights(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        if not self.has_capability("bi_cognitivo"):
            return {"error": "Capacidade transcendente não disponível"}

        dados = await self._coletar_dados_agentes()

        if self.llm:
            prompt = f"""Com base nos dados do condomínio:
{json.dumps(dados, indent=2)}

Gere insights TRANSCENDENTES que:
1. Identifiquem oportunidades não óbvias
2. Conectem dados de diferentes áreas
3. Prevejam problemas antes de ocorrerem
4. Sugiram otimizações com impacto mensurável
5. Priorizem por ROI/impacto

Formato JSON com: titulo, descricao, impacto, acao_sugerida, confianca
"""
            response = await self.llm.generate(self.get_system_prompt(), prompt)
            return {"success": True, "insights": response}

        return {
            "success": True,
            "insights": [
                {
                    "titulo": "Oportunidade de redução de custos",
                    "descricao": "Análise indica possível economia em energia",
                    "impacto": "R$ 2.500/mês",
                    "acao_sugerida": "Revisar contratos e implementar sensores",
                    "confianca": 0.85
                }
            ]
        }

    async def _analise_comparativa(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        periodo_1 = params.get("periodo_1", "mes_atual")
        periodo_2 = params.get("periodo_2", "mes_anterior")

        comparativo = {
            "inadimplencia": {"periodo_1": 3.5, "periodo_2": 4.0, "variacao": -12.5},
            "receita": {"periodo_1": 125000, "periodo_2": 122000, "variacao": 2.5},
            "chamados": {"periodo_1": 12, "periodo_2": 15, "variacao": -20},
            "satisfacao": {"periodo_1": 78, "periodo_2": 75, "variacao": 4}
        }

        return {
            "success": True,
            "periodo_1": periodo_1,
            "periodo_2": periodo_2,
            "comparativo": comparativo
        }

    async def _gerar_dashboard(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        if not self.has_capability("dashboards_autonomos"):
            return {"error": "Capacidade autônoma não disponível"}

        tipo = params.get("tipo", "executivo")

        # Estrutura do dashboard
        dashboard = {
            "titulo": f"Dashboard {tipo.title()}",
            "data_geracao": datetime.now().isoformat(),
            "cards": [
                {"titulo": "Inadimplência", "valor": "3.5%", "variacao": -0.5, "cor": "verde"},
                {"titulo": "Chamados Abertos", "valor": 12, "variacao": -3, "cor": "verde"},
                {"titulo": "Receita Mensal", "valor": "R$ 125.000", "variacao": 2.3, "cor": "verde"},
                {"titulo": "Ocorrências", "valor": 5, "variacao": 2, "cor": "amarelo"}
            ],
            "graficos": [
                {"tipo": "linha", "titulo": "Evolução Inadimplência", "dados": "12_meses"},
                {"tipo": "pizza", "titulo": "Despesas por Categoria", "dados": "categorias"},
                {"tipo": "barra", "titulo": "Chamados por Área", "dados": "areas"}
            ],
            "alertas": [
                {"tipo": "warning", "mensagem": "Consumo de água 38% acima da média"}
            ]
        }

        return {"success": True, "dashboard": dashboard}

    async def _previsao(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        if not self.has_capability("previsoes"):
            return {"error": "Capacidade preditiva não disponível"}

        tipo = params.get("tipo", "financeiro")
        meses = params.get("meses", 3)

        if self.llm:
            prompt = f"""Gere previsão {tipo} para os próximos {meses} meses:

Considere:
- Histórico do condomínio
- Sazonalidade
- Tendências identificadas
- Fatores externos conhecidos

Retorne:
1. Valores projetados mês a mês
2. Intervalos de confiança
3. Premissas utilizadas
4. Riscos principais
"""
            response = await self.llm.generate(self.get_system_prompt(), prompt)
            return {"success": True, "previsao": response}

        return {
            "success": True,
            "tipo": tipo,
            "meses": meses,
            "projecao": [128000, 130000, 132000]
        }

    async def _chat(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        if self.llm:
            response = await self.llm.generate(
                self.get_system_prompt(), params.get("message", "")
            )
            return {"success": True, "response": response}
        return {"error": "LLM não configurado"}


def create_analytics_agent(
    condominio_id: str,
    llm_client: UnifiedLLMClient = None,
    memory: UnifiedMemorySystem = None,
    tools: ToolRegistry = None,
    evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT
) -> AgenteAnalytics:
    return AgenteAnalytics(
        condominio_id=condominio_id,
        llm_client=llm_client or UnifiedLLMClient(),
        memory=memory, tools=tools,
        evolution_level=evolution_level
    )
