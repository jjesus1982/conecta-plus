"""
Agente Comunicação - Gestão de comunicações do condomínio
Conecta Plus
"""

from typing import List, Dict
from agents.base.agent import BaseAgent


class AgenteComunicacao(BaseAgent):
    """Agente de comunicação e notificações"""

    def __init__(self):
        super().__init__(
            name="comunicacao",
            description="Agente de gestão de comunicações",
            model="claude-3-5-sonnet-20241022",
            temperature=0.6,
        )

    @property
    def system_prompt(self) -> str:
        return """Você é o Agente de Comunicação do Conecta Plus, especializado em:

1. CANAIS:
   - App do morador
   - WhatsApp Business
   - Telegram
   - E-mail
   - SMS

2. TIPOS DE COMUNICAÇÃO:
   - Comunicados gerais
   - Alertas urgentes
   - Lembretes
   - Convocações
   - Pesquisas e enquetes

3. AUTOMAÇÃO:
   - Régua de notificações
   - Mensagens programadas
   - Respostas automáticas
   - Chatbot

4. GESTÃO:
   - Mailing de moradores
   - Segmentação de públicos
   - Histórico de envios
   - Métricas de engajamento

5. TEMPLATES:
   - Modelos de comunicados
   - Personalização
   - Múltiplos idiomas

Comunique de forma clara, respeitosa e no canal adequado."""

    def get_tools(self) -> List[Dict]:
        return [
            {"name": "send_notification", "description": "Envia notificação"},
            {"name": "send_whatsapp", "description": "Envia WhatsApp"},
            {"name": "send_telegram", "description": "Envia Telegram"},
            {"name": "send_email", "description": "Envia e-mail"},
            {"name": "send_sms", "description": "Envia SMS"},
            {"name": "create_survey", "description": "Cria enquete"},
            {"name": "schedule_message", "description": "Agenda mensagem"},
            {"name": "get_engagement", "description": "Métricas de engajamento"},
        ]

    def get_mcps(self) -> List[str]:
        return []


agente_comunicacao = AgenteComunicacao()
