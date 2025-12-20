"""
Conecta Plus - Schemas de Assembleia
"""

from typing import Optional, List, Any
from datetime import datetime, date, time
from uuid import UUID
from pydantic import BaseModel

from ..models.assembleia import TipoAssembleia, StatusAssembleia, ModalidadeAssembleia


class AssembleiaBase(BaseModel):
    titulo: str
    tipo: TipoAssembleia
    modalidade: ModalidadeAssembleia = ModalidadeAssembleia.PRESENCIAL


class AssembleiaCreate(AssembleiaBase):
    data: date
    hora_primeira: time
    hora_segunda: Optional[time] = None
    local: Optional[str] = None
    link_virtual: Optional[str] = None
    quorum_necessario: float = 50
    pautas: List[str] = []


class AssembleiaUpdate(BaseModel):
    titulo: Optional[str] = None
    tipo: Optional[TipoAssembleia] = None
    status: Optional[StatusAssembleia] = None
    modalidade: Optional[ModalidadeAssembleia] = None
    data: Optional[date] = None
    hora_primeira: Optional[time] = None
    hora_segunda: Optional[time] = None
    local: Optional[str] = None
    link_virtual: Optional[str] = None
    pautas: Optional[List[str]] = None


class AssembleiaResponse(AssembleiaBase):
    id: UUID
    status: StatusAssembleia
    data: date
    hora_primeira: time
    hora_segunda: Optional[time] = None
    local: Optional[str] = None
    link_virtual: Optional[str] = None
    quorum_necessario: float
    quorum_especial: Optional[float] = None
    pautas: List[Any]
    edital_url: Optional[str] = None
    data_publicacao_edital: Optional[datetime] = None
    condominio_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class VotacaoCreate(BaseModel):
    titulo: str
    descricao: Optional[str] = None
    assembleia_id: UUID
    voto_secreto: bool = False
    quorum_especial: Optional[float] = None


class VotacaoResponse(BaseModel):
    id: UUID
    titulo: str
    descricao: Optional[str] = None
    assembleia_id: UUID
    aberta: bool
    data_abertura: Optional[datetime] = None
    data_encerramento: Optional[datetime] = None
    voto_secreto: bool
    quorum_especial: Optional[float] = None
    votos_favor: int
    votos_contra: int
    votos_abstencao: int
    aprovada: Optional[bool] = None
    resultado_descricao: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class VotoRequest(BaseModel):
    voto: str  # favor, contra, abstencao


class PresencaRequest(BaseModel):
    unidade_id: UUID
    morador_id: Optional[UUID] = None
    confirmado: bool = True
    procuracao: bool = False
    procurador_nome: Optional[str] = None


class AtaCreate(BaseModel):
    assembleia_id: UUID
    conteudo: Optional[str] = None


class AtaResponse(BaseModel):
    id: UUID
    assembleia_id: UUID
    conteudo: Optional[str] = None
    arquivo_url: Optional[str] = None
    status: str
    data_aprovacao: Optional[datetime] = None
    aprovada_por: Optional[str] = None
    data_publicacao: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True
