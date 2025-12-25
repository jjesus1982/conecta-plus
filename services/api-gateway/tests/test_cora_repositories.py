"""
Conecta Plus - Testes: Repositórios Cora
Testes unitários para os repositórios de integração Banco Cora
"""

import pytest
from datetime import datetime, timedelta, date
from decimal import Decimal
from uuid import uuid4
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# Configuração do banco de teste (in-memory SQLite)
TEST_DATABASE_URL = "sqlite:///:memory:"

# Import apenas os modelos Cora (não o Base completo que inclui financeiro)
from models.cora import (
    ContaCora,
    TransacaoCora,
    CobrancaCora,
    WebhookCora,
    CoraToken,
    SaldoCora,
    CoraSyncLog,
    TipoTransacaoCora,
    TipoCobrancaCora,
    StatusCobrancaCora,
    TipoSyncCora,
    StatusSyncCora,
    AmbienteCora,
    VersaoAPICora,
)
from repositories.cora import (
    ContaCoraRepository,
    TransacaoCoraRepository,
    CobrancaCoraRepository,
    WebhookCoraRepository,
    CoraTokenRepository,
    SaldoCoraRepository,
    CoraSyncLogRepository,
)


@pytest.fixture(scope="function")
def db_session():
    """
    Fixture que cria uma sessão de banco de dados para testes

    Returns:
        Session do SQLAlchemy
    """
    engine = create_engine(TEST_DATABASE_URL)

    # Remove o schema para compatibilidade com SQLite
    models_to_create = [ContaCora, TransacaoCora, CobrancaCora, WebhookCora, CoraToken, SaldoCora, CoraSyncLog]

    for model in models_to_create:
        model.__table__.schema = None
        model.__table__.create(engine, checkfirst=True)

    Session = sessionmaker(bind=engine)
    session = Session()

    yield session

    session.close()

    # Drop tabelas na ordem inversa (devido a foreign keys)
    models_to_drop = [CoraSyncLog, SaldoCora, CoraToken, WebhookCora, CobrancaCora, TransacaoCora, ContaCora]

    for model in models_to_drop:
        model.__table__.drop(engine, checkfirst=True)


@pytest.fixture
def conta_cora(db_session):
    """Fixture que cria uma conta Cora de teste"""
    repo = ContaCoraRepository(db_session)

    conta = repo.create(
        condominio_id=uuid4(),
        cora_account_id="acc_test_001",
        cora_document="12345678000199",
        client_id="test_client_id",
        client_secret="test_client_secret",
        webhook_secret="test_webhook_secret",
        ambiente="sandbox",
        api_version="v2"
    )

    db_session.commit()
    return conta


# ==================== TESTES CONTA CORA ====================

def test_create_conta_cora(db_session):
    """Testa criação de conta Cora"""
    repo = ContaCoraRepository(db_session)

    condominio_id = uuid4()
    conta = repo.create(
        condominio_id=condominio_id,
        cora_account_id="acc_test_123",
        cora_document="98765432000188",
        client_id="my_client_id",
        client_secret="my_client_secret",
        webhook_secret="my_webhook_secret",
        ambiente="production",
        api_version="v2"
    )

    assert conta.id is not None
    assert conta.cora_account_id == "acc_test_123"
    assert conta.ambiente.value == "production"
    assert conta.ativa is True
    assert conta.client_id_encrypted is not None  # Deve estar criptografado


def test_get_conta_by_condominio(db_session, conta_cora):
    """Testa busca de conta por condomínio"""
    repo = ContaCoraRepository(db_session)

    conta_encontrada = repo.get_by_condominio(conta_cora.condominio_id)

    assert conta_encontrada is not None
    assert conta_encontrada.id == conta_cora.id


def test_get_credentials(db_session, conta_cora):
    """Testa obtenção de credenciais descriptografadas"""
    repo = ContaCoraRepository(db_session)

    credentials = repo.get_credentials(conta_cora.id)

    assert credentials is not None
    assert credentials["client_id"] == "test_client_id"
    assert credentials["client_secret"] == "test_client_secret"
    assert credentials["webhook_secret"] == "test_webhook_secret"


# ==================== TESTES TRANSACAO CORA ====================

def test_create_transacao(db_session, conta_cora):
    """Testa criação de transação"""
    repo = TransacaoCoraRepository(db_session)

    transacao = repo.create(
        conta_cora_id=conta_cora.id,
        condominio_id=conta_cora.condominio_id,
        cora_transaction_id="trans_123",
        data_transacao=date(2025, 1, 15),
        tipo="C",
        valor=Decimal("850.00"),
        descricao="Pagamento PIX - Apt 101"
    )

    assert transacao.id is not None
    assert transacao.tipo.value == "C"
    assert transacao.valor == Decimal("850.00")
    assert transacao.conciliado is False


