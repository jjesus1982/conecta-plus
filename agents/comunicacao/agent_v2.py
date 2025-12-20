"""
Conecta Plus - Agente de Comunicação (Nível 7)
Sistema inteligente de comunicação condominial

Capacidades:
1. REATIVO: Enviar avisos, responder consultas
2. PROATIVO: Programar comunicados, lembrar eventos
3. PREDITIVO: Prever engajamento, otimizar timing
4. AUTÔNOMO: Gerar conteúdo, segmentar público
5. EVOLUTIVO: Aprender preferências de comunicação
6. COLABORATIVO: Integrar todos os agentes
7. TRANSCENDENTE: Comunicação cognitiva multicanal
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


class TipoComunicado(Enum):
    AVISO = "aviso"
    INFORMATIVO = "informativo"
    URGENTE = "urgente"
    EVENTO = "evento"
    MANUTENCAO = "manutencao"
    FINANCEIRO = "financeiro"


class CanalComunicacao(Enum):
    PUSH = "push"
    EMAIL = "email"
    SMS = "sms"
    APP = "app"
    MURAL = "mural"
    WHATSAPP = "whatsapp"


class StatusComunicado(Enum):
    RASCUNHO = "rascunho"
    AGENDADO = "agendado"
    ENVIADO = "enviado"
    CANCELADO = "cancelado"


@dataclass
class Comunicado:
    id: str
    tipo: TipoComunicado
    titulo: str
    conteudo: str
    canais: List[CanalComunicacao]
    destinatarios: List[str]
    status: StatusComunicado
    autor: str
    data_criacao: datetime = field(default_factory=datetime.now)
    data_envio: Optional[datetime] = None
    data_agendamento: Optional[datetime] = None
    anexos: List[str] = field(default_factory=list)
    metricas: Dict = field(default_factory=dict)


@dataclass
class Enquete:
    id: str
    titulo: str
    pergunta: str
    opcoes: List[str]
    data_inicio: datetime
    data_fim: datetime
    votos: Dict[str, str] = field(default_factory=dict)
    ativa: bool = True


class AgenteComunicacao(BaseAgent):
    """Agente de Comunicação - Nível 7"""

    def __init__(
        self,
        condominio_id: str,
        llm_client: UnifiedLLMClient = None,
        memory: UnifiedMemorySystem = None,
        tools: ToolRegistry = None,
        evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT,
    ):
        super().__init__(
            agent_id=f"comunicacao_{condominio_id}",
            agent_type="comunicacao",
            condominio_id=condominio_id,
            evolution_level=evolution_level,
            llm_client=llm_client,
            memory_store=memory,
        )
        self.tools = tools
        self._comunicados: Dict[str, Comunicado] = {}
        self._enquetes: Dict[str, Enquete] = {}
        self._templates: Dict[str, str] = {}

        self.config = {
            "canais_padrao": ["push", "app"],
            "horario_envio_inicio": "08:00",
            "horario_envio_fim": "20:00",
            "max_envios_dia": 5,
            "aprovacao_sindico": False,
        }

    def _register_capabilities(self) -> None:
        self._capabilities["envio_comunicados"] = AgentCapability(
            name="envio_comunicados", description="Enviar comunicados",
            level=EvolutionLevel.REACTIVE
        )
        self._capabilities["agendamento"] = AgentCapability(
            name="agendamento", description="Agendar comunicados",
            level=EvolutionLevel.PROACTIVE
        )
        self._capabilities["otimizacao_timing"] = AgentCapability(
            name="otimizacao_timing", description="Otimizar timing de envio",
            level=EvolutionLevel.PREDICTIVE
        )
        self._capabilities["geracao_conteudo"] = AgentCapability(
            name="geracao_conteudo", description="Gerar conteúdo automaticamente",
            level=EvolutionLevel.AUTONOMOUS
        )
        self._capabilities["comunicacao_cognitiva"] = AgentCapability(
            name="comunicacao_cognitiva", description="Comunicação cognitiva multicanal",
            level=EvolutionLevel.TRANSCENDENT
        )

    def get_system_prompt(self) -> str:
        return f"""Você é o Agente de Comunicação do Conecta Plus.
ID: {self.agent_id} | Condomínio: {self.condominio_id} | Nível: {self.evolution_level.name}

Responsabilidades:
- Gerenciar comunicados do condomínio
- Enviar avisos e informativos
- Criar e gerenciar enquetes
- Otimizar engajamento
- Segmentar comunicação por público

