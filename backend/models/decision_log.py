"""
Conecta Plus - Modelo de Registro de Decisoes
Sistema unificado de auditoria para todas as decisoes do sistema
"""

import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import relationship

from ..database import Base


class ModuloSistema(str, PyEnum):
    """Modulos do sistema que registram decisoes."""
    ACESSO = "acesso"
    PORTARIA = "portaria"
    SEGURANCA = "seguranca"
    FINANCEIRO = "financeiro"
    OCORRENCIAS = "ocorrencias"
    MANUTENCAO = "manutencao"
    RESERVAS = "reservas"
    COMUNICADOS = "comunicados"
    ASSEMBLEIAS = "assembleias"
    ADMIN = "admin"


class TipoDecisao(str, PyEnum):
    """Tipos de decisoes que podem ser registradas."""
    # Acesso
    ACESSO_LIBERADO = "acesso_liberado"
    ACESSO_NEGADO = "acesso_negado"
    VISITANTE_AUTORIZADO = "visitante_autorizado"
    VISITANTE_NEGADO = "visitante_negado"

    # Financeiro
    PAGAMENTO_APROVADO = "pagamento_aprovado"
    PAGAMENTO_REJEITADO = "pagamento_rejeitado"
    BOLETO_CANCELADO = "boleto_cancelado"
    DESCONTO_APLICADO = "desconto_aplicado"
    MULTA_APLICADA = "multa_aplicada"

    # Ocorrencias
    OCORRENCIA_ATRIBUIDA = "ocorrencia_atribuida"
    OCORRENCIA_ESCALADA = "ocorrencia_escalada"
    OCORRENCIA_RESOLVIDA = "ocorrencia_resolvida"
    OCORRENCIA_CANCELADA = "ocorrencia_cancelada"

    # Seguranca
    ALERTA_RECONHECIDO = "alerta_reconhecido"
    ALERTA_DESCARTADO = "alerta_descartado"
    INCIDENTE_CRIADO = "incidente_criado"
    INCIDENTE_RESOLVIDO = "incidente_resolvido"
    ALARME_ACIONADO = "alarme_acionado"
    SEGURANCA_DESPACHADA = "seguranca_despachada"

    # Admin
    USUARIO_CRIADO = "usuario_criado"
    USUARIO_BLOQUEADO = "usuario_bloqueado"
    PERMISSAO_ALTERADA = "permissao_alterada"
    CONFIG_ALTERADA = "config_alterada"


class NivelCriticidade(str, PyEnum):
    """Nivel de criticidade da decisao."""
    BAIXO = "baixo"
    MEDIO = "medio"
    ALTO = "alto"
    CRITICO = "critico"


class DecisionLog(Base):
    """Registro unificado de decisoes do sistema."""
    __tablename__ = "decision_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Modulo e tipo
    modulo = Column(String(50), nullable=False, index=True)
    tipo_decisao = Column(String(50), nullable=False, index=True)
    criticidade = Column(String(20), default="medio")

    # Entidade afetada
    entidade_tipo = Column(String(50))  # "ocorrencia", "visitante", "boleto", etc
    entidade_id = Column(UUID(as_uuid=True), index=True)
    entidade_descricao = Column(String(255))  # Descricao legivel

    # Descricao da decisao
    titulo = Column(String(255), nullable=False)
    descricao = Column(Text)
    justificativa = Column(Text)  # Motivo da decisao (obrigatorio em criticas)

    # Regra aplicada
    regra_sistema = Column(String(100))  # Nome da regra automatica, se houver
    regra_descricao = Column(String(500))  # Descricao da regra

    # Usuario que tomou a decisao
    usuario_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"), index=True)
    usuario = relationship("Usuario")
    usuario_nome = Column(String(100))
    usuario_role = Column(String(50))

    # Contexto tecnico
    ip_address = Column(INET)
    user_agent = Column(String(500))
    session_id = Column(String(100))

    # Protecao exibida
    protecao_exibida = Column(Boolean, default=False)
    mensagem_protecao = Column(String(255))

    # Resultado
    sucesso = Column(Boolean, default=True)
    resultado = Column(Text)
    erro = Column(Text)

    # Dados adicionais
    dados_antes = Column(JSONB)  # Estado antes da decisao
    dados_depois = Column(JSONB)  # Estado depois da decisao
    meta_dados = Column("metadata", JSONB, default={})  # Renomeado para evitar conflito SQLAlchemy

    # Condominio
    condominio_id = Column(UUID(as_uuid=True), ForeignKey("condominios.id"), index=True)
    condominio = relationship("Condominio", backref="decision_logs")

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<DecisionLog {self.modulo}/{self.tipo_decisao} por {self.usuario_nome}>"


# Mensagens de protecao por tipo de usuario
MENSAGENS_PROTECAO = {
    "porteiro": "Decisao registrada. Voce esta protegido.",
    "sindico": "Acao documentada com data e hora.",
    "gerente": "Registro auditavel criado com sucesso.",
    "admin": "Log de auditoria gerado.",
    "operador": "Voce seguiu o procedimento correto.",
    "default": "Decisao registrada no sistema."
}

# Decisoes que requerem justificativa obrigatoria
DECISOES_CRITICAS = [
    TipoDecisao.ACESSO_NEGADO,
    TipoDecisao.VISITANTE_NEGADO,
    TipoDecisao.PAGAMENTO_REJEITADO,
    TipoDecisao.BOLETO_CANCELADO,
    TipoDecisao.DESCONTO_APLICADO,
    TipoDecisao.OCORRENCIA_CANCELADA,
    TipoDecisao.ALERTA_DESCARTADO,
    TipoDecisao.USUARIO_BLOQUEADO,
]
