"""
Conecta Plus - Device Tools
Ferramentas para controle de dispositivos
"""

import asyncio
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

from .base_tool import (
    BaseTool, ToolContext, ToolResult, ToolMetadata,
    ToolCategory, ToolParameter, ParameterType, tool
)

logger = logging.getLogger(__name__)


# ============================================================
# Camera Tool
# ============================================================

class CameraStatus(Enum):
    """Status da câmera"""
    ONLINE = "online"
    OFFLINE = "offline"
    RECORDING = "recording"
    ERROR = "error"
    MAINTENANCE = "maintenance"


@dataclass
class CameraInfo:
    """Informações da câmera"""
    camera_id: str
    name: str
    location: str
    status: CameraStatus
    ip_address: str
    model: str
    resolution: str = "1080p"
    has_ptz: bool = False
    has_audio: bool = False
    is_recording: bool = False


@tool(
    name="camera",
    version="1.0.0",
    category=ToolCategory.DEVICE,
    description="Controle de câmeras de segurança",
    parameters=[
        ToolParameter("action", ParameterType.ENUM, "Ação da câmera",
                     required=True,
                     enum_values=["list", "status", "snapshot", "stream", "ptz", "recording", "playback"]),
        ToolParameter("camera_id", ParameterType.STRING, "ID da câmera", required=False),
        ToolParameter("direction", ParameterType.ENUM, "Direção PTZ",
                     required=False, enum_values=["up", "down", "left", "right", "zoom_in", "zoom_out"]),
        ToolParameter("preset", ParameterType.INTEGER, "Preset PTZ", required=False),
        ToolParameter("start_time", ParameterType.DATETIME, "Início do playback", required=False),
        ToolParameter("end_time", ParameterType.DATETIME, "Fim do playback", required=False),
    ],
    tags=["camera", "cftv", "security", "video"],
    required_permissions=["cftv_view"]
)
class CameraTool(BaseTool):
    """
    Ferramenta para controle de câmeras.
    Suporta visualização, PTZ, gravação e playback.
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self._cameras: Dict[str, CameraInfo] = self._load_cameras()

    def _load_cameras(self) -> Dict[str, CameraInfo]:
        """Carrega câmeras configuradas"""
        return {
            "cam_001": CameraInfo(
                camera_id="cam_001",
                name="Entrada Principal",
                location="Portaria",
                status=CameraStatus.ONLINE,
                ip_address="192.168.1.101",
                model="Hikvision DS-2CD2143G2",
                has_ptz=True,
                has_audio=True,
                is_recording=True
            ),
            "cam_002": CameraInfo(
                camera_id="cam_002",
                name="Estacionamento",
                location="Garagem",
                status=CameraStatus.RECORDING,
                ip_address="192.168.1.102",
                model="Intelbras VIP 3230",
                is_recording=True
            ),
            "cam_003": CameraInfo(
                camera_id="cam_003",
                name="Área de Lazer",
                location="Piscina",
                status=CameraStatus.ONLINE,
                ip_address="192.168.1.103",
                model="Hikvision DS-2CD2043G2",
                has_ptz=True
            )
        }

    async def _execute(self, context: ToolContext, **params) -> ToolResult:
        """Executa ação na câmera"""
        action = params.get("action")

        if action == "list":
            return await self._list_cameras(context, params)
        elif action == "status":
            return await self._get_status(context, params)
        elif action == "snapshot":
            return await self._get_snapshot(context, params)
        elif action == "stream":
            return await self._get_stream(context, params)
        elif action == "ptz":
            return await self._control_ptz(context, params)
        elif action == "recording":
            return await self._control_recording(context, params)
        elif action == "playback":
            return await self._get_playback(context, params)
        else:
            return ToolResult.fail(f"Ação desconhecida: {action}")

    async def _list_cameras(self, context: ToolContext, params: Dict) -> ToolResult:
        """Lista câmeras"""
        cameras = [
            {
                "camera_id": c.camera_id,
                "name": c.name,
                "location": c.location,
                "status": c.status.value,
                "has_ptz": c.has_ptz,
                "is_recording": c.is_recording
            }
            for c in self._cameras.values()
        ]

        return ToolResult.ok({
            "cameras": cameras,
            "total": len(cameras),
            "online": sum(1 for c in self._cameras.values() if c.status in [CameraStatus.ONLINE, CameraStatus.RECORDING])
        })

    async def _get_status(self, context: ToolContext, params: Dict) -> ToolResult:
        """Obtém status da câmera"""
        camera_id = params.get("camera_id")
        if not camera_id:
            return ToolResult.fail("'camera_id' é obrigatório")

        camera = self._cameras.get(camera_id)
        if not camera:
            return ToolResult.fail(f"Câmera não encontrada: {camera_id}")

        return ToolResult.ok({
            "camera_id": camera.camera_id,
            "name": camera.name,
            "location": camera.location,
            "status": camera.status.value,
            "ip_address": camera.ip_address,
            "model": camera.model,
            "resolution": camera.resolution,
            "has_ptz": camera.has_ptz,
            "has_audio": camera.has_audio,
            "is_recording": camera.is_recording
        })

    async def _get_snapshot(self, context: ToolContext, params: Dict) -> ToolResult:
        """Captura snapshot"""
        camera_id = params.get("camera_id")
        if not camera_id:
            return ToolResult.fail("'camera_id' é obrigatório")

        camera = self._cameras.get(camera_id)
        if not camera:
            return ToolResult.fail(f"Câmera não encontrada: {camera_id}")

        if camera.status == CameraStatus.OFFLINE:
            return ToolResult.fail("Câmera offline", error_code="CAMERA_OFFLINE")

        snapshot_id = hashlib.md5(f"{camera_id}{datetime.now()}".encode()).hexdigest()[:12]

        return ToolResult.ok({
            "camera_id": camera_id,
            "snapshot_id": snapshot_id,
            "url": f"/snapshots/{camera_id}/{snapshot_id}.jpg",
            "timestamp": datetime.now().isoformat(),
            "resolution": camera.resolution
        })

    async def _get_stream(self, context: ToolContext, params: Dict) -> ToolResult:
        """Obtém URL de stream"""
        camera_id = params.get("camera_id")
        if not camera_id:
            return ToolResult.fail("'camera_id' é obrigatório")

        camera = self._cameras.get(camera_id)
        if not camera:
            return ToolResult.fail(f"Câmera não encontrada: {camera_id}")

        if camera.status == CameraStatus.OFFLINE:
            return ToolResult.fail("Câmera offline", error_code="CAMERA_OFFLINE")

        stream_token = hashlib.md5(f"{camera_id}{datetime.now()}".encode()).hexdigest()[:16]

        return ToolResult.ok({
            "camera_id": camera_id,
            "rtsp_url": f"rtsp://streaming.local/{camera_id}",
            "hls_url": f"/streams/{camera_id}/index.m3u8?token={stream_token}",
            "webrtc_url": f"wss://streaming.local/webrtc/{camera_id}",
            "expires_at": (datetime.now() + timedelta(hours=1)).isoformat()
        })

    async def _control_ptz(self, context: ToolContext, params: Dict) -> ToolResult:
        """Controla PTZ"""
        camera_id = params.get("camera_id")
        direction = params.get("direction")
        preset = params.get("preset")

        if not camera_id:
            return ToolResult.fail("'camera_id' é obrigatório")

        camera = self._cameras.get(camera_id)
        if not camera:
            return ToolResult.fail(f"Câmera não encontrada: {camera_id}")

        if not camera.has_ptz:
            return ToolResult.fail("Câmera não suporta PTZ", error_code="NO_PTZ")

        if preset:
            return ToolResult.ok({
                "camera_id": camera_id,
                "action": "goto_preset",
                "preset": preset,
                "success": True
            })

        if direction:
            return ToolResult.ok({
                "camera_id": camera_id,
                "action": "move",
                "direction": direction,
                "success": True
            })

        return ToolResult.fail("'direction' ou 'preset' é obrigatório")

    async def _control_recording(self, context: ToolContext, params: Dict) -> ToolResult:
        """Controla gravação"""
        camera_id = params.get("camera_id")
        enable = params.get("enable", True)

        if not camera_id:
            return ToolResult.fail("'camera_id' é obrigatório")

        camera = self._cameras.get(camera_id)
        if not camera:
            return ToolResult.fail(f"Câmera não encontrada: {camera_id}")

        camera.is_recording = enable

        return ToolResult.ok({
            "camera_id": camera_id,
            "recording": enable,
            "success": True
        })

    async def _get_playback(self, context: ToolContext, params: Dict) -> ToolResult:
        """Obtém playback de gravação"""
        camera_id = params.get("camera_id")
        start_time = params.get("start_time")
        end_time = params.get("end_time")

        if not camera_id or not start_time:
            return ToolResult.fail("'camera_id' e 'start_time' são obrigatórios")

        camera = self._cameras.get(camera_id)
        if not camera:
            return ToolResult.fail(f"Câmera não encontrada: {camera_id}")

        playback_token = hashlib.md5(f"{camera_id}{start_time}".encode()).hexdigest()[:16]

        return ToolResult.ok({
            "camera_id": camera_id,
            "playback_url": f"/playback/{camera_id}?token={playback_token}",
            "start_time": start_time,
            "end_time": end_time or datetime.now().isoformat(),
            "format": "mp4"
        })


# ============================================================
# Access Control Tool
# ============================================================

class AccessPointType(Enum):
    """Tipos de ponto de acesso"""
    GATE = "gate"
    DOOR = "door"
    TURNSTILE = "turnstile"
    BARRIER = "barrier"
    ELEVATOR = "elevator"


class AccessStatus(Enum):
    """Status de acesso"""
    GRANTED = "granted"
    DENIED = "denied"
    PENDING = "pending"


@tool(
    name="access_control",
    version="1.0.0",
    category=ToolCategory.DEVICE,
    description="Controle de acesso (portas, catracas, portões)",
    parameters=[
        ToolParameter("action", ParameterType.ENUM, "Ação de acesso",
                     required=True,
                     enum_values=["list", "status", "open", "close", "authorize", "logs"]),
        ToolParameter("point_id", ParameterType.STRING, "ID do ponto de acesso", required=False),
        ToolParameter("credential", ParameterType.STRING, "Credencial (cartão/tag)", required=False),
        ToolParameter("user_id", ParameterType.STRING, "ID do usuário", required=False),
        ToolParameter("duration", ParameterType.INTEGER, "Duração em segundos", required=False, default=5),
    ],
    tags=["access", "door", "gate", "security"],
    required_permissions=["access_control"]
)
class AccessControlTool(BaseTool):
    """
    Ferramenta para controle de acesso.
    Suporta portões, portas, catracas e cancelas.
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self._access_points: Dict[str, Dict] = {
            "ap_001": {
                "id": "ap_001",
                "name": "Portão Principal",
                "type": AccessPointType.GATE.value,
                "location": "Entrada",
                "status": "closed"
            },
            "ap_002": {
                "id": "ap_002",
                "name": "Portão Pedestres",
                "type": AccessPointType.DOOR.value,
                "location": "Entrada",
                "status": "closed"
            },
            "ap_003": {
                "id": "ap_003",
                "name": "Catraca Hall",
                "type": AccessPointType.TURNSTILE.value,
                "location": "Hall",
                "status": "ready"
            }
        }
        self._access_logs: List[Dict] = []

    async def _execute(self, context: ToolContext, **params) -> ToolResult:
        """Executa ação de controle de acesso"""
        action = params.get("action")

        if action == "list":
            return await self._list_points(context, params)
        elif action == "status":
            return await self._get_status(context, params)
        elif action == "open":
            return await self._open_point(context, params)
        elif action == "close":
            return await self._close_point(context, params)
        elif action == "authorize":
            return await self._authorize(context, params)
        elif action == "logs":
            return await self._get_logs(context, params)
        else:
            return ToolResult.fail(f"Ação desconhecida: {action}")

    async def _list_points(self, context: ToolContext, params: Dict) -> ToolResult:
        """Lista pontos de acesso"""
        return ToolResult.ok({
            "access_points": list(self._access_points.values()),
            "total": len(self._access_points)
        })

    async def _get_status(self, context: ToolContext, params: Dict) -> ToolResult:
        """Obtém status do ponto"""
        point_id = params.get("point_id")
        if not point_id:
            return ToolResult.fail("'point_id' é obrigatório")

        point = self._access_points.get(point_id)
        if not point:
            return ToolResult.fail(f"Ponto não encontrado: {point_id}")

        return ToolResult.ok(point)

    async def _open_point(self, context: ToolContext, params: Dict) -> ToolResult:
        """Abre ponto de acesso"""
        point_id = params.get("point_id")
        duration = params.get("duration", 5)
        user_id = params.get("user_id") or context.user_id

        if not point_id:
            return ToolResult.fail("'point_id' é obrigatório")

        point = self._access_points.get(point_id)
        if not point:
            return ToolResult.fail(f"Ponto não encontrado: {point_id}")

        point["status"] = "open"

        # Registrar log
        self._access_logs.append({
            "timestamp": datetime.now().isoformat(),
            "point_id": point_id,
            "action": "open",
            "user_id": user_id,
            "duration": duration
        })

        return ToolResult.ok({
            "point_id": point_id,
            "status": "open",
            "duration": duration,
            "message": f"Ponto {point['name']} aberto por {duration}s"
        })

    async def _close_point(self, context: ToolContext, params: Dict) -> ToolResult:
        """Fecha ponto de acesso"""
        point_id = params.get("point_id")

        if not point_id:
            return ToolResult.fail("'point_id' é obrigatório")

        point = self._access_points.get(point_id)
        if not point:
            return ToolResult.fail(f"Ponto não encontrado: {point_id}")

        point["status"] = "closed"

        return ToolResult.ok({
            "point_id": point_id,
            "status": "closed"
        })

    async def _authorize(self, context: ToolContext, params: Dict) -> ToolResult:
        """Autoriza acesso por credencial"""
        point_id = params.get("point_id")
        credential = params.get("credential")

        if not point_id or not credential:
            return ToolResult.fail("'point_id' e 'credential' são obrigatórios")

        # Simular validação de credencial
        is_valid = len(credential) >= 8

        if is_valid:
            return await self._open_point(context, {
                "point_id": point_id,
                "duration": 5,
                "user_id": credential
            })

        self._access_logs.append({
            "timestamp": datetime.now().isoformat(),
            "point_id": point_id,
            "action": "denied",
            "credential": credential
        })

        return ToolResult.ok({
            "point_id": point_id,
            "status": AccessStatus.DENIED.value,
            "message": "Credencial inválida"
        })

    async def _get_logs(self, context: ToolContext, params: Dict) -> ToolResult:
        """Obtém logs de acesso"""
        point_id = params.get("point_id")
        limit = params.get("limit", 50)

        logs = self._access_logs
        if point_id:
            logs = [l for l in logs if l.get("point_id") == point_id]

        return ToolResult.ok({
            "logs": logs[-limit:],
            "total": len(logs)
        })


