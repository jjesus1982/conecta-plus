"""
Conecta Plus - Retry com Backoff Exponencial
Implementa retry automatico para operacoes que podem falhar temporariamente
"""

import asyncio
import random
import time
from functools import wraps
from typing import Type, Tuple, Optional, Callable, TypeVar, Any, Union
from dataclasses import dataclass

from ..observability import logger

# Type vars para generics
T = TypeVar('T')
F = TypeVar('F', bound=Callable[..., Any])


# === Excecoes Retriaveis ===

class RetryError(Exception):
    """Excecao lancada apos esgotar todas as tentativas de retry."""

    def __init__(
        self,
        message: str,
        attempts: int,
        last_exception: Optional[Exception] = None
    ):
        self.attempts = attempts
        self.last_exception = last_exception
        super().__init__(f"{message} after {attempts} attempts")


# Excecoes que devem triggerar retry por padrao
DEFAULT_RETRIABLE_EXCEPTIONS: Tuple[Type[Exception], ...] = (
    ConnectionError,
    ConnectionResetError,
    ConnectionRefusedError,
    ConnectionAbortedError,
    TimeoutError,
    asyncio.TimeoutError,
    OSError,  # Inclui erros de rede genericos
)


# Excecoes de banco de dados retriaveis (adicionadas separadamente)
DATABASE_RETRIABLE_EXCEPTIONS: Tuple[Type[Exception], ...] = (
    # SQLAlchemy / psycopg2 connection errors
    # Importados dinamicamente para evitar dependencias obrigatorias
)


def is_retriable_http_error(exception: Exception) -> bool:
    """
    Verifica se uma excecao HTTP e retriavel (5xx errors).
    Suporta httpx e requests.
    """
    # Verificar httpx
    try:
        import httpx
        if isinstance(exception, httpx.HTTPStatusError):
            return 500 <= exception.response.status_code < 600
    except ImportError:
        pass

    # Verificar requests
    try:
        from requests.exceptions import HTTPError
        if isinstance(exception, HTTPError):
            if exception.response is not None:
                return 500 <= exception.response.status_code < 600
    except ImportError:
        pass

    return False


def is_retriable_database_error(exception: Exception) -> bool:
    """
    Verifica se uma excecao de banco de dados e retriavel.
    """
    # SQLAlchemy OperationalError (connection issues)
    try:
        from sqlalchemy.exc import OperationalError, InterfaceError
        if isinstance(exception, (OperationalError, InterfaceError)):
            return True
    except ImportError:
        pass

    # psycopg2 connection errors
    try:
        import psycopg2
        if isinstance(exception, (
            psycopg2.OperationalError,
            psycopg2.InterfaceError,
        )):
            return True
    except ImportError:
        pass

    # Redis connection errors
    try:
        from redis.exceptions import ConnectionError as RedisConnectionError
        from redis.exceptions import TimeoutError as RedisTimeoutError
        if isinstance(exception, (RedisConnectionError, RedisTimeoutError)):
            return True
    except ImportError:
        pass

    return False


def is_retriable(
    exception: Exception,
    retriable_exceptions: Tuple[Type[Exception], ...] = DEFAULT_RETRIABLE_EXCEPTIONS,
    check_http: bool = True,
    check_database: bool = True
) -> bool:
    """
    Verifica se uma excecao deve triggerar retry.

    Args:
        exception: A excecao a verificar
        retriable_exceptions: Tuple de tipos de excecao retriaveis
        check_http: Se deve verificar erros HTTP 5xx
        check_database: Se deve verificar erros de database

    Returns:
        True se a excecao e retriavel
    """
    # Verificar tipos diretos
    if isinstance(exception, retriable_exceptions):
        return True

    # Verificar HTTP 5xx
    if check_http and is_retriable_http_error(exception):
        return True

    # Verificar database errors
    if check_database and is_retriable_database_error(exception):
        return True

    return False


# === Calculo de Delay ===

@dataclass
class RetryConfig:
    """Configuracao do retry."""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    jitter_range: Tuple[float, float] = (0.0, 1.0)
    retriable_exceptions: Tuple[Type[Exception], ...] = DEFAULT_RETRIABLE_EXCEPTIONS
    check_http_errors: bool = True
    check_database_errors: bool = True


