"""
Conecta Plus - Gestão de Visitantes Agent
Agente especializado em gestão de visitantes
"""

from datetime import datetime
from typing import Dict, List, Any
from ..base_specialized import (
    BaseSpecializedAgent, SpecializedAgentConfig, DomainKnowledge,
    SpecializedContext, AgentResponse, SpecializedDomain, AgentCapability
)


class GestaoVisitantesAgent(BaseSpecializedAgent):
    """Agente para gestão de visitantes"""

    def __init__(self, config: SpecializedAgentConfig = None):
        if config is None:
            config = SpecializedAgentConfig(
                domain=SpecializedDomain.ACESSO,
                name="Gestão de Visitantes",
                description="Cadastro e liberação de visitantes",
                capabilities=[AgentCapability.READ, AgentCapability.WRITE, AgentCapability.EXECUTE, AgentCapability.NOTIFY],
                allowed_tools=["access_control", "notification"]
            )
        super().__init__(config)
        self._visitantes_esperados: List[Dict] = []

    @property
    def knowledge(self) -> DomainKnowledge:
        return DomainKnowledge(
            domain=SpecializedDomain.ACESSO,
            expertise_level=4,
            supported_intents=[
                "cadastrar_visitante",
                "liberar_visitante",
                "listar_visitantes",
                "cancelar_visita",
                "autorizar_prestador"
            ],
            faq=[
                {"keywords": ["visitante", "como cadastrar"], "answer": "Você pode cadastrar visitantes pelo app ou ligando para a portaria."},
                {"keywords": ["prestador", "autorizar"], "answer": "Prestadores precisam ser autorizados com antecedência via app ou administração."}
            ]
        )

    async def handle_intent(self, intent: str, context: SpecializedContext, entities: Dict) -> AgentResponse:
        if intent == "cadastrar_visitante":
            return AgentResponse(
                message="Para cadastrar um visitante, informe:\n• Nome completo\n• Documento (RG/CPF)\n• Data e horário da visita",
                requires_input=True
            )
        elif intent == "listar_visitantes":
            if not self._visitantes_esperados:
                return AgentResponse(message="Nenhum visitante esperado para hoje.")
            lista = "\n".join([f"• {v['nome']} - {v['horario']}" for v in self._visitantes_esperados])
            return AgentResponse(message=f"**Visitantes esperados:**\n{lista}")
        elif intent == "liberar_visitante":
            return AgentResponse(
                message="Visitante liberado. Entrada registrada.",
                actions_executed=[{"action": "liberar_visitante"}]
            )
        return AgentResponse(message="Como posso ajudar com visitantes?")

    async def execute_action(self, action: str, context: SpecializedContext, params: Dict) -> Dict:
        return {"success": True, "action": action}
