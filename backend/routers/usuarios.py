"""
Conecta Plus - Router de Usuários
"""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user, require_admin, get_password_hash
from ..models.usuario import Usuario, Role
from ..schemas.usuario import UsuarioCreate, UsuarioUpdate, UsuarioResponse

router = APIRouter(prefix="/usuarios", tags=["Usuários"])


@router.get("/me", response_model=UsuarioResponse)
async def obter_usuario_atual(
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtém os dados do usuário autenticado.
    """
    return current_user


@router.get("/", response_model=List[UsuarioResponse])
async def listar_usuarios(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    role: Optional[Role] = None,
    ativo: Optional[bool] = None,
    current_user: Usuario = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Lista todos os usuários (apenas admin).
    """
    query = db.query(Usuario)

    if current_user.condominio_id:
        query = query.filter(Usuario.condominio_id == current_user.condominio_id)

    if role:
        query = query.filter(Usuario.role == role)
    if ativo is not None:
        query = query.filter(Usuario.ativo == ativo)

    return query.offset(skip).limit(limit).all()


@router.get("/{usuario_id}", response_model=UsuarioResponse)
async def obter_usuario(
    usuario_id: UUID,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtém um usuário pelo ID.
    """
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )

    # Verificar permissão
    if current_user.role not in [Role.ADMIN, Role.SINDICO] and current_user.id != usuario_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sem permissão para acessar este usuário"
        )

    return usuario


@router.post("/", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
async def criar_usuario(
    usuario_data: UsuarioCreate,
    current_user: Usuario = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Cria um novo usuário (apenas admin).
    """
    # Verificar se email já existe
    if db.query(Usuario).filter(Usuario.email == usuario_data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email já cadastrado"
        )

    usuario = Usuario(
        email=usuario_data.email,
        nome=usuario_data.nome,
        telefone=usuario_data.telefone,
        role=usuario_data.role,
        senha_hash=get_password_hash(usuario_data.senha),
        condominio_id=usuario_data.condominio_id or current_user.condominio_id
    )

    db.add(usuario)
    db.commit()
    db.refresh(usuario)

    return usuario


@router.put("/{usuario_id}", response_model=UsuarioResponse)
async def atualizar_usuario(
    usuario_id: UUID,
    usuario_data: UsuarioUpdate,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Atualiza um usuário.
    """
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )

    # Verificar permissão
    if current_user.role not in [Role.ADMIN, Role.SINDICO] and current_user.id != usuario_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sem permissão para editar este usuário"
        )

    # Apenas admin pode alterar role
    if usuario_data.role and current_user.role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores podem alterar o papel do usuário"
        )

    for field, value in usuario_data.model_dump(exclude_unset=True).items():
        setattr(usuario, field, value)

    db.commit()
    db.refresh(usuario)

    return usuario


@router.delete("/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deletar_usuario(
    usuario_id: UUID,
    current_user: Usuario = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Desativa um usuário (soft delete).
    """
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )

    if usuario.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível desativar seu próprio usuário"
        )

    usuario.ativo = False
    db.commit()

    return None
