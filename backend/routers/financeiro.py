"""
Conecta Plus - Router Financeiro
"""

from uuid import UUID
from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..database import get_db
from ..dependencies import get_current_user, require_gerente
from ..models.usuario import Usuario, Role
from ..models.financeiro import Lancamento, Boleto, StatusBoleto, TipoLancamento
from ..models.unidade import Unidade
from ..schemas.financeiro import (
    LancamentoCreate, LancamentoResponse,
    BoletoCreate, BoletoResponse, ResumoFinanceiro
)

router = APIRouter(prefix="/financeiro", tags=["Financeiro"])


# --- Lançamentos ---

@router.get("/lancamentos", response_model=List[LancamentoResponse])
async def listar_lancamentos(
    tipo: Optional[TipoLancamento] = None,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: Usuario = Depends(require_gerente),
    db: Session = Depends(get_db)
):
    """Lista lançamentos financeiros."""
    query = db.query(Lancamento).filter(
        Lancamento.condominio_id == current_user.condominio_id
    )

    if tipo:
        query = query.filter(Lancamento.tipo == tipo)
    if data_inicio:
        query = query.filter(Lancamento.data_competencia >= data_inicio)
    if data_fim:
        query = query.filter(Lancamento.data_competencia <= data_fim)

    return query.order_by(Lancamento.data_competencia.desc()).offset(skip).limit(limit).all()


@router.post("/lancamentos", response_model=LancamentoResponse, status_code=201)
async def criar_lancamento(
    data: LancamentoCreate,
    current_user: Usuario = Depends(require_gerente),
    db: Session = Depends(get_db)
):
    """Cria um novo lançamento."""
    lancamento = Lancamento(
        **data.model_dump(),
        condominio_id=current_user.condominio_id
    )
    db.add(lancamento)
    db.commit()
    db.refresh(lancamento)
    return lancamento


# --- Boletos ---

@router.get("/boletos", response_model=List[BoletoResponse])
async def listar_boletos(
    status: Optional[StatusBoleto] = None,
    unidade_id: Optional[int] = None,
    referencia: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lista boletos."""
    query = db.query(Boleto).filter(
        Boleto.condominio_id == current_user.condominio_id
    )

    # Morador vê apenas seus boletos
    if current_user.role == Role.MORADOR:
        from ..models.morador import Morador
        morador = db.query(Morador).filter(Morador.usuario_id == current_user.id).first()
        if morador:
            query = query.filter(Boleto.unidade_id == morador.unidade_id)

    if status:
        query = query.filter(Boleto.status == status)
    if unidade_id:
        query = query.filter(Boleto.unidade_id == unidade_id)
    if referencia:
        query = query.filter(Boleto.referencia == referencia)

    return query.order_by(Boleto.data_vencimento.desc()).offset(skip).limit(limit).all()


@router.get("/boletos/{boleto_id}", response_model=BoletoResponse)
async def obter_boleto(
    boleto_id: UUID,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtém um boleto."""
    boleto = db.query(Boleto).filter(Boleto.id == boleto_id).first()
    if not boleto:
        raise HTTPException(status_code=404, detail="Boleto não encontrado")
    return boleto


@router.post("/boletos", response_model=BoletoResponse, status_code=201)
async def gerar_boleto(
    data: BoletoCreate,
    current_user: Usuario = Depends(require_gerente),
    db: Session = Depends(get_db)
):
    """Gera um novo boleto."""
    import uuid

    boleto = Boleto(
        numero=f"BOL-{uuid.uuid4().hex[:10].upper()}",
        unidade_id=data.unidade_id,
        valor=data.valor,
        data_vencimento=data.data_vencimento,
        referencia=data.referencia,
        condominio_id=current_user.condominio_id
    )
    db.add(boleto)
    db.commit()
    db.refresh(boleto)
    return boleto


@router.post("/boletos/{boleto_id}/pagar")
async def registrar_pagamento(
    boleto_id: UUID,
    valor_pago: float,
    data_pagamento: date = None,
    current_user: Usuario = Depends(require_gerente),
    db: Session = Depends(get_db)
):
    """Registra pagamento de boleto."""
    boleto = db.query(Boleto).filter(Boleto.id == boleto_id).first()
    if not boleto:
        raise HTTPException(status_code=404, detail="Boleto não encontrado")

    boleto.valor_pago = valor_pago
    boleto.data_pagamento = data_pagamento or date.today()
    boleto.status = StatusBoleto.PAGO
    db.commit()

    return {"message": "Pagamento registrado com sucesso"}


# --- Resumo ---

@router.get("/resumo", response_model=ResumoFinanceiro)
async def resumo_financeiro(
    mes: Optional[int] = None,
    ano: Optional[int] = None,
    current_user: Usuario = Depends(require_gerente),
    db: Session = Depends(get_db)
):
    """Retorna resumo financeiro."""
    from datetime import date as dt_date

    if not mes:
        mes = dt_date.today().month
    if not ano:
        ano = dt_date.today().year

    # Receitas do mês
    receitas = db.query(func.sum(Lancamento.valor)).filter(
        Lancamento.condominio_id == current_user.condominio_id,
        Lancamento.tipo == TipoLancamento.RECEITA,
        func.extract('month', Lancamento.data_competencia) == mes,
        func.extract('year', Lancamento.data_competencia) == ano
    ).scalar() or 0

    # Despesas do mês
    despesas = db.query(func.sum(Lancamento.valor)).filter(
        Lancamento.condominio_id == current_user.condominio_id,
        Lancamento.tipo == TipoLancamento.DESPESA,
        func.extract('month', Lancamento.data_competencia) == mes,
        func.extract('year', Lancamento.data_competencia) == ano
    ).scalar() or 0

    # Inadimplência
    total_unidades = db.query(Unidade).filter(
        Unidade.condominio_id == current_user.condominio_id
    ).count()

    boletos_vencidos = db.query(Boleto).filter(
        Boleto.condominio_id == current_user.condominio_id,
        Boleto.status == StatusBoleto.VENCIDO
    ).count()

    inadimplencia_valor = db.query(func.sum(Boleto.valor)).filter(
        Boleto.condominio_id == current_user.condominio_id,
        Boleto.status == StatusBoleto.VENCIDO
    ).scalar() or 0

    boletos_pendentes = db.query(Boleto).filter(
        Boleto.condominio_id == current_user.condominio_id,
        Boleto.status == StatusBoleto.PENDENTE
    ).count()

    return ResumoFinanceiro(
        receita_mes=receitas,
        despesa_mes=despesas,
        saldo_mes=receitas - despesas,
        inadimplencia_percentual=(boletos_vencidos / total_unidades * 100) if total_unidades > 0 else 0,
        inadimplencia_valor=inadimplencia_valor,
        boletos_pendentes=boletos_pendentes,
        boletos_vencidos=boletos_vencidos
    )
