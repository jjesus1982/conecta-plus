"""Conecta Plus - Fornecedores Agent"""

from typing import Dict
from ..base_specialized import (
    BaseSpecializedAgent, SpecializedAgentConfig, DomainKnowledge,
    SpecializedContext, AgentResponse, SpecializedDomain, AgentCapability
)


class FornecedoresAgent(BaseSpecializedAgent):
    """Agente para gestão de fornecedores"""

    def __init__(self, config: SpecializedAgentConfig = None):
        if config is None:
            config = SpecializedAgentConfig(
                domain=SpecializedDomain.MANUTENCAO,
                name="Fornecedores",
                description="Gestão de fornecedores e prestadores",
                capabilities=[AgentCapability.READ, AgentCapability.WRITE],
                allowed_tools=["database"]
            )
        super().__init__(config)

    @property
    def knowledge(self) -> DomainKnowledge:
        return DomainKnowledge(
            domain=SpecializedDomain.MANUTENCAO,
            supported_intents=["buscar_fornecedor", "avaliar_fornecedor", "contratos_ativos"]
        )

    async def handle_intent(self, intent: str, context: SpecializedContext, entities: Dict) -> AgentResponse:
        if intent == "buscar_fornecedor":
            return AgentResponse(message="**Fornecedores Aprovados:**\n• Elevadores: TecnoLift ⭐4.5\n• Elétrica: EletroMax ⭐4.8\n• Hidráulica: AquaFix ⭐4.2")
        return AgentResponse(message="Posso ajudar com fornecedores do condomínio.")

    async def execute_action(self, action: str, context: SpecializedContext, params: Dict) -> Dict:
        return {"success": True}
