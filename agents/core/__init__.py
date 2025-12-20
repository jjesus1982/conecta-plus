"""
Conecta Plus - Core Agent Framework
Framework de agentes IA com evolução em 7 níveis

Módulos:
- base_agent: Classe base para todos os agentes
- memory_store: Sistema de memória (Redis, Vector DB, Episódica)
- llm_client: Cliente unificado para LLMs (Claude, GPT, Ollama)
- rag_system: Sistema de Retrieval Augmented Generation
"""

from .base_agent import (
    BaseAgent,
    EvolutionLevel,
    Priority,
    AgentCapability,
    AgentContext,
    AgentMessage,
    AgentAction,
    AgentPrediction,
    AgentState,
)

from .memory_store import (
    MemoryItem,
    Episode,
    BaseMemoryStore,
    RedisMemoryStore,
    VectorMemoryStore,
    EpisodicMemory,
    WorkingMemory,
    UnifiedMemorySystem,
)

from .llm_client import (
    LLMProvider,
    LLMMessage,
    LLMResponse,
    Tool,
    BaseLLMClient,
    ClaudeClient,
    OpenAIClient,
    OllamaClient,
    UnifiedLLMClient,
    create_llm_client,
)

from .rag_system import (
    DocumentType,
    Document,
    Chunk,
    RetrievalResult,
    RAGResponse,
    DocumentProcessor,
    Retriever,
    RAGPipeline,
    ConversationalRAG,
    create_rag_system,
    quick_index,
)

from .message_bus import (
    MessageType,
    MessagePriority,
    BusMessage,
    AgentMessageBus,
    MessageBusAgentMixin,
    StandardTopics,
    message_bus,
)

__all__ = [
    # Base Agent
    "BaseAgent",
    "EvolutionLevel",
    "Priority",
    "AgentCapability",
    "AgentContext",
    "AgentMessage",
    "AgentAction",
    "AgentPrediction",
    "AgentState",
    # Memory
    "MemoryItem",
    "Episode",
    "BaseMemoryStore",
    "RedisMemoryStore",
    "VectorMemoryStore",
    "EpisodicMemory",
    "WorkingMemory",
    "UnifiedMemorySystem",
    # LLM
    "LLMProvider",
    "LLMMessage",
    "LLMResponse",
    "Tool",
    "BaseLLMClient",
    "ClaudeClient",
    "OpenAIClient",
    "OllamaClient",
    "UnifiedLLMClient",
    "create_llm_client",
    # RAG
    "DocumentType",
    "Document",
    "Chunk",
    "RetrievalResult",
    "RAGResponse",
    "DocumentProcessor",
    "Retriever",
    "RAGPipeline",
    "ConversationalRAG",
    "create_rag_system",
    "quick_index",
    # Message Bus
    "MessageType",
    "MessagePriority",
    "BusMessage",
    "AgentMessageBus",
    "MessageBusAgentMixin",
    "StandardTopics",
    "message_bus",
]

__version__ = "1.0.0"
