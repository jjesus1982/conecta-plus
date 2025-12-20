"""
Conecta Plus - Schemas de Alarme
"""

from typing import Optional, List
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel

from ..models.alarme import TipoZona, StatusZona, TipoEvento


class ZonaAlarmeBase(BaseModel):
    nome: str
    tipo: TipoZona
    descricao: Optional[str] = None


class ZonaAlarmeCreate(ZonaAlarmeBase):
    numero_sensores: int = 1
    tempo_entrada: int = 30
    tempo_saida: int = 30
    sirene_habilitada: bool = True
    central_id: Optional[str] = None
    zona_id: Optional[str] = None


class ZonaAlarmeResponse(ZonaAlarmeBase):
    id: UUID
    status: StatusZona
    numero_sensores: int
    tempo_entrada: int
    tempo_saida: int
    sirene_habilitada: bool
    ultimo_evento: Optional[datetime] = None
    ultimo_status: Optional[str] = None
    condominio_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class ComandoAlarme(BaseModel):
    acao: str  # armar, desarmar, bypass
    senha: Optional[str] = None
    zonas: Optional[List[UUID]] = None  # IDs das zonas, None = todas


class EventoAlarmeResponse(BaseModel):
    id: UUID
    tipo: TipoEvento
    descricao: Optional[str] = None
    zona_id: UUID
    usuario_id: Optional[UUID] = None
    tratado: bool
    tratado_por: Optional[str] = None
    data_tratamento: Optional[datetime] = None
    observacao_tratamento: Optional[str] = None
    data_hora: datetime

    class Config:
        from_attributes = True


class EventoAlarmeCreate(BaseModel):
    tipo: TipoEvento
    zona_id: UUID
    descricao: Optional[str] = None


class TratamentoEvento(BaseModel):
    observacao: Optional[str] = None


class StatusSistemaAlarme(BaseModel):
    status_geral: str  # armado, desarmado, parcial
    zonas_armadas: int
    zonas_desarmadas: int
    zonas_problema: int
    ultimo_evento: Optional[datetime] = None
    central_online: bool
