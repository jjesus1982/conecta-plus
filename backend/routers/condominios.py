"""
Conecta Plus - Router de Condomínios
"""

from uuid import UUID
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user, require_admin
from ..models.usuario import Usuario, Role
from ..models.condominio import Condominio
from ..schemas.condominio import CondominioCreate, CondominioUpdate, CondominioResponse

router = APIRouter(prefix="/condominios", tags=["Condomínios"])


@router.get("/", response_model=List[CondominioResponse])
async def listar_condominios(
    current_user: Usuario = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Lista todos os condomínios (apenas admin master)."""
    return db.query(Condominio).all()


@router.get("/{condominio_id}", response_model=CondominioResponse)
async def obter_condominio(
    condominio_id: UUID,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtém um condomínio pelo ID."""
    condominio = db.query(Condominio).filter(Condominio.id == condominio_id).first()
    if not condominio:
        raise HTTPException(status_code=404, detail="Condomínio não encontrado")
    return condominio


@router.post("/", response_model=CondominioResponse, status_code=201)
async def criar_condominio(
    data: CondominioCreate,
    current_user: Usuario = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Cria um novo condomínio."""
    condominio = Condominio(**data.model_dump())
    db.add(condominio)
    db.commit()
    db.refresh(condominio)
    return condominio


@router.put("/{condominio_id}", response_model=CondominioResponse)
async def atualizar_condominio(
    condominio_id: UUID,
    data: CondominioUpdate,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Atualiza um condomínio."""
    condominio = db.query(Condominio).filter(Condominio.id == condominio_id).first()
    if not condominio:
        raise HTTPException(status_code=404, detail="Condomínio não encontrado")

    if current_user.role not in [Role.ADMIN, Role.SINDICO]:
        raise HTTPException(status_code=403, detail="Sem permissão")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(condominio, field, value)

    db.commit()
    db.refresh(condominio)
    return condominio
