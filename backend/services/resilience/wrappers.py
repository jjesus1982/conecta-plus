"""
Conecta Plus - Circuit Breaker Wrappers
Wrappers para integrar Circuit Breaker e Retry em diversos componentes
"""

import asyncio
from typing import Optional, Callable, TypeVar, Any, Dict, Tuple
from functools import wraps
import time

from .circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerError,
    CircuitState,
    get_circuit_breaker,
    get_all_circuit_breaker_stats,
)
from .retry import (
    retry,
    calculate_delay,
    is_retriable,
    RetryError,
    DEFAULT_RETRIABLE_EXCEPTIONS,
)
from ..observability import logger

T = TypeVar('T')


# === Configuracoes padrao para diferentes tipos de servico ===

DEFAULT_CONFIGS = {
    "database": CircuitBreakerConfig(
        failure_threshold=5,
        success_threshold=2,
        timeout=10.0,
        reset_timeout=30.0,
        half_open_max_calls=3
    ),
    "redis": CircuitBreakerConfig(
        failure_threshold=5,
        success_threshold=2,
        timeout=5.0,
        reset_timeout=30.0,
        half_open_max_calls=3
    ),
    "http_external": CircuitBreakerConfig(
        failure_threshold=5,
        success_threshold=2,
        timeout=30.0,
        reset_timeout=30.0,
        half_open_max_calls=3
    ),
    "hardware": CircuitBreakerConfig(
        failure_threshold=3,
        success_threshold=2,
        timeout=10.0,
        reset_timeout=60.0,
        half_open_max_calls=2
    ),
    "ldap": CircuitBreakerConfig(
        failure_threshold=3,
        success_threshold=2,
        timeout=15.0,
        reset_timeout=60.0,
        half_open_max_calls=2
    ),
    "oauth": CircuitBreakerConfig(
        failure_threshold=5,
        success_threshold=2,
        timeout=10.0,
        reset_timeout=30.0,
        half_open_max_calls=3
    ),
}


# Configuracoes de retry por tipo de servico
DEFAULT_RETRY_CONFIGS = {
    "database": {
        "max_retries": 3,
        "base_delay": 0.5,
        "max_delay": 10.0,
        "exponential_base": 2.0,
    },
    "redis": {
        "max_retries": 3,
        "base_delay": 0.2,
        "max_delay": 5.0,
        "exponential_base": 2.0,
    },
    "http_external": {
        "max_retries": 3,
        "base_delay": 1.0,
        "max_delay": 30.0,
        "exponential_base": 2.0,
    },
    "hardware": {
        "max_retries": 2,
        "base_delay": 1.0,
        "max_delay": 10.0,
        "exponential_base": 2.0,
    },
    "ldap": {
        "max_retries": 2,
        "base_delay": 1.0,
        "max_delay": 15.0,
        "exponential_base": 2.0,
    },
    "oauth": {
        "max_retries": 3,
        "base_delay": 0.5,
        "max_delay": 10.0,
        "exponential_base": 2.0,
    },
}


def get_config_for_service(service_type: str) -> CircuitBreakerConfig:
    """Obtem configuracao de circuit breaker para um tipo de servico."""
    return DEFAULT_CONFIGS.get(service_type, CircuitBreakerConfig())


def get_retry_config_for_service(service_type: str) -> Dict[str, Any]:
    """Obtem configuracao de retry para um tipo de servico."""
    return DEFAULT_RETRY_CONFIGS.get(service_type, {
        "max_retries": 3,
        "base_delay": 1.0,
        "max_delay": 30.0,
        "exponential_base": 2.0,
    })


# === Decorator para funcoes assincronas ===

