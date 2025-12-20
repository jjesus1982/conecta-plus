"""
Agente CFTV - Monitoramento e análise de câmeras
Conecta Plus
"""

from typing import List, Dict
from agents.base.agent import BaseAgent


class AgenteCFTV(BaseAgent):
    """Agente especializado em CFTV e videomonitoramento"""

    def __init__(self):
        super().__init__(
            name="cftv",
            description="Agente de CFTV para monitoramento, detecção e análise de vídeo",
            model="claude-3-5-sonnet-20241022",
            temperature=0.3,  # Mais determinístico para análises
        )

    @property
    def system_prompt(self) -> str:
        return """Você é o Agente CFTV do Conecta Plus, especializado em:

1. MONITORAMENTO DE CÂMERAS:
   - Verificar status de DVRs/NVRs (Intelbras, Hikvision)
   - Monitorar conectividade de câmeras
   - Detectar câmeras offline ou com problemas

2. ANÁLISE DE VÍDEO:
   - Detecção de objetos (pessoas, veículos, animais)
   - Reconhecimento facial para controle de acesso
   - Leitura de placas (LPR/ALPR)
   - Detecção de movimento em zonas específicas

3. EVENTOS E ALERTAS:
   - Cruzamento de linha virtual
   - Intrusão em área restrita
   - Abandono/remoção de objetos
   - Aglomeração de pessoas

4. GRAVAÇÕES:
   - Busca de gravações por período
   - Identificar eventos específicos
   - Exportar clips de evidência

5. QUALIDADE E MANUTENÇÃO:
   - Verificar qualidade de imagem
   - Detectar obstrução de lente
   - Monitorar espaço em disco

Sempre forneça informações precisas e acionáveis.
Priorize a segurança e a privacidade dos moradores.
Use linguagem técnica quando apropriado, mas seja claro."""

    def get_tools(self) -> List[Dict]:
        return [
            {"name": "get_camera_status", "description": "Status de uma câmera específica"},
            {"name": "list_cameras", "description": "Lista todas as câmeras do condomínio"},
            {"name": "get_stream_url", "description": "URL de streaming de uma câmera"},
            {"name": "capture_snapshot", "description": "Captura imagem atual"},
            {"name": "search_recordings", "description": "Busca gravações por período"},
            {"name": "detect_objects", "description": "Detecta objetos em imagem/vídeo"},
            {"name": "detect_faces", "description": "Detecta e identifica faces"},
            {"name": "read_plate", "description": "Lê placa de veículo"},
            {"name": "get_events", "description": "Lista eventos detectados"},
            {"name": "configure_zone", "description": "Configura zona de detecção"},
            {"name": "ptz_control", "description": "Controle PTZ de câmera"},
        ]

    def get_mcps(self) -> List[str]:
        return [
            "mcp-intelbras-cftv",
            "mcp-hikvision-cftv",
            "mcp-vision-ai",
        ]


# Instância singleton
agente_cftv = AgenteCFTV()
