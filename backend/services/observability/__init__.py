"""
Conecta Plus - Observabilidade
Logging estruturado, métricas e tracing
"""

from .logger import (
    logger,
    get_logger,
    StructuredLogger,
    LogContext,
    with_correlation_id,
)

__all__ = [
    'logger',
    'get_logger',
    'StructuredLogger',
    'LogContext',
    'with_correlation_id',
]