def with_circuit_breaker(
    name: str,
    service_type: str = "http_external",
    fallback: Optional[Callable[[], Any]] = None,
    config: Optional[CircuitBreakerConfig] = None,
    enable_retry: bool = True,
    retry_config: Optional[Dict[str, Any]] = None
):
    """
    Decorator para proteger funcoes assincronas com circuit breaker e retry.

    Uso:
        @with_circuit_breaker("google-oauth", service_type="oauth")
        async def get_google_user_info(token: str):
            return await httpx.get(...)

        @with_circuit_breaker("database", enable_retry=True, retry_config={"max_retries": 5})
        async def fetch_user(user_id: str):
            return await db.get_user(user_id)

    Args:
        name: Nome unico do circuit breaker
        service_type: Tipo de servico (database, redis, http_external, hardware, ldap, oauth)
        fallback: Funcao de fallback (deve retornar valor compativel)
        config: Configuracao customizada de circuit breaker (sobrescreve service_type)
        enable_retry: Se True, aplica retry antes do circuit breaker
        retry_config: Configuracao customizada de retry (sobrescreve service_type)
    """
    cb_config = config or get_config_for_service(service_type)
    circuit = get_circuit_breaker(name, cb_config)

    # Configuracao de retry
    rt_config = retry_config or get_retry_config_for_service(service_type)

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        # Aplicar retry se habilitado
        if enable_retry:
            fn_with_retry = retry(
                max_retries=rt_config.get("max_retries", 3),
                base_delay=rt_config.get("base_delay", 1.0),
                max_delay=rt_config.get("max_delay", 30.0),
                exponential_base=rt_config.get("exponential_base", 2.0),
            )(fn)
        else:
            fn_with_retry = fn

        @wraps(fn)
        async def wrapper(*args, **kwargs):
            async def fallback_fn():
                if fallback:
                    result = fallback()
                    if asyncio.iscoroutine(result):
                        return await result
                    return result
                return None

            # Configurar fallback no circuit se fornecido
            if fallback:
                circuit.fallback = fallback_fn

            return await circuit.execute(lambda: fn_with_retry(*args, **kwargs))

        # Expor o circuit breaker para inspecao
        wrapper.circuit = circuit
        wrapper.retry_enabled = enable_retry
        return wrapper

    return decorator


# === Database Wrapper ===

class ResilientDatabase:
    """
    Wrapper para operacoes de banco de dados com circuit breaker e retry.
    Protege contra falhas de conexao e timeouts.
    """

    def __init__(
        self,
        session_factory,
        name: str = "database",
        enable_retry: bool = True,
        retry_config: Optional[Dict[str, Any]] = None
    ):
        self.session_factory = session_factory
        self.circuit = get_circuit_breaker(
            name,
            get_config_for_service("database")
        )
        self._name = name
        self._enable_retry = enable_retry
        self._retry_config = retry_config or get_retry_config_for_service("database")

    async def execute(self, operation: Callable, *args, **kwargs):
        """
        Executa uma operacao de banco protegida pelo circuit breaker e retry.

        Args:
            operation: Funcao que recebe a sessao como primeiro argumento
            *args, **kwargs: Argumentos adicionais para a operacao
        """
        async def db_operation():
            db = self.session_factory()
            try:
                # Se a operacao e sincrona, executa-la em thread separada
                if asyncio.iscoroutinefunction(operation):
                    result = await operation(db, *args, **kwargs)
                else:
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(
                        None,
                        lambda: operation(db, *args, **kwargs)
                    )
                return result
            finally:
                db.close()

        # Aplicar retry se habilitado
        if self._enable_retry:
            @retry(
                max_retries=self._retry_config.get("max_retries", 3),
                base_delay=self._retry_config.get("base_delay", 0.5),
                max_delay=self._retry_config.get("max_delay", 10.0),
                exponential_base=self._retry_config.get("exponential_base", 2.0),
            )
            async def db_operation_with_retry():
                return await db_operation()

            return await self.circuit.execute(db_operation_with_retry)
        else:
            return await self.circuit.execute(db_operation)

    @property
    def stats(self) -> Dict[str, Any]:
        return self.circuit.stats

    @property
    def state(self) -> CircuitState:
        return self.circuit.state

    @property
    def retry_enabled(self) -> bool:
        return self._enable_retry


# === Redis Wrapper ===

