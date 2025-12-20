"""
Conecta Plus - Schemas Financeiros
"""

from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel


class LancamentoBase(BaseModel):
    descricao: str
    tipo: str  # receita ou despesa
    valor: Decimal


class LancamentoCreate(LancamentoBase):
    condominio_id: UUID
    data_lancamento: date
    data_competencia: Optional[date] = None
    data_vencimento: Optional[date] = None
    unidade_id: Optional[UUID] = None
    categoria_id: Optional[UUID] = None
    fornecedor_nome: Optional[str] = None
    observacao: Optional[str] = None


class LancamentoResponse(LancamentoBase):
    id: UUID
    condominio_id: UUID
    data_lancamento: date
    data_competencia: Optional[date] = None
    data_vencimento: Optional[date] = None
    data_pagamento: Optional[date] = None
    unidade_id: Optional[UUID] = None
    categoria_id: Optional[UUID] = None
    fornecedor_nome: Optional[str] = None
    documento_numero: Optional[str] = None
    documento_url: Optional[str] = None
    observacao: Optional[str] = None
    status: str = "pendente"
    rateio: bool = False
    recorrente: bool = False
    aprovado: bool = False
    conciliado: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BoletoCreate(BaseModel):
    condominio_id: UUID
    unidade_id: UUID
    valor: Decimal
    data_vencimento: date
    referencia: str
    tipo: str = "condominio"
    descricao: Optional[str] = None


class BoletoResponse(BaseModel):
    id: UUID
    condominio_id: UUID
    unidade_id: UUID
    referencia: str
    tipo: str = "condominio"
    descricao: Optional[str] = None
    valor: Decimal
    valor_pago: Optional[Decimal] = None
    valor_juros: Decimal = Decimal(0)
    valor_multa: Decimal = Decimal(0)
    valor_desconto: Decimal = Decimal(0)
    valor_total: Optional[Decimal] = None
    data_vencimento: date
    data_pagamento: Optional[date] = None
    status: str = "aberto"
    linha_digitavel: Optional[str] = None
    codigo_barras: Optional[str] = None
    pdf_url: Optional[str] = None
    pix_qrcode: Optional[str] = None
    pix_copia_cola: Optional[str] = None
    nosso_numero: Optional[str] = None
    parcela: Optional[int] = None
    total_parcelas: Optional[int] = None
    competencia: Optional[date] = None
    forma_pagamento: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ResumoFinanceiro(BaseModel):
    receita_mes: float
    despesa_mes: float
    saldo_mes: float
    inadimplencia_percentual: float
    inadimplencia_valor: float
    boletos_pendentes: int
    boletos_vencidos: int


class BoletoFiltro(BaseModel):
    status: Optional[str] = None
    unidade_id: Optional[UUID] = None
    referencia: Optional[str] = None
    data_inicio: Optional[date] = None
    data_fim: Optional[date] = None