def test_list_transacoes_nao_conciliadas(db_session, conta_cora):
    """Testa listagem de transações não conciliadas"""
    repo = TransacaoCoraRepository(db_session)

    # Cria 3 transações não conciliadas
    for i in range(3):
        repo.create(
            conta_cora_id=conta_cora.id,
            condominio_id=conta_cora.condominio_id,
            cora_transaction_id=f"trans_{i}",
            data_transacao=date(2025, 1, 15),
            tipo="C",
            valor=Decimal("100.00"),
            descricao=f"Transação {i}"
        )

    db_session.commit()

    nao_conciliadas = repo.get_nao_conciliadas(conta_cora_id=conta_cora.id)

    assert len(nao_conciliadas) == 3


def test_conciliar_transacao(db_session, conta_cora):
    """Testa conciliação de transação"""
    repo = TransacaoCoraRepository(db_session)

    transacao = repo.create(
        conta_cora_id=conta_cora.id,
        condominio_id=conta_cora.condominio_id,
        cora_transaction_id="trans_to_conciliate",
        data_transacao=date(2025, 1, 15),
        tipo="C",
        valor=Decimal("850.00"),
        descricao="A conciliar"
    )

    db_session.commit()

    # Concilia
    boleto_id = uuid4()
    transacao_conciliada = repo.conciliar(
        transacao_id=transacao.id,
        boleto_id=boleto_id,
        confianca_match=Decimal("95.00"),
        manual=False
    )

    assert transacao_conciliada.conciliado is True
    assert transacao_conciliada.boleto_id == boleto_id
    assert transacao_conciliada.confianca_match == Decimal("95.00")
    assert transacao_conciliada.conciliado_em is not None


# ==================== TESTES COBRANCA CORA ====================

def test_create_cobranca(db_session, conta_cora):
    """Testa criação de cobrança"""
    repo = CobrancaCoraRepository(db_session)

    cobranca = repo.create(
        conta_cora_id=conta_cora.id,
        condominio_id=conta_cora.condominio_id,
        tipo="hibrido",
        valor=Decimal("850.00"),
        pagador_nome="João Silva",
        pagador_documento="12345678900",
        pagador_email="joao@example.com"
    )

    db_session.commit()

    assert cobranca.id is not None
    assert cobranca.tipo.value == "hibrido"
    assert cobranca.valor == Decimal("850.00")
    assert cobranca.pagador_documento_encrypted is not None  # Criptografado


def test_get_cobranca_descriptografada(db_session, conta_cora):
    """Testa descriptografia de dados da cobrança"""
    repo = CobrancaCoraRepository(db_session)

    cobranca = repo.create(
        conta_cora_id=conta_cora.id,
        condominio_id=conta_cora.condominio_id,
        tipo="boleto",
        valor=Decimal("500.00"),
        pagador_documento="98765432100"
    )

    db_session.commit()

    # Busca novamente (deve descriptografar)
    cobranca_found = repo.get_by_id(cobranca.id)

    assert cobranca_found is not None
    assert cobranca_found.pagador_documento == "98765432100"  # Descriptografado


def test_update_status_cobranca(db_session, conta_cora):
    """Testa atualização de status da cobrança"""
    repo = CobrancaCoraRepository(db_session)

    cobranca = repo.create(
        conta_cora_id=conta_cora.id,
        condominio_id=conta_cora.condominio_id,
        tipo="pix",
        valor=Decimal("300.00")
    )

    db_session.commit()

    # Atualiza para pago
    cobranca_updated = repo.update_status(
        cobranca_id=cobranca.id,
        status="pago",
        valor_pago=Decimal("300.00"),
        data_pagamento=datetime.now()
    )

    assert cobranca_updated.status.value == "pago"
    assert cobranca_updated.valor_pago == Decimal("300.00")


# ==================== TESTES WEBHOOK CORA ====================

def test_create_webhook(db_session):
    """Testa criação de webhook"""
    repo = WebhookCoraRepository(db_session)

    webhook = repo.create(
        event_type="invoice.paid",
        event_id="evt_123",
        body={"id": "inv_123", "amount": 85000},
        signature="fake_signature",
        signature_valid=True,
        ip_origem="192.168.1.1"
    )

    db_session.commit()

    assert webhook.id is not None
    assert webhook.event_type == "invoice.paid"
    assert webhook.processado is False


def test_marcar_webhook_processado(db_session):
    """Testa marcação de webhook como processado"""
    repo = WebhookCoraRepository(db_session)

    webhook = repo.create(
        event_type="pix.received",
        event_id="evt_456",
        body={"txid": "pix_123"},
        signature="sig",
        signature_valid=True
    )

    db_session.commit()

    # Marca como processado
    webhook_processado = repo.marcar_processado(
        webhook_id=webhook.id,
        resultado={"status": "success"},
        erro_mensagem=None
    )

    assert webhook_processado.processado is True
    assert webhook_processado.processado_em is not None
    assert webhook_processado.tentativas_processamento == 1


def test_get_webhooks_nao_processados(db_session):
    """Testa listagem de webhooks não processados"""
    repo = WebhookCoraRepository(db_session)

    # Cria 3 webhooks não processados
    for i in range(3):
        repo.create(
            event_type="test.event",
            event_id=f"evt_{i}",
            body={},
            signature="sig",
            signature_valid=True
        )

    db_session.commit()

    pendentes = repo.get_nao_processados()

    assert len(pendentes) == 3