class ResilientRedis:
    """
    Wrapper para operacoes Redis com circuit breaker e retry.
    Protege contra falhas de conexao.
    """

    def __init__(
        self,
        redis_client,
        name: str = "redis",
        enable_retry: bool = True,
        retry_config: Optional[Dict[str, Any]] = None
    ):
        self.redis = redis_client
        self.circuit = get_circuit_breaker(
            name,
            get_config_for_service("redis")
        )
        self._name = name
        self._enable_retry = enable_retry
        self._retry_config = retry_config or get_retry_config_for_service("redis")

    async def _execute_with_retry(self, operation: Callable, fallback: Any = None):
        """Executa operacao com retry e circuit breaker."""
        if self._enable_retry:
            @retry(
                max_retries=self._retry_config.get("max_retries", 3),
                base_delay=self._retry_config.get("base_delay", 0.2),
                max_delay=self._retry_config.get("max_delay", 5.0),
                exponential_base=self._retry_config.get("exponential_base", 2.0),
            )
            async def operation_with_retry():
                return await operation()

            try:
                return await self.circuit.execute(operation_with_retry)
            except (CircuitBreakerError, RetryError):
                return fallback
        else:
            try:
                return await self.circuit.execute(operation)
            except CircuitBreakerError:
                return fallback

    async def get(self, key: str, default: Any = None) -> Any:
        """GET com fallback para valor default."""
        async def operation():
            value = await self.redis.get(key)
            return value if value is not None else default

        result = await self._execute_with_retry(operation, default)
        if result is None:
            logger.warning(f"Redis circuit open, returning default for {key}")
        return result if result is not None else default

    async def set(self, key: str, value: Any, ex: int = None) -> bool:
        """SET com protecao de circuit breaker e retry."""
        async def operation():
            if ex:
                return await self.redis.set(key, value, ex=ex)
            return await self.redis.set(key, value)

        result = await self._execute_with_retry(operation, False)
        if result is False:
            logger.warning(f"Redis SET failed for {key}")
        return result

    async def delete(self, key: str) -> bool:
        """DELETE com protecao de circuit breaker e retry."""
        async def operation():
            return await self.redis.delete(key)

        result = await self._execute_with_retry(operation, False)
        if result is False:
            logger.warning(f"Redis DELETE failed for {key}")
        return result

    async def hget(self, name: str, key: str, default: Any = None) -> Any:
        """HGET com fallback."""
        async def operation():
            value = await self.redis.hget(name, key)
            return value if value is not None else default

        return await self._execute_with_retry(operation, default)

    async def hset(self, name: str, key: str, value: Any) -> bool:
        """HSET com protecao."""
        async def operation():
            return await self.redis.hset(name, key, value)

        return await self._execute_with_retry(operation, False)

    async def lpush(self, key: str, *values) -> bool:
        """LPUSH com protecao."""
        async def operation():
            return await self.redis.lpush(key, *values)

        return await self._execute_with_retry(operation, False)

    async def ping(self) -> bool:
        """PING para health check."""
        async def operation():
            return await self.redis.ping()

        try:
            return await self.circuit.execute(operation)
        except (CircuitBreakerError, Exception):
            return False

    @property
    def stats(self) -> Dict[str, Any]:
        return self.circuit.stats

    @property
    def state(self) -> CircuitState:
        return self.circuit.state

    @property
    def retry_enabled(self) -> bool:
        return self._enable_retry


# === HTTP Client Wrapper ===

