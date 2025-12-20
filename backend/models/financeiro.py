"""
Conecta Plus - Modelos Financeiros
"""

import uuid
from datetime import datetime, date
from enum import Enum as PyEnum
from decimal import Decimal
from sqlalchemy import Column, String, DateTime, Date, ForeignKey, Text, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.types import Numeric
from sqlalchemy.orm import relationship

from ..database import Base


class TipoLancamento(str, PyEnum):
    RECEITA = "receita"
    DESPESA = "despesa"


class StatusBoleto(str, PyEnum):
    ABERTO = "aberto"
    PAGO = "pago"
    VENCIDO = "vencido"
    CANCELADO = "cancelado"
    NEGOCIADO = "negociado"


class Lancamento(Base):
    __tablename__ = "lancamentos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    condominio_id = Column(UUID(as_uuid=True), ForeignKey("condominios.id"), nullable=False)
    conta_bancaria_id = Column(UUID(as_uuid=True))
    categoria_id = Column(UUID(as_uuid=True))
    unidade_id = Column(UUID(as_uuid=True), ForeignKey("unidades.id"))
    unidade = relationship("Unidade", back_populates="lancamentos")

    tipo = Column(String(20), nullable=False)  # Uses PostgreSQL enum tipo_lancamento
    valor = Column(Numeric(15, 2), nullable=False)

    data_lancamento = Column(Date, nullable=False)
    data_vencimento = Column(Date)
    data_pagamento = Column(Date)
    data_competencia = Column(Date)

    descricao = Column(Text, nullable=False)
    observacao = Column(Text)

    fornecedor_nome = Column(String(200))
    fornecedor_documento = Column(String(20))

    documento_tipo = Column(String(50))
    documento_numero = Column(String(50))
    documento_url = Column(Text)

    rateio = Column(Boolean, default=False)
    rateio_config = Column(JSONB)

    status = Column(String(50), default="pendente")  # Uses PostgreSQL enum status_lancamento

    recorrente = Column(Boolean, default=False)
    recorrencia_config = Column(JSONB)

    lancamento_pai_id = Column(UUID(as_uuid=True), ForeignKey("lancamentos.id"))

    conciliado = Column(Boolean, default=False)
    conciliacao_id = Column(UUID(as_uuid=True))

    aprovado = Column(Boolean, default=False)
    aprovado_por = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"))
    aprovado_em = Column(DateTime)
    criado_por = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"))

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Lancamento {self.descricao} - R$ {self.valor}>"


class Boleto(Base):
    __tablename__ = "boletos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    condominio_id = Column(UUID(as_uuid=True), ForeignKey("condominios.id"), nullable=False)
    unidade_id = Column(UUID(as_uuid=True), ForeignKey("unidades.id"), nullable=False)
    unidade = relationship("Unidade", back_populates="boletos")

    referencia = Column(String(20), nullable=False)
    tipo = Column(String(50), default="condominio")
    descricao = Column(Text)

    valor = Column(Numeric(10, 2), nullable=False)
    data_vencimento = Column(Date, nullable=False)
    data_pagamento = Column(Date)
    valor_pago = Column(Numeric(10, 2))

    valor_juros = Column(Numeric(10, 2), default=0)
    valor_multa = Column(Numeric(10, 2), default=0)
    valor_desconto = Column(Numeric(10, 2), default=0)
    valor_total = Column(Numeric(10, 2))

    status = Column(String(50), default="aberto")

    linha_digitavel = Column(String(100))
    codigo_barras = Column(String(100))
    pdf_url = Column(String(500))

    pix_txid = Column(String(100))
    pix_qrcode = Column(Text)
    pix_copia_cola = Column(Text)

    nosso_numero = Column(String(50))
    banco_id = Column(UUID(as_uuid=True))
    banco_boleto_id = Column(String(100))
    banco_response = Column(JSONB)

    acordo_id = Column(UUID(as_uuid=True))
    parcela = Column(Integer)
    total_parcelas = Column(Integer)

    competencia = Column(Date)
    forma_pagamento = Column(String(50))
    conciliacao_id = Column(UUID(as_uuid=True))

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Boleto {self.referencia}>"
