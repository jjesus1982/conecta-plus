"""
Conecta Plus - Agente Comercial (Nível 7)
Sistema inteligente de gestão comercial e vendas

Capacidades:
1. REATIVO: Atender leads, responder cotações
2. PROATIVO: Prospectar, nutrir leads
3. PREDITIVO: Prever conversões, identificar oportunidades
4. AUTÔNOMO: Qualificar leads, gerar propostas
5. EVOLUTIVO: Aprender padrões de conversão
6. COLABORATIVO: Integrar Marketing, Suporte, Financeiro
7. TRANSCENDENTE: Vendas cognitivas inteligentes
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


class StatusLead(Enum):
    NOVO = "novo"
    QUALIFICANDO = "qualificando"
    QUALIFICADO = "qualificado"
    PROPOSTA = "proposta"
    NEGOCIACAO = "negociacao"
    FECHADO_GANHO = "fechado_ganho"
    FECHADO_PERDIDO = "fechado_perdido"


class FonteLead(Enum):
    SITE = "site"
    INDICACAO = "indicacao"
    EVENTO = "evento"
    PARCEIRO = "parceiro"
    MARKETING = "marketing"
    OUTBOUND = "outbound"


class TipoProduto(Enum):
    BASICO = "basico"
    PROFISSIONAL = "profissional"
    ENTERPRISE = "enterprise"
    PERSONALIZADO = "personalizado"


@dataclass
class Lead:
    id: str
    nome: str
    email: str
    telefone: str
    empresa: str  # Nome do condomínio
    fonte: FonteLead
    status: StatusLead
    score: int = 0
    unidades: int = 0
    responsavel: Optional[str] = None
    data_criacao: datetime = field(default_factory=datetime.now)
    ultima_interacao: Optional[datetime] = None
    proximo_contato: Optional[datetime] = None
    valor_estimado: float = 0.0
    interacoes: List[Dict] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


@dataclass
class Proposta:
    id: str
    lead_id: str
    produto: TipoProduto
    valor_mensal: float
    valor_implantacao: float
    desconto: float = 0.0
    validade: date = None
    status: str = "rascunho"
    data_criacao: datetime = field(default_factory=datetime.now)


class AgenteComercial(BaseAgent):
    """Agente Comercial - Nível 7"""

    def __init__(
        self,
        condominio_id: str,
        llm_client: UnifiedLLMClient = None,
        memory: UnifiedMemorySystem = None,
        tools: ToolRegistry = None,
        evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT,
    ):
        super().__init__(
            agent_id=f"comercial_{condominio_id}",
            agent_type="comercial",
            condominio_id=condominio_id,
            evolution_level=evolution_level,
            llm_client=llm_client,
            memory_store=memory,
        )
        self.tools = tools
        self._leads: Dict[str, Lead] = {}
        self._propostas: Dict[str, Proposta] = {}

        self.config = {
            "score_qualificado": 70,
            "dias_follow_up": 3,
            "auto_qualificar": True,
            "gerar_proposta_automatica": True,
        }

        self.precos = {
            TipoProduto.BASICO: {"por_unidade": 5.0, "implantacao": 500},
            TipoProduto.PROFISSIONAL: {"por_unidade": 10.0, "implantacao": 1500},
            TipoProduto.ENTERPRISE: {"por_unidade": 18.0, "implantacao": 3000},
        }

    def _register_capabilities(self) -> None:
        self._capabilities["gestao_leads"] = AgentCapability(
            name="gestao_leads", description="Gerenciar leads e oportunidades",
            level=EvolutionLevel.REACTIVE
        )
        self._capabilities["prospeccao"] = AgentCapability(
            name="prospeccao", description="Prospectar e nutrir leads",
            level=EvolutionLevel.PROACTIVE
        )
        self._capabilities["previsao_vendas"] = AgentCapability(
            name="previsao_vendas", description="Prever conversões",
            level=EvolutionLevel.PREDICTIVE
        )
        self._capabilities["qualificacao_autonoma"] = AgentCapability(
            name="qualificacao_autonoma", description="Qualificar leads automaticamente",
            level=EvolutionLevel.AUTONOMOUS
        )
        self._capabilities["vendas_cognitivas"] = AgentCapability(
            name="vendas_cognitivas", description="Vendas cognitivas inteligentes",
            level=EvolutionLevel.TRANSCENDENT
        )

    def get_system_prompt(self) -> str:
        return f"""Você é o Agente Comercial do Conecta Plus.
ID: {self.agent_id} | Nível: {self.evolution_level.name}

