"""
Conecta Plus - Modelo de Unidade
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from ..database import Base


class Unidade(Base):
    __tablename__ = "unidades"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    numero = Column(String(20), nullable=False)  # Ex: "101", "A-201"
    bloco = Column(String(50))
    tipo = Column(String(50), default="apartamento")
    area_m2 = Column(Numeric(10, 2))

    condominio_id = Column(UUID(as_uuid=True), ForeignKey("condominios.id"), nullable=False)
    condominio = relationship("Condominio", back_populates="unidades")

    proprietario_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"))
    proprietario = relationship("Usuario")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacionamentos
    moradores = relationship("Morador", back_populates="unidade")
    veiculos = relationship("Veiculo", back_populates="unidade")
    ocorrencias = relationship("Ocorrencia", back_populates="unidade")
    reservas = relationship("Reserva", back_populates="unidade")
    lancamentos = relationship("Lancamento", back_populates="unidade")
    boletos = relationship("Boleto", back_populates="unidade")

    def __repr__(self):
        return f"<Unidade {self.bloco}-{self.identificador}>"
