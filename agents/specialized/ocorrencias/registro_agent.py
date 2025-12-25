"""Conecta Plus - Registro de Ocorrências Agent"""

from typing import Dict
from ..base_specialized import (
    BaseSpecializedAgent, SpecializedAgentConfig, DomainKnowledge,
    SpecializedContext, AgentResponse, SpecializedDomain, AgentCapability
)


class RegistroOcorrenciasAgent(BaseSpecializedAgent):
    """Agente para registro de ocorrências"""

    def __init__(self, config: SpecializedAgentConfig = None):
        if config is None:
            config = SpecializedAgentConfig(
                domain=SpecializedDomain.OCORRENCIAS,
                name="Registro de Ocorrências",
                description="Registro e acompanhamento de ocorrências",
                capabilities=[AgentCapability.READ, AgentCapability.WRITE, AgentCapability.NOTIFY],
                allowed_tools=["database", "notification", "camera"]
            )
        super().__init__(config)

    @property
    def knowledge(self) -> DomainKnowledge:
        return DomainKnowledge(
            domain=SpecializedDomain.OCORRENCIAS,
            supported_intents=["registrar_ocorrencia", "consultar_ocorrencia", "minhas_ocorrencias", "tipos_ocorrencia"]
        )

    async def handle_intent(self, intent: str, context: SpecializedContext, entities: Dict) -> AgentResponse:
        if intent == "registrar_ocorrencia":
            return AgentResponse(
                message="Para registrar uma ocorrência, informe:\n• Tipo (barulho, vazamento, etc)\n• Local\n• Descrição",
                requires_input=True
            )
        elif intent == "minhas_ocorrencias":
            return AgentResponse(message="**Suas Ocorrências:**\n• #1234 - Barulho (Resolvida)\n• #1235 - Vazamento (Em análise)")
        return AgentResponse(message="Posso ajudar com ocorrências.", suggestions=["Registrar", "Consultar"])

    async def execute_action(self, action: str, context: SpecializedContext, params: Dict) -> Dict:
        return {"success": True}
