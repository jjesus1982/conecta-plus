"""
Agente Alarme - Centrais de alarme e monitoramento
Conecta Plus
"""

from typing import List, Dict
from agents.base.agent import BaseAgent


class AgenteAlarme(BaseAgent):
    """Agente especializado em sistemas de alarme"""

    def __init__(self):
        super().__init__(
            name="alarme",
            description="Agente de monitoramento de alarmes",
            model="claude-3-5-sonnet-20241022",
            temperature=0.2,  # Muito determinístico para segurança
        )

    @property
    def system_prompt(self) -> str:
        return """Você é o Agente de Alarme do Conecta Plus, especializado em:

1. MONITORAMENTO:
   - Status de centrais (JFL, Intelbras AMT)
   - Zonas abertas/fechadas
   - Partições armadas/desarmadas
   - Eventos de alarme

2. CONTROLE:
   - Armar/desarmar partições
   - Anular zonas temporariamente
   - Acionar PGMs (sirene, luz, etc)
   - Disparo de pânico

3. ALERTAS:
   - Disparo de alarme
   - Violação de zona
   - Falha de comunicação
   - Bateria baixa / falta de energia

4. INTEGRAÇÃO:
   - Verificação com câmeras
   - Notificação para síndico/segurança
   - Acionamento de iluminação

5. MANUTENÇÃO:
   - Status de sensores
   - Teste de comunicação
   - Histórico de eventos

SEGURANÇA É PRIORIDADE MÁXIMA. Sempre confirme ações críticas."""

    def get_tools(self) -> List[Dict]:
        return [
            {"name": "arm_partition", "description": "Arma partição do alarme"},
            {"name": "disarm_partition", "description": "Desarma partição"},
            {"name": "get_status", "description": "Status da central"},
            {"name": "get_zones", "description": "Status das zonas"},
            {"name": "bypass_zone", "description": "Anula zona temporariamente"},
            {"name": "trigger_pgm", "description": "Aciona PGM"},
            {"name": "panic", "description": "Dispara pânico"},
            {"name": "get_events", "description": "Histórico de eventos"},
            {"name": "test_communication", "description": "Testa comunicação"},
        ]

    def get_mcps(self) -> List[str]:
        return [
            "mcp-jfl",
            "mcp-intelbras-alarme",
        ]


agente_alarme = AgenteAlarme()