Configurações:
- Canais padrão: {self.config['canais_padrao']}
- Horário envio: {self.config['horario_envio_inicio']} - {self.config['horario_envio_fim']}
"""

    async def process(self, input_data: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        action = input_data.get("action", "")
        params = input_data.get("params", {})

        if action == "criar_comunicado":
            return await self._criar_comunicado(params, context)
        elif action == "enviar_comunicado":
            return await self._enviar_comunicado(params, context)
        elif action == "agendar_comunicado":
            return await self._agendar_comunicado(params, context)
        elif action == "listar_comunicados":
            return await self._listar_comunicados(params, context)
        elif action == "criar_enquete":
            return await self._criar_enquete(params, context)
        elif action == "votar_enquete":
            return await self._votar_enquete(params, context)
        elif action == "resultado_enquete":
            return await self._resultado_enquete(params, context)
        elif action == "gerar_conteudo":
            return await self._gerar_conteudo(params, context)
        elif action == "metricas":
            return await self._metricas_comunicacao(params, context)
        elif action == "chat":
            return await self._chat(params, context)
        else:
            return {"error": f"Ação '{action}' não reconhecida"}

    async def _criar_comunicado(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        tipo = TipoComunicado(params.get("tipo", "aviso"))
        canais = [CanalComunicacao(c) for c in params.get("canais", self.config["canais_padrao"])]

        comunicado = Comunicado(
            id=f"com_{datetime.now().timestamp()}",
            tipo=tipo,
            titulo=params.get("titulo", ""),
            conteudo=params.get("conteudo", ""),
            canais=canais,
            destinatarios=params.get("destinatarios", ["todos"]),
            status=StatusComunicado.RASCUNHO,
            autor=params.get("autor", "sistema"),
            anexos=params.get("anexos", [])
        )
        self._comunicados[comunicado.id] = comunicado

        return {
            "success": True,
            "comunicado_id": comunicado.id,
            "status": "rascunho"
        }

    async def _enviar_comunicado(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        comunicado_id = params.get("comunicado_id")

        if comunicado_id not in self._comunicados:
            return {"error": "Comunicado não encontrado"}

        comunicado = self._comunicados[comunicado_id]

        # Enviar por cada canal
        enviados = 0
        falhas = 0

        if self.tools:
            for canal in comunicado.canais:
                try:
                    await self.tools.execute(
                        "send_notification",
                        user_ids=comunicado.destinatarios,
                        title=comunicado.titulo,
                        message=comunicado.conteudo,
                        channels=[canal.value]
                    )
                    enviados += 1
                except Exception as e:
                    logger.error(f"Falha ao enviar por {canal}: {e}")
                    falhas += 1

        comunicado.status = StatusComunicado.ENVIADO
        comunicado.data_envio = datetime.now()
        comunicado.metricas = {
            "canais_enviados": enviados,
            "canais_falha": falhas,
            "destinatarios": len(comunicado.destinatarios)
        }

        return {
            "success": True,
            "comunicado_id": comunicado_id,
            "status": "enviado",
            "canais_enviados": enviados
        }

    async def _agendar_comunicado(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        comunicado_id = params.get("comunicado_id")
        data_hora = params.get("data_hora")

        if comunicado_id not in self._comunicados:
            return {"error": "Comunicado não encontrado"}

        comunicado = self._comunicados[comunicado_id]
        comunicado.status = StatusComunicado.AGENDADO
        comunicado.data_agendamento = datetime.fromisoformat(data_hora)

        return {
            "success": True,
            "comunicado_id": comunicado_id,
            "status": "agendado",
            "data_agendamento": data_hora
        }

    async def _listar_comunicados(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        tipo_filtro = params.get("tipo")
        status_filtro = params.get("status")
        limite = params.get("limite", 50)

        comunicados = list(self._comunicados.values())

        if tipo_filtro:
            comunicados = [c for c in comunicados if c.tipo.value == tipo_filtro]
        if status_filtro:
            comunicados = [c for c in comunicados if c.status.value == status_filtro]

        comunicados = sorted(comunicados, key=lambda c: c.data_criacao, reverse=True)[:limite]

        return {
            "success": True,
            "comunicados": [
                {
                    "id": c.id,
                    "tipo": c.tipo.value,
                    "titulo": c.titulo,
                    "status": c.status.value,
                    "data_criacao": c.data_criacao.isoformat(),
                    "data_envio": c.data_envio.isoformat() if c.data_envio else None
                }
                for c in comunicados
            ]
        }

    async def _criar_enquete(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        enquete = Enquete(
            id=f"enquete_{datetime.now().timestamp()}",
            titulo=params.get("titulo", ""),
            pergunta=params.get("pergunta", ""),
            opcoes=params.get("opcoes", []),
            data_inicio=datetime.now(),
            data_fim=datetime.fromisoformat(params.get("data_fim")) if params.get("data_fim") else datetime.now() + timedelta(days=7)
        )
        self._enquetes[enquete.id] = enquete

        # Notificar moradores
        if self.tools:
            await self.tools.execute(
                "send_notification",
                user_ids=["todos_moradores"],
                title=f"Nova Enquete: {enquete.titulo}",
                message=enquete.pergunta,
                channels=self.config["canais_padrao"]
            )

        return {
            "success": True,
            "enquete_id": enquete.id,
            "data_fim": enquete.data_fim.isoformat()
        }

    async def _votar_enquete(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        enquete_id = params.get("enquete_id")
        morador_id = params.get("morador_id")
        opcao = params.get("opcao")

        if enquete_id not in self._enquetes:
            return {"error": "Enquete não encontrada"}

        enquete = self._enquetes[enquete_id]

        if not enquete.ativa or datetime.now() > enquete.data_fim:
            return {"error": "Enquete encerrada"}

        if opcao not in enquete.opcoes:
            return {"error": "Opção inválida"}

        enquete.votos[morador_id] = opcao

        return {
            "success": True,
            "enquete_id": enquete_id,
            "voto_registrado": opcao
        }

    async def _resultado_enquete(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        enquete_id = params.get("enquete_id")

        if enquete_id not in self._enquetes:
            return {"error": "Enquete não encontrada"}

        enquete = self._enquetes[enquete_id]

        # Contabilizar votos
        contagem = {opcao: 0 for opcao in enquete.opcoes}
        for voto in enquete.votos.values():
            if voto in contagem:
                contagem[voto] += 1

        total_votos = len(enquete.votos)

        return {
            "success": True,
            "enquete_id": enquete_id,
            "titulo": enquete.titulo,
            "total_votos": total_votos,
            "resultados": contagem,
            "percentuais": {k: (v/total_votos*100 if total_votos > 0 else 0) for k, v in contagem.items()},
            "encerrada": not enquete.ativa or datetime.now() > enquete.data_fim
        }

    async def _gerar_conteudo(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        if not self.has_capability("geracao_conteudo"):
            return {"error": "Capacidade autônoma não disponível"}

        tipo = params.get("tipo", "aviso")
        tema = params.get("tema", "")
        tom = params.get("tom", "formal")

        if self.llm:
            prompt = f"""Gere um comunicado para o condomínio:
