"""Conecta Plus - Comunicados Agent"""

from typing import Dict
from ..base_specialized import (
    BaseSpecializedAgent, SpecializedAgentConfig, DomainKnowledge,
    SpecializedContext, AgentResponse, SpecializedDomain, AgentCapability
)


class ComunicadosAgent(BaseSpecializedAgent):
    """Agente para gestão de comunicados"""

    def __init__(self, config: SpecializedAgentConfig = None):
        if config is None:
            config = SpecializedAgentConfig(
                domain=SpecializedDomain.COMUNICACAO,
                name="Comunicados",
                description="Criação e distribuição de comunicados",
                capabilities=[AgentCapability.READ, AgentCapability.WRITE, AgentCapability.NOTIFY],
                allowed_tools=["notification", "template", "broadcast"]
            )
        super().__init__(config)

    @property
    def knowledge(self) -> DomainKnowledge:
        return DomainKnowledge(
            domain=SpecializedDomain.COMUNICACAO,
            supported_intents=["criar_comunicado", "listar_comunicados", "enviar_comunicado"]
        )

    async def handle_intent(self, intent: str, context: SpecializedContext, entities: Dict) -> AgentResponse:
        if intent == "listar_comunicados":
            return AgentResponse(message="**Comunicados Recentes:**\n• Manutenção elevador (hoje)\n• Assembleia 20/12 (ontem)")
        elif intent == "criar_comunicado":
            return AgentResponse(message="Informe o título e conteúdo do comunicado.", requires_input=True)
        return AgentResponse(message="Posso ajudar com comunicados do condomínio.")

    async def execute_action(self, action: str, context: SpecializedContext, params: Dict) -> Dict:
        return {"success": True}
