"""Conecta Plus - Contas Agent"""

from typing import Dict
from ..base_specialized import (
    BaseSpecializedAgent, SpecializedAgentConfig, DomainKnowledge,
    SpecializedContext, AgentResponse, SpecializedDomain, AgentCapability
)


class ContasAgent(BaseSpecializedAgent):
    """Agente para gestão de contas a pagar/receber"""

    def __init__(self, config: SpecializedAgentConfig = None):
        if config is None:
            config = SpecializedAgentConfig(
                domain=SpecializedDomain.FINANCEIRO,
                name="Contas",
                description="Gestão de contas a pagar e receber",
                capabilities=[AgentCapability.READ, AgentCapability.WRITE, AgentCapability.APPROVE],
                allowed_tools=["database", "approval_workflow"]
            )
        super().__init__(config)

    @property
    def knowledge(self) -> DomainKnowledge:
        return DomainKnowledge(
            domain=SpecializedDomain.FINANCEIRO,
            supported_intents=["contas_pagar", "contas_receber", "fluxo_caixa", "aprovar_despesa"]
        )

    async def handle_intent(self, intent: str, context: SpecializedContext, entities: Dict) -> AgentResponse:
        if intent == "contas_pagar":
            return AgentResponse(message="**Contas a Pagar (próx. 30 dias):**\n• Água: R$ 2.500 (10/01)\n• Luz: R$ 3.200 (15/01)\n• Elevador: R$ 1.800 (20/01)")
        elif intent == "fluxo_caixa":
            return AgentResponse(message="**Fluxo de Caixa:**\n• Saldo atual: R$ 45.000\n• Receitas previstas: R$ 85.000\n• Despesas previstas: R$ 62.000")
        return AgentResponse(message="Posso ajudar com contas do condomínio.")

    async def execute_action(self, action: str, context: SpecializedContext, params: Dict) -> Dict:
        return {"success": True}
