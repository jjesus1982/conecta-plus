"""
Conecta Plus - Agente de Automação (Nível 7)
Sistema inteligente de automação predial

Capacidades:
1. REATIVO: Controlar iluminação, portões
2. PROATIVO: Programar cenários, rotinas
3. PREDITIVO: Prever consumo, otimizar energia
4. AUTÔNOMO: Ajustar automaticamente conforme contexto
5. EVOLUTIVO: Aprender preferências dos moradores
6. COLABORATIVO: Integrar sensores, CFTV, alarme
7. TRANSCENDENTE: Automação cognitiva total
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


class TipoDispositivo(Enum):
    ILUMINACAO = "iluminacao"
    PORTAO = "portao"
    IRRIGACAO = "irrigacao"
    AR_CONDICIONADO = "ar_condicionado"
    ELEVADOR = "elevador"
    BOMBA = "bomba"
    GERADOR = "gerador"
    SENSOR = "sensor"


class StatusDispositivo(Enum):
    LIGADO = "ligado"
    DESLIGADO = "desligado"
    AUTOMATICO = "automatico"
    ERRO = "erro"
    MANUTENCAO = "manutencao"


class TipoCenario(Enum):
    NOTURNO = "noturno"
    DIURNO = "diurno"
    EVENTO = "evento"
    EMERGENCIA = "emergencia"
    ECONOMIA = "economia"


@dataclass
class Dispositivo:
    id: str
    nome: str
    tipo: TipoDispositivo
    local: str
    status: StatusDispositivo
    valor_atual: Any = None
    ultimo_comando: Optional[datetime] = None


@dataclass
class Cenario:
    id: str
    nome: str
    tipo: TipoCenario
    dispositivos: List[Dict]
    ativo: bool = False
    horario_inicio: Optional[str] = None
    horario_fim: Optional[str] = None


@dataclass
class Rotina:
    id: str
    nome: str
    trigger: str
    acoes: List[Dict]
    ativa: bool = True
    ultima_execucao: Optional[datetime] = None


class AgenteAutomacao(BaseAgent):
    """Agente de Automação - Nível 7"""

    def __init__(
        self,
        condominio_id: str,
        llm_client: UnifiedLLMClient = None,
        memory: UnifiedMemorySystem = None,
        tools: ToolRegistry = None,
        evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT,
    ):
        super().__init__(
            agent_id=f"automacao_{condominio_id}",
            agent_type="automacao",
            condominio_id=condominio_id,
            evolution_level=evolution_level,
            llm_client=llm_client,
            memory_store=memory,
        )
        self.tools = tools
        self._dispositivos: Dict[str, Dispositivo] = {}
        self._cenarios: Dict[str, Cenario] = {}
        self._rotinas: Dict[str, Rotina] = {}
        self._consumo_energia: List[Dict] = []

        self.config = {
            "modo_economia": False,
            "iluminacao_automatica": True,
            "sensor_presenca_areas_comuns": True,
            "horario_pico_inicio": "18:00",
            "horario_pico_fim": "21:00",
        }

    def _register_capabilities(self) -> None:
        self._capabilities["controlar_dispositivo"] = AgentCapability(
            name="controlar_dispositivo", description="Controlar dispositivos",
            level=EvolutionLevel.REACTIVE
        )
        self._capabilities["programar_cenario"] = AgentCapability(
            name="programar_cenario", description="Programar cenários",
            level=EvolutionLevel.PROACTIVE
        )
        self._capabilities["prever_consumo"] = AgentCapability(
            name="prever_consumo", description="Prever consumo de energia",
            level=EvolutionLevel.PREDICTIVE
        )
        self._capabilities["ajuste_autonomo"] = AgentCapability(
            name="ajuste_autonomo", description="Ajustar automaticamente",
            level=EvolutionLevel.AUTONOMOUS
        )
        self._capabilities["automacao_cognitiva"] = AgentCapability(
            name="automacao_cognitiva", description="Automação cognitiva total",
            level=EvolutionLevel.TRANSCENDENT
        )

    def get_system_prompt(self) -> str:
        return f"""Você é o Agente de Automação do Conecta Plus.
ID: {self.agent_id} | Condomínio: {self.condominio_id} | Nível: {self.evolution_level.name}

