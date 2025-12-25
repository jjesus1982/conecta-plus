# WARNING: This file may contain hardcoded secrets. Move to environment variables!
"""
Conecta Plus - Serviço de Hardware
Camada de abstração para comunicação com dispositivos físicos
Suporta: Controle de Acesso, Alarmes, Câmeras, Portões
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

import httpx
import redis.asyncio as redis

from ..config import settings

logger = logging.getLogger(__name__)


# ==================== Enums e Dataclasses ====================

class DeviceType(str, Enum):
    ACCESS_CONTROL = "access_control"
    ALARM_PANEL = "alarm_panel"
    CAMERA = "camera"
    GATE = "gate"
    INTERCOM = "intercom"


class DeviceStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"
    UNKNOWN = "unknown"


class GateCommand(str, Enum):
    OPEN = "open"
    CLOSE = "close"
    STOP = "stop"


class AlarmCommand(str, Enum):
    ARM = "arm"
    DISARM = "disarm"
    BYPASS = "bypass"
    PANIC = "panic"


@dataclass
class Device:
    """Representação de um dispositivo"""
    id: str
    name: str
    type: DeviceType
    ip: str
    port: int
    protocol: str  # http, https, tcp, modbus, etc
    username: Optional[str] = None
    password: Optional[str] = None
    status: DeviceStatus = DeviceStatus.UNKNOWN
    last_seen: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class CommandResult:
    """Resultado de um comando enviado ao dispositivo"""
    success: bool
    message: str
    device_id: str
    command: str
    timestamp: datetime
    response_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# ==================== Base Driver ====================

class DeviceDriver(ABC):
    """Classe base para drivers de dispositivos"""

    def __init__(self, device: Device):
        self.device = device
        self._connected = False

    @abstractmethod
    async def connect(self) -> bool:
        """Conecta ao dispositivo"""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Desconecta do dispositivo"""
        pass

    @abstractmethod
    async def check_status(self) -> DeviceStatus:
        """Verifica status do dispositivo"""
        pass

    @abstractmethod
    async def send_command(self, command: str, params: Dict[str, Any] = None) -> CommandResult:
        """Envia comando ao dispositivo"""
        pass


# ==================== Control ID Driver ====================

