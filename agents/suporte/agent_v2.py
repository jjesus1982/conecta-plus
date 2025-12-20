"""
Conecta Plus - Agente de Suporte (Nível 7)
Sistema inteligente de atendimento e suporte ao cliente

Capacidades:
1. REATIVO: Atender tickets, responder dúvidas
2. PROATIVO: Alertar problemas, sugerir soluções
3. PREDITIVO: Prever demandas, identificar padrões
4. AUTÔNOMO: Resolver automaticamente, escalar inteligente
5. EVOLUTIVO: Aprender com resoluções anteriores
6. COLABORATIVO: Integrar todos os agentes
7. TRANSCENDENTE: Suporte cognitivo omnichannel
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
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


class TipoTicket(Enum):
    DUVIDA = "duvida"
    PROBLEMA = "problema"
    SOLICITACAO = "solicitacao"
    RECLAMACAO = "reclamacao"
    SUGESTAO = "sugestao"


class StatusTicket(Enum):
    ABERTO = "aberto"
    EM_ATENDIMENTO = "em_atendimento"
    AGUARDANDO_USUARIO = "aguardando_usuario"
    AGUARDANDO_TERCEIRO = "aguardando_terceiro"
    RESOLVIDO = "resolvido"
    FECHADO = "fechado"


class PrioridadeTicket(Enum):
    BAIXA = "baixa"
    MEDIA = "media"
    ALTA = "alta"
    URGENTE = "urgente"


class CanalAtendimento(Enum):
    APP = "app"
    WEB = "web"
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    TELEFONE = "telefone"
    CHAT = "chat"


@dataclass
class Ticket:
    id: str
    tipo: TipoTicket
    titulo: str
    descricao: str
    canal: CanalAtendimento
    prioridade: PrioridadeTicket
    status: StatusTicket
    solicitante_id: str
    atendente_id: Optional[str] = None
    categoria: str = ""
    data_abertura: datetime = field(default_factory=datetime.now)
    data_atualizacao: Optional[datetime] = None
    data_resolucao: Optional[datetime] = None
    resolucao: str = ""
    satisfacao: Optional[int] = None
    interacoes: List[Dict] = field(default_factory=list)


@dataclass
class BaseConhecimento:
    id: str
    titulo: str
    conteudo: str
    categoria: str
    tags: List[str]
    visualizacoes: int = 0
    util: int = 0
    nao_util: int = 0


class AgenteSuporte(BaseAgent):
    """Agente de Suporte - Nível 7"""

    def __init__(
        self,
        condominio_id: str,
        llm_client: UnifiedLLMClient = None,
        memory: UnifiedMemorySystem = None,
        tools: ToolRegistry = None,
        evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT,
    ):
        super().__init__(
            agent_id=f"suporte_{condominio_id}",
            agent_type="suporte",
            condominio_id=condominio_id,
            evolution_level=evolution_level,
            llm_client=llm_client,
            memory_store=memory,
        )
        self.tools = tools
        self._tickets: Dict[str, Ticket] = {}
        self._base_conhecimento: Dict[str, BaseConhecimento] = {}

        self.config = {
            "sla_urgente_horas": 4,
            "sla_alta_horas": 8,
            "sla_media_horas": 24,
            "sla_baixa_horas": 48,
            "resolucao_automatica": True,
            "escalar_automatico": True,
        }

    def _register_capabilities(self) -> None:
        self._capabilities["atendimento"] = AgentCapability(
            name="atendimento", description="Atender tickets de suporte",
            level=EvolutionLevel.REACTIVE
        )
        self._capabilities["sugestao_solucoes"] = AgentCapability(
            name="sugestao_solucoes", description="Sugerir soluções proativamente",
            level=EvolutionLevel.PROACTIVE
        )
        self._capabilities["previsao_demanda"] = AgentCapability(
            name="previsao_demanda", description="Prever demandas de suporte",
            level=EvolutionLevel.PREDICTIVE
        )
        self._capabilities["resolucao_autonoma"] = AgentCapability(
            name="resolucao_autonoma", description="Resolver automaticamente",
            level=EvolutionLevel.AUTONOMOUS
        )
        self._capabilities["suporte_cognitivo"] = AgentCapability(
            name="suporte_cognitivo", description="Suporte cognitivo omnichannel",
            level=EvolutionLevel.TRANSCENDENT
        )

    def get_system_prompt(self) -> str:
        return f"""Você é o Agente de Suporte do Conecta Plus.
