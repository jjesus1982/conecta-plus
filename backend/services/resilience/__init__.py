"""
Conecta Plus - Resiliência
Circuit Breaker, Retry, Fallback
"""

from .circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    CircuitBreakerConfig,
    CircuitBreakerError,
    get_circuit_breaker,
    get_all_circuit_breaker_stats,
)

__all__ = [
    'CircuitBreaker',
    'CircuitState',
    'CircuitBreakerConfig',
    'CircuitBreakerError',
    'get_circuit_breaker',
    'get_all_circuit_breaker_stats',
]
