"""
Conecta Plus - Circuit Breaker Pattern
Implementação de Circuit Breaker para resiliência de serviços externos
"""

import asyncio
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TypeVar, Generic, Callable, Awaitable, Optional, Dict, Any
from functools import wraps
import time

from ..observability import logger, LogContext


class CircuitState(Enum):
    """Estados do Circuit Breaker."""
    CLOSED = "CLOSED"       # Funcionando normalmente
    OPEN = "OPEN"           # Muitas falhas, bloqueando requests
    HALF_OPEN = "HALF_OPEN" # Testando recuperação


class CircuitBreakerError(Exception):
    """Exceção lançada quando o circuito está aberto."""

    def __init__(self, name: str, state: CircuitState, reset_time: Optional[datetime] = None):
        self.name = name
        self.state = state
        self.reset_time = reset_time
        super().__init__(f"Circuit breaker '{name}' is {state.value}")


@dataclass
class CircuitBreakerConfig:
    """Configuração do Circuit Breaker."""
    failure_threshold: int = 5          # Falhas antes de abrir o circuito
    success_threshold: int = 2          # Sucessos para fechar o circuito
    timeout: float = 5.0                # Timeout de request individual (segundos)
    reset_timeout: float = 30.0         # Tempo antes de tentar HALF_OPEN (segundos)
    half_open_max_calls: int = 3        # Máximo de chamadas em HALF_OPEN


