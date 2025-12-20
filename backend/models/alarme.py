"""
Conecta Plus - Modelos de Alarme
"""

import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from ..database import Base


class TipoZona(str, PyEnum):
    PERIMETRO = "perimetro"
    INTERNO = "interno"
    INCENDIO = "incendio"
    EMERGENCIA = "emergencia"
    PANICO = "panico"


class StatusZona(str, PyEnum):
    ARMADA = "armada"
    DESARMADA = "desarmada"
    DISPARADA = "disparada"
    BYPASS = "bypass"
    FALHA = "falha"


class TipoEvento(str, PyEnum):
    ARME = "arme"
    DESARME = "desarme"
    DISPARO = "disparo"
    RESTAURACAO = "restauracao"
    FALHA = "falha"
    PANICO = "panico"
    TESTE = "teste"


class ZonaAlarme(Base):
    __tablename__ = "zonas_alarme"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    nome = Column(String(100), nullable=False)
    tipo = Column(Enum(TipoZona), nullable=False)
    status = Column(Enum(StatusZona), default=StatusZona.DESARMADA)
    descricao = Column(Text)

    # Configuração
    numero_sensores = Column(Integer, default=1)
    tempo_entrada = Column(Integer, default=30)  # segundos
    tempo_saida = Column(Integer, default=30)  # segundos
    sirene_habilitada = Column(Boolean, default=True)

    # Hardware
    central_id = Column(String(50))
    zona_id = Column(String(10))

    condominio_id = Column(UUID(as_uuid=True), ForeignKey("condominios.id"), nullable=False)
    condominio = relationship("Condominio", back_populates="zonas_alarme")

    # Último evento
    ultimo_evento = Column(DateTime)
    ultimo_status = Column(String(50))

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacionamentos
    eventos = relationship("EventoAlarme", back_populates="zona")

    def __repr__(self):
        return f"<ZonaAlarme {self.nome}>"


class EventoAlarme(Base):
    __tablename__ = "eventos_alarme"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    tipo = Column(Enum(TipoEvento), nullable=False)
    descricao = Column(Text)

    # Zona
    zona_id = Column(UUID(as_uuid=True), ForeignKey("zonas_alarme.id"), nullable=False)
    zona = relationship("ZonaAlarme", back_populates="eventos")

    # Usuário que causou/tratou
    usuario_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"))
    usuario = relationship("Usuario")

    # Tratamento
    tratado = Column(Boolean, default=False)
    tratado_por = Column(String(255))
    data_tratamento = Column(DateTime)
    observacao_tratamento = Column(Text)

    data_hora = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<EventoAlarme {self.tipo.value}>"
