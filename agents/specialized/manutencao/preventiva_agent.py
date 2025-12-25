"""Conecta Plus - Manutenção Preventiva Agent"""

from typing import Dict
from ..base_specialized import (
    BaseSpecializedAgent, SpecializedAgentConfig, DomainKnowledge,
    SpecializedContext, AgentResponse, SpecializedDomain, AgentCapability
)


class PreventivaManutencoAgent(BaseSpecializedAgent):
    """Agente para manutenção preventiva"""

    def __init__(self, config: SpecializedAgentConfig = None):
        if config is None:
            config = SpecializedAgentConfig(
                domain=SpecializedDomain.MANUTENCAO,
                name="Manutenção Preventiva",
                description="Gestão de manutenções preventivas",
                capabilities=[AgentCapability.READ, AgentCapability.WRITE, AgentCapability.NOTIFY],
                allowed_tools=["scheduling", "notification", "database"]
            )
        super().__init__(config)

    @property
    def knowledge(self) -> DomainKnowledge:
        return DomainKnowledge(
            domain=SpecializedDomain.MANUTENCAO,
            supported_intents=["agenda_manutencao", "proximas_manutencoes", "historico_manutencao", "agendar_vistoria"]
        )

    async def handle_intent(self, intent: str, context: SpecializedContext, entities: Dict) -> AgentResponse:
        if intent == "proximas_manutencoes":
            return AgentResponse(
                message="**Manutenções Agendadas:**\n• Elevador: 15/01 (mensal)\n• Bombas: 20/01 (trimestral)\n• Gerador: 25/01 (semestral)"
            )
        return AgentResponse(message="Posso ajudar com manutenções preventivas.")

    async def execute_action(self, action: str, context: SpecializedContext, params: Dict) -> Dict:
        return {"success": True}
