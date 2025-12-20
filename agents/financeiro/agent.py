"""
Agente Financeiro - Gestão financeira do condomínio
Conecta Plus
"""

from typing import List, Dict
from agents.base.agent import BaseAgent


class AgenteFinanceiro(BaseAgent):
    """Agente especializado em gestão financeira"""

    def __init__(self):
        super().__init__(
            name="financeiro",
            description="Agente de gestão financeira condominial",
            model="claude-3-5-sonnet-20241022",
            temperature=0.3,  # Preciso para cálculos
        )

    @property
    def system_prompt(self) -> str:
        return """Você é o Agente Financeiro do Conecta Plus, especializado em:

1. TAXAS CONDOMINIAIS:
   - Cálculo de rateio
   - Geração de boletos
   - Cobrança por PIX
   - Segunda via

2. INADIMPLÊNCIA:
   - Monitoramento de devedores
   - Régua de cobrança automatizada
   - Acordos e parcelamentos
   - Negativação e protesto

3. CONTAS A PAGAR:
   - Fornecedores
   - Folha de pagamento
   - Impostos e tributos
   - Controle de vencimentos

4. CONTABILIDADE:
   - Lançamentos contábeis
   - Conciliação bancária
   - Balancete mensal
   - Demonstrativos financeiros

5. FISCAL:
   - Emissão de NFS-e
   - Retenções de impostos
   - Declarações fiscais
   - Certidões e regularidade

Mantenha as contas em dia e a saúde financeira do condomínio."""

    def get_tools(self) -> List[Dict]:
        return [
            {"name": "generate_boleto", "description": "Gera boleto"},
            {"name": "generate_pix", "description": "Gera cobrança PIX"},
            {"name": "get_debtors", "description": "Lista inadimplentes"},
            {"name": "create_agreement", "description": "Cria acordo de pagamento"},
            {"name": "process_payment", "description": "Processa pagamento recebido"},
            {"name": "emit_nfse", "description": "Emite NFS-e"},
            {"name": "get_balance", "description": "Saldo e fluxo de caixa"},
            {"name": "generate_statement", "description": "Gera demonstrativo"},
            {"name": "reconcile_bank", "description": "Conciliação bancária"},
        ]

    def get_mcps(self) -> List[str]:
        return [
            "mcp-boletos",
            "mcp-pix",
            "mcp-nfse",
        ]


agente_financeiro = AgenteFinanceiro()
