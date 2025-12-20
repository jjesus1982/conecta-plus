"""
Agente Automação - Controle de portões e automação
Conecta Plus
"""

from typing import List, Dict
from agents.base.agent import BaseAgent


class AgenteAutomacao(BaseAgent):
    """Agente especializado em automação de portões"""

    def __init__(self):
        super().__init__(
            name="automacao",
            description="Agente de automação de portões e dispositivos",
            model="claude-3-5-sonnet-20241022",
            temperature=0.3,
        )

    @property
    def system_prompt(self) -> str:
        return """Você é o Agente de Automação do Conecta Plus, especializado em:

1. CONTROLE DE PORTÕES:
   - Abertura/fechamento remoto
   - Status de portões (PPA, Garen, Nice)
   - Abertura parcial (pedestre)
   - Parada de emergência

2. GESTÃO DE CONTROLES:
   - Cadastrar controles remotos
   - Remover controles perdidos/roubados
   - Associar controle a morador

3. AUTOMAÇÃO:
   - Regras automáticas (ex: fechar após X segundos)
   - Integração com sensores
   - Acionamento por reconhecimento de placa

4. MANUTENÇÃO:
   - Monitorar ciclos de operação
   - Alertar manutenção preventiva
   - Detectar problemas mecânicos

5. SEGURANÇA:
   - Bloqueio de emergência
   - Modo férias (operação restrita)
   - Log de acionamentos

Sempre priorize a segurança dos moradores e visitantes."""

    def get_tools(self) -> List[Dict]:
        return [
            {"name": "open_gate", "description": "Abre portão"},
            {"name": "close_gate", "description": "Fecha portão"},
            {"name": "stop_gate", "description": "Para movimento do portão"},
            {"name": "partial_open", "description": "Abertura parcial"},
            {"name": "get_gate_status", "description": "Status do portão"},
            {"name": "add_remote", "description": "Cadastra controle remoto"},
            {"name": "remove_remote", "description": "Remove controle"},
            {"name": "list_remotes", "description": "Lista controles cadastrados"},
            {"name": "get_operation_log", "description": "Log de operações"},
            {"name": "set_auto_close", "description": "Configura fechamento automático"},
        ]

    def get_mcps(self) -> List[str]:
        return [
            "mcp-ppa",
            "mcp-garen",
            "mcp-nice",
        ]


agente_automacao = AgenteAutomacao()
