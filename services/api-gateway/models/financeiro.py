"""
Conecta Plus - Modelos de Dados Financeiros
Schemas SQLAlchemy para persistência em PostgreSQL
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from enum import Enum as PyEnum
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Date,
    Text, ForeignKey, Enum, Index, UniqueConstraint, Numeric,
    event, JSON, LargeBinary
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

Base = declarative_base()


# ==================== ENUMS ====================

class StatusBoleto(str, PyEnum):
    PENDENTE = "pendente"
    PAGO = "pago"
    VENCIDO = "vencido"
    CANCELADO = "cancelado"
    PROTESTADO = "protestado"
    NEGOCIADO = "negociado"


class StatusPagamento(str, PyEnum):
    PENDENTE = "pendente"
    CONFIRMADO = "confirmado"
    CANCELADO = "cancelado"
    ESTORNADO = "estornado"


class TipoLancamento(str, PyEnum):
    RECEITA = "receita"
    DESPESA = "despesa"


class CanalCobranca(str, PyEnum):
    EMAIL = "email"
    SMS = "sms"
    WHATSAPP = "whatsapp"
    PUSH = "push"
    CARTA = "carta"


class StatusAcordo(str, PyEnum):
    PROPOSTA = "proposta"
    ATIVO = "ativo"
    QUITADO = "quitado"
    QUEBRADO = "quebrado"
    CANCELADO = "cancelado"


class TipoAuditoria(str, PyEnum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    ACCESS = "access"
    EXPORT = "export"
    COBRANCA = "cobranca"
    PAGAMENTO = "pagamento"


# ==================== MODELOS BASE ====================

class TimestampMixin:
    """Mixin para campos de timestamp"""
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class SoftDeleteMixin:
    """Mixin para soft delete"""
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(String(100), nullable=True)

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


# ==================== MODELOS FINANCEIROS ====================

class Boleto(Base, TimestampMixin, SoftDeleteMixin):
    """Modelo de Boleto Bancário"""
    __tablename__ = "boletos"
    __table_args__ = (
        UniqueConstraint('condominio_id', 'nosso_numero', name='uq_boleto_nosso_numero'),
        UniqueConstraint('condominio_id', 'unidade_id', 'competencia', name='uq_boleto_unidade_competencia'),
        Index('ix_boletos_vencimento', 'vencimento'),
        Index('ix_boletos_status', 'status'),
        Index('ix_boletos_condominio', 'condominio_id'),
        {'schema': 'financeiro'}
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    condominio_id = Column(String(50), nullable=False, index=True)
    unidade_id = Column(String(50), nullable=False, index=True)

    # Dados do boleto
    nosso_numero = Column(String(20), nullable=False)
    numero_documento = Column(String(20), nullable=True)
    competencia = Column(String(7), nullable=False)  # MM/YYYY
    descricao = Column(String(500), nullable=True)

    # Valores
    valor_original = Column(Numeric(12, 2), nullable=False)
    valor_desconto = Column(Numeric(12, 2), default=0)
    valor_juros = Column(Numeric(12, 2), default=0)
    valor_multa = Column(Numeric(12, 2), default=0)
    valor_total = Column(Numeric(12, 2), nullable=False)

    # Datas
    data_emissao = Column(Date, default=date.today, nullable=False)
    vencimento = Column(Date, nullable=False)
    data_limite_desconto = Column(Date, nullable=True)

    # Códigos
    codigo_barras = Column(String(44), nullable=True)
    linha_digitavel = Column(String(54), nullable=True)
    pix_copia_cola = Column(Text, nullable=True)
    pix_txid = Column(String(35), nullable=True)

    # Dados bancários (criptografados)
    banco_codigo = Column(String(3), nullable=False)
    agencia = Column(String(10), nullable=True)
    conta = Column(String(20), nullable=True)

    # Status
    status = Column(Enum(StatusBoleto), default=StatusBoleto.PENDENTE, nullable=False)

    # Pagador (dados criptografados)
    pagador_nome = Column(String(200), nullable=False)
    pagador_documento_hash = Column(String(64), nullable=False)  # Hash do CPF/CNPJ
    pagador_documento_encrypted = Column(LargeBinary, nullable=True)  # CPF/CNPJ criptografado
    pagador_endereco_encrypted = Column(LargeBinary, nullable=True)
    pagador_email_encrypted = Column(LargeBinary, nullable=True)
    pagador_telefone_encrypted = Column(LargeBinary, nullable=True)

    # Metadados
    metadata_json = Column(JSONB, default={})

    # Relacionamentos
    pagamentos = relationship("Pagamento", back_populates="boleto", lazy="dynamic")
    cobrancas = relationship("HistoricoCobranca", back_populates="boleto", lazy="dynamic")

    def __repr__(self):
        return f"<Boleto {self.nosso_numero} - {self.competencia}>"


class Pagamento(Base, TimestampMixin):
    """Modelo de Pagamento"""
    __tablename__ = "pagamentos"
    __table_args__ = (
        Index('ix_pagamentos_data', 'data_pagamento'),
        Index('ix_pagamentos_boleto', 'boleto_id'),
        {'schema': 'financeiro'}
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    boleto_id = Column(UUID(as_uuid=True), ForeignKey('financeiro.boletos.id'), nullable=False)
    condominio_id = Column(String(50), nullable=False, index=True)

    # Valores
    valor_pago = Column(Numeric(12, 2), nullable=False)
    valor_juros = Column(Numeric(12, 2), default=0)
    valor_multa = Column(Numeric(12, 2), default=0)
    valor_desconto = Column(Numeric(12, 2), default=0)

    # Datas
    data_pagamento = Column(Date, nullable=False)
    data_credito = Column(Date, nullable=True)

    # Forma de pagamento
    forma_pagamento = Column(String(50), nullable=False)  # boleto, pix, debito_automatico
    codigo_autenticacao = Column(String(100), nullable=True)

    # Status
    status = Column(Enum(StatusPagamento), default=StatusPagamento.CONFIRMADO)

    # Origem
    origem = Column(String(50), default="manual")  # manual, retorno_bancario, webhook, conciliacao
    arquivo_retorno = Column(String(200), nullable=True)

    # Relacionamentos
    boleto = relationship("Boleto", back_populates="pagamentos")

    def __repr__(self):
        return f"<Pagamento {self.id} - R$ {self.valor_pago}>"


class Lancamento(Base, TimestampMixin, SoftDeleteMixin):
    """Modelo de Lançamento Contábil"""
    __tablename__ = "lancamentos"
    __table_args__ = (
        Index('ix_lancamentos_data', 'data_lancamento'),
        Index('ix_lancamentos_tipo', 'tipo'),
        Index('ix_lancamentos_categoria', 'categoria_codigo'),
        {'schema': 'financeiro'}
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    condominio_id = Column(String(50), nullable=False, index=True)

    # Classificação
    tipo = Column(Enum(TipoLancamento), nullable=False)
    categoria_codigo = Column(String(10), nullable=False)
    categoria_nome = Column(String(100), nullable=False)

    # Valores
    valor = Column(Numeric(12, 2), nullable=False)

    # Datas
    data_lancamento = Column(Date, nullable=False)
    data_competencia = Column(Date, nullable=False)

    # Descrição
    descricao = Column(String(500), nullable=False)
    observacao = Column(Text, nullable=True)

    # Referências
    documento_numero = Column(String(50), nullable=True)
    fornecedor = Column(String(200), nullable=True)
    boleto_id = Column(UUID(as_uuid=True), ForeignKey('financeiro.boletos.id'), nullable=True)

    # Metadados
    metadata_json = Column(JSONB, default={})


class Acordo(Base, TimestampMixin):
    """Modelo de Acordo de Pagamento"""
    __tablename__ = "acordos"
    __table_args__ = (
        Index('ix_acordos_unidade', 'unidade_id'),
        Index('ix_acordos_status', 'status'),
        {'schema': 'financeiro'}
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    condominio_id = Column(String(50), nullable=False, index=True)
    unidade_id = Column(String(50), nullable=False)

    # Valores
    valor_original = Column(Numeric(12, 2), nullable=False)
    valor_desconto = Column(Numeric(12, 2), default=0)
    valor_juros = Column(Numeric(12, 2), default=0)
    valor_total = Column(Numeric(12, 2), nullable=False)

    # Parcelas
    numero_parcelas = Column(Integer, nullable=False)
    valor_entrada = Column(Numeric(12, 2), default=0)
    valor_parcela = Column(Numeric(12, 2), nullable=False)
    dia_vencimento = Column(Integer, nullable=False)

    # Status
    status = Column(Enum(StatusAcordo), default=StatusAcordo.PROPOSTA)

    # Datas
    data_proposta = Column(DateTime, default=datetime.utcnow)
    data_aceite = Column(DateTime, nullable=True)
    data_primeira_parcela = Column(Date, nullable=True)

    # Boletos origem
    boletos_origem = Column(JSONB, default=[])  # Lista de IDs dos boletos incluídos

    # Relacionamentos
    parcelas = relationship("ParcelaAcordo", back_populates="acordo", lazy="dynamic")


class ParcelaAcordo(Base, TimestampMixin):
    """Modelo de Parcela de Acordo"""
    __tablename__ = "parcelas_acordo"
    __table_args__ = {'schema': 'financeiro'}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    acordo_id = Column(UUID(as_uuid=True), ForeignKey('financeiro.acordos.id'), nullable=False)

    numero = Column(Integer, nullable=False)
    valor = Column(Numeric(12, 2), nullable=False)
    vencimento = Column(Date, nullable=False)

    boleto_id = Column(UUID(as_uuid=True), ForeignKey('financeiro.boletos.id'), nullable=True)
    status = Column(String(20), default="pendente")

    acordo = relationship("Acordo", back_populates="parcelas")


class HistoricoCobranca(Base, TimestampMixin):
    """Histórico de Cobranças Enviadas"""
    __tablename__ = "historico_cobrancas"
    __table_args__ = (
        Index('ix_cobrancas_boleto', 'boleto_id'),
        Index('ix_cobrancas_data', 'data_envio'),
        {'schema': 'financeiro'}
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    boleto_id = Column(UUID(as_uuid=True), ForeignKey('financeiro.boletos.id'), nullable=False)
    condominio_id = Column(String(50), nullable=False)

    # Canal
    canal = Column(Enum(CanalCobranca), nullable=False)

    # Resultado
    data_envio = Column(DateTime, default=datetime.utcnow)
    sucesso = Column(Boolean, default=False)
    erro = Column(Text, nullable=True)

    # Rastreamento
    provider_id = Column(String(100), nullable=True)  # ID do provedor (Twilio, SendGrid, etc)
    provider_response = Column(JSONB, default={})

    # Tipo de mensagem
    tipo_mensagem = Column(String(50), nullable=False)  # lembrete, cobranca_leve, etc

    # Interação
    data_leitura = Column(DateTime, nullable=True)
    data_resposta = Column(DateTime, nullable=True)
    resposta = Column(Text, nullable=True)

    boleto = relationship("Boleto", back_populates="cobrancas")


class ScoreUnidade(Base, TimestampMixin):
    """Score de Inadimplência por Unidade"""
    __tablename__ = "scores_unidade"
    __table_args__ = (
        UniqueConstraint('condominio_id', 'unidade_id', name='uq_score_unidade'),
        {'schema': 'financeiro'}
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    condominio_id = Column(String(50), nullable=False, index=True)
    unidade_id = Column(String(50), nullable=False)

    # Score
    score = Column(Integer, nullable=False)  # 0-1000
    classificacao = Column(String(20), nullable=False)
    probabilidade_atraso = Column(Float, nullable=False)

    # Features
    features_json = Column(JSONB, default={})
    fatores_risco = Column(JSONB, default=[])

    # Versão do modelo
    modelo_versao = Column(String(20), nullable=False)
    data_calculo = Column(DateTime, default=datetime.utcnow)


# ==================== AUDIT LOG ====================

class AuditLog(Base):
    """Log de Auditoria - IMUTÁVEL"""
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index('ix_audit_entidade', 'entidade_tipo', 'entidade_id'),
        Index('ix_audit_usuario', 'usuario_id'),
        Index('ix_audit_data', 'created_at'),
        {'schema': 'financeiro'}
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Usuário
    usuario_id = Column(String(50), nullable=False)
    usuario_email = Column(String(200), nullable=False)
    usuario_ip = Column(String(45), nullable=True)
    usuario_user_agent = Column(String(500), nullable=True)

    # Ação
    acao = Column(Enum(TipoAuditoria), nullable=False)
    descricao = Column(String(500), nullable=False)

    # Entidade afetada
    entidade_tipo = Column(String(50), nullable=False)  # boleto, pagamento, acordo, etc
    entidade_id = Column(String(50), nullable=False)

    # Dados
    dados_anteriores = Column(JSONB, nullable=True)
    dados_novos = Column(JSONB, nullable=True)

    # Request
    request_id = Column(String(50), nullable=True)
    endpoint = Column(String(200), nullable=True)
    metodo_http = Column(String(10), nullable=True)


class ConfiguracaoBancaria(Base, TimestampMixin):
    """Configuração de Conta Bancária"""
    __tablename__ = "configuracoes_bancarias"
    __table_args__ = {'schema': 'financeiro'}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    condominio_id = Column(String(50), nullable=False, index=True)

    # Banco
    banco_codigo = Column(String(3), nullable=False)
    banco_nome = Column(String(100), nullable=False)
    agencia = Column(String(10), nullable=False)
    agencia_dv = Column(String(2), nullable=True)
    conta = Column(String(20), nullable=False)
    conta_dv = Column(String(2), nullable=True)

    # Tipo
    tipo_conta = Column(String(20), default="corrente")  # corrente, poupanca

    # Carteira boleto
    carteira = Column(String(5), nullable=True)
    variacao_carteira = Column(String(5), nullable=True)

    # PIX
    chave_pix = Column(String(100), nullable=True)
    tipo_chave_pix = Column(String(20), nullable=True)  # cpf, cnpj, email, telefone, evp

    # Beneficiário
    beneficiario_nome = Column(String(200), nullable=False)
    beneficiario_documento = Column(String(20), nullable=False)

    # Status
    ativo = Column(Boolean, default=True)
    homologado = Column(Boolean, default=False)

    # Credenciais API (criptografadas)
    api_credentials_encrypted = Column(LargeBinary, nullable=True)


# ==================== FUNÇÕES DE SETUP ====================

def create_schema(engine):
    """Cria o schema financeiro se não existir"""
    from sqlalchemy import text
    with engine.connect() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS financeiro"))
        conn.commit()


def create_tables(engine):
    """Cria todas as tabelas"""
    create_schema(engine)
    Base.metadata.create_all(engine)


# ==================== EVENTOS ====================

@event.listens_for(AuditLog, 'before_update')
def prevent_audit_update(mapper, connection, target):
    """Previne atualização de logs de auditoria"""
    raise ValueError("Audit logs são imutáveis e não podem ser alterados")


@event.listens_for(AuditLog, 'before_delete')
def prevent_audit_delete(mapper, connection, target):
    """Previne deleção de logs de auditoria"""
    raise ValueError("Audit logs são imutáveis e não podem ser deletados")
