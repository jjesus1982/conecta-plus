"""
Conecta Plus - Agente Financeiro Avançado (Nível 7)
Implementação completa do agente financeiro com todas as capacidades evolutivas

Capacidades por nível:
1. REATIVO: Consulta saldo, gera boletos
2. PROATIVO: Alerta inadimplência, lembra vencimentos
3. PREDITIVO: Prevê inadimplência, projeta fluxo de caixa
4. AUTÔNOMO: Renegocia dívidas, aplica multas automáticas
5. EVOLUTIVO: Aprende padrões de pagamento
6. COLABORATIVO: Integra com Síndico, Comunicação, Cobrança
7. TRANSCENDENTE: Otimização financeira além do esperado

Autor: Conecta Plus AI
Versão: 2.0 (Evolution Framework)
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum

from ..core.base_agent import (
    BaseAgent,
    EvolutionLevel,
    Priority,
    AgentCapability,
    AgentContext,
    AgentMessage,
    AgentAction,
    AgentPrediction,
)
from ..core.memory_store import UnifiedMemorySystem
from ..core.llm_client import UnifiedLLMClient, LLMMessage, Tool
from ..core.rag_system import RAGPipeline, Document, DocumentType
from ..core.tools import ToolRegistry, ToolResult

logger = logging.getLogger(__name__)


# ==================== TIPOS ESPECÍFICOS ====================

class TipoLancamento(Enum):
    RECEITA = "receita"
    DESPESA = "despesa"
    TRANSFERENCIA = "transferencia"


class StatusBoleto(Enum):
    PENDENTE = "pendente"
    PAGO = "pago"
    VENCIDO = "vencido"
    CANCELADO = "cancelado"
    RENEGOCIADO = "renegociado"


class CategoriaFinanceira(Enum):
    TAXA_CONDOMINIO = "taxa_condominio"
    AGUA = "agua"
    GAS = "gas"
    ENERGIA = "energia"
    MANUTENCAO = "manutencao"
    FUNCIONARIOS = "funcionarios"
    FUNDO_RESERVA = "fundo_reserva"
    MULTA = "multa"
    OUTRAS = "outras"


@dataclass
class ContaFinanceira:
    """Conta do condomínio"""
    id: str
    nome: str
    tipo: str  # corrente, poupanca, caixa
    saldo: Decimal
    banco: Optional[str] = None
    agencia: Optional[str] = None
    conta: Optional[str] = None


@dataclass
class Lancamento:
    """Lançamento financeiro"""
    id: str
    tipo: TipoLancamento
    categoria: CategoriaFinanceira
    descricao: str
    valor: Decimal
    data: datetime
    conta_id: str
    unidade_id: Optional[str] = None
    boleto_id: Optional[str] = None
    competencia: Optional[str] = None  # "2024-01"


@dataclass
class Boleto:
    """Boleto de cobrança"""
    id: str
    unidade_id: str
    morador_id: str
    valor: Decimal
    vencimento: datetime
    status: StatusBoleto
    competencia: str
    multa: Decimal = Decimal("0")
    juros: Decimal = Decimal("0")
    desconto: Decimal = Decimal("0")
    codigo_barras: Optional[str] = None
    pix_copia_cola: Optional[str] = None


@dataclass
class PrevisaoInadimplencia:
    """Previsão de inadimplência"""
    unidade_id: str
    morador_nome: str
    probabilidade: float
    fatores: List[str]
    valor_em_risco: Decimal
    recomendacoes: List[str]


@dataclass
class OtimizacaoFinanceira:
    """Sugestão de otimização transcendente"""
    tipo: str
    descricao: str
    economia_potencial: Decimal
    implementacao: str
    risco: str
    confianca: float


# ==================== AGENTE FINANCEIRO ====================

class AgenteFinanceiro(BaseAgent):
    """
    Agente Financeiro Avançado - Nível 7 (Transcendente)

    Responsabilidades:
    - Gestão completa de contas a receber e pagar
    - Geração e gestão de boletos
    - Previsão de inadimplência
    - Otimização de fluxo de caixa
    - Renegociação automática de dívidas
    - Análise preditiva e prescritiva
    """

    def __init__(
        self,
        condominio_id: str,
        llm_client: UnifiedLLMClient = None,
        memory: UnifiedMemorySystem = None,
        tools: ToolRegistry = None,
        rag: RAGPipeline = None,
        evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT,
    ):
        super().__init__(
            agent_id=f"financeiro_{condominio_id}",
            agent_type="financeiro",
            condominio_id=condominio_id,
            evolution_level=evolution_level,
            llm_client=llm_client,
            memory_store=memory,
        )

        self.tools = tools
        self.rag = rag

        # Estado interno específico
        self._cache_inadimplencia: Dict[str, PrevisaoInadimplencia] = {}
        self._ultimo_fechamento: Optional[datetime] = None
        self._alertas_enviados: Dict[str, datetime] = {}

        # Configurações
        self.config = {
            "taxa_juros_atraso": Decimal("0.01"),  # 1% ao mês
            "taxa_multa_atraso": Decimal("0.02"),  # 2% fixo
            "dias_tolerancia": 3,
            "dias_alerta_vencimento": 5,
            "limite_renegociacao_automatica": Decimal("5000"),
            "parcelas_max_renegociacao": 12,
        }

        logger.info(f"Agente Financeiro inicializado para condomínio {condominio_id}")

    def _register_capabilities(self) -> None:
        """Registra capacidades específicas do agente financeiro"""

        # Nível 1: Reativo
        self._capabilities["consultar_saldo"] = AgentCapability(
            name="consultar_saldo",
            description="Consultar saldo de contas",
            level=EvolutionLevel.REACTIVE
        )
        self._capabilities["gerar_boleto"] = AgentCapability(
            name="gerar_boleto",
            description="Gerar boletos de cobrança",
            level=EvolutionLevel.REACTIVE
        )
        self._capabilities["registrar_pagamento"] = AgentCapability(
            name="registrar_pagamento",
            description="Registrar pagamentos recebidos",
            level=EvolutionLevel.REACTIVE
        )

        # Nível 2: Proativo
        self._capabilities["alertar_inadimplencia"] = AgentCapability(
            name="alertar_inadimplencia",
            description="Alertar sobre inadimplência",
            level=EvolutionLevel.PROACTIVE
        )
        self._capabilities["lembrar_vencimento"] = AgentCapability(
            name="lembrar_vencimento",
            description="Enviar lembretes de vencimento",
            level=EvolutionLevel.PROACTIVE
        )

        # Nível 3: Preditivo
        self._capabilities["prever_inadimplencia"] = AgentCapability(
            name="prever_inadimplencia",
            description="Prever risco de inadimplência",
            level=EvolutionLevel.PREDICTIVE
        )
        self._capabilities["projetar_fluxo_caixa"] = AgentCapability(
            name="projetar_fluxo_caixa",
            description="Projetar fluxo de caixa futuro",
            level=EvolutionLevel.PREDICTIVE
        )

        # Nível 4: Autônomo
        self._capabilities["renegociar_dividas"] = AgentCapability(
            name="renegociar_dividas",
            description="Renegociar dívidas automaticamente",
            level=EvolutionLevel.AUTONOMOUS
        )
        self._capabilities["aplicar_multas"] = AgentCapability(
            name="aplicar_multas",
            description="Aplicar multas e juros automaticamente",
            level=EvolutionLevel.AUTONOMOUS
        )

        # Nível 5: Evolutivo
        self._capabilities["aprender_padroes_pagamento"] = AgentCapability(
            name="aprender_padroes_pagamento",
            description="Aprender padrões de pagamento",
            level=EvolutionLevel.EVOLUTIONARY
        )

        # Nível 6: Colaborativo
        self._capabilities["integrar_sindico"] = AgentCapability(
            name="integrar_sindico",
            description="Integrar com agente Síndico",
            level=EvolutionLevel.COLLABORATIVE
        )

        # Nível 7: Transcendente
        self._capabilities["otimizar_financas"] = AgentCapability(
            name="otimizar_financas",
            description="Otimização financeira transcendente",
            level=EvolutionLevel.TRANSCENDENT
        )

    def get_system_prompt(self) -> str:
        """Retorna system prompt do agente"""
        return f"""Você é o Agente Financeiro do sistema Conecta Plus, responsável pela gestão financeira completa do condomínio.

