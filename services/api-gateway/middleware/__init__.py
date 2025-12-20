"""
Conecta Plus - Middleware Package

Exporta funções para configurar todos os middlewares.
"""
from .rate_limit import (
    RateLimiter,
    RateLimitConfig,
    rate_limit_middleware,
    rate_limit,
    rate_limiter,
    get_rate_limit_config
)
from .logging import setup_logging_middleware, LoggingMiddleware, AuditMiddleware
from .security import (
    setup_security_middleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    IPBlockMiddleware,
    BruteForceProtectionMiddleware
)


def setup_all_middleware(app, settings=None):
    """
    Configura todos os middlewares na aplicação.

    Args:
        app: Instância FastAPI
        settings: Configurações (opcional)
    """
    # Segurança primeiro (mais externo)
    setup_security_middleware(app, settings)

    # Logging por último (mais interno)
    setup_logging_middleware(app)


__all__ = [
    # Rate limit original
    'RateLimiter',
    'RateLimitConfig',
    'rate_limit_middleware',
    'rate_limit',
    'rate_limiter',
    'get_rate_limit_config',
    # Novos
    "setup_all_middleware",
    "setup_logging_middleware",
    "setup_security_middleware",
    "LoggingMiddleware",
    "AuditMiddleware",
    "RateLimitMiddleware",
    "SecurityHeadersMiddleware",
    "IPBlockMiddleware",
    "BruteForceProtectionMiddleware"
]
