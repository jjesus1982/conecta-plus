"""
Conecta Plus - Skills Module
Habilidades reutilizáveis para agentes de IA

Skills são capacidades modulares que podem ser compartilhadas entre agentes.
Cada skill encapsula uma funcionalidade específica com interface padronizada.

Categorias:
- Communication: Habilidades de comunicação (notificações, mensagens)
- Analysis: Habilidades analíticas (sentimento, entidades, classificação)
- Integration: Integrações externas (APIs, dispositivos)
- Document: Processamento de documentos
- Workflow: Automação de fluxos
"""

from .base_skill import (
    BaseSkill,
    SkillContext,
    SkillResult,
    SkillRegistry,
    skill,
)

from .communication_skills import (
    NotificationSkill,
    MessageFormattingSkill,
    MultiChannelSkill,
    EscalationSkill,
)

from .analysis_skills import (
    SentimentAnalysisSkill,
    EntityExtractionSkill,
    IntentClassificationSkill,
    SummarizationSkill,
    TranslationSkill,
)

from .integration_skills import (
    WhatsAppSkill,
    EmailSkill,
    SMSSkill,
    VoIPSkill,
    WebhookSkill,
)

from .document_skills import (
    PDFExtractionSkill,
    OCRSkill,
    DocumentGenerationSkill,
    TemplateSkill,
)

from .workflow_skills import (
    ApprovalWorkflowSkill,
    SchedulingSkill,
    ReminderSkill,
    TaskManagementSkill,
)

__all__ = [
    # Base
    "BaseSkill",
    "SkillContext",
    "SkillResult",
    "SkillRegistry",
    "skill",
    # Communication
    "NotificationSkill",
    "MessageFormattingSkill",
    "MultiChannelSkill",
    "EscalationSkill",
    # Analysis
    "SentimentAnalysisSkill",
    "EntityExtractionSkill",
    "IntentClassificationSkill",
    "SummarizationSkill",
    "TranslationSkill",
    # Integration
    "WhatsAppSkill",
    "EmailSkill",
    "SMSSkill",
    "VoIPSkill",
    "WebhookSkill",
    # Document
    "PDFExtractionSkill",
    "OCRSkill",
    "DocumentGenerationSkill",
    "TemplateSkill",
    # Workflow
    "ApprovalWorkflowSkill",
    "SchedulingSkill",
    "ReminderSkill",
    "TaskManagementSkill",
]