def calculate_delay(
    attempt: int,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    jitter_range: Tuple[float, float] = (0.0, 1.0)
) -> float:
    """
    Calcula o delay para a proxima tentativa usando backoff exponencial com jitter.

    Formula: min(max_delay, base_delay * (exponential_base ** attempt)) + random_jitter

    Args:
        attempt: Numero da tentativa atual (0-indexed)
        base_delay: Delay base em segundos
        max_delay: Delay maximo em segundos
        exponential_base: Base do crescimento exponencial
        jitter_range: Tupla (min, max) do jitter aleatorio em segundos

    Returns:
        Delay em segundos para aguardar
    """
    # Calcular delay exponencial
    exponential_delay = base_delay * (exponential_base ** attempt)

    # Limitar ao max_delay
    capped_delay = min(exponential_delay, max_delay)

    # Adicionar jitter aleatorio
    jitter = random.uniform(jitter_range[0], jitter_range[1])

    return capped_delay + jitter


# === Decorador Retry ===

def retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    jitter_range: Tuple[float, float] = (0.0, 1.0),
    retriable_exceptions: Tuple[Type[Exception], ...] = DEFAULT_RETRIABLE_EXCEPTIONS,
    check_http_errors: bool = True,
    check_database_errors: bool = True,
    on_retry: Optional[Callable[[Exception, int, float], None]] = None
) -> Callable[[F], F]:
    """
    Decorador para adicionar retry com backoff exponencial a funcoes async.

    Args:
        max_retries: Numero maximo de tentativas (default 3)
        base_delay: Delay base em segundos (default 1.0)
        max_delay: Delay maximo em segundos (default 30.0)
        exponential_base: Base do crescimento exponencial (default 2.0)
        jitter_range: Tupla (min, max) do jitter aleatorio (default 0-1s)
        retriable_exceptions: Tipos de excecao que devem triggerar retry
        check_http_errors: Se deve verificar HTTP 5xx automaticamente
        check_database_errors: Se deve verificar database errors automaticamente
        on_retry: Callback chamado antes de cada retry (exception, attempt, delay)

    Uso:
        @retry(max_retries=5, base_delay=0.5)
        async def fetch_data():
            return await http_client.get("/data")

        @retry(retriable_exceptions=(ValueError, KeyError))
        async def process_data(data):
            return parse(data)

    Returns:
        Funcao decorada com retry
    """

    def decorator(func: F) -> F:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            last_exception: Optional[Exception] = None

            for attempt in range(max_retries + 1):  # +1 para incluir tentativa inicial
                try:
                    result = await func(*args, **kwargs)

                    # Log sucesso apos retry
                    if attempt > 0:
                        logger.info(
                            f"Retry successful",
                            function=func.__name__,
                            attempt=attempt + 1,
                            total_attempts=attempt + 1
                        )

                    return result

                except Exception as e:
                    last_exception = e

                    # Verificar se a excecao e retriavel
                    if not is_retriable(
                        e,
                        retriable_exceptions,
                        check_http_errors,
                        check_database_errors
                    ):
                        logger.warning(
                            f"Non-retriable exception",
                            function=func.__name__,
                            exception_type=type(e).__name__,
                            exception_message=str(e)
                        )
                        raise

                    # Se foi a ultima tentativa, propagar a excecao
                    if attempt >= max_retries:
                        logger.error(
                            f"Max retries exceeded",
                            function=func.__name__,
                            max_retries=max_retries,
                            exception_type=type(e).__name__,
                            exception_message=str(e)
                        )
                        raise RetryError(
                            f"Operation {func.__name__} failed",
                            attempts=attempt + 1,
                            last_exception=e
                        ) from e

                    # Calcular delay
                    delay = calculate_delay(
                        attempt,
                        base_delay,
                        max_delay,
                        exponential_base,
                        jitter_range
                    )

                    # Log do retry
                    logger.warning(
                        f"Retrying operation",
                        function=func.__name__,
                        attempt=attempt + 1,
                        max_retries=max_retries,
                        delay_seconds=round(delay, 2),
                        exception_type=type(e).__name__,
                        exception_message=str(e)
                    )

                    # Callback on_retry
                    if on_retry:
                        try:
                            on_retry(e, attempt + 1, delay)
                        except Exception:
                            pass  # Ignorar erros do callback

                    # Aguardar antes do proximo retry
                    await asyncio.sleep(delay)

            # Nao deveria chegar aqui, mas por seguranca
            raise RetryError(
                f"Operation {func.__name__} failed",
                attempts=max_retries + 1,
                last_exception=last_exception
            )

        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            last_exception: Optional[Exception] = None

            for attempt in range(max_retries + 1):
                try:
                    result = func(*args, **kwargs)

                    if attempt > 0:
                        logger.info(
                            f"Retry successful",
                            function=func.__name__,
                            attempt=attempt + 1,
                            total_attempts=attempt + 1
                        )

                    return result

                except Exception as e:
                    last_exception = e

                    if not is_retriable(
                        e,
                        retriable_exceptions,
                        check_http_errors,
                        check_database_errors
                    ):
                        raise

                    if attempt >= max_retries:
                        raise RetryError(
                            f"Operation {func.__name__} failed",
                            attempts=attempt + 1,
                            last_exception=e
                        ) from e

                    delay = calculate_delay(
                        attempt,
                        base_delay,
                        max_delay,
                        exponential_base,
                        jitter_range
                    )

                    logger.warning(
                        f"Retrying operation",
                        function=func.__name__,
                        attempt=attempt + 1,
                        max_retries=max_retries,
                        delay_seconds=round(delay, 2),
                        exception_type=type(e).__name__,
                        exception_message=str(e)
                    )

                    if on_retry:
                        try:
                            on_retry(e, attempt + 1, delay)
                        except Exception:
                            pass

                    time.sleep(delay)

            raise RetryError(
                f"Operation {func.__name__} failed",
                attempts=max_retries + 1,
                last_exception=last_exception
            )

        # Retornar wrapper apropriado baseado no tipo da funcao
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        else:
            return sync_wrapper  # type: ignore

    return decorator


