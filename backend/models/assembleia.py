"""
Conecta Plus - Modelos de Assembleia
"""

import uuid
from datetime import datetime, date, time
from enum import Enum as PyEnum
from sqlalchemy import Column, Integer, String, DateTime, Date, Time, Enum, ForeignKey, Text, Boolean, JSON, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from ..database import Base


class TipoAssembleia(str, PyEnum):
    ORDINARIA = "ordinaria"
    EXTRAORDINARIA = "extraordinaria"


class StatusAssembleia(str, PyEnum):
    AGENDADA = "agendada"
    CONVOCADA = "convocada"
    EM_ANDAMENTO = "em_andamento"
    ENCERRADA = "encerrada"
    CANCELADA = "cancelada"


class ModalidadeAssembleia(str, PyEnum):
    PRESENCIAL = "presencial"
    VIRTUAL = "virtual"
    HIBRIDA = "hibrida"


class Assembleia(Base):
    __tablename__ = "assembleias"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    titulo = Column(String(255), nullable=False)
    tipo = Column(Enum(TipoAssembleia), nullable=False)
    status = Column(Enum(StatusAssembleia), default=StatusAssembleia.AGENDADA)
    modalidade = Column(Enum(ModalidadeAssembleia), default=ModalidadeAssembleia.PRESENCIAL)

    # Data e Local
    data = Column(Date, nullable=False)
    hora_primeira = Column(Time, nullable=False)  # Primeira convocação
    hora_segunda = Column(Time)  # Segunda convocação
    local = Column(String(255))
    link_virtual = Column(String(500))

    # Quórum
    quorum_necessario = Column(Float, default=50)  # Percentual
    quorum_especial = Column(Float)  # Para pautas que exigem quórum especial

    # Pauta
    pautas = Column(JSON, default=[])

    # Edital
    edital_url = Column(String(500))
    data_publicacao_edital = Column(DateTime)

    # Condomínio
    condominio_id = Column(UUID(as_uuid=True), ForeignKey("condominios.id"), nullable=False)
    condominio = relationship("Condominio", back_populates="assembleias")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacionamentos
    votacoes = relationship("Votacao", back_populates="assembleia")
    atas = relationship("Ata", back_populates="assembleia")
    presencas = relationship("PresencaAssembleia", back_populates="assembleia")

    def __repr__(self):
        return f"<Assembleia {self.titulo}>"


class PresencaAssembleia(Base):
    __tablename__ = "presencas_assembleia"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    assembleia_id = Column(UUID(as_uuid=True), ForeignKey("assembleias.id"), nullable=False)
    assembleia = relationship("Assembleia", back_populates="presencas")

    unidade_id = Column(UUID(as_uuid=True), ForeignKey("unidades.id"), nullable=False)
    unidade = relationship("Unidade")

    morador_id = Column(UUID(as_uuid=True), ForeignKey("moradores.id"))
    morador = relationship("Morador")

    # Status
    confirmado = Column(Boolean, default=False)
    presente = Column(Boolean, default=False)
    hora_chegada = Column(Time)
    hora_saida = Column(Time)

    # Procuração
    procuracao = Column(Boolean, default=False)
    procurador_nome = Column(String(255))
    procuracao_url = Column(String(500))

    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<PresencaAssembleia {self.assembleia_id} - {self.unidade_id}>"


class Votacao(Base):
    __tablename__ = "votacoes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    titulo = Column(String(255), nullable=False)
    descricao = Column(Text)

    assembleia_id = Column(UUID(as_uuid=True), ForeignKey("assembleias.id"), nullable=False)
    assembleia = relationship("Assembleia", back_populates="votacoes")

    # Status
    aberta = Column(Boolean, default=False)
    data_abertura = Column(DateTime)
    data_encerramento = Column(DateTime)

    # Tipo de votação
    voto_secreto = Column(Boolean, default=False)
    quorum_especial = Column(Float)  # Percentual necessário para aprovação

    # Resultados
    votos_favor = Column(Integer, default=0)
    votos_contra = Column(Integer, default=0)
    votos_abstencao = Column(Integer, default=0)

    # Resultado final
    aprovada = Column(Boolean)
    resultado_descricao = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Votacao {self.titulo}>"


class Ata(Base):
    __tablename__ = "atas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    assembleia_id = Column(UUID(as_uuid=True), ForeignKey("assembleias.id"), nullable=False)
    assembleia = relationship("Assembleia", back_populates="atas")

    # Conteúdo
    conteudo = Column(Text)
    arquivo_url = Column(String(500))

    # Status
    status = Column(String(20), default="rascunho")  # rascunho, aprovada, publicada

    # Aprovação
    data_aprovacao = Column(DateTime)
    aprovada_por = Column(String(255))

    # Publicação
    data_publicacao = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Ata Assembleia {self.assembleia_id}>"
