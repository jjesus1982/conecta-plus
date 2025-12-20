"""
Agente Encomendas - Gestão de encomendas e correspondências
Conecta Plus
"""

from typing import List, Dict
from agents.base.agent import BaseAgent


class AgenteEncomendas(BaseAgent):
    """Agente de gestão de encomendas"""

    def __init__(self):
        super().__init__(
            name="encomendas",
            description="Agente de gestão de encomendas e correspondências",
            model="claude-3-5-sonnet-20241022",
            temperature=0.4,
        )

    @property
    def system_prompt(self) -> str:
        return """Você é o Agente de Encomendas do Conecta Plus, especializado em:

1. RECEBIMENTO:
   - Registrar encomenda (foto, remetente, destinatário)
   - Classificar tipo (pequena, média, grande, refrigerada)
   - Armazenar em local adequado
   - Notificar morador

2. RETIRADA:
   - Verificar identidade do retirante
   - Conferir autorização
   - Registrar retirada
   - Coletar assinatura

3. TIPOS:
   - Correios
   - Transportadoras
   - Delivery de comida
   - Documentos

4. GESTÃO:
   - Encomendas pendentes
   - Encomendas atrasadas
   - Histórico por unidade
   - Capacidade do espaço

5. AUTOMAÇÃO:
   - Notificação automática
   - Lembrete de retirada
   - Alerta de vencimento
   - Relatórios diários

Garanta que todas as encomendas cheguem ao destinatário."""

    def get_tools(self) -> List[Dict]:
        return [
            {"name": "register_package", "description": "Registra encomenda"},
            {"name": "notify_resident", "description": "Notifica morador"},
            {"name": "confirm_pickup", "description": "Confirma retirada"},
            {"name": "list_pending", "description": "Lista pendentes"},
            {"name": "get_package_history", "description": "Histórico da unidade"},
            {"name": "send_reminder", "description": "Envia lembrete"},
            {"name": "generate_report", "description": "Relatório de encomendas"},
        ]

    def get_mcps(self) -> List[str]:
        return ["mcp-vision-ai"]


agente_encomendas = AgenteEncomendas()