class ControlIDDriver(DeviceDriver):
    """
    Driver para controladoras de acesso Control iD
    Modelos: iDAccess, iDFlex, iDBlock
    Protocolo: HTTP REST API
    """

    def __init__(self, device: Device):
        super().__init__(device)
        self.base_url = f"http://{device.ip}:{device.port or 80}"
        self.session_id = None
        self._client: Optional[httpx.AsyncClient] = None

    async def connect(self) -> bool:
        try:
            self._client = httpx.AsyncClient(timeout=10.0)

            # Login na controladora
            response = await self._client.post(
                f"{self.base_url}/login.fcgi",
                json={
                    "login": self.device.username or "admin",
                    "password": self.device.password or "admin"
                }
            )

            if response.status_code == 200:
                data = response.json()
                self.session_id = data.get("session")
                self._connected = True
                self.device.status = DeviceStatus.ONLINE
                logger.info(f"Conectado ao Control iD {self.device.ip}")
                return True

        except Exception as e:
            logger.error(f"Erro ao conectar Control iD {self.device.ip}: {e}")
            self.device.status = DeviceStatus.ERROR

        return False

    async def disconnect(self) -> None:
        if self._client:
            if self.session_id:
                try:
                    await self._client.post(
                        f"{self.base_url}/logout.fcgi",
                        params={"session": self.session_id}
                    )
                except Exception:
                    pass
            await self._client.aclose()
            self._client = None
            self._connected = False

    async def check_status(self) -> DeviceStatus:
        try:
            if not self._client:
                return DeviceStatus.OFFLINE

            response = await self._client.get(
                f"{self.base_url}/system_information.fcgi",
                params={"session": self.session_id}
            )

            if response.status_code == 200:
                self.device.status = DeviceStatus.ONLINE
                self.device.last_seen = datetime.now()
                return DeviceStatus.ONLINE

        except Exception as e:
            logger.warning(f"Control iD {self.device.ip} offline: {e}")
            self.device.status = DeviceStatus.OFFLINE

        return DeviceStatus.OFFLINE

    async def send_command(self, command: str, params: Dict[str, Any] = None) -> CommandResult:
        params = params or {}

        try:
            if command == "open_door":
                # Acionar porta/relé
                door_id = params.get("door_id", 1)
                response = await self._client.post(
                    f"{self.base_url}/execute_actions.fcgi",
                    params={"session": self.session_id},
                    json={
                        "actions": [{
                            "action": "door",
                            "parameters": f"door={door_id}"
                        }]
                    }
                )

                return CommandResult(
                    success=response.status_code == 200,
                    message="Porta acionada" if response.status_code == 200 else "Falha",
                    device_id=self.device.id,
                    command=command,
                    timestamp=datetime.now(),
                    response_data=response.json() if response.status_code == 200 else None
                )

            elif command == "get_users":
                # Listar usuários cadastrados
                response = await self._client.post(
                    f"{self.base_url}/load_objects.fcgi",
                    params={"session": self.session_id},
                    json={"object": "users"}
                )

                return CommandResult(
                    success=response.status_code == 200,
                    message="Usuários carregados",
                    device_id=self.device.id,
                    command=command,
                    timestamp=datetime.now(),
                    response_data=response.json() if response.status_code == 200 else None
                )

            elif command == "add_user":
                # Adicionar usuário
                response = await self._client.post(
                    f"{self.base_url}/create_objects.fcgi",
                    params={"session": self.session_id},
                    json={
                        "object": "users",
                        "values": [{
                            "name": params.get("name"),
                            "registration": params.get("registration"),
                            "password": params.get("password", ""),
                            "salt": "",
                            "begin_time": 0,
                            "end_time": 0
                        }]
                    }
                )

                return CommandResult(
                    success=response.status_code == 200,
                    message="Usuário adicionado",
                    device_id=self.device.id,
                    command=command,
                    timestamp=datetime.now()
                )

            elif command == "get_access_logs":
                # Buscar logs de acesso
                response = await self._client.post(
                    f"{self.base_url}/load_objects.fcgi",
                    params={"session": self.session_id},
                    json={
                        "object": "access_logs",
                        "limit": params.get("limit", 100)
                    }
                )

                return CommandResult(
                    success=response.status_code == 200,
                    message="Logs carregados",
                    device_id=self.device.id,
                    command=command,
                    timestamp=datetime.now(),
                    response_data=response.json() if response.status_code == 200 else None
                )

        except Exception as e:
            return CommandResult(
                success=False,
                message="Erro ao enviar comando",
                device_id=self.device.id,
                command=command,
                timestamp=datetime.now(),
                error=str(e)
            )


# ==================== Intelbras Alarm Driver ====================