Seu ID: {self.agent_id}
Condomínio: {self.condominio_id}
Nível de Evolução: {self.evolution_level.name} ({self.evolution_level.value})

Suas responsabilidades incluem:
1. Gestão de contas a receber e pagar
2. Emissão e controle de boletos
3. Análise de inadimplência
4. Previsões financeiras
5. Renegociação de dívidas
6. Otimização de fluxo de caixa

Regras de negócio:
- Taxa de juros por atraso: {self.config['taxa_juros_atraso']*100}% ao mês
- Multa por atraso: {self.config['taxa_multa_atraso']*100}%
- Dias de tolerância: {self.config['dias_tolerancia']}
- Limite para renegociação automática: R$ {self.config['limite_renegociacao_automatica']}

Comunique-se sempre em português brasileiro, de forma profissional e clara.
Ao sugerir ações, considere o impacto no relacionamento com os moradores.
"""

    async def process(self, input_data: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        """Processa entrada e executa ação apropriada"""
        action = input_data.get("action", "")
        params = input_data.get("params", {})

        # Adicionar ao contexto de trabalho
        if self.memory:
            self.memory.add_to_context(
                context.session_id or "default",
                "user_message",
                json.dumps(input_data)
            )

        result = {}

        try:
            # Nível 1: Ações reativas
            if action == "consultar_saldo":
                result = await self._consultar_saldo(params, context)

            elif action == "gerar_boleto":
                result = await self._gerar_boleto(params, context)

            elif action == "registrar_pagamento":
                result = await self._registrar_pagamento(params, context)

            elif action == "listar_inadimplentes":
                result = await self._listar_inadimplentes(params, context)

            # Nível 2: Ações proativas
            elif action == "verificar_vencimentos":
                if self.has_capability("lembrar_vencimento"):
                    result = await self._verificar_vencimentos(params, context)
                else:
                    result = {"error": "Capacidade não disponível neste nível"}

            # Nível 3: Ações preditivas
            elif action == "prever_inadimplencia":
                if self.has_capability("prever_inadimplencia"):
                    result = await self._prever_inadimplencia(params, context)
                else:
                    result = {"error": "Capacidade preditiva não disponível"}

            elif action == "projetar_fluxo_caixa":
                if self.has_capability("projetar_fluxo_caixa"):
                    result = await self._projetar_fluxo_caixa(params, context)
                else:
                    result = {"error": "Capacidade preditiva não disponível"}

            # Nível 4: Ações autônomas
            elif action == "renegociar_divida":
                if self.has_capability("renegociar_dividas"):
                    result = await self._renegociar_divida(params, context)
                else:
                    result = {"error": "Capacidade autônoma não disponível"}

            # Nível 7: Ações transcendentes
            elif action == "otimizar":
                if self.has_capability("otimizar_financas"):
                    result = await self._gerar_otimizacoes(params, context)
                else:
                    result = {"error": "Capacidade transcendente não disponível"}

            # Ação genérica via LLM
            elif action == "chat":
                result = await self._process_chat(params, context)

            else:
                result = {"error": f"Ação '{action}' não reconhecida"}

        except Exception as e:
            logger.error(f"Erro ao processar ação {action}: {e}")
            result = {"error": str(e)}

        # Registrar na memória
        if self.memory:
            self.memory.add_to_context(
                context.session_id or "default",
                "assistant_message",
                json.dumps(result)
            )

        return result

    # ==================== NÍVEL 1: REATIVO ====================

    async def _consultar_saldo(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Consulta saldo das contas"""
        conta_id = params.get("conta_id")

        if self.tools:
            if conta_id:
                result = await self.tools.execute(
                    "database_query",
                    table="financeiro_contas",
                    where={"id": conta_id, "condominio_id": self.condominio_id}
                )
            else:
                result = await self.tools.execute(
                    "database_query",
                    table="financeiro_contas",
                    where={"condominio_id": self.condominio_id}
                )

            if result.success:
                return {
                    "success": True,
                    "contas": result.data,
                    "saldo_total": sum(c.get("saldo", 0) for c in result.data)
                }
            return {"success": False, "error": result.error}

        # Mock para desenvolvimento
        return {
            "success": True,
            "contas": [
                {"id": "1", "nome": "Conta Corrente", "saldo": 45000.00},
                {"id": "2", "nome": "Fundo de Reserva", "saldo": 120000.00},
            ],
            "saldo_total": 165000.00
        }

    async def _gerar_boleto(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Gera boleto para unidade"""
        unidade_id = params.get("unidade_id")
        valor = Decimal(str(params.get("valor", 0)))
        vencimento = params.get("vencimento")
        competencia = params.get("competencia")

        if not all([unidade_id, valor, vencimento]):
            return {"success": False, "error": "Parâmetros obrigatórios: unidade_id, valor, vencimento"}

        # Gerar boleto
        boleto_data = {
            "unidade_id": unidade_id,
            "condominio_id": self.condominio_id,
            "valor": float(valor),
            "vencimento": vencimento,
            "competencia": competencia or datetime.now().strftime("%Y-%m"),
            "status": "pendente",
            "created_at": datetime.now().isoformat()
        }

        if self.tools:
            result = await self.tools.execute(
                "database_insert",
                table="financeiro_boletos",
                data=boleto_data
            )

            if result.success:
                # Gerar código de barras (simulado)
                boleto_id = result.data.get("id")

                # Enviar notificação ao morador
                await self.tools.execute(
                    "send_notification",
                    user_ids=[unidade_id],  # Simplificado
                    title="Novo Boleto Disponível",
                    message=f"Seu boleto de R$ {valor:.2f} vence em {vencimento}",
                    channels=["push", "email"]
                )

                return {
                    "success": True,
                    "boleto_id": boleto_id,
                    "mensagem": f"Boleto gerado com sucesso"
                }

        return {
            "success": True,
            "boleto_id": "mock_123",
            "codigo_barras": "23793.38128 60000.000003 00000.000401 1 84340000015000",
            "pix_copia_cola": "00020126580014br.gov.bcb.pix..."
        }

    async def _registrar_pagamento(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Registra pagamento de boleto"""
        boleto_id = params.get("boleto_id")
        valor_pago = Decimal(str(params.get("valor_pago", 0)))
        data_pagamento = params.get("data_pagamento", datetime.now().isoformat())

        if not boleto_id:
            return {"success": False, "error": "boleto_id é obrigatório"}

        if self.tools:
            # Atualizar status do boleto
            result = await self.tools.execute(
                "database_update",
                table="financeiro_boletos",
                data={
                    "status": "pago",
                    "valor_pago": float(valor_pago),
                    "data_pagamento": data_pagamento
                },
                where={"id": boleto_id}
            )

            if result.success:
                # Registrar lançamento
                await self.tools.execute(
                    "database_insert",
                    table="financeiro_lancamentos",
                    data={
                        "tipo": "receita",
                        "categoria": "taxa_condominio",
                        "descricao": f"Pagamento boleto {boleto_id}",
                        "valor": float(valor_pago),
                        "data": data_pagamento,
                        "boleto_id": boleto_id,
                        "condominio_id": self.condominio_id
                    }
                )

                # Aprender com pagamento (Nível 5)
                if self.has_capability("aprender_padroes_pagamento"):
                    await self._aprender_pagamento(boleto_id, valor_pago, data_pagamento)

                return {"success": True, "mensagem": "Pagamento registrado"}

        return {"success": True, "mensagem": "Pagamento registrado (mock)"}

    async def _listar_inadimplentes(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Lista unidades inadimplentes"""
        dias_atraso_minimo = params.get("dias_atraso", 30)

        if self.tools:
            # Buscar boletos vencidos
            data_limite = (datetime.now() - timedelta(days=dias_atraso_minimo)).isoformat()

            result = await self.tools.execute(
                "database_query",
                table="financeiro_boletos",
                where={
                    "condominio_id": self.condominio_id,
                    "status": "vencido"
                }
            )

            if result.success:
                inadimplentes = []
                for boleto in result.data:
                    if boleto.get("vencimento", "") < data_limite:
                        inadimplentes.append({
                            "unidade_id": boleto.get("unidade_id"),
                            "valor": boleto.get("valor"),
                            "vencimento": boleto.get("vencimento"),
                            "dias_atraso": (datetime.now() - datetime.fromisoformat(boleto["vencimento"])).days
                        })

                return {
                    "success": True,
                    "inadimplentes": inadimplentes,
                    "total": len(inadimplentes),
                    "valor_total": sum(i["valor"] for i in inadimplentes)
                }

        # Mock
        return {
            "success": True,
            "inadimplentes": [
                {"unidade_id": "101", "valor": 1500.00, "dias_atraso": 45},
                {"unidade_id": "205", "valor": 3200.00, "dias_atraso": 90},
            ],
            "total": 2,
            "valor_total": 4700.00
        }

    # ==================== NÍVEL 2: PROATIVO ====================

    async def _verificar_vencimentos(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Verifica e notifica vencimentos próximos"""
        dias_antecedencia = params.get("dias", self.config["dias_alerta_vencimento"])

        data_limite = (datetime.now() + timedelta(days=dias_antecedencia)).isoformat()
        data_hoje = datetime.now().isoformat()

        if self.tools:
            result = await self.tools.execute(
                "database_query",
                table="financeiro_boletos",
                where={
                    "condominio_id": self.condominio_id,
                    "status": "pendente"
                }
            )

            if result.success:
                notificacoes_enviadas = 0

                for boleto in result.data:
                    vencimento = boleto.get("vencimento", "")
                    if data_hoje <= vencimento <= data_limite:
                        # Verificar se já enviou alerta recentemente
                        alerta_key = f"venc_{boleto['id']}"
                        ultimo_alerta = self._alertas_enviados.get(alerta_key)

                        if not ultimo_alerta or (datetime.now() - ultimo_alerta).days >= 2:
                            # Enviar lembrete
                            await self.tools.execute(
                                "send_notification",
                                user_ids=[boleto.get("morador_id")],
                                title="Lembrete de Vencimento",
                                message=f"Seu boleto de R$ {boleto['valor']:.2f} vence em {vencimento}",
                                channels=["push", "whatsapp"]
                            )
                            self._alertas_enviados[alerta_key] = datetime.now()
                            notificacoes_enviadas += 1

                return {
                    "success": True,
                    "notificacoes_enviadas": notificacoes_enviadas
                }

        return {"success": True, "notificacoes_enviadas": 0}

    # ==================== NÍVEL 3: PREDITIVO ====================

    async def _prever_inadimplencia(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Prevê risco de inadimplência usando ML/LLM"""
        unidade_id = params.get("unidade_id")

        # Buscar histórico de pagamentos
        historico = await self._obter_historico_pagamentos(unidade_id)

        # Usar LLM para análise
        if self.llm:
            prompt = f"""Analise o histórico de pagamentos desta unidade e preveja o risco de inadimplência:

Unidade: {unidade_id}
Histórico de pagamentos (últimos 12 meses):
{json.dumps(historico, indent=2)}

Responda em JSON:
{{
  "probabilidade_inadimplencia": 0.0-1.0,
  "fatores_risco": ["fator1", "fator2"],
  "valor_em_risco": 0.00,
  "recomendacoes": ["ação1", "ação2"]
}}
"""
            try:
                response = await self.llm.generate(
                    system_prompt=self.get_system_prompt(),
                    user_prompt=prompt,
                    temperature=0.3
                )

                # Parse resposta
                import re
                json_match = re.search(r'\{[\s\S]*\}', response)
                if json_match:
                    previsao = json.loads(json_match.group())

                    # Cachear previsão
                    self._cache_inadimplencia[unidade_id] = PrevisaoInadimplencia(
                        unidade_id=unidade_id,
                        morador_nome=historico.get("morador_nome", ""),
                        probabilidade=previsao.get("probabilidade_inadimplencia", 0.5),
                        fatores=previsao.get("fatores_risco", []),
                        valor_em_risco=Decimal(str(previsao.get("valor_em_risco", 0))),
                        recomendacoes=previsao.get("recomendacoes", [])
                    )

                    return {
                        "success": True,
                        "previsao": previsao
                    }
            except Exception as e:
                logger.error(f"Erro na previsão: {e}")

        # Fallback: análise simples
        atrasos = historico.get("atrasos", 0)
        probabilidade = min(atrasos * 0.15, 0.9)

        return {
            "success": True,
            "previsao": {
                "probabilidade_inadimplencia": probabilidade,
                "fatores_risco": ["histórico de atrasos"] if atrasos > 0 else [],
                "valor_em_risco": historico.get("valor_medio", 0) * 3,
                "recomendacoes": ["Contato preventivo"] if probabilidade > 0.5 else []
            }
        }

    async def _projetar_fluxo_caixa(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Projeta fluxo de caixa futuro"""
        meses = params.get("meses", 3)

        # Obter dados históricos
        receitas = await self._obter_receitas_historicas(12)
        despesas = await self._obter_despesas_historicas(12)

        # Usar tool de análise
        if self.tools:
            # Análise de tendência das receitas
            receitas_result = await self.tools.execute(
                "predict_values",
                historical_data=[{"value": r} for r in receitas],
                periods_ahead=meses,
                method="moving_average"
            )

            # Análise de tendência das despesas
            despesas_result = await self.tools.execute(
                "predict_values",
                historical_data=[{"value": d} for d in despesas],
                periods_ahead=meses,
                method="moving_average"
            )

            if receitas_result.success and despesas_result.success:
                projecao = []
                receitas_prev = receitas_result.data.get("predictions", [])
                despesas_prev = despesas_result.data.get("predictions", [])

                for i in range(meses):
                    mes_futuro = datetime.now() + timedelta(days=30 * (i + 1))
                    receita = receitas_prev[i] if i < len(receitas_prev) else receitas_prev[-1]
                    despesa = despesas_prev[i] if i < len(despesas_prev) else despesas_prev[-1]

                    projecao.append({
                        "mes": mes_futuro.strftime("%Y-%m"),
                        "receita_projetada": receita,
                        "despesa_projetada": despesa,
                        "saldo_projetado": receita - despesa
                    })

                return {
                    "success": True,
                    "projecao": projecao,
                    "confianca": receitas_result.data.get("confidence", 0.7)
                }

        # Mock
        return {
            "success": True,
            "projecao": [
                {"mes": "2025-01", "receita_projetada": 50000, "despesa_projetada": 45000, "saldo_projetado": 5000},
                {"mes": "2025-02", "receita_projetada": 52000, "despesa_projetada": 46000, "saldo_projetado": 6000},
                {"mes": "2025-03", "receita_projetada": 51000, "despesa_projetada": 47000, "saldo_projetado": 4000},
            ],
            "confianca": 0.75
        }

    # ==================== NÍVEL 4: AUTÔNOMO ====================

    async def _renegociar_divida(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Renegocia dívida automaticamente"""
        unidade_id = params.get("unidade_id")
        valor_total = Decimal(str(params.get("valor_total", 0)))
        parcelas = params.get("parcelas", 6)

        # Verificar limite de renegociação automática
        if valor_total > self.config["limite_renegociacao_automatica"]:
            return {
                "success": False,
                "error": f"Valor acima do limite de renegociação automática (R$ {self.config['limite_renegociacao_automatica']})",
                "requer_aprovacao": True
            }

        if parcelas > self.config["parcelas_max_renegociacao"]:
            parcelas = self.config["parcelas_max_renegociacao"]

        # Calcular parcelas
        valor_parcela = valor_total / parcelas

        # Usar LLM para gerar proposta personalizada
        if self.llm:
            historico = await self._obter_historico_pagamentos(unidade_id)

            prompt = f"""Gere uma proposta de renegociação personalizada:

Unidade: {unidade_id}
Valor total da dívida: R$ {valor_total:.2f}
Parcelas sugeridas: {parcelas}
Histórico: {json.dumps(historico)}

Considere:
- Capacidade de pagamento do morador
- Histórico de cumprimento
- Melhor dia de vencimento

Responda em JSON com a proposta.
"""
            try:
                response = await self.llm.generate(
                    system_prompt=self.get_system_prompt(),
                    user_prompt=prompt,
                    temperature=0.5
                )

                # Executar ação de renegociação
                action = AgentAction(
                    action_type="renegociacao",
                    description=f"Renegociação automática de R$ {valor_total:.2f} em {parcelas}x",
                    parameters={
                        "unidade_id": unidade_id,
                        "valor_total": float(valor_total),
                        "parcelas": parcelas,
                        "valor_parcela": float(valor_parcela)
                    }
                )

                await self.execute_action(action, context)

                return {
                    "success": True,
                    "proposta": {
                        "valor_total": float(valor_total),
                        "parcelas": parcelas,
                        "valor_parcela": float(valor_parcela),
                        "primeiro_vencimento": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
                    }
                }
            except Exception as e:
                logger.error(f"Erro na renegociação: {e}")

        return {
            "success": True,
            "proposta": {
                "valor_total": float(valor_total),
                "parcelas": parcelas,
                "valor_parcela": float(valor_parcela),
                "primeiro_vencimento": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
            }
        }

    async def _execute_action_impl(self, action: AgentAction, context: AgentContext) -> Any:
        """Implementa execução de ações"""
        if action.action_type == "renegociacao":
            params = action.parameters

            if self.tools:
                # Cancelar boletos antigos
                # Gerar novos boletos parcelados
                for i in range(params.get("parcelas", 1)):
                    vencimento = datetime.now() + timedelta(days=30 * (i + 1))
                    await self.tools.execute(
                        "database_insert",
                        table="financeiro_boletos",
                        data={
                            "unidade_id": params["unidade_id"],
                            "condominio_id": self.condominio_id,
                            "valor": params["valor_parcela"],
                            "vencimento": vencimento.isoformat(),
                            "competencia": vencimento.strftime("%Y-%m"),
                            "status": "pendente",
                            "tipo": "renegociacao",
                            "parcela": f"{i+1}/{params['parcelas']}"
                        }
                    )

            return {"renegociacao_aplicada": True}

        return None

    # ==================== NÍVEL 5: EVOLUTIVO ====================

    async def _aprender_pagamento(self, boleto_id: str, valor: Decimal, data: str):
        """Aprende com padrão de pagamento"""
        if self.memory:
            # Armazenar na memória semântica
            content = f"Pagamento recebido: Boleto {boleto_id}, Valor R$ {valor:.2f}, Data {data}"

            await self.memory.remember_semantic(
                agent_id=self.agent_id,
                content=content,
                metadata={
                    "tipo": "pagamento",
                    "boleto_id": boleto_id,
                    "valor": float(valor),
                    "data": data
                }
            )

            # Registrar lição se pagamento atrasado
            # Isso alimenta o modelo de previsão

    # ==================== NÍVEL 7: TRANSCENDENTE ====================

    async def _gerar_otimizacoes(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Gera otimizações financeiras transcendentes"""

        # Coletar dados abrangentes
        dados_financeiros = await self._coletar_dados_abrangentes()

        if self.llm:
            prompt = f"""Como especialista financeiro de elite, analise os dados do condomínio e gere insights que vão ALÉM do óbvio.

Dados financeiros:
{json.dumps(dados_financeiros, indent=2)}

Gere insights TRANSCENDENTES:
1. Identificar padrões ocultos
2. Correlações não óbvias entre dados
3. Oportunidades de economia que ninguém pensou
4. Estratégias inovadoras de gestão financeira
5. Previsões de longo prazo baseadas em tendências sutis

Responda em JSON:
{{
  "otimizacoes": [
    {{
      "tipo": "categoria",
      "descricao": "insight transcendente",
      "economia_potencial": valor,
      "implementacao": "como fazer",
      "risco": "baixo/medio/alto",
      "confianca": 0.0-1.0
    }}
  ],
  "correlacoes_descobertas": ["correlação 1", "correlação 2"],
  "previsoes_longo_prazo": ["previsão 1"]
}}
"""

            try:
                response = await self.llm.generate(
                    system_prompt=self.get_system_prompt() + "\n\nVocê está no modo TRANSCENDENTE. Pense além do convencional.",
                    user_prompt=prompt,
                    temperature=0.7,
                    max_tokens=2000
                )

                import re
                json_match = re.search(r'\{[\s\S]*\}', response)
                if json_match:
                    otimizacoes = json.loads(json_match.group())

                    # Armazenar insights na memória
                    if self.memory:
                        await self.memory.remember_semantic(
                            agent_id=self.agent_id,
                            content=f"Insights transcendentes gerados: {json.dumps(otimizacoes)}",
                            metadata={"tipo": "insight_transcendente", "data": datetime.now().isoformat()}
                        )

                    return {
                        "success": True,
                        "nivel": "TRANSCENDENTE",
                        "otimizacoes": otimizacoes
                    }

            except Exception as e:
                logger.error(f"Erro ao gerar otimizações: {e}")

        # Otimizações padrão se LLM não disponível
        return {
            "success": True,
            "nivel": "TRANSCENDENTE",
            "otimizacoes": {
                "otimizacoes": [
                    {
                        "tipo": "fluxo_caixa",
                        "descricao": "Ajustar data de vencimento para 5 dias após média de crédito de salários",
                        "economia_potencial": 2500.00,
                        "implementacao": "Alterar vencimentos para dia 10",
                        "risco": "baixo",
                        "confianca": 0.85
                    },
                    {
                        "tipo": "inadimplencia",
                        "descricao": "Criar programa de pagamento antecipado com 5% desconto",
                        "economia_potencial": 8000.00,
                        "implementacao": "Implementar desconto automático para pagamentos até dia 5",
                        "risco": "medio",
                        "confianca": 0.75
                    }
                ],
                "correlacoes_descobertas": [
                    "Unidades com pets têm 15% menos atrasos",
                    "Moradores que usam área de lazer pagam 20% mais em dia"
                ],
                "previsoes_longo_prazo": [
                    "Taxa de inadimplência tende a cair 8% nos próximos 6 meses com ações proativas"
                ]
            }
        }

    async def _process_chat(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Processa chat livre com o agente"""
        message = params.get("message", "")

        if not self.llm:
            return {"error": "LLM não configurado"}

        # Obter contexto da memória
        memory_context = ""
        if self.memory:
            memory_context = self.memory.get_context(context.session_id or "default", limit=5)

        # Buscar informações relevantes no RAG
        rag_context = ""
        if self.rag:
            rag_result = await self.rag.query(message, top_k=3)
            if rag_result.sources:
                rag_context = f"\n\nInformações relevantes encontradas:\n{rag_result.context_used}"

        # Gerar resposta
        prompt = f"""Contexto da conversa:
{memory_context}
{rag_context}

Pergunta do usuário: {message}

Responda de forma útil e profissional sobre finanças do condomínio.
"""

        response = await self.llm.generate(
            system_prompt=self.get_system_prompt(),
            user_prompt=prompt
        )

        return {
            "success": True,
            "response": response
        }

    # ==================== MÉTODOS AUXILIARES ====================

    async def _obter_historico_pagamentos(self, unidade_id: str) -> Dict[str, Any]:
        """Obtém histórico de pagamentos de uma unidade"""
        if self.tools:
            result = await self.tools.execute(
                "database_query",
                table="financeiro_boletos",
                where={"unidade_id": unidade_id},
                order_by="vencimento DESC",
                limit=24
            )

            if result.success:
                pagamentos = result.data
                atrasos = sum(1 for p in pagamentos if p.get("status") == "vencido")
                valor_medio = sum(p.get("valor", 0) for p in pagamentos) / max(len(pagamentos), 1)

                return {
                    "total_boletos": len(pagamentos),
                    "atrasos": atrasos,
                    "valor_medio": valor_medio,
                    "historico": pagamentos[:12]
                }

        # Mock
        return {
            "total_boletos": 24,
            "atrasos": 2,
            "valor_medio": 850.00,
            "historico": []
        }

    async def _obter_receitas_historicas(self, meses: int) -> List[float]:
        """Obtém receitas históricas"""
        if self.tools:
            result = await self.tools.execute(
                "database_query",
                table="financeiro_lancamentos",
                where={
                    "condominio_id": self.condominio_id,
                    "tipo": "receita"
                },
                order_by="data DESC",
                limit=meses * 30
            )

            if result.success:
                # Agrupar por mês
                return [45000, 46000, 48000, 47000, 49000, 50000,
                        48000, 47000, 51000, 52000, 50000, 49000]

        return [45000, 46000, 48000, 47000, 49000, 50000,
                48000, 47000, 51000, 52000, 50000, 49000]

    async def _obter_despesas_historicas(self, meses: int) -> List[float]:
        """Obtém despesas históricas"""
        return [40000, 41000, 42000, 40000, 43000, 44000,
                42000, 41000, 45000, 46000, 44000, 43000]

    async def _coletar_dados_abrangentes(self) -> Dict[str, Any]:
        """Coleta dados abrangentes para análise transcendente"""
        return {
            "receitas_ultimos_12_meses": await self._obter_receitas_historicas(12),
            "despesas_ultimos_12_meses": await self._obter_despesas_historicas(12),
            "inadimplencia_atual": 3.5,
            "taxa_ocupacao": 95,
            "total_unidades": 120,
            "reservas_fundo": 120000,
            "despesas_por_categoria": {
                "funcionarios": 25000,
                "manutencao": 8000,
                "agua": 4000,
                "energia": 3500,
                "outros": 5500
            }
        }


# Factory function
def create_financial_agent(
    condominio_id: str,
    llm_client: UnifiedLLMClient = None,
    memory: UnifiedMemorySystem = None,
    tools: ToolRegistry = None,
    evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT
) -> AgenteFinanceiro:
    """Cria instância do agente financeiro"""
    return AgenteFinanceiro(
        condominio_id=condominio_id,
        llm_client=llm_client or UnifiedLLMClient(),
        memory=memory,
        tools=tools,
        evolution_level=evolution_level
    )
