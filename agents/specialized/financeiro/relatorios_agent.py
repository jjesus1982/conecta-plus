"""Conecta Plus - Relatórios Financeiros Agent"""

from typing import Dict
from ..base_specialized import (
    BaseSpecializedAgent, SpecializedAgentConfig, DomainKnowledge,
    SpecializedContext, AgentResponse, SpecializedDomain, AgentCapability
)


class RelatoriosFinanceirosAgent(BaseSpecializedAgent):
    """Agente para relatórios financeiros"""

    def __init__(self, config: SpecializedAgentConfig = None):
        if config is None:
            config = SpecializedAgentConfig(
                domain=SpecializedDomain.FINANCEIRO,
                name="Relatórios Financeiros",
                description="Geração de relatórios financeiros",
                capabilities=[AgentCapability.READ],
                allowed_tools=["database", "document_generation"]
            )
        super().__init__(config)

    @property
    def knowledge(self) -> DomainKnowledge:
        return DomainKnowledge(
            domain=SpecializedDomain.FINANCEIRO,
            supported_intents=["relatorio_mensal", "relatorio_inadimplencia", "balancete", "previsao_orcamentaria"]
        )

    async def handle_intent(self, intent: str, context: SpecializedContext, entities: Dict) -> AgentResponse:
        if intent == "relatorio_mensal":
            return AgentResponse(message="Gerando relatório mensal...", attachments=[{"type": "pdf", "name": "relatorio_dez2024.pdf"}])
        elif intent == "balancete":
            return AgentResponse(message="**Balancete Dezembro/2024:**\n• Receitas: R$ 85.000\n• Despesas: R$ 72.000\n• Saldo: R$ 13.000")
        return AgentResponse(message="Qual relatório deseja?", suggestions=["Mensal", "Inadimplência", "Balancete"])

    async def execute_action(self, action: str, context: SpecializedContext, params: Dict) -> Dict:
        return {"success": True}