# ============================================================
# Alarm Panel Tool
# ============================================================

@tool(
    name="alarm_panel",
    version="1.0.0",
    category=ToolCategory.DEVICE,
    description="Controle de central de alarme",
    parameters=[
        ToolParameter("action", ParameterType.ENUM, "Ação do alarme",
                     required=True,
                     enum_values=["status", "arm", "disarm", "bypass", "zones", "events"]),
        ToolParameter("partition", ParameterType.INTEGER, "Partição", required=False, default=1),
        ToolParameter("mode", ParameterType.ENUM, "Modo de arme",
                     required=False, enum_values=["total", "parcial", "noturno", "away"]),
        ToolParameter("zone_id", ParameterType.INTEGER, "ID da zona", required=False),
        ToolParameter("code", ParameterType.STRING, "Código de acesso", required=False),
    ],
    tags=["alarm", "security", "intrusion"],
    required_permissions=["alarm_control"]
)
class AlarmPanelTool(BaseTool):
    """
    Ferramenta para controle de central de alarme.
    Suporta arme/desarme, bypass e monitoramento.
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self._status = "disarmed"
        self._zones: Dict[int, Dict] = {
            1: {"name": "Sala", "type": "PIR", "status": "ready", "bypassed": False},
            2: {"name": "Cozinha", "type": "PIR", "status": "ready", "bypassed": False},
            3: {"name": "Porta Principal", "type": "magnetic", "status": "closed", "bypassed": False},
            4: {"name": "Janela Sala", "type": "magnetic", "status": "closed", "bypassed": False}
        }
        self._events: List[Dict] = []

    async def _execute(self, context: ToolContext, **params) -> ToolResult:
        """Executa ação no painel de alarme"""
        action = params.get("action")

        if action == "status":
            return await self._get_status(context, params)
        elif action == "arm":
            return await self._arm(context, params)
        elif action == "disarm":
            return await self._disarm(context, params)
        elif action == "bypass":
            return await self._bypass_zone(context, params)
        elif action == "zones":
            return await self._list_zones(context, params)
        elif action == "events":
            return await self._get_events(context, params)
        else:
            return ToolResult.fail(f"Ação desconhecida: {action}")

    async def _get_status(self, context: ToolContext, params: Dict) -> ToolResult:
        """Obtém status do alarme"""
        partition = params.get("partition", 1)

        open_zones = [z for z, info in self._zones.items() if info["status"] == "open"]

        return ToolResult.ok({
            "partition": partition,
            "status": self._status,
            "ready": len(open_zones) == 0,
            "open_zones": open_zones,
            "total_zones": len(self._zones)
        })

    async def _arm(self, context: ToolContext, params: Dict) -> ToolResult:
        """Arma o alarme"""
        mode = params.get("mode", "total")
        code = params.get("code")
        partition = params.get("partition", 1)

        # Verificar código (simulado)
        if code and len(code) < 4:
            return ToolResult.fail("Código inválido", error_code="INVALID_CODE")

        # Verificar zonas abertas
        open_zones = [z for z, info in self._zones.items()
                     if info["status"] == "open" and not info["bypassed"]]

        if open_zones and mode == "total":
            return ToolResult.fail(
                f"Zonas abertas: {open_zones}",
                error_code="ZONES_OPEN"
            )

        self._status = f"armed_{mode}"

        self._events.append({
            "timestamp": datetime.now().isoformat(),
            "type": "arm",
            "mode": mode,
            "partition": partition,
            "user": context.user_id
        })

        return ToolResult.ok({
            "status": self._status,
            "mode": mode,
            "partition": partition,
            "armed_at": datetime.now().isoformat()
        })

    async def _disarm(self, context: ToolContext, params: Dict) -> ToolResult:
        """Desarma o alarme"""
        code = params.get("code")
        partition = params.get("partition", 1)

        if code and len(code) < 4:
            return ToolResult.fail("Código inválido", error_code="INVALID_CODE")

        self._status = "disarmed"

        self._events.append({
            "timestamp": datetime.now().isoformat(),
            "type": "disarm",
            "partition": partition,
            "user": context.user_id
        })

        return ToolResult.ok({
            "status": "disarmed",
            "partition": partition,
            "disarmed_at": datetime.now().isoformat()
        })

    async def _bypass_zone(self, context: ToolContext, params: Dict) -> ToolResult:
        """Bypass de zona"""
        zone_id = params.get("zone_id")

        if not zone_id or zone_id not in self._zones:
            return ToolResult.fail("Zona inválida")

        self._zones[zone_id]["bypassed"] = True

        return ToolResult.ok({
            "zone_id": zone_id,
            "zone_name": self._zones[zone_id]["name"],
            "bypassed": True
        })

    async def _list_zones(self, context: ToolContext, params: Dict) -> ToolResult:
        """Lista zonas"""
        zones = [
            {"zone_id": z, **info}
            for z, info in self._zones.items()
        ]

        return ToolResult.ok({
            "zones": zones,
            "total": len(zones)
        })

    async def _get_events(self, context: ToolContext, params: Dict) -> ToolResult:
        """Obtém eventos"""
        limit = params.get("limit", 50)

        return ToolResult.ok({
            "events": self._events[-limit:],
            "total": len(self._events)
        })


# ============================================================
# Intercom Tool
# ============================================================

@tool(
    name="intercom",
    version="1.0.0",
    category=ToolCategory.DEVICE,
    description="Controle de interfone",
    parameters=[
        ToolParameter("action", ParameterType.ENUM, "Ação do interfone",
                     required=True,
                     enum_values=["call", "answer", "hangup", "transfer", "status"]),
        ToolParameter("unit", ParameterType.STRING, "Unidade destino", required=False),
        ToolParameter("device_id", ParameterType.STRING, "ID do dispositivo", required=False),
    ],
    tags=["intercom", "communication", "voice"]
)
class IntercomTool(BaseTool):
    """Controle de sistema de interfone"""

    async def _execute(self, context: ToolContext, **params) -> ToolResult:
        action = params.get("action")
        unit = params.get("unit")

        if action == "call":
            if not unit:
                return ToolResult.fail("'unit' é obrigatório para chamada")
            return ToolResult.ok({
                "action": "calling",
                "unit": unit,
                "call_id": hashlib.md5(f"{unit}{datetime.now()}".encode()).hexdigest()[:8]
            })

        elif action == "answer":
            return ToolResult.ok({"action": "answered", "status": "connected"})

        elif action == "hangup":
            return ToolResult.ok({"action": "hangup", "status": "disconnected"})

        elif action == "transfer":
            if not unit:
                return ToolResult.fail("'unit' é obrigatório para transferência")
            return ToolResult.ok({"action": "transferred", "to_unit": unit})

        elif action == "status":
            return ToolResult.ok({
                "status": "idle",
                "active_calls": 0,
                "devices_online": 50
            })

        return ToolResult.fail(f"Ação desconhecida: {action}")


# ============================================================
# Sensor Tool
# ============================================================

@tool(
    name="sensor",
    version="1.0.0",
    category=ToolCategory.DEVICE,
    description="Leitura de sensores",
    parameters=[
        ToolParameter("action", ParameterType.ENUM, "Ação",
                     required=True, enum_values=["read", "list", "history", "configure"]),
        ToolParameter("sensor_id", ParameterType.STRING, "ID do sensor", required=False),
        ToolParameter("sensor_type", ParameterType.ENUM, "Tipo do sensor",
                     required=False, enum_values=["temperature", "humidity", "motion", "smoke", "water"]),
    ],
    tags=["sensor", "iot", "monitoring"]
)
class SensorTool(BaseTool):
    """Leitura e monitoramento de sensores"""

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self._sensors = {
            "sensor_001": {"type": "temperature", "location": "Hall", "value": 24.5, "unit": "°C"},
            "sensor_002": {"type": "humidity", "location": "Hall", "value": 65, "unit": "%"},
            "sensor_003": {"type": "motion", "location": "Garagem", "value": False},
            "sensor_004": {"type": "smoke", "location": "Cozinha", "value": False, "alarm": False}
        }

    async def _execute(self, context: ToolContext, **params) -> ToolResult:
        action = params.get("action")
        sensor_id = params.get("sensor_id")
        sensor_type = params.get("sensor_type")

        if action == "read":
            if sensor_id:
                sensor = self._sensors.get(sensor_id)
                if not sensor:
                    return ToolResult.fail(f"Sensor não encontrado: {sensor_id}")
                return ToolResult.ok({"sensor_id": sensor_id, **sensor})

            return ToolResult.ok({
                "sensors": [
                    {"sensor_id": sid, **data}
                    for sid, data in self._sensors.items()
                    if not sensor_type or data.get("type") == sensor_type
                ]
            })

        elif action == "list":
            return ToolResult.ok({
                "sensors": list(self._sensors.keys()),
                "total": len(self._sensors)
            })

        elif action == "history":
            return ToolResult.ok({
                "sensor_id": sensor_id,
                "readings": [
                    {"timestamp": datetime.now().isoformat(), "value": 24.5},
                    {"timestamp": (datetime.now() - timedelta(hours=1)).isoformat(), "value": 24.2}
                ]
            })

        return ToolResult.fail(f"Ação desconhecida: {action}")


# ============================================================
# Gate Tool
# ============================================================

@tool(
    name="gate",
    version="1.0.0",
    category=ToolCategory.DEVICE,
    description="Controle de portões e cancelas",
    parameters=[
        ToolParameter("action", ParameterType.ENUM, "Ação",
                     required=True, enum_values=["open", "close", "stop", "status", "schedule"]),
        ToolParameter("gate_id", ParameterType.STRING, "ID do portão", required=True),
        ToolParameter("duration", ParameterType.INTEGER, "Tempo aberto (segundos)", required=False, default=30),
    ],
    tags=["gate", "barrier", "access"],
    required_permissions=["gate_control"]
)
class GateTool(BaseTool):
    """Controle de portões e cancelas"""

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self._gates = {
            "gate_001": {"name": "Portão Veículos", "status": "closed", "type": "sliding"},
            "gate_002": {"name": "Cancela Entrada", "status": "closed", "type": "barrier"},
            "gate_003": {"name": "Cancela Saída", "status": "closed", "type": "barrier"}
        }

    async def _execute(self, context: ToolContext, **params) -> ToolResult:
        action = params.get("action")
        gate_id = params.get("gate_id")
        duration = params.get("duration", 30)

        if not gate_id:
            return ToolResult.fail("'gate_id' é obrigatório")

        gate = self._gates.get(gate_id)
        if not gate:
            return ToolResult.fail(f"Portão não encontrado: {gate_id}")

        if action == "open":
            gate["status"] = "open"
            return ToolResult.ok({
                "gate_id": gate_id,
                "name": gate["name"],
                "status": "opening",
                "duration": duration
            })

        elif action == "close":
            gate["status"] = "closed"
            return ToolResult.ok({
                "gate_id": gate_id,
                "status": "closing"
            })

        elif action == "stop":
            return ToolResult.ok({
                "gate_id": gate_id,
                "status": "stopped"
            })

        elif action == "status":
            return ToolResult.ok({
                "gate_id": gate_id,
                **gate
            })

        return ToolResult.fail(f"Ação desconhecida: {action}")


def register_device_tools():
    """Registra todas as ferramentas de dispositivos"""
    pass
