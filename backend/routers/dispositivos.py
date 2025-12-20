"""
Conecta Plus - Router de Gerenciamento de Dispositivos
Permite registrar, monitorar e gerenciar dispositivos de hardware
"""

import logging
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..database import get_db
from ..dependencies import get_current_user, require_admin
from ..models.usuario import Usuario
from ..services.hardware import (
    get_hardware_manager, HardwareManager, Device, DeviceType, DeviceStatus
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dispositivos", tags=["Dispositivos"])


# Schemas
class DeviceCreate(BaseModel):
    name: str
    type: str  # access_control, alarm_panel, camera, gate, intercom
    ip: str
    port: int = 80
    protocol: str = "http"  # http, controlid, intelbras, onvif, etc
    username: Optional[str] = None
    password: Optional[str] = None
    metadata: Optional[dict] = None


class DeviceResponse(BaseModel):
    id: str
    name: str
    type: str
    ip: str
    port: int
    protocol: str
    status: str
    last_seen: Optional[datetime] = None


class DeviceCommand(BaseModel):
    command: str
    params: Optional[dict] = None


# Routes

@router.get("", response_model=List[DeviceResponse])
async def listar_dispositivos(
    tipo: Optional[str] = None,
    status: Optional[str] = None,
    current_user: Usuario = Depends(get_current_user),
    hw: HardwareManager = Depends(get_hardware_manager)
):
    """Lista todos os dispositivos registrados."""
    devices = await hw.get_all_devices()

    result = []
    for device in devices:
        if tipo and device.type.value != tipo:
            continue
        if status and device.status.value != status:
            continue

        result.append(DeviceResponse(
            id=device.id,
            name=device.name,
            type=device.type.value,
            ip=device.ip,
            port=device.port,
            protocol=device.protocol,
            status=device.status.value,
            last_seen=device.last_seen
        ))

    return result


@router.post("", response_model=DeviceResponse)
async def registrar_dispositivo(
    data: DeviceCreate,
    current_user: Usuario = Depends(require_admin),
    hw: HardwareManager = Depends(get_hardware_manager)
):
    """Registra um novo dispositivo de hardware."""
    # Mapear tipo
    type_map = {
        "access_control": DeviceType.ACCESS_CONTROL,
        "alarm_panel": DeviceType.ALARM_PANEL,
        "camera": DeviceType.CAMERA,
        "gate": DeviceType.GATE,
        "intercom": DeviceType.INTERCOM,
    }

    device_type = type_map.get(data.type)
    if not device_type:
        raise HTTPException(status_code=400, detail=f"Tipo inválido: {data.type}")

    # Criar device
    device_id = f"{data.type}-{current_user.condominio_id}-{data.ip.replace('.', '-')}"
    device = Device(
        id=device_id,
        name=data.name,
        type=device_type,
        ip=data.ip,
        port=data.port,
        protocol=data.protocol,
        username=data.username,
        password=data.password,
        metadata=data.metadata
    )

    # Registrar e tentar conectar
    connected = await hw.register_device(device)

    logger.info(f"Dispositivo {device_id} registrado por {current_user.nome}")

    return DeviceResponse(
        id=device.id,
        name=device.name,
        type=device.type.value,
        ip=device.ip,
        port=device.port,
        protocol=device.protocol,
        status="online" if connected else "offline",
        last_seen=datetime.now() if connected else None
    )


@router.get("/{device_id}", response_model=DeviceResponse)
async def obter_dispositivo(
    device_id: str,
    current_user: Usuario = Depends(get_current_user),
    hw: HardwareManager = Depends(get_hardware_manager)
):
    """Obtém informações de um dispositivo."""
    devices = await hw.get_all_devices()
    device = next((d for d in devices if d.id == device_id), None)

    if not device:
        raise HTTPException(status_code=404, detail="Dispositivo não encontrado")

    return DeviceResponse(
        id=device.id,
        name=device.name,
        type=device.type.value,
        ip=device.ip,
        port=device.port,
        protocol=device.protocol,
        status=device.status.value,
        last_seen=device.last_seen
    )


@router.get("/{device_id}/status")
async def status_dispositivo(
    device_id: str,
    current_user: Usuario = Depends(get_current_user),
    hw: HardwareManager = Depends(get_hardware_manager)
):
    """Verifica status atual do dispositivo (ping)."""
    status = await hw.get_device_status(device_id)

    return {
        "device_id": device_id,
        "status": status.value,
        "timestamp": datetime.now().isoformat()
    }


@router.post("/{device_id}/comando")
async def comandar_dispositivo(
    device_id: str,
    comando: DeviceCommand,
    current_user: Usuario = Depends(require_admin),
    hw: HardwareManager = Depends(get_hardware_manager)
):
    """Envia comando para um dispositivo."""
    result = await hw.send_command(device_id, comando.command, comando.params)

    if not result.success:
        raise HTTPException(status_code=503, detail=result.message)

    logger.info(f"Comando {comando.command} enviado para {device_id} por {current_user.nome}")

    return {
        "success": result.success,
        "message": result.message,
        "timestamp": result.timestamp.isoformat(),
        "response": result.response_data
    }


@router.delete("/{device_id}")
async def remover_dispositivo(
    device_id: str,
    current_user: Usuario = Depends(require_admin),
    hw: HardwareManager = Depends(get_hardware_manager)
):
    """Remove um dispositivo do sistema."""
    devices = await hw.get_all_devices()
    device = next((d for d in devices if d.id == device_id), None)

    if not device:
        raise HTTPException(status_code=404, detail="Dispositivo não encontrado")

    # Desconectar driver
    driver = hw._drivers.get(device_id)
    if driver:
        await driver.disconnect()
        del hw._drivers[device_id]

    # Remover do cache
    del hw._devices[device_id]
    if hw._redis:
        await hw._redis.hdel("hardware:devices", device_id)

    logger.info(f"Dispositivo {device_id} removido por {current_user.nome}")

    return {"message": f"Dispositivo {device_id} removido"}


# Discovery endpoints

@router.post("/discover")
async def descobrir_dispositivos(
    subnet: str = Query(default="192.168.1.0/24", description="Subnet para scan"),
    current_user: Usuario = Depends(require_admin),
    hw: HardwareManager = Depends(get_hardware_manager)
):
    """Descobre dispositivos na rede local (ONVIF, mDNS)."""
    # Esta função seria implementada para scan de rede
    # Por enquanto retorna placeholder

    discovered = []

    # TODO: Implementar WS-Discovery para ONVIF
    # TODO: Implementar mDNS/Bonjour discovery
    # TODO: Implementar scan de portas conhecidas

    return {
        "subnet": subnet,
        "discovered": discovered,
        "message": "Discovery executado"
    }


@router.get("/tipos")
async def listar_tipos():
    """Lista tipos de dispositivos suportados."""
    return {
        "tipos": [
            {
                "value": "access_control",
                "label": "Controle de Acesso",
                "protocols": ["controlid", "http"]
            },
            {
                "value": "alarm_panel",
                "label": "Central de Alarme",
                "protocols": ["intelbras", "paradox", "dsc"]
            },
            {
                "value": "camera",
                "label": "Câmera IP",
                "protocols": ["onvif", "rtsp", "http"]
            },
            {
                "value": "gate",
                "label": "Portão/Motor",
                "protocols": ["http", "relay"]
            },
            {
                "value": "intercom",
                "label": "Interfone",
                "protocols": ["sip", "http"]
            }
        ]
    }
