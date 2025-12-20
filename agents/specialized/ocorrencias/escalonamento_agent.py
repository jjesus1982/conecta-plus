"""Conecta Plus - Escalonamento Agent"""

from typing import Dict
from ..base_specialized import (
    BaseSpecializedAgent, SpecializedAgentConfig, DomainKnowledge,
    SpecializedContext, AgentResponse, SpecializedDomain, AgentCapability
)


class EscalonamentoAgent(BaseSpecializedAgent):
    """Agente para escalonamento de ocorrências"""

    def __init__(self, config: SpecializedAgentConfig = None):
        if config is None:
            config = SpecializedAgentConfig(
                domain=SpecializedDomain.OCORRENCIAS,
                name="Escalonamento",
                description="Escalonamento de ocorrências críticas",
                capabilities=[AgentCapability.READ, AgentCapability.ESCALATE, AgentCapability.NOTIFY],
                allowed_tools=["notification", "workflow"]
            )
        super().__init__(config)

    @property
    def knowledge(self) -> DomainKnowledge:
        return DomainKnowledge(
            domain=SpecializedDomain.OCORRENCIAS,
            supported_intents=["escalonar_urgente", "verificar_prioridade", "notificar_sindico"]
        )

    async def handle_intent(self, intent: str, context: SpecializedContext, entities: Dict) -> AgentResponse:
        if intent == "escalonar_urgente":
            return AgentResponse(message="Ocorrência escalonada para síndico e conselho.", should_escalate=True)
        return AgentResponse(message="Posso ajudar com escalonamento de ocorrências.")

    async def execute_action(self, action: str, context: SpecializedContext, params: Dict) -> Dict:
        return {"success": True}
