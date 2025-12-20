"""
Conecta Plus - Agente de Infraestrutura (Nível 7)
Sistema inteligente de gestão de infraestrutura de TI

Capacidades:
1. REATIVO: Monitorar serviços, reiniciar sistemas
2. PROATIVO: Alertar problemas, backup automático
3. PREDITIVO: Prever falhas, capacity planning
4. AUTÔNOMO: Auto-healing, escalamento automático
5. EVOLUTIVO: Aprender padrões de carga
6. COLABORATIVO: Integrar todos os sistemas
7. TRANSCENDENTE: Infraestrutura auto-gerenciável
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


class TipoServico(Enum):
    API = "api"
    DATABASE = "database"
    CACHE = "cache"
    QUEUE = "queue"
    STORAGE = "storage"
    WEB = "web"
    MCP = "mcp"


class StatusServico(Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADADO = "degradado"
    MANUTENCAO = "manutencao"


class TipoAlerta(Enum):
    CPU = "cpu"
    MEMORIA = "memoria"
    DISCO = "disco"
    REDE = "rede"
    SERVICO = "servico"
    SEGURANCA = "seguranca"


@dataclass
class Servico:
    id: str
    nome: str
    tipo: TipoServico
    url: str
    status: StatusServico
    cpu_percent: float = 0.0
    memoria_percent: float = 0.0
    uptime: Optional[timedelta] = None
    ultimo_check: Optional[datetime] = None


@dataclass
class AlertaInfra:
    id: str
    tipo: TipoAlerta
    servico_id: str
    mensagem: str
    severidade: str
    timestamp: datetime
    resolvido: bool = False


@dataclass
class Backup:
    id: str
    tipo: str
    tamanho_mb: float
    timestamp: datetime
    status: str
    destino: str


class AgenteInfraestrutura(BaseAgent):
    """Agente de Infraestrutura - Nível 7"""

    def __init__(
        self,
        condominio_id: str,
        llm_client: UnifiedLLMClient = None,
        memory: UnifiedMemorySystem = None,
        tools: ToolRegistry = None,
        evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT,
    ):
        super().__init__(
            agent_id=f"infraestrutura_{condominio_id}",
            agent_type="infraestrutura",
            condominio_id=condominio_id,
            evolution_level=evolution_level,
            llm_client=llm_client,
            memory_store=memory,
        )
        self.tools = tools
        self._servicos: Dict[str, Servico] = {}
        self._alertas: List[AlertaInfra] = []
        self._backups: List[Backup] = []

        self.config = {
            "threshold_cpu": 80,
            "threshold_memoria": 85,
            "threshold_disco": 90,
            "backup_automatico": True,
            "auto_healing": True,
            "intervalo_monitoramento": 60,
        }

        # Inicializar serviços padrão
        self._inicializar_servicos()

    def _inicializar_servicos(self):
        servicos_padrao = [
            ("api-gateway", TipoServico.API, "http://api-gateway:8000"),
            ("auth-service", TipoServico.API, "http://auth-service:8001"),
            ("postgres", TipoServico.DATABASE, "postgresql://postgres:5432"),
            ("redis", TipoServico.CACHE, "redis://redis:6379"),
            ("rabbitmq", TipoServico.QUEUE, "amqp://rabbitmq:5672"),
            ("minio", TipoServico.STORAGE, "http://minio:9000"),
            ("ai-orchestrator", TipoServico.API, "http://ai-orchestrator:8080"),
        ]

        for nome, tipo, url in servicos_padrao:
            self._servicos[nome] = Servico(
                id=nome,
                nome=nome,
                tipo=tipo,
                url=url,
                status=StatusServico.ONLINE
            )

    def _register_capabilities(self) -> None:
        self._capabilities["monitoramento"] = AgentCapability(
            name="monitoramento", description="Monitorar serviços",
            level=EvolutionLevel.REACTIVE
        )
        self._capabilities["alertas_proativos"] = AgentCapability(
            name="alertas_proativos", description="Alertar problemas",
            level=EvolutionLevel.PROACTIVE
        )
        self._capabilities["capacity_planning"] = AgentCapability(
            name="capacity_planning", description="Planejar capacidade",
            level=EvolutionLevel.PREDICTIVE
        )
        self._capabilities["auto_healing"] = AgentCapability(
            name="auto_healing", description="Auto-recuperação",
            level=EvolutionLevel.AUTONOMOUS
        )
        self._capabilities["infra_cognitiva"] = AgentCapability(
            name="infra_cognitiva", description="Infraestrutura auto-gerenciável",
            level=EvolutionLevel.TRANSCENDENT
        )

    def get_system_prompt(self) -> str:
        return f"""Você é o Agente de Infraestrutura do Conecta Plus.
