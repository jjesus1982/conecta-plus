#!/usr/bin/env python3
"""
Teste da API Guardian - Servidor Standalone
Executa apenas os endpoints Guardian sem dependencias do banco
"""

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import sys
import os

# Adicionar path do projeto
sys.path.insert(0, '/opt/conecta-plus')

# Importar schemas e service diretamente (sem dependencias do banco)
from backend.schemas.guardian import (
    AlertSeverity, AlertType, AlertCreate, AlertResponse,
    IncidentSeverity, IncidentType, IncidentStatus, IncidentCreate, IncidentResponse,
    RiskLevel, RiskAssessmentResponse, RiskFactor,
    DashboardResponse, AccessStats,
    ChatRequest, ChatResponse,
    AlertListResponse, IncidentListResponse,
    TriggerAlarmRequest, DispatchSecurityRequest, ActionResponse,
    StatisticsResponse, AlertStatistics, IncidentStatistics
)
from backend.services.guardian import GuardianService
from datetime import datetime
from typing import Optional, List
import uuid

# Criar app FastAPI para teste
app = FastAPI(
    title="Guardian API Test",
    version="2.0.0",
    description="Servidor de teste para API Guardian"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instancia do servico Guardian
guardian_service = GuardianService()


# ==================== ENDPOINTS ====================

@app.get("/")
async def root():
    return {
        "name": "Guardian API Test",
        "version": "2.0.0",
        "status": "online",
        "endpoints": {
            "status": "/api/v1/guardian/status",
            "dashboard": "/api/v1/guardian/dashboard",
            "alerts": "/api/v1/guardian/alerts",
            "incidents": "/api/v1/guardian/incidents",
            "risk": "/api/v1/guardian/risk",
            "chat": "/api/v1/guardian/chat",
        }
    }


@app.get("/api/v1/guardian/status")
async def get_status():
    """Status do sistema Guardian."""
    return {
        "status": "operational",
        "version": "2.0.0",
        "uptime_seconds": 3600.0,
        "agents": {
            "monitor": "running",
            "access": "running",
            "analytics": "running",
            "assistant": "running",
            "response": "running"
        },
        "integrations": {
            "frigate": "connected",
            "control_id": "connected",
            "notifications": "ready"
        },
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/v1/guardian/dashboard", response_model=DashboardResponse)
async def get_dashboard():
    """Dashboard consolidado do Guardian."""
    return DashboardResponse(
        system_status="operational",
        uptime_seconds=3600.0,
        risk_score=35.5,
        risk_level="moderate",
        risk_trend="stable",
        active_alerts=3,
        active_incidents=1,
        critical_incidents=0,
        cameras_online=23,
        cameras_total=24,
        access_24h=AccessStats(granted=1250, denied=15),
        recommendations=[
            "Revisar camera CAM-B04 offline",
            "Verificar alertas pendentes"
        ],
        timestamp=datetime.now().isoformat()
    )


@app.get("/api/v1/guardian/alerts", response_model=AlertListResponse)
async def list_alerts(
    severity: Optional[str] = None,
    type: Optional[str] = None,
    acknowledged: Optional[bool] = None,
    limit: int = 50
):
    """Lista alertas ativos."""
    # Dados de exemplo
    alerts = [
        AlertResponse(
            id=f"ALT-{datetime.now().strftime('%Y%m%d')}-001",
            type=AlertType.PERSON,
            severity=AlertSeverity.MEDIUM,
            title="Pessoa detectada na area restrita",
            description="Deteccao de pessoa no estacionamento B",
            location="Bloco B - Estacionamento",
            camera_id="cam_b01",
            timestamp=datetime.now().isoformat(),
            acknowledged=False,
            metadata={"confidence": 0.92}
        ),
        AlertResponse(
            id=f"ALT-{datetime.now().strftime('%Y%m%d')}-002",
            type=AlertType.VEHICLE,
            severity=AlertSeverity.LOW,
            title="Veiculo nao identificado",
            description="Placa nao cadastrada tentou entrada",
            location="Portaria Principal",
            camera_id="cam_port01",
            timestamp=datetime.now().isoformat(),
            acknowledged=True,
            acknowledged_by="operador1",
            acknowledged_at=datetime.now().isoformat(),
            metadata={"plate": "ABC1234"}
        ),
        AlertResponse(
            id=f"ALT-{datetime.now().strftime('%Y%m%d')}-003",
            type=AlertType.EQUIPMENT,
            severity=AlertSeverity.HIGH,
            title="Camera offline",
            description="Camera CAM-B04 nao responde",
            location="Bloco B - Corredor",
            camera_id="cam_b04",
            timestamp=datetime.now().isoformat(),
            acknowledged=False,
            metadata={"last_seen": "2025-12-20T10:30:00"}
        )
    ]

    return AlertListResponse(alerts=alerts, total=len(alerts))


@app.post("/api/v1/guardian/alerts", response_model=AlertResponse)
async def create_alert(alert: AlertCreate):
    """Cria novo alerta."""
    return AlertResponse(
        id=f"ALT-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}",
        type=alert.type,
        severity=alert.severity,
        title=alert.title,
        description=alert.description,
        location=alert.location,
        camera_id=alert.camera_id,
        timestamp=datetime.now().isoformat(),
        acknowledged=False,
        metadata=alert.metadata or {}
    )


@app.get("/api/v1/guardian/incidents", response_model=IncidentListResponse)
async def list_incidents(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 50
):
    """Lista incidentes."""
    incidents = [
        IncidentResponse(
            id=f"INC-{datetime.now().strftime('%Y%m%d')}-001",
            type=IncidentType.SUSPICIOUS_ACTIVITY,
            severity=IncidentSeverity.MEDIUM,
            status=IncidentStatus.IN_PROGRESS,
            title="Atividade suspeita detectada",
            description="Multiplas deteccoes de pessoa em horario nao usual",
            location="Bloco B",
            detected_at=datetime.now().isoformat(),
            assigned_to="security_team",
            escalation_level=1,
            timeline=[]
        )
    ]

    return IncidentListResponse(incidents=incidents, total=len(incidents))


@app.post("/api/v1/guardian/incidents", response_model=IncidentResponse)
async def create_incident(incident: IncidentCreate):
    """Cria novo incidente."""
    return IncidentResponse(
        id=f"INC-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}",
        type=incident.type,
        severity=incident.severity,
        status=IncidentStatus.DETECTED,
        title=incident.title,
        description=incident.description,
        location=incident.location,
        detected_at=datetime.now().isoformat(),
        escalation_level=0,
        timeline=[]
    )


@app.get("/api/v1/guardian/risk", response_model=RiskAssessmentResponse)
async def get_risk_assessment():
    """Avaliacao de risco atual."""
    return RiskAssessmentResponse(
        score=35.5,
        level=RiskLevel.MODERATE,
        trend="stable",
        factors=[
            RiskFactor(
                name="Alertas Pendentes",
                contribution=15.0,
                detail="3 alertas nao reconhecidos"
            ),
            RiskFactor(
                name="Camera Offline",
                contribution=10.0,
                detail="1 camera sem resposta"
            ),
            RiskFactor(
                name="Horario Padrao",
                contribution=5.0,
                detail="Operacao em horario comercial"
            ),
            RiskFactor(
                name="Incidente Ativo",
                contribution=5.5,
                detail="1 incidente em andamento"
            )
        ],
        recommendations=[
            "Verificar camera CAM-B04 offline",
            "Revisar alertas pendentes",
            "Manter vigilancia no Bloco B"
        ],
        assessed_at=datetime.now().isoformat()
    )


@app.post("/api/v1/guardian/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat com assistente Guardian."""
    message = request.message.lower()

    if "status" in message:
        response = """Sistema Guardian operando normalmente.

📊 **Resumo:**
- 23/24 cameras online
- 3 alertas ativos (0 criticos)
- 1 incidente em andamento
- Score de risco: 35.5/100 (moderado)

Todas as integracoes funcionando corretamente."""
        suggestions = ["Ver alertas", "Ver incidentes", "Avaliar risco"]

    elif "alerta" in message:
        response = """📢 **Alertas Ativos:**

1. **Pessoa detectada** (medio) - Bloco B Estacionamento
2. **Veiculo nao identificado** (baixo) - Portaria Principal
3. **Camera offline** (alto) - Bloco B Corredor

Deseja ver detalhes de algum alerta?"""
        suggestions = ["Detalhes alerta 1", "Reconhecer alertas", "Despachar seguranca"]

    elif "risco" in message:
        response = """🎯 **Avaliacao de Risco:**

Score atual: **35.5/100** (Moderado)
Tendencia: ➡️ Estavel

**Fatores:**
- Alertas pendentes: +15.0
- Camera offline: +10.0
- Incidente ativo: +5.5

**Recomendacoes:**
1. Verificar camera CAM-B04
2. Revisar alertas pendentes"""
        suggestions = ["Historico de risco", "Acionar equipe", "Ver cameras"]

    else:
        response = f"""Entendi sua mensagem: "{request.message}"

Sou o Guardian, assistente de seguranca do Conecta Plus.

Posso ajudar com:
- Status do sistema
- Gestao de alertas
- Gestao de incidentes
- Avaliacao de risco
- Acoes de seguranca

Como posso ajudar?"""
        suggestions = ["Ver status", "Listar alertas", "Avaliar risco"]

    return ChatResponse(
        response=response,
        suggestions=suggestions,
        session_id=request.session_id or str(uuid.uuid4())
    )


@app.post("/api/v1/guardian/actions/alarm/trigger", response_model=ActionResponse)
async def trigger_alarm(request: TriggerAlarmRequest):
    """Aciona alarme."""
    return ActionResponse(
        success=True,
        message=f"Alarme {request.type.value} acionado na area {request.area}",
        action_id=f"ACT-{uuid.uuid4().hex[:8].upper()}"
    )


@app.post("/api/v1/guardian/actions/dispatch", response_model=ActionResponse)
async def dispatch_security(request: DispatchSecurityRequest):
    """Despacha equipe de seguranca."""
    return ActionResponse(
        success=True,
        message=f"Equipe despachada para {request.location} com prioridade {request.priority.value}",
        action_id=f"DSP-{uuid.uuid4().hex[:8].upper()}"
    )


@app.get("/api/v1/guardian/statistics", response_model=StatisticsResponse)
async def get_statistics(period_hours: int = 24):
    """Estatisticas do periodo."""
    return StatisticsResponse(
        period_hours=period_hours,
        alerts=AlertStatistics(
            total=45,
            by_severity={"low": 20, "medium": 18, "high": 5, "critical": 2},
            by_type={"person_detected": 25, "vehicle_detected": 10, "equipment_failure": 5, "other": 5},
            acknowledged=38,
            pending=7
        ),
        incidents=IncidentStatistics(
            total=8,
            by_severity={"low": 2, "medium": 4, "high": 2, "critical": 0},
            by_type={"intrusion": 1, "suspicious_activity": 3, "equipment_failure": 2, "unauthorized_access": 2},
            by_status={"resolved": 6, "in_progress": 1, "detected": 1},
            avg_response_time_seconds=180.5
        ),
        timestamp=datetime.now().isoformat()
    )


if __name__ == "__main__":
    print("=" * 60)
    print("Guardian API Test Server")
    print("=" * 60)
    print()
    print("Iniciando servidor de teste na porta 8001...")
    print()
    print("Endpoints disponiveis:")
    print("  GET  /                           - Info do servidor")
    print("  GET  /api/v1/guardian/status     - Status do Guardian")
    print("  GET  /api/v1/guardian/dashboard  - Dashboard")
    print("  GET  /api/v1/guardian/alerts     - Lista alertas")
    print("  POST /api/v1/guardian/alerts     - Cria alerta")
    print("  GET  /api/v1/guardian/incidents  - Lista incidentes")
    print("  POST /api/v1/guardian/incidents  - Cria incidente")
    print("  GET  /api/v1/guardian/risk       - Avaliacao de risco")
    print("  POST /api/v1/guardian/chat       - Chat com assistente")
    print("  POST /api/v1/guardian/actions/*  - Acoes de seguranca")
    print("  GET  /api/v1/guardian/statistics - Estatisticas")
    print()
    print("=" * 60)

    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")
