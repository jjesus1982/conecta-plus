"""
Conecta Plus - Modelos de Manutenção
"""

import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey, Text, JSON, Float, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from ..database import Base


class TipoOS(str, PyEnum):
    PREVENTIVA = "preventiva"
    CORRETIVA = "corretiva"
    EMERGENCIAL = "emergencial"


class StatusOS(str, PyEnum):
    ABERTA = "aberta"
    EM_ANDAMENTO = "em_andamento"
    AGUARDANDO_MATERIAL = "aguardando_material"
    AGUARDANDO_APROVACAO = "aguardando_aprovacao"
    CONCLUIDA = "concluida"
    CANCELADA = "cancelada"


class PrioridadeOS(str, PyEnum):
    BAIXA = "baixa"
    MEDIA = "media"
    ALTA = "alta"
    URGENTE = "urgente"


class Fornecedor(Base):
    __tablename__ = "fornecedores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    nome = Column(String(255), nullable=False)
    cnpj = Column(String(18))
    especialidade = Column(String(100))
    telefone = Column(String(20))
    email = Column(String(255))
    endereco = Column(Text)

    condominio_id = Column(UUID(as_uuid=True), ForeignKey("condominios.id"), nullable=False)
    condominio = relationship("Condominio", back_populates="fornecedores")

    # Avaliação
    avaliacao_media = Column(Float, default=0)
    total_avaliacoes = Column(Integer, default=0)

    ativo = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacionamentos
    ordens_servico = relationship("OrdemServico", back_populates="fornecedor")

    def __repr__(self):
        return f"<Fornecedor {self.nome}>"


class OrdemServico(Base):
    __tablename__ = "ordens_servico"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    numero = Column(String(20), unique=True, nullable=False)
    titulo = Column(String(255), nullable=False)
    descricao = Column(Text)
    tipo = Column(Enum(TipoOS), nullable=False)
    status = Column(Enum(StatusOS), default=StatusOS.ABERTA)
    prioridade = Column(Enum(PrioridadeOS), default=PrioridadeOS.MEDIA)

    # Localização
    local = Column(String(255))
    equipamento = Column(String(255))

    # Solicitante
    solicitante_nome = Column(String(255))
    solicitante_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"))
    solicitante = relationship("Usuario", foreign_keys=[solicitante_id])

    # Responsável interno
    responsavel_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"))
    responsavel = relationship("Usuario", foreign_keys=[responsavel_id])

    # Fornecedor externo
    fornecedor_id = Column(UUID(as_uuid=True), ForeignKey("fornecedores.id"))
    fornecedor = relationship("Fornecedor", back_populates="ordens_servico")

    # Custos
    custo_estimado = Column(Float)
    custo_real = Column(Float)
    aprovado_por = Column(String(255))
    data_aprovacao = Column(DateTime)

    # Datas
    data_abertura = Column(DateTime, default=datetime.utcnow)
    data_previsao = Column(DateTime)
    data_inicio = Column(DateTime)
    data_conclusao = Column(DateTime)

    # Anexos e histórico
    anexos = Column(JSON, default=[])
    historico = Column(JSON, default=[])

    # Avaliação
    avaliacao = Column(Integer)
    comentario_avaliacao = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<OrdemServico {self.numero}>"


class ManutencaoProgramada(Base):
    __tablename__ = "manutencoes_programadas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    equipamento = Column(String(255), nullable=False)
    descricao = Column(Text)
    tipo_manutencao = Column(String(100))

    # Frequência
    frequencia = Column(String(50))  # diaria, semanal, mensal, trimestral, semestral, anual
    dia_semana = Column(Integer)  # 0-6 para frequência semanal
    dia_mes = Column(Integer)  # 1-31 para frequência mensal

    # Próxima execução
    proxima_data = Column(DateTime)
    ultima_execucao = Column(DateTime)

    # Responsável
    responsavel = Column(String(255))
    fornecedor_id = Column(UUID(as_uuid=True), ForeignKey("fornecedores.id"))

    condominio_id = Column(UUID(as_uuid=True), ForeignKey("condominios.id"), nullable=False)

    ativo = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<ManutencaoProgramada {self.equipamento}>"
