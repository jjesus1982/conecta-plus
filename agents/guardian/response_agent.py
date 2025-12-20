"""
Conecta Plus - Guardian Response Agent
Agente de Resposta Automatizada a Incidentes - Nivel 7

Responsabilidades:
- Coordenar respostas automatizadas a incidentes
- Gerenciar protocolos de resposta
- Notificar equipes e stakeholders
- Escalonar incidentes conforme severidade
- Documentar acoes e timeline
"""

import asyncio
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Set
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class IncidentSeverity(Enum):
    """Severidade do incidente."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentStatus(Enum):
    """Status do incidente."""
    DETECTED = "detected"
    ACKNOWLEDGED = "acknowledged"
    IN_PROGRESS = "in_progress"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    CLOSED = "closed"


class IncidentType(Enum):
    """Tipos de incidente."""
    INTRUSION = "intrusion"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    EQUIPMENT_FAILURE = "equipment_failure"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    EMERGENCY = "emergency"
    VANDALISM = "vandalism"
    FIRE = "fire"
    MEDICAL = "medical"
    SECURITY_BREACH = "security_breach"
    SYSTEM_ALERT = "system_alert"


class ActionType(Enum):
    """Tipos de acao de resposta."""
    NOTIFY = "notify"
    ALERT = "alert"
    LOCK_ACCESS = "lock_access"
    UNLOCK_ACCESS = "unlock_access"
    ACTIVATE_ALARM = "activate_alarm"
    DEACTIVATE_ALARM = "deactivate_alarm"
    RECORD_VIDEO = "record_video"
    DISPATCH_SECURITY = "dispatch_security"
    CALL_EMERGENCY = "call_emergency"
    ISOLATE_AREA = "isolate_area"
    LOG_EVENT = "log_event"
    ESCALATE = "escalate"


class NotificationChannel(Enum):
    """Canais de notificacao."""
    SMS = "sms"
    EMAIL = "email"
    PUSH = "push"
    WHATSAPP = "whatsapp"
    PHONE_CALL = "phone_call"
    INTERCOM = "intercom"
    DASHBOARD = "dashboard"


@dataclass
class ResponseAction:
    """Acao de resposta."""
    id: str
    type: ActionType
    target: str
    parameters: Dict[str, Any]
    executed_at: Optional[datetime] = None
    result: Optional[str] = None
    success: bool = False


@dataclass
class Notification:
    """Notificacao enviada."""
    id: str
    channel: NotificationChannel
    recipient: str
    message: str
    sent_at: datetime
    delivered: bool = False
    read: bool = False


@dataclass
class EscalationLevel:
    """Nivel de escalonamento."""
    level: int
    name: str
    contacts: List[Dict[str, str]]
    timeout_minutes: int
    auto_escalate: bool


@dataclass
class ResponseProtocol:
    """Protocolo de resposta a incidente."""
    id: str
    name: str
    incident_type: IncidentType
    severity_threshold: IncidentSeverity
    actions: List[Dict[str, Any]]
    notifications: List[Dict[str, Any]]
    escalation_levels: List[EscalationLevel]
    auto_resolve_minutes: Optional[int] = None
    requires_acknowledgment: bool = True


@dataclass
class Incident:
    """Incidente de seguranca."""
    id: str
    type: IncidentType
    severity: IncidentSeverity
    status: IncidentStatus
    title: str
    description: str
    location: str
    detected_at: datetime
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    assigned_to: Optional[str] = None
    escalation_level: int = 0
    actions_taken: List[ResponseAction] = field(default_factory=list)
    notifications_sent: List[Notification] = field(default_factory=list)
    timeline: List[Dict[str, Any]] = field(default_factory=list)
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    related_alerts: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class GuardianResponseAgent:
    """
    Agente de Resposta Guardian - Nivel 7 TRANSCENDENT

    Capacidades:
    - Execucao automatica de protocolos de resposta
    - Notificacoes multi-canal
    - Escalonamento inteligente
    - Coordenacao com outros agentes
    - Documentacao automatica
    """

    def __init__(
        self,
        agent_id: str = "guardian_response",
        config: Optional[Dict[str, Any]] = None,
        message_bus: Optional[Any] = None
    ):
        self.agent_id = agent_id
        self.config = config or {}
        self.message_bus = message_bus

        # Configuracoes
        self.auto_acknowledge_timeout = self.config.get("auto_acknowledge_timeout", 300)
        self.max_escalation_level = self.config.get("max_escalation_level", 3)

        # Incidentes ativos
        self.active_incidents: Dict[str, Incident] = {}
        self.incident_history: List[Incident] = []

        # Protocolos de resposta
        self.protocols: Dict[str, ResponseProtocol] = {}
        self._load_default_protocols()

        # Handlers de acao
        self.action_handlers: Dict[ActionType, Callable] = {}
        self._register_action_handlers()

        # Contatos de emergencia
        self.emergency_contacts: List[Dict[str, Any]] = []
        self._load_emergency_contacts()

        # Estado
        self.is_running = False
        self._monitor_task: Optional[asyncio.Task] = None

        logger.info(f"GuardianResponseAgent {agent_id} inicializado")

    def _load_default_protocols(self) -> None:
        """Carrega protocolos de resposta padrao."""
        # Protocolo para intrusao
        self.protocols["intrusion"] = ResponseProtocol(
            id="protocol_intrusion",
            name="Protocolo de Intrusao",
            incident_type=IncidentType.INTRUSION,
            severity_threshold=IncidentSeverity.HIGH,
            actions=[
                {"type": ActionType.ACTIVATE_ALARM, "target": "all", "delay": 0},
                {"type": ActionType.RECORD_VIDEO, "target": "affected_area", "duration": 300},
                {"type": ActionType.LOCK_ACCESS, "target": "perimeter", "delay": 0},
                {"type": ActionType.DISPATCH_SECURITY, "target": "location", "delay": 0}
            ],
            notifications=[
                {"channel": NotificationChannel.PUSH, "template": "intrusion_alert", "priority": "high"},
                {"channel": NotificationChannel.SMS, "template": "intrusion_sms", "priority": "high"},
                {"channel": NotificationChannel.PHONE_CALL, "template": "emergency_call", "priority": "critical"}
            ],
            escalation_levels=[
                EscalationLevel(1, "Equipe de Seguranca", [{"role": "security_team"}], 5, True),
                EscalationLevel(2, "Supervisor", [{"role": "supervisor"}], 10, True),
                EscalationLevel(3, "Gerente/Policia", [{"role": "manager"}, {"role": "police"}], 15, False)
            ],
            requires_acknowledgment=True
        )

        # Protocolo para acesso nao autorizado
        self.protocols["unauthorized_access"] = ResponseProtocol(
            id="protocol_unauthorized",
            name="Protocolo de Acesso Nao Autorizado",
            incident_type=IncidentType.UNAUTHORIZED_ACCESS,
            severity_threshold=IncidentSeverity.MEDIUM,
            actions=[
                {"type": ActionType.RECORD_VIDEO, "target": "access_point", "duration": 180},
                {"type": ActionType.LOG_EVENT, "target": "audit", "delay": 0},
                {"type": ActionType.ALERT, "target": "dashboard", "delay": 0}
            ],
            notifications=[
                {"channel": NotificationChannel.PUSH, "template": "access_denied_alert", "priority": "medium"},
                {"channel": NotificationChannel.DASHBOARD, "template": "access_event", "priority": "medium"}
            ],
            escalation_levels=[
                EscalationLevel(1, "Portaria", [{"role": "doorman"}], 5, True),
                EscalationLevel(2, "Seguranca", [{"role": "security_team"}], 10, False)
            ],
            auto_resolve_minutes=30,
            requires_acknowledgment=True
        )

        # Protocolo para emergencia
        self.protocols["emergency"] = ResponseProtocol(
            id="protocol_emergency",
            name="Protocolo de Emergencia",
            incident_type=IncidentType.EMERGENCY,
            severity_threshold=IncidentSeverity.CRITICAL,
            actions=[
                {"type": ActionType.ACTIVATE_ALARM, "target": "all", "delay": 0},
                {"type": ActionType.CALL_EMERGENCY, "target": "services", "delay": 0},
                {"type": ActionType.RECORD_VIDEO, "target": "all", "duration": 600},
                {"type": ActionType.UNLOCK_ACCESS, "target": "emergency_exits", "delay": 0}
            ],
            notifications=[
                {"channel": NotificationChannel.INTERCOM, "template": "emergency_broadcast", "priority": "critical"},
                {"channel": NotificationChannel.PHONE_CALL, "template": "emergency_call", "priority": "critical"},
                {"channel": NotificationChannel.SMS, "template": "emergency_sms", "priority": "critical"}
            ],
            escalation_levels=[
                EscalationLevel(1, "Todos", [{"role": "all_staff"}], 0, True),
                EscalationLevel(2, "Servicos de Emergencia", [{"role": "emergency_services"}], 0, False)
            ],
            requires_acknowledgment=False
        )

        # Protocolo para falha de equipamento
        self.protocols["equipment_failure"] = ResponseProtocol(
            id="protocol_equipment",
            name="Protocolo de Falha de Equipamento",
            incident_type=IncidentType.EQUIPMENT_FAILURE,
            severity_threshold=IncidentSeverity.LOW,
            actions=[
                {"type": ActionType.LOG_EVENT, "target": "maintenance", "delay": 0},
                {"type": ActionType.ALERT, "target": "dashboard", "delay": 0}
            ],
            notifications=[
                {"channel": NotificationChannel.EMAIL, "template": "equipment_failure", "priority": "low"},
                {"channel": NotificationChannel.DASHBOARD, "template": "maintenance_alert", "priority": "low"}
            ],
            escalation_levels=[
                EscalationLevel(1, "Manutencao", [{"role": "maintenance_team"}], 60, True),
                EscalationLevel(2, "TI", [{"role": "it_team"}], 120, False)
            ],
            auto_resolve_minutes=480,
            requires_acknowledgment=True
        )

        # Protocolo para atividade suspeita
        self.protocols["suspicious_activity"] = ResponseProtocol(
            id="protocol_suspicious",
            name="Protocolo de Atividade Suspeita",
            incident_type=IncidentType.SUSPICIOUS_ACTIVITY,
            severity_threshold=IncidentSeverity.MEDIUM,
            actions=[
                {"type": ActionType.RECORD_VIDEO, "target": "affected_area", "duration": 300},
                {"type": ActionType.ALERT, "target": "dashboard", "delay": 0},
                {"type": ActionType.LOG_EVENT, "target": "security", "delay": 0}
            ],
            notifications=[
                {"channel": NotificationChannel.PUSH, "template": "suspicious_alert", "priority": "medium"},
                {"channel": NotificationChannel.DASHBOARD, "template": "suspicious_event", "priority": "medium"}
            ],
            escalation_levels=[
                EscalationLevel(1, "Seguranca", [{"role": "security_team"}], 10, True),
                EscalationLevel(2, "Supervisor", [{"role": "supervisor"}], 20, False)
            ],
            auto_resolve_minutes=60,
            requires_acknowledgment=True
        )

    def _load_emergency_contacts(self) -> None:
        """Carrega contatos de emergencia."""
        self.emergency_contacts = [
            {"role": "security_team", "name": "Equipe de Seguranca", "phone": "", "email": ""},
            {"role": "supervisor", "name": "Supervisor de Turno", "phone": "", "email": ""},
            {"role": "manager", "name": "Gerente de Seguranca", "phone": "", "email": ""},
            {"role": "doorman", "name": "Portaria Central", "phone": "", "email": ""},
            {"role": "maintenance_team", "name": "Equipe de Manutencao", "phone": "", "email": ""},
            {"role": "it_team", "name": "Equipe de TI", "phone": "", "email": ""},
            {"role": "police", "name": "Policia Militar", "phone": "190", "email": ""},
            {"role": "fire_department", "name": "Corpo de Bombeiros", "phone": "193", "email": ""},
            {"role": "ambulance", "name": "SAMU", "phone": "192", "email": ""}
        ]

    def _register_action_handlers(self) -> None:
        """Registra handlers para cada tipo de acao."""
        self.action_handlers = {
            ActionType.NOTIFY: self._execute_notify,
            ActionType.ALERT: self._execute_alert,
            ActionType.LOCK_ACCESS: self._execute_lock_access,
            ActionType.UNLOCK_ACCESS: self._execute_unlock_access,
            ActionType.ACTIVATE_ALARM: self._execute_activate_alarm,
            ActionType.DEACTIVATE_ALARM: self._execute_deactivate_alarm,
            ActionType.RECORD_VIDEO: self._execute_record_video,
            ActionType.DISPATCH_SECURITY: self._execute_dispatch_security,
            ActionType.CALL_EMERGENCY: self._execute_call_emergency,
            ActionType.ISOLATE_AREA: self._execute_isolate_area,
            ActionType.LOG_EVENT: self._execute_log_event,
            ActionType.ESCALATE: self._execute_escalate
        }

    async def start(self) -> None:
        """Inicia o agente de resposta."""
        if self.is_running:
            return

        self.is_running = True
        self._monitor_task = asyncio.create_task(self._monitor_incidents())

        if self.message_bus:
            await self.message_bus.subscribe("alert.created", self._handle_alert)
            await self.message_bus.subscribe("incident.create", self._handle_incident_request)
            await self.message_bus.subscribe("incident.acknowledge", self._handle_acknowledge)
            await self.message_bus.subscribe("incident.resolve", self._handle_resolve)

        logger.info(f"GuardianResponseAgent {self.agent_id} iniciado")

    async def stop(self) -> None:
        """Para o agente de resposta."""
        self.is_running = False

        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        logger.info(f"GuardianResponseAgent {self.agent_id} parado")

    async def _monitor_incidents(self) -> None:
        """Monitora incidentes ativos para escalonamento e auto-resolucao."""
        while self.is_running:
            try:
                await asyncio.sleep(30)  # Verificar a cada 30 segundos

                now = datetime.now()
                incidents_to_check = list(self.active_incidents.values())

                for incident in incidents_to_check:
                    # Verificar auto-acknowledge timeout
                    if incident.status == IncidentStatus.DETECTED:
                        time_since_detection = (now - incident.detected_at).total_seconds()
                        if time_since_detection > self.auto_acknowledge_timeout:
                            await self._auto_escalate(incident)

                    # Verificar escalonamento
                    if incident.status in [IncidentStatus.ACKNOWLEDGED, IncidentStatus.IN_PROGRESS]:
                        await self._check_escalation(incident)

                    # Verificar auto-resolucao
                    protocol = self._get_protocol_for_incident(incident)
                    if protocol and protocol.auto_resolve_minutes:
                        time_since_detection = (now - incident.detected_at).total_seconds() / 60
                        if time_since_detection > protocol.auto_resolve_minutes:
                            await self.resolve_incident(
                                incident.id,
                                "Auto-resolvido por timeout",
                                "system"
                            )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Erro no monitor de incidentes: {e}")

    async def _handle_alert(self, alert: Dict[str, Any]) -> None:
        """Processa alerta recebido e cria incidente se necessario."""
        try:
            alert_type = alert.get("type", "unknown")
            severity = alert.get("severity", "medium")

            # Mapear tipo de alerta para tipo de incidente
            incident_type = self._map_alert_to_incident_type(alert_type)

            # Criar incidente
            incident = await self.create_incident(
                incident_type=incident_type,
                severity=self._map_severity(severity),
                title=f"Alerta: {alert_type}",
                description=alert.get("description", ""),
                location=alert.get("location", "desconhecido"),
                related_alerts=[alert.get("id", "")],
                metadata=alert
            )

            logger.info(f"Incidente {incident.id} criado a partir de alerta {alert.get('id')}")

        except Exception as e:
            logger.error(f"Erro ao processar alerta: {e}")

    async def _handle_incident_request(self, request: Dict[str, Any]) -> None:
        """Processa solicitacao de criacao de incidente."""
        try:
            await self.create_incident(
                incident_type=IncidentType(request.get("type", "system_alert")),
                severity=IncidentSeverity(request.get("severity", "medium")),
                title=request.get("title", "Incidente Manual"),
                description=request.get("description", ""),
                location=request.get("location", ""),
                metadata=request.get("metadata", {})
            )
        except Exception as e:
            logger.error(f"Erro ao criar incidente: {e}")

    async def _handle_acknowledge(self, data: Dict[str, Any]) -> None:
        """Processa reconhecimento de incidente."""
        incident_id = data.get("incident_id")
        user_id = data.get("user_id", "unknown")

        if incident_id and incident_id in self.active_incidents:
            await self.acknowledge_incident(incident_id, user_id)

    async def _handle_resolve(self, data: Dict[str, Any]) -> None:
        """Processa resolucao de incidente."""
        incident_id = data.get("incident_id")
        resolution = data.get("resolution", "")
        user_id = data.get("user_id", "unknown")

        if incident_id and incident_id in self.active_incidents:
            await self.resolve_incident(incident_id, resolution, user_id)

    def _map_alert_to_incident_type(self, alert_type: str) -> IncidentType:
        """Mapeia tipo de alerta para tipo de incidente."""
        mapping = {
            "intrusion_detected": IncidentType.INTRUSION,
            "person_detected": IncidentType.SUSPICIOUS_ACTIVITY,
            "unauthorized_vehicle": IncidentType.UNAUTHORIZED_ACCESS,
            "access_denied": IncidentType.UNAUTHORIZED_ACCESS,
            "camera_offline": IncidentType.EQUIPMENT_FAILURE,
            "face_mismatch": IncidentType.SECURITY_BREACH,
            "loitering": IncidentType.SUSPICIOUS_ACTIVITY,
            "fence_breach": IncidentType.INTRUSION,
            "fire_detected": IncidentType.FIRE,
            "medical_emergency": IncidentType.MEDICAL
        }
        return mapping.get(alert_type, IncidentType.SYSTEM_ALERT)

    def _map_severity(self, severity: str) -> IncidentSeverity:
        """Mapeia string de severidade para enum."""
        mapping = {
            "low": IncidentSeverity.LOW,
            "medium": IncidentSeverity.MEDIUM,
            "high": IncidentSeverity.HIGH,
            "critical": IncidentSeverity.CRITICAL
        }
        return mapping.get(severity.lower(), IncidentSeverity.MEDIUM)

    def _get_protocol_for_incident(self, incident: Incident) -> Optional[ResponseProtocol]:
        """Obtem protocolo de resposta para um incidente."""
        for protocol in self.protocols.values():
            if protocol.incident_type == incident.type:
                return protocol
        return None

    async def create_incident(
        self,
        incident_type: IncidentType,
        severity: IncidentSeverity,
        title: str,
        description: str,
        location: str,
        related_alerts: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Incident:
        """Cria um novo incidente."""
        incident_id = f"INC-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"

        incident = Incident(
            id=incident_id,
            type=incident_type,
            severity=severity,
            status=IncidentStatus.DETECTED,
            title=title,
            description=description,
            location=location,
            detected_at=datetime.now(),
            related_alerts=related_alerts or [],
            metadata=metadata or {}
        )

        # Adicionar evento inicial ao timeline
        incident.timeline.append({
            "timestamp": datetime.now().isoformat(),
            "event": "incident_created",
            "description": f"Incidente detectado: {title}",
            "user": "system"
        })

        # Armazenar incidente
        self.active_incidents[incident_id] = incident

        # Executar protocolo de resposta
        await self._execute_response_protocol(incident)

        # Publicar evento
        if self.message_bus:
            await self.message_bus.publish("incident.created", {
                "id": incident.id,
                "type": incident.type.value,
                "severity": incident.severity.value,
                "title": incident.title,
                "location": incident.location,
                "detected_at": incident.detected_at.isoformat()
            })

        logger.info(f"Incidente criado: {incident_id} - {title}")
        return incident

    async def _execute_response_protocol(self, incident: Incident) -> None:
        """Executa protocolo de resposta para um incidente."""
        protocol = self._get_protocol_for_incident(incident)
        if not protocol:
            logger.warning(f"Nenhum protocolo encontrado para incidente tipo {incident.type}")
            return

        # Executar acoes do protocolo
        for action_config in protocol.actions:
            try:
                action_type = action_config["type"]
                if isinstance(action_type, str):
                    action_type = ActionType(action_type)

                action = ResponseAction(
                    id=f"action_{uuid.uuid4().hex[:8]}",
                    type=action_type,
                    target=action_config.get("target", ""),
                    parameters=action_config
                )

                # Verificar delay
                delay = action_config.get("delay", 0)
                if delay > 0:
                    await asyncio.sleep(delay)

                # Executar acao
                await self._execute_action(action, incident)
                incident.actions_taken.append(action)

            except Exception as e:
                logger.error(f"Erro ao executar acao {action_config}: {e}")

        # Enviar notificacoes
        for notif_config in protocol.notifications:
            try:
                await self._send_notification(
                    incident,
                    NotificationChannel(notif_config["channel"]),
                    notif_config.get("template", "default"),
                    notif_config.get("priority", "medium")
                )
            except Exception as e:
                logger.error(f"Erro ao enviar notificacao: {e}")

        # Iniciar primeiro nivel de escalonamento se requer acknowledgment
        if protocol.requires_acknowledgment and protocol.escalation_levels:
            await self._start_escalation(incident, protocol.escalation_levels[0])

    async def _execute_action(self, action: ResponseAction, incident: Incident) -> None:
        """Executa uma acao de resposta."""
        handler = self.action_handlers.get(action.type)
        if handler:
            try:
                result = await handler(action, incident)
                action.executed_at = datetime.now()
                action.result = result
                action.success = True

                # Adicionar ao timeline
                incident.timeline.append({
                    "timestamp": datetime.now().isoformat(),
                    "event": "action_executed",
                    "description": f"Acao executada: {action.type.value} em {action.target}",
                    "action_id": action.id,
                    "result": result
                })

            except Exception as e:
                action.executed_at = datetime.now()
                action.result = str(e)
                action.success = False
                logger.error(f"Erro ao executar acao {action.type}: {e}")
        else:
            logger.warning(f"Handler nao encontrado para acao {action.type}")

    # Handlers de acao
    async def _execute_notify(self, action: ResponseAction, incident: Incident) -> str:
        """Executa notificacao."""
        logger.info(f"Notificando: {action.target}")
        return "Notificacao enviada"

    async def _execute_alert(self, action: ResponseAction, incident: Incident) -> str:
        """Executa alerta no dashboard."""
        if self.message_bus:
            await self.message_bus.publish("dashboard.alert", {
                "incident_id": incident.id,
                "severity": incident.severity.value,
                "message": incident.title,
                "location": incident.location
            })
        return "Alerta exibido no dashboard"

    async def _execute_lock_access(self, action: ResponseAction, incident: Incident) -> str:
        """Executa bloqueio de acesso."""
        if self.message_bus:
            await self.message_bus.publish("access.lock", {
                "target": action.target,
                "reason": f"Incidente {incident.id}",
                "incident_id": incident.id
            })
        logger.info(f"Bloqueando acesso: {action.target}")
        return f"Acesso bloqueado: {action.target}"

    async def _execute_unlock_access(self, action: ResponseAction, incident: Incident) -> str:
        """Executa desbloqueio de acesso."""
        if self.message_bus:
            await self.message_bus.publish("access.unlock", {
                "target": action.target,
                "reason": f"Emergencia - Incidente {incident.id}",
                "incident_id": incident.id
            })
        logger.info(f"Desbloqueando acesso: {action.target}")
        return f"Acesso desbloqueado: {action.target}"

    async def _execute_activate_alarm(self, action: ResponseAction, incident: Incident) -> str:
        """Ativa alarme."""
        if self.message_bus:
            await self.message_bus.publish("alarm.activate", {
                "target": action.target,
                "type": "security",
                "incident_id": incident.id
            })
        logger.warning(f"Alarme ativado: {action.target}")
        return "Alarme ativado"

    async def _execute_deactivate_alarm(self, action: ResponseAction, incident: Incident) -> str:
        """Desativa alarme."""
        if self.message_bus:
            await self.message_bus.publish("alarm.deactivate", {
                "target": action.target,
                "incident_id": incident.id
            })
        logger.info(f"Alarme desativado: {action.target}")
        return "Alarme desativado"

    async def _execute_record_video(self, action: ResponseAction, incident: Incident) -> str:
        """Inicia gravacao de video."""
        duration = action.parameters.get("duration", 300)
        if self.message_bus:
            await self.message_bus.publish("camera.record", {
                "target": action.target,
                "duration": duration,
                "incident_id": incident.id,
                "priority": "high"
            })

        # Adicionar evidencia
        incident.evidence.append({
            "type": "video_recording",
            "target": action.target,
            "started_at": datetime.now().isoformat(),
            "duration": duration
        })

        return f"Gravacao iniciada: {action.target} por {duration}s"

    async def _execute_dispatch_security(self, action: ResponseAction, incident: Incident) -> str:
        """Despacha equipe de seguranca."""
        if self.message_bus:
            await self.message_bus.publish("security.dispatch", {
                "location": incident.location,
                "incident_id": incident.id,
                "priority": incident.severity.value
            })
        logger.warning(f"Seguranca despachada para: {incident.location}")
        return f"Seguranca despachada para {incident.location}"

    async def _execute_call_emergency(self, action: ResponseAction, incident: Incident) -> str:
        """Aciona servicos de emergencia."""
        services = []
        if incident.type == IncidentType.FIRE:
            services.append("193")  # Bombeiros
        if incident.type == IncidentType.MEDICAL:
            services.append("192")  # SAMU
        if incident.type in [IncidentType.INTRUSION, IncidentType.EMERGENCY]:
            services.append("190")  # Policia

        if self.message_bus:
            await self.message_bus.publish("emergency.call", {
                "services": services,
                "incident_id": incident.id,
                "location": incident.location
            })

        logger.critical(f"Servicos de emergencia acionados: {services}")
        return f"Servicos acionados: {', '.join(services)}"

    async def _execute_isolate_area(self, action: ResponseAction, incident: Incident) -> str:
        """Isola area afetada."""
        if self.message_bus:
            await self.message_bus.publish("area.isolate", {
                "target": action.target,
                "incident_id": incident.id
            })
        return f"Area isolada: {action.target}"

    async def _execute_log_event(self, action: ResponseAction, incident: Incident) -> str:
        """Registra evento em log."""
        log_target = action.target
        logger.info(f"Evento registrado em {log_target}: Incidente {incident.id}")
        return f"Evento registrado em {log_target}"

    async def _execute_escalate(self, action: ResponseAction, incident: Incident) -> str:
        """Executa escalonamento."""
        await self._auto_escalate(incident)
        return "Incidente escalonado"

    async def _send_notification(
        self,
        incident: Incident,
        channel: NotificationChannel,
        template: str,
        priority: str
    ) -> None:
        """Envia notificacao."""
        # Construir mensagem baseada no template
        message = self._build_notification_message(incident, template)

        notification = Notification(
            id=f"notif_{uuid.uuid4().hex[:8]}",
            channel=channel,
            recipient="all",  # Em producao, seria lista de destinatarios
            message=message,
            sent_at=datetime.now(),
            delivered=True
        )

        incident.notifications_sent.append(notification)

        if self.message_bus:
            await self.message_bus.publish("notification.send", {
                "channel": channel.value,
                "message": message,
                "priority": priority,
                "incident_id": incident.id
            })

        logger.info(f"Notificacao enviada via {channel.value}")

    def _build_notification_message(self, incident: Incident, template: str) -> str:
        """Constroi mensagem de notificacao."""
        templates = {
            "intrusion_alert": f"ALERTA DE INTRUSAO: {incident.title} em {incident.location}. "
                              f"Severidade: {incident.severity.value.upper()}",
            "intrusion_sms": f"[SEGURANCA] Intrusao detectada em {incident.location}. "
                            f"Verifique imediatamente. ID: {incident.id}",
            "emergency_call": f"Emergencia em {incident.location}. {incident.description}",
            "access_denied_alert": f"Acesso negado em {incident.location}. {incident.description}",
            "suspicious_alert": f"Atividade suspeita em {incident.location}. {incident.title}",
            "equipment_failure": f"Falha de equipamento: {incident.title} em {incident.location}",
            "emergency_broadcast": f"ATENCAO: Emergencia em andamento. {incident.description}. "
                                  f"Siga os procedimentos de seguranca.",
            "emergency_sms": f"[EMERGENCIA] {incident.type.value.upper()} em {incident.location}. "
                            f"Acoes em andamento.",
            "default": f"Incidente {incident.id}: {incident.title} em {incident.location}"
        }
        return templates.get(template, templates["default"])

    async def _start_escalation(self, incident: Incident, level: EscalationLevel) -> None:
        """Inicia escalonamento para um nivel."""
        incident.escalation_level = level.level

        incident.timeline.append({
            "timestamp": datetime.now().isoformat(),
            "event": "escalation_started",
            "description": f"Escalonamento iniciado: Nivel {level.level} - {level.name}",
            "level": level.level
        })

        # Notificar contatos do nivel
        for contact in level.contacts:
            if self.message_bus:
                await self.message_bus.publish("notification.escalation", {
                    "incident_id": incident.id,
                    "level": level.level,
                    "contact": contact,
                    "message": f"Incidente {incident.id} aguarda atencao"
                })

    async def _check_escalation(self, incident: Incident) -> None:
        """Verifica se incidente precisa ser escalonado."""
        protocol = self._get_protocol_for_incident(incident)
        if not protocol:
            return

        current_level = incident.escalation_level
        if current_level >= len(protocol.escalation_levels):
            return

        level_config = protocol.escalation_levels[current_level]

        # Verificar se passou timeout do nivel atual
        if incident.acknowledged_at:
            time_reference = incident.acknowledged_at
        else:
            time_reference = incident.detected_at

        elapsed_minutes = (datetime.now() - time_reference).total_seconds() / 60

        if elapsed_minutes > level_config.timeout_minutes and level_config.auto_escalate:
            await self._auto_escalate(incident)

    async def _auto_escalate(self, incident: Incident) -> None:
        """Escala incidente automaticamente."""
        protocol = self._get_protocol_for_incident(incident)
        if not protocol:
            return

        next_level = incident.escalation_level + 1
        if next_level > len(protocol.escalation_levels):
            logger.warning(f"Incidente {incident.id} ja esta no nivel maximo de escalonamento")
            return

        if next_level <= len(protocol.escalation_levels):
            level = protocol.escalation_levels[next_level - 1]
            await self._start_escalation(incident, level)

            incident.status = IncidentStatus.ESCALATED

            if self.message_bus:
                await self.message_bus.publish("incident.escalated", {
                    "incident_id": incident.id,
                    "level": next_level,
                    "level_name": level.name
                })

            logger.warning(f"Incidente {incident.id} escalonado para nivel {next_level}")

    async def acknowledge_incident(self, incident_id: str, user_id: str) -> bool:
        """Reconhece um incidente."""
        if incident_id not in self.active_incidents:
            return False

        incident = self.active_incidents[incident_id]
        incident.status = IncidentStatus.ACKNOWLEDGED
        incident.acknowledged_at = datetime.now()
        incident.assigned_to = user_id

        incident.timeline.append({
            "timestamp": datetime.now().isoformat(),
            "event": "incident_acknowledged",
            "description": f"Incidente reconhecido por {user_id}",
            "user": user_id
        })

        if self.message_bus:
            await self.message_bus.publish("incident.acknowledged", {
                "incident_id": incident_id,
                "user_id": user_id,
                "acknowledged_at": incident.acknowledged_at.isoformat()
            })

        logger.info(f"Incidente {incident_id} reconhecido por {user_id}")
        return True

    async def resolve_incident(
        self,
        incident_id: str,
        resolution: str,
        user_id: str
    ) -> bool:
        """Resolve um incidente."""
        if incident_id not in self.active_incidents:
            return False

        incident = self.active_incidents[incident_id]
        incident.status = IncidentStatus.RESOLVED
        incident.resolved_at = datetime.now()

        incident.timeline.append({
            "timestamp": datetime.now().isoformat(),
            "event": "incident_resolved",
            "description": f"Incidente resolvido: {resolution}",
            "user": user_id,
            "resolution": resolution
        })

        if self.message_bus:
            await self.message_bus.publish("incident.resolved", {
                "incident_id": incident_id,
                "user_id": user_id,
                "resolution": resolution,
                "resolved_at": incident.resolved_at.isoformat()
            })

        logger.info(f"Incidente {incident_id} resolvido por {user_id}")
        return True

    async def close_incident(self, incident_id: str, user_id: str) -> bool:
        """Fecha um incidente."""
        if incident_id not in self.active_incidents:
            return False

        incident = self.active_incidents[incident_id]
        incident.status = IncidentStatus.CLOSED
        incident.closed_at = datetime.now()

        incident.timeline.append({
            "timestamp": datetime.now().isoformat(),
            "event": "incident_closed",
            "description": "Incidente fechado",
            "user": user_id
        })

        # Mover para historico
        self.incident_history.append(incident)
        del self.active_incidents[incident_id]

        if self.message_bus:
            await self.message_bus.publish("incident.closed", {
                "incident_id": incident_id,
                "closed_at": incident.closed_at.isoformat()
            })

        logger.info(f"Incidente {incident_id} fechado")
        return True

    # API publica
    async def get_active_incidents(
        self,
        severity: Optional[IncidentSeverity] = None
    ) -> List[Incident]:
        """Retorna incidentes ativos."""
        incidents = list(self.active_incidents.values())
        if severity:
            incidents = [i for i in incidents if i.severity == severity]
        return sorted(incidents, key=lambda x: x.detected_at, reverse=True)

    async def get_incident(self, incident_id: str) -> Optional[Incident]:
        """Retorna um incidente especifico."""
        return self.active_incidents.get(incident_id)

    async def get_incident_timeline(self, incident_id: str) -> List[Dict[str, Any]]:
        """Retorna timeline de um incidente."""
        incident = self.active_incidents.get(incident_id)
        if incident:
            return incident.timeline
        return []

    async def get_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """Retorna estatisticas de incidentes."""
        cutoff = datetime.now() - timedelta(hours=hours)

        all_incidents = list(self.active_incidents.values()) + [
            i for i in self.incident_history
            if i.detected_at > cutoff
        ]

        return {
            "total": len(all_incidents),
            "active": len(self.active_incidents),
            "by_severity": {
                s.value: len([i for i in all_incidents if i.severity == s])
                for s in IncidentSeverity
            },
            "by_type": {
                t.value: len([i for i in all_incidents if i.type == t])
                for t in IncidentType
            },
            "avg_response_time": self._calculate_avg_response_time(all_incidents),
            "period_hours": hours
        }

    def _calculate_avg_response_time(self, incidents: List[Incident]) -> float:
        """Calcula tempo medio de resposta."""
        response_times = []
        for incident in incidents:
            if incident.acknowledged_at:
                delta = (incident.acknowledged_at - incident.detected_at).total_seconds()
                response_times.append(delta)

        if response_times:
            return sum(response_times) / len(response_times)
        return 0.0
