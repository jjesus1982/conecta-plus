"""
Conecta Plus - Schemas de Comunicado
"""

from typing import Optional, List, Any
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel

from ..models.comunicado import TipoComunicado


class ComunicadoBase(BaseModel):
    titulo: str
    conteudo: str
    tipo: TipoComunicado = TipoComunicado.AVISO


class ComunicadoCreate(ComunicadoBase):
    data_expiracao: Optional[datetime] = None
    destinatarios: List[str] = ["todos"]
    enviar_email: bool = True
    enviar_push: bool = True
    enviar_whatsapp: bool = False
    fixado: bool = False
    anexos: List[str] = []


class ComunicadoUpdate(BaseModel):
    titulo: Optional[str] = None
    conteudo: Optional[str] = None
    tipo: Optional[TipoComunicado] = None
    data_expiracao: Optional[datetime] = None
    destinatarios: Optional[List[str]] = None
    fixado: Optional[bool] = None


class ComunicadoResponse(ComunicadoBase):
    id: UUID
    autor_id: UUID
    condominio_id: UUID
    publicado: bool
    data_publicacao: Optional[datetime] = None
    data_expiracao: Optional[datetime] = None
    destinatarios: List[Any]
    enviar_email: bool
    enviar_push: bool
    enviar_whatsapp: bool
    anexos: List[Any]
    fixado: bool
    visualizacoes: int
    created_at: datetime

    class Config:
        from_attributes = True


class ComunicadoFiltro(BaseModel):
    tipo: Optional[TipoComunicado] = None
    publicado: Optional[bool] = None
    fixado: Optional[bool] = None
    data_inicio: Optional[datetime] = None
    data_fim: Optional[datetime] = None
