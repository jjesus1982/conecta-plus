"""
Agente Comercial - Vendas e relacionamento com clientes
Conecta Plus
"""

from typing import List, Dict
from agents.base.agent import BaseAgent


class AgenteComercial(BaseAgent):
    """Agente comercial e de vendas"""

    def __init__(self):
        super().__init__(
            name="comercial",
            description="Agente comercial para vendas e relacionamento",
            model="claude-3-5-sonnet-20241022",
            temperature=0.7,
        )

    @property
    def system_prompt(self) -> str:
        return """Você é o Agente Comercial do Conecta Plus, especializado em:

1. PROSPECÇÃO:
   - Identificar leads (síndicos, administradoras)
   - Qualificar oportunidades
   - Abordagem inicial
   - Agendamento de demos

2. VENDAS:
   - Apresentação de produtos
   - Demonstração da plataforma
   - Proposta comercial
   - Negociação

3. ONBOARDING:
   - Implantação inicial
   - Treinamento de usuários
   - Configuração do condomínio
   - Migração de dados

4. RELACIONAMENTO:
   - Acompanhamento pós-venda
   - Upsell e cross-sell
   - Renovação de contratos
   - Prevenção de churn

5. CRM:
   - Gestão de pipeline
   - Histórico de interações
   - Previsão de vendas
   - Relatórios comerciais

Seja consultivo, entenda as necessidades e ofereça soluções."""

    def get_tools(self) -> List[Dict]:
        return [
            {"name": "create_lead", "description": "Cria lead"},
            {"name": "qualify_lead", "description": "Qualifica lead"},
            {"name": "schedule_demo", "description": "Agenda demonstração"},
            {"name": "create_proposal", "description": "Cria proposta"},
            {"name": "track_opportunity", "description": "Acompanha oportunidade"},
            {"name": "start_onboarding", "description": "Inicia onboarding"},
            {"name": "get_pipeline", "description": "Visão do pipeline"},
            {"name": "forecast", "description": "Previsão de vendas"},
        ]

    def get_mcps(self) -> List[str]:
        return []


agente_comercial = AgenteComercial()
