"""
Conecta Plus - Monitoramento Agent
Agente especializado em monitoramento de câmeras
"""

from datetime import datetime
from typing import Dict, List, Any
from ..base_specialized import (
    BaseSpecializedAgent, SpecializedAgentConfig, DomainKnowledge,
    SpecializedContext, AgentResponse, SpecializedDomain, AgentCapability
)


class MonitoramentoAgent(BaseSpecializedAgent):
    """Agente para monitoramento de CFTV"""

    def __init__(self, config: SpecializedAgentConfig = None):
        if config is None:
            config = SpecializedAgentConfig(
                domain=SpecializedDomain.CFTV,
                name="Monitoramento CFTV",
                description="Monitoramento e controle de câmeras",
                capabilities=[AgentCapability.READ, AgentCapability.EXECUTE, AgentCapability.NOTIFY],
                allowed_tools=["camera", "alarm_panel", "notification"]
            )
        super().__init__(config)
        self._alertas: List[Dict] = []

    @property
    def knowledge(self) -> DomainKnowledge:
        return DomainKnowledge(
            domain=SpecializedDomain.CFTV,
            expertise_level=4,
            supported_intents=[
                "ver_camera",
                "listar_cameras",
                "status_sistema",
                "reportar_alerta",
                "mover_camera",
                "snapshot"
            ],
            faq=[
                {"keywords": ["gravação", "quanto tempo"], "answer": "As gravações são mantidas por 30 dias."},
                {"keywords": ["camera", "offline"], "answer": "Reportarei à manutenção. Enquanto isso, câmeras adjacentes cobrem a área."}
            ]
        )

    async def handle_intent(self, intent: str, context: SpecializedContext, entities: Dict) -> AgentResponse:
        if intent == "listar_cameras":
            return AgentResponse(
                message="**Câmeras Ativas:**\n"
                       "🟢 CAM-01: Entrada Principal\n"
                       "🟢 CAM-02: Estacionamento\n"
                       "🟢 CAM-03: Área de Lazer\n"
                       "🔴 CAM-04: Hall Bloco B (offline)",
                suggestions=["Ver CAM-01", "Status detalhado"]
            )
        elif intent == "status_sistema":
            return AgentResponse(
                message="**Status do CFTV:**\n"
                       "Câmeras online: 15/16\n"
                       "Gravação: Normal\n"
                       "Armazenamento: 45% usado\n"
                       "Última verificação: há 5 min"
            )
        elif intent == "ver_camera":
            camera_id = entities.get("camera_id", "CAM-01")
            return AgentResponse(
                message=f"Acessando câmera {camera_id}...",
                attachments=[{"type": "stream", "camera_id": camera_id}]
            )
        return AgentResponse(message="Como posso ajudar com o monitoramento?")

    async def execute_action(self, action: str, context: SpecializedContext, params: Dict) -> Dict:
        return {"success": True, "action": action}
