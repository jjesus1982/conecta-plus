"""
Conecta Plus - Schemas de Unidade
"""

from typing import Optional
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel


class UnidadeBase(BaseModel):
    numero: str
    bloco: Optional[str] = None
    tipo: str = "apartamento"


class UnidadeCreate(UnidadeBase):
    area_m2: Optional[Decimal] = None
    condominio_id: UUID
    proprietario_id: Optional[UUID] = None


class UnidadeUpdate(BaseModel):
    numero: Optional[str] = None
    bloco: Optional[str] = None
    tipo: Optional[str] = None
    area_m2: Optional[Decimal] = None
    proprietario_id: Optional[UUID] = None


class UnidadeResponse(UnidadeBase):
    id: UUID
    area_m2: Optional[Decimal] = None
    condominio_id: UUID
    proprietario_id: Optional[UUID] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UnidadeResumo(BaseModel):
    id: UUID
    numero: str
    bloco: Optional[str] = None

    class Config:
        from_attributes = True
