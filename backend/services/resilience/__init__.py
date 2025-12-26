"""
Conecta Plus - Resiliencia
Circuit Breaker, Retry, Fallback, Wrappers
"""

from .circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    CircuitBreakerConfig,
    CircuitBreakerError,
    get_circuit_breaker,
    get_all_circuit_breaker_stats,
)

from .retry import (
    retry,
    with_retry,
    RetryConfig,
    RetryContext,
    RetryError,
    calculate_delay,
    is_retriable,
    is_retriable_http_error,
    is_retriable_database_error,
    retry_async,
    DEFAULT_RETRIABLE_EXCEPTIONS,
)

from .wrappers import (
    with_circuit_breaker,
    ResilientDatabase,
    ResilientRedis,
    ResilientHTTPClient,
    get_resilient_redis,
    get_resilient_database,
    get_http_client,
    close_all_clients,
    get_all_resilience_stats,
    get_config_for_service,
    get_retry_config_for_service,
    DEFAULT_CONFIGS,
    DEFAULT_RETRY_CONFIGS,
)

__all__ = [
    # Circuit Breaker Core
    'CircuitBreaker',
    'CircuitState',
    'CircuitBreakerConfig',
    'CircuitBreakerError',
    'get_circuit_breaker',
    'get_all_circuit_breaker_stats',

    # Retry
    'retry',
    'with_retry',
    'RetryConfig',
    'RetryContext',
    'RetryError',
    'calculate_delay',
    'is_retriable',
    'is_retriable_http_error',
    'is_retriable_database_error',
    'retry_async',
    'DEFAULT_RETRIABLE_EXCEPTIONS',

    # Decorators
    'with_circuit_breaker',

    # Wrappers
    'ResilientDatabase',
    'ResilientRedis',
    'ResilientHTTPClient',

    # Factories
    'get_resilient_redis',
    'get_resilient_database',
    'get_http_client',
    'close_all_clients',

    # Utils
    'get_all_resilience_stats',
    'get_config_for_service',
    'get_retry_config_for_service',
    'DEFAULT_CONFIGS',
    'DEFAULT_RETRY_CONFIGS',
]
