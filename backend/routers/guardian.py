"""
Conecta Plus - Router Guardian
API REST para Sistema de Seguranca Inteligente Guardian

Endpoints:
- /guardian/status - Status do sistema
- /guardian/dashboard - Dashboard consolidado
- /guardian/alerts - Gestao de alertas
- /guardian/incidents - Gestao de incidentes
- /guardian/risk - Avaliacao de risco
- /guardian/chat - Assistente conversacional
- /guardian/actions - Acoes de seguranca
- /guardian/ws - WebSocket tempo real
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
import logging

from ..dependencies import get_current_user
from ..models.usuario import Usuario
from ..schemas.guardian import (
    # Alert schemas
    AlertCreate, AlertResponse, AlertAcknowledge, AlertDismiss, AlertListResponse,
    AlertSeverity,
    # Incident schemas
    IncidentCreate, IncidentResponse, IncidentUpdate, IncidentResolve,
    IncidentListResponse, IncidentStatus, IncidentSeverity,
    # Risk schemas
    RiskAssessmentResponse,
    # Dashboard schemas
    DashboardResponse, AccessStats,
    # Chat schemas
    ChatRequest, ChatResponse,
    # Action schemas
    TriggerAlarmRequest, DeactivateAlarmRequest, DispatchSecurityRequest,
    LockAccessRequest, UnlockAccessRequest, ActionResponse,
    # Statistics schemas
    StatisticsResponse, AlertStatistics, IncidentStatistics,
)
from ..services.guardian import get_guardian_service, GuardianService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/guardian", tags=["Guardian - Seguranca Inteligente"])


# ==================== Dependencies ====================

async def get_guardian() -> GuardianService:
    """Dependency para obter GuardianService."""
    return await get_guardian_service()


def require_security_role(user: Usuario):
    """Verifica se usuario tem permissao de seguranca."""
    allowed_roles = ["admin", "sindico", "seguranca", "porteiro"]
    if user.role.value not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permissao insuficiente para operacoes de seguranca"
        )


def require_admin_role(user: Usuario):
    """Verifica se usuario tem permissao de admin."""
    if user.role.value not in ["admin", "sindico"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permissao de administrador necessaria"
        )


# ==================== Status & Dashboard ====================

@router.get("/status")
async def get_status(
    guardian: GuardianService = Depends(get_guardian)
):
    """
    Retorna status geral do sistema Guardian.
    """
    quick_status = await guardian.get_quick_status()
    risk = await guardian.get_risk_assessment()

    return {
        "status": "online" if guardian.is_initialized else "degraded",
        "message": quick_status,
        "risk_score": risk.score,
        "risk_level": risk.level,
        "timestamp": risk.assessed_at
    }


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    current_user: Usuario = Depends(get_current_user),
    guardian: GuardianService = Depends(get_guardian)
):
    """
    Retorna dados consolidados para dashboard de seguranca.
    """
    dashboard = await guardian.get_dashboard()

    return DashboardResponse(
        system_status=dashboard.system_status,
        uptime_seconds=dashboard.uptime_seconds,
        risk_score=dashboard.risk_score,
        risk_level=dashboard.risk_level,
        risk_trend=dashboard.risk_trend,
        active_alerts=dashboard.active_alerts,
        active_incidents=dashboard.active_incidents,
        critical_incidents=dashboard.critical_incidents,
        cameras_online=dashboard.cameras_online,
        cameras_total=dashboard.cameras_total,
        access_24h=AccessStats(**dashboard.access_24h),
        recommendations=dashboard.recommendations,
        timestamp=dashboard.timestamp
    )


# ==================== Alerts ====================

@router.get("/alerts", response_model=AlertListResponse)
async def list_alerts(
    severity: Optional[AlertSeverity] = None,
    location: Optional[str] = None,
    acknowledged: Optional[bool] = None,
    limit: int = Query(100, ge=1, le=500),
    current_user: Usuario = Depends(get_current_user),
    guardian: GuardianService = Depends(get_guardian)
):
    """
    Lista alertas ativos.

    Filtros opcionais:
    - severity: Filtrar por severidade
    - location: Filtrar por local
    - acknowledged: Filtrar por status de reconhecimento
    """
    alerts = await guardian.get_alerts(
        severity=severity.value if severity else None,
        location=location,
        acknowledged=acknowledged,
        limit=limit
    )

    return AlertListResponse(
        alerts=[AlertResponse(
            id=a.id,
            type=a.type,
            severity=a.severity,
            title=a.title,
            description=a.description,
            location=a.location,
            camera_id=a.camera_id,
            timestamp=a.timestamp,
            acknowledged=a.acknowledged,
            acknowledged_by=a.acknowledged_by,
            acknowledged_at=a.acknowledged_at,
            metadata=a.metadata
        ) for a in alerts],
        total=len(alerts)
    )


@router.get("/alerts/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: str,
    current_user: Usuario = Depends(get_current_user),
    guardian: GuardianService = Depends(get_guardian)
):
    """
    Retorna detalhes de um alerta especifico.
    """
    alert = await guardian.get_alert(alert_id)
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alerta nao encontrado"
        )

    return AlertResponse(
        id=alert.id,
        type=alert.type,
        severity=alert.severity,
        title=alert.title,
        description=alert.description,
        location=alert.location,
        camera_id=alert.camera_id,
        timestamp=alert.timestamp,
        acknowledged=alert.acknowledged,
        acknowledged_by=alert.acknowledged_by,
        acknowledged_at=alert.acknowledged_at,
        metadata=alert.metadata
    )


@router.post("/alerts", response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
async def create_alert(
    alert_data: AlertCreate,
    current_user: Usuario = Depends(get_current_user),
    guardian: GuardianService = Depends(get_guardian)
):
    """
    Cria um novo alerta manualmente.
    Requer permissao de seguranca.
    """
    require_security_role(current_user)

    alert = await guardian.create_alert(
        alert_type=alert_data.type.value,
        severity=alert_data.severity.value,
        title=alert_data.title,
        description=alert_data.description,
        location=alert_data.location,
        camera_id=alert_data.camera_id,
        metadata=alert_data.metadata
    )

    logger.info(f"Alerta criado por {current_user.email}: {alert.id}")

    return AlertResponse(
        id=alert.id,
        type=alert.type,
        severity=alert.severity,
        title=alert.title,
        description=alert.description,
        location=alert.location,
        camera_id=alert.camera_id,
        timestamp=alert.timestamp,
        acknowledged=alert.acknowledged,
        metadata=alert.metadata
    )


@router.post("/alerts/{alert_id}/acknowledge", response_model=AlertResponse)
async def acknowledge_alert(
    alert_id: str,
    data: AlertAcknowledge,
    current_user: Usuario = Depends(get_current_user),
    guardian: GuardianService = Depends(get_guardian)
):
    """
    Reconhece um alerta.
    """
    require_security_role(current_user)

    alert = await guardian.acknowledge_alert(
        alert_id=alert_id,
        user_id=current_user.email,
        notes=data.notes
    )

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alerta nao encontrado"
        )

    logger.info(f"Alerta {alert_id} reconhecido por {current_user.email}")

    return AlertResponse(
        id=alert.id,
        type=alert.type,
        severity=alert.severity,
        title=alert.title,
        description=alert.description,
        location=alert.location,
        camera_id=alert.camera_id,
        timestamp=alert.timestamp,
        acknowledged=alert.acknowledged,
        acknowledged_by=alert.acknowledged_by,
        acknowledged_at=alert.acknowledged_at,
        metadata=alert.metadata
    )


@router.delete("/alerts/{alert_id}")
async def dismiss_alert(
    alert_id: str,
    data: AlertDismiss,
    current_user: Usuario = Depends(get_current_user),
    guardian: GuardianService = Depends(get_guardian)
):
    """
    Descarta um alerta (falso positivo).
    """
    require_security_role(current_user)

    success = await guardian.dismiss_alert(
        alert_id=alert_id,
        user_id=current_user.email,
        reason=data.reason
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alerta nao encontrado"
        )

    logger.info(f"Alerta {alert_id} descartado por {current_user.email}: {data.reason}")

    return {"success": True, "message": "Alerta descartado"}


# ==================== Incidents ====================

@router.get("/incidents", response_model=IncidentListResponse)
async def list_incidents(
    status_filter: Optional[IncidentStatus] = Query(None, alias="status"),
    severity: Optional[IncidentSeverity] = None,
    limit: int = Query(100, ge=1, le=500),
    current_user: Usuario = Depends(get_current_user),
    guardian: GuardianService = Depends(get_guardian)
):
    """
    Lista incidentes.
    """
    incidents = await guardian.get_incidents(
        status=status_filter.value if status_filter else None,
        severity=severity.value if severity else None,
        limit=limit
    )

    return IncidentListResponse(
        incidents=[IncidentResponse(
            id=i.id,
            type=i.type,
            severity=i.severity,
            status=i.status,
            title=i.title,
            description=i.description,
            location=i.location,
            detected_at=i.detected_at,
            acknowledged_at=i.acknowledged_at,
            resolved_at=i.resolved_at,
            assigned_to=i.assigned_to,
            escalation_level=i.escalation_level,
            timeline=i.timeline
        ) for i in incidents],
        total=len(incidents)
    )


@router.get("/incidents/{incident_id}", response_model=IncidentResponse)
async def get_incident(
    incident_id: str,
    current_user: Usuario = Depends(get_current_user),
    guardian: GuardianService = Depends(get_guardian)
):
    """
    Retorna detalhes de um incidente.
    """
    incident = await guardian.get_incident(incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incidente nao encontrado"
        )

    return IncidentResponse(
        id=incident.id,
        type=incident.type,
        severity=incident.severity,
        status=incident.status,
        title=incident.title,
        description=incident.description,
        location=incident.location,
        detected_at=incident.detected_at,
        acknowledged_at=incident.acknowledged_at,
        resolved_at=incident.resolved_at,
        assigned_to=incident.assigned_to,
        escalation_level=incident.escalation_level,
        timeline=incident.timeline
    )


@router.post("/incidents", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED)
async def create_incident(
    incident_data: IncidentCreate,
    current_user: Usuario = Depends(get_current_user),
    guardian: GuardianService = Depends(get_guardian)
):
    """
    Cria um novo incidente.
    """
    require_security_role(current_user)

    incident = await guardian.create_incident(
        incident_type=incident_data.type.value,
        severity=incident_data.severity.value,
        title=incident_data.title,
        description=incident_data.description,
        location=incident_data.location,
        metadata=incident_data.metadata
    )

    logger.info(f"Incidente criado por {current_user.email}: {incident.id}")

    return IncidentResponse(
        id=incident.id,
        type=incident.type,
        severity=incident.severity,
        status=incident.status,
        title=incident.title,
        description=incident.description,
        location=incident.location,
        detected_at=incident.detected_at,
        escalation_level=incident.escalation_level,
        timeline=incident.timeline
    )


@router.post("/incidents/{incident_id}/acknowledge", response_model=IncidentResponse)
async def acknowledge_incident(
    incident_id: str,
    current_user: Usuario = Depends(get_current_user),
    guardian: GuardianService = Depends(get_guardian)
):
    """
    Reconhece um incidente e assume responsabilidade.
    """
    require_security_role(current_user)

    incident = await guardian.acknowledge_incident(
        incident_id=incident_id,
        user_id=current_user.email
    )

    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incidente nao encontrado"
        )

    logger.info(f"Incidente {incident_id} reconhecido por {current_user.email}")

    return IncidentResponse(
        id=incident.id,
        type=incident.type,
        severity=incident.severity,
        status=incident.status,
        title=incident.title,
        description=incident.description,
        location=incident.location,
        detected_at=incident.detected_at,
        acknowledged_at=incident.acknowledged_at,
        assigned_to=incident.assigned_to,
        escalation_level=incident.escalation_level,
        timeline=incident.timeline
    )


@router.put("/incidents/{incident_id}", response_model=IncidentResponse)
async def update_incident(
    incident_id: str,
    data: IncidentUpdate,
    current_user: Usuario = Depends(get_current_user),
    guardian: GuardianService = Depends(get_guardian)
):
    """
    Atualiza status de um incidente.
    """
    require_security_role(current_user)

    incident = await guardian.update_incident_status(
        incident_id=incident_id,
        status=data.status.value,
        user_id=current_user.email,
        notes=data.notes
    )

    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incidente nao encontrado"
        )

    return IncidentResponse(
        id=incident.id,
        type=incident.type,
        severity=incident.severity,
        status=incident.status,
        title=incident.title,
        description=incident.description,
        location=incident.location,
        detected_at=incident.detected_at,
        acknowledged_at=incident.acknowledged_at,
        resolved_at=incident.resolved_at,
        assigned_to=incident.assigned_to,
        escalation_level=incident.escalation_level,
        timeline=incident.timeline
    )


@router.post("/incidents/{incident_id}/resolve", response_model=IncidentResponse)
async def resolve_incident(
    incident_id: str,
    data: IncidentResolve,
    current_user: Usuario = Depends(get_current_user),
    guardian: GuardianService = Depends(get_guardian)
):
    """
    Resolve um incidente.
    """
    require_security_role(current_user)

    incident = await guardian.resolve_incident(
        incident_id=incident_id,
        resolution=data.resolution,
        user_id=current_user.email
    )

    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incidente nao encontrado"
        )

    logger.info(f"Incidente {incident_id} resolvido por {current_user.email}")

    return IncidentResponse(
        id=incident.id,
        type=incident.type,
        severity=incident.severity,
        status=incident.status,
        title=incident.title,
        description=incident.description,
        location=incident.location,
        detected_at=incident.detected_at,
        acknowledged_at=incident.acknowledged_at,
        resolved_at=incident.resolved_at,
        assigned_to=incident.assigned_to,
        escalation_level=incident.escalation_level,
        timeline=incident.timeline
    )


# ==================== Risk ====================

@router.get("/risk", response_model=RiskAssessmentResponse)
async def get_risk_assessment(
    current_user: Usuario = Depends(get_current_user),
    guardian: GuardianService = Depends(get_guardian)
):
    """
    Retorna avaliacao de risco atual.
    """
    risk = await guardian.get_risk_assessment()

    return RiskAssessmentResponse(
        score=risk.score,
        level=risk.level,
        trend=risk.trend,
        factors=risk.factors,
        recommendations=risk.recommendations,
        assessed_at=risk.assessed_at
    )


# ==================== Chat ====================

@router.post("/chat", response_model=ChatResponse)
async def chat(
    data: ChatRequest,
    current_user: Usuario = Depends(get_current_user),
    guardian: GuardianService = Depends(get_guardian)
):
    """
    Interface de chat com assistente de seguranca.
    """
    result = await guardian.chat(
        message=data.message,
        user_id=current_user.email,
        session_id=data.session_id
    )

    return ChatResponse(
        response=result.get("response", ""),
        suggestions=result.get("suggestions", []),
        session_id=result.get("session_id"),
        data=result.get("data")
    )


# ==================== Actions ====================

@router.post("/actions/alarm/trigger", response_model=ActionResponse)
async def trigger_alarm(
    data: TriggerAlarmRequest,
    current_user: Usuario = Depends(get_current_user),
    guardian: GuardianService = Depends(get_guardian)
):
    """
    Aciona um alarme em uma area especifica.
    """
    require_security_role(current_user)

    result = await guardian.trigger_alarm(
        area=data.area,
        alarm_type=data.type.value,
        reason=data.reason,
        user_id=current_user.email
    )

    logger.warning(f"Alarme acionado por {current_user.email}: {data.type} em {data.area}")

    return ActionResponse(
        success=result["success"],
        message=result["message"],
        action_id=result.get("alarm_id")
    )


@router.post("/actions/alarm/deactivate", response_model=ActionResponse)
async def deactivate_alarm(
    data: DeactivateAlarmRequest,
    current_user: Usuario = Depends(get_current_user),
    guardian: GuardianService = Depends(get_guardian)
):
    """
    Desativa um alarme.
    """
    require_security_role(current_user)

    result = await guardian.deactivate_alarm(
        area=data.area,
        user_id=current_user.email
    )

    logger.info(f"Alarme desativado por {current_user.email} em {data.area}")

    return ActionResponse(
        success=result["success"],
        message=result["message"]
    )


@router.post("/actions/security/dispatch", response_model=ActionResponse)
async def dispatch_security(
    data: DispatchSecurityRequest,
    current_user: Usuario = Depends(get_current_user),
    guardian: GuardianService = Depends(get_guardian)
):
    """
    Despacha equipe de seguranca para um local.
    """
    require_security_role(current_user)

    result = await guardian.dispatch_security(
        location=data.location,
        priority=data.priority.value,
        reason=data.reason,
        user_id=current_user.email
    )

    logger.warning(f"Seguranca despachada por {current_user.email} para {data.location}")

    return ActionResponse(
        success=result["success"],
        message=result["message"],
        action_id=result.get("dispatch_id")
    )


# ==================== WebSocket ====================

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    guardian: GuardianService = Depends(get_guardian)
):
    """
    WebSocket para receber eventos em tempo real.

    Eventos:
    - alert.created
    - alert.acknowledged
    - alert.dismissed
    - incident.created
    - incident.acknowledged
    - incident.updated
    - incident.resolved
    - alarm.triggered
    - alarm.deactivated
    - security.dispatched
    """
    await websocket.accept()
    await guardian.register_websocket(websocket)

    try:
        while True:
            # Manter conexao aberta, recebendo pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        await guardian.unregister_websocket(websocket)
    except Exception as e:
        logger.error(f"Erro no WebSocket: {e}")
        await guardian.unregister_websocket(websocket)


# ==================== Statistics ====================

@router.get("/statistics", response_model=StatisticsResponse)
async def get_statistics(
    period_hours: int = Query(24, ge=1, le=720),
    current_user: Usuario = Depends(get_current_user),
    guardian: GuardianService = Depends(get_guardian)
):
    """
    Retorna estatisticas do sistema.
    """
    from datetime import datetime

    alerts = await guardian.get_alerts(limit=1000)
    incidents = await guardian.get_incidents(limit=1000)

    alert_stats = AlertStatistics(
        total=len(alerts),
        by_severity={
            "critical": len([a for a in alerts if a.severity == "critical"]),
            "high": len([a for a in alerts if a.severity == "high"]),
            "medium": len([a for a in alerts if a.severity == "medium"]),
            "low": len([a for a in alerts if a.severity == "low"]),
            "info": len([a for a in alerts if a.severity == "info"]),
        },
        by_type={},
        acknowledged=len([a for a in alerts if a.acknowledged]),
        pending=len([a for a in alerts if not a.acknowledged])
    )

    incident_stats = IncidentStatistics(
        total=len(incidents),
        by_severity={
            "critical": len([i for i in incidents if i.severity == "critical"]),
            "high": len([i for i in incidents if i.severity == "high"]),
            "medium": len([i for i in incidents if i.severity == "medium"]),
            "low": len([i for i in incidents if i.severity == "low"]),
        },
        by_type={},
        by_status={
            "detected": len([i for i in incidents if i.status == "detected"]),
            "acknowledged": len([i for i in incidents if i.status == "acknowledged"]),
            "in_progress": len([i for i in incidents if i.status == "in_progress"]),
            "escalated": len([i for i in incidents if i.status == "escalated"]),
            "resolved": len([i for i in incidents if i.status == "resolved"]),
        },
        avg_response_time_seconds=120.0
    )

    return StatisticsResponse(
        period_hours=period_hours,
        alerts=alert_stats,
        incidents=incident_stats,
        timestamp=datetime.now().isoformat()
    )
