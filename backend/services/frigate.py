"""
Conecta Plus - Serviço de Integração Frigate NVR
Frigate é um NVR open-source com detecção de objetos em tempo real
https://frigate.video/
Com Circuit Breaker para resiliência
"""

import httpx
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

from ..config import settings
from .resilience import get_circuit_breaker, CircuitBreakerConfig, CircuitBreakerError
from .observability import logger


class ObjectLabel(str, Enum):
    """Labels de objetos detectáveis pelo Frigate"""
    PERSON = "person"
    CAR = "car"
    MOTORCYCLE = "motorcycle"
    BICYCLE = "bicycle"
    DOG = "dog"
    CAT = "cat"
    BIRD = "bird"
    TRUCK = "truck"
    BUS = "bus"


@dataclass
class FrigateInstance:
    """Configuração de uma instância Frigate"""
    id: str
    name: str
    url: str
    api_key: Optional[str] = None
    mqtt_enabled: bool = False
    mqtt_host: Optional[str] = None
    mqtt_topic_prefix: str = "frigate"


@dataclass
class FrigateCamera:
    """Informações de uma câmera no Frigate"""
    name: str
    enabled: bool = True
    detect_enabled: bool = True
    record_enabled: bool = False
    snapshots_enabled: bool = False
    motion_enabled: bool = True
    width: int = 1920
    height: int = 1080
    fps: int = 5


@dataclass
class FrigateEvent:
    """Evento de detecção do Frigate"""
    id: str
    camera: str
    label: str
    sub_label: Optional[str] = None
    score: float = 0.0
    top_score: float = 0.0
    start_time: float = 0.0
    end_time: Optional[float] = None
    has_clip: bool = False
    has_snapshot: bool = False
    zones: List[str] = field(default_factory=list)
    thumbnail: Optional[str] = None
    retain_indefinitely: bool = False


@dataclass
class FrigateRecording:
    """Gravação do Frigate"""
    id: str
    camera: str
    start_time: float
    end_time: float
    duration: float
    motion: float
    objects: float


