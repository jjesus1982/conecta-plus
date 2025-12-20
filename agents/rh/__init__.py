"""
Conecta Plus - Agente RH
Sistema de gestão de recursos humanos inteligente
"""

from .agent_v2 import (
    AgenteRH,
    create_hr_agent,
    TipoFuncionario,
    StatusFuncionario,
    TipoRegistro,
    Funcionario,
    RegistroPonto,
    Escala,
)

__all__ = [
    "AgenteRH",
    "create_hr_agent",
    "TipoFuncionario",
    "StatusFuncionario",
    "TipoRegistro",
    "Funcionario",
    "RegistroPonto",
    "Escala",
]
