"""
Conecta Plus - Schemas de Reserva
"""

from typing import Optional, List, Any
from datetime import datetime, date, time
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel

from ..models.reserva import StatusReserva


class AreaComumBase(BaseModel):
    nome: str
    descricao: Optional[str] = None
    capacidade: Optional[int] = None


class AreaComumCreate(AreaComumBase):
    condominio_id: UUID
    valor: Decimal = Decimal(0)
    regras: Optional[str] = None
    horario_abertura: Optional[time] = None
    horario_fechamento: Optional[time] = None
    dias_funcionamento: List[int] = [1, 2, 3, 4, 5, 6, 0]


class AreaComumResponse(AreaComumBase):
    id: UUID
    condominio_id: UUID
    valor: Decimal = Decimal(0)
    regras: Optional[str] = None
    horario_abertura: Optional[time] = None
    horario_fechamento: Optional[time] = None
    dias_funcionamento: List[int] = [1, 2, 3, 4, 5, 6, 0]
    ativo: bool
    fotos: List[Any] = []
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ReservaCreate(BaseModel):
    area_id: UUID
    unidade_id: UUID
    data: date
    hora_inicio: time
    hora_fim: time
    evento_nome: Optional[str] = None
    num_convidados: int = 0
    observacoes: Optional[str] = None


class ReservaUpdate(BaseModel):
    data: Optional[date] = None
    hora_inicio: Optional[time] = None
    hora_fim: Optional[time] = None
    evento_nome: Optional[str] = None
    num_convidados: Optional[int] = None
    observacoes: Optional[str] = None
    status: Optional[StatusReserva] = None


class ReservaResponse(BaseModel):
    id: UUID
    area_id: UUID
    unidade_id: UUID
    responsavel_id: UUID
    data: date
    hora_inicio: time
    hora_fim: time
    status: StatusReserva
    evento_nome: Optional[str] = None
    num_convidados: int
    valor_total: Decimal = Decimal(0)
    caucao_pago: bool
    aprovado_por: Optional[str] = None
    data_aprovacao: Optional[datetime] = None
    motivo_cancelamento: Optional[str] = None
    observacoes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DisponibilidadeRequest(BaseModel):
    area_id: UUID
    data: date


class HorarioDisponivel(BaseModel):
    hora_inicio: time
    hora_fim: time
    disponivel: bool