@dataclass
class CircuitBreakerStats:
    """Estatísticas do Circuit Breaker."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    state_changes: int = 0


T = TypeVar('T')


class CircuitBreaker(Generic[T]):
    """
    Circuit Breaker Pattern para resiliência de serviços externos.

    Uso:
        circuit = CircuitBreaker("external-api", config, fallback=get_cached_data)
        result = await circuit.execute(lambda: fetch_from_api())
    """

    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
        fallback: Optional[Callable[[], Awaitable[T]]] = None
    ):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.fallback = fallback

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0
        self._last_failure_time: Optional[datetime] = None
        self._stats = CircuitBreakerStats()
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        """Estado atual do circuito."""
        return self._state

    @property
    def stats(self) -> Dict[str, Any]:
        """Estatísticas do circuit breaker."""
        return {
            "name": self.name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "total_calls": self._stats.total_calls,
            "successful_calls": self._stats.successful_calls,
            "failed_calls": self._stats.failed_calls,
            "rejected_calls": self._stats.rejected_calls,
            "state_changes": self._stats.state_changes,
            "last_failure": self._stats.last_failure_time.isoformat() if self._stats.last_failure_time else None,
            "last_success": self._stats.last_success_time.isoformat() if self._stats.last_success_time else None,
        }

    def _should_attempt_reset(self) -> bool:
        """Verifica se deve tentar resetar o circuito."""
        if not self._last_failure_time:
            return False

        time_since_failure = datetime.now() - self._last_failure_time
        return time_since_failure.total_seconds() >= self.config.reset_timeout

    async def _transition_to(self, new_state: CircuitState) -> None:
        """Transiciona para um novo estado."""
        if self._state != new_state:
            old_state = self._state
            self._state = new_state
            self._stats.state_changes += 1

            logger.info(
                f"Circuit breaker state change",
                circuit=self.name,
                old_state=old_state.value,
                new_state=new_state.value,
                failure_count=self._failure_count
            )

            if new_state == CircuitState.HALF_OPEN:
                self._half_open_calls = 0
                self._success_count = 0

    async def _on_success(self) -> None:
        """Chamado quando uma operação é bem sucedida."""
        async with self._lock:
            self._stats.successful_calls += 1
            self._stats.last_success_time = datetime.now()
            self._failure_count = 0

            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.config.success_threshold:
                    await self._transition_to(CircuitState.CLOSED)

    async def _on_failure(self) -> None:
        """Chamado quando uma operação falha."""
        async with self._lock:
            self._stats.failed_calls += 1
            self._stats.last_failure_time = datetime.now()
            self._failure_count += 1
            self._last_failure_time = datetime.now()
            self._success_count = 0

            if self._state == CircuitState.HALF_OPEN:
                await self._transition_to(CircuitState.OPEN)
            elif self._failure_count >= self.config.failure_threshold:
                await self._transition_to(CircuitState.OPEN)

    async def _execute_with_timeout(self, fn: Callable[[], Awaitable[T]]) -> T:
        """Executa a função com timeout."""
        try:
            return await asyncio.wait_for(fn(), timeout=self.config.timeout)
        except asyncio.TimeoutError:
            raise TimeoutError(f"Request timeout after {self.config.timeout}s")

    async def execute(self, fn: Callable[[], Awaitable[T]]) -> T:
        """
        Executa a função protegida pelo circuit breaker.

        Args:
            fn: Função assíncrona a ser executada

        Returns:
            Resultado da função ou do fallback

        Raises:
            CircuitBreakerError: Se o circuito está aberto e não há fallback
        """
        self._stats.total_calls += 1

        # Se o circuito está OPEN, verificar se deve tentar HALF_OPEN
        if self._state == CircuitState.OPEN:
            if self._should_attempt_reset():
                await self._transition_to(CircuitState.HALF_OPEN)
            else:
                self._stats.rejected_calls += 1

                logger.warning(
                    "Circuit breaker rejecting call",
                    circuit=self.name,
                    state=self._state.value
                )

                # Tentar fallback
                if self.fallback:
                    logger.info(f"Using fallback for {self.name}")
                    return await self.fallback()

                raise CircuitBreakerError(
                    self.name,
                    self._state,
                    self._last_failure_time + timedelta(seconds=self.config.reset_timeout)
                    if self._last_failure_time else None
                )

        # Se HALF_OPEN, limitar número de chamadas
        if self._state == CircuitState.HALF_OPEN:
            async with self._lock:
                if self._half_open_calls >= self.config.half_open_max_calls:
                    if self.fallback:
                        return await self.fallback()
                    raise CircuitBreakerError(self.name, self._state)
                self._half_open_calls += 1

        # Executar a função
        start_time = time.time()
        try:
            result = await self._execute_with_timeout(fn)
            await self._on_success()

            duration_ms = (time.time() - start_time) * 1000
            logger.external_call(
                service=self.name,
                endpoint="execute",
                success=True,
                duration_ms=round(duration_ms, 2)
            )

            return result

        except Exception as e:
            await self._on_failure()

            duration_ms = (time.time() - start_time) * 1000
            logger.external_call(
                service=self.name,
                endpoint="execute",
                success=False,
                duration_ms=round(duration_ms, 2),
                error=str(e)
            )

            # Tentar fallback em caso de erro
            if self.fallback:
                logger.info(f"Using fallback after error for {self.name}")
                try:
                    return await self.fallback()
                except Exception as fallback_error:
                    logger.error(f"Fallback also failed for {self.name}", exc=fallback_error)
                    raise e

            raise

    def reset(self) -> None:
        """Reset manual do circuit breaker."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0
        self._last_failure_time = None

        logger.info(f"Circuit breaker manually reset", circuit=self.name)


def circuit_breaker(
    name: str,
    config: Optional[CircuitBreakerConfig] = None,
    fallback_value: Optional[T] = None
):
    """
    Decorator para aplicar circuit breaker a uma função.

    Uso:
        @circuit_breaker("my-service", fallback_value=[])
        async def fetch_data():
            return await http_client.get("/data")
    """
    _circuit = CircuitBreaker(
        name,
        config,
        fallback=(lambda: asyncio.coroutine(lambda: fallback_value)()) if fallback_value else None
    )

    def decorator(fn: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(fn)
        async def wrapper(*args, **kwargs) -> T:
            return await _circuit.execute(lambda: fn(*args, **kwargs))
        wrapper.circuit = _circuit  # type: ignore
        return wrapper
    return decorator


# === Registry global de Circuit Breakers ===

_circuit_breakers: Dict[str, CircuitBreaker] = {}


def get_circuit_breaker(name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
    """Obtém ou cria um circuit breaker pelo nome."""
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(name, config)
    return _circuit_breakers[name]


def get_all_circuit_breaker_stats() -> Dict[str, Dict[str, Any]]:
    """Obtém estatísticas de todos os circuit breakers."""
    return {name: cb.stats for name, cb in _circuit_breakers.items()}
