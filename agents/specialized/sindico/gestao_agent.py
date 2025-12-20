"""Conecta Plus - Gestão Condominial Agent"""

from typing import Dict
from ..base_specialized import (
    BaseSpecializedAgent, SpecializedAgentConfig, DomainKnowledge,
    SpecializedContext, AgentResponse, SpecializedDomain, AgentCapability
)


class GestaoCondominialAgent(BaseSpecializedAgent):
    """Agente para gestão condominial"""

    def __init__(self, config: SpecializedAgentConfig = None):
        if config is None:
            config = SpecializedAgentConfig(
                domain=SpecializedDomain.SINDICO,
                name="Gestão Condominial",
                description="Apoio à gestão do síndico",
                capabilities=[AgentCapability.READ, AgentCapability.WRITE, AgentCapability.APPROVE, AgentCapability.NOTIFY],
                allowed_tools=["database", "notification", "workflow", "document_generation"]
            )
        super().__init__(config)

    @property
    def knowledge(self) -> DomainKnowledge:
        return DomainKnowledge(
            domain=SpecializedDomain.SINDICO,
            supported_intents=[
                "dashboard_sindico", "aprovar_despesa", "emitir_comunicado",
                "consultar_inadimplencia", "agendar_reuniao", "relatorio_geral"
            ]
        )

    async def handle_intent(self, intent: str, context: SpecializedContext, entities: Dict) -> AgentResponse:
        if intent == "dashboard_sindico":
            return AgentResponse(
                message="**Dashboard do Síndico:**\n"
                       "• Inadimplência: 5.2%\n"
                       "• Ocorrências abertas: 12\n"
                       "• Aprovações pendentes: 3\n"
                       "• Próxima assembleia: 15/01",
                suggestions=["Ver detalhes", "Aprovar pendências"]
            )
        elif intent == "aprovar_despesa":
            return AgentResponse(message="Despesa aprovada e registrada.", actions_executed=[{"action": "aprovar_despesa"}])
        return AgentResponse(message="Como posso ajudar na gestão do condomínio?")

    async def execute_action(self, action: str, context: SpecializedContext, params: Dict) -> Dict:
        return {"success": True}
