"""
Conecta Plus - Base Agent Class
Framework de Evolução de Agentes em 7 Níveis

Níveis de Evolução:
1. REATIVO      - Responde a comandos
2. PROATIVO     - Antecipa necessidades
3. PREDITIVO    - Prevê o futuro com dados
4. AUTÔNOMO     - Age sozinho quando necessário
5. EVOLUTIVO    - Aprende e melhora continuamente
6. COLABORATIVO - Agentes trabalham em sinergia
7. TRANSCENDENTE - Cria soluções que humanos não pensariam
"""

from abc import ABC, abstractmethod
from enum import IntEnum
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
import json
import logging
from pydantic import BaseModel

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EvolutionLevel(IntEnum):
    """Níveis de evolução do agente"""
    REACTIVE = 1        # Responde a comandos
    PROACTIVE = 2       # Antecipa necessidades
    PREDICTIVE = 3      # Prevê com ML
    AUTONOMOUS = 4      # Age sozinho
    EVOLUTIONARY = 5    # Aprende continuamente
    COLLABORATIVE = 6   # Trabalha em sinergia
    TRANSCENDENT = 7    # Soluções além do humano


class Priority(IntEnum):
    """Prioridade de tarefas e alertas"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4
    CRITICAL = 5


@dataclass
class AgentCapability:
    """Representa uma capacidade do agente"""
    name: str
    description: str
    level: EvolutionLevel
    enabled: bool = True
    dependencies: List[str] = field(default_factory=list)


@dataclass
class AgentContext:
    """Contexto de execução do agente"""
    condominio_id: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentMessage:
    """Mensagem entre agentes ou com usuários"""
    sender: str
    receiver: str
    content: Any
    message_type: str = "text"
    priority: Priority = Priority.MEDIUM
    timestamp: datetime = field(default_factory=datetime.now)
    requires_response: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentAction:
    """Ação executada ou a executar pelo agente"""
    action_type: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Any] = None
    status: str = "pending"  # pending, executing, completed, failed
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


@dataclass
class AgentPrediction:
    """Previsão feita pelo agente"""
    prediction_type: str
    description: str
    probability: float  # 0.0 - 1.0
    confidence: float   # 0.0 - 1.0
    timeframe: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    recommended_actions: List[str] = field(default_factory=list)


class AgentState(BaseModel):
    """Estado atual do agente"""
    agent_id: str
    agent_type: str
    evolution_level: int
    is_active: bool = True
    current_task: Optional[str] = None
    pending_tasks: int = 0
    last_activity: Optional[datetime] = None
    performance_score: float = 0.0
    error_count: int = 0


class BaseAgent(ABC):
    """
    Classe base para todos os agentes do Conecta Plus.
    Implementa o framework de evolução em 7 níveis.
    """

    def __init__(
        self,
        agent_id: str,
        agent_type: str,
        condominio_id: str,
        evolution_level: EvolutionLevel = EvolutionLevel.REACTIVE,
        llm_client: Any = None,
        memory_store: Any = None,
        vector_store: Any = None,
    ):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.condominio_id = condominio_id
        self.evolution_level = evolution_level
        self.llm = llm_client
        self.memory = memory_store
        self.vector_store = vector_store

        # Estado interno
        self._is_running = False
        self._capabilities: Dict[str, AgentCapability] = {}
        self._tools: Dict[str, Callable] = {}
        self._collaborators: Dict[str, 'BaseAgent'] = {}
        self._action_history: List[AgentAction] = []
        self._prediction_history: List[AgentPrediction] = []
        self._message_queue: asyncio.Queue = asyncio.Queue()

        # Callbacks
        self._on_action_callbacks: List[Callable] = []
        self._on_prediction_callbacks: List[Callable] = []
        self._on_error_callbacks: List[Callable] = []

        # Métricas
        self._metrics = {
            "actions_executed": 0,
            "predictions_made": 0,
            "successful_actions": 0,
            "failed_actions": 0,
            "messages_sent": 0,
            "messages_received": 0,
            "learning_iterations": 0,
        }

        # Inicializar capacidades
        self._register_base_capabilities()
        self._register_capabilities()

        logger.info(f"Agente {agent_id} ({agent_type}) inicializado no nível {evolution_level.name}")

    # ==================== MÉTODOS ABSTRATOS ====================

    @abstractmethod
    def _register_capabilities(self) -> None:
        """Registra capacidades específicas do agente"""
        pass

    @abstractmethod
    async def process(self, input_data: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        """Processa entrada e retorna resultado"""
        pass

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Retorna o system prompt do agente"""
        pass

    # ==================== CAPACIDADES BASE ====================

    def _register_base_capabilities(self) -> None:
        """Registra capacidades base disponíveis para todos os agentes"""

        # Nível 1: Reativo
        self._capabilities["respond_to_commands"] = AgentCapability(
            name="respond_to_commands",
            description="Responder a comandos diretos",
            level=EvolutionLevel.REACTIVE,
        )

        # Nível 2: Proativo
        self._capabilities["anticipate_needs"] = AgentCapability(
            name="anticipate_needs",
            description="Antecipar necessidades baseado em padrões",
            level=EvolutionLevel.PROACTIVE,
        )

        self._capabilities["send_alerts"] = AgentCapability(
            name="send_alerts",
            description="Enviar alertas proativamente",
            level=EvolutionLevel.PROACTIVE,
        )

        # Nível 3: Preditivo
        self._capabilities["make_predictions"] = AgentCapability(
            name="make_predictions",
            description="Fazer previsões com ML",
            level=EvolutionLevel.PREDICTIVE,
        )

        self._capabilities["analyze_patterns"] = AgentCapability(
            name="analyze_patterns",
            description="Analisar padrões em dados históricos",
            level=EvolutionLevel.PREDICTIVE,
        )

        # Nível 4: Autônomo
        self._capabilities["autonomous_actions"] = AgentCapability(
            name="autonomous_actions",
            description="Executar ações sem intervenção humana",
            level=EvolutionLevel.AUTONOMOUS,
        )

        self._capabilities["self_decision"] = AgentCapability(
            name="self_decision",
            description="Tomar decisões baseadas em regras e contexto",
            level=EvolutionLevel.AUTONOMOUS,
        )

        # Nível 5: Evolutivo
        self._capabilities["continuous_learning"] = AgentCapability(
            name="continuous_learning",
            description="Aprender com cada interação",
            level=EvolutionLevel.EVOLUTIONARY,
        )

        self._capabilities["self_improvement"] = AgentCapability(
            name="self_improvement",
            description="Identificar e melhorar pontos fracos",
            level=EvolutionLevel.EVOLUTIONARY,
        )

        # Nível 6: Colaborativo
        self._capabilities["agent_collaboration"] = AgentCapability(
            name="agent_collaboration",
            description="Colaborar com outros agentes",
            level=EvolutionLevel.COLLABORATIVE,
        )

        self._capabilities["knowledge_sharing"] = AgentCapability(
            name="knowledge_sharing",
            description="Compartilhar conhecimento entre agentes",
            level=EvolutionLevel.COLLABORATIVE,
        )

        # Nível 7: Transcendente
        self._capabilities["creative_solutions"] = AgentCapability(
            name="creative_solutions",
            description="Criar soluções inovadoras",
            level=EvolutionLevel.TRANSCENDENT,
        )

        self._capabilities["cross_domain_insights"] = AgentCapability(
            name="cross_domain_insights",
            description="Gerar insights entre domínios diferentes",
            level=EvolutionLevel.TRANSCENDENT,
        )

    def has_capability(self, capability_name: str) -> bool:
        """Verifica se o agente tem uma capacidade ativa"""
        if capability_name not in self._capabilities:
            return False
        capability = self._capabilities[capability_name]
        return capability.enabled and capability.level <= self.evolution_level

    def get_active_capabilities(self) -> List[AgentCapability]:
        """Retorna lista de capacidades ativas"""
        return [
            cap for cap in self._capabilities.values()
            if cap.enabled and cap.level <= self.evolution_level
        ]

    # ==================== FERRAMENTAS ====================

    def register_tool(self, name: str, func: Callable, description: str = "") -> None:
        """Registra uma ferramenta para o agente usar"""
        self._tools[name] = func
        logger.debug(f"Ferramenta '{name}' registrada para {self.agent_id}")

    async def use_tool(self, tool_name: str, **kwargs) -> Any:
        """Usa uma ferramenta registrada"""
        if tool_name not in self._tools:
            raise ValueError(f"Ferramenta '{tool_name}' não encontrada")

        try:
            result = self._tools[tool_name](**kwargs)
            if asyncio.iscoroutine(result):
                result = await result
            return result
        except Exception as e:
            logger.error(f"Erro ao usar ferramenta '{tool_name}': {e}")
            raise

    # ==================== AÇÕES ====================

    async def execute_action(self, action: AgentAction, context: AgentContext) -> AgentAction:
        """Executa uma ação e registra o resultado"""
        action.status = "executing"
        action.started_at = datetime.now()

        try:
            # Verificar se pode executar ações autônomas
            if not self.has_capability("autonomous_actions"):
                # Requer aprovação para ações
                action.status = "pending_approval"
                return action

            # Executar ação específica (implementar em subclasses)
            result = await self._execute_action_impl(action, context)
            action.result = result
            action.status = "completed"
            self._metrics["successful_actions"] += 1

        except Exception as e:
            action.status = "failed"
            action.error = str(e)
            self._metrics["failed_actions"] += 1
            logger.error(f"Erro ao executar ação: {e}")

        action.completed_at = datetime.now()
        self._action_history.append(action)
        self._metrics["actions_executed"] += 1

        # Callbacks
        for callback in self._on_action_callbacks:
            try:
                callback(action)
            except Exception as e:
                logger.error(f"Erro em callback de ação: {e}")

        return action

    async def _execute_action_impl(self, action: AgentAction, context: AgentContext) -> Any:
        """Implementação específica da execução de ação (sobrescrever em subclasses)"""
        raise NotImplementedError("Subclasse deve implementar _execute_action_impl")

    # ==================== PREDIÇÕES ====================

    async def make_prediction(
        self,
        prediction_type: str,
        data: Dict[str, Any],
        context: AgentContext
    ) -> Optional[AgentPrediction]:
        """Faz uma previsão baseada em dados"""
        if not self.has_capability("make_predictions"):
            logger.warning(f"Agente {self.agent_id} não tem capacidade de predição")
            return None

        try:
            prediction = await self._make_prediction_impl(prediction_type, data, context)
            if prediction:
                self._prediction_history.append(prediction)
                self._metrics["predictions_made"] += 1

                # Callbacks
                for callback in self._on_prediction_callbacks:
                    try:
                        callback(prediction)
                    except Exception as e:
                        logger.error(f"Erro em callback de predição: {e}")

            return prediction

        except Exception as e:
            logger.error(f"Erro ao fazer predição: {e}")
            return None

    async def _make_prediction_impl(
        self,
        prediction_type: str,
        data: Dict[str, Any],
        context: AgentContext
    ) -> Optional[AgentPrediction]:
        """Implementação específica de predição (sobrescrever em subclasses)"""
        return None

    # ==================== COLABORAÇÃO ====================

    def register_collaborator(self, agent: 'BaseAgent') -> None:
        """Registra outro agente como colaborador"""
        if self.has_capability("agent_collaboration"):
            self._collaborators[agent.agent_id] = agent
            logger.info(f"Agente {agent.agent_id} registrado como colaborador de {self.agent_id}")

    async def send_message(self, receiver_id: str, content: Any, **kwargs) -> bool:
        """Envia mensagem para outro agente"""
        if receiver_id not in self._collaborators:
            logger.warning(f"Agente {receiver_id} não é colaborador de {self.agent_id}")
            return False

        message = AgentMessage(
            sender=self.agent_id,
            receiver=receiver_id,
            content=content,
            **kwargs
        )

        try:
            receiver = self._collaborators[receiver_id]
            await receiver.receive_message(message)
            self._metrics["messages_sent"] += 1
            return True
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem: {e}")
            return False

    async def receive_message(self, message: AgentMessage) -> None:
        """Recebe mensagem de outro agente"""
        await self._message_queue.put(message)
        self._metrics["messages_received"] += 1

    async def process_messages(self) -> None:
        """Processa mensagens na fila"""
        while not self._message_queue.empty():
            message = await self._message_queue.get()
            await self._handle_message(message)

    async def _handle_message(self, message: AgentMessage) -> None:
        """Processa uma mensagem recebida (sobrescrever em subclasses)"""
        logger.info(f"Mensagem recebida de {message.sender}: {message.content}")

    # ==================== APRENDIZADO ====================

    async def learn(self, feedback: Dict[str, Any], context: AgentContext) -> None:
        """Aprende com feedback"""
        if not self.has_capability("continuous_learning"):
            return

        try:
            await self._learn_impl(feedback, context)
            self._metrics["learning_iterations"] += 1
            logger.debug(f"Agente {self.agent_id} aprendeu com feedback")
        except Exception as e:
            logger.error(f"Erro ao aprender: {e}")

    async def _learn_impl(self, feedback: Dict[str, Any], context: AgentContext) -> None:
        """Implementação específica de aprendizado (sobrescrever em subclasses)"""
        pass

    # ==================== MEMÓRIA ====================

    async def remember(self, key: str, value: Any, metadata: Dict[str, Any] = None) -> None:
        """Armazena informação na memória de longo prazo"""
        if self.memory:
            await self.memory.store(
                agent_id=self.agent_id,
                key=key,
                value=value,
                metadata=metadata or {}
            )

    async def recall(self, key: str) -> Optional[Any]:
        """Recupera informação da memória"""
        if self.memory:
            return await self.memory.retrieve(agent_id=self.agent_id, key=key)
        return None

    async def search_memory(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Busca semântica na memória"""
        if self.vector_store:
            return await self.vector_store.search(
                agent_id=self.agent_id,
                query=query,
                limit=limit
            )
        return []

    # ==================== LLM ====================

    async def think(self, prompt: str, context: AgentContext = None) -> str:
        """Usa o LLM para raciocínio"""
        if not self.llm:
            raise ValueError("LLM não configurado")

        system_prompt = self.get_system_prompt()

        # Adicionar contexto
        if context:
            system_prompt += f"\n\nContexto atual:\n{json.dumps(context.metadata, indent=2)}"

        # Adicionar memórias relevantes
        if self.vector_store:
            memories = await self.search_memory(prompt, limit=5)
            if memories:
                system_prompt += "\n\nMemórias relevantes:\n"
                for mem in memories:
                    system_prompt += f"- {mem.get('content', '')}\n"

        return await self.llm.generate(
            system_prompt=system_prompt,
            user_prompt=prompt
        )

    # ==================== ESTADO E MÉTRICAS ====================

    def get_state(self) -> AgentState:
        """Retorna estado atual do agente"""
        return AgentState(
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            evolution_level=self.evolution_level,
            is_active=self._is_running,
            pending_tasks=self._message_queue.qsize(),
            performance_score=self._calculate_performance_score(),
            error_count=self._metrics["failed_actions"],
        )

    def get_metrics(self) -> Dict[str, Any]:
        """Retorna métricas do agente"""
        return {
            **self._metrics,
            "success_rate": (
                self._metrics["successful_actions"] / max(self._metrics["actions_executed"], 1)
            ),
            "capabilities_active": len(self.get_active_capabilities()),
            "collaborators_count": len(self._collaborators),
        }

    def _calculate_performance_score(self) -> float:
        """Calcula score de performance do agente"""
        if self._metrics["actions_executed"] == 0:
            return 0.0

        success_rate = self._metrics["successful_actions"] / self._metrics["actions_executed"]
        return round(success_rate * 100, 2)

    # ==================== LIFECYCLE ====================

    async def start(self) -> None:
        """Inicia o agente"""
        self._is_running = True
        logger.info(f"Agente {self.agent_id} iniciado")

    async def stop(self) -> None:
        """Para o agente"""
        self._is_running = False
        logger.info(f"Agente {self.agent_id} parado")

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.agent_id}, level={self.evolution_level.name})>"
