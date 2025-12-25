"""
Conecta Plus - Fixtures para Testes
"""

import pytest
import pytest_asyncio
import asyncio
from httpx import AsyncClient, ASGITransport
import sys
import os

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app


@pytest.fixture(scope="session")
def event_loop():
    """Cria event loop para testes async"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def client():
    """Cliente HTTP async para testes"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_client(client):
    """Cliente autenticado para testes"""
    # Faz login para obter token
    response = await client.post(
        "/api/auth/login",
        json={"email": "admin@conectaplus.com.br", "senha": "admin123"}
    )
    if response.status_code == 200:
        token = response.json().get("access_token", "mock_token")
        client.headers["Authorization"] = f"Bearer {token}"
    else:
        # Fallback para mock token se login falhar
        client.headers["Authorization"] = "Bearer mock_token_for_tests"
    yield client


@pytest.fixture
def sample_boleto():
    """Dados de boleto para teste"""
    return {
        "unidade_id": "1",
        "valor": 850.00,
        "vencimento": "2025-01-15",
        "descricao": "Taxa de Condominio - Janeiro/2025",
        "tipo": "condominio"
    }


@pytest.fixture
def sample_lancamento():
    """Dados de lançamento para teste"""
    return {
        "tipo": "despesa",
        "categoria": "manutencao",
        "descricao": "Manutencao do elevador",
        "valor": 1500.00,
        "data": "2025-01-10"
    }


@pytest.fixture
def sample_pagamento():
    """Dados de pagamento para teste"""
    return {
        "boleto_id": "bol_001",
        "valor_pago": 850.00,
        "data_pagamento": "2025-01-08",
        "forma_pagamento": "pix"
    }
