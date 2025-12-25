"""
Conecta Plus - Modelo de Tranquilidade
Sistema de estado e recomendacoes por perfil de usuario
"""

import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, String, DateTime, Integer, Float, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from ..database import Base


class EstadoTranquilidade(str, PyEnum):
    """Estados possiveis de tranquilidade."""
    VERDE = "verde"
    AMARELO = "amarelo"
    VERMELHO = "vermelho"


class PerfilUsuario(str, PyEnum):
    """Perfis de usuario para painel de tranquilidade."""
    SINDICO = "sindico"
    PORTEIRO = "porteiro"
    GERENTE = "gerente"
    MORADOR = "morador"
    ADMIN = "admin"


class TranquilidadeSnapshot(Base):
    """Snapshot do estado de tranquilidade por perfil/condominio."""
    __tablename__ = "tranquilidade_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Perfil e contexto
    perfil = Column(String(50), nullable=False, index=True)
    usuario_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"), index=True)
    usuario = relationship("Usuario")

    # Estado geral
    estado = Column(String(20), nullable=False, default="verde")
    score = Column(Float, default=100.0)  # 0-100, quanto maior melhor

    # Mensagem principal
    mensagem_principal = Column(String(255))
    mensagem_secundaria = Column(String(500))

    # Contadores
    alertas_criticos = Column(Integer, default=0)
    alertas_medios = Column(Integer, default=0)
    ocorrencias_abertas = Column(Integer, default=0)
    ocorrencias_sla_proximo = Column(Integer, default=0)
    ocorrencias_sla_estourado = Column(Integer, default=0)
    cameras_offline = Column(Integer, default=0)
    inadimplencia_percentual = Column(Float, default=0.0)

    # Itens "Precisa de voce" (max 3)
    precisa_de_voce = Column(JSONB, default=[])
    # Formato: [{"titulo": "...", "descricao": "...", "urgencia": "alta", "link": "/...", "tipo": "ocorrencia"}]

    # Ja resolvido hoje
    resolvido_hoje = Column(Integer, default=0)

    # Recomendacao
    recomendacao = Column(String(500))
    recomendacao_tipo = Column(String(50))  # "acao", "informativo", "parabens"

    # Saude do condominio (para sindico/gerente)
    saude_condominio = Column(JSONB, default={})
    # Formato: {"inadimplencia": {"valor": 15, "tendencia": "estavel"}, ...}

    # Proximas tarefas (para porteiro)
    proxima_tarefa = Column(JSONB)
    # Formato: {"titulo": "...", "procedimento": ["passo1", "passo2"], "urgencia": "..."}

    # Condominio
    condominio_id = Column(UUID(as_uuid=True), ForeignKey("condominios.id"), nullable=False, index=True)
    condominio = relationship("Condominio", backref="tranquilidade_snapshots")

    calculated_at = Column(DateTime, default=datetime.utcnow, index=True)
    expires_at = Column(DateTime)  # Quando recalcular

    def __repr__(self):
        return f"<TranquilidadeSnapshot {self.perfil} - {self.estado}>"


class RecomendacaoTemplate(Base):
    """Templates de recomendacoes por situacao."""
    __tablename__ = "recomendacao_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Identificacao
    codigo = Column(String(50), unique=True, nullable=False)
    nome = Column(String(100), nullable=False)

    # Condicoes de ativacao
    perfil = Column(String(50))  # null = todos
    condicao = Column(JSONB, nullable=False)
    # Formato: {"campo": "inadimplencia_percentual", "operador": ">", "valor": 20}

    # Prioridade (maior = mais importante)
    prioridade = Column(Integer, default=50)

    # Mensagem
    tipo = Column(String(50), default="informativo")  # acao, informativo, parabens, alerta
    mensagem = Column(String(500), nullable=False)
    mensagem_curta = Column(String(100))
    icone = Column(String(50))
    cor = Column(String(20))

    # Link de acao
    link = Column(String(255))
    link_texto = Column(String(50))

    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<RecomendacaoTemplate {self.codigo}>"


from sqlalchemy import Boolean

# Criterios para calculo de estado
CRITERIOS_ESTADO = {
    EstadoTranquilidade.VERDE: {
        "alertas_criticos": 0,
        "alertas_medios_max": 2,
        "ocorrencias_sla_estourado": 0,
        "cameras_offline_max": 1,
        "inadimplencia_max": 10,
        "mensagem": "Tudo sob controle",
    },
    EstadoTranquilidade.AMARELO: {
        "alertas_criticos_max": 1,
        "alertas_medios_max": 5,
        "ocorrencias_sla_estourado_max": 2,
        "cameras_offline_max": 3,
        "inadimplencia_max": 20,
        "mensagem": "Atencao necessaria",
    },
    EstadoTranquilidade.VERMELHO: {
        "mensagem": "Acao imediata requerida",
    },
}

# Recomendacoes padrao
RECOMENDACOES_PADRAO = [
    {
        "codigo": "TUDO_OK",
        "perfil": None,
        "condicao": {"estado": "verde"},
        "prioridade": 10,
        "tipo": "parabens",
        "mensagem": "Nenhuma acao necessaria agora. Tudo esta sob controle!",
    },
    {
        "codigo": "INADIMPLENCIA_ALTA",
        "perfil": "sindico",
        "condicao": {"inadimplencia_percentual": {">": 15}},
        "prioridade": 80,
        "tipo": "acao",
        "mensagem": "Inadimplencia acima do ideal ({valor}%). Acoes recomendadas disponiveis.",
        "link": "/financeiro/inadimplencia",
    },
    {
        "codigo": "SLA_ESTOURADO",
        "perfil": None,
        "condicao": {"ocorrencias_sla_estourado": {">": 0}},
        "prioridade": 90,
        "tipo": "alerta",
        "mensagem": "{valor} ocorrencia(s) com SLA estourado. Priorize imediatamente!",
        "link": "/ocorrencias?status=sla_estourado",
    },
    {
        "codigo": "CAMERAS_OFFLINE",
        "perfil": None,
        "condicao": {"cameras_offline": {">": 2}},
        "prioridade": 85,
        "tipo": "alerta",
        "mensagem": "{valor} cameras offline. Seguranca comprometida.",
        "link": "/cftv",
    },
]
