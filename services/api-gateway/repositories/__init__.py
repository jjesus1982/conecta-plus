"""
Conecta Plus - Repositories Package
"""

# Importações base
try:
    from .base import (
        UsuarioRepository,
        CondominioRepository,
        CameraRepository,
        UnidadeRepository,
        MoradorRepository,
        AcessoRepository,
        DashboardRepository,
        PontoAcessoRepository,
        ManutencaoRepository,
        usuario_repo,
        condominio_repo,
        camera_repo,
        unidade_repo,
        morador_repo,
        acesso_repo,
        dashboard_repo,
        ponto_acesso_repo,
        manutencao_repo,
    )
except ImportError as e:
    print(f"Aviso: Repositórios base não disponíveis: {e}")

# Importações financeiro (opcional)
try:
    from .financeiro import (
        BoletoRepository,
        PagamentoRepository,
        LancamentoRepository,
        CategoriaRepository,
        ContaBancariaRepository,
        AcordoRepository,
        ConciliacaoRepository,
        WebhookRepository,
    )
except ImportError as e:
    print(f"Aviso: Repositórios financeiros não disponíveis: {e}")

# Importações Cora Bank (opcional)
try:
    from .cora import (
        ContaCoraRepository,
        TransacaoCoraRepository,
        CobrancaCoraRepository,
        WebhookCoraRepository,
        CoraTokenRepository,
        SaldoCoraRepository,
        CoraSyncLogRepository,
    )
except ImportError as e:
    print(f"Aviso: Repositórios Cora não disponíveis: {e}")
