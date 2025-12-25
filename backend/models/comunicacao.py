"""
Conecta Plus - Q2: Modelos de Comunicacao Inteligente
RF-07: Comunicacao Inteligente
"""

import enum
from datetime import datetime, time
from typing import Optional, Dict, Any, List
from uuid import uuid4

from sqlalchemy import (
    Column, String, DateTime, Integer, Float, Boolean,
    ForeignKey, Text, Enum, Time
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship

from ..database import Base


class CanalComunicacao(str, enum.Enum):
    """Canais de comunicacao disponiveis"""
    PUSH = "push"
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    SMS = "sms"
    IN_APP = "in_app"


class TipoComunicacao(str, enum.Enum):
    """Tipos de comunicacao"""
    ALERTA = "alerta"
    COMUNICADO = "comunicado"
    LEMBRETE = "lembrete"
    SUGESTAO = "sugestao"
    NOTIFICACAO = "notificacao"
    BOLETIM = "boletim"


class UrgenciaComunicacao(str, enum.Enum):
    """Nivel de urgencia"""
    CRITICA = "critica"
    ALTA = "alta"
    MEDIA = "media"
    BAIXA = "baixa"


class PreferenciaComunicacao(Base):
    """
    Preferencias de comunicacao do usuario.
    Armazena configuracoes e dados aprendidos sobre o comportamento do usuario.
    """
    __tablename__ = "preferencias_comunicacao"
    __table_args__ = {"schema": "conecta"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    usuario_id = Column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id"),
        unique=True,
        nullable=False,
        index=True
    )

    # Horarios preferidos (aprendido automaticamente ou configurado)
    horario_preferido_inicio = Column(Time, default=time(8, 0))
    horario_preferido_fim = Column(Time, default=time(21, 0))
    dias_preferidos = Column(ARRAY(Integer), default=[1, 2, 3, 4, 5])  # 1=Seg, 7=Dom
    fuso_horario = Column(String(50), default="America/Sao_Paulo")

    # Canais preferidos
    canal_primario = Column(
        Enum(CanalComunicacao, name="canal_comunicacao", schema="conecta",
             values_callable=lambda obj: [e.value for e in obj]),
        default=CanalComunicacao.PUSH
    )
    canal_secundario = Column(
        Enum(CanalComunicacao, name="canal_comunicacao_sec", schema="conecta",
             create_type=False, values_callable=lambda obj: [e.value for e in obj]),
        default=CanalComunicacao.EMAIL,
        nullable=True
    )
    canal_emergencia = Column(
        Enum(CanalComunicacao, name="canal_comunicacao_emerg", schema="conecta",
             create_type=False, values_callable=lambda obj: [e.value for e in obj]),
        default=CanalComunicacao.SMS,
        nullable=True
    )

    # Contatos para cada canal
    email = Column(String(255), nullable=True)
    telefone_whatsapp = Column(String(20), nullable=True)
    telefone_sms = Column(String(20), nullable=True)
    push_token = Column(String(500), nullable=True)

    # Frequencia
    max_notificacoes_dia = Column(Integer, default=5)
    agrupar_similares = Column(Boolean, default=True)
    intervalo_minimo_minutos = Column(Integer, default=30)  # Entre notificacoes

    # Categorias (opt-in/opt-out)
    receber_financeiro = Column(Boolean, default=True)
    receber_manutencao = Column(Boolean, default=True)
    receber_seguranca = Column(Boolean, default=True)
    receber_comunicados = Column(Boolean, default=True)
    receber_assembleias = Column(Boolean, default=True)
    receber_reservas = Column(Boolean, default=True)
    receber_sugestoes = Column(Boolean, default=True)
    receber_marketing = Column(Boolean, default=False)

    # Modo nao perturbe
    nao_perturbe_ativo = Column(Boolean, default=False)
    nao_perturbe_inicio = Column(Time, default=time(22, 0))
    nao_perturbe_fim = Column(Time, default=time(7, 0))
    nao_perturbe_exceto_emergencias = Column(Boolean, default=True)

    # Metricas aprendidas (atualizadas pelo sistema)
    taxa_abertura_push = Column(Float, default=0.0)
    taxa_abertura_email = Column(Float, default=0.0)
    taxa_abertura_whatsapp = Column(Float, default=0.0)
    tempo_medio_resposta_segundos = Column(Integer, default=0)
    horario_mais_engajado = Column(Time, nullable=True)
    dia_mais_engajado = Column(Integer, nullable=True)  # 1-7

    # Contadores para calcular metricas
    total_enviadas = Column(Integer, default=0)
    total_abertas = Column(Integer, default=0)
    total_clicadas = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<PreferenciaComunicacao usuario={self.usuario_id}>"

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionario"""
        return {
            "id": str(self.id),
            "usuario_id": str(self.usuario_id),
            "horario_preferido_inicio": self.horario_preferido_inicio.isoformat() if self.horario_preferido_inicio else None,
            "horario_preferido_fim": self.horario_preferido_fim.isoformat() if self.horario_preferido_fim else None,
            "dias_preferidos": self.dias_preferidos,
            "canal_primario": self.canal_primario.value if self.canal_primario else None,
            "canal_secundario": self.canal_secundario.value if self.canal_secundario else None,
            "max_notificacoes_dia": self.max_notificacoes_dia,
            "agrupar_similares": self.agrupar_similares,
            "categorias": {
                "financeiro": self.receber_financeiro,
                "manutencao": self.receber_manutencao,
                "seguranca": self.receber_seguranca,
                "comunicados": self.receber_comunicados,
                "assembleias": self.receber_assembleias,
                "reservas": self.receber_reservas,
                "sugestoes": self.receber_sugestoes,
            },
            "metricas": {
                "taxa_abertura_push": self.taxa_abertura_push,
                "taxa_abertura_email": self.taxa_abertura_email,
                "tempo_medio_resposta": self.tempo_medio_resposta_segundos,
            }
        }

    def melhor_canal_para(self, urgencia: UrgenciaComunicacao) -> CanalComunicacao:
        """Determina o melhor canal baseado na urgencia"""
        if urgencia == UrgenciaComunicacao.CRITICA:
            return self.canal_emergencia or CanalComunicacao.SMS
        elif urgencia == UrgenciaComunicacao.ALTA:
            return self.canal_primario
        else:
            # Para urgencia media/baixa, usar canal com melhor taxa
            if self.taxa_abertura_email > self.taxa_abertura_push:
                return CanalComunicacao.EMAIL
            return self.canal_primario

    def pode_notificar_agora(self, urgencia: UrgenciaComunicacao = UrgenciaComunicacao.MEDIA) -> bool:
        """Verifica se pode enviar notificacao no momento atual"""
        agora = datetime.now().time()

        # Emergencias sempre podem ser enviadas (se configurado)
        if urgencia == UrgenciaComunicacao.CRITICA:
            if self.nao_perturbe_ativo and self.nao_perturbe_exceto_emergencias:
                return True

        # Verifica modo nao perturbe
        if self.nao_perturbe_ativo:
            if self.nao_perturbe_inicio <= agora or agora <= self.nao_perturbe_fim:
                return False

        # Verifica horario preferido
        if self.horario_preferido_inicio and self.horario_preferido_fim:
            if not (self.horario_preferido_inicio <= agora <= self.horario_preferido_fim):
                return False

        return True


class HistoricoComunicacao(Base):
    """
    Historico de comunicacoes enviadas ao usuario.
    Usado para analise de engajamento e aprendizado.
    """
    __tablename__ = "historico_comunicacao"
    __table_args__ = {"schema": "conecta"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    usuario_id = Column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id"),
        nullable=False,
        index=True
    )

    # Mensagem
    tipo = Column(
        Enum(TipoComunicacao, name="tipo_comunicacao", schema="conecta",
             values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        index=True
    )
    titulo = Column(String(255), nullable=False)
    conteudo_resumo = Column(String(1000), nullable=True)
    conteudo_completo = Column(Text, nullable=True)

    # Urgencia
    urgencia = Column(
        Enum(UrgenciaComunicacao, name="urgencia_comunicacao", schema="conecta",
             values_callable=lambda obj: [e.value for e in obj]),
        default=UrgenciaComunicacao.MEDIA
    )

    # Canal e envio
    canal = Column(
        Enum(CanalComunicacao, name="canal_hist_comunicacao", schema="conecta",
             create_type=False, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False
    )
    enviado_em = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    horario_otimizado = Column(Boolean, default=False)  # Se usou ML para escolher horario
    canal_otimizado = Column(Boolean, default=False)  # Se usou ML para escolher canal

    # Status de entrega
    entregue = Column(Boolean, default=False)
    entregue_em = Column(DateTime, nullable=True)
    falha_entrega = Column(String(255), nullable=True)

    # Engajamento
    aberto = Column(Boolean, default=False)
    aberto_em = Column(DateTime, nullable=True)
    clicou = Column(Boolean, default=False)
    clicou_em = Column(DateTime, nullable=True)
    respondeu = Column(Boolean, default=False)
    respondeu_em = Column(DateTime, nullable=True)

    # Tempo de resposta (calculado)
    tempo_ate_abertura_segundos = Column(Integer, nullable=True)
    tempo_ate_clique_segundos = Column(Integer, nullable=True)

    # Feedback
    foi_util = Column(Boolean, nullable=True)
    marcou_spam = Column(Boolean, default=False)
    silenciou_tipo = Column(Boolean, default=False)  # Pediu para nao receber mais este tipo

    # Contexto adicional
    origem_id = Column(UUID(as_uuid=True), nullable=True)  # ID da entidade que gerou
    origem_tipo = Column(String(50), nullable=True)  # sugestao, previsao, ocorrencia, etc
    categoria = Column(String(50), nullable=True)  # financeiro, seguranca, etc

    # Relacionamentos
    condominio_id = Column(
        UUID(as_uuid=True),
        ForeignKey("condominios.id"),
        nullable=False,
        index=True
    )

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<HistoricoComunicacao {self.tipo.value} canal={self.canal.value}>"

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionario"""
        return {
            "id": str(self.id),
            "tipo": self.tipo.value,
            "titulo": self.titulo,
            "conteudo_resumo": self.conteudo_resumo,
            "urgencia": self.urgencia.value,
            "canal": self.canal.value,
            "enviado_em": self.enviado_em.isoformat() if self.enviado_em else None,
            "horario_otimizado": self.horario_otimizado,
            "entregue": self.entregue,
            "aberto": self.aberto,
            "aberto_em": self.aberto_em.isoformat() if self.aberto_em else None,
            "clicou": self.clicou,
            "respondeu": self.respondeu,
            "foi_util": self.foi_util,
        }

    def registrar_entrega(self) -> None:
        """Registra que a mensagem foi entregue"""
        self.entregue = True
        self.entregue_em = datetime.utcnow()

    def registrar_abertura(self) -> None:
        """Registra que a mensagem foi aberta"""
        self.aberto = True
        self.aberto_em = datetime.utcnow()
        if self.enviado_em:
            delta = self.aberto_em - self.enviado_em
            self.tempo_ate_abertura_segundos = int(delta.total_seconds())

    def registrar_clique(self) -> None:
        """Registra que houve clique na mensagem"""
        self.clicou = True
        self.clicou_em = datetime.utcnow()
        if self.enviado_em:
            delta = self.clicou_em - self.enviado_em
            self.tempo_ate_clique_segundos = int(delta.total_seconds())

    def registrar_resposta(self) -> None:
        """Registra que houve resposta a mensagem"""
        self.respondeu = True
        self.respondeu_em = datetime.utcnow()


class FilaComunicacao(Base):
    """
    Fila de comunicacoes pendentes de envio.
    Permite agendar envios e otimizar timing.
    """
    __tablename__ = "fila_comunicacao"
    __table_args__ = {"schema": "conecta"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    usuario_id = Column(
        UUID(as_uuid=True),
        ForeignKey("usuarios.id"),
        nullable=False,
        index=True
    )

    # Mensagem
    tipo = Column(
        Enum(TipoComunicacao, name="tipo_fila_comunicacao", schema="conecta",
             create_type=False, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False
    )
    titulo = Column(String(255), nullable=False)
    conteudo = Column(Text, nullable=False)
    urgencia = Column(
        Enum(UrgenciaComunicacao, name="urgencia_fila", schema="conecta",
             create_type=False, values_callable=lambda obj: [e.value for e in obj]),
        default=UrgenciaComunicacao.MEDIA
    )

    # Canal
    canal = Column(
        Enum(CanalComunicacao, name="canal_fila_comunicacao", schema="conecta",
             create_type=False, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False
    )

    # Agendamento
    agendar_para = Column(DateTime, nullable=True)  # Se None, enviar assim que possivel
    prioridade = Column(Integer, default=50)  # 1-100

    # Agrupamento
    pode_agrupar = Column(Boolean, default=True)
    grupo_id = Column(UUID(as_uuid=True), nullable=True)  # Para agrupar mensagens similares

    # Status
    processado = Column(Boolean, default=False)
    processado_em = Column(DateTime, nullable=True)
    historico_id = Column(UUID(as_uuid=True), ForeignKey("historico_comunicacao.id"), nullable=True)
    erro = Column(String(500), nullable=True)

    # Contexto
    origem_id = Column(UUID(as_uuid=True), nullable=True)
    origem_tipo = Column(String(50), nullable=True)
    categoria = Column(String(50), nullable=True)

    # Relacionamentos
    condominio_id = Column(
        UUID(as_uuid=True),
        ForeignKey("condominios.id"),
        nullable=False,
        index=True
    )

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<FilaComunicacao {self.tipo.value} para={self.usuario_id}>"