Tipo: {tipo}
Tema: {tema}
Tom: {tom}

O comunicado deve:
1. Ter título chamativo
2. Ser claro e objetivo
3. Incluir informações relevantes
4. Ter chamada para ação se aplicável
"""
            response = await self.llm.generate(self.get_system_prompt(), prompt)
            return {"success": True, "conteudo_gerado": response}

        return {"error": "LLM não configurado"}

    async def _metricas_comunicacao(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        if not self.has_capability("comunicacao_cognitiva"):
            return {"error": "Capacidade transcendente não disponível"}

        periodo = params.get("periodo", "mes")

        # Coletar métricas
        comunicados = list(self._comunicados.values())
        enviados = [c for c in comunicados if c.status == StatusComunicado.ENVIADO]

        total_enviados = len(enviados)
        por_tipo = {}
        for c in enviados:
            por_tipo[c.tipo.value] = por_tipo.get(c.tipo.value, 0) + 1

        if self.llm:
            prompt = f"""Analise as métricas de comunicação:
Total enviados: {total_enviados}
Por tipo: {por_tipo}
Período: {periodo}

Gere análise TRANSCENDENTE com:
1. Engajamento por canal
2. Melhores horários de envio
3. Tipos mais efetivos
4. Recomendações de melhoria
5. Previsão de engajamento
"""
            response = await self.llm.generate(self.get_system_prompt(), prompt)
            return {"success": True, "metricas": response}

        return {
            "success": True,
            "total_enviados": total_enviados,
            "por_tipo": por_tipo
        }

    async def _chat(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        if self.llm:
            response = await self.llm.generate(
                self.get_system_prompt(), params.get("message", "")
            )
            return {"success": True, "response": response}
        return {"error": "LLM não configurado"}


def create_communication_agent(
    condominio_id: str,
    llm_client: UnifiedLLMClient = None,
    memory: UnifiedMemorySystem = None,
    tools: ToolRegistry = None,
    evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT
) -> AgenteComunicacao:
    return AgenteComunicacao(
        condominio_id=condominio_id,
        llm_client=llm_client or UnifiedLLMClient(),
        memory=memory, tools=tools,
        evolution_level=evolution_level
    )
