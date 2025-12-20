"""
Conecta Plus - Guardian Service
Servico de integracao entre Backend FastAPI e Agentes Guardian

Este servico fornece uma interface unificada para:
- Orquestrador de agentes Guardian
- Sistema de alertas e incidentes
- Analytics e predicoes
- Controle de acesso
- Notificacoes
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import sys
import os

# Adicionar path dos agentes
sys.path.insert(0, '/opt/conecta-plus')

logger = logging.getLogger(__name__)

# Singleton para o servico Guardian
_guardian_service: Optional['GuardianService'] = None


@dataclass
class AlertDTO:
    """Data Transfer Object para Alerta."""
    id: str
    type: str
    severity: str
    title: str
    description: str
    location: str
    camera_id: Optional[str] = None
    timestamp: str = ""
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IncidentDTO:
    """Data Transfer Object para Incidente."""
    id: str
    type: str
    severity: str
    status: str
    title: str
    description: str
    location: str
    detected_at: str
    acknowledged_at: Optional[str] = None
    resolved_at: Optional[str] = None
    assigned_to: Optional[str] = None
    escalation_level: int = 0
    timeline: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class RiskAssessmentDTO:
    """Data Transfer Object para Avaliacao de Risco."""
    score: float
    level: str
    trend: str
    factors: List[Dict[str, Any]]
    recommendations: List[str]
    assessed_at: str


@dataclass
class DashboardDTO:
    """Data Transfer Object para Dashboard."""
    system_status: str
    uptime_seconds: float
    risk_score: float
    risk_level: str
    risk_trend: str
    active_alerts: int
    active_incidents: int
    critical_incidents: int
    cameras_online: int
    cameras_total: int
    access_24h: Dict[str, int]
    recommendations: List[str]
    timestamp: str


class GuardianService:
    """
    Servico principal de integracao Guardian.

    Gerencia:
    - Orquestrador de agentes
    - Cache de dados
    - Conexoes WebSocket
    - Publicacao de eventos
    """

    def __init__(self):
        self.orchestrator = None
        self.is_initialized = False
        self.websocket_connections: List[Any] = []

        # Cache local para dados frequentes
        self._alerts_cache: Dict[str, AlertDTO] = {}
        self._incidents_cache: Dict[str, IncidentDTO] = {}
        self._risk_cache: Optional[RiskAssessmentDTO] = None
        self._risk_cache_time: Optional[datetime] = None

        # Configuracoes
        self.risk_cache_ttl = 60  # segundos

        logger.info("GuardianService criado")

    async def initialize(self) -> bool:
        """Inicializa o servico e o orquestrador de agentes."""
        if self.is_initialized:
            return True

        try:
            # Importar e criar orquestrador
            from agents.guardian import create_guardian_system

            self.orchestrator = await create_guardian_system({
                "monitor": {
                    "alert_cooldown": 60,
                },
                "access": {
                    "face_threshold": 0.85,
                    "plate_threshold": 0.90,
                },
                "analytics": {
                    "anomaly_z_threshold": 2.5,
                },
                "response": {
                    "auto_acknowledge_timeout": 300,
                },
                "assistant": {
                    "max_context_messages": 20,
                },
            })

            await self.orchestrator.start()
            self.is_initialized = True

            logger.info("GuardianService inicializado com sucesso")
            return True

        except ImportError as e:
            logger.warning(f"Agentes Guardian nao disponiveis: {e}")
            # Continuar sem orquestrador - modo degradado
            self.is_initialized = True
            return True

        except Exception as e:
            logger.error(f"Erro ao inicializar GuardianService: {e}")
            return False

    async def shutdown(self) -> None:
        """Encerra o servico."""
        if self.orchestrator:
            await self.orchestrator.stop()

        # Fechar conexoes WebSocket
        for ws in self.websocket_connections:
            try:
                await ws.close()
            except Exception:
                pass

        self.is_initialized = False
        logger.info("GuardianService encerrado")

    # ==================== Alertas ====================

    async def get_alerts(
        self,
        severity: Optional[str] = None,
        location: Optional[str] = None,
        acknowledged: Optional[bool] = None,
        limit: int = 100
    ) -> List[AlertDTO]:
        """Retorna lista de alertas ativos."""
        alerts = list(self._alerts_cache.values())

        # Filtros
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        if location:
            alerts = [a for a in alerts if location.lower() in a.location.lower()]
        if acknowledged is not None:
            alerts = [a for a in alerts if a.acknowledged == acknowledged]

        # Ordenar por timestamp (mais recente primeiro)
        alerts.sort(key=lambda x: x.timestamp, reverse=True)

        return alerts[:limit]

    async def get_alert(self, alert_id: str) -> Optional[AlertDTO]:
        """Retorna um alerta especifico."""
        return self._alerts_cache.get(alert_id)

    async def create_alert(
        self,
        alert_type: str,
        severity: str,
        title: str,
        description: str,
        location: str,
        camera_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AlertDTO:
        """Cria um novo alerta."""
        alert_id = f"ALT-{datetime.now().strftime('%Y%m%d%H%M%S')}-{len(self._alerts_cache):04d}"

        alert = AlertDTO(
            id=alert_id,
            type=alert_type,
            severity=severity,
            title=title,
            description=description,
            location=location,
            camera_id=camera_id,
            timestamp=datetime.now().isoformat(),
            metadata=metadata or {}
        )

        self._alerts_cache[alert_id] = alert

        # Publicar via WebSocket
        await self._broadcast_event("alert.created", {
            "id": alert.id,
            "type": alert.type,
            "severity": alert.severity,
            "title": alert.title,
            "location": alert.location,
        })

        logger.info(f"Alerta criado: {alert_id} - {title}")
        return alert

    async def acknowledge_alert(
        self,
        alert_id: str,
        user_id: str,
        notes: Optional[str] = None
    ) -> Optional[AlertDTO]:
        """Reconhece um alerta."""
        alert = self._alerts_cache.get(alert_id)
        if not alert:
            return None

        alert.acknowledged = True
        alert.acknowledged_by = user_id
        alert.acknowledged_at = datetime.now().isoformat()

        await self._broadcast_event("alert.acknowledged", {
            "id": alert_id,
            "acknowledged_by": user_id,
        })

        logger.info(f"Alerta reconhecido: {alert_id} por {user_id}")
        return alert

    async def dismiss_alert(self, alert_id: str, user_id: str, reason: str) -> bool:
        """Descarta um alerta."""
        if alert_id in self._alerts_cache:
            del self._alerts_cache[alert_id]

            await self._broadcast_event("alert.dismissed", {
                "id": alert_id,
                "dismissed_by": user_id,
                "reason": reason,
            })

            logger.info(f"Alerta descartado: {alert_id} por {user_id}")
            return True
        return False

    # ==================== Incidentes ====================

    async def get_incidents(
        self,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 100
    ) -> List[IncidentDTO]:
        """Retorna lista de incidentes."""
        incidents = list(self._incidents_cache.values())

        if status:
            incidents = [i for i in incidents if i.status == status]
        if severity:
            incidents = [i for i in incidents if i.severity == severity]

        incidents.sort(key=lambda x: x.detected_at, reverse=True)
        return incidents[:limit]

    async def get_incident(self, incident_id: str) -> Optional[IncidentDTO]:
        """Retorna um incidente especifico."""
        return self._incidents_cache.get(incident_id)

    async def create_incident(
        self,
        incident_type: str,
        severity: str,
        title: str,
        description: str,
        location: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> IncidentDTO:
        """Cria um novo incidente."""
        incident_id = f"INC-{datetime.now().strftime('%Y%m%d%H%M%S')}-{len(self._incidents_cache):04d}"

        incident = IncidentDTO(
            id=incident_id,
            type=incident_type,
            severity=severity,
            status="detected",
            title=title,
            description=description,
            location=location,
            detected_at=datetime.now().isoformat(),
            timeline=[{
                "timestamp": datetime.now().isoformat(),
                "event": "incident_created",
                "description": f"Incidente detectado: {title}",
                "user": "system"
            }]
        )

        self._incidents_cache[incident_id] = incident

        # Publicar via WebSocket
        await self._broadcast_event("incident.created", {
            "id": incident.id,
            "type": incident.type,
            "severity": incident.severity,
            "title": incident.title,
            "location": incident.location,
        })

        logger.info(f"Incidente criado: {incident_id} - {title}")
        return incident

    async def acknowledge_incident(
        self,
        incident_id: str,
        user_id: str
    ) -> Optional[IncidentDTO]:
        """Reconhece um incidente."""
        incident = self._incidents_cache.get(incident_id)
        if not incident:
            return None

        incident.status = "acknowledged"
        incident.acknowledged_at = datetime.now().isoformat()
        incident.assigned_to = user_id
        incident.timeline.append({
            "timestamp": datetime.now().isoformat(),
            "event": "incident_acknowledged",
            "description": f"Incidente reconhecido por {user_id}",
            "user": user_id
        })

        await self._broadcast_event("incident.acknowledged", {
            "id": incident_id,
            "acknowledged_by": user_id,
        })

        return incident

    async def update_incident_status(
        self,
        incident_id: str,
        status: str,
        user_id: str,
        notes: Optional[str] = None
    ) -> Optional[IncidentDTO]:
        """Atualiza status de um incidente."""
        incident = self._incidents_cache.get(incident_id)
        if not incident:
            return None

        old_status = incident.status
        incident.status = status

        if status == "escalated":
            incident.escalation_level += 1

        incident.timeline.append({
            "timestamp": datetime.now().isoformat(),
            "event": f"status_changed",
            "description": notes or f"Status alterado de {old_status} para {status}",
            "user": user_id
        })

        await self._broadcast_event("incident.updated", {
            "id": incident_id,
            "status": status,
            "updated_by": user_id,
        })

        return incident

    async def resolve_incident(
        self,
        incident_id: str,
        resolution: str,
        user_id: str
    ) -> Optional[IncidentDTO]:
        """Resolve um incidente."""
        incident = self._incidents_cache.get(incident_id)
        if not incident:
            return None

        incident.status = "resolved"
        incident.resolved_at = datetime.now().isoformat()
        incident.timeline.append({
            "timestamp": datetime.now().isoformat(),
            "event": "incident_resolved",
            "description": resolution,
            "user": user_id
        })

        await self._broadcast_event("incident.resolved", {
            "id": incident_id,
            "resolution": resolution,
            "resolved_by": user_id,
        })

        return incident

    # ==================== Risco ====================

    async def get_risk_assessment(self) -> RiskAssessmentDTO:
        """Retorna avaliacao de risco atual."""
        # Verificar cache
        if self._risk_cache and self._risk_cache_time:
            if datetime.now() - self._risk_cache_time < timedelta(seconds=self.risk_cache_ttl):
                return self._risk_cache

        # Calcular novo score
        alert_count = len([a for a in self._alerts_cache.values() if not a.acknowledged])
        incident_count = len([i for i in self._incidents_cache.values() if i.status not in ["resolved", "closed"]])

        # Base score
        base_score = 20.0
        alert_factor = min(alert_count * 8, 30)
        incident_factor = min(incident_count * 12, 35)

        # Fator horario
        hour = datetime.now().hour
        time_factor = 15 if 0 <= hour <= 5 else 0

        total_score = min(base_score + alert_factor + incident_factor + time_factor, 100)

        # Determinar nivel
        if total_score < 20:
            level = "minimal"
        elif total_score < 40:
            level = "low"
        elif total_score < 60:
            level = "moderate"
        elif total_score < 80:
            level = "high"
        else:
            level = "critical"

        factors = []
        if alert_count > 0:
            factors.append({
                "name": "Alertas ativos",
                "contribution": alert_factor,
                "detail": f"{alert_count} alertas nao reconhecidos"
            })
        if incident_count > 0:
            factors.append({
                "name": "Incidentes abertos",
                "contribution": incident_factor,
                "detail": f"{incident_count} incidentes em andamento"
            })
        if time_factor > 0:
            factors.append({
                "name": "Horario de risco",
                "contribution": time_factor,
                "detail": "Periodo noturno - menor vigilancia"
            })

        recommendations = []
        if total_score > 60:
            recommendations.extend([
                "Acionar equipe de resposta",
                "Aumentar frequencia de rondas"
            ])
        elif total_score > 40:
            recommendations.append("Manter atencao redobrada")
        else:
            recommendations.append("Manter monitoramento padrao")

        assessment = RiskAssessmentDTO(
            score=total_score,
            level=level,
            trend="stable",
            factors=factors,
            recommendations=recommendations,
            assessed_at=datetime.now().isoformat()
        )

        # Atualizar cache
        self._risk_cache = assessment
        self._risk_cache_time = datetime.now()

        return assessment

    # ==================== Dashboard ====================

    async def get_dashboard(self) -> DashboardDTO:
        """Retorna dados consolidados para dashboard."""
        risk = await self.get_risk_assessment()

        active_alerts = len([a for a in self._alerts_cache.values() if not a.acknowledged])
        active_incidents = len([i for i in self._incidents_cache.values() if i.status not in ["resolved", "closed"]])
        critical_incidents = len([
            i for i in self._incidents_cache.values()
            if i.severity == "critical" and i.status not in ["resolved", "closed"]
        ])

        return DashboardDTO(
            system_status="online" if self.is_initialized else "degraded",
            uptime_seconds=0,  # Seria calculado do orchestrator
            risk_score=risk.score,
            risk_level=risk.level,
            risk_trend=risk.trend,
            active_alerts=active_alerts,
            active_incidents=active_incidents,
            critical_incidents=critical_incidents,
            cameras_online=23,  # Placeholder - viria do Frigate
            cameras_total=24,
            access_24h={"granted": 487, "denied": 12},
            recommendations=risk.recommendations,
            timestamp=datetime.now().isoformat()
        )

    # ==================== Assistente ====================

    async def chat(
        self,
        message: str,
        user_id: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Interface de chat com assistente."""
        if self.orchestrator:
            try:
                return await self.orchestrator.chat(
                    message=message,
                    user_id=user_id,
                    session_id=session_id
                )
            except Exception as e:
                logger.error(f"Erro no chat: {e}")

        # Fallback
        return {
            "response": "Sistema de assistente indisponivel no momento.",
            "suggestions": ["Status do sistema", "Ver alertas"],
            "session_id": session_id
        }

    async def get_quick_status(self) -> str:
        """Retorna status rapido em texto."""
        alerts = len([a for a in self._alerts_cache.values() if not a.acknowledged])
        incidents = len([i for i in self._incidents_cache.values() if i.status not in ["resolved", "closed"]])

        if alerts == 0 and incidents == 0:
            return "Sistema OK | Sem alertas ou incidentes"
        else:
            return f"{alerts} alertas | {incidents} incidentes ativos"

    # ==================== WebSocket ====================

    async def register_websocket(self, websocket) -> None:
        """Registra uma conexao WebSocket."""
        self.websocket_connections.append(websocket)
        logger.debug(f"WebSocket conectado. Total: {len(self.websocket_connections)}")

    async def unregister_websocket(self, websocket) -> None:
        """Remove uma conexao WebSocket."""
        if websocket in self.websocket_connections:
            self.websocket_connections.remove(websocket)
        logger.debug(f"WebSocket desconectado. Total: {len(self.websocket_connections)}")

    async def _broadcast_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Envia evento para todos os WebSockets conectados."""
        if not self.websocket_connections:
            return

        message = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }

        disconnected = []
        for ws in self.websocket_connections:
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.append(ws)

        # Remover conexoes mortas
        for ws in disconnected:
            self.websocket_connections.remove(ws)

    # ==================== Acoes ====================

    async def trigger_alarm(
        self,
        area: str,
        alarm_type: str,
        reason: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Aciona alarme."""
        await self._broadcast_event("alarm.triggered", {
            "area": area,
            "type": alarm_type,
            "reason": reason,
            "triggered_by": user_id,
        })

        logger.warning(f"Alarme acionado: {alarm_type} em {area} por {user_id}")

        return {
            "success": True,
            "message": f"Alarme {alarm_type} acionado em {area}",
            "alarm_id": f"ALM-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        }

    async def deactivate_alarm(
        self,
        area: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Desativa alarme."""
        await self._broadcast_event("alarm.deactivated", {
            "area": area,
            "deactivated_by": user_id,
        })

        logger.info(f"Alarme desativado em {area} por {user_id}")

        return {
            "success": True,
            "message": f"Alarme desativado em {area}"
        }

    async def dispatch_security(
        self,
        location: str,
        priority: str,
        reason: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Despacha equipe de seguranca."""
        await self._broadcast_event("security.dispatched", {
            "location": location,
            "priority": priority,
            "reason": reason,
            "dispatched_by": user_id,
        })

        logger.warning(f"Seguranca despachada para {location} - {priority}")

        return {
            "success": True,
            "message": f"Equipe despachada para {location}",
            "dispatch_id": f"DSP-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        }


# ==================== Factory Functions ====================

async def get_guardian_service() -> GuardianService:
    """Retorna instancia singleton do GuardianService."""
    global _guardian_service

    if _guardian_service is None:
        _guardian_service = GuardianService()
        await _guardian_service.initialize()

    return _guardian_service


async def shutdown_guardian_service() -> None:
    """Encerra o GuardianService."""
    global _guardian_service

    if _guardian_service:
        await _guardian_service.shutdown()
        _guardian_service = None
