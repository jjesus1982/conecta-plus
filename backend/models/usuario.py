"""
Conecta Plus - Modelo de Usuário
"""

import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from ..database import Base


class Role(str, PyEnum):
    ADMIN = "admin"
    SINDICO = "sindico"
    GERENTE = "gerente"
    PORTEIRO = "porteiro"
    MORADOR = "morador"
    VISITANTE = "visitante"


class AuthProvider(str, PyEnum):
    LOCAL = "local"
    GOOGLE = "google"
    MICROSOFT = "microsoft"
    LDAP = "ldap"


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    senha_hash = Column(String(255), nullable=True)  # Nullable para OAuth users
    nome = Column(String(255), nullable=False)
    telefone = Column(String(20))
    role = Column(Enum(Role), default=Role.MORADOR)
    ativo = Column(Boolean, default=True)
    avatar_url = Column(String(500))

    # OAuth/SSO Fields
    auth_provider = Column(Enum(AuthProvider), default=AuthProvider.LOCAL)
    oauth_id = Column(String(255), unique=True, nullable=True, index=True)
    oauth_access_token = Column(String(2000), nullable=True)
    oauth_refresh_token = Column(String(2000), nullable=True)
    oauth_token_expires = Column(DateTime, nullable=True)

    # LDAP Fields
    ldap_dn = Column(String(500), nullable=True)
    ldap_groups = Column(String(2000), nullable=True)  # JSON string of groups

    condominio_id = Column(UUID(as_uuid=True), ForeignKey("condominios.id"))
    condominio = relationship("Condominio", back_populates="usuarios")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime)

    # Relacionamentos
    morador = relationship("Morador", back_populates="usuario", uselist=False)
    ocorrencias_criadas = relationship("Ocorrencia", back_populates="reportador", foreign_keys="Ocorrencia.reportado_por")

    def __repr__(self):
        return f"<Usuario {self.email}>"
