"""
Agente Compliance - Conformidade e regulamentações
Conecta Plus
"""

from typing import List, Dict
from agents.base.agent import BaseAgent


class AgenteCompliance(BaseAgent):
    """Agente de compliance e conformidade"""

    def __init__(self):
        super().__init__(
            name="compliance",
            description="Agente de compliance e conformidade regulatória",
            model="claude-3-5-sonnet-20241022",
            temperature=0.3,
        )

    @property
    def system_prompt(self) -> str:
        return """Você é o Agente de Compliance do Conecta Plus, especializado em:

1. LEGISLAÇÃO:
   - Código Civil (condomínios)
   - Lei do Inquilinato
   - LGPD (proteção de dados)
   - Normas trabalhistas

2. DOCUMENTAÇÃO:
   - Convenção do condomínio
   - Regimento interno
   - Atas de assembleia
   - Contratos

3. CERTIFICAÇÕES:
   - AVCB (Corpo de Bombeiros)
   - Elevadores (RIA)
   - Para-raios (SPDA)
   - Limpeza de caixas d'água

4. AUDITORIAS:
   - Checklist de conformidade
   - Identificação de gaps
   - Plano de ação
   - Monitoramento contínuo

5. LGPD:
   - Inventário de dados
   - Consentimentos
   - Direitos dos titulares
   - Relatório de impacto

Mantenha o condomínio em conformidade com todas as regulamentações."""

    def get_tools(self) -> List[Dict]:
        return [
            {"name": "check_compliance", "description": "Verifica conformidade"},
            {"name": "list_expirations", "description": "Lista vencimentos"},
            {"name": "generate_checklist", "description": "Gera checklist"},
            {"name": "query_legislation", "description": "Consulta legislação"},
            {"name": "manage_consent", "description": "Gerencia consentimentos LGPD"},
            {"name": "audit", "description": "Executa auditoria"},
            {"name": "generate_report", "description": "Gera relatório de compliance"},
        ]

    def get_mcps(self) -> List[str]:
        return []


agente_compliance = AgenteCompliance()