Responsabilidades:
- Captar e qualificar leads
- Gerar e acompanhar propostas
- Nutrir relacionamento com prospects
- Fechar vendas
- Analisar pipeline comercial

Produtos:
- Básico: R$ 5/unidade - Funções essenciais
- Profissional: R$ 10/unidade - Automação e IA
- Enterprise: R$ 18/unidade - Solução completa + suporte premium

Comportamento:
- Seja consultivo, não vendedor
- Entenda a dor do cliente
- Apresente valor, não preço
"""

    async def process(self, input_data: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        action = input_data.get("action", "")
        params = input_data.get("params", {})

        if action == "criar_lead":
            return await self._criar_lead(params, context)
        elif action == "atualizar_lead":
            return await self._atualizar_lead(params, context)
        elif action == "listar_leads":
            return await self._listar_leads(params, context)
        elif action == "qualificar_lead":
            return await self._qualificar_lead(params, context)
        elif action == "criar_proposta":
            return await self._criar_proposta(params, context)
        elif action == "pipeline":
            return await self._pipeline(params, context)
        elif action == "follow_up":
            return await self._follow_up(params, context)
        elif action == "previsao":
            return await self._previsao_vendas(params, context)
        elif action == "chat_comercial":
            return await self._chat_comercial(params, context)
        elif action == "chat":
            return await self._chat(params, context)
        else:
            return {"error": f"Ação '{action}' não reconhecida"}

    async def _criar_lead(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        fonte = FonteLead(params.get("fonte", "site"))

        lead = Lead(
            id=f"lead_{datetime.now().timestamp()}",
            nome=params.get("nome", ""),
            email=params.get("email", ""),
            telefone=params.get("telefone", ""),
            empresa=params.get("empresa", ""),  # Nome do condomínio
            fonte=fonte,
            status=StatusLead.NOVO,
            unidades=params.get("unidades", 0),
            tags=params.get("tags", [])
        )
        self._leads[lead.id] = lead

        # Score inicial
        lead.score = self._calcular_score_inicial(lead)

        # Estimar valor
        lead.valor_estimado = self._estimar_valor(lead.unidades)

        # Qualificar automaticamente se configurado
        if self.config["auto_qualificar"] and self.has_capability("qualificacao_autonoma"):
            await self._qualificar_lead({"lead_id": lead.id}, context)

        # Notificar equipe comercial
        if self.tools:
            await self.tools.execute(
                "send_notification",
                user_ids=["comercial"],
                title="Novo Lead!",
                message=f"{lead.empresa} - {lead.unidades} unidades - Score: {lead.score}",
                channels=["push"]
            )

        return {
            "success": True,
            "lead_id": lead.id,
            "score": lead.score,
            "valor_estimado": lead.valor_estimado
        }

    def _calcular_score_inicial(self, lead: Lead) -> int:
        score = 0

        # Tamanho do condomínio
        if lead.unidades >= 200:
            score += 30
        elif lead.unidades >= 100:
            score += 25
        elif lead.unidades >= 50:
            score += 20
        elif lead.unidades >= 20:
            score += 10

        # Fonte do lead
        fonte_scores = {
            FonteLead.INDICACAO: 25,
            FonteLead.EVENTO: 20,
            FonteLead.PARCEIRO: 20,
            FonteLead.SITE: 15,
            FonteLead.MARKETING: 10,
            FonteLead.OUTBOUND: 5,
        }
        score += fonte_scores.get(lead.fonte, 10)

        # Email corporativo
        if lead.email and not any(d in lead.email for d in ["gmail", "hotmail", "yahoo"]):
            score += 10

        # Telefone informado
        if lead.telefone:
            score += 10

        return min(score, 100)

    def _estimar_valor(self, unidades: int) -> float:
        # Valor médio por unidade (plano profissional)
        return unidades * 10.0 * 12  # Valor anual

    async def _atualizar_lead(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        lead_id = params.get("lead_id")

        if lead_id not in self._leads:
            return {"error": "Lead não encontrado"}

        lead = self._leads[lead_id]

        if "status" in params:
            lead.status = StatusLead(params["status"])
        if "responsavel" in params:
            lead.responsavel = params["responsavel"]
        if "proximo_contato" in params:
            lead.proximo_contato = datetime.fromisoformat(params["proximo_contato"])
        if "score" in params:
            lead.score = params["score"]

        # Registrar interação
        if "interacao" in params:
            lead.interacoes.append({
                "timestamp": datetime.now().isoformat(),
                **params["interacao"]
            })
            lead.ultima_interacao = datetime.now()

        return {
            "success": True,
            "lead_id": lead_id,
            "status": lead.status.value
        }

    async def _listar_leads(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        status_filtro = params.get("status")
        responsavel = params.get("responsavel")
        score_minimo = params.get("score_minimo", 0)
        limite = params.get("limite", 50)

        leads = list(self._leads.values())

        if status_filtro:
            leads = [l for l in leads if l.status.value == status_filtro]
        if responsavel:
            leads = [l for l in leads if l.responsavel == responsavel]
        leads = [l for l in leads if l.score >= score_minimo]

        # Ordenar por score
        leads = sorted(leads, key=lambda l: l.score, reverse=True)[:limite]

        return {
            "success": True,
            "leads": [
                {
                    "id": l.id,
                    "nome": l.nome,
                    "empresa": l.empresa,
                    "unidades": l.unidades,
                    "score": l.score,
                    "status": l.status.value,
                    "valor_estimado": l.valor_estimado
                }
                for l in leads
            ]
        }

    async def _qualificar_lead(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        lead_id = params.get("lead_id")

        if lead_id not in self._leads:
            return {"error": "Lead não encontrado"}

        lead = self._leads[lead_id]

        if self.llm:
            prompt = f"""Qualifique este lead para venda de sistema de gestão condominial:
