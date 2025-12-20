"""
Conecta Plus - Modelo de Morador
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from ..database import Base


class TipoMorador(str):
    MORADOR = "morador"
    PROPRIETARIO = "proprietario"
    INQUILINO = "inquilino"
    DEPENDENTE = "dependente"
    FUNCIONARIO = "funcionario"


class Morador(Base):
    __tablename__ = "moradores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Vínculo com usuário do sistema
    usuario_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=False)
    usuario = relationship("Usuario", back_populates="morador")

    # Vínculo com unidade
    unidade_id = Column(UUID(as_uuid=True), ForeignKey("unidades.id"), nullable=False)
    unidade = relationship("Unidade", back_populates="moradores")

    tipo = Column(String(50), default="morador")
    principal = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Morador {self.id}>"
