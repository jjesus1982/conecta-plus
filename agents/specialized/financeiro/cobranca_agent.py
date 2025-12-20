"""Conecta Plus - Cobrança Agent"""

from typing import Dict
from ..base_specialized import (
    BaseSpecializedAgent, SpecializedAgentConfig, DomainKnowledge,
    SpecializedContext, AgentResponse, SpecializedDomain, AgentCapability
)


class CobrancaAgent(BaseSpecializedAgent):
    """Agente para gestão de cobranças"""

    def __init__(self, config: SpecializedAgentConfig = None):
        if config is None:
            config = SpecializedAgentConfig(
                domain=SpecializedDomain.FINANCEIRO,
                name="Cobrança",
                description="Gestão de cobranças e inadimplência",
                capabilities=[AgentCapability.READ, AgentCapability.WRITE, AgentCapability.NOTIFY],
                allowed_tools=["database", "notification", "email"]
            )
        super().__init__(config)

    @property
    def knowledge(self) -> DomainKnowledge:
        return DomainKnowledge(
            domain=SpecializedDomain.FINANCEIRO,
            supported_intents=["consultar_debito", "segunda_via_boleto", "negociar_divida", "historico_pagamentos"],
            faq=[
                {"keywords": ["boleto", "segunda via"], "answer": "Acesse o app ou solicite por aqui informando sua unidade."},
                {"keywords": ["parcelar", "negociar"], "answer": "Parcelas em até 6x. Agende com a administração."}
            ]
        )

    async def handle_intent(self, intent: str, context: SpecializedContext, entities: Dict) -> AgentResponse:
        if intent == "consultar_debito":
            unidade = entities.get("unidade")
            return AgentResponse(
                message=f"**Situação Unidade {unidade or 'sua'}:**\n• Débitos: R$ 0,00\n• Próximo vencimento: 10/01",
                suggestions=["Segunda via boleto", "Histórico"]
            )
        elif intent == "segunda_via_boleto":
            return AgentResponse(message="Boleto gerado! Enviando por email e WhatsApp.", actions_executed=[{"action": "gerar_boleto"}])
        return AgentResponse(message="Posso ajudar com cobranças e boletos.")

    async def execute_action(self, action: str, context: SpecializedContext, params: Dict) -> Dict:
        return {"success": True}