ID: {self.agent_id} | Condomínio: {self.condominio_id} | Nível: {self.evolution_level.name}

Responsabilidades:
- Atender tickets e chamados
- Resolver dúvidas e problemas
- Escalar quando necessário
- Manter base de conhecimento
- Garantir satisfação do usuário

SLAs:
- Urgente: {self.config['sla_urgente_horas']}h
- Alta: {self.config['sla_alta_horas']}h
- Média: {self.config['sla_media_horas']}h
- Baixa: {self.config['sla_baixa_horas']}h

Comportamento:
- Seja cordial e empático
- Busque resolver na primeira interação
- Mantenha o usuário informado
"""

    async def process(self, input_data: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        action = input_data.get("action", "")
        params = input_data.get("params", {})

        if action == "abrir_ticket":
            return await self._abrir_ticket(params, context)
        elif action == "atualizar_ticket":
            return await self._atualizar_ticket(params, context)
        elif action == "listar_tickets":
            return await self._listar_tickets(params, context)
        elif action == "resolver_ticket":
            return await self._resolver_ticket(params, context)
        elif action == "buscar_solucao":
            return await self._buscar_solucao(params, context)
        elif action == "avaliar_atendimento":
            return await self._avaliar_atendimento(params, context)
        elif action == "dashboard":
            return await self._dashboard(params, context)
        elif action == "chat_suporte":
            return await self._chat_suporte(params, context)
        elif action == "chat":
            return await self._chat(params, context)
        else:
            return {"error": f"Ação '{action}' não reconhecida"}

    async def _abrir_ticket(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        tipo = TipoTicket(params.get("tipo", "duvida"))
        canal = CanalAtendimento(params.get("canal", "app"))
        descricao = params.get("descricao", "")

        # Classificar prioridade automaticamente
        prioridade = PrioridadeTicket(params.get("prioridade", "media"))
        if self.has_capability("resolucao_autonoma") and self.llm:
            classificacao = await self._classificar_ticket(descricao)
            prioridade = PrioridadeTicket(classificacao.get("prioridade", "media"))
            categoria = classificacao.get("categoria", "geral")
        else:
            categoria = params.get("categoria", "geral")

        ticket = Ticket(
            id=f"ticket_{datetime.now().timestamp()}",
            tipo=tipo,
            titulo=params.get("titulo", descricao[:50]),
            descricao=descricao,
            canal=canal,
            prioridade=prioridade,
            status=StatusTicket.ABERTO,
            solicitante_id=params.get("solicitante_id", ""),
            categoria=categoria
        )
        self._tickets[ticket.id] = ticket

        # Tentar resolução automática
        if self.config["resolucao_automatica"] and self.has_capability("resolucao_autonoma"):
            solucao = await self._buscar_solucao({"query": descricao}, context)
            if solucao.get("solucao_encontrada"):
                ticket.interacoes.append({
                    "timestamp": datetime.now().isoformat(),
                    "tipo": "resposta_automatica",
                    "mensagem": solucao.get("resposta")
                })
                ticket.status = StatusTicket.AGUARDANDO_USUARIO

        # Notificar
        if self.tools:
            await self.tools.execute(
                "send_notification",
                user_ids=[ticket.solicitante_id],
                title="Ticket Aberto",
                message=f"Seu ticket #{ticket.id} foi aberto com sucesso",
                channels=["push", "app"]
            )

        return {
            "success": True,
            "ticket_id": ticket.id,
            "prioridade": prioridade.value,
            "sla_horas": self._get_sla(prioridade),
            "resposta_automatica": ticket.interacoes[-1] if ticket.interacoes else None
        }

    async def _classificar_ticket(self, descricao: str) -> Dict:
        if not self.llm:
            return {"prioridade": "media", "categoria": "geral"}

        prompt = f"""Classifique este ticket de suporte:
