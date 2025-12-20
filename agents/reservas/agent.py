"""
Agente Reservas - Sistema de reserva de áreas comuns
Conecta Plus
"""

from typing import List, Dict
from agents.base.agent import BaseAgent


class AgenteReservas(BaseAgent):
    """Agente especializado em reservas de áreas comuns"""

    def __init__(self):
        super().__init__(
            name="reservas",
            description="Agente de reservas de áreas comuns",
            model="claude-3-5-sonnet-20241022",
            temperature=0.5,
        )

    @property
    def system_prompt(self) -> str:
        return """Você é o Agente de Reservas do Conecta Plus, especializado em:

1. ÁREAS RESERVÁVEIS:
   - Salão de festas
   - Churrasqueira
   - Quadra esportiva
   - Espaço gourmet
   - Sala de reuniões

2. GESTÃO DE RESERVAS:
   - Verificar disponibilidade
   - Fazer reserva
   - Cancelar reserva
   - Lista de espera

3. REGRAS:
   - Antecedência mínima/máxima
   - Limite de reservas por unidade
   - Horários permitidos
   - Capacidade máxima

4. COBRANÇA:
   - Taxa de reserva
   - Caução
   - Multa por cancelamento
   - Cobrança de danos

5. PÓS-USO:
   - Checklist de entrega
   - Vistoria
   - Liberação de caução
   - Avaliação do espaço

Facilite as reservas mantendo a organização e regras do condomínio."""

    def get_tools(self) -> List[Dict]:
        return [
            {"name": "check_availability", "description": "Verifica disponibilidade"},
            {"name": "make_reservation", "description": "Faz reserva"},
            {"name": "cancel_reservation", "description": "Cancela reserva"},
            {"name": "list_reservations", "description": "Lista reservas"},
            {"name": "get_rules", "description": "Regras do espaço"},
            {"name": "charge_fee", "description": "Cobra taxa"},
            {"name": "do_checklist", "description": "Checklist de entrega"},
            {"name": "release_deposit", "description": "Libera caução"},
        ]

    def get_mcps(self) -> List[str]:
        return []


agente_reservas = AgenteReservas()
