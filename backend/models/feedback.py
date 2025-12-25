"""
Conecta Plus - Q2: Modelos de Aprendizado Continuo
RF-08: Aprendizado Continuo
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


class TipoOrigem(str, enum.Enum):
    """Tipo de entidade que originou o feedback"""
    PREVISAO = "previsao"
    SUGESTAO = "sugestao"
    COMUNICACAO = "comunicacao"
    OCORRENCIA = "ocorrencia"
    ATENDIMENTO = "atendimento"
    GERAL = "geral"


class TipoFeedback(str, enum.Enum):
    """Tipo de feedback"""
    EXPLICITO = "explicito"  # Usuario deu feedback direto
    IMPLICITO = "implicito"  # Sistema inferiu do comportamento


class ValorFeedback(str, enum.Enum):
    """Valores possiveis de feedback"""
    UTIL = "util"
    NAO_UTIL = "nao_util"
    ACEITO = "aceito"
    REJEITADO = "rejeitado"
    CONFIRMADO = "confirmado"
    FALSO_POSITIVO = "falso_positivo"
    IGNORADO = "ignorado"
    SPAM = "spam"


class FeedbackModelo(Base):
    """
    Armazena feedback sobre previsoes, sugestoes e comunicacoes.
    Usado para treinar e melhorar os modelos de ML.
    """
    __tablename__ = "feedback_modelo"
    __table_args__ = {"schema": "conecta"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Origem do feedback
    tipo_origem = Column(
        Enum(TipoOrigem, name="tipo_origem_feedback", schema="conecta",
             values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        index=True
    )
    origem_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Tipo e valor do feedback
    tipo_feedback = Column(
        Enum(TipoFeedback, name="tipo_feedback", schema="conecta",
             values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        index=True
    )
    valor = Column(
        Enum(ValorFeedback, name="valor_feedback", schema="conecta",
             values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        index=True
    )

    # Detalhes adicionais
    comentario = Column(Text, nullable=True)
    avaliacao = Column(Integer, nullable=True)  # 1-5 estrelas
    tags = Column(JSONB, default=list)  # Tags para categorizar

    # Contexto do usuario
    usuario_id = Column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id"),
        nullable=True,
        index=True
    )
    perfil_usuario = Column(String(50), nullable=True)  # sindico, morador, etc

    # Contexto do momento
    contexto = Column(JSONB, default=dict)  # Dados do contexto quando feedback foi dado

    # Uso no treinamento
    usado_treinamento = Column(Boolean, default=False)
    data_treinamento = Column(DateTime, nullable=True)
    versao_modelo = Column(String(50), nullable=True)
    peso = Column(Float, default=1.0)  # Peso do feedback no treinamento

    # Relacionamentos
    condominio_id = Column(
        UUID(as_uuid=True),
        ForeignKey("condominios.id"),
        nullable=False,
        index=True
    )

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    def __repr__(self):
        return f"<FeedbackModelo {self.tipo_origem.value} valor={self.valor.value}>"

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionario"""
        return {
            "id": str(self.id),
            "tipo_origem": self.tipo_origem.value,
            "origem_id": str(self.origem_id),
            "tipo_feedback": self.tipo_feedback.value,
            "valor": self.valor.value,
            "comentario": self.comentario,
            "avaliacao": self.avaliacao,
            "usuario_id": str(self.usuario_id) if self.usuario_id else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class MetricaModelo(Base):
    """
    Armazena metricas de performance dos modelos de ML.
    Usado para monitorar e comparar versoes.
    """
    __tablename__ = "metricas_modelo"
    __table_args__ = {"schema": "conecta"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Identificacao do modelo
    modelo = Column(String(100), nullable=False, index=True)  # previsao_inadimplencia, etc
    versao = Column(String(50), nullable=False, index=True)

    # Periodo de avaliacao
    periodo_inicio = Column(DateTime, nullable=False)
    periodo_fim = Column(DateTime, nullable=False)

    # Metricas de classificacao
    total_predicoes = Column(Integer, default=0)
    verdadeiros_positivos = Column(Integer, default=0)
    falsos_positivos = Column(Integer, default=0)
    verdadeiros_negativos = Column(Integer, default=0)
    falsos_negativos = Column(Integer, default=0)

    # Metricas calculadas
    precision_val = Column("precision", Float, nullable=True)  # Renomeado para evitar conflito
    recall_val = Column("recall", Float, nullable=True)
    f1_score = Column(Float, nullable=True)
    accuracy = Column(Float, nullable=True)

    # Metricas de negocio
    taxa_aceitacao = Column(Float, nullable=True)  # Para sugestoes
    taxa_utilidade = Column(Float, nullable=True)
    nps = Column(Float, nullable=True)  # Net Promoter Score
    economia_gerada = Column(Float, nullable=True)  # Em reais
    problemas_evitados = Column(Integer, nullable=True)

    # Metricas de comunicacao
    taxa_entrega = Column(Float, nullable=True)
    taxa_abertura = Column(Float, nullable=True)
    taxa_clique = Column(Float, nullable=True)
    tempo_medio_resposta = Column(Float, nullable=True)  # Em segundos

    # Detalhes adicionais
    detalhes = Column(JSONB, default=dict)
    notas = Column(Text, nullable=True)

    # Condominio (None = metricas globais)
    condominio_id = Column(
        UUID(as_uuid=True),
        ForeignKey("condominios.id"),
        nullable=True,
        index=True
    )

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<MetricaModelo {self.modelo} v{self.versao}>"

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionario"""
        return {
            "id": str(self.id),
            "modelo": self.modelo,
            "versao": self.versao,
            "periodo_inicio": self.periodo_inicio.isoformat() if self.periodo_inicio else None,
            "periodo_fim": self.periodo_fim.isoformat() if self.periodo_fim else None,
            "metricas_classificacao": {
                "total_predicoes": self.total_predicoes,
                "verdadeiros_positivos": self.verdadeiros_positivos,
                "falsos_positivos": self.falsos_positivos,
                "verdadeiros_negativos": self.verdadeiros_negativos,
                "falsos_negativos": self.falsos_negativos,
            },
            "metricas_calculadas": {
                "precision": self.precision_val,
                "recall": self.recall_val,
                "f1_score": self.f1_score,
                "accuracy": self.accuracy,
            },
            "metricas_negocio": {
                "taxa_aceitacao": self.taxa_aceitacao,
                "taxa_utilidade": self.taxa_utilidade,
                "nps": self.nps,
                "economia_gerada": self.economia_gerada,
                "problemas_evitados": self.problemas_evitados,
            },
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def calcular_metricas(self) -> None:
        """Calcula precision, recall, f1_score e accuracy"""
        tp = self.verdadeiros_positivos or 0
        fp = self.falsos_positivos or 0
        tn = self.verdadeiros_negativos or 0
        fn = self.falsos_negativos or 0

        # Precision = TP / (TP + FP)
        if tp + fp > 0:
            self.precision_val = tp / (tp + fp)

        # Recall = TP / (TP + FN)
        if tp + fn > 0:
            self.recall_val = tp / (tp + fn)

        # F1 = 2 * (precision * recall) / (precision + recall)
        if self.precision_val and self.recall_val and (self.precision_val + self.recall_val) > 0:
            self.f1_score = 2 * (self.precision_val * self.recall_val) / (self.precision_val + self.recall_val)

        # Accuracy = (TP + TN) / (TP + TN + FP + FN)
        total = tp + tn + fp + fn
        if total > 0:
            self.accuracy = (tp + tn) / total


class HistoricoTreinamento(Base):
    """
    Historico de treinamentos dos modelos.
    Registro de quando e como os modelos foram atualizados.
    """
    __tablename__ = "historico_treinamento"
    __table_args__ = {"schema": "conecta"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Modelo
    modelo = Column(String(100), nullable=False, index=True)
    versao_anterior = Column(String(50), nullable=True)
    versao_nova = Column(String(50), nullable=False)

    # Dados de treinamento
    total_amostras = Column(Integer, nullable=False)
    amostras_positivas = Column(Integer, nullable=True)
    amostras_negativas = Column(Integer, nullable=True)
    periodo_dados_inicio = Column(DateTime, nullable=True)
    periodo_dados_fim = Column(DateTime, nullable=True)

    # Parametros do treinamento
    parametros = Column(JSONB, default=dict)
    features = Column(JSONB, default=list)  # Lista de features usadas

    # Resultados
    metricas_validacao = Column(JSONB, default=dict)  # Metricas no conjunto de validacao
    melhorou = Column(Boolean, nullable=True)  # Se melhorou em relacao a versao anterior
    delta_f1 = Column(Float, nullable=True)  # Diferenca no F1 score

    # Deploy
    deployed = Column(Boolean, default=False)
    deployed_em = Column(DateTime, nullable=True)
    rollback = Column(Boolean, default=False)
    rollback_motivo = Column(String(500), nullable=True)

    # Metadata
    duracao_segundos = Column(Integer, nullable=True)
    executado_por = Column(String(100), nullable=True)  # Sistema ou usuario
    notas = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<HistoricoTreinamento {self.modelo} {self.versao_anterior}->{self.versao_nova}>"

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionario"""
        return {
            "id": str(self.id),
            "modelo": self.modelo,
            "versao_anterior": self.versao_anterior,
            "versao_nova": self.versao_nova,
            "total_amostras": self.total_amostras,
            "metricas_validacao": self.metricas_validacao,
            "melhorou": self.melhorou,
            "deployed": self.deployed,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