class FrigateService:
    """Serviço para integração com Frigate NVR com Circuit Breaker"""

    # Configuração do Circuit Breaker para Frigate
    FRIGATE_CB_CONFIG = CircuitBreakerConfig(
        failure_threshold=5,
        success_threshold=2,
        timeout=30.0,
        reset_timeout=30.0,
        half_open_max_calls=3
    )

    def __init__(self, instance: FrigateInstance):
        self.instance = instance
        self.base_url = instance.url.rstrip('/')
        self._client: Optional[httpx.AsyncClient] = None
        # Circuit breaker por instância
        self._circuit = get_circuit_breaker(
            f"frigate-{instance.id}",
            self.FRIGATE_CB_CONFIG
        )

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            headers = {}
            if self.instance.api_key:
                headers["Authorization"] = f"Bearer {self.instance.api_key}"
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=30.0
            )
        return self._client

    @property
    def circuit_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do circuit breaker."""
        return self._circuit.stats

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _request(self, method: str, endpoint: str, **kwargs) -> Any:
        """
        Faz requisição à API do Frigate protegida por Circuit Breaker.
        """
        async def do_request():
            response = await self.client.request(method, f"/api{endpoint}", **kwargs)
            response.raise_for_status()
            return response.json() if response.content else None

        try:
            return await self._circuit.execute(do_request)
        except CircuitBreakerError as e:
            logger.warning(
                f"Frigate circuit breaker open",
                instance=self.instance.id,
                state=e.state.value
            )
            raise

    # === System ===

    async def get_version(self) -> str:
        """Obtém versão do Frigate"""
        return await self._request("GET", "/version")

    async def get_stats(self) -> Dict[str, Any]:
        """Obtém estatísticas do sistema"""
        return await self._request("GET", "/stats")

    async def get_config(self) -> Dict[str, Any]:
        """Obtém configuração completa"""
        return await self._request("GET", "/config")

    async def restart(self) -> bool:
        """Reinicia o Frigate"""
        await self._request("POST", "/restart")
        return True

    # === Cameras ===

    async def list_cameras(self) -> List[FrigateCamera]:
        """Lista todas as câmeras"""
        config = await self.get_config()
        cameras = []

        for name, cam_config in config.get("cameras", {}).items():
            cameras.append(FrigateCamera(
                name=name,
                enabled=cam_config.get("enabled", True),
                detect_enabled=cam_config.get("detect", {}).get("enabled", True),
                record_enabled=cam_config.get("record", {}).get("enabled", False),
                snapshots_enabled=cam_config.get("snapshots", {}).get("enabled", False),
                motion_enabled=cam_config.get("motion", {}).get("enabled", True),
                width=cam_config.get("detect", {}).get("width", 1920),
                height=cam_config.get("detect", {}).get("height", 1080),
                fps=cam_config.get("detect", {}).get("fps", 5),
            ))

        return cameras

    async def get_camera_snapshot(
        self,
        camera: str,
        timestamp: Optional[float] = None,
        bbox: bool = False,
        height: int = 720
    ) -> str:
        """Obtém URL do snapshot de uma câmera"""
        params = []
        if timestamp:
            params.append(f"timestamp={timestamp}")
        if bbox:
            params.append("bbox=1")
        params.append(f"h={height}")

        query = "&".join(params)
        return f"{self.base_url}/api/{camera}/latest.jpg?{query}"

    async def toggle_detection(self, camera: str, enabled: bool) -> bool:
        """Ativa/desativa detecção"""
        state = "ON" if enabled else "OFF"
        await self._request("POST", f"/{camera}/detect/{state}")
        return True

    async def toggle_recording(self, camera: str, enabled: bool) -> bool:
        """Ativa/desativa gravação"""
        state = "ON" if enabled else "OFF"
        await self._request("POST", f"/{camera}/recordings/{state}")
        return True

    async def toggle_snapshots(self, camera: str, enabled: bool) -> bool:
        """Ativa/desativa snapshots"""
        state = "ON" if enabled else "OFF"
        await self._request("POST", f"/{camera}/snapshots/{state}")
        return True

    async def toggle_motion(self, camera: str, enabled: bool) -> bool:
        """Ativa/desativa detecção de movimento"""
        state = "ON" if enabled else "OFF"
        await self._request("POST", f"/{camera}/motion/{state}")
        return True

    # === Events ===

    async def get_events(
        self,
        camera: Optional[str] = None,
        label: Optional[str] = None,
        zone: Optional[str] = None,
        after: Optional[float] = None,
        before: Optional[float] = None,
        has_clip: Optional[bool] = None,
        has_snapshot: Optional[bool] = None,
        min_score: Optional[float] = None,
        limit: int = 50
    ) -> List[FrigateEvent]:
        """Busca eventos de detecção"""
        params = {"limit": limit}

        if camera:
            params["camera"] = camera
        if label:
            params["label"] = label
        if zone:
            params["zone"] = zone
        if after:
            params["after"] = after
        if before:
            params["before"] = before
        if has_clip is not None:
            params["has_clip"] = 1 if has_clip else 0
        if has_snapshot is not None:
            params["has_snapshot"] = 1 if has_snapshot else 0
        if min_score:
            params["min_score"] = min_score

        events_data = await self._request("GET", "/events", params=params)

        events = []
        for e in events_data:
            events.append(FrigateEvent(
                id=e["id"],
                camera=e["camera"],
                label=e["label"],
                sub_label=e.get("sub_label"),
                score=e.get("score", 0),
                top_score=e.get("top_score", 0),
                start_time=e["start_time"],
                end_time=e.get("end_time"),
                has_clip=e.get("has_clip", False),
                has_snapshot=e.get("has_snapshot", False),
                zones=e.get("zones", []),
                retain_indefinitely=e.get("retain_indefinitely", False),
            ))

        return events

    async def get_event(self, event_id: str) -> FrigateEvent:
        """Obtém detalhes de um evento"""
        e = await self._request("GET", f"/events/{event_id}")
        return FrigateEvent(
            id=e["id"],
            camera=e["camera"],
            label=e["label"],
            sub_label=e.get("sub_label"),
            score=e.get("score", 0),
            top_score=e.get("top_score", 0),
            start_time=e["start_time"],
            end_time=e.get("end_time"),
            has_clip=e.get("has_clip", False),
            has_snapshot=e.get("has_snapshot", False),
            zones=e.get("zones", []),
            retain_indefinitely=e.get("retain_indefinitely", False),
        )

    def get_event_clip_url(self, event_id: str) -> str:
        """Obtém URL do clipe de um evento"""
        return f"{self.base_url}/api/events/{event_id}/clip.mp4"

    def get_event_thumbnail_url(self, event_id: str) -> str:
        """Obtém URL do thumbnail de um evento"""
        return f"{self.base_url}/api/events/{event_id}/thumbnail.jpg"

    def get_event_snapshot_url(self, event_id: str) -> str:
        """Obtém URL do snapshot de um evento"""
        return f"{self.base_url}/api/events/{event_id}/snapshot.jpg"

    async def delete_event(self, event_id: str) -> bool:
        """Deleta um evento"""
        await self._request("DELETE", f"/events/{event_id}")
        return True

    async def retain_event(self, event_id: str, retain: bool = True) -> bool:
        """Marca evento para retenção"""
        await self._request("POST", f"/events/{event_id}/retain", json={"retain": retain})
        return True

    async def set_sub_label(self, event_id: str, sub_label: str) -> bool:
        """Define sub-label para um evento (ex: nome da pessoa)"""
        await self._request("POST", f"/events/{event_id}/sub_label", json={"subLabel": sub_label})
        return True

    # === Recordings ===

    async def get_recordings(
        self,
        camera: str,
        after: Optional[float] = None,
        before: Optional[float] = None
    ) -> List[FrigateRecording]:
        """Lista gravações de uma câmera"""
        params = {}
        if after:
            params["after"] = after
        if before:
            params["before"] = before

        recordings_data = await self._request("GET", f"/{camera}/recordings", params=params)

        recordings = []
        for r in recordings_data:
            recordings.append(FrigateRecording(
                id=r.get("id", ""),
                camera=camera,
                start_time=r["start_time"],
                end_time=r["end_time"],
                duration=r.get("duration", 0),
                motion=r.get("motion", 0),
                objects=r.get("objects", 0),
            ))

        return recordings

    async def get_recording_summary(
        self,
        camera: str,
        timezone: str = "America/Sao_Paulo"
    ) -> Dict[str, Any]:
        """Obtém resumo de gravações por hora/dia"""
        return await self._request("GET", f"/{camera}/recordings/summary", params={"timezone": timezone})

    async def export_recording(
        self,
        camera: str,
        start_time: float,
        end_time: float,
        playback_factor: float = 1.0
    ) -> Dict[str, Any]:
        """Exporta gravação para download"""
        return await self._request(
            "POST",
            f"/export/{camera}/start/{start_time}/end/{end_time}",
            json={"playback": playback_factor}
        )

    def get_recording_url(self, camera: str, start_time: float, end_time: float) -> str:
        """Obtém URL para playback de gravação"""
        return f"{self.base_url}/vod/{camera}/start/{start_time}/end/{end_time}/index.m3u8"

    # === Streaming ===

    def get_stream_url(self, camera: str, stream_type: str = "hls") -> str:
        """Obtém URL de streaming"""
        if stream_type == "rtsp":
            # RTSP via go2rtc
            host = self.base_url.replace("http://", "").replace("https://", "").split(":")[0]
            return f"rtsp://{host}:8554/{camera}"
        elif stream_type == "hls":
            return f"{self.base_url}/api/{camera}/stream.m3u8"
        elif stream_type == "webrtc":
            return f"{self.base_url}/live/webrtc/api/ws?src={camera}"
        elif stream_type == "mse":
            return f"{self.base_url}/live/mse/api/ws?src={camera}"
        else:
            return f"{self.base_url}/api/{camera}/stream.m3u8"

    # === PTZ ===

    async def ptz_move(
        self,
        camera: str,
        action: str,
        speed: float = 0.5
    ) -> bool:
        """Controle PTZ"""
        await self._request("POST", f"/{camera}/ptz/{action}", params={"speed": speed})
        return True

    async def ptz_preset(self, camera: str, preset: str) -> bool:
        """Vai para preset PTZ"""
        await self._request("POST", f"/{camera}/ptz/preset", params={"preset": preset})
        return True

    # === Reviews ===

    async def get_reviews(
        self,
        camera: Optional[str] = None,
        label: Optional[str] = None,
        reviewed: bool = False,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Obtém itens para revisão"""
        params = {"limit": limit, "reviewed": 1 if reviewed else 0}
        if camera:
            params["camera"] = camera
        if label:
            params["label"] = label

        return await self._request("GET", "/review", params=params)

    async def mark_reviewed(self, review_id: str) -> bool:
        """Marca item como revisado"""
        await self._request("POST", f"/review/{review_id}/viewed")
        return True

    # === Zones ===

    async def get_zones(self, camera: str) -> List[str]:
        """Lista zonas de uma câmera"""
        config = await self.get_config()
        camera_config = config.get("cameras", {}).get(camera, {})
        return list(camera_config.get("zones", {}).keys())

    # === Timeline ===

    async def get_timeline(
        self,
        camera: Optional[str] = None,
        source_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Obtém timeline de eventos"""
        params = {"limit": limit}
        if camera:
            params["camera"] = camera
        if source_id:
            params["source_id"] = source_id

        return await self._request("GET", "/timeline", params=params)


# Gerenciador de instâncias Frigate
class FrigateManager:
    """Gerenciador de múltiplas instâncias Frigate"""

    def __init__(self):
        self._instances: Dict[str, FrigateService] = {}

    def add_instance(self, instance: FrigateInstance) -> FrigateService:
        """Adiciona uma instância Frigate"""
        service = FrigateService(instance)
        self._instances[instance.id] = service
        return service

    def get_instance(self, instance_id: str) -> Optional[FrigateService]:
        """Obtém uma instância pelo ID"""
        return self._instances.get(instance_id)

    def list_instances(self) -> List[str]:
        """Lista IDs das instâncias"""
        return list(self._instances.keys())

    def remove_instance(self, instance_id: str) -> bool:
        """Remove uma instância"""
        if instance_id in self._instances:
            del self._instances[instance_id]
            return True
        return False

    async def close_all(self):
        """Fecha todas as conexões"""
        for service in self._instances.values():
            await service.close()
        self._instances.clear()


# Instância global do gerenciador
frigate_manager = FrigateManager()


def get_frigate_manager() -> FrigateManager:
    """Obtém o gerenciador Frigate"""
    return frigate_manager
