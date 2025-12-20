"""
Conecta Plus - Modelo de Veículo
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from ..database import Base


class Veiculo(Base):
    __tablename__ = "veiculos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    placa = Column(String(10), unique=True, nullable=False)
    modelo = Column(String(100))
    marca = Column(String(50))
    cor = Column(String(30))
    ano = Column(Integer)
    tipo = Column(String(30))  # carro, moto, bicicleta

    # Vínculo
    unidade_id = Column(UUID(as_uuid=True), ForeignKey("unidades.id"), nullable=False)
    unidade = relationship("Unidade", back_populates="veiculos")

    morador_id = Column(UUID(as_uuid=True), ForeignKey("moradores.id"))
    morador = relationship("Morador")

    # Controle de acesso
    tag_acesso = Column(String(50))
    vaga_fixa = Column(String(20))  # Número da vaga

    ativo = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Veiculo {self.placa}>"
