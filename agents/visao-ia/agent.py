"""
Agente Visão IA - Processamento de imagem e vídeo com IA
Conecta Plus
"""

from typing import List, Dict
from agents.base.agent import BaseAgent


class AgenteVisaoIA(BaseAgent):
    """Agente de visão computacional"""

    def __init__(self):
        super().__init__(
            name="visao_ia",
            description="Agente de visão computacional e processamento de imagem",
            model="claude-3-5-sonnet-20241022",
            temperature=0.2,
        )

    @property
    def system_prompt(self) -> str:
        return """Você é o Agente de Visão IA do Conecta Plus, especializado em:

1. DETECÇÃO DE OBJETOS:
   - Pessoas
   - Veículos
   - Animais
   - Objetos abandonados

2. RECONHECIMENTO:
   - Reconhecimento facial
   - Leitura de placas (LPR/ALPR)
   - OCR de documentos
   - Identificação de uniformes/EPIs

3. ANÁLISE DE COMPORTAMENTO:
   - Cruzamento de linha
   - Intrusão em área
   - Aglomeração
   - Vadiagem (loitering)
   - Movimento atípico

4. CONTAGEM:
   - Pessoas em área
   - Veículos em estacionamento
   - Fluxo de entrada/saída

5. QUALIDADE:
   - Verificar desfoque
   - Detectar obstrução
   - Ajuste de iluminação

Processe imagens em tempo real com alta precisão."""

    def get_tools(self) -> List[Dict]:
        return [
            {"name": "detect_objects", "description": "Detecta objetos em imagem"},
            {"name": "detect_faces", "description": "Detecta e reconhece faces"},
            {"name": "read_plate", "description": "Lê placa de veículo"},
            {"name": "ocr", "description": "Extrai texto de imagem"},
            {"name": "count_people", "description": "Conta pessoas"},
            {"name": "detect_intrusion", "description": "Detecta intrusão"},
            {"name": "analyze_behavior", "description": "Analisa comportamento"},
            {"name": "check_ppe", "description": "Verifica EPIs"},
        ]

    def get_mcps(self) -> List[str]:
        return ["mcp-vision-ai"]


agente_visao_ia = AgenteVisaoIA()