"{descricao}"

Retorne JSON:
- prioridade: baixa, media, alta, urgente
- categoria: financeiro, acesso, manutencao, reservas, geral

Critérios:
- urgente: impacto crítico ou segurança
- alta: problema que impede uso
- media: problema com workaround
- baixa: dúvida ou sugestão
"""
        response = await self.llm.generate(self.get_system_prompt(), prompt)
        try:
            return json.loads(response)
        except:
            return {"prioridade": "media", "categoria": "geral"}

    def _get_sla(self, prioridade: PrioridadeTicket) -> int:
        slas = {
            PrioridadeTicket.URGENTE: self.config["sla_urgente_horas"],
            PrioridadeTicket.ALTA: self.config["sla_alta_horas"],
            PrioridadeTicket.MEDIA: self.config["sla_media_horas"],
            PrioridadeTicket.BAIXA: self.config["sla_baixa_horas"],
        }
        return slas.get(prioridade, 24)

    async def _atualizar_ticket(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        ticket_id = params.get("ticket_id")
        mensagem = params.get("mensagem")

        if ticket_id not in self._tickets:
            return {"error": "Ticket não encontrado"}

        ticket = self._tickets[ticket_id]

        if "status" in params:
            ticket.status = StatusTicket(params["status"])

        if mensagem:
            ticket.interacoes.append({
                "timestamp": datetime.now().isoformat(),
                "tipo": "resposta",
                "autor": params.get("autor", "suporte"),
                "mensagem": mensagem
            })

        ticket.data_atualizacao = datetime.now()

        return {
            "success": True,
            "ticket_id": ticket_id,
            "status": ticket.status.value
        }

    async def _listar_tickets(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        status_filtro = params.get("status")
        prioridade_filtro = params.get("prioridade")
        solicitante = params.get("solicitante_id")
        limite = params.get("limite", 50)

        tickets = list(self._tickets.values())

        if status_filtro:
            tickets = [t for t in tickets if t.status.value == status_filtro]
        if prioridade_filtro:
            tickets = [t for t in tickets if t.prioridade.value == prioridade_filtro]
        if solicitante:
            tickets = [t for t in tickets if t.solicitante_id == solicitante]

        # Ordenar por prioridade e data
        prioridade_ordem = {"urgente": 0, "alta": 1, "media": 2, "baixa": 3}
        tickets = sorted(tickets, key=lambda t: (prioridade_ordem.get(t.prioridade.value, 4), t.data_abertura))
        tickets = tickets[:limite]

        return {
            "success": True,
            "tickets": [
                {
                    "id": t.id,
                    "titulo": t.titulo,
                    "tipo": t.tipo.value,
                    "prioridade": t.prioridade.value,
                    "status": t.status.value,
                    "categoria": t.categoria,
                    "data_abertura": t.data_abertura.isoformat()
                }
                for t in tickets
            ]
        }

    async def _resolver_ticket(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        ticket_id = params.get("ticket_id")
        resolucao = params.get("resolucao", "")

        if ticket_id not in self._tickets:
            return {"error": "Ticket não encontrado"}

        ticket = self._tickets[ticket_id]
        ticket.status = StatusTicket.RESOLVIDO
        ticket.resolucao = resolucao
        ticket.data_resolucao = datetime.now()

        # Notificar solicitante
        if self.tools:
            await self.tools.execute(
                "send_notification",
                user_ids=[ticket.solicitante_id],
                title="Ticket Resolvido",
                message=f"Seu ticket #{ticket_id} foi resolvido. Por favor, avalie o atendimento.",
                channels=["push", "app"]
            )

        return {
            "success": True,
            "ticket_id": ticket_id,
            "tempo_resolucao": str(ticket.data_resolucao - ticket.data_abertura)
        }

    async def _buscar_solucao(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        query = params.get("query", "")

        # Buscar na base de conhecimento
        resultados = []
        for artigo in self._base_conhecimento.values():
            if any(tag in query.lower() for tag in artigo.tags) or query.lower() in artigo.conteudo.lower():
                resultados.append(artigo)

        if resultados:
            artigo = resultados[0]
            artigo.visualizacoes += 1
            return {
                "success": True,
                "solucao_encontrada": True,
                "artigo_id": artigo.id,
                "titulo": artigo.titulo,
                "resposta": artigo.conteudo
            }

        # Se não encontrou, usar LLM
        if self.llm and self.has_capability("suporte_cognitivo"):
            prompt = f"""Responda esta dúvida de suporte sobre o sistema de condomínio:
