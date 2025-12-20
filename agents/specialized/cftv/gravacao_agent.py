"""
Conecta Plus - Gravação Agent
Agente especializado em gestão de gravações
"""

from typing import Dict
from ..base_specialized import (
    BaseSpecializedAgent, SpecializedAgentConfig, DomainKnowledge,
    SpecializedContext, AgentResponse, SpecializedDomain, AgentCapability
)


class GravacaoAgent(BaseSpecializedAgent):
    """Agente para gestão de gravações"""

    def __init__(self, config: SpecializedAgentConfig = None):
        if config is None:
            config = SpecializedAgentConfig(
                domain=SpecializedDomain.CFTV,
                name="Gestão de Gravações",
                description="Acesso e gestão de gravações",
                capabilities=[AgentCapability.READ, AgentCapability.EXECUTE],
                allowed_tools=["camera", "file"]
            )
        super().__init__(config)

    @property
    def knowledge(self) -> DomainKnowledge:
        return DomainKnowledge(
            domain=SpecializedDomain.CFTV,
            supported_intents=["buscar_gravacao", "exportar_video", "status_storage", "backup"]
        )

    async def handle_intent(self, intent: str, context: SpecializedContext, entities: Dict) -> AgentResponse:
        if intent == "buscar_gravacao":
            data = entities.get("data", "hoje")
            return AgentResponse(
                message=f"Gravações de {data}:\n• CAM-01: 24h disponível\n• CAM-02: 24h disponível",
                suggestions=["Exportar trecho", "Ver timeline"]
            )
        elif intent == "status_storage":
            return AgentResponse(
                message="**Armazenamento:**\n• Usado: 2.5TB / 5TB\n• Dias de gravação: 30\n• Status: Normal"
            )
        return AgentResponse(message="Posso ajudar com gravações. O que precisa?")

    async def execute_action(self, action: str, context: SpecializedContext, params: Dict) -> Dict:
        return {"success": True, "action": action}
