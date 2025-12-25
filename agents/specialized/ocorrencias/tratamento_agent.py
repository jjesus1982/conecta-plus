"""Conecta Plus - Tratamento de Ocorrências Agent"""

from typing import Dict
from ..base_specialized import (
    BaseSpecializedAgent, SpecializedAgentConfig, DomainKnowledge,
    SpecializedContext, AgentResponse, SpecializedDomain, AgentCapability
)


class TratamentoOcorrenciasAgent(BaseSpecializedAgent):
    """Agente para tratamento de ocorrências"""

    def __init__(self, config: SpecializedAgentConfig = None):
        if config is None:
            config = SpecializedAgentConfig(
                domain=SpecializedDomain.OCORRENCIAS,
                name="Tratamento de Ocorrências",
                description="Análise e resolução de ocorrências",
                capabilities=[AgentCapability.READ, AgentCapability.WRITE, AgentCapability.EXECUTE],
                allowed_tools=["database", "notification", "workflow"]
            )
        super().__init__(config)

    @property
    def knowledge(self) -> DomainKnowledge:
        return DomainKnowledge(
            domain=SpecializedDomain.OCORRENCIAS,
            supported_intents=["analisar_ocorrencia", "resolver_ocorrencia", "atribuir_responsavel"]
        )

    async def handle_intent(self, intent: str, context: SpecializedContext, entities: Dict) -> AgentResponse:
        if intent == "resolver_ocorrencia":
            return AgentResponse(message="Ocorrência marcada como resolvida. Notificando interessados.")
        return AgentResponse(message="Posso ajudar com o tratamento de ocorrências.")

    async def execute_action(self, action: str, context: SpecializedContext, params: Dict) -> Dict:
        return {"success": True}
