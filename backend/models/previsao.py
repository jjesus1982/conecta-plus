"""
Conecta Plus - Q2: Modelo de Previsao de Problemas
RF-05: Previsao de Problemas
"""

import enum
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import uuid4

from sqlalchemy import (
    Column, String, DateTime, Integer, Float, Boolean,
    ForeignKey, Text, Enum
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from ..database import Base


class TipoPrevisao(str, enum.Enum):
    """Categorias de previsao"""
    FINANCEIRO = "financeiro"
    MANUTENCAO = "manutencao"
    SEGURANCA = "seguranca"
    CONVIVENCIA = "convivencia"


class SubtipoPrevisao(str, enum.Enum):
    """Subtipos especificos de previsao"""
    # Financeiro
    INADIMPLENCIA_RISCO = "inadimplencia_risco"
    FLUXO_CAIXA_ALERTA = "fluxo_caixa_alerta"
    # Manutencao
    EQUIPAMENTO_RISCO = "equipamento_risco"
    AREA_COMUM_DESGASTE = "area_comum_desgaste"
    # Seguranca
    HORARIO_VULNERAVEL = "horario_vulneravel"
    PADRAO_ANOMALO = "padrao_anomalo"
    # Convivencia
    CONFLITO_POTENCIAL = "conflito_potencial"


class StatusPrevisao(str, enum.Enum):
    """Status da previsao"""
    PENDENTE = "pendente"
    CONFIRMADA = "confirmada"
    EVITADA = "evitada"
    FALSO_POSITIVO = "falso_positivo"
    EXPIRADA = "expirada"


class TipoEntidadePrevisao(str, enum.Enum):
    """Tipo de entidade relacionada a previsao"""
    MORADOR = "morador"
    UNIDADE = "unidade"
    EQUIPAMENTO = "equipamento"
    AREA = "area"
    CONDOMINIO = "condominio"


class Previsao(Base):
    """
    Modelo para armazenar previsoes de problemas.
    O sistema analisa tendencias e preve problemas antes que ocorram.
    """
    __tablename__ = "previsoes"
    __table_args__ = {"schema": "conecta"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Classificacao
    tipo = Column(
        Enum(TipoPrevisao, name="tipo_previsao", schema="conecta",
             values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        index=True
    )
    subtipo = Column(
        Enum(SubtipoPrevisao, name="subtipo_previsao", schema="conecta",
             values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        index=True
    )

    # Entidade relacionada
    entidade_tipo = Column(
        Enum(TipoEntidadePrevisao, name="tipo_entidade_previsao", schema="conecta",
             values_callable=lambda obj: [e.value for e in obj]),
        nullable=False
    )
    entidade_id = Column(UUID(as_uuid=True), nullable=True)
    entidade_nome = Column(String(255), nullable=True)  # Nome para exibicao

    # Analise de probabilidade
    probabilidade = Column(Float, nullable=False)  # 0.0 a 1.0
    confianca = Column(Float, nullable=False, default=0.5)  # Nivel de confianca
    horizonte_dias = Column(Integer, nullable=False)  # Em quantos dias pode ocorrer

    # Sinais detectados
    sinais = Column(JSONB, default=list)  # Lista de sinais que levaram a previsao
    dados_entrada = Column(JSONB, default=dict)  # Dados usados na analise

    # Acao recomendada
    acao_recomendada = Column(Text, nullable=False)
    acao_url = Column(String(500), nullable=True)  # Link para executar acao
    acao_params = Column(JSONB, default=dict)  # Parametros pre-preenchidos

    # Resultado da acao
    acao_tomada = Column(Boolean, default=False)
    acao_tomada_em = Column(DateTime, nullable=True)
    acao_tomada_por = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True)
    acao_resultado = Column(String(500), nullable=True)

    # Status e validacao
    status = Column(
        Enum(StatusPrevisao, name="status_previsao", schema="conecta",
             values_callable=lambda obj: [e.value for e in obj]),
        default=StatusPrevisao.PENDENTE,
        nullable=False,
        index=True
    )
    validada_em = Column(DateTime, nullable=True)
    validada_por = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True)
    motivo_validacao = Column(String(500), nullable=True)

    # Impacto (para metricas)
    impacto_estimado = Column(String(255), nullable=True)  # Ex: "R$ 5.000 em inadimplencia"
    impacto_real = Column(String(255), nullable=True)  # Apos validacao

    # Relacionamentos
    condominio_id = Column(
        UUID(as_uuid=True),
        ForeignKey("condominios.id"),
        nullable=False,
        index=True
    )

    # Modelo que gerou a previsao (para aprendizado)
    modelo_versao = Column(String(50), nullable=True)
    modelo_score = Column(Float, nullable=True)  # Score interno do modelo

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)  # Quando a previsao expira

    def __repr__(self):
        return f"<Previsao {self.tipo.value}/{self.subtipo.value} prob={self.probabilidade:.0%}>"

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionario"""
        return {
            "id": str(self.id),
            "tipo": self.tipo.value,
            "subtipo": self.subtipo.value,
            "entidade_tipo": self.entidade_tipo.value,
            "entidade_id": str(self.entidade_id) if self.entidade_id else None,
            "entidade_nome": self.entidade_nome,
            "probabilidade": self.probabilidade,
            "confianca": self.confianca,
            "horizonte_dias": self.horizonte_dias,
            "sinais": self.sinais,
            "acao_recomendada": self.acao_recomendada,
            "acao_url": self.acao_url,
            "status": self.status.value,
            "impacto_estimado": self.impacto_estimado,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }

    @property
    def is_expired(self) -> bool:
        """Verifica se a previsao expirou"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at

    @property
    def probabilidade_percentual(self) -> str:
        """Retorna probabilidade formatada"""
        return f"{self.probabilidade * 100:.0f}%"

    @property
    def nivel_risco(self) -> str:
        """Classifica nivel de risco baseado na probabilidade"""
        if self.probabilidade >= 0.8:
            return "critico"
        elif self.probabilidade >= 0.6:
            return "alto"
        elif self.probabilidade >= 0.4:
            return "medio"
        else:
            return "baixo"
