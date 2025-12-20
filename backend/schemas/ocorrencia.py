"""
Conecta Plus - Schemas de Ocorrência
"""

from typing import Optional, List, Any
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class OcorrenciaBase(BaseModel):
    titulo: str
    descricao: Optional[str] = None
    tipo: Optional[str] = None
    prioridade: str = "media"


class OcorrenciaCreate(OcorrenciaBase):
    condominio_id: UUID
    unidade_id: Optional[UUID] = None
    anexos: List[str] = []


class OcorrenciaUpdate(BaseModel):
    titulo: Optional[str] = None
    descricao: Optional[str] = None
    tipo: Optional[str] = None
    status: Optional[str] = None
    prioridade: Optional[str] = None
    responsavel_id: Optional[UUID] = None


class OcorrenciaResponse(OcorrenciaBase):
    id: UUID
    condominio_id: UUID
    status: str = "aberta"
    unidade_id: Optional[UUID] = None
    reportado_por: Optional[UUID] = None
    responsavel_id: Optional[UUID] = None
    anexos: List[Any] = []
    created_at: datetime
    updated_at: Optional[datetime] = None
    resolvido_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class OcorrenciaFiltro(BaseModel):
    status: Optional[str] = None
    tipo: Optional[str] = None
    prioridade: Optional[str] = None
    unidade_id: Optional[UUID] = None
    data_inicio: Optional[datetime] = None
    data_fim: Optional[datetime] = None
