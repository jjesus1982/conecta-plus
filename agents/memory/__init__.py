"""
Conecta Plus - Memory Module
Sistema de memória especializado para agentes de IA

Módulos:
- ConversationMemory: Memória de conversas e diálogos
- EntityMemory: Memória de entidades (pessoas, lugares, objetos)
- KnowledgeBase: Base de conhecimento persistente
- ProceduralMemory: Memória de procedimentos e habilidades
- TemporalMemory: Memória baseada em tempo e eventos
- RelationshipMemory: Memória de relacionamentos entre entidades
"""

from .conversation_memory import (
    ConversationMemory,
    ConversationTurn,
    ConversationSummary,
    ConversationAnalytics,
)

from .entity_memory import (
    EntityMemory,
    Entity,
    EntityType,
    EntityAttribute,
    EntityMention,
)

from .knowledge_base import (
    KnowledgeBase,
    KnowledgeItem,
    KnowledgeCategory,
    KnowledgeSource,
)

from .procedural_memory import (
    ProceduralMemory,
    Procedure,
    ProcedureStep,
    ProcedureExecution,
    SkillLevel,
)

from .temporal_memory import (
    TemporalMemory,
    TemporalEvent,
    RecurringPattern,
    TimeSlot,
    CalendarEntry,
)

from .relationship_memory import (
    RelationshipMemory,
    Relationship,
    RelationshipType,
    InteractionHistory,
)

__all__ = [
    # Conversation
    "ConversationMemory",
    "ConversationTurn",
    "ConversationSummary",
    "ConversationAnalytics",
    # Entity
    "EntityMemory",
    "Entity",
    "EntityType",
    "EntityAttribute",
    "EntityMention",
    # Knowledge
    "KnowledgeBase",
    "KnowledgeItem",
    "KnowledgeCategory",
    "KnowledgeSource",
    # Procedural
    "ProceduralMemory",
    "Procedure",
    "ProcedureStep",
    "ProcedureExecution",
    "SkillLevel",
    # Temporal
    "TemporalMemory",
    "TemporalEvent",
    "RecurringPattern",
    "TimeSlot",
    "CalendarEntry",
    # Relationship
    "RelationshipMemory",
    "Relationship",
    "RelationshipType",
    "InteractionHistory",
]