"{query}"

Forneça resposta clara, objetiva e útil.
Se não souber, indique que será necessário encaminhar para atendimento humano.
"""
            response = await self.llm.generate(self.get_system_prompt(), prompt)
            return {
                "success": True,
                "solucao_encontrada": True,
                "resposta": response,
                "fonte": "ia"
            }

        return {"success": True, "solucao_encontrada": False}

    async def _avaliar_atendimento(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        ticket_id = params.get("ticket_id")
        nota = params.get("nota")  # 1-5
        comentario = params.get("comentario", "")

        if ticket_id not in self._tickets:
            return {"error": "Ticket não encontrado"}

        ticket = self._tickets[ticket_id]
        ticket.satisfacao = nota

        ticket.interacoes.append({
            "timestamp": datetime.now().isoformat(),
            "tipo": "avaliacao",
            "nota": nota,
            "comentario": comentario
        })

        return {
            "success": True,
            "ticket_id": ticket_id,
            "avaliacao_registrada": True
        }

    async def _dashboard(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        tickets = list(self._tickets.values())

        abertos = len([t for t in tickets if t.status in [StatusTicket.ABERTO, StatusTicket.EM_ATENDIMENTO]])
        resolvidos_hoje = len([t for t in tickets if t.status == StatusTicket.RESOLVIDO and t.data_resolucao and t.data_resolucao.date() == datetime.now().date()])

        # Satisfação média
        avaliacoes = [t.satisfacao for t in tickets if t.satisfacao]
        satisfacao_media = sum(avaliacoes) / len(avaliacoes) if avaliacoes else 0

        # SLA compliance
        dentro_sla = 0
        fora_sla = 0
        for t in tickets:
            if t.data_resolucao:
                tempo = (t.data_resolucao - t.data_abertura).total_seconds() / 3600
                sla = self._get_sla(t.prioridade)
                if tempo <= sla:
                    dentro_sla += 1
                else:
                    fora_sla += 1

        return {
            "success": True,
            "resumo": {
                "abertos": abertos,
                "resolvidos_hoje": resolvidos_hoje,
                "satisfacao_media": satisfacao_media,
                "sla_compliance": dentro_sla / (dentro_sla + fora_sla) * 100 if (dentro_sla + fora_sla) > 0 else 100
            }
        }

    async def _chat_suporte(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Chat em tempo real com suporte"""
        mensagem = params.get("mensagem", "")
        sessao_id = params.get("sessao_id")
        usuario_id = params.get("usuario_id")

        if self.llm:
            prompt = f"""Você é o assistente de suporte do condomínio.
Usuário: {usuario_id}
Mensagem: {mensagem}

Responda de forma:
1. Cordial e empática
2. Clara e objetiva
3. Oferecendo soluções práticas
4. Se necessário, sugira abrir ticket

Se for uma questão que você não pode resolver, indique claramente.
"""
            response = await self.llm.generate(self.get_system_prompt(), prompt)
            return {
                "success": True,
                "resposta": response,
                "sessao_id": sessao_id
            }

        return {"error": "Chat indisponível"}

    async def _chat(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        if self.llm:
            response = await self.llm.generate(
                self.get_system_prompt(), params.get("message", "")
            )
            return {"success": True, "response": response}
        return {"error": "LLM não configurado"}


def create_support_agent(
    condominio_id: str,
    llm_client: UnifiedLLMClient = None,
    memory: UnifiedMemorySystem = None,
    tools: ToolRegistry = None,
    evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT
) -> AgenteSuporte:
    return AgenteSuporte(
        condominio_id=condominio_id,
        llm_client=llm_client or UnifiedLLMClient(),
        memory=memory, tools=tools,
        evolution_level=evolution_level
    )
