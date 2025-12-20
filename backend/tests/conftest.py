"""
Conecta Plus - Configuracao de Testes
Fixtures compartilhadas para pytest
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import os

# Configurar ambiente de teste
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key-minimum-32-characters-long"
os.environ["RATE_LIMIT_ENABLED"] = "false"

from ..database import Base, get_db
from ..main import app


# Engine de teste em memoria
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override da dependencia de banco para testes."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def db_session():
    """Fixture que cria banco de dados limpo para cada teste."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Fixture que cria cliente de teste."""
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def auth_headers(client):
    """Fixture que retorna headers com token de autenticacao."""
    # Criar usuario de teste
    from ..dependencies import get_password_hash

    # Registrar usuario via API ou inserir direto no banco
    # Por simplicidade, retornamos um token mockado
    return {"Authorization": "Bearer test-token"}


@pytest.fixture
def sample_user_data():
    """Dados de usuario para testes."""
    return {
        "nome": "Teste Usuario",
        "email": "teste@example.com",
        "password": "SenhaForte@123",
        "cpf": "12345678909",
        "telefone": "11999999999",
    }


@pytest.fixture
def sample_condominio_data():
    """Dados de condominio para testes."""
    return {
        "nome": "Condominio Teste",
        "cnpj": "12345678000199",
        "endereco": "Rua Teste, 123",
        "cidade": "Sao Paulo",
        "estado": "SP",
        "cep": "01234567",
    }