Responsabilidades:
- Controlar iluminação, portões, bombas, geradores
- Gerenciar cenários e rotinas automatizadas
- Otimizar consumo de energia
- Integrar com sensores e sistemas
- Responder a eventos do condomínio

Configurações:
- Modo economia: {self.config['modo_economia']}
- Iluminação automática: {self.config['iluminacao_automatica']}
"""

    async def process(self, input_data: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        action = input_data.get("action", "")
        params = input_data.get("params", {})

        if action == "controlar":
            return await self._controlar_dispositivo(params, context)
        elif action == "listar_dispositivos":
            return await self._listar_dispositivos(params, context)
        elif action == "ativar_cenario":
            return await self._ativar_cenario(params, context)
        elif action == "criar_cenario":
            return await self._criar_cenario(params, context)
        elif action == "criar_rotina":
            return await self._criar_rotina(params, context)
        elif action == "consumo_energia":
            return await self._get_consumo_energia(params, context)
        elif action == "otimizar_energia":
            return await self._otimizar_energia(params, context)
        elif action == "status_geral":
            return await self._status_geral(params, context)
        elif action == "chat":
            return await self._chat(params, context)
        else:
            return {"error": f"Ação '{action}' não reconhecida"}

    async def _controlar_dispositivo(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        dispositivo_id = params.get("dispositivo_id")
        comando = params.get("comando")
        valor = params.get("valor")

        if dispositivo_id not in self._dispositivos:
            # Criar dispositivo se não existir
            self._dispositivos[dispositivo_id] = Dispositivo(
                id=dispositivo_id,
                nome=params.get("nome", dispositivo_id),
                tipo=TipoDispositivo(params.get("tipo", "iluminacao")),
                local=params.get("local", ""),
                status=StatusDispositivo.DESLIGADO
            )

        dispositivo = self._dispositivos[dispositivo_id]

        # Executar comando via MCP
        if self.tools:
            mcp_name = self._get_mcp_for_device(dispositivo.tipo)
            await self.tools.execute(
                "call_mcp", mcp_name=mcp_name,
                method=comando, params={"dispositivo": dispositivo_id, "valor": valor}
            )

        # Atualizar status
        if comando == "ligar":
            dispositivo.status = StatusDispositivo.LIGADO
        elif comando == "desligar":
            dispositivo.status = StatusDispositivo.DESLIGADO
        elif comando == "automatico":
            dispositivo.status = StatusDispositivo.AUTOMATICO

        dispositivo.valor_atual = valor
        dispositivo.ultimo_comando = datetime.now()

        return {
            "success": True,
            "dispositivo_id": dispositivo_id,
            "status": dispositivo.status.value,
            "valor": valor
        }

    def _get_mcp_for_device(self, tipo: TipoDispositivo) -> str:
        mapping = {
            TipoDispositivo.ILUMINACAO: "mcp-automacao",
            TipoDispositivo.PORTAO: "mcp-ppa",
            TipoDispositivo.AR_CONDICIONADO: "mcp-automacao",
            TipoDispositivo.IRRIGACAO: "mcp-automacao",
            TipoDispositivo.BOMBA: "mcp-automacao",
            TipoDispositivo.GERADOR: "mcp-automacao",
        }
        return mapping.get(tipo, "mcp-automacao")

    async def _listar_dispositivos(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        tipo_filtro = params.get("tipo")
        local_filtro = params.get("local")

        dispositivos = list(self._dispositivos.values())

        if tipo_filtro:
            dispositivos = [d for d in dispositivos if d.tipo.value == tipo_filtro]
        if local_filtro:
            dispositivos = [d for d in dispositivos if local_filtro in d.local]

        return {
            "success": True,
            "dispositivos": [
                {
                    "id": d.id,
                    "nome": d.nome,
                    "tipo": d.tipo.value,
                    "local": d.local,
                    "status": d.status.value,
                    "valor": d.valor_atual
                }
                for d in dispositivos
            ]
        }

    async def _ativar_cenario(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        cenario_id = params.get("cenario_id")

        if cenario_id not in self._cenarios:
            return {"error": f"Cenário '{cenario_id}' não encontrado"}

        cenario = self._cenarios[cenario_id]

        # Desativar outros cenários do mesmo tipo
        for c in self._cenarios.values():
            if c.tipo == cenario.tipo:
                c.ativo = False

        cenario.ativo = True

        # Aplicar configurações dos dispositivos
        for config in cenario.dispositivos:
            await self._controlar_dispositivo(config, context)

        return {
            "success": True,
            "cenario_id": cenario_id,
            "nome": cenario.nome,
            "dispositivos_configurados": len(cenario.dispositivos)
        }

    async def _criar_cenario(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        nome = params.get("nome")
        tipo = TipoCenario(params.get("tipo", "diurno"))
        dispositivos = params.get("dispositivos", [])

        cenario = Cenario(
            id=f"cenario_{datetime.now().timestamp()}",
            nome=nome,
            tipo=tipo,
            dispositivos=dispositivos,
            horario_inicio=params.get("horario_inicio"),
            horario_fim=params.get("horario_fim")
        )
        self._cenarios[cenario.id] = cenario

        return {
            "success": True,
            "cenario_id": cenario.id,
            "nome": nome
        }

    async def _criar_rotina(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        nome = params.get("nome")
        trigger = params.get("trigger")
        acoes = params.get("acoes", [])

        rotina = Rotina(
            id=f"rotina_{datetime.now().timestamp()}",
            nome=nome,
            trigger=trigger,
            acoes=acoes
        )
        self._rotinas[rotina.id] = rotina

        return {
            "success": True,
            "rotina_id": rotina.id,
            "nome": nome
        }

    async def _get_consumo_energia(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        periodo = params.get("periodo", "dia")

        # Simular leitura de medidores
        if self.tools:
            resultado = await self.tools.execute(
                "call_mcp", mcp_name="mcp-medidores",
                method="leitura_consumo", params={"periodo": periodo}
            )
            return {
                "success": True,
                "consumo": resultado.get("consumo", 0),
                "periodo": periodo,
                "unidade": "kWh"
            }

        return {
            "success": True,
            "consumo": 1250.5,
            "periodo": periodo,
            "unidade": "kWh",
            "custo_estimado": 875.35
        }

    async def _otimizar_energia(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        if not self.has_capability("automacao_cognitiva"):
            return {"error": "Capacidade transcendente não disponível"}

        if self.llm:
            consumo = await self._get_consumo_energia({"periodo": "mes"}, context)
            dispositivos = await self._listar_dispositivos({}, context)

            prompt = f"""Analise e otimize o consumo de energia:
