"""
Conecta Plus - Agente do Morador (Nível 7)
Assistente pessoal inteligente do morador

Capacidades:
1. REATIVO: Responder consultas, informar status
2. PROATIVO: Alertar vencimentos, sugerir serviços
3. PREDITIVO: Prever necessidades, personalizar
4. AUTÔNOMO: Agendar automaticamente, solicitar serviços
5. EVOLUTIVO: Aprender preferências individuais
6. COLABORATIVO: Integrar todos os serviços
7. TRANSCENDENTE: Concierge cognitivo pessoal
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


class TipoMorador(Enum):
    PROPRIETARIO = "proprietario"
    INQUILINO = "inquilino"
    DEPENDENTE = "dependente"


class StatusCadastro(Enum):
    ATIVO = "ativo"
    INATIVO = "inativo"
    PENDENTE = "pendente"


@dataclass
class Morador:
    id: str
    nome: str
    unidade: str
    tipo: TipoMorador
    status: StatusCadastro
    email: str
    telefone: str
    cpf: str
    data_nascimento: Optional[date] = None
    foto_url: Optional[str] = None
    veiculos: List[str] = field(default_factory=list)
    pets: List[Dict] = field(default_factory=list)
    biometria_cadastrada: bool = False
    facial_cadastrado: bool = False


@dataclass
class Preferencia:
    morador_id: str
    categoria: str
    valor: Any
    atualizado_em: datetime = field(default_factory=datetime.now)


class AgenteMorador(BaseAgent):
    """Agente do Morador - Nível 7"""

    def __init__(
        self,
        condominio_id: str,
        morador_id: str = None,
        llm_client: UnifiedLLMClient = None,
        memory: UnifiedMemorySystem = None,
        tools: ToolRegistry = None,
        evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT,
    ):
        super().__init__(
            agent_id=f"morador_{morador_id or condominio_id}",
            agent_type="morador",
            condominio_id=condominio_id,
            evolution_level=evolution_level,
            llm_client=llm_client,
            memory_store=memory,
        )
        self.morador_id = morador_id
        self.tools = tools
        self._moradores: Dict[str, Morador] = {}
        self._preferencias: Dict[str, List[Preferencia]] = {}
        self._historico_interacoes: List[Dict] = []

        self.config = {
            "notificacoes_ativas": True,
            "modo_privacidade": False,
            "idioma": "pt-BR",
        }

    def _register_capabilities(self) -> None:
        self._capabilities["atendimento"] = AgentCapability(
            name="atendimento", description="Atender consultas do morador",
            level=EvolutionLevel.REACTIVE
        )
        self._capabilities["alertas_personalizados"] = AgentCapability(
            name="alertas_personalizados", description="Alertar sobre eventos relevantes",
            level=EvolutionLevel.PROACTIVE
        )
        self._capabilities["personalizacao"] = AgentCapability(
            name="personalizacao", description="Personalizar experiência",
            level=EvolutionLevel.PREDICTIVE
        )
        self._capabilities["servicos_autonomos"] = AgentCapability(
            name="servicos_autonomos", description="Solicitar serviços automaticamente",
            level=EvolutionLevel.AUTONOMOUS
        )
        self._capabilities["concierge_cognitivo"] = AgentCapability(
            name="concierge_cognitivo", description="Concierge pessoal cognitivo",
            level=EvolutionLevel.TRANSCENDENT
        )

    def get_system_prompt(self) -> str:
        morador = self._moradores.get(self.morador_id)
        nome = morador.nome if morador else "Morador"
        unidade = morador.unidade if morador else "N/A"

        return f"""Você é o Assistente Pessoal do morador no Conecta Plus.
ID: {self.agent_id} | Condomínio: {self.condominio_id} | Nível: {self.evolution_level.name}

Morador: {nome}
Unidade: {unidade}

Responsabilidades:
- Atender solicitações do morador
- Informar sobre status de serviços
- Facilitar reservas e agendamentos
- Notificar sobre eventos importantes
- Personalizar experiência baseado em preferências

