"""
Agente Portaria Virtual - Atendimento remoto
Conecta Plus
"""

from typing import List, Dict
from agents.base.agent import BaseAgent


class AgentePortariaVirtual(BaseAgent):
    """Agente de portaria virtual e atendimento"""

    def __init__(self):
        super().__init__(
            name="portaria_virtual",
            description="Agente de portaria virtual para atendimento remoto",
            model="claude-3-5-sonnet-20241022",
            temperature=0.5,
        )

    @property
    def system_prompt(self) -> str:
        return """Você é o Agente de Portaria Virtual do Conecta Plus, especializado em:

1. ATENDIMENTO DE VISITANTES:
   - Identificar visitante (nome, documento, foto)
   - Verificar autorização com morador
   - Liberar ou negar acesso
   - Registrar visita

2. COMUNICAÇÃO:
   - Interfone virtual (voz e vídeo)
   - Chat com moradores
   - Notificações em tempo real
   - Transcrição de áudio

3. PROCEDIMENTOS:
   - Validação de prestadores de serviço
   - Entregas e encomendas
   - Emergências e incidentes
   - Acesso de moradores

4. INTEGRAÇÕES:
   - Abrir portões remotamente
   - Verificar câmeras do visitante
   - Consultar lista de autorizados
   - Registrar ocorrências

5. RELATÓRIOS:
   - Log de atendimentos
   - Tempo médio de espera
   - Visitantes por período

Seja educado, eficiente e priorize a segurança."""

    def get_tools(self) -> List[Dict]:
        return [
            {"name": "start_call", "description": "Inicia chamada com interfone"},
            {"name": "end_call", "description": "Encerra chamada"},
            {"name": "register_visitor", "description": "Registra visitante"},
            {"name": "check_authorization", "description": "Verifica autorização com morador"},
            {"name": "open_gate", "description": "Libera acesso"},
            {"name": "deny_access", "description": "Nega acesso"},
            {"name": "notify_resident", "description": "Notifica morador"},
            {"name": "capture_photo", "description": "Captura foto do visitante"},
            {"name": "transcribe_audio", "description": "Transcreve áudio"},
            {"name": "get_visit_log", "description": "Histórico de visitas"},
        ]

    def get_mcps(self) -> List[str]:
        return [
            "mcp-asterisk",
            "mcp-issabel",
            "mcp-whisper",
            "mcp-vision-ai",
            "mcp-control-id",
            "mcp-ppa",
        ]


agente_portaria_virtual = AgentePortariaVirtual()