Nome: {lead.nome}
Empresa/Condomínio: {lead.empresa}
Unidades: {lead.unidades}
Fonte: {lead.fonte.value}
Score atual: {lead.score}

Avalie:
1. Fit com o produto (1-10)
2. Budget provável (1-10)
3. Autoridade de decisão (1-10)
4. Necessidade/urgência (1-10)
5. Próximos passos recomendados
"""
            response = await self.llm.generate(self.get_system_prompt(), prompt)

            lead.status = StatusLead.QUALIFICANDO
            lead.interacoes.append({
                "timestamp": datetime.now().isoformat(),
                "tipo": "qualificacao_ia",
                "resultado": response
            })

            return {
                "success": True,
                "lead_id": lead_id,
                "qualificacao": response
            }

        # Qualificação básica
        if lead.score >= self.config["score_qualificado"]:
            lead.status = StatusLead.QUALIFICADO
        else:
            lead.status = StatusLead.QUALIFICANDO

        return {
            "success": True,
            "lead_id": lead_id,
            "status": lead.status.value
        }

    async def _criar_proposta(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        lead_id = params.get("lead_id")
        produto = TipoProduto(params.get("produto", "profissional"))
        desconto = params.get("desconto", 0)

        if lead_id not in self._leads:
            return {"error": "Lead não encontrado"}

        lead = self._leads[lead_id]
        preco = self.precos.get(produto, self.precos[TipoProduto.PROFISSIONAL])

        valor_mensal = lead.unidades * preco["por_unidade"]
        valor_mensal_com_desconto = valor_mensal * (1 - desconto/100)

        proposta = Proposta(
            id=f"prop_{datetime.now().timestamp()}",
            lead_id=lead_id,
            produto=produto,
            valor_mensal=valor_mensal_com_desconto,
            valor_implantacao=preco["implantacao"],
            desconto=desconto,
            validade=date.today() + timedelta(days=15),
            status="enviada"
        )
        self._propostas[proposta.id] = proposta

        # Atualizar status do lead
        lead.status = StatusLead.PROPOSTA

        # Gerar documento da proposta com LLM
        if self.llm and self.has_capability("vendas_cognitivas"):
            prompt = f"""Gere texto personalizado para proposta comercial:
Cliente: {lead.empresa}
Unidades: {lead.unidades}
Produto: {produto.value}
Valor mensal: R$ {valor_mensal_com_desconto:.2f}
Implantação: R$ {preco['implantacao']:.2f}
Desconto: {desconto}%