class IntelbrasAlarmDriver(DeviceDriver):
    """
    Driver para centrais de alarme Intelbras
    Modelos: AMT 4010, AMT 8000
    Protocolo: Intelbras ISP (porta 9009)
    """

    def __init__(self, device: Device):
        super().__init__(device)
        self.port = device.port or 9009
        self._reader = None
        self._writer = None

    async def connect(self) -> bool:
        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self.device.ip, self.port),
                timeout=10.0
            )

            # Enviar comando de autenticação
            auth_cmd = self._build_auth_command()
            self._writer.write(auth_cmd)
            await self._writer.drain()

            response = await asyncio.wait_for(
                self._reader.read(256),
                timeout=5.0
            )

            if self._parse_response(response).get("success"):
                self._connected = True
                self.device.status = DeviceStatus.ONLINE
                logger.info(f"Conectado à central Intelbras {self.device.ip}")
                return True

        except Exception as e:
            logger.error(f"Erro ao conectar central Intelbras {self.device.ip}: {e}")
            self.device.status = DeviceStatus.ERROR

        return False

    async def disconnect(self) -> None:
        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()
        self._connected = False

    async def check_status(self) -> DeviceStatus:
        try:
            if not self._connected:
                return DeviceStatus.OFFLINE

            # Enviar comando de status
            status_cmd = bytes([0x21, 0x00, 0x00, 0x21])  # Comando simplificado
            self._writer.write(status_cmd)
            await self._writer.drain()

            response = await asyncio.wait_for(
                self._reader.read(256),
                timeout=5.0
            )

            if response:
                self.device.status = DeviceStatus.ONLINE
                self.device.last_seen = datetime.now()
                return DeviceStatus.ONLINE

        except Exception as e:
            logger.warning(f"Central Intelbras {self.device.ip} sem resposta: {e}")
            self.device.status = DeviceStatus.OFFLINE

        return DeviceStatus.OFFLINE

    async def send_command(self, command: str, params: Dict[str, Any] = None) -> CommandResult:
        params = params or {}

        try:
            if command == "arm":
                partition = params.get("partition", 1)
                cmd = self._build_arm_command(partition)
                self._writer.write(cmd)
                await self._writer.drain()

                response = await self._reader.read(256)
                parsed = self._parse_response(response)

                return CommandResult(
                    success=parsed.get("success", False),
                    message="Central armada" if parsed.get("success") else "Falha ao armar",
                    device_id=self.device.id,
                    command=command,
                    timestamp=datetime.now()
                )

            elif command == "disarm":
                partition = params.get("partition", 1)
                password = params.get("password", self.device.password)
                cmd = self._build_disarm_command(partition, password)
                self._writer.write(cmd)
                await self._writer.drain()

                response = await self._reader.read(256)
                parsed = self._parse_response(response)

                return CommandResult(
                    success=parsed.get("success", False),
                    message="Central desarmada" if parsed.get("success") else "Falha ao desarmar",
                    device_id=self.device.id,
                    command=command,
                    timestamp=datetime.now()
                )

            elif command == "get_zones":
                cmd = self._build_zones_status_command()
                self._writer.write(cmd)
                await self._writer.drain()

                response = await self._reader.read(1024)
                zones = self._parse_zones_response(response)

                return CommandResult(
                    success=True,
                    message="Status das zonas",
                    device_id=self.device.id,
                    command=command,
                    timestamp=datetime.now(),
                    response_data={"zones": zones}
                )

            elif command == "bypass":
                zone = params.get("zone")
                cmd = self._build_bypass_command(zone)
                self._writer.write(cmd)
                await self._writer.drain()

                response = await self._reader.read(256)
                parsed = self._parse_response(response)

                return CommandResult(
                    success=parsed.get("success", False),
                    message=f"Zona {zone} em bypass",
                    device_id=self.device.id,
                    command=command,
                    timestamp=datetime.now()
                )

        except Exception as e:
            return CommandResult(
                success=False,
                message="Erro ao enviar comando",
                device_id=self.device.id,
                command=command,
                timestamp=datetime.now(),
                error=str(e)
            )

    def _build_auth_command(self) -> bytes:
        """Constrói comando de autenticação"""
        password = self.device.password or "1234"
        # Formato simplificado - ajustar conforme protocolo real
        cmd = bytes([0x40]) + password.encode() + bytes([0x00])
        checksum = sum(cmd) & 0xFF
        return cmd + bytes([checksum])

    def _build_arm_command(self, partition: int) -> bytes:
        """Constrói comando de armar"""
        return bytes([0x41, partition, 0x00, 0x41 + partition])

    def _build_disarm_command(self, partition: int, password: str) -> bytes:
        """Constrói comando de desarmar"""
        cmd = bytes([0x42, partition]) + password.encode()
        checksum = sum(cmd) & 0xFF
        return cmd + bytes([checksum])

    def _build_zones_status_command(self) -> bytes:
        """Constrói comando para status das zonas"""
        return bytes([0x50, 0x00, 0x00, 0x50])

    def _build_bypass_command(self, zone: int) -> bytes:
        """Constrói comando de bypass"""
        return bytes([0x43, zone, 0x00, 0x43 + zone])

    def _parse_response(self, response: bytes) -> Dict[str, Any]:
        """Parse da resposta da central"""
        if not response:
            return {"success": False}
        # Resposta ACK = 0x06
        return {"success": response[0] == 0x06 if response else False}

    def _parse_zones_response(self, response: bytes) -> List[Dict]:
        """Parse do status das zonas"""
        zones = []
        # Simplificado - implementar parse real do protocolo
        for i in range(1, 17):
            zones.append({
                "zone": i,
                "name": f"Zona {i}",
                "status": "normal",
                "bypassed": False
            })
        return zones