class ResilientHTTPClient:
    """
    Wrapper para clientes HTTP com circuit breaker e retry.
    Protege chamadas a APIs externas.
    """

    def __init__(
        self,
        name: str,
        base_url: str = "",
        service_type: str = "http_external",
        default_timeout: float = 30.0,
        enable_retry: bool = True,
        retry_config: Optional[Dict[str, Any]] = None
    ):
        self.name = name
        self.base_url = base_url.rstrip('/')
        self.default_timeout = default_timeout
        self.circuit = get_circuit_breaker(
            name,
            get_config_for_service(service_type)
        )
        self._client = None
        self._enable_retry = enable_retry
        self._retry_config = retry_config or get_retry_config_for_service(service_type)

    async def _get_client(self):
        if self._client is None:
            import httpx
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.default_timeout
            )
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    async def request(
        self,
        method: str,
        url: str,
        fallback_value: Any = None,
        **kwargs
    ) -> Any:
        """
        Faz requisicao HTTP protegida pelo circuit breaker e retry.

        Args:
            method: GET, POST, PUT, DELETE, etc.
            url: URL (relativa ao base_url ou absoluta)
            fallback_value: Valor retornado se circuit estiver aberto
            **kwargs: Argumentos passados para httpx

        Returns:
            Response object ou fallback_value
        """
        async def operation():
            client = await self._get_client()
            full_url = url if url.startswith('http') else f"{self.base_url}{url}"
            response = await client.request(method, full_url, **kwargs)
            response.raise_for_status()
            return response

        # Aplicar retry se habilitado
        if self._enable_retry:
            @retry(
                max_retries=self._retry_config.get("max_retries", 3),
                base_delay=self._retry_config.get("base_delay", 1.0),
                max_delay=self._retry_config.get("max_delay", 30.0),
                exponential_base=self._retry_config.get("exponential_base", 2.0),
                check_http_errors=True,  # Retry em HTTP 5xx
            )
            async def operation_with_retry():
                return await operation()

            try:
                return await self.circuit.execute(operation_with_retry)
            except (CircuitBreakerError, RetryError) as e:
                logger.warning(
                    f"HTTP request failed",
                    client=self.name,
                    url=url,
                    error=str(e)
                )
                return fallback_value
        else:
            try:
                return await self.circuit.execute(operation)
            except CircuitBreakerError:
                logger.warning(
                    f"HTTP circuit '{self.name}' open, returning fallback",
                    url=url
                )
                return fallback_value

    async def get(self, url: str, fallback_value: Any = None, **kwargs):
        return await self.request("GET", url, fallback_value, **kwargs)

    async def post(self, url: str, fallback_value: Any = None, **kwargs):
        return await self.request("POST", url, fallback_value, **kwargs)

    async def put(self, url: str, fallback_value: Any = None, **kwargs):
        return await self.request("PUT", url, fallback_value, **kwargs)

    async def delete(self, url: str, fallback_value: Any = None, **kwargs):
        return await self.request("DELETE", url, fallback_value, **kwargs)

    @property
    def stats(self) -> Dict[str, Any]:
        return self.circuit.stats

    @property
    def state(self) -> CircuitState:
        return self.circuit.state

    @property
    def retry_enabled(self) -> bool:
        return self._enable_retry


# === Factory Functions ===

_resilient_redis: Optional[ResilientRedis] = None
_resilient_db: Optional[ResilientDatabase] = None
_http_clients: Dict[str, ResilientHTTPClient] = {}


async def get_resilient_redis(redis_url: str = None) -> ResilientRedis:
    """
    Obtém instância singleton do Redis resiliente.
    """
    global _resilient_redis

    if _resilient_redis is None:
        import redis.asyncio as redis_lib
        import os

        url = redis_url or os.getenv('REDIS_URL', 'redis://localhost:6379')
        client = await redis_lib.from_url(url)
        _resilient_redis = ResilientRedis(client)

    return _resilient_redis


def get_resilient_database(session_factory) -> ResilientDatabase:
    """
    Obtém instância do Database resiliente.
    """
    global _resilient_db

    if _resilient_db is None:
        _resilient_db = ResilientDatabase(session_factory)

    return _resilient_db


def get_http_client(
    name: str,
    base_url: str = "",
    service_type: str = "http_external"
) -> ResilientHTTPClient:
    """
    Obtém ou cria um HTTP client resiliente.
    Reutiliza clients existentes pelo nome.
    """
    if name not in _http_clients:
        _http_clients[name] = ResilientHTTPClient(name, base_url, service_type)

    return _http_clients[name]


async def close_all_clients():
    """Fecha todos os clientes HTTP."""
    for client in _http_clients.values():
        await client.close()
    _http_clients.clear()


# === Utilitário para Health Check ===

def get_all_resilience_stats() -> Dict[str, Any]:
    """
    Obtém estatísticas de todos os circuit breakers e wrappers.
    """
    stats = {
        "circuit_breakers": get_all_circuit_breaker_stats(),
        "wrappers": {
            "redis": _resilient_redis.stats if _resilient_redis else None,
            "database": _resilient_db.stats if _resilient_db else None,
            "http_clients": {
                name: client.stats
                for name, client in _http_clients.items()
            }
        },
        "summary": {
            "total_circuits": len(get_all_circuit_breaker_stats()),
            "open_circuits": sum(
                1 for cb in get_all_circuit_breaker_stats().values()
                if cb.get("state") == "OPEN"
            ),
            "half_open_circuits": sum(
                1 for cb in get_all_circuit_breaker_stats().values()
                if cb.get("state") == "HALF_OPEN"
            ),
        }
    }

    return stats
