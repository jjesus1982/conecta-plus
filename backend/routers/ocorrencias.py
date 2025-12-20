"""
Conecta Plus - Router de Ocorrências
"""

from uuid import UUID
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user, require_gerente
from ..models.usuario import Usuario, Role
from ..models.ocorrencia import Ocorrencia
from ..schemas.ocorrencia import OcorrenciaCreate, OcorrenciaUpdate, OcorrenciaResponse

router = APIRouter(prefix="/ocorrencias", tags=["Ocorrências"])


@router.get("/", response_model=List[OcorrenciaResponse])
async def listar_ocorrencias(
    status: Optional[str] = None,
    tipo: Optional[str] = None,
    unidade_id: Optional[UUID] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lista ocorrências."""
    query = db.query(Ocorrencia).filter(
        Ocorrencia.condominio_id == current_user.condominio_id
    )

    # Moradores veem apenas suas ocorrências
    if current_user.role == Role.MORADOR:
        query = query.filter(Ocorrencia.reportado_por == current_user.id)

    if status:
        query = query.filter(Ocorrencia.status == status)
    if tipo:
        query = query.filter(Ocorrencia.tipo == tipo)
    if unidade_id:
        query = query.filter(Ocorrencia.unidade_id == unidade_id)

    return query.order_by(Ocorrencia.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/{ocorrencia_id}", response_model=OcorrenciaResponse)
async def obter_ocorrencia(
    ocorrencia_id: UUID,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtém uma ocorrência."""
    ocorrencia = db.query(Ocorrencia).filter(Ocorrencia.id == ocorrencia_id).first()
    if not ocorrencia:
        raise HTTPException(status_code=404, detail="Ocorrência não encontrada")
    return ocorrencia


@router.post("/", response_model=OcorrenciaResponse, status_code=201)
async def criar_ocorrencia(
    data: OcorrenciaCreate,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cria uma nova ocorrência."""
    ocorrencia = Ocorrencia(
        condominio_id=data.condominio_id,
        titulo=data.titulo,
        descricao=data.descricao,
        tipo=data.tipo,
        prioridade=data.prioridade,
        unidade_id=data.unidade_id,
        reportado_por=current_user.id,
        anexos=data.anexos
    )

    db.add(ocorrencia)
    db.commit()
    db.refresh(ocorrencia)
    return ocorrencia


@router.put("/{ocorrencia_id}", response_model=OcorrenciaResponse)
async def atualizar_ocorrencia(
    ocorrencia_id: UUID,
    data: OcorrenciaUpdate,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Atualiza uma ocorrência."""
    ocorrencia = db.query(Ocorrencia).filter(Ocorrencia.id == ocorrencia_id).first()
    if not ocorrencia:
        raise HTTPException(status_code=404, detail="Ocorrência não encontrada")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(ocorrencia, field, value)

    # Se resolvida, registrar data
    if data.status == "resolvida":
        ocorrencia.resolvido_at = datetime.utcnow()

    db.commit()
    db.refresh(ocorrencia)
    return ocorrencia


@router.delete("/{ocorrencia_id}", status_code=204)
async def deletar_ocorrencia(
    ocorrencia_id: UUID,
    current_user: Usuario = Depends(require_gerente),
    db: Session = Depends(get_db)
):
    """Deleta uma ocorrência."""
    ocorrencia = db.query(Ocorrencia).filter(Ocorrencia.id == ocorrencia_id).first()
    if not ocorrencia:
        raise HTTPException(status_code=404, detail="Ocorrência não encontrada")

    db.delete(ocorrencia)
    db.commit()
    return None


@router.get("/estatisticas/resumo")
async def estatisticas_ocorrencias(
    current_user: Usuario = Depends(require_gerente),
    db: Session = Depends(get_db)
):
    """Retorna estatísticas de ocorrências."""
    query = db.query(Ocorrencia).filter(
        Ocorrencia.condominio_id == current_user.condominio_id
    )

    total = query.count()
    abertas = query.filter(Ocorrencia.status == "aberta").count()
    em_andamento = query.filter(Ocorrencia.status == "em_andamento").count()
    resolvidas = query.filter(Ocorrencia.status == "resolvida").count()

    return {
        "total": total,
        "abertas": abertas,
        "em_andamento": em_andamento,
        "resolvidas": resolvidas
    }
