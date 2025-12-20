"""
Conecta Plus - Conversation Memory
Memória especializada para conversas e diálogos

Funcionalidades:
- Armazenamento de turnos de conversa
- Sumarização automática de conversas longas
- Detecção de tópicos e intenções
- Análise de sentimento por conversa
- Recuperação de conversas anteriores por contexto
"""

import asyncio
import json
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


class MessageRole(Enum):
    """Papel do autor da mensagem"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class ConversationStatus(Enum):
    """Status da conversa"""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    ESCALATED = "escalated"


class Sentiment(Enum):
    """Sentimento detectado"""
    VERY_NEGATIVE = -2
    NEGATIVE = -1
    NEUTRAL = 0
    POSITIVE = 1
    VERY_POSITIVE = 2


class Intent(Enum):
    """Intenções comuns"""
    QUESTION = "question"
    REQUEST = "request"
    COMPLAINT = "complaint"
    FEEDBACK = "feedback"
    GREETING = "greeting"
    FAREWELL = "farewell"
    CONFIRMATION = "confirmation"
    NEGATION = "negation"
    CLARIFICATION = "clarification"
    EMERGENCY = "emergency"
    INFORMATION = "information"
    UNKNOWN = "unknown"


@dataclass
class ConversationTurn:
    """Um turno de conversa (mensagem + resposta)"""
    turn_id: str
    conversation_id: str
    role: MessageRole
    content: str
    timestamp: datetime = field(default_factory=datetime.now)

    # Análise
    intent: Optional[Intent] = None
    sentiment: Sentiment = Sentiment.NEUTRAL
    topics: List[str] = field(default_factory=list)
    entities_mentioned: List[str] = field(default_factory=list)

    # Metadados
    tokens: int = 0
    processing_time_ms: int = 0
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "turn_id": self.turn_id,
            "conversation_id": self.conversation_id,
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "intent": self.intent.value if self.intent else None,
            "sentiment": self.sentiment.value,
            "topics": self.topics,
            "entities_mentioned": self.entities_mentioned,
            "tokens": self.tokens,
            "processing_time_ms": self.processing_time_ms,
            "tool_calls": self.tool_calls,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationTurn":
        return cls(
            turn_id=data["turn_id"],
            conversation_id=data["conversation_id"],
            role=MessageRole(data["role"]),
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            intent=Intent(data["intent"]) if data.get("intent") else None,
            sentiment=Sentiment(data.get("sentiment", 0)),
            topics=data.get("topics", []),
            entities_mentioned=data.get("entities_mentioned", []),
            tokens=data.get("tokens", 0),
            processing_time_ms=data.get("processing_time_ms", 0),
            tool_calls=data.get("tool_calls", []),
            metadata=data.get("metadata", {}),
        )


@dataclass
class ConversationSummary:
    """Resumo de uma conversa"""
    conversation_id: str
    summary: str
    key_points: List[str] = field(default_factory=list)
    action_items: List[str] = field(default_factory=list)
    unresolved_issues: List[str] = field(default_factory=list)
    main_topics: List[str] = field(default_factory=list)
    overall_sentiment: Sentiment = Sentiment.NEUTRAL
    resolution_status: str = "pending"
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "summary": self.summary,
            "key_points": self.key_points,
            "action_items": self.action_items,
            "unresolved_issues": self.unresolved_issues,
            "main_topics": self.main_topics,
            "overall_sentiment": self.overall_sentiment.value,
            "resolution_status": self.resolution_status,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class ConversationAnalytics:
    """Analytics de uma conversa"""
    conversation_id: str
    total_turns: int = 0
    total_tokens: int = 0
    avg_response_time_ms: float = 0
    user_messages: int = 0
    assistant_messages: int = 0
    tool_calls: int = 0

    # Sentimento ao longo do tempo
    sentiment_progression: List[int] = field(default_factory=list)
    sentiment_start: Sentiment = Sentiment.NEUTRAL
    sentiment_end: Sentiment = Sentiment.NEUTRAL
    sentiment_improved: bool = False

    # Tópicos
    topics_discussed: List[str] = field(default_factory=list)
    topic_frequency: Dict[str, int] = field(default_factory=dict)

    # Eficiência
    resolution_achieved: bool = False
    escalation_needed: bool = False
    first_response_time_ms: int = 0

    # Duração
    duration_seconds: int = 0
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "total_turns": self.total_turns,
            "total_tokens": self.total_tokens,
            "avg_response_time_ms": self.avg_response_time_ms,
            "user_messages": self.user_messages,
            "assistant_messages": self.assistant_messages,
            "tool_calls": self.tool_calls,
            "sentiment_improved": self.sentiment_improved,
            "topics_discussed": self.topics_discussed,
            "resolution_achieved": self.resolution_achieved,
            "escalation_needed": self.escalation_needed,
            "duration_seconds": self.duration_seconds,
        }


@dataclass
class Conversation:
    """Representa uma conversa completa"""
    conversation_id: str
    agent_id: str
    user_id: Optional[str] = None
    channel: str = "chat"  # chat, whatsapp, voice, email

    # Estado
    status: ConversationStatus = ConversationStatus.ACTIVE
    turns: List[ConversationTurn] = field(default_factory=list)

    # Contexto
    context: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    category: Optional[str] = None
    priority: int = 1  # 1-5

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    closed_at: Optional[datetime] = None

    # Relacionamentos
    parent_conversation_id: Optional[str] = None
    related_conversations: List[str] = field(default_factory=list)
    ticket_id: Optional[str] = None

    # Analytics e resumo
    summary: Optional[ConversationSummary] = None
    analytics: Optional[ConversationAnalytics] = None

    def add_turn(self, role: MessageRole, content: str, **kwargs) -> ConversationTurn:
        """Adiciona um turno à conversa"""
        turn = ConversationTurn(
            turn_id=f"{self.conversation_id}_turn_{len(self.turns)}",
            conversation_id=self.conversation_id,
            role=role,
            content=content,
            **kwargs
        )
        self.turns.append(turn)
        self.updated_at = datetime.now()
        return turn

    def get_messages_for_llm(self, max_turns: int = None) -> List[Dict[str, str]]:
        """Retorna mensagens formatadas para LLM"""
        turns = self.turns[-max_turns:] if max_turns else self.turns
        return [
            {"role": t.role.value, "content": t.content}
            for t in turns
            if t.role in [MessageRole.USER, MessageRole.ASSISTANT, MessageRole.SYSTEM]
        ]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "agent_id": self.agent_id,
            "user_id": self.user_id,
            "channel": self.channel,
            "status": self.status.value,
            "turns": [t.to_dict() for t in self.turns],
            "context": self.context,
            "tags": self.tags,
            "category": self.category,
            "priority": self.priority,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
            "summary": self.summary.to_dict() if self.summary else None,
            "analytics": self.analytics.to_dict() if self.analytics else None,
        }


class ConversationMemory:
    """
    Sistema de memória para conversas.
    Gerencia armazenamento, busca e análise de conversas.
    """

    def __init__(
        self,
        redis_client=None,
        vector_store=None,
        llm_client=None,
        max_active_conversations: int = 1000,
        summarize_after_turns: int = 20,
    ):
        self.redis = redis_client
        self.vector_store = vector_store
        self.llm = llm_client
        self.max_active = max_active_conversations
        self.summarize_threshold = summarize_after_turns

        # Cache em memória para conversas ativas
        self._active_conversations: Dict[str, Conversation] = {}

        # Índices
        self._user_conversations: Dict[str, List[str]] = defaultdict(list)
        self._agent_conversations: Dict[str, List[str]] = defaultdict(list)

    # ========================================================================
    # GESTÃO DE CONVERSAS
    # ========================================================================

    def start_conversation(
        self,
        agent_id: str,
        user_id: Optional[str] = None,
        channel: str = "chat",
        context: Dict[str, Any] = None,
        **kwargs
    ) -> Conversation:
        """Inicia uma nova conversa"""
        conversation_id = self._generate_conversation_id(agent_id)

        conversation = Conversation(
            conversation_id=conversation_id,
            agent_id=agent_id,
            user_id=user_id,
            channel=channel,
            context=context or {},
            **kwargs
        )

        # Adicionar aos índices
        self._active_conversations[conversation_id] = conversation
        self._agent_conversations[agent_id].append(conversation_id)
        if user_id:
            self._user_conversations[user_id].append(conversation_id)

        # Limpar cache se muito grande
        if len(self._active_conversations) > self.max_active:
            self._cleanup_old_conversations()

        logger.info(f"Conversa iniciada: {conversation_id}")
        return conversation

    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Recupera uma conversa pelo ID"""
        # Primeiro verificar cache
        if conversation_id in self._active_conversations:
            return self._active_conversations[conversation_id]

        # Se não estiver no cache, buscar no storage
        return asyncio.get_event_loop().run_until_complete(
            self._load_conversation(conversation_id)
        )

    async def _load_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Carrega conversa do storage"""
        if self.redis:
            data = await self.redis.get(f"conversation:{conversation_id}")
            if data:
                return self._deserialize_conversation(json.loads(data))
        return None

    def add_message(
        self,
        conversation_id: str,
        role: MessageRole,
        content: str,
        **kwargs
    ) -> Optional[ConversationTurn]:
        """Adiciona mensagem a uma conversa"""
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            logger.warning(f"Conversa não encontrada: {conversation_id}")
            return None

        turn = conversation.add_turn(role, content, **kwargs)

        # Verificar se precisa sumarizar
        if len(conversation.turns) % self.summarize_threshold == 0:
            asyncio.create_task(self._auto_summarize(conversation))

        return turn

    async def close_conversation(
        self,
        conversation_id: str,
        status: ConversationStatus = ConversationStatus.COMPLETED,
        resolution: str = None
    ) -> Optional[Conversation]:
        """Fecha uma conversa"""
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return None

        conversation.status = status
        conversation.closed_at = datetime.now()

        if resolution:
            conversation.context["resolution"] = resolution

        # Gerar resumo final
        await self._generate_summary(conversation)

        # Calcular analytics
        self._calculate_analytics(conversation)

        # Persistir
        await self._save_conversation(conversation)

        # Indexar no vector store para busca futura
        if self.vector_store:
            await self._index_conversation(conversation)

        # Remover do cache ativo
        if conversation_id in self._active_conversations:
            del self._active_conversations[conversation_id]

        logger.info(f"Conversa fechada: {conversation_id} - Status: {status.value}")
        return conversation

    async def escalate_conversation(
        self,
        conversation_id: str,
        reason: str,
        to_agent: str = None
    ) -> bool:
        """Escala uma conversa para outro agente/humano"""
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return False

        conversation.status = ConversationStatus.ESCALATED
        conversation.context["escalation"] = {
            "reason": reason,
            "to_agent": to_agent,
            "timestamp": datetime.now().isoformat()
        }
        conversation.tags.append("escalated")

        await self._save_conversation(conversation)
        return True

    # ========================================================================
    # BUSCA E RECUPERAÇÃO
    # ========================================================================

    async def search_conversations(
        self,
        agent_id: str,
        query: str,
        limit: int = 10,
        filters: Dict[str, Any] = None
    ) -> List[Conversation]:
        """Busca conversas por similaridade semântica"""
        if not self.vector_store:
            return []

        results = await self.vector_store.search(
            agent_id=agent_id,
            query=query,
            limit=limit,
            filter_metadata={"type": "conversation", **(filters or {})}
        )

        conversations = []
        for result in results:
            conv_id = result.get("metadata", {}).get("conversation_id")
            if conv_id:
                conv = await self._load_conversation(conv_id)
                if conv:
                    conversations.append(conv)

        return conversations

    async def get_user_history(
        self,
        user_id: str,
        limit: int = 10,
        include_active: bool = True
    ) -> List[Conversation]:
        """Recupera histórico de conversas de um usuário"""
        conversation_ids = self._user_conversations.get(user_id, [])

        # Buscar também no storage
        if self.redis:
            stored_ids = await self.redis.smembers(f"user_conversations:{user_id}")
            conversation_ids = list(set(conversation_ids) | set(stored_ids or []))

        conversations = []
        for conv_id in conversation_ids[-limit:]:
            conv = await self._load_conversation(conv_id)
            if conv:
                if include_active or conv.status != ConversationStatus.ACTIVE:
                    conversations.append(conv)

        return sorted(conversations, key=lambda c: c.created_at, reverse=True)

    async def get_similar_past_conversations(
        self,
        conversation_id: str,
        limit: int = 5
    ) -> List[Tuple[Conversation, float]]:
        """Encontra conversas passadas similares à atual"""
        conversation = self.get_conversation(conversation_id)
        if not conversation or not self.vector_store:
            return []

        # Criar query a partir do conteúdo da conversa
        content = " ".join([t.content for t in conversation.turns[-5:]])

        results = await self.vector_store.search(
            agent_id=conversation.agent_id,
            query=content,
            limit=limit + 1,  # +1 para excluir a própria conversa
            filter_metadata={"type": "conversation"}
        )

        similar = []
        for result in results:
            conv_id = result.get("metadata", {}).get("conversation_id")
            if conv_id and conv_id != conversation_id:
                conv = await self._load_conversation(conv_id)
                if conv:
                    distance = result.get("distance", 0)
                    similar.append((conv, 1 - distance))  # Converter para similaridade

        return similar[:limit]

    # ========================================================================
    # ANÁLISE E SUMARIZAÇÃO
    # ========================================================================

    async def _generate_summary(self, conversation: Conversation) -> ConversationSummary:
        """Gera resumo da conversa usando LLM"""
        if not self.llm:
            # Fallback: resumo básico
            summary = ConversationSummary(
                conversation_id=conversation.conversation_id,
                summary=f"Conversa com {len(conversation.turns)} mensagens",
                main_topics=list(set(
                    topic for turn in conversation.turns for topic in turn.topics
                ))
            )
            conversation.summary = summary
            return summary

        # Preparar contexto para LLM
        messages_text = "\n".join([
            f"{t.role.value}: {t.content}"
            for t in conversation.turns
        ])

        prompt = f"""Analise a seguinte conversa e gere um resumo estruturado:

