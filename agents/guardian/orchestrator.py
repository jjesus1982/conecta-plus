"""
Conecta Plus - Guardian Orchestrator
Orquestrador Central dos Agentes Guardian - Nivel 7

Responsabilidades:
- Coordenar todos os agentes Guardian
- Gerenciar ciclo de vida dos agentes
- Fornecer message bus centralizado
- Monitorar saude e performance
- API unificada para o sistema
"""

import asyncio
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Set
from enum import Enum
from collections import defaultdict
import uuid

from .monitor_agent import GuardianMonitorAgent
from .access_agent import GuardianAccessAgent
from .analytics_agent import GuardianAnalyticsAgent
from .assistant_agent import GuardianAssistantAgent
from .response_agent import GuardianResponseAgent

logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    """Status do agente."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


class MessagePriority(Enum):
    """Prioridade de mensagem."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class AgentInfo:
    """Informacoes sobre um agente."""
    id: str
    name: str
    type: str
    status: AgentStatus
    started_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    messages_processed: int = 0
    errors: int = 0
    instance: Optional[Any] = None


@dataclass
class Message:
    """Mensagem do message bus."""
    id: str
    topic: str
    payload: Dict[str, Any]
    priority: MessagePriority
    timestamp: datetime
    source: str
    correlation_id: Optional[str] = None


class MessageBus:
    """
    Message Bus para comunicacao entre agentes.
    Implementa pub/sub assincrono.
    """

    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self.message_history: List[Message] = []
        self.max_history = 1000

    async def subscribe(self, topic: str, handler: Callable) -> None:
        """Inscreve um handler para um topico."""
        self.subscribers[topic].append(handler)
        logger.debug(f"Handler inscrito no topico: {topic}")

    async def unsubscribe(self, topic: str, handler: Callable) -> None:
        """Remove inscricao de um handler."""
        if handler in self.subscribers[topic]:
            self.subscribers[topic].remove(handler)

    async def publish(
        self,
        topic: str,
        payload: Dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL,
        source: str = "unknown",
        correlation_id: Optional[str] = None
    ) -> str:
        """Publica mensagem em um topico."""
        message_id = f"msg_{uuid.uuid4().hex[:12]}"

        message = Message(
            id=message_id,
            topic=topic,
            payload=payload,
            priority=priority,
            timestamp=datetime.now(),
            source=source,
            correlation_id=correlation_id
        )

        # Armazenar no historico
        self.message_history.append(message)
        if len(self.message_history) > self.max_history:
            self.message_history = self.message_history[-self.max_history:]

        # Notificar subscribers
        handlers = self.subscribers.get(topic, [])

        # Tambem notificar wildcards
        for pattern, pattern_handlers in self.subscribers.items():
            if pattern.endswith(".*"):
                prefix = pattern[:-2]
                if topic.startswith(prefix):
                    handlers.extend(pattern_handlers)

        # Executar handlers
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    asyncio.create_task(handler(payload))
                else:
                    handler(payload)
            except Exception as e:
                logger.error(f"Erro ao executar handler para {topic}: {e}")

        return message_id

    async def request(
        self,
        topic: str,
        payload: Dict[str, Any],
        timeout: float = 5.0
    ) -> Optional[Dict[str, Any]]:
        """Faz request/response sincrono."""
        response_event = asyncio.Event()
        response_data: Dict[str, Any] = {}
        correlation_id = f"req_{uuid.uuid4().hex[:8]}"

        async def response_handler(data: Dict[str, Any]) -> None:
            if data.get("correlation_id") == correlation_id:
                response_data.update(data)
                response_event.set()

        response_topic = f"{topic}.response"
        await self.subscribe(response_topic, response_handler)

        try:
            await self.publish(topic, payload, correlation_id=correlation_id)
            await asyncio.wait_for(response_event.wait(), timeout=timeout)
            return response_data
        except asyncio.TimeoutError:
            logger.warning(f"Timeout esperando resposta para {topic}")
            return None
        finally:
            await self.unsubscribe(response_topic, response_handler)

    def get_recent_messages(
        self,
        topic: Optional[str] = None,
        limit: int = 100
    ) -> List[Message]:
        """Retorna mensagens recentes."""
        messages = self.message_history
        if topic:
            messages = [m for m in messages if m.topic == topic]
        return messages[-limit:]


