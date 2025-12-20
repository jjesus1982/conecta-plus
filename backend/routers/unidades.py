"""
Conecta Plus - Router de Unidades
"""

from uuid import UUID
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user, require_gerente
from ..models.usuario import Usuario
from ..models.unidade import Unidade
from ..schemas.unidade import UnidadeCreate, UnidadeUpdate, UnidadeResponse

router = APIRouter(prefix="/unidades", tags=["Unidades"])


@router.get("/", response_model=List[UnidadeResponse])
async def listar_unidades(
    bloco: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lista unidades do condomínio."""
    query = db.query(Unidade).filter(Unidade.condominio_id == current_user.condominio_id)

    if bloco:
        query = query.filter(Unidade.bloco == bloco)

    return query.offset(skip).limit(limit).all()


@router.get("/{unidade_id}", response_model=UnidadeResponse)
async def obter_unidade(
    unidade_id: UUID,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtém uma unidade pelo ID."""
    unidade = db.query(Unidade).filter(
        Unidade.id == unidade_id,
        Unidade.condominio_id == current_user.condominio_id
    ).first()

    if not unidade:
        raise HTTPException(status_code=404, detail="Unidade não encontrada")
    return unidade


@router.post("/", response_model=UnidadeResponse, status_code=201)
async def criar_unidade(
    data: UnidadeCreate,
    current_user: Usuario = Depends(require_gerente),
    db: Session = Depends(get_db)
):
    """Cria uma nova unidade."""
    unidade = Unidade(**data.model_dump())
    db.add(unidade)
    db.commit()
    db.refresh(unidade)
    return unidade


@router.put("/{unidade_id}", response_model=UnidadeResponse)
async def atualizar_unidade(
    unidade_id: UUID,
    data: UnidadeUpdate,
    current_user: Usuario = Depends(require_gerente),
    db: Session = Depends(get_db)
):
    """Atualiza uma unidade."""
    unidade = db.query(Unidade).filter(Unidade.id == unidade_id).first()
    if not unidade:
        raise HTTPException(status_code=404, detail="Unidade não encontrada")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(unidade, field, value)

    db.commit()
    db.refresh(unidade)
    return unidade


@router.delete("/{unidade_id}", status_code=204)
async def deletar_unidade(
    unidade_id: UUID,
    current_user: Usuario = Depends(require_gerente),
    db: Session = Depends(get_db)
):
    """Deleta uma unidade."""
    unidade = db.query(Unidade).filter(Unidade.id == unidade_id).first()
    if not unidade:
        raise HTTPException(status_code=404, detail="Unidade não encontrada")

    db.delete(unidade)
    db.commit()
    return None
