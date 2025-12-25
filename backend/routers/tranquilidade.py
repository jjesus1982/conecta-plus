"""
Conecta Plus - Router de Tranquilidade
Endpoints para painel de tranquilidade por perfil
"""

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user
from ..models.usuario import Usuario
from ..services.tranquilidade import TranquilidadeService
from ..services.sla_manager import SLAManagerService

router = APIRouter(prefix="/tranquilidade", tags=["Tranquilidade"])


@router.get("/")
async def get_tranquilidade(
    forcar_recalculo: bool = Query(False, description="Forcar recalculo ignorando cache"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Retorna estado de tranquilidade para o usuario atual.
    Calcula automaticamente baseado no perfil (role) do usuario.
    """
    service = TranquilidadeService(db)

    # Mapeia role para perfil
    perfil_map = {
        "admin": "admin",
        "sindico": "sindico",
        "gerente": "gerente",
        "porteiro": "porteiro",
        "zelador": "porteiro",
        "morador": "morador",
        "funcionario": "porteiro"
    }
    perfil = perfil_map.get(current_user.role, "morador")

    snapshot = await service.get_ou_calcular(
        perfil=perfil,
        usuario_id=current_user.id,
        condominio_id=current_user.condominio_id,
        forcar_recalculo=forcar_recalculo
    )

    return {
        "success": True,
        "data": {
            "estado": snapshot.estado,
            "score": snapshot.score,
            "mensagem_principal": snapshot.mensagem_principal,
            "precisa_de_voce": snapshot.precisa_de_voce,
            "resolvido_hoje": snapshot.resolvido_hoje,
            "recomendacao": {
                "mensagem": snapshot.recomendacao,
                "tipo": snapshot.recomendacao_tipo
            },
            "contadores": {
                "alertas_criticos": snapshot.alertas_criticos,
                "alertas_medios": snapshot.alertas_medios,
                "ocorrencias_abertas": snapshot.ocorrencias_abertas,
                "ocorrencias_sla_proximo": snapshot.ocorrencias_sla_proximo,
                "ocorrencias_sla_estourado": snapshot.ocorrencias_sla_estourado,
                "cameras_offline": snapshot.cameras_offline,
                "inadimplencia_percentual": snapshot.inadimplencia_percentual
            },
            "saude_condominio": snapshot.saude_condominio,
            "proxima_tarefa": snapshot.proxima_tarefa,
            "calculado_em": snapshot.calculated_at.isoformat(),
            "expira_em": snapshot.expires_at.isoformat() if snapshot.expires_at else None
        }
    }


@router.get("/sindico")
async def get_tranquilidade_sindico(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Retorna painel de tranquilidade especifico para sindico.
    Inclui saude do condominio e metricas de gestao.
    """
    if current_user.role not in ["admin", "sindico", "gerente"]:
        raise HTTPException(status_code=403, detail="Acesso restrito a sindicos e gerentes")

    service = TranquilidadeService(db)
    sla_service = SLAManagerService(db)

    # Calcula tranquilidade
    snapshot = await service.get_ou_calcular(
        perfil="sindico",
        usuario_id=current_user.id,
        condominio_id=current_user.condominio_id
    )

    # Busca ocorrencias com SLA critico
    ocorrencias_criticas = await sla_service.get_ocorrencias_sla_critico(
        current_user.condominio_id,
        limite=5
    )

    return {
        "success": True,
        "data": {
            "tranquilidade": {
                "estado": snapshot.estado,
                "score": snapshot.score,
                "mensagem": snapshot.mensagem_principal
            },
            "precisa_de_voce": snapshot.precisa_de_voce,
            "saude_condominio": snapshot.saude_condominio,
            "recomendacao": {
                "mensagem": snapshot.recomendacao,
                "tipo": snapshot.recomendacao_tipo
            },
            "ocorrencias_criticas": ocorrencias_criticas,
            "resolvido_hoje": snapshot.resolvido_hoje
        }
    }


@router.get("/porteiro")
async def get_tranquilidade_porteiro(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Retorna painel de tranquilidade especifico para porteiro.
    Foco em tarefas imediatas e procedimentos.
    """
    if current_user.role not in ["admin", "porteiro", "zelador", "gerente"]:
        raise HTTPException(status_code=403, detail="Acesso restrito")

    service = TranquilidadeService(db)

    snapshot = await service.get_ou_calcular(
        perfil="porteiro",
        usuario_id=current_user.id,
        condominio_id=current_user.condominio_id
    )

    return {
        "success": True,
        "data": {
            "situacao": {
                "estado": snapshot.estado,
                "mensagem": snapshot.mensagem_principal
            },
            "proxima_tarefa": snapshot.proxima_tarefa,
            "precisa_de_voce": snapshot.precisa_de_voce[:2],  # Max 2 para porteiro
            "botao_duvida": {
                "texto": "Estou em duvida",
                "link": "/suporte",
                "descricao": "Acione o suporte se precisar de ajuda"
            }
        }
    }


@router.get("/morador")
async def get_tranquilidade_morador(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Retorna painel de tranquilidade para morador.
    Foco nas proprias ocorrencias, encomendas e comunicados.
    """
    service = TranquilidadeService(db)

    snapshot = await service.get_ou_calcular(
        perfil="morador",
        usuario_id=current_user.id,
        condominio_id=current_user.condominio_id
    )

    # TODO: Buscar ocorrencias do morador
    # TODO: Buscar encomendas pendentes
    # TODO: Buscar comunicados nao lidos
    # TODO: Buscar proximas reservas

    return {
        "success": True,
        "data": {
            "situacao": {
                "estado": "verde",  # Morador geralmente ve verde
                "mensagem": "Tudo certo com sua unidade"
            },
            "minhas_ocorrencias": [],  # TODO
            "minhas_encomendas": [],  # TODO
            "comunicados_novos": [],  # TODO
            "proximas_reservas": [],  # TODO
            "financeiro": {
                "situacao": "em_dia",
                "proximo_vencimento": None
            }
        }
    }


@router.get("/sla/criticos")
async def get_sla_criticos(
    limite: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Retorna ocorrencias com SLA critico (proximo ou estourado).
    """
    if current_user.role not in ["admin", "sindico", "gerente"]:
        raise HTTPException(status_code=403, detail="Acesso restrito")

    service = SLAManagerService(db)

    ocorrencias = await service.get_ocorrencias_sla_critico(
        current_user.condominio_id,
        limite=limite
    )

    return {
        "success": True,
        "data": {
            "total": len(ocorrencias),
            "items": ocorrencias
        }
    }
