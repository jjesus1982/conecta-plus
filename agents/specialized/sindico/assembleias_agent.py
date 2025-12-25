"""Conecta Plus - Assembleias Agent"""

from typing import Dict
from ..base_specialized import (
    BaseSpecializedAgent, SpecializedAgentConfig, DomainKnowledge,
    SpecializedContext, AgentResponse, SpecializedDomain, AgentCapability
)


class AssembleiasAgent(BaseSpecializedAgent):
    """Agente para gestão de assembleias"""

    def __init__(self, config: SpecializedAgentConfig = None):
        if config is None:
            config = SpecializedAgentConfig(
                domain=SpecializedDomain.SINDICO,
                name="Assembleias",
                description="Gestão de assembleias e votações",
                capabilities=[AgentCapability.READ, AgentCapability.WRITE, AgentCapability.NOTIFY],
                allowed_tools=["scheduling", "notification", "document_generation", "template"]
            )
        super().__init__(config)

    @property
    def knowledge(self) -> DomainKnowledge:
        return DomainKnowledge(
            domain=SpecializedDomain.SINDICO,
            supported_intents=[
                "agendar_assembleia", "consultar_assembleia", "edital_convocacao",
                "registrar_votacao", "resultado_votacao", "listar_presentes"
            ]
        )

    async def handle_intent(self, intent: str, context: SpecializedContext, entities: Dict) -> AgentResponse:
        if intent == "consultar_assembleia":
            return AgentResponse(
                message="**Próxima Assembleia:**\n"
                       "• Data: 15/01/2025 às 19h\n"
                       "• Tipo: Ordinária\n"
                       "• Local: Salão de Festas\n"
                       "• Pauta: Prestação de contas 2024",
                suggestions=["Ver edital", "Confirmar presença"]
            )
        elif intent == "edital_convocacao":
            return AgentResponse(
                message="Edital gerado e pronto para distribuição.",
                attachments=[{"type": "pdf", "name": "edital_janeiro2025.pdf"}]
            )
        return AgentResponse(message="Posso ajudar com assembleias e votações.")

    async def execute_action(self, action: str, context: SpecializedContext, params: Dict) -> Dict:
        return {"success": True}
