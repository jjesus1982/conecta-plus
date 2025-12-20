"""Conecta Plus - Documentos Agent"""

from typing import Dict
from ..base_specialized import (
    BaseSpecializedAgent, SpecializedAgentConfig, DomainKnowledge,
    SpecializedContext, AgentResponse, SpecializedDomain, AgentCapability
)


class DocumentosAgent(BaseSpecializedAgent):
    """Agente para gestão de documentos do condomínio"""

    def __init__(self, config: SpecializedAgentConfig = None):
        if config is None:
            config = SpecializedAgentConfig(
                domain=SpecializedDomain.SINDICO,
                name="Documentos",
                description="Gestão de documentos e arquivos",
                capabilities=[AgentCapability.READ, AgentCapability.WRITE],
                allowed_tools=["file", "document_generation", "template"]
            )
        super().__init__(config)

    @property
    def knowledge(self) -> DomainKnowledge:
        return DomainKnowledge(
            domain=SpecializedDomain.SINDICO,
            supported_intents=[
                "buscar_documento", "gerar_declaracao", "convenção",
                "regulamento", "atas_assembleia", "contratos"
            ]
        )

    async def handle_intent(self, intent: str, context: SpecializedContext, entities: Dict) -> AgentResponse:
        if intent == "buscar_documento":
            return AgentResponse(
                message="Qual documento procura?",
                suggestions=["Convenção", "Regulamento", "Atas", "Contratos"]
            )
        elif intent == "convenção":
            return AgentResponse(
                message="Convenção do Condomínio (atualizada em 2023).",
                attachments=[{"type": "pdf", "name": "convencao_2023.pdf"}]
            )
        elif intent == "gerar_declaracao":
            return AgentResponse(
                message="Informe o tipo de declaração:\n• Quitação\n• Nada Consta\n• Residência",
                requires_input=True
            )
        return AgentResponse(message="Posso ajudar com documentos do condomínio.")

    async def execute_action(self, action: str, context: SpecializedContext, params: Dict) -> Dict:
        return {"success": True}