Comportamento:
- Seja cordial e prestativo
- Antecipe necessidades
- Respeite preferências de privacidade
- Comunique proativamente
"""

    async def process(self, input_data: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        action = input_data.get("action", "")
        params = input_data.get("params", {})

        if action == "consultar_saldo":
            return await self._consultar_saldo(params, context)
        elif action == "segunda_via":
            return await self._segunda_via_boleto(params, context)
        elif action == "minhas_reservas":
            return await self._minhas_reservas(params, context)
        elif action == "fazer_reserva":
            return await self._fazer_reserva(params, context)
        elif action == "minhas_encomendas":
            return await self._minhas_encomendas(params, context)
        elif action == "abrir_chamado":
            return await self._abrir_chamado(params, context)
        elif action == "meus_acessos":
            return await self._meus_acessos(params, context)
        elif action == "atualizar_cadastro":
            return await self._atualizar_cadastro(params, context)
        elif action == "configurar_preferencias":
            return await self._configurar_preferencias(params, context)
        elif action == "resumo_dia":
            return await self._resumo_dia(params, context)
        elif action == "chat":
            return await self._chat(params, context)
        else:
            return {"error": f"Ação '{action}' não reconhecida"}

    async def _consultar_saldo(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        morador = self._moradores.get(self.morador_id)
        if not morador:
            return {"error": "Morador não encontrado"}

        # Consultar agente financeiro
        if self.has_capability("agent_collaboration"):
            resultado = await self.send_message(
                f"financeiro_{self.condominio_id}",
                {
                    "action": "saldo_unidade",
                    "params": {"unidade": morador.unidade}
                }
            )
            return resultado

        return {
            "success": True,
            "unidade": morador.unidade,
            "saldo": 0.0,
            "parcelas_abertas": []
        }

    async def _segunda_via_boleto(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        morador = self._moradores.get(self.morador_id)
        if not morador:
            return {"error": "Morador não encontrado"}

        competencia = params.get("competencia", datetime.now().strftime("%Y-%m"))

        # Solicitar ao financeiro
        if self.has_capability("agent_collaboration"):
            resultado = await self.send_message(
                f"financeiro_{self.condominio_id}",
                {
                    "action": "segunda_via",
                    "params": {"unidade": morador.unidade, "competencia": competencia}
                }
            )
            return resultado

        return {
            "success": True,
            "message": "Segunda via solicitada",
            "competencia": competencia
        }

    async def _minhas_reservas(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        morador = self._moradores.get(self.morador_id)
        if not morador:
            return {"error": "Morador não encontrado"}

        # Consultar agente de reservas
        if self.has_capability("agent_collaboration"):
            resultado = await self.send_message(
                f"reservas_{self.condominio_id}",
                {
                    "action": "listar_reservas",
                    "params": {"unidade": morador.unidade}
                }
            )
            return resultado

        return {"success": True, "reservas": []}

    async def _fazer_reserva(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        morador = self._moradores.get(self.morador_id)
        if not morador:
            return {"error": "Morador não encontrado"}

        params["unidade"] = morador.unidade
        params["responsavel"] = morador.nome
        params["telefone"] = morador.telefone

        # Enviar para agente de reservas
        if self.has_capability("agent_collaboration"):
            resultado = await self.send_message(
                f"reservas_{self.condominio_id}",
                {"action": "criar_reserva", "params": params}
            )
            return resultado

        return {"error": "Serviço de reservas indisponível"}

    async def _minhas_encomendas(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        morador = self._moradores.get(self.morador_id)
        if not morador:
            return {"error": "Morador não encontrado"}

        # Consultar agente de encomendas
        if self.has_capability("agent_collaboration"):
            resultado = await self.send_message(
                f"encomendas_{self.condominio_id}",
                {
                    "action": "listar_encomendas",
                    "params": {"unidade": morador.unidade}
                }
            )
            return resultado

        return {"success": True, "encomendas": []}

    async def _abrir_chamado(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        morador = self._moradores.get(self.morador_id)
        if not morador:
            return {"error": "Morador não encontrado"}

        params["solicitante"] = morador.nome
        params["local"] = params.get("local", morador.unidade)

        # Enviar para manutenção
        if self.has_capability("agent_collaboration"):
            resultado = await self.send_message(
                f"manutencao_{self.condominio_id}",
                {"action": "abrir_chamado", "params": params}
            )
            return resultado

        return {"error": "Serviço de manutenção indisponível"}

    async def _meus_acessos(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        morador = self._moradores.get(self.morador_id)
        if not morador:
            return {"error": "Morador não encontrado"}

        periodo = params.get("periodo", 7)

        # Consultar agente de acesso
        if self.has_capability("agent_collaboration"):
            resultado = await self.send_message(
                f"acesso_{self.condominio_id}",
                {
                    "action": "historico_unidade",
                    "params": {"unidade": morador.unidade, "dias": periodo}
                }
            )
            return resultado

        return {"success": True, "acessos": []}

    async def _atualizar_cadastro(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        morador = self._moradores.get(self.morador_id)
        if not morador:
            return {"error": "Morador não encontrado"}

        # Atualizar campos permitidos
        if "email" in params:
            morador.email = params["email"]
        if "telefone" in params:
            morador.telefone = params["telefone"]
        if "veiculos" in params:
            morador.veiculos = params["veiculos"]
        if "pets" in params:
            morador.pets = params["pets"]

        return {
            "success": True,
            "message": "Cadastro atualizado",
            "morador_id": self.morador_id
        }

    async def _configurar_preferencias(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        categoria = params.get("categoria")
        valor = params.get("valor")

        if self.morador_id not in self._preferencias:
            self._preferencias[self.morador_id] = []

        preferencia = Preferencia(
            morador_id=self.morador_id,
            categoria=categoria,
            valor=valor
        )
        self._preferencias[self.morador_id].append(preferencia)

        return {
            "success": True,
            "categoria": categoria,
            "valor": valor
        }

    async def _resumo_dia(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        if not self.has_capability("concierge_cognitivo"):
            return {"error": "Capacidade transcendente não disponível"}

        morador = self._moradores.get(self.morador_id)
        if not morador:
            return {"error": "Morador não encontrado"}

        # Coletar informações de vários agentes
        informacoes = {}

        if self.has_capability("agent_collaboration"):
            # Financeiro
            saldo = await self.send_message(
                f"financeiro_{self.condominio_id}",
                {"action": "saldo_unidade", "params": {"unidade": morador.unidade}}
            )
            informacoes["financeiro"] = saldo

            # Encomendas
            encomendas = await self.send_message(
                f"encomendas_{self.condominio_id}",
                {"action": "pendentes_unidade", "params": {"unidade": morador.unidade}}
            )
            informacoes["encomendas"] = encomendas

            # Reservas
            reservas = await self.send_message(
                f"reservas_{self.condominio_id}",
                {"action": "listar_reservas", "params": {"unidade": morador.unidade, "data_inicio": date.today().isoformat()}}
            )
            informacoes["reservas"] = reservas

        if self.llm:
            prompt = f"""Gere resumo diário personalizado para {morador.nome}:
