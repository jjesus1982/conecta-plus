"""
Agente Síndico - Assistente do síndico
Conecta Plus
"""

from typing import List, Dict
from agents.base.agent import BaseAgent


class AgenteSindico(BaseAgent):
    """Agente assistente do síndico"""

    def __init__(self):
        super().__init__(
            name="sindico",
            description="Assistente inteligente do síndico",
            model="claude-3-5-sonnet-20241022",
            temperature=0.6,
        )

    @property
    def system_prompt(self) -> str:
        return """Você é o Agente Síndico do Conecta Plus, assistente pessoal do síndico:

1. DASHBOARD EXECUTIVO:
   - Visão geral do condomínio
   - Indicadores principais (inadimplência, ocorrências, etc)
   - Alertas críticos
   - Tarefas pendentes

2. TOMADA DE DECISÃO:
   - Análise de situações
   - Sugestão de ações
   - Precedentes e histórico
   - Consulta a regimento e convenção

3. COMUNICAÇÃO:
   - Redigir comunicados
   - Responder moradores
   - Convocar assembleias
   - Notificações e advertências

4. GESTÃO:
   - Aprovação de orçamentos
   - Autorização de visitantes VIP
   - Situações de emergência
   - Mediação de conflitos

5. RELATÓRIOS:
   - Relatório mensal para assembleia
   - Prestação de contas
   - Indicadores de gestão
   - Comparativos e tendências

Seja estratégico, proativo e apoie as decisões do síndico."""

    def get_tools(self) -> List[Dict]:
        return [
            {"name": "get_dashboard", "description": "Dashboard executivo"},
            {"name": "get_alerts", "description": "Alertas críticos"},
            {"name": "draft_notice", "description": "Redige comunicado"},
            {"name": "approve_budget", "description": "Aprova orçamento"},
            {"name": "mediate_conflict", "description": "Auxilia mediação"},
            {"name": "generate_report", "description": "Gera relatório"},
            {"name": "query_regulation", "description": "Consulta regimento"},
            {"name": "schedule_meeting", "description": "Agenda reunião"},
            {"name": "authorize_access", "description": "Autoriza acesso especial"},
        ]

    def get_mcps(self) -> List[str]:
        return []  # Coordena outros agentes


agente_sindico = AgenteSindico()
