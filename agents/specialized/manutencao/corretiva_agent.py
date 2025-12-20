"""Conecta Plus - Manutenção Corretiva Agent"""

from typing import Dict
from ..base_specialized import (
    BaseSpecializedAgent, SpecializedAgentConfig, DomainKnowledge,
    SpecializedContext, AgentResponse, SpecializedDomain, AgentCapability
)


class CorretivaManutencoAgent(BaseSpecializedAgent):
    """Agente para manutenção corretiva"""

    def __init__(self, config: SpecializedAgentConfig = None):
        if config is None:
            config = SpecializedAgentConfig(
                domain=SpecializedDomain.MANUTENCAO,
                name="Manutenção Corretiva",
                description="Gestão de manutenções corretivas e emergências",
                capabilities=[AgentCapability.READ, AgentCapability.WRITE, AgentCapability.EXECUTE, AgentCapability.NOTIFY],
                allowed_tools=["scheduling", "notification", "database"]
            )
        super().__init__(config)

    @property
    def knowledge(self) -> DomainKnowledge:
        return DomainKnowledge(
            domain=SpecializedDomain.MANUTENCAO,
            supported_intents=["reportar_problema", "status_chamado", "urgencia", "listar_chamados"]
        )

    async def handle_intent(self, intent: str, context: SpecializedContext, entities: Dict) -> AgentResponse:
        if intent == "reportar_problema":
            return AgentResponse(message="Descreva o problema e a localização.", requires_input=True)
        elif intent == "status_chamado":
            return AgentResponse(message="**Chamado #1234:**\n• Status: Em andamento\n• Previsão: Hoje às 14h")
        return AgentResponse(message="Posso ajudar com manutenções corretivas.")

    async def execute_action(self, action: str, context: SpecializedContext, params: Dict) -> Dict:
        return {"success": True}