ID: {self.agent_id} | Condomínio: {self.condominio_id} | Nível: {self.evolution_level.name}

Responsabilidades:
- Monitorar todos os serviços e sistemas
- Gerenciar backups e recuperação
- Escalar recursos automaticamente
- Detectar e corrigir problemas
- Otimizar performance

Thresholds:
- CPU: {self.config['threshold_cpu']}%
- Memória: {self.config['threshold_memoria']}%
- Disco: {self.config['threshold_disco']}%
"""

    async def process(self, input_data: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        action = input_data.get("action", "")
        params = input_data.get("params", {})

        if action == "status_geral":
            return await self._status_geral(params, context)
        elif action == "status_servico":
            return await self._status_servico(params, context)
        elif action == "reiniciar_servico":
            return await self._reiniciar_servico(params, context)
        elif action == "listar_alertas":
            return await self._listar_alertas(params, context)
        elif action == "executar_backup":
            return await self._executar_backup(params, context)
        elif action == "listar_backups":
            return await self._listar_backups(params, context)
        elif action == "health_check":
            return await self._health_check(params, context)
        elif action == "diagnostico":
            return await self._diagnostico(params, context)
        elif action == "escalar":
            return await self._escalar_servico(params, context)
        elif action == "chat":
            return await self._chat(params, context)
        else:
            return {"error": f"Ação '{action}' não reconhecida"}

    async def _status_geral(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        total_servicos = len(self._servicos)
        online = len([s for s in self._servicos.values() if s.status == StatusServico.ONLINE])
        alertas_ativos = len([a for a in self._alertas if not a.resolvido])

        # Coletar métricas
        if self.tools:
            metricas = await self.tools.execute(
                "call_mcp", mcp_name="mcp-infraestrutura",
                method="get_metrics", params={}
            )
        else:
            metricas = {"cpu": 45, "memoria": 62, "disco": 55}

        return {
            "success": True,
            "status": "operacional" if online == total_servicos else "degradado",
            "servicos": {
                "total": total_servicos,
                "online": online,
                "offline": total_servicos - online
            },
            "recursos": metricas,
            "alertas_ativos": alertas_ativos
        }

    async def _status_servico(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        servico_id = params.get("servico_id")

        if servico_id not in self._servicos:
            return {"error": "Serviço não encontrado"}

        s = self._servicos[servico_id]

        # Atualizar métricas
        if self.tools:
            metricas = await self.tools.execute(
                "call_mcp", mcp_name="mcp-infraestrutura",
                method="service_metrics", params={"service": servico_id}
            )
            s.cpu_percent = metricas.get("cpu", 0)
            s.memoria_percent = metricas.get("memoria", 0)

        s.ultimo_check = datetime.now()

        return {
            "success": True,
            "servico": {
                "id": s.id,
                "nome": s.nome,
                "tipo": s.tipo.value,
                "status": s.status.value,
                "cpu": s.cpu_percent,
                "memoria": s.memoria_percent,
                "url": s.url
            }
        }

    async def _reiniciar_servico(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        servico_id = params.get("servico_id")
        motivo = params.get("motivo", "Manual")

        if servico_id not in self._servicos:
            return {"error": "Serviço não encontrado"}

        servico = self._servicos[servico_id]

        # Executar reinício via Docker/Kubernetes
        if self.tools:
            await self.tools.execute(
                "call_mcp", mcp_name="mcp-infraestrutura",
                method="restart_service", params={"service": servico_id}
            )

        servico.status = StatusServico.ONLINE
        servico.uptime = timedelta(seconds=0)

        # Notificar
        if self.tools:
            await self.tools.execute(
                "send_notification",
                user_ids=["ti", "administracao"],
                title=f"Serviço Reiniciado: {servico_id}",
                message=f"Motivo: {motivo}",
                channels=["push"]
            )

        return {
            "success": True,
            "servico_id": servico_id,
            "status": "reiniciando"
        }

    async def _listar_alertas(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        apenas_ativos = params.get("apenas_ativos", True)
        tipo_filtro = params.get("tipo")
        limite = params.get("limite", 50)

        alertas = self._alertas

        if apenas_ativos:
            alertas = [a for a in alertas if not a.resolvido]
        if tipo_filtro:
            alertas = [a for a in alertas if a.tipo.value == tipo_filtro]

        alertas = sorted(alertas, key=lambda a: a.timestamp, reverse=True)[:limite]

        return {
            "success": True,
            "alertas": [
                {
                    "id": a.id,
                    "tipo": a.tipo.value,
                    "servico": a.servico_id,
                    "mensagem": a.mensagem,
                    "severidade": a.severidade,
                    "timestamp": a.timestamp.isoformat()
                }
                for a in alertas
            ]
        }

    async def _executar_backup(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        tipo = params.get("tipo", "completo")
        destino = params.get("destino", "s3://backups/")

        if self.tools:
            resultado = await self.tools.execute(
                "call_mcp", mcp_name="mcp-infraestrutura",
                method="backup", params={
                    "type": tipo,
                    "destination": destino,
                    "databases": ["postgres"],
                    "files": ["/data/uploads", "/data/logs"]
                }
            )

            backup = Backup(
                id=f"backup_{datetime.now().timestamp()}",
                tipo=tipo,
                tamanho_mb=resultado.get("size_mb", 0),
                timestamp=datetime.now(),
                status="concluido",
                destino=destino
            )
            self._backups.append(backup)

            return {
                "success": True,
                "backup_id": backup.id,
                "tamanho_mb": backup.tamanho_mb,
                "destino": destino
            }

        return {"error": "Serviço de backup indisponível"}

    async def _listar_backups(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        limite = params.get("limite", 20)

        backups = sorted(self._backups, key=lambda b: b.timestamp, reverse=True)[:limite]

        return {
            "success": True,
            "backups": [
                {
                    "id": b.id,
                    "tipo": b.tipo,
                    "tamanho_mb": b.tamanho_mb,
                    "status": b.status,
                    "timestamp": b.timestamp.isoformat()
                }
                for b in backups
            ]
        }

    async def _health_check(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        resultados = {}

        for servico_id, servico in self._servicos.items():
            if self.tools:
                try:
                    resultado = await self.tools.execute(
                        "call_mcp", mcp_name="mcp-infraestrutura",
                        method="health_check", params={"service": servico_id}
                    )
                    resultados[servico_id] = {
                        "status": "healthy" if resultado.get("healthy") else "unhealthy",
                        "latencia_ms": resultado.get("latency_ms", 0)
                    }
                    servico.status = StatusServico.ONLINE if resultado.get("healthy") else StatusServico.OFFLINE
                except:
                    resultados[servico_id] = {"status": "unreachable"}
                    servico.status = StatusServico.OFFLINE

                    # Auto-healing se configurado
                    if self.config["auto_healing"] and self.has_capability("auto_healing"):
                        await self._reiniciar_servico({"servico_id": servico_id, "motivo": "Auto-healing"}, context)

        return {"success": True, "health": resultados}

    async def _diagnostico(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        if not self.has_capability("infra_cognitiva"):
            return {"error": "Capacidade transcendente não disponível"}

        # Coletar informações
        status = await self._status_geral({}, context)
        alertas = await self._listar_alertas({"apenas_ativos": True}, context)
        health = await self._health_check({}, context)

        if self.llm:
            prompt = f"""Faça diagnóstico completo da infraestrutura:
