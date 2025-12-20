"""
Conecta Plus - Router de Alarmes
Integração real com centrais de alarme via HardwareManager
"""

import logging
from uuid import UUID
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user, require_porteiro
from ..models.usuario import Usuario
from ..models.alarme import ZonaAlarme, EventoAlarme, StatusZona, TipoEvento
from ..schemas.alarme import (
    ZonaAlarmeCreate, ZonaAlarmeResponse,
    EventoAlarmeResponse, ComandoAlarme, StatusSistemaAlarme
)
from ..services.hardware import (
    get_hardware_manager, HardwareManager, DeviceStatus
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/alarmes", tags=["Alarmes"])


@router.get("/status", response_model=StatusSistemaAlarme)
async def status_sistema(
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
    hw: HardwareManager = Depends(get_hardware_manager)
):
    """Retorna status geral do sistema de alarmes com dados do dispositivo real."""
    zonas = db.query(ZonaAlarme).filter(
        ZonaAlarme.condominio_id == current_user.condominio_id
    ).all()

    # Tentar obter status real da central de alarme
    central_online = False
    device_id = f"alarm-{current_user.condominio_id}"

    try:
        # Buscar status real das zonas do dispositivo
        result = await hw.send_command(device_id, "get_zones")
        if result.success and result.response_data:
            central_online = True
            hw_zones = result.response_data.get("zones", [])

            # Atualizar status das zonas com dados reais
            for zona in zonas:
                hw_zone = next(
                    (z for z in hw_zones if z.get("zone") == zona.numero_zona),
                    None
                )
                if hw_zone:
                    if hw_zone.get("bypassed"):
                        zona.status = StatusZona.BYPASS
                    elif hw_zone.get("status") == "armed":
                        zona.status = StatusZona.ARMADA
                    elif hw_zone.get("status") == "triggered":
                        zona.status = StatusZona.DISPARADA
                    else:
                        zona.status = StatusZona.DESARMADA
            db.commit()
    except Exception as e:
        logger.warning(f"Não foi possível obter status da central: {e}")
        # Verificar status do dispositivo
        device_status = await hw.get_device_status(device_id)
        central_online = device_status == DeviceStatus.ONLINE

    armadas = sum(1 for z in zonas if z.status == StatusZona.ARMADA)
    desarmadas = sum(1 for z in zonas if z.status == StatusZona.DESARMADA)
    problema = sum(1 for z in zonas if z.status in [StatusZona.DISPARADA, StatusZona.FALHA])

    # Determinar status geral
    if problema > 0:
        status_geral = "problema"
    elif armadas == len(zonas):
        status_geral = "armado"
    elif desarmadas == len(zonas):
        status_geral = "desarmado"
    else:
        status_geral = "parcial"

    ultimo_evento = db.query(EventoAlarme).join(ZonaAlarme).filter(
        ZonaAlarme.condominio_id == current_user.condominio_id
    ).order_by(EventoAlarme.data_hora.desc()).first()

    return StatusSistemaAlarme(
        status_geral=status_geral,
        zonas_armadas=armadas,
        zonas_desarmadas=desarmadas,
        zonas_problema=problema,
        ultimo_evento=ultimo_evento.data_hora if ultimo_evento else None,
        central_online=central_online
    )


@router.get("/zonas", response_model=List[ZonaAlarmeResponse])
async def listar_zonas(
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lista zonas de alarme."""
    return db.query(ZonaAlarme).filter(
        ZonaAlarme.condominio_id == current_user.condominio_id
    ).all()


@router.get("/zonas/{zona_id}", response_model=ZonaAlarmeResponse)
async def obter_zona(
    zona_id: UUID,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtém uma zona de alarme."""
    zona = db.query(ZonaAlarme).filter(ZonaAlarme.id == zona_id).first()
    if not zona:
        raise HTTPException(status_code=404, detail="Zona não encontrada")
    return zona


@router.post("/zonas/{zona_id}/comando")
async def comandar_zona(
    zona_id: UUID,
    comando: ComandoAlarme,
    background: BackgroundTasks,
    current_user: Usuario = Depends(require_porteiro),
    db: Session = Depends(get_db),
    hw: HardwareManager = Depends(get_hardware_manager)
):
    """Envia comando para uma zona (armar, desarmar, bypass) via hardware real."""
    zona = db.query(ZonaAlarme).filter(ZonaAlarme.id == zona_id).first()
    if not zona:
        raise HTTPException(status_code=404, detail="Zona não encontrada")

    # Mapear ação para status e tipo de evento
    if comando.acao == "armar":
        novo_status = StatusZona.ARMADA
        tipo_evento = TipoEvento.ARME
        hw_command = "arm"
    elif comando.acao == "desarmar":
        novo_status = StatusZona.DESARMADA
        tipo_evento = TipoEvento.DESARME
        hw_command = "disarm"
    elif comando.acao == "bypass":
        novo_status = StatusZona.BYPASS
        tipo_evento = TipoEvento.DESARME
        hw_command = "bypass"
    else:
        raise HTTPException(status_code=400, detail="Ação inválida")

    # Enviar comando para dispositivo real
    device_id = f"alarm-{zona.condominio_id}"
    result = await hw.send_command(
        device_id=device_id,
        command=hw_command,
        params={
            "partition": zona.particao if hasattr(zona, 'particao') else 1,
            "zone": zona.numero_zona if hasattr(zona, 'numero_zona') else zona_id,
            "password": comando.senha if hasattr(comando, 'senha') else None
        }
    )

    if result.success:
        # Atualizar zona no banco
        zona.status = novo_status
        zona.ultimo_evento = datetime.now()
        zona.ultimo_status = comando.acao

        # Criar evento
        evento = EventoAlarme(
            tipo=tipo_evento,
            descricao=f"Zona {comando.acao} por {current_user.nome}",
            zona_id=zona_id,
            usuario_id=current_user.id,
            tratado=True,
            tratado_por=current_user.nome,
            data_tratamento=datetime.now()
        )
        db.add(evento)
        db.commit()

        logger.info(f"Comando {comando.acao} enviado para zona {zona_id} por {current_user.nome}")
        return {
            "success": True,
            "message": f"Zona {comando.acao} com sucesso",
            "status": novo_status.value
        }
    else:
        logger.error(f"Falha ao enviar comando para zona {zona_id}: {result.error}")
        raise HTTPException(
            status_code=503,
            detail=f"Falha ao comunicar com central de alarme: {result.message}"
        )


@router.post("/comando-geral")
async def comando_geral(
    comando: ComandoAlarme,
    current_user: Usuario = Depends(require_porteiro),
    db: Session = Depends(get_db),
    hw: HardwareManager = Depends(get_hardware_manager)
):
    """Envia comando para todas as zonas via hardware real."""
    zonas = db.query(ZonaAlarme).filter(
        ZonaAlarme.condominio_id == current_user.condominio_id
    )

    if comando.zonas:
        zonas = zonas.filter(ZonaAlarme.id.in_(comando.zonas))

    zonas = zonas.all()

    novo_status = StatusZona.ARMADA if comando.acao == "armar" else StatusZona.DESARMADA
    tipo_evento = TipoEvento.ARME if comando.acao == "armar" else TipoEvento.DESARME
    hw_command = "arm" if comando.acao == "armar" else "disarm"

    # Enviar comando geral para a central
    device_id = f"alarm-{current_user.condominio_id}"
    result = await hw.send_command(
        device_id=device_id,
        command=hw_command,
        params={
            "partition": 0,  # 0 = todas as partições
            "password": comando.senha if hasattr(comando, 'senha') else None
        }
    )

    if result.success:
        for zona in zonas:
            zona.status = novo_status
            zona.ultimo_evento = datetime.now()

            evento = EventoAlarme(
                tipo=tipo_evento,
                descricao=f"Comando geral: {comando.acao}",
                zona_id=zona.id,
                usuario_id=current_user.id,
                tratado=True
            )
            db.add(evento)

        db.commit()

        logger.info(f"Comando geral {comando.acao} executado por {current_user.nome}")
        return {
            "success": True,
            "message": f"{len(zonas)} zonas atualizadas",
            "acao": comando.acao
        }
    else:
        logger.error(f"Falha no comando geral: {result.error}")
        raise HTTPException(
            status_code=503,
            detail=f"Falha ao comunicar com central: {result.message}"
        )


@router.get("/eventos", response_model=List[EventoAlarmeResponse])
async def listar_eventos(
    zona_id: Optional[int] = None,
    tipo: Optional[TipoEvento] = None,
    tratado: Optional[bool] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lista eventos de alarme."""
    query = db.query(EventoAlarme).join(ZonaAlarme).filter(
        ZonaAlarme.condominio_id == current_user.condominio_id
    )

    if zona_id:
        query = query.filter(EventoAlarme.zona_id == zona_id)
    if tipo:
        query = query.filter(EventoAlarme.tipo == tipo)
    if tratado is not None:
        query = query.filter(EventoAlarme.tratado == tratado)

    return query.order_by(EventoAlarme.data_hora.desc()).offset(skip).limit(limit).all()


@router.post("/eventos/{evento_id}/tratar")
async def tratar_evento(
    evento_id: UUID,
    observacao: Optional[str] = None,
    current_user: Usuario = Depends(require_porteiro),
    db: Session = Depends(get_db)
):
    """Marca evento como tratado."""
    evento = db.query(EventoAlarme).filter(EventoAlarme.id == evento_id).first()
    if not evento:
        raise HTTPException(status_code=404, detail="Evento não encontrado")

    evento.tratado = True
    evento.tratado_por = current_user.nome
    evento.data_tratamento = datetime.now()
    evento.observacao_tratamento = observacao
    db.commit()

    return {"message": "Evento tratado com sucesso"}
