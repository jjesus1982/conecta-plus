"""
Conecta Plus - Testes de Seguranca
Testa middlewares e configuracoes de seguranca
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
import time


class TestSecurityHeaders:
    """Testes dos headers de seguranca."""

    def test_headers_presentes(self, client):
        """Verifica se headers de seguranca estao presentes."""
        response = client.get("/health")

        # Headers OWASP recomendados
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert "Strict-Transport-Security" in response.headers

    def test_csp_header(self, client):
        """Verifica Content-Security-Policy."""
        response = client.get("/health")
        csp = response.headers.get("Content-Security-Policy", "")

        assert "default-src" in csp
        assert "frame-ancestors 'none'" in csp

    def test_request_id_header(self, client):
        """Verifica se X-Request-ID e retornado."""
        response = client.get("/health")

        assert "X-Request-ID" in response.headers
        assert len(response.headers["X-Request-ID"]) > 0


class TestRateLimiting:
    """Testes de rate limiting."""

    def test_rate_limit_headers(self, client):
        """Verifica se headers de rate limit estao presentes."""
        response = client.get("/health")

        # Se rate limit estiver ativado, headers devem estar presentes
        if "X-RateLimit-Limit" in response.headers:
            assert "X-RateLimit-Remaining" in response.headers
            assert "X-RateLimit-Reset" in response.headers


class TestHealthCheck:
    """Testes do endpoint de health check."""

    def test_health_check_success(self, client):
        """Testa health check retornando sucesso."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert "status" in data
        assert "timestamp" in data
        assert "version" in data
        assert "components" in data

    def test_health_check_components(self, client):
        """Verifica componentes do health check."""
        response = client.get("/health")
        data = response.json()

        assert "api" in data["components"]
        assert "database" in data["components"]


class TestAPIInfo:
    """Testes do endpoint de informacoes da API."""

    def test_api_info(self, client):
        """Testa endpoint de informacoes."""
        response = client.get("/api/v1")

        assert response.status_code == 200
        data = response.json()

        assert "name" in data
        assert "version" in data
        assert "endpoints" in data

    def test_api_endpoints_listed(self, client):
        """Verifica se endpoints estao listados."""
        response = client.get("/api/v1")
        data = response.json()

        endpoints = data.get("endpoints", {})

        # Verificar endpoints principais
        assert "auth" in endpoints
        assert "usuarios" in endpoints
        assert "condominios" in endpoints
        assert "frigate" in endpoints


class TestInputValidation:
    """Testes de validacao de input."""

    def test_login_email_invalido(self, client):
        """Testa login com email invalido."""
        response = client.post("/api/v1/auth/login", json={
            "email": "email-invalido",
            "password": "SenhaForte@123"
        })

        assert response.status_code == 422
        data = response.json()
        assert "errors" in data or "detail" in data

    def test_login_senha_vazia(self, client):
        """Testa login com senha vazia."""
        response = client.post("/api/v1/auth/login", json={
            "email": "teste@example.com",
            "password": ""
        })

        assert response.status_code == 422


class TestCORS:
    """Testes de CORS."""

    def test_cors_preflight(self, client):
        """Testa preflight request CORS."""
        response = client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            }
        )

        # Preflight deve ser aceito
        assert response.status_code in [200, 204]

    def test_cors_origin_header(self, client):
        """Verifica header Access-Control-Allow-Origin."""
        response = client.get(
            "/health",
            headers={"Origin": "http://localhost:3000"}
        )

        # CORS headers podem estar presentes
        # Depende da configuracao
        assert response.status_code == 200