{messages_text}

Forneça:
1. Resumo em 2-3 frases
2. Pontos principais (lista)
3. Itens de ação pendentes (se houver)
4. Problemas não resolvidos (se houver)
5. Tópicos principais
6. Status de resolução (resolvido, parcial, não resolvido)

Responda em JSON."""

        try:
            response = await self.llm.generate(
                system_prompt="Você é um assistente de análise de conversas.",
                user_message=prompt,
                response_format="json"
            )

            data = json.loads(response)
            summary = ConversationSummary(
                conversation_id=conversation.conversation_id,
                summary=data.get("summary", ""),
                key_points=data.get("key_points", []),
                action_items=data.get("action_items", []),
                unresolved_issues=data.get("unresolved_issues", []),
                main_topics=data.get("main_topics", []),
                resolution_status=data.get("resolution_status", "pending")
            )

        except Exception as e:
            logger.error(f"Erro ao gerar resumo: {e}")
            summary = ConversationSummary(
                conversation_id=conversation.conversation_id,
                summary=f"Conversa com {len(conversation.turns)} mensagens"
            )

        conversation.summary = summary
        return summary

    async def _auto_summarize(self, conversation: Conversation):
        """Sumarização automática para conversas longas"""
        if len(conversation.turns) < self.summarize_threshold:
            return

        # Sumarizar turnos antigos
        old_turns = conversation.turns[:-10]  # Manter últimos 10

        if not old_turns:
            return

        if self.llm:
            messages_text = "\n".join([
                f"{t.role.value}: {t.content}"
                for t in old_turns
            ])

            prompt = f"Resuma brevemente esta parte da conversa em 2-3 frases:\n\n{messages_text}"

            try:
                summary = await self.llm.generate(
                    system_prompt="Seja conciso.",
                    user_message=prompt
                )

                # Criar turno de sistema com o resumo
                system_turn = ConversationTurn(
                    turn_id=f"{conversation.conversation_id}_summary_{len(conversation.turns)}",
                    conversation_id=conversation.conversation_id,
                    role=MessageRole.SYSTEM,
                    content=f"[Resumo do histórico anterior: {summary}]",
                    metadata={"is_summary": True, "summarized_turns": len(old_turns)}
                )

                # Substituir turnos antigos pelo resumo
                conversation.turns = [system_turn] + conversation.turns[-10:]

            except Exception as e:
                logger.error(f"Erro na sumarização automática: {e}")

    def _calculate_analytics(self, conversation: Conversation):
        """Calcula analytics da conversa"""
        analytics = ConversationAnalytics(
            conversation_id=conversation.conversation_id,
            total_turns=len(conversation.turns),
            started_at=conversation.created_at,
            ended_at=conversation.closed_at or datetime.now()
        )

        response_times = []
        sentiments = []
        topics = []

        for i, turn in enumerate(conversation.turns):
            # Contar por tipo
            if turn.role == MessageRole.USER:
                analytics.user_messages += 1
            elif turn.role == MessageRole.ASSISTANT:
                analytics.assistant_messages += 1

            # Tokens
            analytics.total_tokens += turn.tokens

            # Tool calls
            analytics.tool_calls += len(turn.tool_calls)

            # Response time
            if turn.processing_time_ms > 0:
                response_times.append(turn.processing_time_ms)

            # Sentimento
            sentiments.append(turn.sentiment.value)

            # Tópicos
            topics.extend(turn.topics)

        # Calcular médias
        if response_times:
            analytics.avg_response_time_ms = sum(response_times) / len(response_times)
            analytics.first_response_time_ms = response_times[0] if response_times else 0

        # Progressão de sentimento
        analytics.sentiment_progression = sentiments
        if sentiments:
            analytics.sentiment_start = Sentiment(sentiments[0])
            analytics.sentiment_end = Sentiment(sentiments[-1])
            analytics.sentiment_improved = sentiments[-1] > sentiments[0]

        # Tópicos
        analytics.topics_discussed = list(set(topics))
        for topic in topics:
            analytics.topic_frequency[topic] = analytics.topic_frequency.get(topic, 0) + 1

        # Duração
        if analytics.ended_at and analytics.started_at:
            analytics.duration_seconds = int(
                (analytics.ended_at - analytics.started_at).total_seconds()
            )

        # Status
        analytics.resolution_achieved = conversation.status == ConversationStatus.COMPLETED
        analytics.escalation_needed = conversation.status == ConversationStatus.ESCALATED

        conversation.analytics = analytics

    # ========================================================================
    # ANÁLISE DE MENSAGENS
    # ========================================================================

    async def analyze_message(
        self,
        content: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Analisa uma mensagem individual"""
        analysis = {
            "intent": Intent.UNKNOWN,
            "sentiment": Sentiment.NEUTRAL,
            "topics": [],
            "entities": [],
            "urgency": 1,
            "requires_action": False
        }

        # Detecção básica de intenção
        content_lower = content.lower()

        if any(w in content_lower for w in ["?", "como", "qual", "quando", "onde", "por que"]):
            analysis["intent"] = Intent.QUESTION
        elif any(w in content_lower for w in ["preciso", "quero", "gostaria", "pode"]):
            analysis["intent"] = Intent.REQUEST
        elif any(w in content_lower for w in ["problema", "erro", "não funciona", "reclamação"]):
            analysis["intent"] = Intent.COMPLAINT
            analysis["urgency"] = 3
        elif any(w in content_lower for w in ["olá", "oi", "bom dia", "boa tarde", "boa noite"]):
            analysis["intent"] = Intent.GREETING
        elif any(w in content_lower for w in ["tchau", "obrigado", "até logo", "valeu"]):
            analysis["intent"] = Intent.FAREWELL
        elif any(w in content_lower for w in ["urgente", "emergência", "socorro", "ajuda"]):
            analysis["intent"] = Intent.EMERGENCY
            analysis["urgency"] = 5
            analysis["requires_action"] = True
        elif any(w in content_lower for w in ["sim", "correto", "isso", "exato"]):
            analysis["intent"] = Intent.CONFIRMATION
        elif any(w in content_lower for w in ["não", "errado", "negativo"]):
            analysis["intent"] = Intent.NEGATION

        # Detecção básica de sentimento
        positive_words = ["obrigado", "ótimo", "excelente", "perfeito", "bom", "legal", "parabéns"]
        negative_words = ["péssimo", "horrível", "ruim", "terrível", "absurdo", "inaceitável"]

        pos_count = sum(1 for w in positive_words if w in content_lower)
        neg_count = sum(1 for w in negative_words if w in content_lower)

        if neg_count > pos_count:
            analysis["sentiment"] = Sentiment.NEGATIVE if neg_count == 1 else Sentiment.VERY_NEGATIVE
        elif pos_count > neg_count:
            analysis["sentiment"] = Sentiment.POSITIVE if pos_count == 1 else Sentiment.VERY_POSITIVE

        # Se tiver LLM, fazer análise mais profunda
        if self.llm and len(content) > 50:
            try:
                llm_analysis = await self._llm_analyze_message(content, context)
                analysis.update(llm_analysis)
            except Exception as e:
                logger.debug(f"Análise LLM falhou: {e}")

        return analysis

    async def _llm_analyze_message(
        self,
        content: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Análise avançada usando LLM"""
        prompt = f"""Analise a seguinte mensagem de um usuário:

"{content}"

Contexto: {json.dumps(context or {})}

Responda em JSON com:
- intent: intenção principal (question, request, complaint, feedback, greeting, farewell, emergency, information, unknown)
- sentiment: sentimento (-2 muito negativo, -1 negativo, 0 neutro, 1 positivo, 2 muito positivo)
- topics: lista de tópicos mencionados
- entities: entidades mencionadas (pessoas, lugares, datas, valores)
- urgency: nível de urgência (1-5)
- requires_action: se requer ação imediata (true/false)
"""

        response = await self.llm.generate(
            system_prompt="Você analisa mensagens. Responda apenas em JSON válido.",
            user_message=prompt,
            response_format="json"
        )

        return json.loads(response)

    # ========================================================================
    # PERSISTÊNCIA
    # ========================================================================

    async def _save_conversation(self, conversation: Conversation):
        """Salva conversa no storage"""
        if self.redis:
            data = json.dumps(conversation.to_dict())
            await self.redis.set(
                f"conversation:{conversation.conversation_id}",
                data
            )

            # Atualizar índices
            if conversation.user_id:
                await self.redis.sadd(
                    f"user_conversations:{conversation.user_id}",
                    conversation.conversation_id
                )

            await self.redis.sadd(
                f"agent_conversations:{conversation.agent_id}",
                conversation.conversation_id
            )

    async def _index_conversation(self, conversation: Conversation):
        """Indexa conversa no vector store para busca"""
        if not self.vector_store:
            return

        # Criar texto pesquisável
        content_parts = []

        if conversation.summary:
            content_parts.append(conversation.summary.summary)
            content_parts.extend(conversation.summary.key_points)

        # Adicionar últimas mensagens do usuário
        user_messages = [
            t.content for t in conversation.turns
            if t.role == MessageRole.USER
        ][-5:]
        content_parts.extend(user_messages)

        searchable_content = " ".join(content_parts)

        await self.vector_store.store(
            agent_id=conversation.agent_id,
            content=searchable_content,
            metadata={
                "type": "conversation",
                "conversation_id": conversation.conversation_id,
                "user_id": conversation.user_id,
                "status": conversation.status.value,
                "category": conversation.category,
                "tags": conversation.tags,
            }
        )

    # ========================================================================
    # UTILITÁRIOS
    # ========================================================================

    def _generate_conversation_id(self, agent_id: str) -> str:
        """Gera ID único para conversa"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        hash_input = f"{agent_id}:{timestamp}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]

    def _cleanup_old_conversations(self):
        """Remove conversas antigas do cache"""
        # Ordenar por última atualização
        sorted_convs = sorted(
            self._active_conversations.items(),
            key=lambda x: x[1].updated_at
        )

        # Remover metade mais antiga
        to_remove = len(sorted_convs) // 2
        for conv_id, _ in sorted_convs[:to_remove]:
            if self._active_conversations[conv_id].status != ConversationStatus.ACTIVE:
                del self._active_conversations[conv_id]

    def _deserialize_conversation(self, data: Dict[str, Any]) -> Conversation:
        """Deserializa conversa do JSON"""
        conversation = Conversation(
            conversation_id=data["conversation_id"],
            agent_id=data["agent_id"],
            user_id=data.get("user_id"),
            channel=data.get("channel", "chat"),
            status=ConversationStatus(data.get("status", "active")),
            context=data.get("context", {}),
            tags=data.get("tags", []),
            category=data.get("category"),
            priority=data.get("priority", 1),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
        )

        # Deserializar turnos
        for turn_data in data.get("turns", []):
            conversation.turns.append(ConversationTurn.from_dict(turn_data))

        return conversation

    # ========================================================================
    # MÉTRICAS E ESTATÍSTICAS
    # ========================================================================

    def get_agent_stats(self, agent_id: str) -> Dict[str, Any]:
        """Retorna estatísticas do agente"""
        conversations = [
            c for c in self._active_conversations.values()
            if c.agent_id == agent_id
        ]

        return {
            "active_conversations": len([c for c in conversations if c.status == ConversationStatus.ACTIVE]),
            "total_conversations": len(conversations),
            "avg_turns": sum(len(c.turns) for c in conversations) / max(len(conversations), 1),
            "channels": list(set(c.channel for c in conversations)),
        }

    async def get_daily_summary(self, agent_id: str, date: datetime = None) -> Dict[str, Any]:
        """Retorna resumo diário de conversas"""
        date = date or datetime.now()
        start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)

        # Buscar conversas do dia
        conversations = [
            c for c in self._active_conversations.values()
            if c.agent_id == agent_id and start <= c.created_at < end
        ]

        completed = [c for c in conversations if c.status == ConversationStatus.COMPLETED]
        escalated = [c for c in conversations if c.status == ConversationStatus.ESCALATED]

        return {
            "date": date.strftime("%Y-%m-%d"),
            "total_conversations": len(conversations),
            "completed": len(completed),
            "escalated": len(escalated),
            "completion_rate": len(completed) / max(len(conversations), 1) * 100,
            "avg_duration_minutes": sum(
                (c.closed_at - c.created_at).total_seconds() / 60
                for c in completed if c.closed_at
            ) / max(len(completed), 1),
        }
