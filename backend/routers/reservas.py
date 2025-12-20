"""
Conecta Plus - Router de Reservas
"""

from uuid import UUID
from typing import List, Optional
from datetime import date, time, datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user, require_gerente
from ..models.usuario import Usuario, Role
from ..models.reserva import AreaComum, Reserva, StatusReserva
from ..models.morador import Morador
from ..schemas.reserva import (
    AreaComumCreate, AreaComumResponse,
    ReservaCreate, ReservaUpdate, ReservaResponse
)

router = APIRouter(prefix="/reservas", tags=["Reservas"])


# --- Áreas Comuns ---

@router.get("/areas", response_model=List[AreaComumResponse])
async def listar_areas(
    ativo: bool = True,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lista áreas comuns disponíveis."""
    return db.query(AreaComum).filter(
        AreaComum.condominio_id == current_user.condominio_id,
        AreaComum.ativo == ativo
    ).all()


@router.get("/areas/{area_id}", response_model=AreaComumResponse)
async def obter_area(
    area_id: UUID,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtém uma área comum."""
    area = db.query(AreaComum).filter(AreaComum.id == area_id).first()
    if not area:
        raise HTTPException(status_code=404, detail="Área não encontrada")
    return area


@router.post("/areas", response_model=AreaComumResponse, status_code=201)
async def criar_area(
    data: AreaComumCreate,
    current_user: Usuario = Depends(require_gerente),
    db: Session = Depends(get_db)
):
    """Cria uma nova área comum."""
    area = AreaComum(
        **data.model_dump(),
        condominio_id=current_user.condominio_id
    )
    db.add(area)
    db.commit()
    db.refresh(area)
    return area


# --- Reservas ---

@router.get("/", response_model=List[ReservaResponse])
async def listar_reservas(
    area_id: Optional[int] = None,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    status: Optional[StatusReserva] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lista reservas."""
    query = db.query(Reserva).join(AreaComum).filter(
        AreaComum.condominio_id == current_user.condominio_id
    )

    # Morador vê apenas suas reservas
    if current_user.role == Role.MORADOR:
        query = query.filter(Reserva.responsavel_id == current_user.id)

    if area_id:
        query = query.filter(Reserva.area_id == area_id)
    if data_inicio:
        query = query.filter(Reserva.data >= data_inicio)
    if data_fim:
        query = query.filter(Reserva.data <= data_fim)
    if status:
        query = query.filter(Reserva.status == status)

    return query.order_by(Reserva.data.desc()).offset(skip).limit(limit).all()


@router.get("/{reserva_id}", response_model=ReservaResponse)
async def obter_reserva(
    reserva_id: UUID,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtém uma reserva."""
    reserva = db.query(Reserva).filter(Reserva.id == reserva_id).first()
    if not reserva:
        raise HTTPException(status_code=404, detail="Reserva não encontrada")
    return reserva


@router.post("/", response_model=ReservaResponse, status_code=201)
async def criar_reserva(
    data: ReservaCreate,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cria uma nova reserva."""
    # Verificar área
    area = db.query(AreaComum).filter(AreaComum.id == data.area_id).first()
    if not area:
        raise HTTPException(status_code=404, detail="Área não encontrada")

    # Verificar conflito de horário
    conflito = db.query(Reserva).filter(
        Reserva.area_id == data.area_id,
        Reserva.data == data.data,
        Reserva.status.in_([StatusReserva.PENDENTE, StatusReserva.CONFIRMADA]),
        ((Reserva.hora_inicio <= data.hora_inicio) & (Reserva.hora_fim > data.hora_inicio)) |
        ((Reserva.hora_inicio < data.hora_fim) & (Reserva.hora_fim >= data.hora_fim))
    ).first()

    if conflito:
        raise HTTPException(status_code=400, detail="Horário já reservado")

    # Obter unidade do morador
    morador = db.query(Morador).filter(Morador.usuario_id == current_user.id).first()
    if not morador:
        raise HTTPException(status_code=400, detail="Usuário não é morador")

    reserva = Reserva(
        area_id=data.area_id,
        unidade_id=morador.unidade_id,
        responsavel_id=current_user.id,
        data=data.data,
        hora_inicio=data.hora_inicio,
        hora_fim=data.hora_fim,
        evento_nome=data.evento_nome,
        num_convidados=data.num_convidados,
        observacoes=data.observacoes,
        valor_total=area.taxa_reserva + area.taxa_limpeza,
        status=StatusReserva.PENDENTE if area.requer_aprovacao else StatusReserva.CONFIRMADA
    )

    db.add(reserva)
    db.commit()
    db.refresh(reserva)
    return reserva


@router.put("/{reserva_id}", response_model=ReservaResponse)
async def atualizar_reserva(
    reserva_id: UUID,
    data: ReservaUpdate,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Atualiza uma reserva."""
    reserva = db.query(Reserva).filter(Reserva.id == reserva_id).first()
    if not reserva:
        raise HTTPException(status_code=404, detail="Reserva não encontrada")

    if reserva.responsavel_id != current_user.id and current_user.role not in [Role.ADMIN, Role.SINDICO]:
        raise HTTPException(status_code=403, detail="Sem permissão")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(reserva, field, value)

    db.commit()
    db.refresh(reserva)
    return reserva


@router.post("/{reserva_id}/cancelar")
async def cancelar_reserva(
    reserva_id: UUID,
    motivo: Optional[str] = None,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancela uma reserva."""
    reserva = db.query(Reserva).filter(Reserva.id == reserva_id).first()
    if not reserva:
        raise HTTPException(status_code=404, detail="Reserva não encontrada")

    if reserva.responsavel_id != current_user.id and current_user.role not in [Role.ADMIN, Role.SINDICO]:
        raise HTTPException(status_code=403, detail="Sem permissão")

    reserva.status = StatusReserva.CANCELADA
    reserva.motivo_cancelamento = motivo
    db.commit()

    return {"message": "Reserva cancelada"}


@router.post("/{reserva_id}/aprovar")
async def aprovar_reserva(
    reserva_id: UUID,
    current_user: Usuario = Depends(require_gerente),
    db: Session = Depends(get_db)
):
    """Aprova uma reserva pendente."""
    reserva = db.query(Reserva).filter(Reserva.id == reserva_id).first()
    if not reserva:
        raise HTTPException(status_code=404, detail="Reserva não encontrada")

    reserva.status = StatusReserva.CONFIRMADA
    reserva.aprovado_por = current_user.nome
    reserva.data_aprovacao = datetime.now()
    db.commit()

    return {"message": "Reserva aprovada"}
