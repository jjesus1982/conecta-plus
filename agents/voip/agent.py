"""
Agente VoIP - Comunicação por voz
Conecta Plus
"""

from typing import List, Dict
from agents.base.agent import BaseAgent


class AgenteVoIP(BaseAgent):
    """Agente de VoIP e telefonia"""

    def __init__(self):
        super().__init__(
            name="voip",
            description="Agente de VoIP e telefonia IP",
            model="claude-3-5-sonnet-20241022",
            temperature=0.4,
        )

    @property
    def system_prompt(self) -> str:
        return """Você é o Agente VoIP do Conecta Plus, especializado em:

1. TELEFONIA:
   - Gerenciar ramais (Asterisk/Issabel)
   - Configurar troncos
   - Filas de atendimento
   - URA (atendimento automático)

2. INTERFONIA:
   - Chamadas de interfone
   - Intercomunicação entre portarias
   - Chamadas de emergência
   - Integração com câmeras

3. GRAVAÇÕES:
   - Gravar chamadas
   - Transcrever áudio
   - Buscar gravações
   - Relatórios de chamadas

4. INTEGRAÇÕES:
   - Click-to-call
   - Notificações por voz
   - Conferências
   - Voicemail

5. MONITORAMENTO:
   - Status de ramais
   - Chamadas em andamento
   - Qualidade de áudio
   - Logs de CDR

Garanta comunicação de voz clara e confiável."""

    def get_tools(self) -> List[Dict]:
        return [
            {"name": "make_call", "description": "Origina chamada"},
            {"name": "hangup", "description": "Desliga chamada"},
            {"name": "transfer", "description": "Transfere chamada"},
            {"name": "get_extension_status", "description": "Status do ramal"},
            {"name": "list_active_calls", "description": "Chamadas ativas"},
            {"name": "get_recordings", "description": "Lista gravações"},
            {"name": "transcribe_call", "description": "Transcreve chamada"},
            {"name": "get_cdr", "description": "Registros de chamadas"},
        ]

    def get_mcps(self) -> List[str]:
        return [
            "mcp-asterisk",
            "mcp-issabel",
            "mcp-whisper",
        ]


agente_voip = AgenteVoIP()
