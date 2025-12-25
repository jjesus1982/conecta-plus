"""
Conecta Plus - Modelo de Ocorrencia
Sistema de gerenciamento de ocorrencias com SLA, timeline e avaliacao
"""

import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from ..database import Base


class TipoOcorrencia(str, PyEnum):
    BARULHO = "barulho"
    MANUTENCAO = "manutencao"
    SEGURANCA = "seguranca"
    LIMPEZA = "limpeza"
    ESTACIONAMENTO = "estacionamento"
    ANIMAIS = "animais"
    OBRAS = "obras"
    VAZAMENTO = "vazamento"
    AREA_COMUM = "area_comum"
    OUTROS = "outros"


class StatusOcorrencia(str, PyEnum):
    ABERTA = "aberta"
    EM_ANALISE = "em_analise"
    EM_ANDAMENTO = "em_andamento"
    AGUARDANDO = "aguardando"
    RESOLVIDA = "resolvida"
    CANCELADA = "cancelada"


class OrigemPrazo(str, PyEnum):
    """Origem do calculo do prazo estimado."""
    SLA = "sla"
    MANUAL = "manual"
    IA = "ia"


class Ocorrencia(Base):
    __tablename__ = "ocorrencias"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    condominio_id = Column(UUID(as_uuid=True), ForeignKey("condominios.id"), nullable=False)

    titulo = Column(String(255), nullable=False)
    descricao = Column(Text)
    tipo = Column(String(50))
    prioridade = Column(String(20), default="media")
    status = Column(String(50), default="aberta")

    # Quem reportou
    reportado_por = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"))
    reportador = relationship("Usuario", back_populates="ocorrencias_criadas", foreign_keys=[reportado_por])

    # Unidade
    unidade_id = Column(UUID(as_uuid=True), ForeignKey("unidades.id"))
    unidade = relationship("Unidade", back_populates="ocorrencias")

    # Responsavel pelo atendimento
    responsavel_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"))
    responsavel = relationship("Usuario", foreign_keys=[responsavel_id])

    # Anexos
    anexos = Column(JSONB, default=[])

    # ============ NOVOS CAMPOS Q1 ============

    # SLA e Prazo (RF-02)
    prazo_estimado = Column(DateTime, index=True)
    prazo_origem = Column(String(20), default="sla")  # sla, manual, ia
    sla_config_id = Column(UUID(as_uuid=True), ForeignKey("sla_configs.id"))
    sla_notificado_amarelo = Column(Boolean, default=False)
    sla_notificado_vermelho = Column(Boolean, default=False)
    sla_estourado = Column(Boolean, default=False, index=True)

    # Timeline de eventos (RF-02)
    timeline = Column(JSONB, default=[])
    # Formato: [{"timestamp": "...", "evento": "status_changed", "de": "aberta", "para": "em_analise", "usuario": "...", "descricao": "..."}]

    # Avaliacao pos-resolucao (RF-02)
    avaliacao_nota = Column(Integer)  # 1-5 estrelas
    avaliacao_comentario = Column(Text)
    avaliacao_data = Column(DateTime)
    avaliacao_solicitada = Column(Boolean, default=False)

    # Notificacoes enviadas (RF-02)
    notificacoes_enviadas = Column(JSONB, default=[])
    # Formato: [{"tipo": "abertura", "canal": "email", "enviado_em": "...", "sucesso": true}]

    # Primeira resposta (para metricas)
    primeira_resposta_at = Column(DateTime)
    primeira_resposta_por = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"))

    # ============ FIM NOVOS CAMPOS ============

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolvido_at = Column(DateTime)

    def __repr__(self):
        return f"<Ocorrencia {self.titulo}>"

    def adicionar_evento_timeline(
        self,
        evento: str,
        descricao: str,
        usuario_id: str = "system",
        usuario_nome: str = "Sistema",
        dados_extras: dict = None
    ):
        """Adiciona um evento ao timeline da ocorrencia."""
        if self.timeline is None:
            self.timeline = []

        evento_obj = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "evento": evento,
            "descricao": descricao,
            "usuario_id": usuario_id,
            "usuario_nome": usuario_nome
        }

        if dados_extras:
            evento_obj.update(dados_extras)

        self.timeline.append(evento_obj)

    def registrar_mudanca_status(
        self,
        status_anterior: str,
        status_novo: str,
        usuario_id: str,
        usuario_nome: str,
        motivo: str = None
    ):
        """Registra mudanca de status no timeline."""
        self.adicionar_evento_timeline(
            evento="status_changed",
            descricao=f"Status alterado de '{status_anterior}' para '{status_novo}'" + (f": {motivo}" if motivo else ""),
            usuario_id=usuario_id,
            usuario_nome=usuario_nome,
            dados_extras={
                "de": status_anterior,
                "para": status_novo,
                "motivo": motivo
            }
        )

    def registrar_notificacao(
        self,
        tipo: str,
        canal: str,
        sucesso: bool,
        destinatario: str = None,
        erro: str = None
    ):
        """Registra envio de notificacao."""
        if self.notificacoes_enviadas is None:
            self.notificacoes_enviadas = []

        self.notificacoes_enviadas.append({
            "tipo": tipo,
            "canal": canal,
            "enviado_em": datetime.utcnow().isoformat(),
            "sucesso": sucesso,
            "destinatario": destinatario,
            "erro": erro
        })
