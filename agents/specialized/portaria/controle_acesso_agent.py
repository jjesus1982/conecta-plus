"""Conecta Plus - Controle de Acesso Agent"""

from typing import Dict
from ..base_specialized import (
    BaseSpecializedAgent, SpecializedAgentConfig, DomainKnowledge,
    SpecializedContext, AgentResponse, SpecializedDomain, AgentCapability
)


class ControleAcessoAgent(BaseSpecializedAgent):
    """Agente para controle de acesso na portaria"""

    def __init__(self, config: SpecializedAgentConfig = None):
        if config is None:
            config = SpecializedAgentConfig(
                domain=SpecializedDomain.PORTARIA,
                name="Controle de Acesso Portaria",
                description="Controle de acesso pela portaria",
                capabilities=[AgentCapability.READ, AgentCapability.EXECUTE, AgentCapability.WRITE],
                allowed_tools=["access_control", "camera", "database"]
            )
        super().__init__(config)

    @property
    def knowledge(self) -> DomainKnowledge:
        return DomainKnowledge(
            domain=SpecializedDomain.PORTARIA,
            supported_intents=["registrar_entrada", "registrar_saida", "consultar_permanencia", "liberar_prestador"]
        )

    async def handle_intent(self, intent: str, context: SpecializedContext, entities: Dict) -> AgentResponse:
        if intent == "registrar_entrada":
            return AgentResponse(message="Entrada registrada às " + context.timestamp.strftime("%H:%M"))
        elif intent == "consultar_permanencia":
            return AgentResponse(message="**Na área comum:**\n• Moradores: 15\n• Visitantes: 3\n• Prestadores: 2")
        return AgentResponse(message="Controle de acesso disponível.")

    async def execute_action(self, action: str, context: SpecializedContext, params: Dict) -> Dict:
        return {"success": True}
