"""
Agente Manutenção - Gestão de manutenções preventivas e corretivas
Conecta Plus
"""

from typing import List, Dict
from agents.base.agent import BaseAgent


class AgenteManutencao(BaseAgent):
    """Agente especializado em manutenção predial"""

    def __init__(self):
        super().__init__(
            name="manutencao",
            description="Agente de gestão de manutenções",
            model="claude-3-5-sonnet-20241022",
            temperature=0.4,
        )

    @property
    def system_prompt(self) -> str:
        return """Você é o Agente de Manutenção do Conecta Plus, especializado em:

1. MANUTENÇÃO PREVENTIVA:
   - Cronograma de manutenções
   - Checklist de itens
   - Alertas de vencimento
   - Histórico de serviços

2. MANUTENÇÃO CORRETIVA:
   - Recebimento de chamados
   - Priorização de urgências
   - Acompanhamento de resolução
   - Registro de soluções

3. EQUIPAMENTOS:
   - Elevadores
   - Bombas e motores
   - Sistema elétrico
   - Ar condicionado
   - Portões e câmeras

4. ORDENS DE SERVIÇO:
   - Abertura de OS
   - Atribuição a técnicos
   - Status e SLA
   - Encerramento e avaliação

5. FORNECEDORES E CONTRATOS:
   - Contratos de manutenção
   - Garantias
   - Orçamentos
   - Avaliação de serviço

Priorize manutenções preventivas para evitar emergências."""

    def get_tools(self) -> List[Dict]:
        return [
            {"name": "create_work_order", "description": "Cria ordem de serviço"},
            {"name": "update_work_order", "description": "Atualiza OS"},
            {"name": "close_work_order", "description": "Encerra OS"},
            {"name": "schedule_preventive", "description": "Agenda preventiva"},
            {"name": "get_maintenance_calendar", "description": "Calendário de manutenções"},
            {"name": "alert_expiring", "description": "Alerta vencimentos"},
            {"name": "evaluate_supplier", "description": "Avalia fornecedor"},
            {"name": "get_equipment_history", "description": "Histórico do equipamento"},
        ]

    def get_mcps(self) -> List[str]:
        return ["mcp-mqtt"]


agente_manutencao = AgenteManutencao()
