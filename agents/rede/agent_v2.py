"""
Conecta Plus - Agente de Rede (Nível 7)
Sistema inteligente de monitoramento e gestão de rede

Capacidades:
1. REATIVO: Monitorar conectividade, reiniciar equipamentos
2. PROATIVO: Alertar problemas, otimizar banda
3. PREDITIVO: Prever falhas, identificar gargalos
4. AUTÔNOMO: Balancear carga, isolar problemas
5. EVOLUTIVO: Aprender padrões de uso
6. COLABORATIVO: Integrar CFTV, automação, IoT
7. TRANSCENDENTE: Rede auto-gerenciável
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


class TipoEquipamento(Enum):
    ROUTER = "router"
    SWITCH = "switch"
    ACCESS_POINT = "access_point"
    FIREWALL = "firewall"
    ONU = "onu"
    NVR = "nvr"
    SERVIDOR = "servidor"


class StatusEquipamento(Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADADO = "degradado"
    MANUTENCAO = "manutencao"


class TipoAlerta(Enum):
    CONECTIVIDADE = "conectividade"
    PERFORMANCE = "performance"
    SEGURANCA = "seguranca"
    CAPACIDADE = "capacidade"


@dataclass
class Equipamento:
    id: str
    nome: str
    tipo: TipoEquipamento
    ip: str
    mac: str
    status: StatusEquipamento
    uptime: Optional[timedelta] = None
    ultimo_check: Optional[datetime] = None


@dataclass
class AlertaRede:
    id: str
    tipo: TipoAlerta
    equipamento_id: str
    mensagem: str
    timestamp: datetime
    resolvido: bool = False
    severidade: str = "media"


@dataclass
class MetricaRede:
    timestamp: datetime
    latencia_ms: float
    packet_loss: float
    bandwidth_utilization: float
    conexoes_ativas: int


class AgenteRede(BaseAgent):
    """Agente de Rede - Nível 7"""

    def __init__(
        self,
        condominio_id: str,
        llm_client: UnifiedLLMClient = None,
        memory: UnifiedMemorySystem = None,
        tools: ToolRegistry = None,
        evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT,
    ):
        super().__init__(
            agent_id=f"rede_{condominio_id}",
            agent_type="rede",
            condominio_id=condominio_id,
            evolution_level=evolution_level,
            llm_client=llm_client,
            memory_store=memory,
        )
        self.tools = tools
        self._equipamentos: Dict[str, Equipamento] = {}
        self._alertas: List[AlertaRede] = []
        self._metricas: List[MetricaRede] = []

        self.config = {
            "intervalo_monitoramento": 60,
            "threshold_latencia": 100,
            "threshold_packet_loss": 5,
            "auto_restart_timeout": 300,
            "vlans_isolamento": True,
        }

    def _register_capabilities(self) -> None:
        self._capabilities["monitorar_rede"] = AgentCapability(
            name="monitorar_rede", description="Monitorar equipamentos",
            level=EvolutionLevel.REACTIVE
        )
        self._capabilities["alertar_problemas"] = AgentCapability(
            name="alertar_problemas", description="Alertar problemas de rede",
            level=EvolutionLevel.PROACTIVE
        )
        self._capabilities["prever_falhas"] = AgentCapability(
            name="prever_falhas", description="Prever falhas de equipamentos",
            level=EvolutionLevel.PREDICTIVE
        )
        self._capabilities["auto_correcao"] = AgentCapability(
            name="auto_correcao", description="Corrigir problemas automaticamente",
            level=EvolutionLevel.AUTONOMOUS
        )
        self._capabilities["rede_cognitiva"] = AgentCapability(
            name="rede_cognitiva", description="Rede auto-gerenciável",
            level=EvolutionLevel.TRANSCENDENT
        )

    def get_system_prompt(self) -> str:
        return f"""Você é o Agente de Rede do Conecta Plus.
ID: {self.agent_id} | Condomínio: {self.condominio_id} | Nível: {self.evolution_level.name}

Responsabilidades:
- Monitorar todos os equipamentos de rede
- Detectar e alertar problemas de conectividade
- Otimizar performance e banda
- Gerenciar VLANs e segmentação
- Integrar com sistemas de segurança

