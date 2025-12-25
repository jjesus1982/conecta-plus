"""
Conecta Plus - Modelos de Dados: Integração Banco Cora
Schemas SQLAlchemy para integração completa com Cora Bank API V2
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from enum import Enum as PyEnum
from sqlalchemy import (
    Column, String, Boolean, DateTime, Date, Text, ForeignKey,
    Enum, Index, UniqueConstraint, Numeric, Integer, CheckConstraint,
    event, text
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy import JSON
from sqlalchemy import LargeBinary
import uuid

# Usa o mesmo Base que os outros modelos
from models.financeiro import Base, TimestampMixin


# ==================== ENUMS ====================

class TipoTransacaoCora(str, PyEnum):
    """Tipo de transação bancária"""
    CREDITO = "C"
    DEBITO = "D"


class TipoCobrancaCora(str, PyEnum):
    """Tipo de cobrança Cora"""
    BOLETO = "boleto"
    PIX = "pix"
    HIBRIDO = "hibrido"  # Boleto + PIX


class StatusCobrancaCora(str, PyEnum):
    """Status da cobrança"""
    PENDENTE = "pendente"
    PAGO = "pago"
    VENCIDO = "vencido"
    CANCELADO = "cancelado"
    EXPIRADO = "expirado"


class TipoSyncCora(str, PyEnum):
    """Tipo de sincronização"""
    EXTRATO = "extrato"
    COBRANCAS = "cobrancas"
    SALDO = "saldo"


class StatusSyncCora(str, PyEnum):
    """Status da sincronização"""
    INICIADO = "iniciado"
    CONCLUIDO = "concluido"
    ERRO = "erro"


class AmbienteCora(str, PyEnum):
    """Ambiente Cora"""
    PRODUCTION = "production"
    SANDBOX = "sandbox"


class VersaoAPICora(str, PyEnum):
    """Versão da API Cora"""
    V1 = "v1"
    V2 = "v2"


# ==================== MODELOS ====================

class ContaCora(Base, TimestampMixin):
    """
    Conta Bancária Cora vinculada a um condomínio

    Armazena as credenciais e configurações da integração
    """
    __tablename__ = "contas_cora"
    __table_args__ = (
        Index('idx_contas_cora_condominio', 'condominio_id'),
        Index('idx_contas_cora_account_id', 'cora_account_id'),
        Index('idx_contas_cora_documento', 'cora_document'),
        {'schema': 'financeiro'},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Relacionamentos
    condominio_id = Column(UUID(as_uuid=True), nullable=False)
    conta_bancaria_id = Column(UUID(as_uuid=True))

    # Dados da Conta Cora
    cora_account_id = Column(String(100), nullable=False, unique=True)
    cora_document = Column(String(20), nullable=False)  # CPF/CNPJ sem formatação
    cora_agencia = Column(String(10))
    cora_conta = Column(String(20))
    cora_conta_digito = Column(String(2))

    # Configuração
    ambiente = Column(Enum(AmbienteCora), nullable=False, default=AmbienteCora.PRODUCTION)
    api_version = Column(Enum(VersaoAPICora), nullable=False, default=VersaoAPICora.V2)
    ativa = Column(Boolean, nullable=False, default=True)

    # Credenciais OAuth2 (criptografadas)
    client_id_encrypted = Column(LargeBinary)
    client_id_salt = Column(LargeBinary)
    client_secret_encrypted = Column(LargeBinary)
    client_secret_salt = Column(LargeBinary)

    # Webhook
    webhook_secret_encrypted = Column(LargeBinary)
    webhook_secret_salt = Column(LargeBinary)

    # Auditoria
    created_by = Column(UUID(as_uuid=True))
    updated_by = Column(UUID(as_uuid=True))

    # Relationships
    transacoes = relationship("TransacaoCora", back_populates="conta", cascade="all, delete-orphan")
    cobrancas = relationship("CobrancaCora", back_populates="conta", cascade="all, delete-orphan")
    tokens = relationship("CoraToken", back_populates="conta", cascade="all, delete-orphan")
    saldo = relationship("SaldoCora", back_populates="conta", uselist=False, cascade="all, delete-orphan")
    sync_logs = relationship("CoraSyncLog", back_populates="conta", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ContaCora(id={self.id}, account={self.cora_account_id}, ativa={self.ativa})>"


class TransacaoCora(Base, TimestampMixin):
    """
    Transação do extrato bancário Cora

    Armazena todas as movimentações (créditos e débitos) sincronizadas da API
    """
    __tablename__ = "transacoes_cora"
    __table_args__ = (
        Index('idx_transacoes_cora_conta', 'conta_cora_id'),
        Index('idx_transacoes_cora_condominio', 'condominio_id'),
        Index('idx_transacoes_cora_data', 'data_transacao'),
        Index('idx_transacoes_cora_tipo', 'tipo'),
        Index('idx_transacoes_cora_conciliado', 'conciliado'),
        Index('idx_transacoes_cora_end_to_end', 'end_to_end_id'),
        Index('idx_transacoes_cora_nosso_numero', 'nosso_numero'),
        Index('idx_transacoes_cora_categoria', 'categoria'),
        {'schema': 'financeiro'},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Relacionamentos
    conta_cora_id = Column(UUID(as_uuid=True), ForeignKey('financeiro.contas_cora.id', ondelete='CASCADE'), nullable=False)
    condominio_id = Column(UUID(as_uuid=True), nullable=False)

    # Dados da Transação Cora
    cora_transaction_id = Column(String(100), nullable=False, unique=True)
    data_transacao = Column(Date, nullable=False)
    tipo = Column(Enum(TipoTransacaoCora), nullable=False)
    valor = Column(Numeric(12, 2), nullable=False)

    # Descrição
    descricao = Column(Text, nullable=False)
    categoria = Column(String(50))  # INVOICE_PAYMENT, PIX_RECEIVED, TRANSFER, etc

    # Contrapartida
    contrapartida_nome = Column(String(255))
    contrapartida_documento = Column(String(20))

    # PIX
    end_to_end_id = Column(String(100))  # ID único PIX para conciliação
    pix_txid = Column(String(50))

    # Boleto
    nosso_numero = Column(String(20))
    codigo_barras = Column(String(60))

    # Conciliação
    conciliado = Column(Boolean, nullable=False, default=False)
    boleto_id = Column(UUID(as_uuid=True))
    pagamento_id = Column(UUID(as_uuid=True))
    lancamento_id = Column(UUID(as_uuid=True))
    confianca_match = Column(Numeric(5, 2))  # 0-100
    conciliado_em = Column(DateTime)
    conciliado_por = Column(UUID(as_uuid=True))
    conciliacao_manual = Column(Boolean, default=False)

    # Metadados
    raw_data = Column(JSON)  # Dados originais da API

    # Relationships
    conta = relationship("ContaCora", back_populates="transacoes")

    def __repr__(self):
        return f"<TransacaoCora(id={self.id}, data={self.data_transacao}, tipo={self.tipo}, valor={self.valor})>"


class CobrancaCora(Base, TimestampMixin):
    """
    Cobrança (Boleto ou PIX) criada no Banco Cora

    Armazena dados de boletos, PIX ou cobranças híbridas geradas via API
    """
    __tablename__ = "cobrancas_cora"
    __table_args__ = (
        Index('idx_cobrancas_cora_conta', 'conta_cora_id'),
        Index('idx_cobrancas_cora_condominio', 'condominio_id'),
        Index('idx_cobrancas_cora_boleto', 'boleto_id'),
        Index('idx_cobrancas_cora_invoice_id', 'cora_invoice_id'),
        Index('idx_cobrancas_cora_pix_txid', 'cora_pix_txid'),
        Index('idx_cobrancas_cora_status', 'status'),
        Index('idx_cobrancas_cora_vencimento', 'data_vencimento'),
        Index('idx_cobrancas_cora_carne', 'carne_id'),
        Index('idx_cobrancas_cora_nosso_numero', 'nosso_numero'),
        {'schema': 'financeiro'},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Relacionamentos
    conta_cora_id = Column(UUID(as_uuid=True), ForeignKey('financeiro.contas_cora.id', ondelete='CASCADE'), nullable=False)
    condominio_id = Column(UUID(as_uuid=True), nullable=False)
    boleto_id = Column(UUID(as_uuid=True))
    carne_id = Column(UUID(as_uuid=True))  # ID do carnê (se faz parte de um)

    # IDs Cora
    cora_invoice_id = Column(String(100), unique=True)
    cora_pix_txid = Column(String(50), unique=True)

    # Tipo e Status
    tipo = Column(Enum(TipoCobrancaCora), nullable=False)
    status = Column(Enum(StatusCobrancaCora), nullable=False, default=StatusCobrancaCora.PENDENTE)

    # Valores
    valor = Column(Numeric(12, 2), nullable=False)
    valor_pago = Column(Numeric(12, 2))

    # Datas
    data_vencimento = Column(Date)
    data_criacao = Column(DateTime, nullable=False, default=datetime.utcnow)
    data_pagamento = Column(DateTime)
    data_cancelamento = Column(DateTime)

    # Dados do Pagador (CRIPTOGRAFADOS)
    pagador_nome = Column(String(255))
    pagador_documento_encrypted = Column(LargeBinary)
    pagador_documento_salt = Column(LargeBinary)
    pagador_email_encrypted = Column(LargeBinary)
    pagador_email_salt = Column(LargeBinary)

    # PIX
    pix_qrcode = Column(Text)  # Base64 ou URL
    pix_copia_cola = Column(Text)  # EMV
    pix_expiracao = Column(DateTime)

    # Boleto
    codigo_barras = Column(String(60))
    linha_digitavel = Column(String(60))
    nosso_numero = Column(String(20))
    url_pdf = Column(Text)

    # Carnê
    numero_parcela = Column(Integer)
    total_parcelas = Column(Integer)

    # Metadados
    descricao = Column(Text)
    raw_data = Column(JSON)

    # Auditoria
    created_by = Column(UUID(as_uuid=True))
    updated_by = Column(UUID(as_uuid=True))

    # Relationships
    conta = relationship("ContaCora", back_populates="cobrancas")

    def __repr__(self):
        return f"<CobrancaCora(id={self.id}, tipo={self.tipo}, valor={self.valor}, status={self.status})>"


class WebhookCora(Base):
    """
    Log IMUTÁVEL de webhooks recebidos do Banco Cora

    Armazena todos os eventos recebidos para auditoria e reprocessamento
    IMPORTANTE: Não permite UPDATE (exceto marcar como processado)
    """
    __tablename__ = "webhooks_cora"
    __table_args__ = (
        Index('idx_webhooks_cora_event_type', 'event_type'),
        Index('idx_webhooks_cora_processado', 'processado'),
        Index('idx_webhooks_cora_received_at', 'received_at'),
        Index('idx_webhooks_cora_event_id', 'event_id'),
        {'schema': 'financeiro'},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Dados do Webhook
    event_type = Column(String(100), nullable=False)
    event_id = Column(String(100), nullable=False, unique=True)

    # Payload
    body = Column(JSON, nullable=False)

    # Assinatura
    signature = Column(String(255), nullable=False)
    signature_valid = Column(Boolean, nullable=False)

    # Processamento
    processado = Column(Boolean, nullable=False, default=False)
    processado_em = Column(DateTime)
    resultado = Column(JSON)
    erro_mensagem = Column(Text)
    tentativas_processamento = Column(Integer, default=0)

    # Metadados
    ip_origem = Column(String(45))
    user_agent = Column(Text)

    # Auditoria (SEM updated_at - imutável)
    received_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"<WebhookCora(id={self.id}, type={self.event_type}, processado={self.processado})>"


class CoraToken(Base, TimestampMixin):
    """
    Token OAuth2 do Banco Cora (criptografado)

    Armazena access tokens e refresh tokens com criptografia AES-256
    """
    __tablename__ = "cora_tokens"
    __table_args__ = (
        Index('idx_cora_tokens_conta', 'conta_cora_id'),
        Index('idx_cora_tokens_ativo', 'conta_cora_id', 'ativo', postgresql_where=text("ativo = true")),
        Index('idx_cora_tokens_expires', 'expires_at'),
        {'schema': 'financeiro'},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Relacionamento
    conta_cora_id = Column(UUID(as_uuid=True), ForeignKey('financeiro.contas_cora.id', ondelete='CASCADE'), nullable=False)

    # Tokens Criptografados (AES-256)
    access_token_encrypted = Column(LargeBinary, nullable=False)
    access_token_salt = Column(LargeBinary, nullable=False)
    refresh_token_encrypted = Column(LargeBinary)
    refresh_token_salt = Column(LargeBinary)

    # Expiração
    expires_at = Column(DateTime, nullable=False)
    token_type = Column(String(20), default='Bearer')

    # Status
    ativo = Column(Boolean, nullable=False, default=True)
    revogado = Column(Boolean, default=False)
    revogado_em = Column(DateTime)
    revogado_motivo = Column(Text)

    # Relationships
    conta = relationship("ContaCora", back_populates="tokens")

    def __repr__(self):
        return f"<CoraToken(id={self.id}, conta={self.conta_cora_id}, ativo={self.ativo})>"


class SaldoCora(Base, TimestampMixin):
    """
    Cache de saldo do Banco Cora

    Armazena saldo consultado da API com TTL (Time To Live) de 10 minutos
    """
    __tablename__ = "saldos_cora"
    __table_args__ = (
        Index('idx_saldos_cora_conta', 'conta_cora_id'),
        Index('idx_saldos_cora_validade', 'valido_ate'),
        {'schema': 'financeiro'},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Relacionamento
    conta_cora_id = Column(UUID(as_uuid=True), ForeignKey('financeiro.contas_cora.id', ondelete='CASCADE'), nullable=False, unique=True)

    # Saldos
    saldo_disponivel = Column(Numeric(12, 2), nullable=False)
    saldo_bloqueado = Column(Numeric(12, 2), nullable=False, default=0)
    saldo_total = Column(Numeric(12, 2), nullable=False)

    # Referência
    data_referencia = Column(DateTime, nullable=False)

    # Cache
    valido_ate = Column(DateTime, nullable=False)

    # Relationships
    conta = relationship("ContaCora", back_populates="saldo")

    @property
    def is_valido(self) -> bool:
        """Verifica se o cache ainda é válido"""
        return datetime.utcnow() < self.valido_ate

    def __repr__(self):
        return f"<SaldoCora(conta={self.conta_cora_id}, disponivel={self.saldo_disponivel}, valido={self.is_valido})>"


class CoraSyncLog(Base):
    """
    Log de sincronização de dados com Banco Cora

    Armazena histórico de sincronizações de extrato, saldo e cobranças
    """
    __tablename__ = "cora_sync_logs"
    __table_args__ = (
        Index('idx_cora_sync_logs_conta', 'conta_cora_id'),
        Index('idx_cora_sync_logs_condominio', 'condominio_id'),
        Index('idx_cora_sync_logs_tipo', 'tipo'),
        Index('idx_cora_sync_logs_status', 'status'),
        Index('idx_cora_sync_logs_iniciado_em', 'iniciado_em'),
        {'schema': 'financeiro'},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Relacionamentos
    conta_cora_id = Column(UUID(as_uuid=True), ForeignKey('financeiro.contas_cora.id', ondelete='CASCADE'), nullable=False)
    condominio_id = Column(UUID(as_uuid=True), nullable=False)

    # Tipo e Status
    tipo = Column(Enum(TipoSyncCora), nullable=False)
    status = Column(Enum(StatusSyncCora), nullable=False)

    # Período (para extrato)
    data_inicio = Column(Date)
    data_fim = Column(Date)

    # Resultados
    registros_processados = Column(Integer, default=0)
    registros_novos = Column(Integer, default=0)
    registros_atualizados = Column(Integer, default=0)
    registros_erro = Column(Integer, default=0)

    # Performance
    duracao_segundos = Column(Numeric(8, 2))

    # Erro
    erro_mensagem = Column(Text)
    erro_stack_trace = Column(Text)

    # Metadados
    parametros = Column(JSON)
    resultado = Column(JSON)

    # Auditoria
    iniciado_em = Column(DateTime, nullable=False, default=datetime.utcnow)
    finalizado_em = Column(DateTime)
    iniciado_por = Column(UUID(as_uuid=True))

    # Relationships
    conta = relationship("ContaCora", back_populates="sync_logs")

    @property
    def duracao_formatada(self) -> str:
        """Retorna duração formatada"""
        if self.duracao_segundos:
            return f"{self.duracao_segundos:.2f}s"
        return "N/A"

    def __repr__(self):
        return f"<CoraSyncLog(id={self.id}, tipo={self.tipo}, status={self.status})>"


# ==================== EVENTOS SQLALCHEMY ====================

@event.listens_for(SaldoCora, 'before_insert')
@event.listens_for(SaldoCora, 'before_update')
def validate_saldo_total(mapper, connection, target):
    """Valida que saldo_total = saldo_disponivel + saldo_bloqueado"""
    expected_total = target.saldo_disponivel + target.saldo_bloqueado
    if target.saldo_total != expected_total:
        raise ValueError(
            f"saldo_total ({target.saldo_total}) deve ser igual a "
            f"saldo_disponivel ({target.saldo_disponivel}) + "
            f"saldo_bloqueado ({target.saldo_bloqueado})"
        )
