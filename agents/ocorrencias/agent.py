"""
Agente Ocorrências - Gestão de ocorrências e incidentes
Conecta Plus
"""

from typing import List, Dict
from agents.base.agent import BaseAgent


class AgenteOcorrencias(BaseAgent):
    """Agente de gestão de ocorrências"""

    def __init__(self):
        super().__init__(
            name="ocorrencias",
            description="Agente de gestão de ocorrências e incidentes",
            model="claude-3-5-sonnet-20241022",
            temperature=0.4,
        )

    @property
    def system_prompt(self) -> str:
        return """Você é o Agente de Ocorrências do Conecta Plus, especializado em:

1. TIPOS DE OCORRÊNCIA:
   - Barulho/perturbação
   - Vazamento/infiltração
   - Dano ao patrimônio
   - Segurança
   - Animais
   - Estacionamento irregular

2. REGISTRO:
   - Abrir ocorrência
   - Anexar evidências (fotos, vídeos, áudios)
   - Classificar prioridade
   - Atribuir responsável

3. TRATAMENTO:
   - Investigação
   - Mediação entre partes
   - Aplicação de regimento
   - Notificação/advertência

4. ACOMPANHAMENTO:
   - Status da ocorrência
   - Histórico de ações
   - Prazo de resolução
   - Feedback do reclamante

5. ANÁLISE:
   - Ocorrências por tipo
   - Reincidências
   - Unidades problemáticas
   - Tendências

Resolva ocorrências com justiça e imparcialidade."""

    def get_tools(self) -> List[Dict]:
        return [
            {"name": "create_incident", "description": "Cria ocorrência"},
            {"name": "update_incident", "description": "Atualiza ocorrência"},
            {"name": "close_incident", "description": "Encerra ocorrência"},
            {"name": "add_evidence", "description": "Adiciona evidência"},
            {"name": "send_warning", "description": "Envia advertência"},
            {"name": "get_history", "description": "Histórico da unidade"},
            {"name": "mediate", "description": "Auxilia mediação"},
            {"name": "generate_report", "description": "Relatório de ocorrências"},
        ]

    def get_mcps(self) -> List[str]:
        return ["mcp-vision-ai", "mcp-whisper"]


agente_ocorrencias = AgenteOcorrencias()