# === Context Manager para Retry ===

class RetryContext:
    """
    Context manager para retry em blocos de codigo.

    Uso:
        async with RetryContext(max_retries=3) as ctx:
            async for attempt in ctx:
                result = await some_operation()
                if result.ok:
                    break  # Sucesso, sair do loop
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential_base: float = 2.0,
        jitter_range: Tuple[float, float] = (0.0, 1.0),
        retriable_exceptions: Tuple[Type[Exception], ...] = DEFAULT_RETRIABLE_EXCEPTIONS
    ):
        self.config = RetryConfig(
            max_retries=max_retries,
            base_delay=base_delay,
            max_delay=max_delay,
            exponential_base=exponential_base,
            jitter_range=jitter_range,
            retriable_exceptions=retriable_exceptions
        )
        self._attempt = 0
        self._last_exception: Optional[Exception] = None

    @property
    def attempt(self) -> int:
        """Numero da tentativa atual (1-indexed)."""
        return self._attempt

    @property
    def last_exception(self) -> Optional[Exception]:
        """Ultima excecao capturada."""
        return self._last_exception

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return False

    def __aiter__(self):
        return self

    async def __anext__(self) -> int:
        # Se ja excedeu max_retries, parar
        if self._attempt > self.config.max_retries:
            if self._last_exception:
                raise RetryError(
                    "Max retries exceeded",
                    attempts=self._attempt,
                    last_exception=self._last_exception
                )
            raise StopAsyncIteration

        # Se nao e a primeira tentativa, aguardar delay
        if self._attempt > 0 and self._last_exception:
            delay = calculate_delay(
                self._attempt - 1,
                self.config.base_delay,
                self.config.max_delay,
                self.config.exponential_base,
                self.config.jitter_range
            )

            logger.warning(
                "Retrying operation",
                attempt=self._attempt + 1,
                max_retries=self.config.max_retries,
                delay_seconds=round(delay, 2)
            )

            await asyncio.sleep(delay)

        self._attempt += 1
        return self._attempt

    def record_exception(self, exception: Exception) -> bool:
        """
        Registra uma excecao. Retorna True se deve tentar retry.
        """
        self._last_exception = exception

        if not is_retriable(exception, self.config.retriable_exceptions):
            return False

        return self._attempt <= self.config.max_retries


# === Funcoes Utilitarias ===

async def retry_async(
    func: Callable[..., Any],
    *args,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    **kwargs
) -> Any:
    """
    Executa uma funcao async com retry.

    Uso:
        result = await retry_async(fetch_data, url, max_retries=5)
    """
    @retry(max_retries=max_retries, base_delay=base_delay, max_delay=max_delay)
    async def _wrapper():
        return await func(*args, **kwargs)

    return await _wrapper()


def with_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0
) -> Callable[[F], F]:
    """
    Alias simplificado para @retry com configuracoes padrao.

    Uso:
        @with_retry()
        async def fetch_data():
            ...

        @with_retry(max_retries=5)
        async def critical_operation():
            ...
    """
    return retry(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay
    )


# === Exports ===

__all__ = [
    # Decoradores
    'retry',
    'with_retry',

    # Classes
    'RetryConfig',
    'RetryContext',
    'RetryError',

    # Funcoes
    'calculate_delay',
    'is_retriable',
    'is_retriable_http_error',
    'is_retriable_database_error',
    'retry_async',

    # Constantes
    'DEFAULT_RETRIABLE_EXCEPTIONS',
]