Inclua:
1. Apresentação personalizada
2. Benefícios específicos
3. Escopo detalhado
4. Condições comerciais
5. Próximos passos
"""
            texto_proposta = await self.llm.generate(self.get_system_prompt(), prompt)
        else:
            texto_proposta = None

        return {
            "success": True,
            "proposta_id": proposta.id,
            "valor_mensal": proposta.valor_mensal,
            "valor_implantacao": proposta.valor_implantacao,
            "validade": proposta.validade.isoformat(),
            "texto": texto_proposta
        }

    async def _pipeline(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        leads = list(self._leads.values())

        pipeline = {
            "novo": [],
            "qualificando": [],
            "qualificado": [],
            "proposta": [],
            "negociacao": [],
            "fechado_ganho": [],
            "fechado_perdido": []
        }

        for lead in leads:
            pipeline[lead.status.value].append({
                "id": lead.id,
                "empresa": lead.empresa,
                "valor": lead.valor_estimado
            })

        # Calcular métricas
        total_pipeline = sum(l.valor_estimado for l in leads if l.status not in [StatusLead.FECHADO_GANHO, StatusLead.FECHADO_PERDIDO])
        fechados = sum(l.valor_estimado for l in leads if l.status == StatusLead.FECHADO_GANHO)

        return {
            "success": True,
            "pipeline": pipeline,
            "metricas": {
                "total_leads": len(leads),
                "valor_pipeline": total_pipeline,
                "valor_fechado": fechados
            }
        }

    async def _follow_up(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Identificar leads que precisam de follow-up"""
        dias = params.get("dias", self.config["dias_follow_up"])
        data_limite = datetime.now() - timedelta(days=dias)

        leads_follow_up = []
        for lead in self._leads.values():
            if lead.status in [StatusLead.QUALIFICADO, StatusLead.PROPOSTA, StatusLead.NEGOCIACAO]:
                if not lead.ultima_interacao or lead.ultima_interacao < data_limite:
                    leads_follow_up.append(lead)

        # Gerar sugestões de mensagem
        sugestoes = []
        if self.llm and leads_follow_up:
            for lead in leads_follow_up[:5]:  # Top 5
                prompt = f"""Sugira mensagem de follow-up para:
Lead: {lead.nome}
Empresa: {lead.empresa}
Status: {lead.status.value}
Última interação: {lead.ultima_interacao}

Mensagem deve ser:
1. Personalizada
2. Agregar valor
3. Ter call-to-action claro
"""
                sugestao = await self.llm.generate(self.get_system_prompt(), prompt)
                sugestoes.append({
                    "lead_id": lead.id,
                    "empresa": lead.empresa,
                    "sugestao": sugestao
                })

        return {
            "success": True,
            "leads_follow_up": len(leads_follow_up),
            "sugestoes": sugestoes
        }

    async def _previsao_vendas(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        if not self.has_capability("previsao_vendas"):
            return {"error": "Capacidade preditiva não disponível"}

        meses = params.get("meses", 3)

        if self.llm:
            pipeline = await self._pipeline({}, context)

            prompt = f"""Faça previsão de vendas para os próximos {meses} meses:
Pipeline atual: {json.dumps(pipeline)}

Considere:
1. Taxa de conversão por estágio
2. Ciclo médio de vendas
3. Sazonalidade

Forneça:
1. Previsão de receita por mês
2. Número de fechamentos esperados
3. Riscos e oportunidades
4. Ações recomendadas
"""
            response = await self.llm.generate(self.get_system_prompt(), prompt)
            return {"success": True, "previsao": response}

        return {
            "success": True,
            "previsao_simplificada": {
                "mes_1": pipeline["metricas"]["valor_pipeline"] * 0.2,
                "mes_2": pipeline["metricas"]["valor_pipeline"] * 0.3,
                "mes_3": pipeline["metricas"]["valor_pipeline"] * 0.25
            }
        }

    async def _chat_comercial(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Chat para atendimento comercial de prospects"""
        mensagem = params.get("mensagem", "")
        lead_id = params.get("lead_id")

        if self.llm:
            contexto_lead = ""
            if lead_id and lead_id in self._leads:
                lead = self._leads[lead_id]
                contexto_lead = f"\nLead: {lead.empresa}, {lead.unidades} unidades, Status: {lead.status.value}"

            prompt = f"""Você é o consultor comercial do Conecta Plus.
{contexto_lead}

Mensagem do prospect: {mensagem}

Responda de forma:
1. Consultiva e não agressiva
2. Focada em resolver a dor do cliente
3. Destacando benefícios, não features
4. Com próximo passo claro
"""
            response = await self.llm.generate(self.get_system_prompt(), prompt)
            return {"success": True, "resposta": response}

        return {"error": "Chat indisponível"}

    async def _chat(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        if self.llm:
            response = await self.llm.generate(
                self.get_system_prompt(), params.get("message", "")
            )
            return {"success": True, "response": response}
        return {"error": "LLM não configurado"}


def create_sales_agent(
    condominio_id: str,
    llm_client: UnifiedLLMClient = None,
    memory: UnifiedMemorySystem = None,
    tools: ToolRegistry = None,
    evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT
) -> AgenteComercial:
    return AgenteComercial(
        condominio_id=condominio_id,
        llm_client=llm_client or UnifiedLLMClient(),
        memory=memory, tools=tools,
        evolution_level=evolution_level
    )
