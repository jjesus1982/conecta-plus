"""
Conecta Plus - Modelo de Ocorrência
"""

import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from ..database import Base


class TipoOcorrencia(str, PyEnum):
    BARULHO = "barulho"
    MANUTENCAO = "manutencao"
    SEGURANCA = "seguranca"
    LIMPEZA = "limpeza"
    ESTACIONAMENTO = "estacionamento"
    ANIMAIS = "animais"
    OBRAS = "obras"
    VAZAMENTO = "vazamento"
    AREA_COMUM = "area_comum"
    OUTROS = "outros"


class StatusOcorrencia(str, PyEnum):
    ABERTA = "aberta"
    EM_ANALISE = "em_analise"
    EM_ANDAMENTO = "em_andamento"
    AGUARDANDO = "aguardando"
    RESOLVIDA = "resolvida"
    CANCELADA = "cancelada"


class Ocorrencia(Base):
    __tablename__ = "ocorrencias"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    condominio_id = Column(UUID(as_uuid=True), ForeignKey("condominios.id"), nullable=False)

    titulo = Column(String(255), nullable=False)
    descricao = Column(Text)
    tipo = Column(String(50))
    prioridade = Column(String(20), default="media")
    status = Column(String(50), default="aberta")

    # Quem reportou
    reportado_por = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"))
    reportador = relationship("Usuario", back_populates="ocorrencias_criadas", foreign_keys=[reportado_por])

    # Unidade
    unidade_id = Column(UUID(as_uuid=True), ForeignKey("unidades.id"))
    unidade = relationship("Unidade", back_populates="ocorrencias")

    # Responsável pelo atendimento
    responsavel_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"))
    responsavel = relationship("Usuario", foreign_keys=[responsavel_id])

    # Anexos
    anexos = Column(JSONB, default=[])

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolvido_at = Column(DateTime)

    def __repr__(self):
        return f"<Ocorrencia {self.titulo}>"
