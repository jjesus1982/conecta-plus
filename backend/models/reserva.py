"""
Conecta Plus - Modelos de Reserva
"""

import uuid
from datetime import datetime, date, time
from enum import Enum as PyEnum
from decimal import Decimal
from sqlalchemy import Column, String, DateTime, Date, Time, Enum, ForeignKey, Text, Boolean, Numeric, ARRAY, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from ..database import Base


class StatusReserva(str, PyEnum):
    PENDENTE = "pendente"
    CONFIRMADA = "confirmada"
    CANCELADA = "cancelada"
    CONCLUIDA = "concluida"


class AreaComum(Base):
    __tablename__ = "areas_comuns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    condominio_id = Column(UUID(as_uuid=True), ForeignKey("condominios.id"), nullable=False)
    condominio = relationship("Condominio", back_populates="areas_comuns")

    nome = Column(String(100), nullable=False)
    descricao = Column(Text)
    capacidade = Column(Integer)
    valor = Column(Numeric(10, 2), default=0)
    regras = Column(Text)

    horario_abertura = Column(Time)
    horario_fechamento = Column(Time)
    dias_funcionamento = Column(ARRAY(Integer), default=[1, 2, 3, 4, 5, 6, 0])

    ativo = Column(Boolean, default=True)
    fotos = Column(JSONB, default=[])

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacionamentos
    reservas = relationship("Reserva", back_populates="area")

    def __repr__(self):
        return f"<AreaComum {self.nome}>"


class Reserva(Base):
    __tablename__ = "reservas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Área
    area_id = Column(UUID(as_uuid=True), ForeignKey("areas_comuns.id"), nullable=False)
    area = relationship("AreaComum", back_populates="reservas")

    # Unidade
    unidade_id = Column(UUID(as_uuid=True), ForeignKey("unidades.id"), nullable=False)
    unidade = relationship("Unidade", back_populates="reservas")

    # Responsável
    responsavel_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=False)
    responsavel = relationship("Usuario")

    # Período
    data = Column(Date, nullable=False)
    hora_inicio = Column(Time, nullable=False)
    hora_fim = Column(Time, nullable=False)

    # Status
    status = Column(Enum(StatusReserva), default=StatusReserva.PENDENTE)

    # Evento
    evento_nome = Column(String(255))
    num_convidados = Column(Integer, default=0)

    # Valores
    valor_total = Column(Numeric(10, 2), default=0)
    caucao_pago = Column(Boolean, default=False)

    # Aprovação
    aprovado_por = Column(String(255))
    data_aprovacao = Column(DateTime)
    motivo_cancelamento = Column(Text)

    observacoes = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Reserva {self.area_id} - {self.data}>"
