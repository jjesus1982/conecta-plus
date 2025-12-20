"""
Conecta Plus - Guardian Schemas
Schemas Pydantic para API Guardian
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


# ==================== Enums ====================

class AlertSeverity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertType(str, Enum):
    INTRUSION = "intrusion_detected"
    PERSON = "person_detected"
    VEHICLE = "vehicle_detected"
    LOITERING = "loitering"
    UNAUTHORIZED = "unauthorized_access"
    EQUIPMENT = "equipment_failure"
    SUSPICIOUS = "suspicious_activity"
    CUSTOM = "custom"


class IncidentSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentType(str, Enum):
    INTRUSION = "intrusion"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    EQUIPMENT_FAILURE = "equipment_failure"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    EMERGENCY = "emergency"
    VANDALISM = "vandalism"
    FIRE = "fire"
    MEDICAL = "medical"


class IncidentStatus(str, Enum):
    DETECTED = "detected"
    ACKNOWLEDGED = "acknowledged"
    IN_PROGRESS = "in_progress"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    CLOSED = "closed"


class RiskLevel(str, Enum):
    MINIMAL = "minimal"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class AlarmType(str, Enum):
    SECURITY = "security"
    FIRE = "fire"
    EMERGENCY = "emergency"


class DispatchPriority(str, Enum):
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


# ==================== Alert Schemas ====================

class AlertBase(BaseModel):
    type: AlertType
    severity: AlertSeverity
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    location: str = Field(..., min_length=1, max_length=200)
    camera_id: Optional[str] = None


class AlertCreate(AlertBase):
    metadata: Optional[Dict[str, Any]] = None


class AlertResponse(AlertBase):
    id: str
    timestamp: str
    acknowledged: bool
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[str] = None
    metadata: Dict[str, Any] = {}

    class Config:
        from_attributes = True


class AlertAcknowledge(BaseModel):
    notes: Optional[str] = Field(None, max_length=500)


class AlertDismiss(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)


class AlertListResponse(BaseModel):
    alerts: List[AlertResponse]
    total: int


# ==================== Incident Schemas ====================

class IncidentBase(BaseModel):
    type: IncidentType
    severity: IncidentSeverity
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    location: str = Field(..., min_length=1, max_length=200)


class IncidentCreate(IncidentBase):
    metadata: Optional[Dict[str, Any]] = None


class TimelineEvent(BaseModel):
    timestamp: str
    event: str
    description: str
    user: Optional[str] = None


class IncidentResponse(IncidentBase):
    id: str
    status: IncidentStatus
    detected_at: str
    acknowledged_at: Optional[str] = None
    resolved_at: Optional[str] = None
    assigned_to: Optional[str] = None
    escalation_level: int = 0
    timeline: List[TimelineEvent] = []

    class Config:
        from_attributes = True


class IncidentUpdate(BaseModel):
    status: IncidentStatus
    notes: Optional[str] = Field(None, max_length=500)


class IncidentResolve(BaseModel):
    resolution: str = Field(..., min_length=1, max_length=1000)


class IncidentListResponse(BaseModel):
    incidents: List[IncidentResponse]
    total: int


# ==================== Risk Schemas ====================

class RiskFactor(BaseModel):
    name: str
    contribution: float
    detail: str


class RiskAssessmentResponse(BaseModel):
    score: float = Field(..., ge=0, le=100)
    level: RiskLevel
    trend: str
    factors: List[RiskFactor]
    recommendations: List[str]
    assessed_at: str


# ==================== Dashboard Schemas ====================

class AccessStats(BaseModel):
    granted: int
    denied: int


class DashboardResponse(BaseModel):
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
    access_24h: AccessStats
    recommendations: List[str]
    timestamp: str


# ==================== Chat Schemas ====================

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    suggestions: List[str] = []
    session_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


# ==================== Action Schemas ====================

class TriggerAlarmRequest(BaseModel):
    area: str = Field(..., min_length=1, max_length=100)
    type: AlarmType
    reason: str = Field(..., min_length=1, max_length=500)


class DeactivateAlarmRequest(BaseModel):
    area: str = Field(..., min_length=1, max_length=100)


class DispatchSecurityRequest(BaseModel):
    location: str = Field(..., min_length=1, max_length=200)
    priority: DispatchPriority
    reason: str = Field(..., min_length=1, max_length=500)


class LockAccessRequest(BaseModel):
    access_point: str = Field(..., min_length=1, max_length=100)
    reason: str = Field(..., min_length=1, max_length=500)
    duration_minutes: Optional[int] = Field(None, ge=1, le=1440)


class UnlockAccessRequest(BaseModel):
    access_point: str = Field(..., min_length=1, max_length=100)


class ActionResponse(BaseModel):
    success: bool
    message: str
    action_id: Optional[str] = None


# ==================== Statistics Schemas ====================

class StatisticsRequest(BaseModel):
    period_hours: int = Field(24, ge=1, le=720)


class IncidentStatistics(BaseModel):
    total: int
    by_severity: Dict[str, int]
    by_type: Dict[str, int]
    by_status: Dict[str, int]
    avg_response_time_seconds: float


class AlertStatistics(BaseModel):
    total: int
    by_severity: Dict[str, int]
    by_type: Dict[str, int]
    acknowledged: int
    pending: int


class StatisticsResponse(BaseModel):
    period_hours: int
    alerts: AlertStatistics
    incidents: IncidentStatistics
    timestamp: str


# ==================== WebSocket Schemas ====================

class WebSocketMessage(BaseModel):
    type: str
    data: Dict[str, Any]
    timestamp: str
