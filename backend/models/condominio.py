"""
Conecta Plus - Modelo de Condomínio
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from ..database import Base


class Condominio(Base):
    __tablename__ = "condominios"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    nome = Column(String(255), nullable=False)
    cnpj = Column(String(18), unique=True)

    # Endereço (JSONB com estrutura: logradouro, numero, complemento, bairro, cidade, estado, cep)
    endereco = Column(JSONB, default={})

    # Contato
    telefone = Column(String(20))
    email = Column(String(255))

    # Configurações (JSONB com opções do condomínio)
    configuracoes = Column(JSONB, default={})

    # Status
    ativo = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacionamentos
    usuarios = relationship("Usuario", back_populates="condominio")
    unidades = relationship("Unidade", back_populates="condominio")
    areas_comuns = relationship("AreaComum", back_populates="condominio")
    zonas_alarme = relationship("ZonaAlarme", back_populates="condominio")
    pontos_acesso = relationship("PontoAcesso", back_populates="condominio")
    comunicados = relationship("Comunicado", back_populates="condominio")
    assembleias = relationship("Assembleia", back_populates="condominio")
    fornecedores = relationship("Fornecedor", back_populates="condominio")

    def __repr__(self):
        return f"<Condominio {self.nome}>"
