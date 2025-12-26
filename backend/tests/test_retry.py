"""
Testes para o modulo de Retry com Backoff Exponencial
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
import time

from services.resilience.retry import (
    retry,
    with_retry,
    calculate_delay,
    is_retriable,
    is_retriable_http_error,
    is_retriable_database_error,
    RetryError,
    RetryContext,
    retry_async,
    DEFAULT_RETRIABLE_EXCEPTIONS,
)


class TestCalculateDelay:
    """Testes para calculo de delay com backoff exponencial."""

    def test_primeira_tentativa_delay_base(self):
        """Primeira tentativa deve usar delay base + jitter."""
        delay = calculate_delay(
            attempt=0,
            base_delay=1.0,
            max_delay=30.0,
            exponential_base=2.0,
            jitter_range=(0.0, 0.0)  # Sem jitter para teste deterministico
        )
        assert delay == 1.0

    def test_segunda_tentativa_delay_exponencial(self):
        """Segunda tentativa deve dobrar o delay."""
        delay = calculate_delay(
            attempt=1,
            base_delay=1.0,
            max_delay=30.0,
            exponential_base=2.0,
            jitter_range=(0.0, 0.0)
        )
        assert delay == 2.0

    def test_terceira_tentativa_delay_exponencial(self):
        """Terceira tentativa deve quadruplicar o delay base."""
        delay = calculate_delay(
            attempt=2,
            base_delay=1.0,
            max_delay=30.0,
            exponential_base=2.0,
            jitter_range=(0.0, 0.0)
        )
        assert delay == 4.0

    def test_delay_respects_max_delay(self):
        """Delay nunca deve exceder max_delay."""
        delay = calculate_delay(
            attempt=10,  # 2^10 = 1024, muito maior que max_delay
            base_delay=1.0,
            max_delay=30.0,
            exponential_base=2.0,
            jitter_range=(0.0, 0.0)
        )
        assert delay == 30.0

    def test_jitter_adicionado(self):
        """Jitter deve ser adicionado ao delay."""
        delays = [
            calculate_delay(
                attempt=0,
                base_delay=1.0,
                max_delay=30.0,
                exponential_base=2.0,
                jitter_range=(0.5, 1.0)
            )
            for _ in range(10)
        ]
        # Com jitter (0.5, 1.0), delay deve estar entre 1.5 e 2.0
        for delay in delays:
            assert 1.5 <= delay <= 2.0


class TestIsRetriable:
    """Testes para verificacao de excecoes retriaveis."""

    def test_connection_error_retriable(self):
        """ConnectionError deve ser retriavel."""
        assert is_retriable(ConnectionError("Connection refused"))

    def test_timeout_error_retriable(self):
        """TimeoutError deve ser retriavel."""
        assert is_retriable(TimeoutError("Request timed out"))

    def test_asyncio_timeout_retriable(self):
        """asyncio.TimeoutError deve ser retriavel."""
        assert is_retriable(asyncio.TimeoutError())

    def test_value_error_not_retriable(self):
        """ValueError nao deve ser retriavel por padrao."""
        assert not is_retriable(ValueError("Invalid value"))

    def test_custom_retriable_exceptions(self):
        """Excecoes customizadas devem ser retriaveis se configuradas."""
        assert is_retriable(
            ValueError("test"),
            retriable_exceptions=(ValueError,)
        )


class TestIsRetriableHTTPError:
    """Testes para verificacao de erros HTTP retriaveis."""

    def test_http_500_retriable(self):
        """HTTP 500 deve ser retriavel."""
        try:
            import httpx
            response = MagicMock()
            response.status_code = 500
            error = httpx.HTTPStatusError(
                "Server Error",
                request=MagicMock(),
                response=response
            )
            assert is_retriable_http_error(error)
        except ImportError:
            pytest.skip("httpx nao instalado")

    def test_http_503_retriable(self):
        """HTTP 503 deve ser retriavel."""
        try:
            import httpx
            response = MagicMock()
            response.status_code = 503
            error = httpx.HTTPStatusError(
                "Service Unavailable",
                request=MagicMock(),
                response=response
            )
            assert is_retriable_http_error(error)
        except ImportError:
            pytest.skip("httpx nao instalado")

    def test_http_400_not_retriable(self):
        """HTTP 400 nao deve ser retriavel."""
        try:
            import httpx
            response = MagicMock()
            response.status_code = 400
            error = httpx.HTTPStatusError(
                "Bad Request",
                request=MagicMock(),
                response=response
            )
            assert not is_retriable_http_error(error)
        except ImportError:
            pytest.skip("httpx nao instalado")


class TestRetryDecorator:
    """Testes para o decorador @retry."""

    @pytest.mark.asyncio
    async def test_sucesso_primeira_tentativa(self):
        """Funcao que sucede na primeira tentativa nao deve fazer retry."""
        call_count = 0

        @retry(max_retries=3, base_delay=0.01)
        async def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await successful_func()
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_apos_falha(self):
        """Funcao que falha deve fazer retry."""
        call_count = 0

        @retry(max_retries=3, base_delay=0.01)
        async def failing_then_success():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Connection failed")
            return "success"

        result = await failing_then_success()
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """Exceder max_retries deve levantar RetryError."""
        call_count = 0

        @retry(max_retries=2, base_delay=0.01)
        async def always_fails():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Always fails")

        with pytest.raises(RetryError) as exc_info:
            await always_fails()

        assert call_count == 3  # tentativa inicial + 2 retries
        assert exc_info.value.attempts == 3
        assert isinstance(exc_info.value.last_exception, ConnectionError)

    @pytest.mark.asyncio
    async def test_excecao_nao_retriavel_nao_faz_retry(self):
        """Excecao nao retriavel deve ser propagada imediatamente."""
        call_count = 0

        @retry(max_retries=3, base_delay=0.01)
        async def raises_value_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("Not retriable")

        with pytest.raises(ValueError):
            await raises_value_error()

        assert call_count == 1  # Nao deve fazer retry

    @pytest.mark.asyncio
    async def test_callback_on_retry(self):
        """Callback on_retry deve ser chamado antes de cada retry."""
        retry_info = []

        def on_retry_callback(exc, attempt, delay):
            retry_info.append({
                "exception": type(exc).__name__,
                "attempt": attempt,
                "delay": delay
            })

        @retry(max_retries=2, base_delay=0.01, on_retry=on_retry_callback)
        async def fails_twice():
            if len(retry_info) < 2:
                raise ConnectionError("Failing")
            return "success"

        result = await fails_twice()
        assert result == "success"
        assert len(retry_info) == 2
        assert retry_info[0]["attempt"] == 1
        assert retry_info[1]["attempt"] == 2


class TestRetryContext:
    """Testes para o context manager RetryContext."""

    @pytest.mark.asyncio
    async def test_retry_context_sucesso(self):
        """RetryContext deve permitir loop de retry."""
        attempts = []

        async with RetryContext(max_retries=3, base_delay=0.01) as ctx:
            async for attempt in ctx:
                attempts.append(attempt)
                if attempt == 2:
                    break  # Sucesso na segunda tentativa
                ctx.record_exception(ConnectionError("Retry"))

        assert attempts == [1, 2]

    @pytest.mark.asyncio
    async def test_retry_context_max_exceeded(self):
        """RetryContext deve levantar RetryError apos esgotar tentativas."""
        async with RetryContext(max_retries=2, base_delay=0.01) as ctx:
            with pytest.raises(RetryError):
                async for attempt in ctx:
                    ctx.record_exception(ConnectionError("Always fails"))


class TestWithRetryAlias:
    """Testes para o alias @with_retry."""

    @pytest.mark.asyncio
    async def test_with_retry_funciona(self):
        """@with_retry deve funcionar como @retry."""
        call_count = 0

        @with_retry(max_retries=2, base_delay=0.01)
        async def func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError()
            return "ok"

        result = await func()
        assert result == "ok"
        assert call_count == 2


class TestRetryAsync:
    """Testes para a funcao retry_async."""

    @pytest.mark.asyncio
    async def test_retry_async_funciona(self):
        """retry_async deve executar funcao com retry."""
        call_count = 0

        async def func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError()
            return "ok"

        result = await retry_async(func, max_retries=2, base_delay=0.01)
        assert result == "ok"
        assert call_count == 2


class TestSyncRetry:
    """Testes para retry em funcoes sincronas."""

    def test_sync_retry_funciona(self):
        """@retry deve funcionar com funcoes sincronas."""
        call_count = 0

        @retry(max_retries=2, base_delay=0.01)
        def sync_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError()
            return "ok"

        result = sync_func()
        assert result == "ok"
        assert call_count == 2


class TestBackoffTiming:
    """Testes para verificar timing do backoff exponencial."""

    @pytest.mark.asyncio
    async def test_backoff_timing(self):
        """Delays devem seguir padrao exponencial."""
        times = []

        @retry(
            max_retries=3,
            base_delay=0.1,
            max_delay=10.0,
            exponential_base=2.0,
            jitter_range=(0.0, 0.0)  # Sem jitter para teste deterministico
        )
        async def timed_func():
            times.append(time.time())
            if len(times) < 4:
                raise ConnectionError()
            return "ok"

        start = time.time()
        await timed_func()

        # Verificar delays entre tentativas
        # Delay 1: 0.1s, Delay 2: 0.2s, Delay 3: 0.4s
        # Total esperado: ~0.7s
        total_time = time.time() - start
        assert 0.6 < total_time < 1.0, f"Total time was {total_time}s"

        # Verificar delays individuais
        if len(times) >= 2:
            delay1 = times[1] - times[0]
            assert 0.09 < delay1 < 0.15, f"Delay 1 was {delay1}s"

        if len(times) >= 3:
            delay2 = times[2] - times[1]
            assert 0.18 < delay2 < 0.25, f"Delay 2 was {delay2}s"

        if len(times) >= 4:
            delay3 = times[3] - times[2]
            assert 0.38 < delay3 < 0.45, f"Delay 3 was {delay3}s"


class TestDatabaseRetriable:
    """Testes para verificacao de erros de database retriaveis."""

    def test_sqlalchemy_operational_error(self):
        """SQLAlchemy OperationalError deve ser retriavel."""
        try:
            from sqlalchemy.exc import OperationalError
            error = OperationalError("statement", {}, Exception())
            assert is_retriable_database_error(error)
        except ImportError:
            pytest.skip("SQLAlchemy nao instalado")

    def test_redis_connection_error(self):
        """Redis ConnectionError deve ser retriavel."""
        try:
            from redis.exceptions import ConnectionError as RedisConnectionError
            error = RedisConnectionError("Connection refused")
            assert is_retriable_database_error(error)
        except ImportError:
            pytest.skip("redis nao instalado")


class TestRetryWithHTTPErrors:
    """Testes para retry com erros HTTP."""

    @pytest.mark.asyncio
    async def test_retry_on_http_500(self):
        """Retry deve acontecer em HTTP 500."""
        call_count = 0

        try:
            import httpx

            @retry(max_retries=2, base_delay=0.01, check_http_errors=True)
            async def http_request():
                nonlocal call_count
                call_count += 1
                if call_count < 2:
                    response = MagicMock()
                    response.status_code = 500
                    raise httpx.HTTPStatusError(
                        "Server Error",
                        request=MagicMock(),
                        response=response
                    )
                return "ok"

            result = await http_request()
            assert result == "ok"
            assert call_count == 2

        except ImportError:
            pytest.skip("httpx nao instalado")

    @pytest.mark.asyncio
    async def test_no_retry_on_http_400(self):
        """Retry nao deve acontecer em HTTP 400."""
        call_count = 0

        try:
            import httpx

            @retry(max_retries=2, base_delay=0.01, check_http_errors=True)
            async def http_request():
                nonlocal call_count
                call_count += 1
                response = MagicMock()
                response.status_code = 400
                raise httpx.HTTPStatusError(
                    "Bad Request",
                    request=MagicMock(),
                    response=response
                )

            with pytest.raises(httpx.HTTPStatusError):
                await http_request()

            assert call_count == 1  # Sem retry

        except ImportError:
            pytest.skip("httpx nao instalado")
