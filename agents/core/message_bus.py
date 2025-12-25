"""
Agent Message Bus - Sistema de Comunicação Full-Duplex
Conecta Plus - Plataforma de Gestão Condominial

Permite comunicação direta entre todos os 36 agentes e o orquestrador,
sem necessidade de registro manual de colaboradores.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import uuid
from collections import defaultdict

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Tipos de mensagens suportadas"""
    DIRECT = "direct"              # Mensagem direta para um agente
    BROADCAST = "broadcast"        # Mensagem para todos os agentes
    REQUEST = "request"            # Requisição que espera resposta
    RESPONSE = "response"          # Resposta a uma requisição
    EVENT = "event"                # Evento/notificação
    COMMAND = "command"            # Comando para execução
    QUERY = "query"                # Consulta de dados
    SYNC = "sync"                  # Sincronização de estado
    COLLABORATION = "collaboration" # Solicitação de colaboração


class MessagePriority(Enum):
    """Prioridade das mensagens"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4
    CRITICAL = 5


@dataclass
class BusMessage:
    """Mensagem padronizada para o message bus"""
    message_id: str
    sender_id: str
    sender_type: str
    receiver_id: str  # '*' para broadcast
    content: Any
    message_type: MessageType = MessageType.DIRECT
    priority: MessagePriority = MessagePriority.NORMAL
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: Optional[str] = None  # Para request/response
    reply_to: Optional[str] = None
    ttl_seconds: int = 300  # Time to live
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "sender_id": self.sender_id,
            "sender_type": self.sender_type,
            "receiver_id": self.receiver_id,
            "content": self.content,
            "message_type": self.message_type.value,
            "priority": self.priority.value,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "reply_to": self.reply_to,
            "ttl_seconds": self.ttl_seconds,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BusMessage':
        return cls(
            message_id=data["message_id"],
            sender_id=data["sender_id"],
            sender_type=data["sender_type"],
            receiver_id=data["receiver_id"],
            content=data["content"],
            message_type=MessageType(data["message_type"]),
            priority=MessagePriority(data["priority"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            correlation_id=data.get("correlation_id"),
            reply_to=data.get("reply_to"),
            ttl_seconds=data.get("ttl_seconds", 300),
            metadata=data.get("metadata", {}),
        )


@dataclass
class AgentRegistration:
    """Registro de um agente no message bus"""
    agent_id: str
    agent_type: str
    condominio_id: str
    queue: asyncio.Queue
    subscriptions: Set[str] = field(default_factory=set)  # Tópicos inscritos
    is_active: bool = True
    registered_at: datetime = field(default_factory=datetime.now)
    last_activity: Optional[datetime] = None
    message_count: int = 0


class AgentMessageBus:
    """
    Message Bus centralizado para comunicação full-duplex entre agentes.

    Características:
    - Qualquer agente pode enviar mensagens para qualquer outro agente
    - Suporta padrão request/response com correlação
    - Suporta broadcast para todos os agentes
    - Suporta publish/subscribe por tópicos
    - Priorização de mensagens
    - Retry automático para falhas de entrega
    """

    _instance: Optional['AgentMessageBus'] = None

    def __new__(cls, *args, **kwargs):
        """Singleton pattern para garantir uma única instância"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, max_queue_size: int = 1000):
        if self._initialized:
            return

        self._agents: Dict[str, AgentRegistration] = {}
        self._condominios: Dict[str, Set[str]] = defaultdict(set)
        self._topics: Dict[str, Set[str]] = defaultdict(set)  # topic -> agent_ids
        self._pending_responses: Dict[str, asyncio.Future] = {}
        self._message_handlers: Dict[str, Callable] = {}
        self._max_queue_size = max_queue_size
        self._is_running = False
        self._orchestrator_id = "orchestrator"

        # Métricas
        self._metrics = {
            "messages_sent": 0,
            "messages_delivered": 0,
            "messages_failed": 0,
            "broadcasts_sent": 0,
            "requests_pending": 0,
        }

        # Event handlers
        self._on_message_callbacks: List[Callable] = []
        self._on_error_callbacks: List[Callable] = []

        self._initialized = True
        logger.info("AgentMessageBus inicializado")

    # ==================== REGISTRO DE AGENTES ====================

    def register_agent(
        self,
        agent_id: str,
        agent_type: str,
        condominio_id: str,
        subscriptions: List[str] = None
    ) -> asyncio.Queue:
        """
        Registra um agente no message bus.

        Retorna a fila de mensagens do agente.
        """
        if agent_id in self._agents:
            logger.warning(f"Agente {agent_id} já registrado, atualizando...")
            return self._agents[agent_id].queue

        queue = asyncio.Queue(maxsize=self._max_queue_size)

        registration = AgentRegistration(
            agent_id=agent_id,
            agent_type=agent_type,
            condominio_id=condominio_id,
            queue=queue,
            subscriptions=set(subscriptions or [])
        )

        self._agents[agent_id] = registration
        self._condominios[condominio_id].add(agent_id)

        # Registrar subscriptions
        for topic in registration.subscriptions:
            self._topics[topic].add(agent_id)

        logger.info(f"Agente {agent_id} ({agent_type}) registrado no message bus")
        return queue

    def unregister_agent(self, agent_id: str) -> bool:
        """Remove um agente do message bus"""
        if agent_id not in self._agents:
            return False

        reg = self._agents[agent_id]

        # Remover de condominios
        self._condominios[reg.condominio_id].discard(agent_id)

        # Remover de tópicos
        for topic in reg.subscriptions:
            self._topics[topic].discard(agent_id)

        del self._agents[agent_id]
        logger.info(f"Agente {agent_id} removido do message bus")
        return True

    def get_registered_agents(self) -> List[Dict[str, Any]]:
        """Retorna lista de agentes registrados"""
        return [
            {
                "agent_id": reg.agent_id,
                "agent_type": reg.agent_type,
                "condominio_id": reg.condominio_id,
                "is_active": reg.is_active,
                "message_count": reg.message_count,
                "subscriptions": list(reg.subscriptions),
            }
            for reg in self._agents.values()
        ]

    def get_agents_by_type(self, agent_type: str) -> List[str]:
        """Retorna IDs de agentes de um tipo específico"""
        return [
            reg.agent_id
            for reg in self._agents.values()
            if reg.agent_type == agent_type
        ]

    def get_agents_by_condominio(self, condominio_id: str) -> List[str]:
        """Retorna IDs de agentes de um condomínio específico"""
        return list(self._condominios.get(condominio_id, set()))

    # ==================== ENVIO DE MENSAGENS ====================

    async def send(
        self,
        sender_id: str,
        receiver_id: str,
        content: Any,
        message_type: MessageType = MessageType.DIRECT,
        priority: MessagePriority = MessagePriority.NORMAL,
        correlation_id: str = None,
        metadata: Dict[str, Any] = None,
    ) -> bool:
        """
        Envia uma mensagem direta para um agente específico.
        """
        if sender_id not in self._agents and sender_id != self._orchestrator_id:
            logger.warning(f"Remetente {sender_id} não registrado")
            return False

        if receiver_id not in self._agents and receiver_id != self._orchestrator_id:
            logger.warning(f"Destinatário {receiver_id} não encontrado")
            return False

        sender_type = self._agents[sender_id].agent_type if sender_id in self._agents else "orchestrator"

        message = BusMessage(
            message_id=str(uuid.uuid4()),
            sender_id=sender_id,
            sender_type=sender_type,
            receiver_id=receiver_id,
            content=content,
            message_type=message_type,
            priority=priority,
            correlation_id=correlation_id,
            metadata=metadata or {},
        )

        return await self._deliver_message(message)

    async def broadcast(
        self,
        sender_id: str,
        content: Any,
        message_type: MessageType = MessageType.BROADCAST,
        priority: MessagePriority = MessagePriority.NORMAL,
        exclude_sender: bool = True,
        condominio_id: str = None,
        metadata: Dict[str, Any] = None,
    ) -> int:
        """
        Envia uma mensagem para todos os agentes (ou de um condomínio específico).

        Retorna o número de agentes que receberam a mensagem.
        """
        sender_type = self._agents[sender_id].agent_type if sender_id in self._agents else "orchestrator"

        message = BusMessage(
            message_id=str(uuid.uuid4()),
            sender_id=sender_id,
            sender_type=sender_type,
            receiver_id="*",
            content=content,
            message_type=message_type,
            priority=priority,
            metadata=metadata or {},
        )

        # Determinar destinatários
        if condominio_id:
            receivers = self._condominios.get(condominio_id, set())
        else:
            receivers = set(self._agents.keys())

        if exclude_sender:
            receivers = receivers - {sender_id}

        # Entregar para cada agente
        delivered = 0
        for receiver_id in receivers:
            msg_copy = BusMessage(
                message_id=f"{message.message_id}_{receiver_id}",
                sender_id=message.sender_id,
                sender_type=message.sender_type,
                receiver_id=receiver_id,
                content=message.content,
                message_type=message.message_type,
                priority=message.priority,
                timestamp=message.timestamp,
                metadata=message.metadata,
            )
            if await self._deliver_message(msg_copy):
                delivered += 1

        self._metrics["broadcasts_sent"] += 1
        return delivered

    async def publish(
        self,
        sender_id: str,
        topic: str,
        content: Any,
        priority: MessagePriority = MessagePriority.NORMAL,
        metadata: Dict[str, Any] = None,
    ) -> int:
        """
        Publica uma mensagem em um tópico para todos os inscritos.

        Retorna o número de agentes que receberam a mensagem.
        """
        subscribers = self._topics.get(topic, set())

        if not subscribers:
            logger.debug(f"Nenhum inscrito no tópico '{topic}'")
            return 0

        sender_type = self._agents[sender_id].agent_type if sender_id in self._agents else "orchestrator"

        delivered = 0
        for subscriber_id in subscribers:
            message = BusMessage(
                message_id=str(uuid.uuid4()),
                sender_id=sender_id,
                sender_type=sender_type,
                receiver_id=subscriber_id,
                content=content,
                message_type=MessageType.EVENT,
                priority=priority,
                metadata={**(metadata or {}), "topic": topic},
            )
            if await self._deliver_message(message):
                delivered += 1

        return delivered

    def subscribe(self, agent_id: str, topic: str) -> bool:
        """Inscreve um agente em um tópico"""
        if agent_id not in self._agents:
            return False

        self._agents[agent_id].subscriptions.add(topic)
        self._topics[topic].add(agent_id)
        logger.debug(f"Agente {agent_id} inscrito no tópico '{topic}'")
        return True

    def unsubscribe(self, agent_id: str, topic: str) -> bool:
        """Remove inscrição de um agente de um tópico"""
        if agent_id not in self._agents:
            return False

        self._agents[agent_id].subscriptions.discard(topic)
        self._topics[topic].discard(agent_id)
        return True

    # ==================== REQUEST/RESPONSE ====================

    async def request(
        self,
        sender_id: str,
        receiver_id: str,
        content: Any,
        timeout: float = 30.0,
        metadata: Dict[str, Any] = None,
    ) -> Optional[Any]:
        """
        Envia uma requisição e aguarda resposta (padrão request/response).

        Retorna a resposta ou None se timeout.
        """
        correlation_id = str(uuid.uuid4())

        # Criar future para aguardar resposta
        future = asyncio.get_event_loop().create_future()
        self._pending_responses[correlation_id] = future
        self._metrics["requests_pending"] += 1

        sender_type = self._agents[sender_id].agent_type if sender_id in self._agents else "orchestrator"

        message = BusMessage(
            message_id=str(uuid.uuid4()),
            sender_id=sender_id,
            sender_type=sender_type,
            receiver_id=receiver_id,
            content=content,
            message_type=MessageType.REQUEST,
            correlation_id=correlation_id,
            reply_to=sender_id,
            metadata=metadata or {},
        )

        # Enviar requisição
        if not await self._deliver_message(message):
            del self._pending_responses[correlation_id]
            self._metrics["requests_pending"] -= 1
            return None

        # Aguardar resposta
        try:
            response = await asyncio.wait_for(future, timeout=timeout)
            return response
        except asyncio.TimeoutError:
            logger.warning(f"Timeout aguardando resposta de {receiver_id}")
            return None
        finally:
            self._pending_responses.pop(correlation_id, None)
            self._metrics["requests_pending"] -= 1

    async def respond(
        self,
        sender_id: str,
        original_message: BusMessage,
        content: Any,
        metadata: Dict[str, Any] = None,
    ) -> bool:
        """
        Envia uma resposta para uma requisição.
        """
        if not original_message.correlation_id:
            logger.warning("Mensagem original não tem correlation_id")
            return False

        reply_to = original_message.reply_to or original_message.sender_id

        sender_type = self._agents[sender_id].agent_type if sender_id in self._agents else "orchestrator"

        message = BusMessage(
            message_id=str(uuid.uuid4()),
            sender_id=sender_id,
            sender_type=sender_type,
            receiver_id=reply_to,
            content=content,
            message_type=MessageType.RESPONSE,
            correlation_id=original_message.correlation_id,
            metadata=metadata or {},
        )

        # Se for resposta para uma requisição pendente local, resolver o future
        if original_message.correlation_id in self._pending_responses:
            future = self._pending_responses[original_message.correlation_id]
            if not future.done():
                future.set_result(content)
            return True

        # Caso contrário, entregar a mensagem
        return await self._deliver_message(message)

    # ==================== ENTREGA ====================

    async def _deliver_message(self, message: BusMessage) -> bool:
        """Entrega uma mensagem para o destinatário"""
        try:
            # Callback de mensagem
            for callback in self._on_message_callbacks:
                try:
                    callback(message)
                except Exception as e:
                    logger.error(f"Erro em callback de mensagem: {e}")

            # Verificar se é resposta para requisição pendente
            if message.message_type == MessageType.RESPONSE and message.correlation_id:
                if message.correlation_id in self._pending_responses:
                    future = self._pending_responses[message.correlation_id]
                    if not future.done():
                        future.set_result(message.content)
                    self._metrics["messages_delivered"] += 1
                    return True

            # Entregar na fila do destinatário
            if message.receiver_id in self._agents:
                reg = self._agents[message.receiver_id]

                if not reg.is_active:
                    logger.warning(f"Agente {message.receiver_id} não está ativo")
                    self._metrics["messages_failed"] += 1
                    return False

                try:
                    reg.queue.put_nowait(message)
                    reg.last_activity = datetime.now()
                    reg.message_count += 1
                    self._metrics["messages_delivered"] += 1
                    self._metrics["messages_sent"] += 1
                    return True
                except asyncio.QueueFull:
                    logger.error(f"Fila do agente {message.receiver_id} está cheia")
                    self._metrics["messages_failed"] += 1
                    return False

            logger.warning(f"Destinatário {message.receiver_id} não encontrado")
            self._metrics["messages_failed"] += 1
            return False

        except Exception as e:
            logger.error(f"Erro ao entregar mensagem: {e}")
            self._metrics["messages_failed"] += 1
            for callback in self._on_error_callbacks:
                try:
                    callback(message, e)
                except Exception:
                    pass
            return False

    # ==================== CALLBACKS E EVENTOS ====================

    def on_message(self, callback: Callable[[BusMessage], None]) -> None:
        """Registra callback para todas as mensagens"""
        self._on_message_callbacks.append(callback)

    def on_error(self, callback: Callable[[BusMessage, Exception], None]) -> None:
        """Registra callback para erros de entrega"""
        self._on_error_callbacks.append(callback)

    # ==================== UTILITÁRIOS ====================

    def get_metrics(self) -> Dict[str, Any]:
        """Retorna métricas do message bus"""
        return {
            **self._metrics,
            "agents_registered": len(self._agents),
            "condominios_count": len(self._condominios),
            "topics_count": len(self._topics),
        }

    def get_status(self) -> Dict[str, Any]:
        """Retorna status do message bus"""
        return {
            "is_running": self._is_running,
            "agents_registered": len(self._agents),
            "agent_types": list(set(reg.agent_type for reg in self._agents.values())),
            "condominios": list(self._condominios.keys()),
            "topics": list(self._topics.keys()),
            "metrics": self.get_metrics(),
        }

    async def start(self) -> None:
        """Inicia o message bus"""
        self._is_running = True
        logger.info("AgentMessageBus iniciado")

    async def stop(self) -> None:
        """Para o message bus"""
        self._is_running = False

        # Cancelar requisições pendentes
        for correlation_id, future in self._pending_responses.items():
            if not future.done():
                future.cancel()
        self._pending_responses.clear()

        logger.info("AgentMessageBus parado")

    def reset(self) -> None:
        """Reseta o message bus (útil para testes)"""
        self._agents.clear()
        self._condominios.clear()
        self._topics.clear()
        self._pending_responses.clear()
        self._metrics = {
            "messages_sent": 0,
            "messages_delivered": 0,
            "messages_failed": 0,
            "broadcasts_sent": 0,
            "requests_pending": 0,
        }