# ==================== ONVIF Camera Driver ====================

class ONVIFCameraDriver(DeviceDriver):
    """
    Driver para câmeras IP via protocolo ONVIF
    Suporta: Hikvision, Dahua, Intelbras, Axis, etc
    """

    def __init__(self, device: Device):
        super().__init__(device)
        self.base_url = f"http://{device.ip}:{device.port or 80}"
        self._client: Optional[httpx.AsyncClient] = None
        self.onvif_port = 80
        self.media_profile = None

    async def connect(self) -> bool:
        try:
            self._client = httpx.AsyncClient(
                timeout=10.0,
                auth=(self.device.username or "admin", self.device.password or "admin")
            )

            # Testar conectividade via GetCapabilities
            capabilities_xml = self._build_get_capabilities_request()
            response = await self._client.post(
                f"{self.base_url}/onvif/device_service",
                content=capabilities_xml,
                headers={"Content-Type": "application/soap+xml"}
            )

            if response.status_code == 200:
                self._connected = True
                self.device.status = DeviceStatus.ONLINE
                logger.info(f"Conectado à câmera ONVIF {self.device.ip}")
                return True

        except Exception as e:
            logger.error(f"Erro ao conectar câmera ONVIF {self.device.ip}: {e}")
            self.device.status = DeviceStatus.ERROR

        return False

    async def disconnect(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
            self._connected = False

    async def check_status(self) -> DeviceStatus:
        try:
            if not self._client:
                return DeviceStatus.OFFLINE

            # GetSystemDateAndTime é um comando simples para verificar status
            request_xml = self._build_get_system_datetime_request()
            response = await self._client.post(
                f"{self.base_url}/onvif/device_service",
                content=request_xml,
                headers={"Content-Type": "application/soap+xml"},
                timeout=5.0
            )

            if response.status_code == 200:
                self.device.status = DeviceStatus.ONLINE
                self.device.last_seen = datetime.now()
                return DeviceStatus.ONLINE

        except Exception as e:
            logger.warning(f"Câmera ONVIF {self.device.ip} sem resposta: {e}")
            self.device.status = DeviceStatus.OFFLINE

        return DeviceStatus.OFFLINE

    async def send_command(self, command: str, params: Dict[str, Any] = None) -> CommandResult:
        params = params or {}

        try:
            if command == "get_snapshot":
                # Capturar snapshot
                snapshot_uri = await self._get_snapshot_uri()
                if snapshot_uri:
                    response = await self._client.get(snapshot_uri)
                    if response.status_code == 200:
                        return CommandResult(
                            success=True,
                            message="Snapshot capturado",
                            device_id=self.device.id,
                            command=command,
                            timestamp=datetime.now(),
                            response_data={
                                "content_type": response.headers.get("content-type"),
                                "size": len(response.content)
                            }
                        )

            elif command == "get_stream_uri":
                # Obter URI do stream RTSP
                stream_uri = await self._get_stream_uri(params.get("profile", "main"))
                return CommandResult(
                    success=stream_uri is not None,
                    message="Stream URI obtido" if stream_uri else "Falha",
                    device_id=self.device.id,
                    command=command,
                    timestamp=datetime.now(),
                    response_data={"stream_uri": stream_uri}
                )

            elif command == "ptz_move":
                # Controle PTZ
                direction = params.get("direction", "stop")  # up, down, left, right, zoom_in, zoom_out
                speed = params.get("speed", 0.5)
                result = await self._ptz_continuous_move(direction, speed)
                return CommandResult(
                    success=result,
                    message=f"PTZ {direction}",
                    device_id=self.device.id,
                    command=command,
                    timestamp=datetime.now()
                )

            elif command == "ptz_stop":
                result = await self._ptz_stop()
                return CommandResult(
                    success=result,
                    message="PTZ parado",
                    device_id=self.device.id,
                    command=command,
                    timestamp=datetime.now()
                )

            elif command == "ptz_preset":
                # Ir para preset ou salvar preset
                preset_token = params.get("preset", "1")
                action = params.get("action", "goto")  # goto, set
                if action == "goto":
                    result = await self._ptz_goto_preset(preset_token)
                else:
                    result = await self._ptz_set_preset(preset_token)
                return CommandResult(
                    success=result,
                    message=f"Preset {action} {preset_token}",
                    device_id=self.device.id,
                    command=command,
                    timestamp=datetime.now()
                )

            elif command == "get_device_info":
                # Informações do dispositivo
                info = await self._get_device_information()
                return CommandResult(
                    success=info is not None,
                    message="Informações obtidas",
                    device_id=self.device.id,
                    command=command,
                    timestamp=datetime.now(),
                    response_data=info
                )

        except Exception as e:
            return CommandResult(
                success=False,
                message="Erro ao enviar comando",
                device_id=self.device.id,
                command=command,
                timestamp=datetime.now(),
                error=str(e)
            )

    def _build_soap_envelope(self, body: str) -> str:
        """Constrói envelope SOAP"""
        return f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope"
               xmlns:tds="http://www.onvif.org/ver10/device/wsdl"
               xmlns:trt="http://www.onvif.org/ver10/media/wsdl"
               xmlns:tptz="http://www.onvif.org/ver20/ptz/wsdl">
    <soap:Body>
        {body}
    </soap:Body>
</soap:Envelope>"""

    def _build_get_capabilities_request(self) -> str:
        return self._build_soap_envelope("<tds:GetCapabilities><tds:Category>All</tds:Category></tds:GetCapabilities>")

    def _build_get_system_datetime_request(self) -> str:
        return self._build_soap_envelope("<tds:GetSystemDateAndTime/>")

    async def _get_snapshot_uri(self) -> Optional[str]:
        """Obtém URI do snapshot"""
        request = self._build_soap_envelope("<trt:GetSnapshotUri><trt:ProfileToken>Profile_1</trt:ProfileToken></trt:GetSnapshotUri>")
        try:
            response = await self._client.post(
                f"{self.base_url}/onvif/media_service",
                content=request,
                headers={"Content-Type": "application/soap+xml"}
            )
            if response.status_code == 200:
                # Parse XML response
                import re
                match = re.search(r'<tt:Uri>([^<]+)</tt:Uri>', response.text)
                if match:
                    return match.group(1)
        except Exception as e:
            logger.error(f"Erro ao obter snapshot URI: {e}")
        return None

    async def _get_stream_uri(self, profile: str = "main") -> Optional[str]:
        """Obtém URI do stream RTSP"""
        profile_token = "Profile_1" if profile == "main" else "Profile_2"
        request = self._build_soap_envelope(f"""
            <trt:GetStreamUri>
                <trt:StreamSetup>
                    <tt:Stream xmlns:tt="http://www.onvif.org/ver10/schema">RTP-Unicast</tt:Stream>
                    <tt:Transport xmlns:tt="http://www.onvif.org/ver10/schema">
                        <tt:Protocol>RTSP</tt:Protocol>
                    </tt:Transport>
                </trt:StreamSetup>
                <trt:ProfileToken>{profile_token}</trt:ProfileToken>
            </trt:GetStreamUri>
        """)
        try:
            response = await self._client.post(
                f"{self.base_url}/onvif/media_service",
                content=request,
                headers={"Content-Type": "application/soap+xml"}
            )
            if response.status_code == 200:
                import re
                match = re.search(r'<tt:Uri>([^<]+)</tt:Uri>', response.text)
                if match:
                    return match.group(1)
        except Exception as e:
            logger.error(f"Erro ao obter stream URI: {e}")
        return None

    async def _ptz_continuous_move(self, direction: str, speed: float) -> bool:
        """Movimento contínuo PTZ"""
        velocity_map = {
            "up": (0, speed, 0),
            "down": (0, -speed, 0),
            "left": (-speed, 0, 0),
            "right": (speed, 0, 0),
            "zoom_in": (0, 0, speed),
            "zoom_out": (0, 0, -speed),
        }
        x, y, z = velocity_map.get(direction, (0, 0, 0))

        request = self._build_soap_envelope(f"""
            <tptz:ContinuousMove>
                <tptz:ProfileToken>Profile_1</tptz:ProfileToken>
                <tptz:Velocity>
                    <tt:PanTilt xmlns:tt="http://www.onvif.org/ver10/schema" x="{x}" y="{y}"/>
                    <tt:Zoom xmlns:tt="http://www.onvif.org/ver10/schema" x="{z}"/>
                </tptz:Velocity>
            </tptz:ContinuousMove>
        """)
        try:
            response = await self._client.post(
                f"{self.base_url}/onvif/ptz_service",
                content=request,
                headers={"Content-Type": "application/soap+xml"}
            )
            return response.status_code == 200
        except Exception:
            return False

    async def _ptz_stop(self) -> bool:
        """Para movimento PTZ"""
        request = self._build_soap_envelope("""
            <tptz:Stop>
                <tptz:ProfileToken>Profile_1</tptz:ProfileToken>
                <tptz:PanTilt>true</tptz:PanTilt>
                <tptz:Zoom>true</tptz:Zoom>
            </tptz:Stop>
        """)
        try:
            response = await self._client.post(
                f"{self.base_url}/onvif/ptz_service",
                content=request,
                headers={"Content-Type": "application/soap+xml"}
            )
            return response.status_code == 200
        except Exception:
            return False

    async def _ptz_goto_preset(self, preset_token: str) -> bool:
        """Vai para um preset PTZ"""
        request = self._build_soap_envelope(f"""
            <tptz:GotoPreset>
                <tptz:ProfileToken>Profile_1</tptz:ProfileToken>
                <tptz:PresetToken>{preset_token}</tptz:PresetToken>
            </tptz:GotoPreset>
        """)
        try:
            response = await self._client.post(
                f"{self.base_url}/onvif/ptz_service",
                content=request,
                headers={"Content-Type": "application/soap+xml"}
            )
            return response.status_code == 200
        except Exception:
            return False

    async def _ptz_set_preset(self, preset_token: str) -> bool:
        """Salva posição atual como preset"""
        request = self._build_soap_envelope(f"""
            <tptz:SetPreset>
                <tptz:ProfileToken>Profile_1</tptz:ProfileToken>
                <tptz:PresetToken>{preset_token}</tptz:PresetToken>
            </tptz:SetPreset>
        """)
        try:
            response = await self._client.post(
                f"{self.base_url}/onvif/ptz_service",
                content=request,
                headers={"Content-Type": "application/soap+xml"}
            )
            return response.status_code == 200
        except Exception:
            return False

    async def _get_device_information(self) -> Optional[Dict[str, Any]]:
        """Obtém informações do dispositivo"""
        request = self._build_soap_envelope("<tds:GetDeviceInformation/>")
        try:
            response = await self._client.post(
                f"{self.base_url}/onvif/device_service",
                content=request,
                headers={"Content-Type": "application/soap+xml"}
            )
            if response.status_code == 200:
                import re
                info = {}
                patterns = {
                    "manufacturer": r"<tds:Manufacturer>([^<]+)</tds:Manufacturer>",
                    "model": r"<tds:Model>([^<]+)</tds:Model>",
                    "firmware_version": r"<tds:FirmwareVersion>([^<]+)</tds:FirmwareVersion>",
                    "serial_number": r"<tds:SerialNumber>([^<]+)</tds:SerialNumber>",
                    "hardware_id": r"<tds:HardwareId>([^<]+)</tds:HardwareId>",
                }
                for key, pattern in patterns.items():
                    match = re.search(pattern, response.text)
                    if match:
                        info[key] = match.group(1)
                return info
        except Exception as e:
            logger.error(f"Erro ao obter informações do dispositivo: {e}")
        return None


# ==================== Gate Driver (PPA/Garen/Nice) ====================

class GateDriver(DeviceDriver):
    """
    Driver para automatizadores de portão
    Suporta: PPA, Garen, Nice via interface de relé/HTTP
    """

    def __init__(self, device: Device):
        super().__init__(device)
        self.base_url = f"http://{device.ip}:{device.port or 80}"
        self._client: Optional[httpx.AsyncClient] = None

    async def connect(self) -> bool:
        try:
            self._client = httpx.AsyncClient(timeout=5.0)

            # Testar conexão
            response = await self._client.get(f"{self.base_url}/status")
            if response.status_code == 200:
                self._connected = True
                self.device.status = DeviceStatus.ONLINE
                return True

        except Exception as e:
            logger.error(f"Erro ao conectar portão {self.device.ip}: {e}")
            self.device.status = DeviceStatus.ERROR

        return False

    async def disconnect(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
            self._connected = False

    async def check_status(self) -> DeviceStatus:
        try:
            if not self._client:
                return DeviceStatus.OFFLINE

            response = await self._client.get(f"{self.base_url}/status")
            if response.status_code == 200:
                self.device.status = DeviceStatus.ONLINE
                self.device.last_seen = datetime.now()
                return DeviceStatus.ONLINE

        except Exception:
            self.device.status = DeviceStatus.OFFLINE

        return DeviceStatus.OFFLINE

    async def send_command(self, command: str, params: Dict[str, Any] = None) -> CommandResult:
        try:
            if command in ["open", "close", "stop"]:
                response = await self._client.post(
                    f"{self.base_url}/command",
                    json={"action": command}
                )

                return CommandResult(
                    success=response.status_code == 200,
                    message=f"Portão: {command}",
                    device_id=self.device.id,
                    command=command,
                    timestamp=datetime.now()
                )

            elif command == "pulse":
                # Pulso no relé (abrir e fechar)
                duration = params.get("duration", 1000) if params else 1000
                response = await self._client.post(
                    f"{self.base_url}/pulse",
                    json={"duration": duration}
                )

                return CommandResult(
                    success=response.status_code == 200,
                    message="Pulso enviado",
                    device_id=self.device.id,
                    command=command,
                    timestamp=datetime.now()
                )

        except Exception as e:
            return CommandResult(
                success=False,
                message="Erro ao enviar comando",
                device_id=self.device.id,
                command=command,
                timestamp=datetime.now(),
                error=str(e)
            )


# ==================== Hardware Manager ====================

class HardwareManager:
    """
    Gerenciador centralizado de dispositivos de hardware
    Mantém conexões, status e envia comandos
    """

    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or settings.REDIS_URL
        self._devices: Dict[str, Device] = {}
        self._drivers: Dict[str, DeviceDriver] = {}
        self._redis: Optional[redis.Redis] = None
        self._running = False

    async def initialize(self):
        """Inicializa o gerenciador"""
        try:
            self._redis = await redis.from_url(self.redis_url)
            await self._load_devices_from_cache()
            self._running = True
            # Iniciar loop de monitoramento
            asyncio.create_task(self._monitoring_loop())
            logger.info("HardwareManager inicializado")
        except Exception as e:
            logger.error(f"Erro ao inicializar HardwareManager: {e}")

    async def shutdown(self):
        """Encerra o gerenciador"""
        self._running = False
        for driver in self._drivers.values():
            await driver.disconnect()
        if self._redis:
            await self._redis.close()

    async def register_device(self, device: Device) -> bool:
        """Registra um novo dispositivo"""
        self._devices[device.id] = device

        # Criar driver apropriado
        driver = self._create_driver(device)
        if driver:
            self._drivers[device.id] = driver
            # Conectar
            connected = await driver.connect()
            # Salvar no cache
            await self._save_device_to_cache(device)
            return connected

        return False

    def _create_driver(self, device: Device) -> Optional[DeviceDriver]:
        """Cria driver baseado no tipo de dispositivo"""
        if device.type == DeviceType.ACCESS_CONTROL:
            if "control" in device.protocol.lower():
                return ControlIDDriver(device)
        elif device.type == DeviceType.ALARM_PANEL:
            if "intelbras" in device.protocol.lower():
                return IntelbrasAlarmDriver(device)
        elif device.type == DeviceType.GATE:
            return GateDriver(device)
        elif device.type == DeviceType.CAMERA:
            if "onvif" in device.protocol.lower():
                return ONVIFCameraDriver(device)

        return None

    async def send_command(
        self,
        device_id: str,
        command: str,
        params: Dict[str, Any] = None
    ) -> CommandResult:
        """Envia comando para um dispositivo"""
        driver = self._drivers.get(device_id)
        if not driver:
            return CommandResult(
                success=False,
                message="Dispositivo não encontrado",
                device_id=device_id,
                command=command,
                timestamp=datetime.now(),
                error="Device not registered"
            )

        result = await driver.send_command(command, params)

        # Log do comando
        if self._redis:
            log_entry = {
                "device_id": device_id,
                "command": command,
                "success": result.success,
                "timestamp": result.timestamp.isoformat()
            }
            await self._redis.lpush("hardware:command_log", str(log_entry))
            await self._redis.ltrim("hardware:command_log", 0, 999)

        return result

    async def get_device_status(self, device_id: str) -> DeviceStatus:
        """Obtém status de um dispositivo"""
        driver = self._drivers.get(device_id)
        if driver:
            return await driver.check_status()
        return DeviceStatus.UNKNOWN

    async def get_all_devices(self) -> List[Device]:
        """Retorna todos os dispositivos registrados"""
        return list(self._devices.values())

    async def _monitoring_loop(self):
        """Loop de monitoramento de dispositivos"""
        while self._running:
            for device_id, driver in self._drivers.items():
                try:
                    status = await driver.check_status()
                    self._devices[device_id].status = status
                    self._devices[device_id].last_seen = datetime.now()
                except Exception as e:
                    logger.warning(f"Erro ao verificar {device_id}: {e}")

            await asyncio.sleep(30)  # Verificar a cada 30 segundos

    async def _load_devices_from_cache(self):
        """Carrega dispositivos do cache Redis"""
        if not self._redis:
            return

        try:
            devices_data = await self._redis.hgetall("hardware:devices")
            for device_id, device_json in devices_data.items():
                import json
                device_dict = json.loads(device_json)
                device = Device(**device_dict)
                await self.register_device(device)
        except Exception as e:
            logger.warning(f"Erro ao carregar cache: {e}")

    async def _save_device_to_cache(self, device: Device):
        """Salva dispositivo no cache Redis"""
        if not self._redis:
            return

        import json
        device_dict = {
            "id": device.id,
            "name": device.name,
            "type": device.type.value,
            "ip": device.ip,
            "port": device.port,
            "protocol": device.protocol,
            "username": device.username,
            "password": device.password
        }
        await self._redis.hset("hardware:devices", device.id, json.dumps(device_dict))


# Instância global
hardware_manager = HardwareManager()


async def get_hardware_manager() -> HardwareManager:
    """Obtém o gerenciador de hardware"""
    if not hardware_manager._running:
        await hardware_manager.initialize()
    return hardware_manager
