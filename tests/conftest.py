"""
Configuração global de testes pytest - Conecta Plus
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from uuid import uuid4
import sys
import os

# Adicionar diretórios ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'services'))


# ==========================================
# Fixtures Globais
# ==========================================

@pytest.fixture(scope="session")
def test_condominio_id():
    """ID de condomínio para testes"""
    return "a1b2c3d4-e5f6-7890-abcd-ef1234567890"


@pytest.fixture(scope="session")
def test_usuario_id():
    """ID de usuário para testes"""
    return "b2c3d4e5-f6a7-8901-bcde-f12345678901"


@pytest.fixture
def mock_db_session():
    """Mock de sessão de banco de dados"""
    session = Mock()
    session.execute = Mock()
    session.commit = Mock()
    session.rollback = Mock()
    session.close = Mock()
    session.query = Mock()
    session.add = Mock()
    session.delete = Mock()
    return session


@pytest.fixture
def mock_redis_client():
    """Mock de cliente Redis"""
    client = AsyncMock()
    client.get = AsyncMock(return_value=None)
    client.set = AsyncMock(return_value=True)
    client.delete = AsyncMock(return_value=1)
    client.exists = AsyncMock(return_value=False)
    client.ping = AsyncMock(return_value=True)
    return client


@pytest.fixture
def auth_token():
    """Token JWT de teste"""
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LXVzZXIiLCJleHAiOjE3MDAwMDAwMDB9.test"


@pytest.fixture
def auth_headers(auth_token):
    """Headers de autenticação"""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }


# ==========================================
# Fixtures de Modelos
# ==========================================

@pytest.fixture
def sample_condominio(test_condominio_id):
    """Modelo de condomínio de teste"""
    return {
        "id": test_condominio_id,
        "nome": "Condomínio Teste",
        "endereco": "Rua das Flores, 123",
        "cidade": "São Paulo",
        "estado": "SP",
        "cep": "01234-567",
        "cnpj": "12.345.678/0001-90",
        "total_unidades": 100,
        "ativo": True,
        "created_at": datetime.utcnow().isoformat()
    }


@pytest.fixture
def sample_usuario(test_usuario_id):
    """Modelo de usuário de teste"""
    return {
        "id": test_usuario_id,
        "email": "admin@conectaplus.com.br",
        "nome": "Admin Teste",
        "role": "admin",
        "ativo": True,
        "created_at": datetime.utcnow().isoformat()
    }


@pytest.fixture
def sample_unidade(test_condominio_id):
    """Modelo de unidade de teste"""
    return {
        "id": str(uuid4()),
        "condominio_id": test_condominio_id,
        "bloco": "A",
        "numero": "101",
        "tipo": "apartamento",
        "area_m2": 75.5,
        "ocupada": True,
        "ativo": True
    }


@pytest.fixture
def sample_morador(test_condominio_id):
    """Modelo de morador de teste"""
    return {
        "id": str(uuid4()),
        "condominio_id": test_condominio_id,
        "unidade_id": str(uuid4()),
        "nome": "João Silva",
        "cpf": "123.456.789-00",
        "email": "joao@email.com",
        "telefone": "(11) 98765-4321",
        "tipo": "proprietario",
        "ativo": True
    }


@pytest.fixture
def sample_boleto(test_condominio_id):
    """Modelo de boleto de teste"""
    return {
        "id": str(uuid4()),
        "condominio_id": test_condominio_id,
        "unidade_id": str(uuid4()),
        "tipo": "taxa_condominial",
        "descricao": "Taxa condominial - Janeiro/2025",
        "valor": 850.00,
        "vencimento": "2025-01-10",
        "status": "pendente",
        "codigo_barras": "23793.38128 60000.000003 00000.000405 1 92340000085000"
    }


@pytest.fixture
def sample_ocorrencia(test_condominio_id):
    """Modelo de ocorrência de teste"""
    return {
        "id": str(uuid4()),
        "condominio_id": test_condominio_id,
        "tipo": "barulho",
        "titulo": "Barulho excessivo",
        "descricao": "Música alta após 22h",
        "prioridade": "media",
        "status": "aberta"
    }


@pytest.fixture
def sample_reserva(test_condominio_id):
    """Modelo de reserva de teste"""
    return {
        "id": str(uuid4()),
        "condominio_id": test_condominio_id,
        "area_comum_id": str(uuid4()),
        "unidade_id": str(uuid4()),
        "data_reserva": "2025-02-15",
        "hora_inicio": "14:00",
        "hora_fim": "22:00",
        "status": "pendente"
    }


@pytest.fixture
def sample_previsao(test_condominio_id):
    """Modelo de previsão de teste"""
    return {
        "id": str(uuid4()),
        "condominio_id": test_condominio_id,
        "tipo": "inadimplencia",
        "subtipo": "atraso_pagamento",
        "probabilidade": 0.85,
        "confianca": 0.92,
        "horizonte_dias": 30,
        "status": "pendente"
    }


@pytest.fixture
def sample_sugestao(test_condominio_id):
    """Modelo de sugestão de teste"""
    return {
        "id": str(uuid4()),
        "condominio_id": test_condominio_id,
        "tipo": "economia",
        "codigo": "ECO-001",
        "titulo": "Reduzir consumo de energia",
        "descricao": "Instalar sensores de presença",
        "prioridade": 2,
        "status": "pendente"
    }


# ==========================================
# Fixtures de API
# ==========================================

@pytest.fixture
def mock_http_client():
    """Mock de cliente HTTP"""
    client = AsyncMock()
    client.get = AsyncMock()
    client.post = AsyncMock()
    client.put = AsyncMock()
    client.patch = AsyncMock()
    client.delete = AsyncMock()
    return client


# ==========================================
# Markers
# ==========================================

def pytest_configure(config):
    """Configurar markers customizados"""
    config.addinivalue_line("markers", "slow: marca testes lentos")
    config.addinivalue_line("markers", "integration: marca testes de integração")
    config.addinivalue_line("markers", "e2e: marca testes end-to-end")
    config.addinivalue_line("markers", "unit: marca testes unitários")


# ==========================================
# Hooks
# ==========================================

def pytest_collection_modifyitems(config, items):
    """Modificar coleta de testes"""
    for item in items:
        # Adicionar marker de slow para testes de integração
        if "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        if "e2e" in item.nodeid:
            item.add_marker(pytest.mark.e2e)
            item.add_marker(pytest.mark.slow)