Status geral: {json.dumps(status)}
Alertas ativos: {json.dumps(alertas)}
Health checks: {json.dumps(health)}

Gere análise TRANSCENDENTE:
1. Estado geral da infraestrutura
2. Problemas identificados e causas raiz
3. Riscos potenciais
4. Recomendações de otimização
5. Previsão de necessidades de capacidade
6. Plano de ação priorizado
"""
            response = await self.llm.generate(self.get_system_prompt(), prompt)
            return {"success": True, "diagnostico": response}

        return {
            "success": True,
            "status": status,
            "alertas": alertas,
            "health": health
        }

    async def _escalar_servico(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        servico_id = params.get("servico_id")
        replicas = params.get("replicas", 2)
        motivo = params.get("motivo", "Manual")

        if self.tools:
            await self.tools.execute(
                "call_mcp", mcp_name="mcp-infraestrutura",
                method="scale", params={
                    "service": servico_id,
                    "replicas": replicas
                }
            )

        return {
            "success": True,
            "servico_id": servico_id,
            "replicas": replicas,
            "motivo": motivo
        }

    async def _chat(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        if self.llm:
            response = await self.llm.generate(
                self.get_system_prompt(), params.get("message", "")
            )
            return {"success": True, "response": response}
        return {"error": "LLM não configurado"}


def create_infrastructure_agent(
    condominio_id: str,
    llm_client: UnifiedLLMClient = None,
    memory: UnifiedMemorySystem = None,
    tools: ToolRegistry = None,
    evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT
) -> AgenteInfraestrutura:
    return AgenteInfraestrutura(
        condominio_id=condominio_id,
        llm_client=llm_client or UnifiedLLMClient(),
        memory=memory, tools=tools,
        evolution_level=evolution_level
    )
