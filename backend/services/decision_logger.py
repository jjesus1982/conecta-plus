"""
Conecta Plus - Servico de Registro de Decisoes
Registra automaticamente todas as decisoes do sistema para auditoria
"""

from datetime import datetime
from typing import Optional, Dict, Any, Callable
from uuid import UUID
from functools import wraps
import logging

from sqlalchemy.orm import Session
from fastapi import Request

from ..models.decision_log import (
    DecisionLog,
    ModuloSistema,
    TipoDecisao,
    NivelCriticidade,
    MENSAGENS_PROTECAO,
    DECISOES_CRITICAS
)

logger = logging.getLogger(__name__)


class DecisionLoggerService:
    """Servico para registro unificado de decisoes."""

    def __init__(self, db: Session):
        self.db = db

    async def registrar_decisao(
        self,
        modulo: str,
        tipo_decisao: str,
        titulo: str,
        usuario_id: UUID,
        usuario_nome: str,
        usuario_role: str,
        condominio_id: UUID,
        entidade_tipo: Optional[str] = None,
        entidade_id: Optional[UUID] = None,
        entidade_descricao: Optional[str] = None,
        descricao: Optional[str] = None,
        justificativa: Optional[str] = None,
        regra_sistema: Optional[str] = None,
        regra_descricao: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None,
        dados_antes: Optional[Dict] = None,
        dados_depois: Optional[Dict] = None,
        metadata: Optional[Dict] = None,
        sucesso: bool = True,
        resultado: Optional[str] = None,
        erro: Optional[str] = None,
        exibir_protecao: bool = True
    ) -> DecisionLog:
        """
        Registra uma decisao no sistema.
        Retorna o log criado e a mensagem de protecao se aplicavel.
        """
        # Determina criticidade
        criticidade = self._calcular_criticidade(tipo_decisao, modulo)

        # Verifica se precisa justificativa
        requer_justificativa = tipo_decisao in [t.value for t in DECISOES_CRITICAS]
        if requer_justificativa and not justificativa:
            logger.warning(
                "decisao_critica_sem_justificativa",
                modulo=modulo,
                tipo=tipo_decisao,
                usuario=usuario_nome
            )

        # Determina mensagem de protecao
        mensagem_protecao = None
        if exibir_protecao:
            mensagem_protecao = MENSAGENS_PROTECAO.get(
                usuario_role,
                MENSAGENS_PROTECAO["default"]
            )

        # Cria o registro
        log = DecisionLog(
            modulo=modulo,
            tipo_decisao=tipo_decisao,
            criticidade=criticidade,
            titulo=titulo,
            descricao=descricao,
            justificativa=justificativa,
            entidade_tipo=entidade_tipo,
            entidade_id=entidade_id,
            entidade_descricao=entidade_descricao,
            regra_sistema=regra_sistema,
            regra_descricao=regra_descricao,
            usuario_id=usuario_id,
            usuario_nome=usuario_nome,
            usuario_role=usuario_role,
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id,
            protecao_exibida=exibir_protecao,
            mensagem_protecao=mensagem_protecao,
            sucesso=sucesso,
            resultado=resultado,
            erro=erro,
            dados_antes=dados_antes,
            dados_depois=dados_depois,
            metadata=metadata or {},
            condominio_id=condominio_id
        )

        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)

        logger.info(
            "decisao_registrada",
            log_id=str(log.id),
            modulo=modulo,
            tipo=tipo_decisao,
            usuario=usuario_nome,
            sucesso=sucesso
        )

        return log

    def _calcular_criticidade(self, tipo_decisao: str, modulo: str) -> str:
        """Calcula nivel de criticidade da decisao."""
        criticos = [
            TipoDecisao.USUARIO_BLOQUEADO.value,
            TipoDecisao.ALARME_ACIONADO.value,
            TipoDecisao.SEGURANCA_DESPACHADA.value,
            TipoDecisao.INCIDENTE_CRIADO.value,
        ]

        altos = [
            TipoDecisao.ACESSO_NEGADO.value,
            TipoDecisao.VISITANTE_NEGADO.value,
            TipoDecisao.PAGAMENTO_REJEITADO.value,
            TipoDecisao.BOLETO_CANCELADO.value,
            TipoDecisao.PERMISSAO_ALTERADA.value,
        ]

        medios = [
            TipoDecisao.OCORRENCIA_ESCALADA.value,
            TipoDecisao.ALERTA_DESCARTADO.value,
            TipoDecisao.DESCONTO_APLICADO.value,
            TipoDecisao.CONFIG_ALTERADA.value,
        ]

        if tipo_decisao in criticos:
            return NivelCriticidade.CRITICO.value
        elif tipo_decisao in altos:
            return NivelCriticidade.ALTO.value
        elif tipo_decisao in medios:
            return NivelCriticidade.MEDIO.value
        else:
            return NivelCriticidade.BAIXO.value

    async def buscar_decisoes(
        self,
        condominio_id: UUID,
        modulo: Optional[str] = None,
        tipo_decisao: Optional[str] = None,
        usuario_id: Optional[UUID] = None,
        entidade_id: Optional[UUID] = None,
        data_inicio: Optional[datetime] = None,
        data_fim: Optional[datetime] = None,
        criticidade: Optional[str] = None,
        limite: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Busca decisoes com filtros."""
        query = self.db.query(DecisionLog).filter(
            DecisionLog.condominio_id == condominio_id
        )

        if modulo:
            query = query.filter(DecisionLog.modulo == modulo)
        if tipo_decisao:
            query = query.filter(DecisionLog.tipo_decisao == tipo_decisao)
        if usuario_id:
            query = query.filter(DecisionLog.usuario_id == usuario_id)
        if entidade_id:
            query = query.filter(DecisionLog.entidade_id == entidade_id)
        if data_inicio:
            query = query.filter(DecisionLog.created_at >= data_inicio)
        if data_fim:
            query = query.filter(DecisionLog.created_at <= data_fim)
        if criticidade:
            query = query.filter(DecisionLog.criticidade == criticidade)

        total = query.count()
        decisoes = query.order_by(
            DecisionLog.created_at.desc()
        ).offset(offset).limit(limite).all()

        return {
            "total": total,
            "items": decisoes,
            "limite": limite,
            "offset": offset
        }

    async def get_timeline_entidade(
        self,
        entidade_tipo: str,
        entidade_id: UUID
    ) -> list:
        """Retorna timeline de decisoes de uma entidade."""
        decisoes = self.db.query(DecisionLog).filter(
            DecisionLog.entidade_tipo == entidade_tipo,
            DecisionLog.entidade_id == entidade_id
        ).order_by(DecisionLog.created_at.asc()).all()

        return [
            {
                "id": str(d.id),
                "timestamp": d.created_at.isoformat(),
                "tipo": d.tipo_decisao,
                "titulo": d.titulo,
                "descricao": d.descricao,
                "usuario": d.usuario_nome,
                "sucesso": d.sucesso
            }
            for d in decisoes
        ]


def log_decision(
    modulo: str,
    tipo_decisao: str,
    titulo_template: str = "{action}",
    exibir_protecao: bool = True
):
    """
    Decorator para registrar decisoes automaticamente em endpoints.

    Uso:
        @log_decision("acesso", "acesso_liberado", "Acesso liberado para {pessoa}")
        async def liberar_acesso(...):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extrai request e db dos argumentos
            request = kwargs.get("request")
            db = kwargs.get("db")
            current_user = kwargs.get("current_user")

            # Executa a funcao original
            resultado = await func(*args, **kwargs)

            # Tenta registrar a decisao
            if db and current_user:
                try:
                    service = DecisionLoggerService(db)
                    await service.registrar_decisao(
                        modulo=modulo,
                        tipo_decisao=tipo_decisao,
                        titulo=titulo_template,
                        usuario_id=current_user.id,
                        usuario_nome=current_user.nome,
                        usuario_role=current_user.role,
                        condominio_id=current_user.condominio_id,
                        ip_address=request.client.host if request else None,
                        user_agent=request.headers.get("user-agent") if request else None,
                        exibir_protecao=exibir_protecao,
                        sucesso=True
                    )
                except Exception as e:
                    logger.error("erro_registrar_decisao", error=str(e))

            return resultado
        return wrapper
    return decorator
