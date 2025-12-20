"""
Agente RH - Gestão de recursos humanos
Conecta Plus
"""

from typing import List, Dict
from agents.base.agent import BaseAgent


class AgenteRH(BaseAgent):
    """Agente especializado em RH e departamento pessoal"""

    def __init__(self):
        super().__init__(
            name="rh",
            description="Agente de gestão de recursos humanos",
            model="claude-3-5-sonnet-20241022",
            temperature=0.4,
        )

    @property
    def system_prompt(self) -> str:
        return """Você é o Agente de RH do Conecta Plus, especializado em:

1. GESTÃO DE FUNCIONÁRIOS:
   - Cadastro de colaboradores
   - Documentação e contratos
   - Férias e afastamentos
   - Admissões e demissões

2. PONTO ELETRÔNICO:
   - Coleta de marcações do REP
   - Tratamento de inconsistências
   - Banco de horas
   - Horas extras

3. FOLHA DE PAGAMENTO:
   - Cálculo de salários
   - Benefícios e descontos
   - Encargos trabalhistas
   - Geração de holerites

4. OBRIGAÇÕES LEGAIS:
   - eSocial (eventos S-1200, S-2200, etc)
   - RAIS, DIRF, CAGED
   - Férias e 13º salário
   - FGTS e INSS

5. RELATÓRIOS:
   - Quadro de funcionários
   - Custos de pessoal
   - Turnover e absenteísmo

Mantenha conformidade com legislação trabalhista brasileira."""

    def get_tools(self) -> List[Dict]:
        return [
            {"name": "add_employee", "description": "Cadastra funcionário"},
            {"name": "update_employee", "description": "Atualiza dados"},
            {"name": "terminate_employee", "description": "Rescisão contratual"},
            {"name": "get_timesheet", "description": "Busca marcações de ponto"},
            {"name": "calculate_payroll", "description": "Calcula folha de pagamento"},
            {"name": "generate_payslip", "description": "Gera holerite"},
            {"name": "send_esocial", "description": "Envia evento eSocial"},
            {"name": "request_vacation", "description": "Solicita férias"},
            {"name": "get_employee_report", "description": "Relatório de funcionário"},
        ]

    def get_mcps(self) -> List[str]:
        return [
            "mcp-ponto-rep",
            "mcp-esocial",
        ]


agente_rh = AgenteRH()
