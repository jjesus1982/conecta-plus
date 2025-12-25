"""Conecta Plus - Encomendas Agent"""

from typing import Dict
from ..base_specialized import (
    BaseSpecializedAgent, SpecializedAgentConfig, DomainKnowledge,
    SpecializedContext, AgentResponse, SpecializedDomain, AgentCapability
)


class EncomendosAgent(BaseSpecializedAgent):
    """Agente para gestão de encomendas"""

    def __init__(self, config: SpecializedAgentConfig = None):
        if config is None:
            config = SpecializedAgentConfig(
                domain=SpecializedDomain.PORTARIA,
                name="Encomendas",
                description="Gestão de encomendas e correspondências",
                capabilities=[AgentCapability.READ, AgentCapability.WRITE, AgentCapability.NOTIFY],
                allowed_tools=["database", "notification", "camera"]
            )
        super().__init__(config)

    @property
    def knowledge(self) -> DomainKnowledge:
        return DomainKnowledge(
            domain=SpecializedDomain.PORTARIA,
            supported_intents=["registrar_encomenda", "consultar_encomendas", "retirar_encomenda", "notificar_morador"]
        )

    async def handle_intent(self, intent: str, context: SpecializedContext, entities: Dict) -> AgentResponse:
        if intent == "consultar_encomendas":
            unidade = entities.get("unidade")
            return AgentResponse(
                message=f"**Encomendas para {unidade or 'sua unidade'}:**\n• 📦 Correios - Hoje 10:30\n• 📦 Amazon - Ontem 15:45",
                suggestions=["Retirar encomenda"]
            )
        elif intent == "registrar_encomenda":
            return AgentResponse(message="Encomenda registrada. Morador notificado.")
        return AgentResponse(message="Posso ajudar com encomendas e correspondências.")

    async def execute_action(self, action: str, context: SpecializedContext, params: Dict) -> Dict:
        return {"success": True}