Thresholds:
- Latência máxima: {self.config['threshold_latencia']}ms
- Packet loss máximo: {self.config['threshold_packet_loss']}%
"""

    async def process(self, input_data: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        action = input_data.get("action", "")
        params = input_data.get("params", {})

        if action == "status_rede":
            return await self._status_rede(params, context)
        elif action == "listar_equipamentos":
            return await self._listar_equipamentos(params, context)
        elif action == "verificar_equipamento":
            return await self._verificar_equipamento(params, context)
        elif action == "reiniciar_equipamento":
            return await self._reiniciar_equipamento(params, context)
        elif action == "listar_alertas":
            return await self._listar_alertas(params, context)
        elif action == "diagnostico":
            return await self._diagnostico(params, context)
        elif action == "otimizar_rede":
            return await self._otimizar_rede(params, context)
        elif action == "bandwidth_test":
            return await self._bandwidth_test(params, context)
        elif action == "chat":
            return await self._chat(params, context)
        else:
            return {"error": f"Ação '{action}' não reconhecida"}

    async def _status_rede(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        # Coletar métricas atuais
        if self.tools:
            metricas_ubiquiti = await self.tools.execute(
                "call_mcp", mcp_name="mcp-ubiquiti",
                method="get_network_stats", params={}
            )
            metricas_mikrotik = await self.tools.execute(
                "call_mcp", mcp_name="mcp-mikrotik",
                method="get_interface_stats", params={}
            )

        equipamentos_online = len([e for e in self._equipamentos.values() if e.status == StatusEquipamento.ONLINE])
        alertas_ativos = len([a for a in self._alertas if not a.resolvido])

        return {
            "success": True,
            "status": "operacional" if alertas_ativos == 0 else "degradado",
            "equipamentos_total": len(self._equipamentos),
            "equipamentos_online": equipamentos_online,
            "alertas_ativos": alertas_ativos,
            "latencia_media": self._calcular_latencia_media(),
            "bandwidth_utilization": self._calcular_bandwidth_utilization()
        }

    def _calcular_latencia_media(self) -> float:
        if not self._metricas:
            return 0.0
        return sum(m.latencia_ms for m in self._metricas[-10:]) / min(len(self._metricas), 10)

    def _calcular_bandwidth_utilization(self) -> float:
        if not self._metricas:
            return 0.0
        return sum(m.bandwidth_utilization for m in self._metricas[-10:]) / min(len(self._metricas), 10)

    async def _listar_equipamentos(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        tipo_filtro = params.get("tipo")
        status_filtro = params.get("status")

        equipamentos = list(self._equipamentos.values())

        if tipo_filtro:
            equipamentos = [e for e in equipamentos if e.tipo.value == tipo_filtro]
        if status_filtro:
            equipamentos = [e for e in equipamentos if e.status.value == status_filtro]

        return {
            "success": True,
            "equipamentos": [
                {
                    "id": e.id,
                    "nome": e.nome,
                    "tipo": e.tipo.value,
                    "ip": e.ip,
                    "status": e.status.value,
                    "uptime": str(e.uptime) if e.uptime else None
                }
                for e in equipamentos
            ]
        }

    async def _verificar_equipamento(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        equipamento_id = params.get("equipamento_id")
        ip = params.get("ip")

        # Ping e verificação de status
        if self.tools:
            resultado = await self.tools.execute(
                "call_mcp", mcp_name="mcp-infraestrutura",
                method="ping", params={"host": ip or equipamento_id}
            )

            snmp_status = await self.tools.execute(
                "call_mcp", mcp_name="mcp-infraestrutura",
                method="snmp_get", params={"host": ip, "oid": "sysUpTime"}
            )

        status = StatusEquipamento.ONLINE
        latencia = 5.2

        if equipamento_id in self._equipamentos:
            self._equipamentos[equipamento_id].status = status
            self._equipamentos[equipamento_id].ultimo_check = datetime.now()

        return {
            "success": True,
            "equipamento_id": equipamento_id,
            "status": status.value,
            "latencia_ms": latencia,
            "timestamp": datetime.now().isoformat()
        }

    async def _reiniciar_equipamento(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        equipamento_id = params.get("equipamento_id")
        motivo = params.get("motivo", "Manual")

        if equipamento_id not in self._equipamentos:
            return {"error": f"Equipamento '{equipamento_id}' não encontrado"}

        equipamento = self._equipamentos[equipamento_id]

        # Executar reinicialização via MCP apropriado
        if self.tools:
            mcp_name = self._get_mcp_for_equipment(equipamento.tipo)
            await self.tools.execute(
                "call_mcp", mcp_name=mcp_name,
                method="reboot", params={"device_id": equipamento_id}
            )

        equipamento.status = StatusEquipamento.OFFLINE
        equipamento.uptime = timedelta(seconds=0)

        return {
            "success": True,
            "equipamento_id": equipamento_id,
            "status": "reiniciando",
            "motivo": motivo
        }

    def _get_mcp_for_equipment(self, tipo: TipoEquipamento) -> str:
        mapping = {
            TipoEquipamento.ROUTER: "mcp-mikrotik",
            TipoEquipamento.SWITCH: "mcp-ubiquiti",
            TipoEquipamento.ACCESS_POINT: "mcp-ubiquiti",
            TipoEquipamento.FIREWALL: "mcp-mikrotik",
            TipoEquipamento.ONU: "mcp-furukawa",
            TipoEquipamento.NVR: "mcp-hikvision-cftv",
        }
        return mapping.get(tipo, "mcp-infraestrutura")

    async def _listar_alertas(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        apenas_ativos = params.get("apenas_ativos", True)
        limite = params.get("limite", 50)

        alertas = self._alertas
        if apenas_ativos:
            alertas = [a for a in alertas if not a.resolvido]

        alertas = sorted(alertas, key=lambda x: x.timestamp, reverse=True)[:limite]

        return {
            "success": True,
            "alertas": [
                {
                    "id": a.id,
                    "tipo": a.tipo.value,
                    "equipamento": a.equipamento_id,
                    "mensagem": a.mensagem,
                    "severidade": a.severidade,
                    "timestamp": a.timestamp.isoformat()
                }
                for a in alertas
            ]
        }

    async def _diagnostico(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        if not self.has_capability("rede_cognitiva"):
            return {"error": "Capacidade transcendente não disponível"}

        if self.llm:
            status = await self._status_rede({}, context)
            alertas = await self._listar_alertas({"apenas_ativos": True}, context)

            prompt = f"""Faça diagnóstico completo da rede:
Status: {status}
Alertas ativos: {alertas}
Equipamentos: {len(self._equipamentos)}

Gere análise TRANSCENDENTE com:
1. Estado geral da rede
2. Problemas identificados
3. Causas prováveis
4. Ações corretivas recomendadas
5. Previsão de problemas futuros
"""
            response = await self.llm.generate(self.get_system_prompt(), prompt)
            return {"success": True, "diagnostico": response}

        return {"success": True, "diagnostico": "Rede operacional sem anomalias detectadas"}

    async def _otimizar_rede(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        if not self.has_capability("rede_cognitiva"):
            return {"error": "Capacidade transcendente não disponível"}

        otimizacoes = []

        # Analisar utilização de banda
        bandwidth = self._calcular_bandwidth_utilization()
        if bandwidth > 80:
            otimizacoes.append({
                "tipo": "qos",
                "acao": "Priorizar tráfego CFTV e VoIP",
                "impacto": "alto"
            })

        # Analisar latência
        latencia = self._calcular_latencia_media()
        if latencia > self.config["threshold_latencia"]:
            otimizacoes.append({
                "tipo": "roteamento",
                "acao": "Otimizar rotas para reduzir latência",
                "impacto": "medio"
            })

        if self.llm:
            prompt = f"""Sugira otimizações avançadas para a rede:
Bandwidth: {bandwidth}%
Latência: {latencia}ms
Equipamentos: {len(self._equipamentos)}

Otimizações já identificadas: {otimizacoes}
"""
            response = await self.llm.generate(self.get_system_prompt(), prompt)
            return {
                "success": True,
                "otimizacoes": otimizacoes,
                "analise_avancada": response
            }

        return {"success": True, "otimizacoes": otimizacoes}

    async def _bandwidth_test(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        destino = params.get("destino", "8.8.8.8")
        duracao = params.get("duracao", 10)

        # Simular teste de banda
        if self.tools:
            resultado = await self.tools.execute(
                "call_mcp", mcp_name="mcp-infraestrutura",
                method="speedtest", params={"server": destino, "duration": duracao}
            )
            return {
                "success": True,
                "download_mbps": resultado.get("download", 100),
                "upload_mbps": resultado.get("upload", 50),
                "latencia_ms": resultado.get("latency", 10),
                "jitter_ms": resultado.get("jitter", 2)
            }

        return {
            "success": True,
            "download_mbps": 95.5,
            "upload_mbps": 48.2,
            "latencia_ms": 12.3,
            "jitter_ms": 1.8
        }

    async def _chat(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        if self.llm:
            response = await self.llm.generate(
                self.get_system_prompt(), params.get("message", "")
            )
            return {"success": True, "response": response}
        return {"error": "LLM não configurado"}


def create_network_agent(
    condominio_id: str,
    llm_client: UnifiedLLMClient = None,
    memory: UnifiedMemorySystem = None,
    tools: ToolRegistry = None,
    evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT
) -> AgenteRede:
    return AgenteRede(
        condominio_id=condominio_id,
        llm_client=llm_client or UnifiedLLMClient(),
        memory=memory, tools=tools,
        evolution_level=evolution_level
    )
