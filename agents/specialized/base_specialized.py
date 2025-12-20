"""
Conecta Plus - Base Specialized Agent
Classe base para agentes especializados

Agentes especializados são extensões do BaseAgent que:
- Possuem conhecimento de domínio específico
- Implementam workflows especializados
- Têm acesso a ferramentas específicas do domínio
- Podem ter prompts e comportamentos customizados
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable, Type
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class SpecializedDomain(Enum):
    """Domínios de especialização"""
    ACESSO = "acesso"
    CFTV = "cftv"
    COMUNICACAO = "comunicacao"
    FINANCEIRO = "financeiro"
    MANUTENCAO = "manutencao"
    OCORRENCIAS = "ocorrencias"
    PORTARIA = "portaria"
    SINDICO = "sindico"


class AgentCapability(Enum):
    """Capacidades dos agentes"""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    APPROVE = "approve"
    ESCALATE = "escalate"
    NOTIFY = "notify"
    INTEGRATE = "integrate"


@dataclass
class DomainKnowledge:
    """Conhecimento de domínio do agente"""
    domain: SpecializedDomain
    expertise_level: int = 1  # 1-5
    knowledge_base: Dict[str, Any] = field(default_factory=dict)
    procedures: List[Dict[str, Any]] = field(default_factory=list)
    rules: List[Dict[str, Any]] = field(default_factory=list)
    faq: List[Dict[str, Any]] = field(default_factory=list)

    # Entidades conhecidas
    entities: Dict[str, List[str]] = field(default_factory=dict)

    # Intents que o agente pode tratar
    supported_intents: List[str] = field(default_factory=list)

    # Padrões de resposta
    response_templates: Dict[str, str] = field(default_factory=dict)

    def get_knowledge(self, key: str) -> Any:
        """Retorna conhecimento específico"""
        return self.knowledge_base.get(key)

    def add_procedure(self, procedure: Dict[str, Any]):
        """Adiciona procedimento"""
        self.procedures.append(procedure)

    def find_procedure(self, intent: str) -> Optional[Dict]:
        """Encontra procedimento por intent"""
        for proc in self.procedures:
            if proc.get("intent") == intent:
                return proc
        return None

    def get_faq_answer(self, question: str) -> Optional[str]:
        """Busca resposta no FAQ"""
        question_lower = question.lower()
        for item in self.faq:
            keywords = item.get("keywords", [])
            if any(kw in question_lower for kw in keywords):
                return item.get("answer")
        return None


@dataclass
class SpecializedAgentConfig:
    """Configuração de agente especializado"""
    domain: SpecializedDomain
    name: str
    description: str

    # Capacidades
    capabilities: List[AgentCapability] = field(default_factory=list)

    # Ferramentas permitidas
    allowed_tools: List[str] = field(default_factory=list)

    # Limites
    max_concurrent_tasks: int = 5
    task_timeout_seconds: int = 300
    max_retries: int = 3

    # Comportamento
    auto_escalate: bool = True
    require_approval_for: List[str] = field(default_factory=list)
    notify_on: List[str] = field(default_factory=list)

    # Horário de funcionamento
    active_hours_start: int = 0  # 0-23
    active_hours_end: int = 24
    active_days: List[int] = field(default_factory=lambda: [0, 1, 2, 3, 4, 5, 6])

    # Prioridade
    priority: int = 5  # 1-10

    # Prompts customizados
    system_prompt_additions: str = ""
    greeting_template: str = ""


@dataclass
class SpecializedContext:
    """Contexto de execução especializado"""
    domain: SpecializedDomain
    condominio_id: str
    agent_id: str

    # Identificação
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    conversation_id: Optional[str] = None

    # Entidade em foco
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None

    # Estado da conversa
    current_intent: Optional[str] = None
    intent_confidence: float = 0.0
    extracted_entities: Dict[str, Any] = field(default_factory=dict)
    pending_confirmations: List[str] = field(default_factory=list)

    # Histórico
    actions_taken: List[Dict] = field(default_factory=list)

    # Permissões
    user_permissions: List[str] = field(default_factory=list)

    # Metadados
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def has_permission(self, permission: str) -> bool:
        """Verifica permissão do usuário"""
        return permission in self.user_permissions or "admin" in self.user_permissions

    def record_action(self, action: str, details: Dict = None):
        """Registra ação tomada"""
        self.actions_taken.append({
            "action": action,
            "details": details or {},
            "timestamp": datetime.now().isoformat()
        })

    def needs_confirmation(self, action: str) -> bool:
        """Verifica se ação precisa de confirmação"""
        return action in self.pending_confirmations

    def confirm_action(self, action: str):
        """Confirma ação pendente"""
        if action in self.pending_confirmations:
            self.pending_confirmations.remove(action)


@dataclass
class AgentResponse:
    """Resposta do agente especializado"""
    message: str
    intent_handled: Optional[str] = None
    actions_executed: List[Dict] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    requires_input: bool = False
    input_type: Optional[str] = None  # text, choice, confirmation
    choices: List[str] = field(default_factory=list)
    attachments: List[Dict] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    should_escalate: bool = False
    escalation_reason: Optional[str] = None


class BaseSpecializedAgent(ABC):
    """
    Classe base para agentes especializados.

    Agentes especializados implementam lógica específica de domínio
    e podem usar conhecimento especializado para responder.
    """

    def __init__(self, config: SpecializedAgentConfig):
        self.config = config
        self.domain = config.domain
        self.name = config.name

        # Conhecimento de domínio
        self._knowledge: Optional[DomainKnowledge] = None

        # Estado
        self._active_tasks: Dict[str, Dict] = {}
        self._initialized = False

        # Callbacks
        self._on_action_callbacks: List[Callable] = []
        self._on_escalate_callbacks: List[Callable] = []

        # Métricas
        self._metrics = {
            "tasks_handled": 0,
            "tasks_escalated": 0,
            "avg_response_time_ms": 0,
            "success_rate": 1.0
        }

    @property
    @abstractmethod
    def knowledge(self) -> DomainKnowledge:
        """Retorna conhecimento de domínio do agente"""
        pass

    @abstractmethod
    async def handle_intent(
        self,
        intent: str,
        context: SpecializedContext,
        entities: Dict[str, Any]
    ) -> AgentResponse:
        """Processa intent específico do domínio"""
        pass

    @abstractmethod
    async def execute_action(
        self,
        action: str,
        context: SpecializedContext,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Executa ação específica do domínio"""
        pass

    async def initialize(self) -> bool:
        """Inicializa o agente"""
        try:
            self._knowledge = self.knowledge
            await self._on_initialize()
            self._initialized = True
            logger.info(f"Agente {self.name} inicializado")
            return True
        except Exception as e:
            logger.error(f"Erro ao inicializar {self.name}: {e}")
            return False

    async def _on_initialize(self):
        """Override para inicialização customizada"""
        pass

    async def shutdown(self):
        """Desliga o agente"""
        await self._on_shutdown()
        self._initialized = False
        logger.info(f"Agente {self.name} desligado")

    async def _on_shutdown(self):
        """Override para shutdown customizado"""
        pass

    async def process_message(
        self,
        message: str,
        context: SpecializedContext
    ) -> AgentResponse:
        """
        Processa mensagem do usuário.
        """
        if not self._initialized:
            await self.initialize()

        # Detectar intent
        intent, confidence, entities = await self._detect_intent(message, context)

        context.current_intent = intent
        context.intent_confidence = confidence
        context.extracted_entities.update(entities)

        # Verificar se consegue tratar
        if not self._can_handle_intent(intent):
            return await self._escalate(context, f"Intent não suportado: {intent}")

        # Verificar procedimento
        procedure = self._knowledge.find_procedure(intent)
        if procedure:
            return await self._execute_procedure(procedure, context)

        # Processar intent
        return await self.handle_intent(intent, context, entities)

    async def _detect_intent(
        self,
        message: str,
        context: SpecializedContext
    ) -> tuple[str, float, Dict]:
        """Detecta intent e entidades da mensagem"""
        message_lower = message.lower()

        # Buscar em intents suportados
        for intent in self._knowledge.supported_intents:
            intent_keywords = self._get_intent_keywords(intent)
            if any(kw in message_lower for kw in intent_keywords):
                entities = self._extract_entities(message)
                return intent, 0.85, entities

        # Default: intent genérico
        return "unknown", 0.3, {}

    def _get_intent_keywords(self, intent: str) -> List[str]:
        """Retorna palavras-chave para um intent"""
        intent_map = {
            "saudacao": ["olá", "oi", "bom dia", "boa tarde", "boa noite"],
            "despedida": ["tchau", "até logo", "adeus", "obrigado"],
            "ajuda": ["ajuda", "help", "preciso de ajuda", "como funciona"],
            "reclamacao": ["reclamação", "reclamar", "problema", "não funciona"],
            "solicitacao": ["solicitar", "quero", "preciso", "gostaria"],
            "consulta": ["consultar", "verificar", "como está", "qual"],
            "cancelamento": ["cancelar", "desistir", "não quero mais"],
            "agendamento": ["agendar", "marcar", "reservar"],
        }
        return intent_map.get(intent, [intent])

    def _extract_entities(self, message: str) -> Dict[str, Any]:
        """Extrai entidades da mensagem"""
        import re

        entities = {}

        # Unidade (ex: 101A, 102-B)
        unit_match = re.search(r'\b(\d{2,4}[A-Za-z]?(-[A-Za-z])?)\b', message)
        if unit_match:
            entities["unidade"] = unit_match.group(1)

        # Data (ex: 25/12, 25/12/2024)
        date_match = re.search(r'\b(\d{1,2}/\d{1,2}(/\d{2,4})?)\b', message)
        if date_match:
            entities["data"] = date_match.group(1)

        # Horário (ex: 14:30, 14h30)
        time_match = re.search(r'\b(\d{1,2}[h:]\d{2})\b', message)
        if time_match:
            entities["horario"] = time_match.group(1)

        # Valor monetário
        money_match = re.search(r'R?\$?\s*(\d+[.,]?\d*)', message)
        if money_match:
            entities["valor"] = money_match.group(1)

        # Placa de veículo
        plate_match = re.search(r'\b([A-Za-z]{3}[-]?\d[A-Za-z\d]\d{2})\b', message)
        if plate_match:
            entities["placa"] = plate_match.group(1).upper()

        return entities

    def _can_handle_intent(self, intent: str) -> bool:
        """Verifica se agente pode tratar o intent"""
        return intent in self._knowledge.supported_intents or intent == "unknown"

    async def _execute_procedure(
        self,
        procedure: Dict,
        context: SpecializedContext
    ) -> AgentResponse:
        """Executa procedimento definido"""
        steps = procedure.get("steps", [])
        results = []

        for step in steps:
            step_type = step.get("type")
            step_action = step.get("action")

            if step_type == "action":
                result = await self.execute_action(step_action, context, step.get("params", {}))
                results.append(result)

            elif step_type == "message":
                # Retornar mensagem e aguardar resposta
                return AgentResponse(
                    message=step.get("message", ""),
                    requires_input=True,
                    input_type=step.get("input_type", "text")
                )

            elif step_type == "condition":
                # Avaliar condição
                condition_met = self._evaluate_condition(step.get("condition"), context)
                if not condition_met:
                    break

        return AgentResponse(
            message=procedure.get("completion_message", "Procedimento concluído."),
            actions_executed=results
        )

    def _evaluate_condition(self, condition: str, context: SpecializedContext) -> bool:
        """Avalia condição"""
        # Implementação simplificada
        return True

    async def _escalate(
        self,
        context: SpecializedContext,
        reason: str
    ) -> AgentResponse:
        """Escalona para atendimento humano ou outro agente"""
        self._metrics["tasks_escalated"] += 1

        # Notificar callbacks
        for callback in self._on_escalate_callbacks:
            await callback(context, reason)

        return AgentResponse(
            message="Vou transferir você para um atendente especializado.",
            should_escalate=True,
            escalation_reason=reason
        )

    def can_execute_action(self, action: str, context: SpecializedContext) -> bool:
        """Verifica se agente pode executar ação"""
        # Verificar capacidades
        action_capability_map = {
            "read": AgentCapability.READ,
            "write": AgentCapability.WRITE,
            "execute": AgentCapability.EXECUTE,
            "approve": AgentCapability.APPROVE,
            "notify": AgentCapability.NOTIFY
        }

        action_type = action.split("_")[0] if "_" in action else "execute"
        required_cap = action_capability_map.get(action_type, AgentCapability.EXECUTE)

        if required_cap not in self.config.capabilities:
            return False

        # Verificar se ação requer aprovação
        if action in self.config.require_approval_for:
            return context.has_permission("approve")

        return True

    def is_active(self) -> bool:
        """Verifica se agente está ativo (horário de funcionamento)"""
        now = datetime.now()

        # Verificar dia da semana
        if now.weekday() not in self.config.active_days:
            return False

        # Verificar horário
        if not (self.config.active_hours_start <= now.hour < self.config.active_hours_end):
            return False

        return True

    def on_action(self, callback: Callable):
        """Registra callback para ações"""
        self._on_action_callbacks.append(callback)

    def on_escalate(self, callback: Callable):
        """Registra callback para escalonamentos"""
        self._on_escalate_callbacks.append(callback)

    def get_greeting(self, context: SpecializedContext) -> str:
        """Retorna saudação do agente"""
        if self.config.greeting_template:
            return self.config.greeting_template

        hour = datetime.now().hour
        if hour < 12:
            period = "Bom dia"
        elif hour < 18:
            period = "Boa tarde"
        else:
            period = "Boa noite"

        return f"{period}! Sou o {self.name}, como posso ajudar?"

    def get_faq_response(self, question: str) -> Optional[str]:
        """Busca resposta no FAQ do domínio"""
        if self._knowledge:
            return self._knowledge.get_faq_answer(question)
        return None

    @property
    def metrics(self) -> Dict[str, Any]:
        """Retorna métricas do agente"""
        return {
            **self._metrics,
            "active_tasks": len(self._active_tasks),
            "initialized": self._initialized
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serializa agente para dict"""
        return {
            "name": self.name,
            "domain": self.domain.value,
            "description": self.config.description,
            "capabilities": [c.value for c in self.config.capabilities],
            "active": self.is_active(),
            "initialized": self._initialized,
            "metrics": self.metrics
        }
