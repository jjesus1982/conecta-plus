"""
Conecta Plus - Router de Integração Frigate NVR
API REST para gerenciamento de Frigate NVR
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel

from ..dependencies import get_current_user
from ..models.usuario import Usuario
from ..services.frigate import (
    FrigateInstance, FrigateManager, get_frigate_manager,
    FrigateCamera, FrigateEvent
)

router = APIRouter(prefix="/frigate", tags=["Frigate NVR"])


# === Schemas ===

class FrigateInstanceCreate(BaseModel):
    id: str
    name: str
    url: str
    api_key: Optional[str] = None
    mqtt_enabled: bool = False
    mqtt_host: Optional[str] = None
    mqtt_topic_prefix: str = "frigate"


class FrigateInstanceResponse(BaseModel):
    id: str
    name: str
    url: str
    mqtt_enabled: bool


class CameraResponse(BaseModel):
    name: str
    enabled: bool
    detect_enabled: bool
    record_enabled: bool
    snapshots_enabled: bool
    motion_enabled: bool
    width: int
    height: int
    fps: int


class EventResponse(BaseModel):
    id: str
    camera: str
    label: str
    sub_label: Optional[str]
    score: float
    top_score: float
    start_time: float
    end_time: Optional[float]
    has_clip: bool
    has_snapshot: bool
    zones: List[str]
    clip_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    snapshot_url: Optional[str] = None


class StreamUrlResponse(BaseModel):
    stream_url: str
    stream_type: str


class SnapshotResponse(BaseModel):
    snapshot_url: str


# === Instance Management ===

@router.post("/instances", response_model=FrigateInstanceResponse)
async def add_instance(
    instance_data: FrigateInstanceCreate,
    current_user: Usuario = Depends(get_current_user)
):
    """
    Adiciona uma nova instância Frigate NVR.
    Requer permissão de admin.
    """
    if current_user.role.value not in ["admin", "sindico"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permissão insuficiente"
        )

    manager = get_frigate_manager()

    instance = FrigateInstance(
        id=instance_data.id,
        name=instance_data.name,
        url=instance_data.url,
        api_key=instance_data.api_key,
        mqtt_enabled=instance_data.mqtt_enabled,
        mqtt_host=instance_data.mqtt_host,
        mqtt_topic_prefix=instance_data.mqtt_topic_prefix
    )

    manager.add_instance(instance)

    return FrigateInstanceResponse(
        id=instance.id,
        name=instance.name,
        url=instance.url,
        mqtt_enabled=instance.mqtt_enabled
    )


@router.get("/instances", response_model=List[FrigateInstanceResponse])
async def list_instances(
    current_user: Usuario = Depends(get_current_user)
):
    """Lista todas as instâncias Frigate configuradas."""
    manager = get_frigate_manager()

    instances = []
    for instance_id in manager.list_instances():
        service = manager.get_instance(instance_id)
        if service:
            instances.append(FrigateInstanceResponse(
                id=service.instance.id,
                name=service.instance.name,
                url=service.instance.url,
                mqtt_enabled=service.instance.mqtt_enabled
            ))

    return instances


@router.delete("/instances/{instance_id}")
async def remove_instance(
    instance_id: str,
    current_user: Usuario = Depends(get_current_user)
):
    """Remove uma instância Frigate."""
    if current_user.role.value not in ["admin", "sindico"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permissão insuficiente"
        )

    manager = get_frigate_manager()

    if not manager.remove_instance(instance_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instância não encontrada"
        )

    return {"success": True}


# === System Info ===

@router.get("/instances/{instance_id}/stats")
async def get_stats(
    instance_id: str,
    current_user: Usuario = Depends(get_current_user)
):
    """Obtém estatísticas do sistema Frigate."""
    manager = get_frigate_manager()
    service = manager.get_instance(instance_id)

    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instância não encontrada"
        )

    try:
        stats = await service.get_stats()
        return stats
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Erro ao conectar com Frigate: {str(e)}"
        )


@router.get("/instances/{instance_id}/version")
async def get_version(
    instance_id: str,
    current_user: Usuario = Depends(get_current_user)
):
    """Obtém versão do Frigate."""
    manager = get_frigate_manager()
    service = manager.get_instance(instance_id)

    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instância não encontrada"
        )

    try:
        version = await service.get_version()
        return {"version": version}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Erro ao conectar com Frigate: {str(e)}"
        )


# === Cameras ===

@router.get("/instances/{instance_id}/cameras", response_model=List[CameraResponse])
async def list_cameras(
    instance_id: str,
    current_user: Usuario = Depends(get_current_user)
):
    """Lista câmeras configuradas no Frigate."""
    manager = get_frigate_manager()
    service = manager.get_instance(instance_id)

    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instância não encontrada"
        )

    try:
        cameras = await service.list_cameras()
        return [CameraResponse(
            name=cam.name,
            enabled=cam.enabled,
            detect_enabled=cam.detect_enabled,
            record_enabled=cam.record_enabled,
            snapshots_enabled=cam.snapshots_enabled,
            motion_enabled=cam.motion_enabled,
            width=cam.width,
            height=cam.height,
            fps=cam.fps
        ) for cam in cameras]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Erro ao conectar com Frigate: {str(e)}"
        )


@router.get("/instances/{instance_id}/cameras/{camera}/snapshot", response_model=SnapshotResponse)
async def get_camera_snapshot(
    instance_id: str,
    camera: str,
    bbox: bool = False,
    height: int = 720,
    current_user: Usuario = Depends(get_current_user)
):
    """Obtém URL do snapshot atual de uma câmera."""
    manager = get_frigate_manager()
    service = manager.get_instance(instance_id)

    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instância não encontrada"
        )

    snapshot_url = await service.get_camera_snapshot(camera, bbox=bbox, height=height)
    return SnapshotResponse(snapshot_url=snapshot_url)


@router.post("/instances/{instance_id}/cameras/{camera}/detect/{state}")
async def toggle_detection(
    instance_id: str,
    camera: str,
    state: str,
    current_user: Usuario = Depends(get_current_user)
):
    """Ativa/desativa detecção. State: ON ou OFF."""
    if current_user.role.value not in ["admin", "sindico", "gerente", "porteiro"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permissão insuficiente"
        )

    manager = get_frigate_manager()
    service = manager.get_instance(instance_id)

    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instância não encontrada"
        )

    enabled = state.upper() == "ON"

    try:
        await service.toggle_detection(camera, enabled)
        return {"success": True, "detect": enabled}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Erro: {str(e)}"
        )


@router.post("/instances/{instance_id}/cameras/{camera}/recording/{state}")
async def toggle_recording(
    instance_id: str,
    camera: str,
    state: str,
    current_user: Usuario = Depends(get_current_user)
):
    """Ativa/desativa gravação. State: ON ou OFF."""
    if current_user.role.value not in ["admin", "sindico", "gerente"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permissão insuficiente"
        )

    manager = get_frigate_manager()
    service = manager.get_instance(instance_id)

    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instância não encontrada"
        )

    enabled = state.upper() == "ON"

    try:
        await service.toggle_recording(camera, enabled)
        return {"success": True, "recording": enabled}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Erro: {str(e)}"
        )


@router.get("/instances/{instance_id}/cameras/{camera}/stream", response_model=StreamUrlResponse)
async def get_stream_url(
    instance_id: str,
    camera: str,
    stream_type: str = Query("hls", enum=["rtsp", "hls", "webrtc", "mse"]),
    current_user: Usuario = Depends(get_current_user)
):
    """Obtém URL de streaming."""
    manager = get_frigate_manager()
    service = manager.get_instance(instance_id)

    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instância não encontrada"
        )

    stream_url = service.get_stream_url(camera, stream_type)
    return StreamUrlResponse(stream_url=stream_url, stream_type=stream_type)


# === Events ===

@router.get("/instances/{instance_id}/events", response_model=List[EventResponse])
async def get_events(
    instance_id: str,
    camera: Optional[str] = None,
    label: Optional[str] = None,
    zone: Optional[str] = None,
    after: Optional[float] = None,
    before: Optional[float] = None,
    has_clip: Optional[bool] = None,
    has_snapshot: Optional[bool] = None,
    min_score: Optional[float] = None,
    limit: int = Query(50, ge=1, le=500),
    current_user: Usuario = Depends(get_current_user)
):
    """Busca eventos de detecção."""
    manager = get_frigate_manager()
    service = manager.get_instance(instance_id)

    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instância não encontrada"
        )

    try:
        events = await service.get_events(
            camera=camera,
            label=label,
            zone=zone,
            after=after,
            before=before,
            has_clip=has_clip,
            has_snapshot=has_snapshot,
            min_score=min_score,
            limit=limit
        )

        return [EventResponse(
            id=e.id,
            camera=e.camera,
            label=e.label,
            sub_label=e.sub_label,
            score=e.score,
            top_score=e.top_score,
            start_time=e.start_time,
            end_time=e.end_time,
            has_clip=e.has_clip,
            has_snapshot=e.has_snapshot,
            zones=e.zones,
            clip_url=service.get_event_clip_url(e.id) if e.has_clip else None,
            thumbnail_url=service.get_event_thumbnail_url(e.id),
            snapshot_url=service.get_event_snapshot_url(e.id) if e.has_snapshot else None
        ) for e in events]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Erro: {str(e)}"
        )


@router.get("/instances/{instance_id}/events/{event_id}", response_model=EventResponse)
async def get_event(
    instance_id: str,
    event_id: str,
    current_user: Usuario = Depends(get_current_user)
):
    """Obtém detalhes de um evento."""
    manager = get_frigate_manager()
    service = manager.get_instance(instance_id)

    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instância não encontrada"
        )

    try:
        e = await service.get_event(event_id)
        return EventResponse(
            id=e.id,
            camera=e.camera,
            label=e.label,
            sub_label=e.sub_label,
            score=e.score,
            top_score=e.top_score,
            start_time=e.start_time,
            end_time=e.end_time,
            has_clip=e.has_clip,
            has_snapshot=e.has_snapshot,
            zones=e.zones,
            clip_url=service.get_event_clip_url(e.id) if e.has_clip else None,
            thumbnail_url=service.get_event_thumbnail_url(e.id),
            snapshot_url=service.get_event_snapshot_url(e.id) if e.has_snapshot else None
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Erro: {str(e)}"
        )


@router.delete("/instances/{instance_id}/events/{event_id}")
async def delete_event(
    instance_id: str,
    event_id: str,
    current_user: Usuario = Depends(get_current_user)
):
    """Deleta um evento."""
    if current_user.role.value not in ["admin", "sindico", "gerente"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permissão insuficiente"
        )

    manager = get_frigate_manager()
    service = manager.get_instance(instance_id)

    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instância não encontrada"
        )

    try:
        await service.delete_event(event_id)
        return {"success": True}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Erro: {str(e)}"
        )


@router.post("/instances/{instance_id}/events/{event_id}/retain")
async def retain_event(
    instance_id: str,
    event_id: str,
    retain: bool = True,
    current_user: Usuario = Depends(get_current_user)
):
    """Marca evento para retenção indefinida."""
    manager = get_frigate_manager()
    service = manager.get_instance(instance_id)

    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instância não encontrada"
        )

    try:
        await service.retain_event(event_id, retain)
        return {"success": True, "retain": retain}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Erro: {str(e)}"
        )


# === Recordings ===

@router.get("/instances/{instance_id}/cameras/{camera}/recordings")
async def get_recordings(
    instance_id: str,
    camera: str,
    after: Optional[float] = None,
    before: Optional[float] = None,
    current_user: Usuario = Depends(get_current_user)
):
    """Lista gravações de uma câmera."""
    manager = get_frigate_manager()
    service = manager.get_instance(instance_id)

    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instância não encontrada"
        )

    try:
        recordings = await service.get_recordings(camera, after=after, before=before)
        return {"recordings": [
            {
                "id": r.id,
                "camera": r.camera,
                "start_time": r.start_time,
                "end_time": r.end_time,
                "duration": r.duration,
                "motion": r.motion,
                "objects": r.objects,
                "playback_url": service.get_recording_url(camera, r.start_time, r.end_time)
            } for r in recordings
        ]}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Erro: {str(e)}"
        )


@router.get("/instances/{instance_id}/cameras/{camera}/recordings/summary")
async def get_recording_summary(
    instance_id: str,
    camera: str,
    timezone: str = "America/Sao_Paulo",
    current_user: Usuario = Depends(get_current_user)
):
    """Obtém resumo de gravações por hora/dia."""
    manager = get_frigate_manager()
    service = manager.get_instance(instance_id)

    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instância não encontrada"
        )

    try:
        summary = await service.get_recording_summary(camera, timezone)
        return summary
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Erro: {str(e)}"
        )


# === PTZ ===

@router.post("/instances/{instance_id}/cameras/{camera}/ptz/{action}")
async def ptz_control(
    instance_id: str,
    camera: str,
    action: str,
    speed: float = Query(0.5, ge=0.0, le=1.0),
    current_user: Usuario = Depends(get_current_user)
):
    """Controle PTZ da câmera."""
    if current_user.role.value not in ["admin", "sindico", "gerente", "porteiro"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permissão insuficiente"
        )

    manager = get_frigate_manager()
    service = manager.get_instance(instance_id)

    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instância não encontrada"
        )

    valid_actions = ["up", "down", "left", "right", "zoom_in", "zoom_out", "stop"]
    if action not in valid_actions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ação inválida. Use: {', '.join(valid_actions)}"
        )

    try:
        await service.ptz_move(camera, action, speed)
        return {"success": True, "action": action}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Erro: {str(e)}"
        )


@router.post("/instances/{instance_id}/cameras/{camera}/ptz/preset/{preset}")
async def ptz_preset(
    instance_id: str,
    camera: str,
    preset: str,
    current_user: Usuario = Depends(get_current_user)
):
    """Vai para preset PTZ."""
    if current_user.role.value not in ["admin", "sindico", "gerente", "porteiro"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permissão insuficiente"
        )

    manager = get_frigate_manager()
    service = manager.get_instance(instance_id)

    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instância não encontrada"
        )

    try:
        await service.ptz_preset(camera, preset)
        return {"success": True, "preset": preset}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Erro: {str(e)}"
        )


# === Zones ===

@router.get("/instances/{instance_id}/cameras/{camera}/zones")
async def get_zones(
    instance_id: str,
    camera: str,
    current_user: Usuario = Depends(get_current_user)
):
    """Lista zonas de uma câmera."""
    manager = get_frigate_manager()
    service = manager.get_instance(instance_id)

    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instância não encontrada"
        )

    try:
        zones = await service.get_zones(camera)
        return {"zones": zones}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Erro: {str(e)}"
        )
