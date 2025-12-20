"""
Conecta Plus - Agente de Manutenção (Nível 7)
Sistema inteligente de gestão de manutenção predial

Capacidades:
1. REATIVO: Registrar chamados, atribuir técnicos
2. PROATIVO: Programar manutenções preventivas
3. PREDITIVO: Prever falhas de equipamentos
4. AUTÔNOMO: Priorizar e escalar automaticamente
5. EVOLUTIVO: Aprender padrões de falhas
6. COLABORATIVO: Integrar Facilities, RH, Síndico
7. TRANSCENDENTE: Manutenção preditiva cognitiva
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


class TipoChamado(Enum):
    CORRETIVA = "corretiva"
    PREVENTIVA = "preventiva"
    EMERGENCIA = "emergencia"
    MELHORIA = "melhoria"


class StatusChamado(Enum):
    ABERTO = "aberto"
    EM_ANDAMENTO = "em_andamento"
    AGUARDANDO_PECA = "aguardando_peca"
    CONCLUIDO = "concluido"
    CANCELADO = "cancelado"


class PrioridadeChamado(Enum):
    BAIXA = "baixa"
    MEDIA = "media"
    ALTA = "alta"
    URGENTE = "urgente"


class AreaManutencao(Enum):
    ELETRICA = "eletrica"
    HIDRAULICA = "hidraulica"
    CIVIL = "civil"
    ELEVADORES = "elevadores"
    PISCINA = "piscina"
    JARDINAGEM = "jardinagem"
    AR_CONDICIONADO = "ar_condicionado"
    SEGURANCA = "seguranca"


@dataclass
class Chamado:
    id: str
    tipo: TipoChamado
    area: AreaManutencao
    titulo: str
    descricao: str
    local: str
    prioridade: PrioridadeChamado
    status: StatusChamado
    solicitante: str
    tecnico_responsavel: Optional[str] = None
    data_abertura: datetime = field(default_factory=datetime.now)
    data_previsao: Optional[datetime] = None
    data_conclusao: Optional[datetime] = None
    custo: float = 0.0
    observacoes: str = ""


@dataclass
class ManutencaoPreventiva:
    id: str
    equipamento: str
    descricao: str
    frequencia_dias: int
    ultima_execucao: Optional[date] = None
    proxima_execucao: Optional[date] = None
    ativa: bool = True


class AgenteManutencao(BaseAgent):
    """Agente de Manutenção - Nível 7"""

    def __init__(
        self,
        condominio_id: str,
        llm_client: UnifiedLLMClient = None,
        memory: UnifiedMemorySystem = None,
        tools: ToolRegistry = None,
        evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT,
    ):
        super().__init__(
            agent_id=f"manutencao_{condominio_id}",
            agent_type="manutencao",
            condominio_id=condominio_id,
            evolution_level=evolution_level,
            llm_client=llm_client,
            memory_store=memory,
        )
        self.tools = tools
        self._chamados: Dict[str, Chamado] = {}
        self._preventivas: Dict[str, ManutencaoPreventiva] = {}
        self._tecnicos: Dict[str, Dict] = {}

        self.config = {
            "sla_urgente_horas": 4,
            "sla_alta_horas": 24,
            "sla_media_horas": 72,
            "sla_baixa_horas": 168,
            "escalar_automatico": True,
        }

    def _register_capabilities(self) -> None:
        self._capabilities["gestao_chamados"] = AgentCapability(
            name="gestao_chamados", description="Gerenciar chamados de manutenção",
            level=EvolutionLevel.REACTIVE
        )
        self._capabilities["preventivas"] = AgentCapability(
            name="preventivas", description="Programar manutenções preventivas",
            level=EvolutionLevel.PROACTIVE
        )
        self._capabilities["previsao_falhas"] = AgentCapability(
            name="previsao_falhas", description="Prever falhas de equipamentos",
            level=EvolutionLevel.PREDICTIVE
        )
        self._capabilities["priorizacao_autonoma"] = AgentCapability(
            name="priorizacao_autonoma", description="Priorizar automaticamente",
            level=EvolutionLevel.AUTONOMOUS
        )
        self._capabilities["manutencao_cognitiva"] = AgentCapability(
            name="manutencao_cognitiva", description="Manutenção preditiva cognitiva",
            level=EvolutionLevel.TRANSCENDENT
        )

    def get_system_prompt(self) -> str:
        return f"""Você é o Agente de Manutenção do Conecta Plus.
ID: {self.agent_id} | Condomínio: {self.condominio_id} | Nível: {self.evolution_level.name}

Responsabilidades:
- Gerenciar chamados de manutenção
- Programar manutenções preventivas
- Atribuir técnicos e priorizar
- Monitorar SLAs e prazos
- Prever e prevenir falhas

