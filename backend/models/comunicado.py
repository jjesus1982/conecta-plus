"""
Conecta Plus - Modelo de Comunicado
"""

import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey, Text, Boolean, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from ..database import Base


class TipoComunicado(str, PyEnum):
    AVISO = "aviso"
    INFORMATIVO = "informativo"
    URGENTE = "urgente"
    MANUTENCAO = "manutencao"
    EVENTO = "evento"
    ASSEMBLEIA = "assembleia"
    FINANCEIRO = "financeiro"


class Comunicado(Base):
    __tablename__ = "comunicados"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    titulo = Column(String(255), nullable=False)
    conteudo = Column(Text, nullable=False)
    tipo = Column(Enum(TipoComunicado), default=TipoComunicado.AVISO)

    # Autor
    autor_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=False)
    autor = relationship("Usuario")

    # Condomínio
    condominio_id = Column(UUID(as_uuid=True), ForeignKey("condominios.id"), nullable=False)
    condominio = relationship("Condominio", back_populates="comunicados")

    # Publicação
    publicado = Column(Boolean, default=False)
    data_publicacao = Column(DateTime)
    data_expiracao = Column(DateTime)

    # Destinatários
    destinatarios = Column(JSON, default=["todos"])  # ["todos", "sindico", "bloco_a", etc]

    # Notificação
    enviar_email = Column(Boolean, default=True)
    enviar_push = Column(Boolean, default=True)
    enviar_whatsapp = Column(Boolean, default=False)

    # Anexos
    anexos = Column(JSON, default=[])

    # Fixado no topo
    fixado = Column(Boolean, default=False)

    # Visualizações
    visualizacoes = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Comunicado {self.titulo}>"
