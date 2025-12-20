"""
Conecta Plus - Testes de Autenticacao
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_login_sucesso(client):
    """Testa login com credenciais validas"""
    response = await client.post(
        "/api/auth/login",
        json={"email": "admin@conectaplus.com.br", "senha": "admin123"}
    )

    assert response.status_code == 200
    data = response.json()

    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "admin@conectaplus.com.br"
    assert data["user"]["role"] == "admin"


@pytest.mark.asyncio
async def test_login_email_invalido(client):
    """Testa login com email invalido"""
    response = await client.post(
        "/api/auth/login",
        json={"email": "invalido@email.com", "senha": "admin123"}
    )

    assert response.status_code == 401
    assert "incorretos" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_senha_invalida(client):
    """Testa login com senha invalida"""
    response = await client.post(
        "/api/auth/login",
        json={"email": "admin@conectaplus.com.br", "senha": "senhaerrada"}
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_acesso_sem_token(client):
    """Testa acesso a rota protegida sem token"""
    response = await client.get("/api/auth/me")

    assert response.status_code == 403  # Forbidden - sem token


@pytest.mark.asyncio
async def test_acesso_com_token_valido(auth_client):
    """Testa acesso a rota protegida com token valido"""
    response = await auth_client.get("/api/auth/me")

    assert response.status_code == 200
    data = response.json()

    assert "user" in data
    assert data["user"]["email"] == "admin@conectaplus.com.br"


@pytest.mark.asyncio
async def test_logout(auth_client):
    """Testa logout"""
    response = await auth_client.post("/api/auth/logout")

    assert response.status_code == 200
    assert "sucesso" in response.json()["message"].lower()


@pytest.mark.asyncio
async def test_login_diferentes_roles(client):
    """Testa login com diferentes roles"""
    roles = [
        ("admin@conectaplus.com.br", "admin123", "admin"),
        ("sindico@conectaplus.com.br", "sindico123", "sindico"),
        ("porteiro@conectaplus.com.br", "porteiro123", "porteiro"),
    ]

    for email, senha, role_esperado in roles:
        response = await client.post(
            "/api/auth/login",
            json={"email": email, "senha": senha}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["user"]["role"] == role_esperado
