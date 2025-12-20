"""Conecta Plus - Porteiro Virtual Agent"""

from typing import Dict
from ..base_specialized import (
    BaseSpecializedAgent, SpecializedAgentConfig, DomainKnowledge,
    SpecializedContext, AgentResponse, SpecializedDomain, AgentCapability
)


class PorteiroVirtualAgent(BaseSpecializedAgent):
    """Agente de porteiro virtual"""

    def __init__(self, config: SpecializedAgentConfig = None):
        if config is None:
            config = SpecializedAgentConfig(
                domain=SpecializedDomain.PORTARIA,
                name="Porteiro Virtual",
                description="Atendimento virtual na portaria",
                capabilities=[AgentCapability.READ, AgentCapability.EXECUTE, AgentCapability.NOTIFY],
                allowed_tools=["access_control", "intercom", "camera", "notification"],
                active_hours_start=0,
                active_hours_end=24
            )
        super().__init__(config)

    @property
    def knowledge(self) -> DomainKnowledge:
        return DomainKnowledge(
            domain=SpecializedDomain.PORTARIA,
            supported_intents=["atender_interfone", "identificar_visitante", "liberar_acesso", "chamar_morador"],
            faq=[
                {"keywords": ["horário", "portaria"], "answer": "A portaria virtual funciona 24 horas."},
                {"keywords": ["entrega", "correspondência"], "answer": "Entregas são recebidas de 8h às 20h."}
            ]
        )

    async def handle_intent(self, intent: str, context: SpecializedContext, entities: Dict) -> AgentResponse:
        if intent == "atender_interfone":
            return AgentResponse(
                message="Portaria Virtual, boa tarde! Por favor, identifique-se e informe a unidade que deseja visitar.",
                requires_input=True
            )
        elif intent == "liberar_acesso":
            return AgentResponse(message="Acesso liberado. Portão abrindo.", actions_executed=[{"action": "liberar_portao"}])
        return AgentResponse(message="Portaria Virtual. Como posso ajudar?")

    async def execute_action(self, action: str, context: SpecializedContext, params: Dict) -> Dict:
        return {"success": True}
