"""
Conecta Plus - Q2: Modelo de Sugestoes Automaticas
RF-06: Sugestoes Automaticas
"""

import enum
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import uuid4

from sqlalchemy import (
    Column, String, DateTime, Integer, Float, Boolean,
    ForeignKey, Text, Enum
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from ..database import Base


class TipoSugestao(str, enum.Enum):
    """Categorias de sugestao"""
    OPERACIONAL = "operacional"
    FINANCEIRA = "financeira"
    CONVIVENCIA = "convivencia"
    SEGURANCA = "seguranca"
    MANUTENCAO = "manutencao"


class CodigoSugestao(str, enum.Enum):
    """Codigos especificos de sugestao"""
    # Operacionais
    OTIMIZAR_RONDA = "otimizar_ronda"
    REAGENDAR_MANUTENCAO = "reagendar_manutencao"
    CONSOLIDAR_COMUNICADOS = "consolidar_comunicados"
    # Financeiras
    RENEGOCIAR_CONTRATO = "renegociar_contrato"
    ANTECIPAR_COBRANCA = "antecipar_cobranca"
    RESERVA_EMERGENCIA = "reserva_emergencia"
    REDUZIR_CUSTOS = "reduzir_custos"
    # Convivencia
    MEDIAR_CONFLITO = "mediar_conflito"
    RECONHECER_COLABORADOR = "reconhecer_colaborador"
    EVENTO_INTEGRACAO = "evento_integracao"
    # Seguranca
    REFORCAR_HORARIO = "reforcar_horario"
    ATUALIZAR_CADASTRO = "atualizar_cadastro"
    # Manutencao
    PREVENTIVA_URGENTE = "preventiva_urgente"
    SUBSTITUIR_EQUIPAMENTO = "substituir_equipamento"


class StatusSugestao(str, enum.Enum):
    """Status da sugestao"""
    PENDENTE = "pendente"
    VISUALIZADA = "visualizada"
    ACEITA = "aceita"
    REJEITADA = "rejeitada"
    EXPIRADA = "expirada"
    EM_ANDAMENTO = "em_andamento"
    CONCLUIDA = "concluida"


class PerfilDestino(str, enum.Enum):
    """Perfil de usuario destino"""
    SINDICO = "sindico"
    ADMIN = "admin"
    PORTEIRO = "porteiro"
    ZELADOR = "zelador"
    MORADOR = "morador"
    CONSELHO = "conselho"


class Sugestao(Base):
    """
    Modelo para armazenar sugestoes automaticas.
    O sistema recomenda acoes baseadas em padroes e contexto.
    """
    __tablename__ = "sugestoes"
    __table_args__ = {"schema": "conecta"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Classificacao
    tipo = Column(
        Enum(TipoSugestao, name="tipo_sugestao", schema="conecta",
             values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        index=True
    )
    codigo = Column(
        Enum(CodigoSugestao, name="codigo_sugestao", schema="conecta",
             values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        index=True
    )

    # Conteudo
    titulo = Column(String(255), nullable=False)
    descricao = Column(Text, nullable=False)
    contexto = Column(Text, nullable=True)  # Por que esta sugerindo
    beneficio_estimado = Column(String(255), nullable=True)  # Ex: "Economia de R$ 500/mes"

    # Dados que geraram a sugestao
    dados_entrada = Column(JSONB, default=dict)
    regra_aplicada = Column(String(100), nullable=True)

    # Destinatario
    perfil_destino = Column(
        Enum(PerfilDestino, name="perfil_destino_sugestao", schema="conecta",
             values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        index=True
    )
    usuario_destino_id = Column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id"),
        nullable=True,
        index=True
    )

    # Acao
    acao_url = Column(String(500), nullable=True)  # Link para executar acao
    acao_params = Column(JSONB, default=dict)  # Parametros pre-preenchidos
    acao_automatica = Column(Boolean, default=False)  # Se pode ser executada automaticamente

    # Status
    status = Column(
        Enum(StatusSugestao, name="status_sugestao", schema="conecta",
             values_callable=lambda obj: [e.value for e in obj]),
        default=StatusSugestao.PENDENTE,
        nullable=False,
        index=True
    )
    visualizada_em = Column(DateTime, nullable=True)
    respondida_em = Column(DateTime, nullable=True)
    respondida_por = Column(UUID(as_uuid=True), ForeignKey("conecta.usuarios.id"), nullable=True)
    motivo_rejeicao = Column(String(500), nullable=True)

    # Execucao (se aceita)
    executada_em = Column(DateTime, nullable=True)
    resultado_execucao = Column(Text, nullable=True)

    # Feedback
    foi_util = Column(Boolean, nullable=True)
    feedback = Column(Text, nullable=True)
    avaliacao = Column(Integer, nullable=True)  # 1-5 estrelas

    # Prioridade e ordenacao
    prioridade = Column(Integer, default=50)  # 1-100 (100 = mais urgente)
    score_relevancia = Column(Float, default=0.5)  # Score de ML

    # Relacionamentos
    condominio_id = Column(
        UUID(as_uuid=True),
        ForeignKey("condominios.id"),
        nullable=False,
        index=True
    )

    # Previsao relacionada (se gerada a partir de uma previsao)
    previsao_id = Column(
        UUID(as_uuid=True),
        ForeignKey("previsoes.id"),
        nullable=True
    )

    # Modelo que gerou a sugestao
    modelo_versao = Column(String(50), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<Sugestao {self.codigo.value} status={self.status.value}>"

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionario"""
        return {
            "id": str(self.id),
            "tipo": self.tipo.value,
            "codigo": self.codigo.value,
            "titulo": self.titulo,
            "descricao": self.descricao,
            "contexto": self.contexto,
            "beneficio_estimado": self.beneficio_estimado,
            "perfil_destino": self.perfil_destino.value,
            "acao_url": self.acao_url,
            "status": self.status.value,
            "prioridade": self.prioridade,
            "foi_util": self.foi_util,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }

    @property
    def is_expired(self) -> bool:
        """Verifica se a sugestao expirou"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at

    @property
    def urgencia(self) -> str:
        """Classifica urgencia baseada na prioridade"""
        if self.prioridade >= 80:
            return "critica"
        elif self.prioridade >= 60:
            return "alta"
        elif self.prioridade >= 40:
            return "media"
        else:
            return "baixa"

    def aceitar(self, usuario_id: UUID) -> None:
        """Marca sugestao como aceita"""
        self.status = StatusSugestao.ACEITA
        self.respondida_em = datetime.utcnow()
        self.respondida_por = usuario_id

    def rejeitar(self, usuario_id: UUID, motivo: str = None) -> None:
        """Marca sugestao como rejeitada"""
        self.status = StatusSugestao.REJEITADA
        self.respondida_em = datetime.utcnow()
        self.respondida_por = usuario_id
        self.motivo_rejeicao = motivo

    def registrar_feedback(self, util: bool, texto: str = None, avaliacao: int = None) -> None:
        """Registra feedback do usuario"""
        self.foi_util = util
        self.feedback = texto
        if avaliacao and 1 <= avaliacao <= 5:
            self.avaliacao = avaliacao
