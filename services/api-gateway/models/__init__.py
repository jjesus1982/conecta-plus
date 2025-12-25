"""
Conecta Plus - Models Package
"""
from .financeiro import (
    Base,
    Boleto,
    Pagamento,
    Lancamento,
    Acordo,
    ParcelaAcordo,
    HistoricoCobranca,
    ScoreUnidade,
    AuditLog,
    ConfiguracaoBancaria,
    StatusBoleto,
    StatusPagamento,
    TipoLancamento,
    StatusAcordo,
    TipoAuditoria,
    create_tables,
    create_schema
)

from .cora import (
    ContaCora,
    TransacaoCora,
    CobrancaCora,
    WebhookCora,
    CoraToken,
    SaldoCora,
    CoraSyncLog,
    TipoTransacaoCora,
    TipoCobrancaCora,
    StatusCobrancaCora,
    TipoSyncCora,
    StatusSyncCora,
    AmbienteCora,
    VersaoAPICora,
)

__all__ = [
    # Modelos Financeiros
    'Base',
    'Boleto',
    'Pagamento',
    'Lancamento',
    'Acordo',
    'ParcelaAcordo',
    'HistoricoCobranca',
    'ScoreUnidade',
    'AuditLog',
    'ConfiguracaoBancaria',
    'StatusBoleto',
    'StatusPagamento',
    'TipoLancamento',
    'StatusAcordo',
    'TipoAuditoria',
    'create_tables',
    'create_schema',

    # Modelos Cora Bank
    'ContaCora',
    'TransacaoCora',
    'CobrancaCora',
    'WebhookCora',
    'CoraToken',
    'SaldoCora',
    'CoraSyncLog',

    # Enums Cora
    'TipoTransacaoCora',
    'TipoCobrancaCora',
    'StatusCobrancaCora',
    'TipoSyncCora',
    'StatusSyncCora',
    'AmbienteCora',
    'VersaoAPICora',
]
