"""
Conecta Plus - Router de Controle de Acesso
Integração real com dispositivos via HardwareManager
"""

import logging
from uuid import UUID
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user, require_porteiro
from ..models.usuario import Usuario
from ..models.acesso import RegistroAcesso, PontoAcesso, TipoAcesso
from ..schemas.acesso import (
    RegistroAcessoCreate, RegistroAcessoResponse,
    PontoAcessoResponse, PontoAcessoComando
)
from ..services.hardware import (
    get_hardware_manager, HardwareManager, Device, DeviceType, DeviceStatus
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/acesso", tags=["Controle de Acesso"])


# --- Pontos de Acesso ---

@router.get("/pontos", response_model=List[PontoAcessoResponse])
async def listar_pontos(
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lista pontos de acesso do condomínio."""
    return db.query(PontoAcesso).filter(
        PontoAcesso.condominio_id == current_user.condominio_id
    ).all()


@router.get("/pontos/{ponto_id}", response_model=PontoAcessoResponse)
async def obter_ponto(
    ponto_id: UUID,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtém um ponto de acesso."""
    ponto = db.query(PontoAcesso).filter(PontoAcesso.id == ponto_id).first()
    if not ponto:
        raise HTTPException(status_code=404, detail="Ponto não encontrado")
    return ponto


@router.post("/pontos/{ponto_id}/comando")
async def comandar_ponto(
    ponto_id: UUID,
    comando: PontoAcessoComando,
    background: BackgroundTasks,
    current_user: Usuario = Depends(require_porteiro),
    db: Session = Depends(get_db),
    hw: HardwareManager = Depends(get_hardware_manager)
):
    """Envia comando para um ponto de acesso (abrir, fechar, travar)."""
    ponto = db.query(PontoAcesso).filter(PontoAcesso.id == ponto_id).first()
    if not ponto:
        raise HTTPException(status_code=404, detail="Ponto não encontrado")

    # Mapear ação para comando de hardware
    command_map = {
        "abrir": "open_door",
        "fechar": "close_door",
        "travar": "lock_door"
    }
    hw_command = command_map.get(comando.acao, "open_door")

    # Enviar comando para dispositivo real
    device_id = ponto.device_id if hasattr(ponto, 'device_id') and ponto.device_id else f"access-{ponto.id}"

    result = await hw.send_command(
        device_id=device_id,
        command=hw_command,
        params={"door_id": ponto.porta_numero if hasattr(ponto, 'porta_numero') else 1}
    )

    if result.success:
        # Atualizar status no banco
        if comando.acao == "abrir":
            ponto.status = "aberto"
        elif comando.acao == "fechar":
            ponto.status = "fechado"
        elif comando.acao == "travar":
            ponto.status = "travado"
        db.commit()

        # Registrar evento de acesso em background
        background.add_task(
            _registrar_comando_acesso,
            db, ponto_id, current_user.id, comando.acao
        )

        logger.info(f"Comando {comando.acao} enviado para ponto {ponto_id} por {current_user.nome}")
        return {
            "success": True,
            "message": f"Comando '{comando.acao}' executado com sucesso",
            "status": ponto.status,
            "device_response": result.response_data
        }
    else:
        logger.error(f"Falha ao enviar comando para ponto {ponto_id}: {result.error}")
        raise HTTPException(
            status_code=503,
            detail=f"Falha ao comunicar com dispositivo: {result.message}"
        )


async def _registrar_comando_acesso(db: Session, ponto_id: UUID, usuario_id: UUID, acao: str):
    """Registra comando de acesso no histórico."""
    try:
        registro = RegistroAcesso(
            ponto_id=ponto_id,
            usuario_id=usuario_id,
            tipo=TipoAcesso.COMANDO,
            observacao=f"Comando: {acao}",
            data_hora=datetime.now()
        )
        db.add(registro)
        db.commit()
    except Exception as e:
        logger.error(f"Erro ao registrar comando: {e}")


# --- Registros de Acesso ---

@router.get("/registros", response_model=List[RegistroAcessoResponse])
async def listar_registros(
    data_inicio: Optional[datetime] = None,
    data_fim: Optional[datetime] = None,
    tipo: Optional[TipoAcesso] = None,
    ponto_id: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lista registros de acesso."""
    query = db.query(RegistroAcesso).join(PontoAcesso).filter(
        PontoAcesso.condominio_id == current_user.condominio_id
    )

    if not data_inicio:
        data_inicio = datetime.now() - timedelta(days=1)
    query = query.filter(RegistroAcesso.data_hora >= data_inicio)

    if data_fim:
        query = query.filter(RegistroAcesso.data_hora <= data_fim)
    if tipo:
        query = query.filter(RegistroAcesso.tipo == tipo)
    if ponto_id:
        query = query.filter(RegistroAcesso.ponto_id == ponto_id)

    return query.order_by(RegistroAcesso.data_hora.desc()).offset(skip).limit(limit).all()


@router.post("/registros", response_model=RegistroAcessoResponse, status_code=201)
async def registrar_acesso(
    data: RegistroAcessoCreate,
    current_user: Usuario = Depends(require_porteiro),
    db: Session = Depends(get_db)
):
    """Registra um novo acesso."""
    registro = RegistroAcesso(**data.model_dump())
    db.add(registro)
    db.commit()
    db.refresh(registro)
    return registro


@router.get("/registros/{registro_id}", response_model=RegistroAcessoResponse)
async def obter_registro(
    registro_id: UUID,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtém um registro de acesso."""
    registro = db.query(RegistroAcesso).filter(RegistroAcesso.id == registro_id).first()
    if not registro:
        raise HTTPException(status_code=404, detail="Registro não encontrado")
    return registro


# --- Estatísticas ---

@router.get("/estatisticas")
async def estatisticas_acesso(
    periodo: str = Query("hoje", regex="^(hoje|semana|mes)$"),
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retorna estatísticas de acesso."""
    now = datetime.now()

    if periodo == "hoje":
        data_inicio = now.replace(hour=0, minute=0, second=0)
    elif periodo == "semana":
        data_inicio = now - timedelta(days=7)
    else:
        data_inicio = now - timedelta(days=30)

    query = db.query(RegistroAcesso).join(PontoAcesso).filter(
        PontoAcesso.condominio_id == current_user.condominio_id,
        RegistroAcesso.data_hora >= data_inicio
    )

    total = query.count()
    entradas = query.filter(RegistroAcesso.tipo == TipoAcesso.ENTRADA).count()
    saidas = query.filter(RegistroAcesso.tipo == TipoAcesso.SAIDA).count()

    return {
        "periodo": periodo,
        "total": total,
        "entradas": entradas,
        "saidas": saidas
    }
