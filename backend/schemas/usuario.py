"""
Conecta Plus - Schemas de Usuário
"""

from typing import Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr

from ..models.usuario import Role


class UsuarioBase(BaseModel):
    email: EmailStr
    nome: str
    telefone: Optional[str] = None
    role: Role = Role.MORADOR


class UsuarioCreate(UsuarioBase):
    senha: str
    condominio_id: Optional[str] = None


class UsuarioUpdate(BaseModel):
    nome: Optional[str] = None
    telefone: Optional[str] = None
    role: Optional[Role] = None
    ativo: Optional[bool] = None
    avatar_url: Optional[str] = None


class UsuarioResponse(UsuarioBase):
    id: UUID
    ativo: bool
    avatar_url: Optional[str] = None
    condominio_id: Optional[UUID] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class UsuarioSimples(BaseModel):
    id: UUID
    nome: str
    email: str
    role: Role

    class Config:
        from_attributes = True
