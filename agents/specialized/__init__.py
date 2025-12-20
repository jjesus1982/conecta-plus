"""
Conecta Plus - Specialized Agents Module
Agentes especializados para domínios específicos do condomínio

Este módulo contém agentes especializados que herdam do BaseAgent
e implementam funcionalidades específicas para cada área do condomínio.

Subdiretórios:
- acesso: Controle de acesso (portões, catracas, visitantes)
- cftv: CFTV e vigilância
- comunicacao: Comunicação e notificações
- financeiro: Gestão financeira
- manutencao: Manutenção predial
- ocorrencias: Gestão de ocorrências
- portaria: Portaria e recepção
- sindico: Gestão administrativa
"""

from .base_specialized import (
    BaseSpecializedAgent,
    SpecializedAgentConfig,
    DomainKnowledge,
    SpecializedContext,
)

from .acesso import (
    AcessoVeiculosAgent,
    AcessoPedestresAgent,
    GestaoVisitantesAgent,
)

from .cftv import (
    MonitoramentoAgent,
    AnaliseVideoAgent,
    GravacaoAgent,
)

from .comunicacao import (
    NotificacoesAgent,
    AtendimentoAgent,
    ComunicadosAgent,
)

from .financeiro import (
    CobrancaAgent,
    ContasAgent,
    RelatoriosFinanceirosAgent,
)

from .manutencao import (
    PreventivaManutencoAgent,
    CorretivaManutencoAgent,
    FornecedoresAgent,
)

from .ocorrencias import (
    RegistroOcorrenciasAgent,
    TratamentoOcorrenciasAgent,
    EscalonamentoAgent,
)

from .portaria import (
    PorteiroVirtualAgent,
    ControleAcessoAgent,
    EncomendosAgent,
)

from .sindico import (
    GestaoCondominialAgent,
    AssembleiasAgent,
    DocumentosAgent,
)

__all__ = [
    # Base
    "BaseSpecializedAgent",
    "SpecializedAgentConfig",
    "DomainKnowledge",
    "SpecializedContext",
    # Acesso
    "AcessoVeiculosAgent",
    "AcessoPedestresAgent",
    "GestaoVisitantesAgent",
    # CFTV
    "MonitoramentoAgent",
    "AnaliseVideoAgent",
    "GravacaoAgent",
    # Comunicação
    "NotificacoesAgent",
    "AtendimentoAgent",
    "ComunicadosAgent",
    # Financeiro
    "CobrancaAgent",
    "ContasAgent",
    "RelatoriosFinanceirosAgent",
    # Manutenção
    "PreventivaManutencoAgent",
    "CorretivaManutencoAgent",
    "FornecedoresAgent",
    # Ocorrências
    "RegistroOcorrenciasAgent",
    "TratamentoOcorrenciasAgent",
    "EscalonamentoAgent",
    # Portaria
    "PorteiroVirtualAgent",
    "ControleAcessoAgent",
    "EncomendosAgent",
    # Síndico
    "GestaoCondominialAgent",
    "AssembleiasAgent",
    "DocumentosAgent",
]