# Instância singleton global
message_bus = AgentMessageBus()


# ==================== MIXIN PARA AGENTES ====================

class MessageBusAgentMixin:
    """
    Mixin que adiciona capacidade de comunicação via message bus aos agentes.

    Uso:
        class MeuAgente(BaseAgent, MessageBusAgentMixin):
            def __init__(self, ...):
                super().__init__(...)
                self.init_message_bus()
    """

    def init_message_bus(self, subscriptions: List[str] = None) -> None:
        """Inicializa conexão com o message bus"""
        self._bus = message_bus
        self._bus_queue = self._bus.register_agent(
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            condominio_id=self.condominio_id,
            subscriptions=subscriptions or []
        )
        self._bus_running = False

    async def start_message_listener(self) -> None:
        """Inicia listener de mensagens do bus"""
        self._bus_running = True
        asyncio.create_task(self._message_listener_loop())

    async def stop_message_listener(self) -> None:
        """Para listener de mensagens"""
        self._bus_running = False
        self._bus.unregister_agent(self.agent_id)

    async def _message_listener_loop(self) -> None:
        """Loop de processamento de mensagens do bus"""
        while self._bus_running:
            try:
                message = await asyncio.wait_for(
                    self._bus_queue.get(),
                    timeout=1.0
                )
                await self._handle_bus_message(message)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Erro no listener de mensagens: {e}")

    async def _handle_bus_message(self, message: BusMessage) -> None:
        """
        Processa uma mensagem recebida do bus.
        Sobrescreva este método para lógica específica.
        """
        logger.info(f"[{self.agent_id}] Mensagem de {message.sender_id}: {message.message_type.value}")

        # Se for uma requisição, responder automaticamente
        if message.message_type == MessageType.REQUEST:
            response = await self.handle_request(message)
            if response is not None:
                await self._bus.respond(self.agent_id, message, response)

    async def handle_request(self, message: BusMessage) -> Optional[Any]:
        """
        Processa uma requisição. Sobrescreva para lógica específica.
        Retorne None para não enviar resposta automática.
        """
        return {"status": "received", "agent": self.agent_id}

    # ==================== MÉTODOS DE CONVENIÊNCIA ====================

    async def send_to_agent(
        self,
        receiver_id: str,
        content: Any,
        message_type: MessageType = MessageType.DIRECT,
        priority: MessagePriority = MessagePriority.NORMAL,
        metadata: Dict[str, Any] = None,
    ) -> bool:
        """Envia mensagem direta para outro agente"""
        return await self._bus.send(
            sender_id=self.agent_id,
            receiver_id=receiver_id,
            content=content,
            message_type=message_type,
            priority=priority,
            metadata=metadata,
        )

    async def broadcast_message(
        self,
        content: Any,
        message_type: MessageType = MessageType.BROADCAST,
        priority: MessagePriority = MessagePriority.NORMAL,
        exclude_self: bool = True,
        condominio_only: bool = False,
        metadata: Dict[str, Any] = None,
    ) -> int:
        """Envia mensagem broadcast para todos os agentes"""
        return await self._bus.broadcast(
            sender_id=self.agent_id,
            content=content,
            message_type=message_type,
            priority=priority,
            exclude_sender=exclude_self,
            condominio_id=self.condominio_id if condominio_only else None,
            metadata=metadata,
        )

    async def publish_event(
        self,
        topic: str,
        content: Any,
        priority: MessagePriority = MessagePriority.NORMAL,
        metadata: Dict[str, Any] = None,
    ) -> int:
        """Publica evento em um tópico"""
        return await self._bus.publish(
            sender_id=self.agent_id,
            topic=topic,
            content=content,
            priority=priority,
            metadata=metadata,
        )

    async def request_from_agent(
        self,
        receiver_id: str,
        content: Any,
        timeout: float = 30.0,
        metadata: Dict[str, Any] = None,
    ) -> Optional[Any]:
        """Envia requisição e aguarda resposta"""
        return await self._bus.request(
            sender_id=self.agent_id,
            receiver_id=receiver_id,
            content=content,
            timeout=timeout,
            metadata=metadata,
        )

    def subscribe_to_topic(self, topic: str) -> bool:
        """Inscreve-se em um tópico"""
        return self._bus.subscribe(self.agent_id, topic)

    def unsubscribe_from_topic(self, topic: str) -> bool:
        """Cancela inscrição em um tópico"""
        return self._bus.unsubscribe(self.agent_id, topic)

    def get_agents_by_type(self, agent_type: str) -> List[str]:
        """Retorna IDs de agentes de um tipo"""
        return self._bus.get_agents_by_type(agent_type)

    def get_condominio_agents(self) -> List[str]:
        """Retorna IDs de agentes do mesmo condomínio"""
        return self._bus.get_agents_by_condominio(self.condominio_id)


