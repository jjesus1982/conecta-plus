"""
Agente Morador - Assistente pessoal do morador
Conecta Plus
"""

from typing import List, Dict
from agents.base.agent import BaseAgent


class AgenteMorador(BaseAgent):
    """Agente assistente pessoal do morador"""

    def __init__(self):
        super().__init__(
            name="morador",
            description="Assistente pessoal do morador",
            model="claude-3-5-sonnet-20241022",
            temperature=0.7,
        )

    @property
    def system_prompt(self) -> str:
        return """Você é o Agente do Morador do Conecta Plus, assistente pessoal:

1. SERVIÇOS:
   - 2ª via de boleto
   - Reserva de áreas comuns
   - Autorização de visitantes
   - Cadastro de veículos

2. COMUNICAÇÃO:
   - Enviar mensagens ao síndico
   - Registrar ocorrências
   - Receber comunicados
   - Participar de enquetes

3. ACESSO:
   - Cadastrar biometria
   - Gerenciar controles remotos
   - Autorizar prestadores
   - Liberar entregas

4. INFORMAÇÕES:
   - Consultar regimento
   - Ver câmeras autorizadas
   - Histórico de acessos
   - Extrato financeiro

5. SUPORTE:
   - Dúvidas frequentes
   - Solicitações de manutenção
   - Reclamações e sugestões
   - Emergências

Seja amigável, prestativo e resolva as necessidades do morador."""

    def get_tools(self) -> List[Dict]:
        return [
            {"name": "get_boleto", "description": "2ª via de boleto"},
            {"name": "make_reservation", "description": "Reservar área comum"},
            {"name": "authorize_visitor", "description": "Autorizar visitante"},
            {"name": "register_vehicle", "description": "Cadastrar veículo"},
            {"name": "send_message", "description": "Enviar mensagem"},
            {"name": "report_issue", "description": "Registrar ocorrência"},
            {"name": "get_statement", "description": "Extrato financeiro"},
            {"name": "get_regulation", "description": "Consultar regimento"},
            {"name": "request_maintenance", "description": "Solicitar manutenção"},
        ]

    def get_mcps(self) -> List[str]:
        return [
            "mcp-boletos",
            "mcp-control-id",
        ]


agente_morador = AgenteMorador()
