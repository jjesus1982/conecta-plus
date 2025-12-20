"""
Conecta Plus - Schemas de Manutenção
"""

from typing import Optional, List, Any
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr

from ..models.manutencao import TipoOS, StatusOS, PrioridadeOS


class FornecedorBase(BaseModel):
    nome: str
    cnpj: Optional[str] = None
    especialidade: Optional[str] = None
    telefone: Optional[str] = None
    email: Optional[EmailStr] = None
    endereco: Optional[str] = None


class FornecedorCreate(FornecedorBase):
    condominio_id: UUID


class FornecedorResponse(FornecedorBase):
    id: UUID
    avaliacao_media: float
    total_avaliacoes: int
    ativo: bool
    created_at: datetime

    class Config:
        from_attributes = True


class OrdemServicoBase(BaseModel):
    titulo: str
    descricao: Optional[str] = None
    tipo: TipoOS
    prioridade: PrioridadeOS = PrioridadeOS.MEDIA


class OrdemServicoCreate(OrdemServicoBase):
    local: Optional[str] = None
    equipamento: Optional[str] = None
    solicitante_nome: Optional[str] = None
    fornecedor_id: Optional[UUID] = None
    custo_estimado: Optional[float] = None
    data_previsao: Optional[datetime] = None


class OrdemServicoUpdate(BaseModel):
    titulo: Optional[str] = None
    descricao: Optional[str] = None
    tipo: Optional[TipoOS] = None
    status: Optional[StatusOS] = None
    prioridade: Optional[PrioridadeOS] = None
    responsavel_id: Optional[UUID] = None
    fornecedor_id: Optional[UUID] = None
    custo_estimado: Optional[float] = None
    custo_real: Optional[float] = None
    data_previsao: Optional[datetime] = None
    observacao: Optional[str] = None


class OrdemServicoResponse(OrdemServicoBase):
    id: UUID
    numero: str
    status: StatusOS
    local: Optional[str] = None
    equipamento: Optional[str] = None
    solicitante_nome: Optional[str] = None
    solicitante_id: Optional[UUID] = None
    responsavel_id: Optional[UUID] = None
    fornecedor_id: Optional[UUID] = None
    custo_estimado: Optional[float] = None
    custo_real: Optional[float] = None
    data_abertura: datetime
    data_previsao: Optional[datetime] = None
    data_conclusao: Optional[datetime] = None
    anexos: List[Any]
    historico: List[Any]
    avaliacao: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class OrdemServicoFiltro(BaseModel):
    status: Optional[StatusOS] = None
    tipo: Optional[TipoOS] = None
    prioridade: Optional[PrioridadeOS] = None
    fornecedor_id: Optional[UUID] = None
    data_inicio: Optional[datetime] = None
    data_fim: Optional[datetime] = None
