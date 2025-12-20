"""
Conecta Plus - Router de Comunicados
"""

from uuid import UUID
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user, require_gerente
from ..models.usuario import Usuario
from ..models.comunicado import Comunicado, TipoComunicado
from ..schemas.comunicado import ComunicadoCreate, ComunicadoUpdate, ComunicadoResponse

router = APIRouter(prefix="/comunicados", tags=["Comunicados"])


@router.get("/", response_model=List[ComunicadoResponse])
async def listar_comunicados(
    tipo: Optional[TipoComunicado] = None,
    publicado: Optional[bool] = True,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lista comunicados."""
    query = db.query(Comunicado).filter(
        Comunicado.condominio_id == current_user.condominio_id
    )

    if publicado is not None:
        query = query.filter(Comunicado.publicado == publicado)
    if tipo:
        query = query.filter(Comunicado.tipo == tipo)

    # Filtrar expirados
    query = query.filter(
        (Comunicado.data_expiracao == None) |
        (Comunicado.data_expiracao > datetime.now())
    )

    return query.order_by(
        Comunicado.fixado.desc(),
        Comunicado.data_publicacao.desc()
    ).offset(skip).limit(limit).all()


@router.get("/{comunicado_id}", response_model=ComunicadoResponse)
async def obter_comunicado(
    comunicado_id: UUID,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtém um comunicado e incrementa visualizações."""
    comunicado = db.query(Comunicado).filter(Comunicado.id == comunicado_id).first()
    if not comunicado:
        raise HTTPException(status_code=404, detail="Comunicado não encontrado")

    comunicado.visualizacoes += 1
    db.commit()
    db.refresh(comunicado)

    return comunicado


@router.post("/", response_model=ComunicadoResponse, status_code=201)
async def criar_comunicado(
    data: ComunicadoCreate,
    current_user: Usuario = Depends(require_gerente),
    db: Session = Depends(get_db)
):
    """Cria um novo comunicado."""
    comunicado = Comunicado(
        titulo=data.titulo,
        conteudo=data.conteudo,
        tipo=data.tipo,
        autor_id=current_user.id,
        condominio_id=current_user.condominio_id,
        data_expiracao=data.data_expiracao,
        destinatarios=data.destinatarios,
        enviar_email=data.enviar_email,
        enviar_push=data.enviar_push,
        enviar_whatsapp=data.enviar_whatsapp,
        fixado=data.fixado,
        anexos=data.anexos
    )

    db.add(comunicado)
    db.commit()
    db.refresh(comunicado)
    return comunicado


@router.put("/{comunicado_id}", response_model=ComunicadoResponse)
async def atualizar_comunicado(
    comunicado_id: UUID,
    data: ComunicadoUpdate,
    current_user: Usuario = Depends(require_gerente),
    db: Session = Depends(get_db)
):
    """Atualiza um comunicado."""
    comunicado = db.query(Comunicado).filter(Comunicado.id == comunicado_id).first()
    if not comunicado:
        raise HTTPException(status_code=404, detail="Comunicado não encontrado")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(comunicado, field, value)

    db.commit()
    db.refresh(comunicado)
    return comunicado


@router.post("/{comunicado_id}/publicar")
async def publicar_comunicado(
    comunicado_id: UUID,
    current_user: Usuario = Depends(require_gerente),
    db: Session = Depends(get_db)
):
    """Publica um comunicado."""
    comunicado = db.query(Comunicado).filter(Comunicado.id == comunicado_id).first()
    if not comunicado:
        raise HTTPException(status_code=404, detail="Comunicado não encontrado")

    comunicado.publicado = True
    comunicado.data_publicacao = datetime.now()
    db.commit()

    # Aqui seria o envio de notificações
    # TODO: Integrar com serviço de notificações

    return {"message": "Comunicado publicado com sucesso"}


@router.delete("/{comunicado_id}", status_code=204)
async def deletar_comunicado(
    comunicado_id: UUID,
    current_user: Usuario = Depends(require_gerente),
    db: Session = Depends(get_db)
):
    """Deleta um comunicado."""
    comunicado = db.query(Comunicado).filter(Comunicado.id == comunicado_id).first()
    if not comunicado:
        raise HTTPException(status_code=404, detail="Comunicado não encontrado")

    db.delete(comunicado)
    db.commit()
    return None
