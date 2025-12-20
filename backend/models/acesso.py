"""
Conecta Plus - Modelos de Controle de Acesso
"""

import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from ..database import Base


class TipoAcesso(str, PyEnum):
    ENTRADA = "entrada"
    SAIDA = "saida"


class TipoPonto(str, PyEnum):
    PORTAO_SOCIAL = "portao_social"
    PORTAO_SERVICO = "portao_servico"
    GARAGEM = "garagem"
    PEDESTRES = "pedestres"
    ELEVADOR = "elevador"


class MetodoAcesso(str, PyEnum):
    TAG = "tag"
    BIOMETRIA = "biometria"
    FACIAL = "facial"
    QR_CODE = "qr_code"
    SENHA = "senha"
    REMOTO = "remoto"
    MANUAL = "manual"


class PontoAcesso(Base):
    __tablename__ = "pontos_acesso"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    nome = Column(String(100), nullable=False)
    tipo = Column(Enum(TipoPonto), nullable=False)
    descricao = Column(Text)

    condominio_id = Column(UUID(as_uuid=True), ForeignKey("condominios.id"), nullable=False)
    condominio = relationship("Condominio", back_populates="pontos_acesso")

    # Hardware
    controlador_ip = Column(String(15))
    camera_id = Column(String(50))

    # Status
    online = Column(Boolean, default=True)
    status = Column(String(20), default="fechado")  # aberto, fechado, travado, erro

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relacionamentos
    registros = relationship("RegistroAcesso", back_populates="ponto")

    def __repr__(self):
        return f"<PontoAcesso {self.nome}>"


class RegistroAcesso(Base):
    __tablename__ = "registros_acesso"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    tipo = Column(Enum(TipoAcesso), nullable=False)
    metodo = Column(Enum(MetodoAcesso), nullable=False)

    # Ponto de acesso
    ponto_id = Column(UUID(as_uuid=True), ForeignKey("pontos_acesso.id"), nullable=False)
    ponto = relationship("PontoAcesso", back_populates="registros")

    # Quem acessou (pode ser morador, visitante ou veículo)
    morador_id = Column(UUID(as_uuid=True), ForeignKey("moradores.id"))
    morador = relationship("Morador")

    veiculo_id = Column(UUID(as_uuid=True), ForeignKey("veiculos.id"))
    veiculo = relationship("Veiculo")

    # Para visitantes não cadastrados
    visitante_nome = Column(String(255))
    visitante_documento = Column(String(20))
    visitante_foto_url = Column(String(500))
    destino_unidade_id = Column(UUID(as_uuid=True), ForeignKey("unidades.id"))

    # Autorização
    autorizado = Column(Boolean, default=True)
    autorizado_por = Column(String(255))  # Morador ou porteiro que autorizou

    # Captura
    foto_captura_url = Column(String(500))
    placa_capturada = Column(String(10))

    observacao = Column(Text)

    data_hora = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<RegistroAcesso {self.id} - {self.tipo.value}>"