SLAs:
- Urgente: {self.config['sla_urgente_horas']}h
- Alta: {self.config['sla_alta_horas']}h
- Média: {self.config['sla_media_horas']}h
- Baixa: {self.config['sla_baixa_horas']}h
"""

    async def process(self, input_data: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        action = input_data.get("action", "")
        params = input_data.get("params", {})

        if action == "abrir_chamado":
            return await self._abrir_chamado(params, context)
        elif action == "atualizar_chamado":
            return await self._atualizar_chamado(params, context)
        elif action == "listar_chamados":
            return await self._listar_chamados(params, context)
        elif action == "atribuir_tecnico":
            return await self._atribuir_tecnico(params, context)
        elif action == "programar_preventiva":
            return await self._programar_preventiva(params, context)
        elif action == "listar_preventivas":
            return await self._listar_preventivas(params, context)
        elif action == "dashboard":
            return await self._dashboard(params, context)
        elif action == "analise_preditiva":
            return await self._analise_preditiva(params, context)
        elif action == "chat":
            return await self._chat(params, context)
        else:
            return {"error": f"Ação '{action}' não reconhecida"}

    async def _abrir_chamado(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        tipo = TipoChamado(params.get("tipo", "corretiva"))
        area = AreaManutencao(params.get("area", "eletrica"))
        prioridade = PrioridadeChamado(params.get("prioridade", "media"))

        chamado = Chamado(
            id=f"chamado_{datetime.now().timestamp()}",
            tipo=tipo,
            area=area,
            titulo=params.get("titulo", ""),
            descricao=params.get("descricao", ""),
            local=params.get("local", ""),
            prioridade=prioridade,
            status=StatusChamado.ABERTO,
            solicitante=params.get("solicitante", ""),
            data_previsao=self._calcular_previsao(prioridade)
        )
        self._chamados[chamado.id] = chamado

        # Atribuir técnico automaticamente se disponível
        if self.has_capability("priorizacao_autonoma"):
            tecnico = await self._selecionar_tecnico(area)
            if tecnico:
                chamado.tecnico_responsavel = tecnico
                chamado.status = StatusChamado.EM_ANDAMENTO

        # Notificar
        if self.tools:
            destinatarios = ["manutencao"]
            if prioridade in [PrioridadeChamado.URGENTE, PrioridadeChamado.ALTA]:
                destinatarios.extend(["sindico", "zelador"])

            await self.tools.execute(
                "send_notification",
                user_ids=destinatarios,
                title=f"Novo Chamado - {prioridade.value.upper()}",
                message=f"{chamado.titulo} em {chamado.local}",
                channels=["push", "app"]
            )

        return {
            "success": True,
            "chamado_id": chamado.id,
            "prioridade": prioridade.value,
            "previsao": chamado.data_previsao.isoformat() if chamado.data_previsao else None,
            "tecnico": chamado.tecnico_responsavel
        }

    def _calcular_previsao(self, prioridade: PrioridadeChamado) -> datetime:
        horas = {
            PrioridadeChamado.URGENTE: self.config["sla_urgente_horas"],
            PrioridadeChamado.ALTA: self.config["sla_alta_horas"],
            PrioridadeChamado.MEDIA: self.config["sla_media_horas"],
            PrioridadeChamado.BAIXA: self.config["sla_baixa_horas"],
        }
        return datetime.now() + timedelta(hours=horas[prioridade])

    async def _selecionar_tecnico(self, area: AreaManutencao) -> Optional[str]:
        # Selecionar técnico disponível para a área
        for tecnico_id, info in self._tecnicos.items():
            if area.value in info.get("areas", []) and info.get("disponivel", True):
                return tecnico_id
        return None

    async def _atualizar_chamado(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        chamado_id = params.get("chamado_id")
        if chamado_id not in self._chamados:
            return {"error": "Chamado não encontrado"}

        chamado = self._chamados[chamado_id]

        if "status" in params:
            novo_status = StatusChamado(params["status"])
            chamado.status = novo_status
            if novo_status == StatusChamado.CONCLUIDO:
                chamado.data_conclusao = datetime.now()

        if "observacoes" in params:
            chamado.observacoes = params["observacoes"]

        if "custo" in params:
            chamado.custo = params["custo"]

        return {
            "success": True,
            "chamado_id": chamado_id,
            "status": chamado.status.value
        }

    async def _listar_chamados(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        status_filtro = params.get("status")
        area_filtro = params.get("area")
        prioridade_filtro = params.get("prioridade")
        limite = params.get("limite", 50)

        chamados = list(self._chamados.values())

        if status_filtro:
            chamados = [c for c in chamados if c.status.value == status_filtro]
        if area_filtro:
            chamados = [c for c in chamados if c.area.value == area_filtro]
        if prioridade_filtro:
            chamados = [c for c in chamados if c.prioridade.value == prioridade_filtro]

        # Ordenar por prioridade e data
        prioridade_ordem = {"urgente": 0, "alta": 1, "media": 2, "baixa": 3}
        chamados = sorted(chamados, key=lambda c: (prioridade_ordem.get(c.prioridade.value, 4), c.data_abertura))
        chamados = chamados[:limite]

        return {
            "success": True,
            "chamados": [
                {
                    "id": c.id,
                    "titulo": c.titulo,
                    "area": c.area.value,
                    "local": c.local,
                    "prioridade": c.prioridade.value,
                    "status": c.status.value,
                    "tecnico": c.tecnico_responsavel,
                    "data_abertura": c.data_abertura.isoformat()
                }
                for c in chamados
            ]
        }

    async def _atribuir_tecnico(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        chamado_id = params.get("chamado_id")
        tecnico_id = params.get("tecnico_id")

        if chamado_id not in self._chamados:
            return {"error": "Chamado não encontrado"}

        chamado = self._chamados[chamado_id]
        chamado.tecnico_responsavel = tecnico_id
        chamado.status = StatusChamado.EM_ANDAMENTO

        # Notificar técnico
        if self.tools:
            await self.tools.execute(
                "send_notification",
                user_ids=[tecnico_id],
                title="Novo Chamado Atribuído",
                message=f"{chamado.titulo} em {chamado.local}",
                channels=["push", "sms"]
            )

        return {
            "success": True,
            "chamado_id": chamado_id,
            "tecnico_id": tecnico_id
        }

    async def _programar_preventiva(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        preventiva = ManutencaoPreventiva(
            id=f"prev_{datetime.now().timestamp()}",
            equipamento=params.get("equipamento"),
            descricao=params.get("descricao", ""),
            frequencia_dias=params.get("frequencia_dias", 30),
            proxima_execucao=date.today() + timedelta(days=params.get("frequencia_dias", 30))
        )
        self._preventivas[preventiva.id] = preventiva

        return {
            "success": True,
            "preventiva_id": preventiva.id,
            "proxima_execucao": preventiva.proxima_execucao.isoformat()
        }

    async def _listar_preventivas(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        apenas_ativas = params.get("apenas_ativas", True)
        proximos_dias = params.get("proximos_dias")

        preventivas = list(self._preventivas.values())

        if apenas_ativas:
            preventivas = [p for p in preventivas if p.ativa]

        if proximos_dias:
            data_limite = date.today() + timedelta(days=proximos_dias)
            preventivas = [p for p in preventivas if p.proxima_execucao and p.proxima_execucao <= data_limite]

        return {
            "success": True,
            "preventivas": [
                {
                    "id": p.id,
                    "equipamento": p.equipamento,
                    "descricao": p.descricao,
                    "frequencia_dias": p.frequencia_dias,
                    "proxima_execucao": p.proxima_execucao.isoformat() if p.proxima_execucao else None
                }
                for p in preventivas
            ]
        }

    async def _dashboard(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        chamados = list(self._chamados.values())

        abertos = len([c for c in chamados if c.status == StatusChamado.ABERTO])
        em_andamento = len([c for c in chamados if c.status == StatusChamado.EM_ANDAMENTO])
        concluidos_mes = len([c for c in chamados if c.status == StatusChamado.CONCLUIDO and c.data_conclusao and c.data_conclusao.month == datetime.now().month])

        # Calcular SLA
        atrasados = 0
        for c in chamados:
            if c.status in [StatusChamado.ABERTO, StatusChamado.EM_ANDAMENTO]:
                if c.data_previsao and datetime.now() > c.data_previsao:
                    atrasados += 1

        return {
            "success": True,
            "resumo": {
                "abertos": abertos,
                "em_andamento": em_andamento,
                "concluidos_mes": concluidos_mes,
                "atrasados_sla": atrasados,
                "preventivas_pendentes": len([p for p in self._preventivas.values() if p.proxima_execucao and p.proxima_execucao <= date.today()])
            }
        }

    async def _analise_preditiva(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        if not self.has_capability("manutencao_cognitiva"):
            return {"error": "Capacidade transcendente não disponível"}

        if self.llm:
            chamados = await self._listar_chamados({"limite": 100}, context)
            preventivas = await self._listar_preventivas({}, context)
            dashboard = await self._dashboard({}, context)

            prompt = f"""Analise a manutenção do condomínio:
Chamados recentes: {chamados}
Preventivas: {preventivas}
Dashboard: {dashboard}

Gere análise TRANSCENDENTE com:
1. Equipamentos com maior incidência de falhas
2. Padrões de problemas identificados
3. Previsão de falhas próximas
4. Recomendações de preventivas adicionais
5. Otimização de recursos de manutenção
"""
            response = await self.llm.generate(self.get_system_prompt(), prompt)
            return {"success": True, "analise": response}

        return {"success": True, "analise": "Sistema operacional"}

    async def _chat(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        if self.llm:
            response = await self.llm.generate(
                self.get_system_prompt(), params.get("message", "")
            )
            return {"success": True, "response": response}
        return {"error": "LLM não configurado"}


def create_maintenance_agent(
    condominio_id: str,
    llm_client: UnifiedLLMClient = None,
    memory: UnifiedMemorySystem = None,
    tools: ToolRegistry = None,
    evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT
) -> AgenteManutencao:
    return AgenteManutencao(
        condominio_id=condominio_id,
        llm_client=llm_client or UnifiedLLMClient(),
        memory=memory, tools=tools,
        evolution_level=evolution_level
    )