Consumo atual: {consumo}
Dispositivos: {len(dispositivos.get('dispositivos', []))}
Modo economia: {self.config['modo_economia']}

Gere análise TRANSCENDENTE com:
1. Dispositivos com maior consumo
2. Oportunidades de economia
3. Cenários otimizados sugeridos
4. Previsão de redução de custo
"""
            response = await self.llm.generate(self.get_system_prompt(), prompt)
            return {"success": True, "otimizacao": response}

        # Otimização básica
        acoes = []
        if self.config["modo_economia"]:
            acoes.append("Reduzir iluminação áreas comuns em 30%")
            acoes.append("Desligar ar-condicionado fora do horário comercial")

        return {
            "success": True,
            "acoes_sugeridas": acoes,
            "economia_estimada": "15%"
        }

    async def _status_geral(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        return {
            "success": True,
            "total_dispositivos": len(self._dispositivos),
            "dispositivos_ligados": len([d for d in self._dispositivos.values() if d.status == StatusDispositivo.LIGADO]),
            "cenarios_ativos": len([c for c in self._cenarios.values() if c.ativo]),
            "rotinas_ativas": len([r for r in self._rotinas.values() if r.ativa]),
            "modo_economia": self.config["modo_economia"]
        }

    async def _chat(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        if self.llm:
            response = await self.llm.generate(
                self.get_system_prompt(), params.get("message", "")
            )
            return {"success": True, "response": response}
        return {"error": "LLM não configurado"}


def create_automation_agent(
    condominio_id: str,
    llm_client: UnifiedLLMClient = None,
    memory: UnifiedMemorySystem = None,
    tools: ToolRegistry = None,
    evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT
) -> AgenteAutomacao:
    return AgenteAutomacao(
        condominio_id=condominio_id,
        llm_client=llm_client or UnifiedLLMClient(),
        memory=memory, tools=tools,
        evolution_level=evolution_level
    )