Informações: {json.dumps(informacoes)}
Data: {date.today().isoformat()}

Inclua:
1. Pendências financeiras
2. Encomendas aguardando
3. Reservas próximas
4. Avisos importantes
5. Sugestões personalizadas
"""
            response = await self.llm.generate(self.get_system_prompt(), prompt)
            return {"success": True, "resumo": response}

        return {"success": True, "informacoes": informacoes}

    async def _chat(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        message = params.get("message", "")

        # Registrar interação
        self._historico_interacoes.append({
            "timestamp": datetime.now().isoformat(),
            "message": message,
            "morador_id": self.morador_id
        })

        if self.llm:
            # Incluir contexto do morador
            morador = self._moradores.get(self.morador_id)
            contexto = f"\nMorador: {morador.nome if morador else 'N/A'}\nUnidade: {morador.unidade if morador else 'N/A'}\n"

            response = await self.llm.generate(
                self.get_system_prompt() + contexto, message
            )
            return {"success": True, "response": response}

        return {"error": "LLM não configurado"}


def create_resident_agent(
    condominio_id: str,
    morador_id: str = None,
    llm_client: UnifiedLLMClient = None,
    memory: UnifiedMemorySystem = None,
    tools: ToolRegistry = None,
    evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT
) -> AgenteMorador:
    return AgenteMorador(
        condominio_id=condominio_id,
        morador_id=morador_id,
        llm_client=llm_client or UnifiedLLMClient(),
        memory=memory, tools=tools,
        evolution_level=evolution_level
    )
