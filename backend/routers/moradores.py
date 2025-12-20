"""
Conecta Plus - Router de Moradores
"""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user, require_gerente
from ..models.usuario import Usuario
from ..models.morador import Morador
from ..schemas.morador import MoradorCreate, MoradorUpdate, MoradorResponse

router = APIRouter(prefix="/moradores", tags=["Moradores"])


@router.get("/", response_model=List[MoradorResponse])
async def listar_moradores(
    unidade_id: Optional[UUID] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lista moradores do condomínio."""
    from ..models.unidade import Unidade

    query = db.query(Morador).join(Unidade).filter(
        Unidade.condominio_id == current_user.condominio_id
    )

    if unidade_id:
        query = query.filter(Morador.unidade_id == unidade_id)

    return query.offset(skip).limit(limit).all()


@router.get("/{morador_id}", response_model=MoradorResponse)
async def obter_morador(
    morador_id: UUID,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtém um morador pelo ID."""
    morador = db.query(Morador).filter(Morador.id == morador_id).first()
    if not morador:
        raise HTTPException(status_code=404, detail="Morador não encontrado")
    return morador


@router.post("/", response_model=MoradorResponse, status_code=201)
async def criar_morador(
    data: MoradorCreate,
    current_user: Usuario = Depends(require_gerente),
    db: Session = Depends(get_db)
):
    """Cria um novo morador."""
    morador = Morador(**data.model_dump())

    db.add(morador)
    db.commit()
    db.refresh(morador)
    return morador


@router.put("/{morador_id}", response_model=MoradorResponse)
async def atualizar_morador(
    morador_id: UUID,
    data: MoradorUpdate,
    current_user: Usuario = Depends(require_gerente),
    db: Session = Depends(get_db)
):
    """Atualiza um morador."""
    morador = db.query(Morador).filter(Morador.id == morador_id).first()
    if not morador:
        raise HTTPException(status_code=404, detail="Morador não encontrado")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(morador, field, value)

    db.commit()
    db.refresh(morador)
    return morador


@router.delete("/{morador_id}", status_code=204)
async def deletar_morador(
    morador_id: UUID,
    current_user: Usuario = Depends(require_gerente),
    db: Session = Depends(get_db)
):
    """Deleta um morador."""
    morador = db.query(Morador).filter(Morador.id == morador_id).first()
    if not morador:
        raise HTTPException(status_code=404, detail="Morador não encontrado")

    db.delete(morador)
    db.commit()
    return None
