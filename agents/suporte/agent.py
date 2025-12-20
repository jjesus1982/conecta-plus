"""
Agente Suporte - Atendimento e suporte técnico
Conecta Plus
"""

from typing import List, Dict
from agents.base.agent import BaseAgent


class AgenteSuporte(BaseAgent):
    """Agente de suporte técnico"""

    def __init__(self):
        super().__init__(
            name="suporte",
            description="Agente de atendimento e suporte técnico",
            model="claude-3-5-sonnet-20241022",
            temperature=0.6,
        )

    @property
    def system_prompt(self) -> str:
        return """Você é o Agente de Suporte do Conecta Plus, especializado em:

1. ATENDIMENTO:
   - Primeiro contato (L1)
   - Triagem de chamados
   - Resolução de dúvidas
   - Escalonamento quando necessário

2. TICKETS:
   - Abertura de chamados
   - Classificação e priorização
   - Acompanhamento de SLA
   - Encerramento com feedback

3. BASE DE CONHECIMENTO:
   - FAQs
   - Tutoriais
   - Troubleshooting
   - Documentação

4. CANAIS:
   - Chat ao vivo
   - WhatsApp
   - E-mail
   - Telefone

5. MÉTRICAS:
   - Tempo de resposta
   - Taxa de resolução
   - Satisfação do cliente
   - Volume de chamados

Resolva problemas com rapidez e empatia."""

    def get_tools(self) -> List[Dict]:
        return [
            {"name": "create_ticket", "description": "Cria ticket"},
            {"name": "update_ticket", "description": "Atualiza ticket"},
            {"name": "close_ticket", "description": "Fecha ticket"},
            {"name": "search_kb", "description": "Busca na base de conhecimento"},
            {"name": "escalate", "description": "Escalona para próximo nível"},
            {"name": "get_customer_history", "description": "Histórico do cliente"},
            {"name": "send_response", "description": "Envia resposta"},
            {"name": "get_sla_status", "description": "Status de SLA"},
        ]

    def get_mcps(self) -> List[str]:
        return []


agente_suporte = AgenteSuporte()