# ==================== TESTES CORA TOKEN ====================

def test_create_token(db_session, conta_cora):
    """Testa criação de token"""
    repo = CoraTokenRepository(db_session)

    expires_at = datetime.utcnow() + timedelta(hours=1)
    token = repo.create(
        conta_cora_id=conta_cora.id,
        access_token="fake_access_token_123",
        expires_at=expires_at,
        refresh_token="fake_refresh_token"
    )

    db_session.commit()

    assert token.id is not None
    assert token.ativo is True
    assert token.access_token_encrypted is not None


def test_get_token_ativo(db_session, conta_cora):
    """Testa obtenção de token ativo"""
    repo = CoraTokenRepository(db_session)

    # Cria token
    expires_at = datetime.utcnow() + timedelta(hours=1)
    repo.create(
        conta_cora_id=conta_cora.id,
        access_token="my_access_token",
        expires_at=expires_at
    )

    db_session.commit()

    # Busca token
    token_data = repo.get_ativo(conta_cora.id)

    assert token_data is not None
    assert token_data["access_token"] == "my_access_token"
    assert token_data["expires_at"] == expires_at


def test_revogar_tokens(db_session, conta_cora):
    """Testa revogação de tokens"""
    repo = CoraTokenRepository(db_session)

    # Cria 2 tokens
    for i in range(2):
        repo.create(
            conta_cora_id=conta_cora.id,
            access_token=f"token_{i}",
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )

    db_session.commit()

    # Revoga todos
    count = repo.revogar(conta_cora.id, motivo="Teste de revogação")

    db_session.commit()

    # Verifica que não há token ativo
    token_ativo = repo.get_ativo(conta_cora.id)
    assert token_ativo is None


# ==================== TESTES SALDO CORA ====================

def test_create_saldo(db_session, conta_cora):
    """Testa criação de saldo (cache)"""
    repo = SaldoCoraRepository(db_session)

    saldo = repo.create(
        conta_cora_id=conta_cora.id,
        saldo_disponivel=Decimal("10000.50"),
        saldo_bloqueado=Decimal("500.00"),
        data_referencia=datetime.utcnow(),
        ttl_minutos=10
    )

    db_session.commit()

    assert saldo.id is not None
    assert saldo.saldo_total == Decimal("10500.50")
    assert saldo.is_valido is True


def test_saldo_expirado(db_session, conta_cora):
    """Testa verificação de saldo expirado"""
    repo = SaldoCoraRepository(db_session)

    # Cria saldo com TTL negativo (já expirado)
    saldo = repo.create(
        conta_cora_id=conta_cora.id,
        saldo_disponivel=Decimal("5000.00"),
        saldo_bloqueado=Decimal("0.00"),
        data_referencia=datetime.utcnow(),
        ttl_minutos=-1  # Expirado
    )

    db_session.commit()

    # Busca saldo
    saldo_valido = repo.get_ultimo(conta_cora.id)

    assert saldo_valido is None  # Deve retornar None pois expirou


# ==================== TESTES SYNC LOG ====================

def test_criar_sync_log(db_session, conta_cora):
    """Testa criação de log de sincronização"""
    repo = CoraSyncLogRepository(db_session)

    log = repo.criar(
        conta_cora_id=conta_cora.id,
        condominio_id=conta_cora.condominio_id,
        tipo="extrato",
        data_inicio=date(2025, 1, 1),
        data_fim=date(2025, 1, 31)
    )

    db_session.commit()

    assert log.id is not None
    assert log.status.value == "iniciado"
    assert log.iniciado_em is not None


def test_finalizar_sync_log(db_session, conta_cora):
    """Testa finalização de log de sincronização"""
    repo = CoraSyncLogRepository(db_session)

    log = repo.criar(
        conta_cora_id=conta_cora.id,
        condominio_id=conta_cora.condominio_id,
        tipo="saldo"
    )

    db_session.commit()

    # Finaliza
    log_finalizado = repo.finalizar(
        sync_id=log.id,
        status="concluido",
        registros_processados=100,
        registros_novos=50,
        registros_atualizados=40,
        registros_erro=10
    )

    assert log_finalizado.status.value == "concluido"
    assert log_finalizado.finalizado_em is not None
    assert log_finalizado.registros_novos == 50
    assert log_finalizado.duracao_segundos is not None


def test_list_sync_logs_recentes(db_session, conta_cora):
    """Testa listagem de logs recentes"""
    repo = CoraSyncLogRepository(db_session)

    # Cria 5 logs
    for i in range(5):
        repo.criar(
            conta_cora_id=conta_cora.id,
            condominio_id=conta_cora.condominio_id,
            tipo="extrato"
        )

    db_session.commit()

    logs = repo.list_recentes(conta_cora_id=conta_cora.id, limit=3)

    assert len(logs) == 3


# ==================== MAIN ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