class GuardianOrchestrator:
    """
    Orquestrador Central Guardian - Nivel 7 TRANSCENDENT

    Capacidades:
    - Gerenciamento de ciclo de vida dos agentes
    - Message bus para comunicacao
    - Monitoramento de saude
    - Metricas e logging centralizado
    - API unificada
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None
    ):
        self.config = config or {}
        self.orchestrator_id = f"guardian_orch_{uuid.uuid4().hex[:8]}"

        # Message Bus
        self.message_bus = MessageBus()

        # Agentes registrados
        self.agents: Dict[str, AgentInfo] = {}

        # Instancias dos agentes
        self.monitor_agent: Optional[GuardianMonitorAgent] = None
        self.access_agent: Optional[GuardianAccessAgent] = None
        self.analytics_agent: Optional[GuardianAnalyticsAgent] = None
        self.assistant_agent: Optional[GuardianAssistantAgent] = None
        self.response_agent: Optional[GuardianResponseAgent] = None

        # Estado
        self.is_running = False
        self.started_at: Optional[datetime] = None
        self._health_check_task: Optional[asyncio.Task] = None

        # Metricas
        self.metrics: Dict[str, Any] = {
            "total_messages": 0,
            "total_alerts": 0,
            "total_incidents": 0,
            "uptime_seconds": 0
        }

        logger.info(f"GuardianOrchestrator {self.orchestrator_id} criado")

    async def initialize(self) -> None:
        """Inicializa todos os agentes."""
        logger.info("Inicializando agentes Guardian...")

        # Criar instancias dos agentes
        self.monitor_agent = GuardianMonitorAgent(
            agent_id="guardian_monitor",
            config=self.config.get("monitor", {}),
            message_bus=self.message_bus
        )
        self._register_agent("monitor", "Monitor Agent", self.monitor_agent)

        self.access_agent = GuardianAccessAgent(
            agent_id="guardian_access",
            config=self.config.get("access", {}),
            message_bus=self.message_bus
        )
        self._register_agent("access", "Access Agent", self.access_agent)

        self.analytics_agent = GuardianAnalyticsAgent(
            agent_id="guardian_analytics",
            config=self.config.get("analytics", {}),
            message_bus=self.message_bus
        )
        self._register_agent("analytics", "Analytics Agent", self.analytics_agent)

        self.response_agent = GuardianResponseAgent(
            agent_id="guardian_response",
            config=self.config.get("response", {}),
            message_bus=self.message_bus
        )
        self._register_agent("response", "Response Agent", self.response_agent)

        # Assistente precisa referencias para outros agentes
        self.assistant_agent = GuardianAssistantAgent(
            agent_id="guardian_assistant",
            config=self.config.get("assistant", {}),
            message_bus=self.message_bus,
            monitor_agent=self.monitor_agent,
            access_agent=self.access_agent,
            analytics_agent=self.analytics_agent
        )
        self._register_agent("assistant", "Assistant Agent", self.assistant_agent)

        # Configurar subscricoes internas
        await self._setup_internal_subscriptions()

        logger.info(f"Agentes inicializados: {len(self.agents)}")

    def _register_agent(self, agent_id: str, name: str, instance: Any) -> None:
        """Registra um agente."""
        self.agents[agent_id] = AgentInfo(
            id=agent_id,
            name=name,
            type=type(instance).__name__,
            status=AgentStatus.STOPPED,
            instance=instance
        )

    async def _setup_internal_subscriptions(self) -> None:
        """Configura subscricoes internas do orquestrador."""
        # Contadores de metricas
        async def count_alert(payload: Dict[str, Any]) -> None:
            self.metrics["total_alerts"] += 1

        async def count_incident(payload: Dict[str, Any]) -> None:
            self.metrics["total_incidents"] += 1

        await self.message_bus.subscribe("alert.*", count_alert)
        await self.message_bus.subscribe("incident.created", count_incident)

        # Log de eventos importantes
        async def log_critical(payload: Dict[str, Any]) -> None:
            logger.critical(f"Evento critico: {payload}")

        await self.message_bus.subscribe("emergency.*", log_critical)
        await self.message_bus.subscribe("incident.escalated", log_critical)

    async def start(self) -> None:
        """Inicia o orquestrador e todos os agentes."""
        if self.is_running:
            logger.warning("Orquestrador ja esta em execucao")
            return

        logger.info("Iniciando Guardian Orchestrator...")
        self.started_at = datetime.now()

        # Iniciar agentes
        for agent_id, agent_info in self.agents.items():
            try:
                await self._start_agent(agent_id)
            except Exception as e:
                logger.error(f"Erro ao iniciar agente {agent_id}: {e}")
                agent_info.status = AgentStatus.ERROR
                agent_info.errors += 1

        self.is_running = True
        self._health_check_task = asyncio.create_task(self._health_check_loop())

        # Publicar evento de inicio
        await self.message_bus.publish(
            "orchestrator.started",
            {
                "orchestrator_id": self.orchestrator_id,
                "agents": list(self.agents.keys()),
                "timestamp": datetime.now().isoformat()
            },
            source="orchestrator"
        )

        logger.info("Guardian Orchestrator iniciado com sucesso")

    async def _start_agent(self, agent_id: str) -> None:
        """Inicia um agente especifico."""
        if agent_id not in self.agents:
            raise ValueError(f"Agente {agent_id} nao encontrado")

        agent_info = self.agents[agent_id]
        agent_info.status = AgentStatus.STARTING

        try:
            if agent_info.instance and hasattr(agent_info.instance, 'start'):
                await agent_info.instance.start()

            agent_info.status = AgentStatus.RUNNING
            agent_info.started_at = datetime.now()
            logger.info(f"Agente {agent_id} iniciado")

        except Exception as e:
            agent_info.status = AgentStatus.ERROR
            agent_info.errors += 1
            raise

    async def stop(self) -> None:
        """Para o orquestrador e todos os agentes."""
        if not self.is_running:
            return

        logger.info("Parando Guardian Orchestrator...")

        # Publicar evento de parada
        await self.message_bus.publish(
            "orchestrator.stopping",
            {"orchestrator_id": self.orchestrator_id},
            source="orchestrator"
        )

        # Parar health check
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

        # Parar agentes na ordem inversa
        agent_ids = list(reversed(list(self.agents.keys())))
        for agent_id in agent_ids:
            try:
                await self._stop_agent(agent_id)
            except Exception as e:
                logger.error(f"Erro ao parar agente {agent_id}: {e}")

        self.is_running = False
        logger.info("Guardian Orchestrator parado")

    async def _stop_agent(self, agent_id: str) -> None:
        """Para um agente especifico."""
        if agent_id not in self.agents:
            return

        agent_info = self.agents[agent_id]
        agent_info.status = AgentStatus.STOPPING

        try:
            if agent_info.instance and hasattr(agent_info.instance, 'stop'):
                await agent_info.instance.stop()

            agent_info.status = AgentStatus.STOPPED
            logger.info(f"Agente {agent_id} parado")

        except Exception as e:
            agent_info.status = AgentStatus.ERROR
            agent_info.errors += 1
            raise

    async def _health_check_loop(self) -> None:
        """Loop de verificacao de saude dos agentes."""
        while self.is_running:
            try:
                await asyncio.sleep(30)  # Verificar a cada 30 segundos

                for agent_id, agent_info in self.agents.items():
                    if agent_info.status == AgentStatus.RUNNING:
                        # Verificar se agente esta respondendo
                        healthy = await self._check_agent_health(agent_id)
                        if not healthy:
                            logger.warning(f"Agente {agent_id} nao esta saudavel")
                            agent_info.errors += 1

                            # Tentar reiniciar se muitos erros
                            if agent_info.errors > 3:
                                await self._restart_agent(agent_id)

                # Atualizar uptime
                if self.started_at:
                    self.metrics["uptime_seconds"] = (
                        datetime.now() - self.started_at
                    ).total_seconds()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Erro no health check: {e}")

    async def _check_agent_health(self, agent_id: str) -> bool:
        """Verifica saude de um agente."""
        agent_info = self.agents.get(agent_id)
        if not agent_info or not agent_info.instance:
            return False

        # Verificar se agente tem metodo de health
        if hasattr(agent_info.instance, 'is_running'):
            return agent_info.instance.is_running

        return agent_info.status == AgentStatus.RUNNING

    async def _restart_agent(self, agent_id: str) -> None:
        """Reinicia um agente."""
        logger.warning(f"Reiniciando agente {agent_id}...")

        try:
            await self._stop_agent(agent_id)
            await asyncio.sleep(1)
            await self._start_agent(agent_id)

            agent_info = self.agents[agent_id]
            agent_info.errors = 0

            logger.info(f"Agente {agent_id} reiniciado com sucesso")

        except Exception as e:
            logger.error(f"Falha ao reiniciar agente {agent_id}: {e}")

    # API Publica
    async def get_status(self) -> Dict[str, Any]:
        """Retorna status completo do sistema."""
        agent_statuses = {
            agent_id: {
                "name": info.name,
                "type": info.type,
                "status": info.status.value,
                "started_at": info.started_at.isoformat() if info.started_at else None,
                "errors": info.errors
            }
            for agent_id, info in self.agents.items()
        }

        return {
            "orchestrator_id": self.orchestrator_id,
            "is_running": self.is_running,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "uptime_seconds": self.metrics.get("uptime_seconds", 0),
            "agents": agent_statuses,
            "metrics": self.metrics,
            "timestamp": datetime.now().isoformat()
        }

    async def get_agent(self, agent_id: str) -> Optional[Any]:
        """Retorna instancia de um agente."""
        agent_map = {
            "monitor": self.monitor_agent,
            "access": self.access_agent,
            "analytics": self.analytics_agent,
            "assistant": self.assistant_agent,
            "response": self.response_agent
        }
        return agent_map.get(agent_id)

    async def chat(
        self,
        message: str,
        user_id: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Interface de chat via assistente."""
        if not self.assistant_agent:
            return {"error": "Assistente nao disponivel"}

        return await self.assistant_agent.chat(
            message=message,
            user_id=user_id,
            session_id=session_id
        )

    async def get_risk_assessment(self) -> Dict[str, Any]:
        """Retorna avaliacao de risco via analytics."""
        if not self.analytics_agent:
            return {"error": "Analytics nao disponivel"}

        assessment = await self.analytics_agent.get_risk_assessment()
        if assessment:
            return {
                "score": assessment.risk_score,
                "level": assessment.risk_level.value,
                "trend": assessment.trend.value,
                "recommendations": assessment.recommendations,
                "assessed_at": assessment.assessed_at.isoformat()
            }
        return {"score": 0, "level": "unknown"}

    async def get_active_incidents(self) -> List[Dict[str, Any]]:
        """Retorna incidentes ativos via response agent."""
        if not self.response_agent:
            return []

        incidents = await self.response_agent.get_active_incidents()
        return [
            {
                "id": i.id,
                "type": i.type.value,
                "severity": i.severity.value,
                "status": i.status.value,
                "title": i.title,
                "location": i.location,
                "detected_at": i.detected_at.isoformat()
            }
            for i in incidents
        ]

    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Retorna dados consolidados para dashboard."""
        status = await self.get_status()
        risk = await self.get_risk_assessment()
        incidents = await self.get_active_incidents()

        # Dados do monitor agent
        monitor_data = {}
        if self.monitor_agent:
            try:
                alerts = await self.monitor_agent.get_active_alerts()
                monitor_data = {
                    "active_alerts": len(alerts),
                    "cameras_online": 24,  # Placeholder
                    "cameras_offline": 0
                }
            except Exception:
                pass

        # Dados do access agent
        access_data = {}
        if self.access_agent:
            try:
                stats = await self.access_agent.get_access_statistics(hours=24)
                access_data = {
                    "total_access_24h": stats.get("total", 0),
                    "denied_24h": stats.get("denied", 0)
                }
            except Exception:
                pass

        return {
            "system_status": "online" if self.is_running else "offline",
            "uptime_seconds": status.get("uptime_seconds", 0),
            "agents_running": len([
                a for a in status.get("agents", {}).values()
                if a.get("status") == "running"
            ]),
            "total_agents": len(self.agents),
            "risk_score": risk.get("score", 0),
            "risk_level": risk.get("level", "unknown"),
            "active_incidents": len(incidents),
            "critical_incidents": len([
                i for i in incidents if i.get("severity") == "critical"
            ]),
            **monitor_data,
            **access_data,
            "timestamp": datetime.now().isoformat()
        }

    async def process_event(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """Processa evento externo e distribui para agentes."""
        await self.message_bus.publish(
            f"external.{event_type}",
            event_data,
            source="external"
        )

    async def validate_access(
        self,
        credential_type: str,
        credential_data: Dict[str, Any],
        access_point: str
    ) -> Dict[str, Any]:
        """Valida acesso via access agent."""
        if not self.access_agent:
            return {"allowed": False, "error": "Access agent nao disponivel"}

        from .access_agent import CredentialType

        cred_type = CredentialType(credential_type)

        result = await self.access_agent.validate_access(
            credential_type=cred_type,
            credential_data=credential_data,
            access_point_id=access_point
        )

        return {
            "allowed": result.allowed,
            "reason": result.reason,
            "person_id": result.person_id,
            "person_name": result.person_name,
            "confidence": result.confidence,
            "requires_verification": result.requires_verification
        }


# Factory function
async def create_guardian_system(
    config: Optional[Dict[str, Any]] = None
) -> GuardianOrchestrator:
    """
    Cria e inicializa o sistema Guardian completo.

    Args:
        config: Configuracao opcional para os agentes

    Returns:
        GuardianOrchestrator pronto para uso
    """
    orchestrator = GuardianOrchestrator(config=config)
    await orchestrator.initialize()
    return orchestrator


# Exemplo de uso
async def main():
    """Exemplo de uso do Guardian System."""
    config = {
        "monitor": {
            "alert_cooldown": 60
        },
        "access": {
            "face_threshold": 0.85
        },
        "analytics": {
            "anomaly_z_threshold": 2.5
        }
    }

    # Criar sistema
    guardian = await create_guardian_system(config)

    try:
        # Iniciar
        await guardian.start()

        # Exemplo: obter status
        status = await guardian.get_status()
        print(f"Sistema Guardian ativo: {len(status['agents'])} agentes")

        # Exemplo: chat
        response = await guardian.chat(
            message="Status do sistema",
            user_id="admin"
        )
        print(f"Resposta: {response.get('response')}")

        # Exemplo: dashboard
        dashboard = await guardian.get_dashboard_data()
        print(f"Risk Score: {dashboard['risk_score']}")

        # Manter rodando
        while True:
            await asyncio.sleep(60)

    except KeyboardInterrupt:
        print("\nEncerrando...")
    finally:
        await guardian.stop()


if __name__ == "__main__":
    asyncio.run(main())
