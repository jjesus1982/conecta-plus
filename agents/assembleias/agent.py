"""
Agente Assembleias - Gestão de assembleias condominiais
Conecta Plus
"""

from typing import List, Dict
from agents.base.agent import BaseAgent


class AgenteAssembleias(BaseAgent):
    """Agente especializado em assembleias"""

    def __init__(self):
        super().__init__(
            name="assembleias",
            description="Agente de gestão de assembleias condominiais",
            model="claude-3-5-sonnet-20241022",
            temperature=0.5,
        )

    @property
    def system_prompt(self) -> str:
        return """Você é o Agente de Assembleias do Conecta Plus, especializado em:

1. CONVOCAÇÃO:
   - Elaborar edital de convocação
   - Definir pauta
   - Cumprir prazos legais
   - Enviar notificações

2. REALIZAÇÃO:
   - Controle de presença
   - Verificação de quórum
   - Cálculo de frações ideais
   - Procurações e representações

3. VOTAÇÃO:
   - Votação presencial ou remota
   - Contagem de votos
   - Quórum qualificado
   - Registro de abstenções

4. DOCUMENTAÇÃO:
   - Ata de assembleia
   - Registro em cartório
   - Publicação de decisões
   - Arquivo histórico

5. TIPOS DE ASSEMBLEIA:
   - AGO (Assembleia Geral Ordinária)
   - AGE (Assembleia Geral Extraordinária)
   - Assembleia virtual
   - Assembleia híbrida

Garanta que as assembleias sigam a legislação e a convenção."""

    def get_tools(self) -> List[Dict]:
        return [
            {"name": "create_assembly", "description": "Cria assembleia"},
            {"name": "send_convocation", "description": "Envia convocação"},
            {"name": "register_attendance", "description": "Registra presença"},
            {"name": "check_quorum", "description": "Verifica quórum"},
            {"name": "start_voting", "description": "Inicia votação"},
            {"name": "record_vote", "description": "Registra voto"},
            {"name": "close_voting", "description": "Encerra votação"},
            {"name": "generate_minutes", "description": "Gera ata"},
            {"name": "publish_results", "description": "Publica resultados"},
        ]

    def get_mcps(self) -> List[str]:
        return ["mcp-assinatura-digital"]


agente_assembleias = AgenteAssembleias()
