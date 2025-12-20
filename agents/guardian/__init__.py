"""
Conecta Plus - Guardian Agents
Sistema de Agentes de IA para Seguranca Eletronica

Agentes:
- GuardianMonitorAgent: Monitoramento inteligente de cameras
- GuardianAccessAgent: Controle de acesso inteligente
- GuardianAnalyticsAgent: Analise preditiva de seguranca
- GuardianAssistantAgent: Assistente conversacional de seguranca
- GuardianResponseAgent: Resposta automatizada a incidentes
- GuardianOrchestrator: Orquestrador central dos agentes
"""

from .monitor_agent import GuardianMonitorAgent
from .access_agent import GuardianAccessAgent
from .analytics_agent import GuardianAnalyticsAgent
from .assistant_agent import GuardianAssistantAgent
from .response_agent import GuardianResponseAgent
from .orchestrator import GuardianOrchestrator, create_guardian_system, MessageBus

__all__ = [
    "GuardianMonitorAgent",
    "GuardianAccessAgent",
    "GuardianAnalyticsAgent",
    "GuardianAssistantAgent",
    "GuardianResponseAgent",
    "GuardianOrchestrator",
    "create_guardian_system",
    "MessageBus",
]

__version__ = "2.0.0"
