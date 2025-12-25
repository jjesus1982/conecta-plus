"""Conecta Plus - Atendimento Agent"""

from typing import Dict
from ..base_specialized import (
    BaseSpecializedAgent, SpecializedAgentConfig, DomainKnowledge,
    SpecializedContext, AgentResponse, SpecializedDomain, AgentCapability
)


class AtendimentoAgent(BaseSpecializedAgent):
    """Agente para atendimento ao condômino"""

    def __init__(self, config: SpecializedAgentConfig = None):
        if config is None:
            config = SpecializedAgentConfig(
                domain=SpecializedDomain.COMUNICACAO,
                name="Atendimento",
                description="Atendimento ao condômino",
                capabilities=[AgentCapability.READ, AgentCapability.WRITE, AgentCapability.ESCALATE],
                allowed_tools=["notification", "knowledge_base"]
            )
        super().__init__(config)

    @property
    def knowledge(self) -> DomainKnowledge:
        return DomainKnowledge(
            domain=SpecializedDomain.COMUNICACAO,
            supported_intents=["duvida_geral", "reclamacao", "sugestao", "elogio", "falar_humano"]
        )

    async def handle_intent(self, intent: str, context: SpecializedContext, entities: Dict) -> AgentResponse:
        if intent == "falar_humano":
            return AgentResponse(message="Transferindo para atendente...", should_escalate=True)
        elif intent == "reclamacao":
            return AgentResponse(message="Sinto muito pelo inconveniente. Descreva sua reclamação.", requires_input=True)
        return AgentResponse(message="Olá! Como posso ajudar?", suggestions=["Dúvidas", "Reclamação", "Falar com atendente"])

    async def execute_action(self, action: str, context: SpecializedContext, params: Dict) -> Dict:
        return {"success": True}
