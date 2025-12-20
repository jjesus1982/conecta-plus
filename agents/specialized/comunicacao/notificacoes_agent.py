"""Conecta Plus - Notificações Agent"""

from typing import Dict
from ..base_specialized import (
    BaseSpecializedAgent, SpecializedAgentConfig, DomainKnowledge,
    SpecializedContext, AgentResponse, SpecializedDomain, AgentCapability
)


class NotificacoesAgent(BaseSpecializedAgent):
    """Agente para gestão de notificações"""

    def __init__(self, config: SpecializedAgentConfig = None):
        if config is None:
            config = SpecializedAgentConfig(
                domain=SpecializedDomain.COMUNICACAO,
                name="Notificações",
                description="Envio e gestão de notificações",
                capabilities=[AgentCapability.READ, AgentCapability.WRITE, AgentCapability.NOTIFY],
                allowed_tools=["notification", "email", "sms", "whatsapp"]
            )
        super().__init__(config)

    @property
    def knowledge(self) -> DomainKnowledge:
        return DomainKnowledge(
            domain=SpecializedDomain.COMUNICACAO,
            supported_intents=["enviar_notificacao", "listar_notificacoes", "configurar_preferencias"]
        )

    async def handle_intent(self, intent: str, context: SpecializedContext, entities: Dict) -> AgentResponse:
        if intent == "enviar_notificacao":
            return AgentResponse(message="Informe o destinatário e a mensagem.", requires_input=True)
        elif intent == "listar_notificacoes":
            return AgentResponse(message="Últimas notificações:\n• Boleto vencendo (ontem)\n• Assembleia agendada (há 3 dias)")
        return AgentResponse(message="Como posso ajudar com notificações?")

    async def execute_action(self, action: str, context: SpecializedContext, params: Dict) -> Dict:
        return {"success": True}
