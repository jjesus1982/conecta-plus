"""
Conecta Plus - Modelo de Configuracao de SLA
Sistema de gerenciamento de prazos e niveis de servico
"""

import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, String, DateTime, Integer, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from ..database import Base


class TipoEntidade(str, PyEnum):
    """Tipos de entidades que podem ter SLA configurado."""
    OCORRENCIA = "ocorrencia"
    ALERTA = "alerta"
    MANUTENCAO = "manutencao"
    CHAMADO = "chamado"


class PrioridadeSLA(str, PyEnum):
    """Niveis de prioridade para SLA."""
    BAIXA = "baixa"
    MEDIA = "media"
    ALTA = "alta"
    URGENTE = "urgente"
    CRITICA = "critica"


class SLAConfig(Base):
    """Configuracao de SLA por tipo e prioridade."""
    __tablename__ = "sla_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Identificacao
    nome = Column(String(100), nullable=False)
    descricao = Column(String(500))

    # Tipo de entidade (ocorrencia, alerta, manutencao)
    tipo_entidade = Column(String(50), nullable=False, index=True)

    # Subtipo especifico (barulho, vazamento, seguranca, etc)
    subtipo = Column(String(50), index=True)

    # Prioridade
    prioridade = Column(String(20), default="media")

    # Prazos em minutos
    prazo_primeira_resposta = Column(Integer, default=60)  # Tempo para primeiro contato
    prazo_resolucao = Column(Integer, default=1440)  # Tempo para resolver (default 24h)
    prazo_alerta_amarelo = Column(Integer)  # Quando alertar que esta proximo
    prazo_alerta_vermelho = Column(Integer)  # Quando escalar

    # Escalacao automatica
    escalar_automaticamente = Column(Boolean, default=True)
    escalar_para = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"))
    escalar_usuario = relationship("Usuario")

    # Notificacoes
    notificar_solicitante = Column(Boolean, default=True)
    notificar_responsavel = Column(Boolean, default=True)
    notificar_gestor = Column(Boolean, default=False)

    # Templates de notificacao
    template_abertura = Column(String(500), default="Recebemos sua solicitacao #{numero}. Prazo estimado: {prazo}.")
    template_atualizacao = Column(String(500), default="Sua solicitacao #{numero} foi atualizada: {status}.")
    template_resolucao = Column(String(500), default="Sua solicitacao #{numero} foi resolvida. Avalie nosso atendimento!")
    template_sla_proximo = Column(String(500), default="Atencao: Solicitacao #{numero} com prazo em {tempo_restante}.")
    template_sla_estourado = Column(String(500), default="URGENTE: SLA estourado na solicitacao #{numero}!")

    # Condominio (null = regra global)
    condominio_id = Column(UUID(as_uuid=True), ForeignKey("condominios.id"))
    condominio = relationship("Condominio", backref="sla_configs")

    # Ativo
    ativo = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<SLAConfig {self.nome} - {self.tipo_entidade}/{self.subtipo}>"

    def get_prazo_minutos(self) -> int:
        """Retorna o prazo de resolucao em minutos."""
        return self.prazo_resolucao or 1440

    def get_prazo_horas(self) -> float:
        """Retorna o prazo de resolucao em horas."""
        return self.get_prazo_minutos() / 60

    def get_prazo_formatado(self) -> str:
        """Retorna o prazo formatado para exibicao."""
        minutos = self.get_prazo_minutos()
        if minutos < 60:
            return f"{minutos} minutos"
        elif minutos < 1440:
            horas = minutos / 60
            return f"{horas:.0f}h" if horas == int(horas) else f"{horas:.1f}h"
        else:
            dias = minutos / 1440
            return f"{dias:.0f} dia(s)" if dias == int(dias) else f"{dias:.1f} dia(s)"


# Configuracoes padrao de SLA
SLA_DEFAULTS = {
    "ocorrencia": {
        "seguranca": {"baixa": 240, "media": 120, "alta": 60, "urgente": 30, "critica": 15},
        "vazamento": {"baixa": 480, "media": 240, "alta": 120, "urgente": 60, "critica": 30},
        "manutencao": {"baixa": 2880, "media": 1440, "alta": 480, "urgente": 240, "critica": 60},
        "barulho": {"baixa": 1440, "media": 720, "alta": 240, "urgente": 60, "critica": 30},
        "limpeza": {"baixa": 1440, "media": 720, "alta": 240, "urgente": 120, "critica": 60},
        "default": {"baixa": 2880, "media": 1440, "alta": 720, "urgente": 240, "critica": 60},
    },
    "alerta": {
        "intrusion": {"low": 30, "medium": 15, "high": 5, "critical": 1},
        "motion": {"low": 60, "medium": 30, "high": 15, "critical": 5},
        "access": {"low": 30, "medium": 15, "high": 5, "critical": 1},
        "fire": {"low": 5, "medium": 3, "high": 1, "critical": 1},
        "panic": {"low": 5, "medium": 3, "high": 1, "critical": 1},
        "equipment": {"low": 240, "medium": 120, "high": 60, "critical": 15},
        "default": {"low": 60, "medium": 30, "high": 15, "critical": 5},
    }
}
