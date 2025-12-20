"""
Conecta Plus - Schemas de Morador
"""

from typing import Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class MoradorBase(BaseModel):
    tipo: str = "morador"
    principal: bool = False


class MoradorCreate(MoradorBase):
    usuario_id: UUID
    unidade_id: UUID


class MoradorUpdate(BaseModel):
    tipo: Optional[str] = None
    principal: Optional[bool] = None


class MoradorResponse(MoradorBase):
    id: UUID
    usuario_id: UUID
    unidade_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