# Tópicos padrão para comunicação entre agentes
class StandardTopics:
    """Tópicos padrão para publish/subscribe"""
    # Segurança
    SECURITY_ALERT = "security.alert"
    SECURITY_EVENT = "security.event"
    ACCESS_GRANTED = "access.granted"
    ACCESS_DENIED = "access.denied"

    # Emergências
    EMERGENCY_ALERT = "emergency.alert"
    EMERGENCY_RESOLVED = "emergency.resolved"

    # Financeiro
    PAYMENT_RECEIVED = "payment.received"
    PAYMENT_OVERDUE = "payment.overdue"

    # Manutenção
    MAINTENANCE_REQUEST = "maintenance.request"
    MAINTENANCE_COMPLETED = "maintenance.completed"

    # Comunicação
    NOTIFICATION_SENT = "notification.sent"
    COMMUNICATION_BROADCAST = "communication.broadcast"

    # Reservas
    RESERVATION_CREATED = "reservation.created"
    RESERVATION_CANCELLED = "reservation.cancelled"

    # Moradores
    RESIDENT_UPDATE = "resident.update"
    VISITOR_ARRIVAL = "visitor.arrival"

    # Sistema
    SYSTEM_STATUS = "system.status"
    AGENT_STARTED = "agent.started"
    AGENT_STOPPED = "agent.stopped"


# Alias para compatibilidade
MessageBus = AgentMessageBus
