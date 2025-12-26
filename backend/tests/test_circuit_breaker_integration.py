"""
Conecta Plus - Testes de Integração do Circuit Breaker
Verifica funcionamento dos wrappers e integrações
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from services.resilience import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerError,
    CircuitState,
    get_circuit_breaker,
    get_all_circuit_breaker_stats,
    with_circuit_breaker,
    ResilientRedis,
    ResilientHTTPClient,
    get_config_for_service,
    DEFAULT_CONFIGS,
)


# === Testes de Configuracao ===

class TestCircuitBreakerConfig:
    """Testes de configuracao do Circuit Breaker."""

    def test_default_configs_exist(self):
        """Verifica que configuracoes default existem."""
        assert "database" in DEFAULT_CONFIGS
        assert "redis" in DEFAULT_CONFIGS
        assert "http_external" in DEFAULT_CONFIGS
        assert "hardware" in DEFAULT_CONFIGS
        assert "ldap" in DEFAULT_CONFIGS
        assert "oauth" in DEFAULT_CONFIGS

    def test_database_config_thresholds(self):
        """Verifica thresholds da config de database."""
        config = get_config_for_service("database")
        assert config.failure_threshold == 5
        assert config.reset_timeout == 30.0
        assert config.half_open_max_calls == 3

    def test_hardware_config_thresholds(self):
        """Verifica thresholds da config de hardware."""
        config = get_config_for_service("hardware")
        assert config.failure_threshold == 3
        assert config.reset_timeout == 60.0
        assert config.half_open_max_calls == 2


# === Testes do Circuit Breaker Core ===

class TestCircuitBreakerCore:
    """Testes do circuit breaker core."""

    @pytest.fixture
    def circuit(self):
        """Cria circuit breaker para testes."""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=2,
            timeout=5.0,
            reset_timeout=1.0,
            half_open_max_calls=2
        )
        return CircuitBreaker("test-circuit", config)

    @pytest.mark.asyncio
    async def test_initial_state_is_closed(self, circuit):
        """Verifica que estado inicial e CLOSED."""
        assert circuit.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_success_keeps_circuit_closed(self, circuit):
        """Sucesso mantem circuito fechado."""
        async def success_fn():
            return "ok"

        result = await circuit.execute(success_fn)
        assert result == "ok"
        assert circuit.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_failures_open_circuit(self, circuit):
        """Falhas abrem o circuito."""
        async def fail_fn():
            raise Exception("falha")

        # Falhar 3 vezes (failure_threshold)
        for _ in range(3):
            with pytest.raises(Exception):
                await circuit.execute(fail_fn)

        assert circuit.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_open_circuit_rejects_calls(self, circuit):
        """Circuito aberto rejeita chamadas."""
        async def fail_fn():
            raise Exception("falha")

        # Abrir circuito
        for _ in range(3):
            with pytest.raises(Exception):
                await circuit.execute(fail_fn)

        # Proxima chamada deve ser rejeitada
        async def should_not_run():
            return "nao deveria executar"

        with pytest.raises(CircuitBreakerError):
            await circuit.execute(should_not_run)

    @pytest.mark.asyncio
    async def test_circuit_stats(self, circuit):
        """Verifica estatisticas do circuit."""
        async def success_fn():
            return "ok"

        await circuit.execute(success_fn)
        await circuit.execute(success_fn)

        stats = circuit.stats
        assert stats["name"] == "test-circuit"
        assert stats["state"] == "CLOSED"
        assert stats["successful_calls"] == 2
        assert stats["total_calls"] == 2

    @pytest.mark.asyncio
    async def test_reset_closes_circuit(self, circuit):
        """Reset fecha o circuito."""
        async def fail_fn():
            raise Exception("falha")

        # Abrir circuito
        for _ in range(3):
            with pytest.raises(Exception):
                await circuit.execute(fail_fn)

        assert circuit.state == CircuitState.OPEN

        # Reset
        circuit.reset()
        assert circuit.state == CircuitState.CLOSED


# === Testes do Decorator ===

class TestWithCircuitBreakerDecorator:
    """Testes do decorator with_circuit_breaker."""

    @pytest.mark.asyncio
    async def test_decorator_protects_function(self):
        """Decorator protege funcao com circuit breaker."""
        call_count = 0

        @with_circuit_breaker("test-decorator", service_type="http_external")
        async def protected_function():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await protected_function()
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_decorator_exposes_circuit(self):
        """Decorator expoe o circuit breaker."""
        @with_circuit_breaker("test-exposed", service_type="oauth")
        async def protected_function():
            return "ok"

        assert hasattr(protected_function, 'circuit')
        assert protected_function.circuit.name == "test-exposed"


# === Testes do ResilientRedis ===

class TestResilientRedis:
    """Testes do wrapper Redis resiliente."""

    @pytest.fixture
    def mock_redis(self):
        """Mock do cliente Redis."""
        mock = AsyncMock()
        mock.get = AsyncMock(return_value="value")
        mock.set = AsyncMock(return_value=True)
        mock.delete = AsyncMock(return_value=1)
        mock.ping = AsyncMock(return_value=True)
        return mock

    @pytest.fixture
    def resilient_redis(self, mock_redis):
        """Cria ResilientRedis com mock."""
        return ResilientRedis(mock_redis, "test-redis")

    @pytest.mark.asyncio
    async def test_get_returns_value(self, resilient_redis, mock_redis):
        """GET retorna valor do Redis."""
        result = await resilient_redis.get("key")
        assert result == "value"
        mock_redis.get.assert_called_once_with("key")

    @pytest.mark.asyncio
    async def test_get_returns_default_on_miss(self, resilient_redis, mock_redis):
        """GET retorna default quando chave nao existe."""
        mock_redis.get = AsyncMock(return_value=None)
        result = await resilient_redis.get("key", default="default")
        assert result == "default"

    @pytest.mark.asyncio
    async def test_set_returns_success(self, resilient_redis, mock_redis):
        """SET retorna sucesso."""
        result = await resilient_redis.set("key", "value")
        assert result == True

    @pytest.mark.asyncio
    async def test_ping_checks_connection(self, resilient_redis, mock_redis):
        """PING verifica conexao."""
        result = await resilient_redis.ping()
        assert result == True

    @pytest.mark.asyncio
    async def test_circuit_stats_available(self, resilient_redis):
        """Estatisticas do circuit estao disponiveis."""
        stats = resilient_redis.stats
        assert "name" in stats
        assert "state" in stats


# === Testes do ResilientHTTPClient ===

class TestResilientHTTPClient:
    """Testes do cliente HTTP resiliente."""

    @pytest.fixture
    def http_client(self):
        """Cria cliente HTTP para testes."""
        return ResilientHTTPClient(
            "test-http",
            base_url="http://test.local",
            service_type="http_external"
        )

    def test_client_has_circuit(self, http_client):
        """Cliente tem circuit breaker."""
        assert http_client.circuit is not None
        assert http_client.name == "test-http"

    def test_stats_available(self, http_client):
        """Estatisticas estao disponiveis."""
        stats = http_client.stats
        assert "name" in stats
        assert stats["name"] == "test-http"


# === Testes de Integracao Global ===

class TestGlobalRegistry:
    """Testes do registro global de circuit breakers."""

    def test_get_circuit_breaker_creates_new(self):
        """get_circuit_breaker cria novo se nao existir."""
        cb = get_circuit_breaker("new-circuit")
        assert cb is not None
        assert cb.name == "new-circuit"

    def test_get_circuit_breaker_returns_existing(self):
        """get_circuit_breaker retorna existente."""
        cb1 = get_circuit_breaker("existing-circuit")
        cb2 = get_circuit_breaker("existing-circuit")
        assert cb1 is cb2

    def test_get_all_stats_includes_circuits(self):
        """get_all_circuit_breaker_stats inclui todos os circuits."""
        get_circuit_breaker("stats-test-1")
        get_circuit_breaker("stats-test-2")

        stats = get_all_circuit_breaker_stats()
        assert "stats-test-1" in stats
        assert "stats-test-2" in stats


# === Teste de Cenario Real ===

class TestRealWorldScenario:
    """Testes de cenarios do mundo real."""

    @pytest.mark.asyncio
    async def test_cascading_failure_protection(self):
        """Circuit breaker protege contra falhas em cascata."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            success_threshold=1,
            timeout=1.0,
            reset_timeout=0.5,
            half_open_max_calls=1
        )
        circuit = CircuitBreaker("cascade-test", config)

        call_count = 0
        fail_count = 0

        async def unreliable_service():
            nonlocal call_count, fail_count
            call_count += 1
            if call_count <= 3:
                fail_count += 1
                raise Exception("Servico indisponivel")
            return "recovered"

        # Primeiras chamadas falham
        for _ in range(2):
            with pytest.raises(Exception):
                await circuit.execute(unreliable_service)

        # Circuito abre
        assert circuit.state == CircuitState.OPEN

        # Proximas chamadas sao rejeitadas sem chamar o servico
        with pytest.raises(CircuitBreakerError):
            await circuit.execute(unreliable_service)

        # call_count nao aumentou porque o servico nao foi chamado
        assert call_count == 2

        # Aguardar reset_timeout
        await asyncio.sleep(0.6)

        # Circuito deve ir para HALF_OPEN e tentar
        result = await circuit.execute(unreliable_service)
        assert result == "recovered"
        assert circuit.state == CircuitState.CLOSED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
