"""
Agente Facilities - Gestão de facilidades e áreas comuns
Conecta Plus
"""

from typing import List, Dict
from agents.base.agent import BaseAgent


class AgenteFacilities(BaseAgent):
    """Agente especializado em gestão de facilidades"""

    def __init__(self):
        super().__init__(
            name="facilities",
            description="Agente de gestão de facilidades e áreas comuns",
            model="claude-3-5-sonnet-20241022",
            temperature=0.5,
        )

    @property
    def system_prompt(self) -> str:
        return """Você é o Agente de Facilities do Conecta Plus, especializado em:

1. ÁREAS COMUNS:
   - Piscina, academia, salão de festas
   - Churrasqueira, playground, quadra
   - Jardins e paisagismo
   - Estacionamento

2. MANUTENÇÃO PREDIAL:
   - Elevadores e escadas
   - Iluminação de áreas comuns
   - Sistema hidráulico
   - Portões e cercas

3. LIMPEZA E CONSERVAÇÃO:
   - Escalas de limpeza
   - Controle de insumos
   - Coleta de lixo
   - Dedetização e controle de pragas

4. SEGURANÇA PATRIMONIAL:
   - Rondas e vigilância
   - Extintores e hidrantes
   - Sinalização de emergência
   - Sistemas de combate a incêndio

5. FORNECEDORES:
   - Contratos de manutenção
   - Avaliação de prestadores
   - Orçamentos e aprovações

Mantenha as áreas comuns em perfeito estado."""

    def get_tools(self) -> List[Dict]:
        return [
            {"name": "get_area_status", "description": "Status de área comum"},
            {"name": "schedule_maintenance", "description": "Agenda manutenção"},
            {"name": "create_checklist", "description": "Cria checklist de vistoria"},
            {"name": "report_issue", "description": "Reporta problema"},
            {"name": "assign_task", "description": "Atribui tarefa a funcionário"},
            {"name": "manage_supplier", "description": "Gerencia fornecedor"},
            {"name": "control_inventory", "description": "Controle de estoque"},
            {"name": "get_cleaning_schedule", "description": "Escala de limpeza"},
        ]

    def get_mcps(self) -> List[str]:
        return ["mcp-mqtt"]


agente_facilities = AgenteFacilities()
