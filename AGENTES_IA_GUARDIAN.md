# AGENTES DE IA GUARDIAN - FASE 3
## Sistema de Agentes Inteligentes para Seguranca Eletronica

**Data:** 2025-12-20
**Versao:** 2.0.0
**Modulo:** agents/guardian/

---

## VISAO GERAL

O sistema Guardian implementa uma arquitetura de agentes de IA de **Nivel 7 (TRANSCENDENT)** para seguranca eletronica inteligente. Os agentes trabalham de forma coordenada atraves de um Message Bus centralizado e um Orquestrador que gerencia o ciclo de vida de todo o sistema.

### Arquitetura

```
                    ┌──────────────────────┐
                    │  GuardianOrchestrator │
                    │   (Orquestrador)      │
                    └──────────┬───────────┘
                               │
                    ┌──────────┴───────────┐
                    │     Message Bus       │
                    └──────────┬───────────┘
          ┌────────────────────┼────────────────────┐
          │         │          │          │         │
    ┌─────┴─────┐ ┌─┴──────┐ ┌─┴───────┐ ┌┴───────┐ ┌┴────────┐
    │  Monitor  │ │ Access │ │Analytics│ │Response│ │Assistant│
    │   Agent   │ │ Agent  │ │  Agent  │ │ Agent  │ │  Agent  │
    └───────────┘ └────────┘ └─────────┘ └────────┘ └─────────┘
```

---

## AGENTES IMPLEMENTADOS

### 1. GuardianMonitorAgent
**Arquivo:** `agents/guardian/monitor_agent.py`
**Funcao:** Monitoramento inteligente de cameras e deteccao de eventos

#### Capacidades:
- Processamento de eventos de deteccao (YOLO, Frigate)
- Analise contextual de cenas
- Geracao automatica de alertas
- Rastreamento de objetos/pessoas
- Integracao com CFTV

#### Classes Principais:
```python
class AlertType(Enum):
    INTRUSION_DETECTED, PERSON_DETECTED, VEHICLE_DETECTED,
    LOITERING, CROWD_DETECTED, OBJECT_LEFT, CAMERA_TAMPERING,
    FACE_DETECTED, UNAUTHORIZED_VEHICLE, FENCE_BREACH

class AlertSeverity(Enum):
    INFO, LOW, MEDIUM, HIGH, CRITICAL

class GuardianMonitorAgent:
    async def process(event_data: Dict) -> Optional[Alert]
    async def get_active_alerts() -> List[Alert]
    async def acknowledge_alert(alert_id: str) -> bool
```

#### Exemplo de Uso:
```python
monitor = GuardianMonitorAgent(message_bus=bus)
await monitor.start()

# Processar deteccao
alert = await monitor.process({
    "type": "person_detected",
    "camera_id": "cam_01",
    "confidence": 0.95,
    "location": "Entrada Principal"
})
```

---

### 2. GuardianAccessAgent
**Arquivo:** `agents/guardian/access_agent.py`
**Funcao:** Controle de acesso inteligente com biometria

#### Capacidades:
- Validacao de acesso por face (anti-spoofing)
- Reconhecimento de placas (ANPR/LPR)
- Validacao de cartoes e QR codes
- Deteccao de fraude e anomalias
- Aprendizado de padroes de acesso

#### Classes Principais:
```python
class CredentialType(Enum):
    FACE, CARD, PLATE, QR_CODE, BIOMETRIC, PIN

class AccessDecision(Enum):
    GRANTED, DENIED, PENDING_VERIFICATION, REQUIRES_ESCORT

class GuardianAccessAgent:
    async def validate_access(
        credential_type: CredentialType,
        credential_data: Dict,
        access_point_id: str
    ) -> AccessResult
```

#### Deteccao de Fraude:
- Liveness detection (anti-spoofing)
- Verificacao de blacklist
- Analise de padroes anomalos
- Tailgating detection
- Horario fora do padrao

#### Exemplo de Uso:
```python
access = GuardianAccessAgent(message_bus=bus)

result = await access.validate_access(
    credential_type=CredentialType.FACE,
    credential_data={
        "embedding": face_embedding,
        "image": face_image,
        "liveness_score": 0.98
    },
    access_point_id="portaria_principal"
)

if result.allowed:
    await liberar_catraca()
```

---

### 3. GuardianAnalyticsAgent
**Arquivo:** `agents/guardian/analytics_agent.py`
**Funcao:** Analise preditiva e deteccao de anomalias

#### Capacidades:
- Analise estatistica de eventos
- Deteccao de anomalias (Z-score, IQR)
- Previsao de incidentes
- Score de risco em tempo real
- Insights operacionais

#### Classes Principais:
```python
class RiskLevel(Enum):
    MINIMAL, LOW, MODERATE, HIGH, CRITICAL

class AnomalyType(Enum):
    FREQUENCY_SPIKE, UNUSUAL_TIMING, PATTERN_BREAK,
    GEOGRAPHIC_CLUSTER, BEHAVIORAL_DEVIATION

class PredictionType(Enum):
    INCIDENT_PROBABILITY, PEAK_ACTIVITY,
    VULNERABILITY_WINDOW, RESOURCE_NEED

class GuardianAnalyticsAgent:
    async def get_risk_assessment() -> RiskAssessment
    async def get_anomalies(hours: int = 24) -> List[Anomaly]
    async def get_predictions() -> List[Prediction]
    async def get_dashboard_data() -> Dict
```

#### Algoritmos Implementados:
- **Z-Score Analysis:** Deteccao de desvios estatisticos
- **Sliding Window:** Analise temporal de eventos
- **Pattern Recognition:** Identificacao de padroes horarios/diarios
- **Trend Analysis:** Tendencias crescentes/decrescentes

#### Exemplo de Uso:
```python
analytics = GuardianAnalyticsAgent(message_bus=bus)

# Obter score de risco
risk = await analytics.get_risk_assessment()
print(f"Risco: {risk.risk_score}/100 ({risk.risk_level.value})")

# Obter anomalias
anomalies = await analytics.get_anomalies(hours=6)
for a in anomalies:
    print(f"Anomalia: {a.type.value} - {a.description}")
```

---

### 4. GuardianAssistantAgent
**Arquivo:** `agents/guardian/assistant_agent.py`
**Funcao:** Assistente conversacional (CFO de Seguranca)

#### Capacidades:
- Processamento de linguagem natural
- Respostas contextualizadas
- Consultas de status
- Geracao de relatorios
- Recomendacoes proativas

#### Intencoes Suportadas:
| Intencao | Exemplos |
|----------|----------|
| STATUS_QUERY | "status", "como esta o sistema" |
| ALERT_QUERY | "alertas ativos", "incidentes" |
| CAMERA_QUERY | "cameras", "cftv", "gravacoes" |
| ACCESS_QUERY | "acessos", "entradas", "visitantes" |
| REPORT_REQUEST | "relatorio", "exportar" |
| ANALYTICS_QUERY | "risco", "analise", "previsao" |
| HELP_REQUEST | "ajuda", "como faco" |

#### Exemplo de Uso:
```python
assistant = GuardianAssistantAgent(
    monitor_agent=monitor,
    analytics_agent=analytics
)

# Chat
response = await assistant.chat(
    message="Qual o status do sistema?",
    user_id="operador_01",
    user_name="Joao"
)

print(response["response"])
# "Sistema operando normalmente. 24 cameras ativas..."

print(response["suggestions"])
# ["Ver alertas ativos", "Ver status das cameras"]
```

---

### 5. GuardianResponseAgent
**Arquivo:** `agents/guardian/response_agent.py`
**Funcao:** Resposta automatizada a incidentes

#### Capacidades:
- Execucao de protocolos de resposta
- Notificacoes multi-canal
- Escalonamento automatico
- Documentacao de timeline
- Coordenacao de acoes

#### Protocolos Pre-configurados:
| Tipo | Acoes | Escalonamento |
|------|-------|---------------|
| Intrusao | Alarme, Video, Bloqueio, Despacho | 3 niveis |
| Acesso Nao Autorizado | Video, Log, Alerta | 2 niveis |
| Emergencia | Alarme, 190/192/193, Desbloqueio | 2 niveis |
| Falha Equipamento | Log, Email | 2 niveis |
| Atividade Suspeita | Video, Alerta | 2 niveis |

#### Acoes Disponiveis:
```python
class ActionType(Enum):
    NOTIFY, ALERT, LOCK_ACCESS, UNLOCK_ACCESS,
    ACTIVATE_ALARM, DEACTIVATE_ALARM, RECORD_VIDEO,
    DISPATCH_SECURITY, CALL_EMERGENCY, ISOLATE_AREA
```

#### Canais de Notificacao:
- SMS, Email, Push, WhatsApp
- Chamada telefonica
- Intercomunicador
- Dashboard

#### Exemplo de Uso:
```python
response = GuardianResponseAgent(message_bus=bus)

# Criar incidente manualmente
incident = await response.create_incident(
    incident_type=IncidentType.INTRUSION,
    severity=IncidentSeverity.HIGH,
    title="Invasao detectada no Bloco B",
    description="Pessoa nao identificada pulou o muro",
    location="Bloco B - Muro lateral"
)

# Reconhecer incidente
await response.acknowledge_incident(incident.id, "operador_01")

# Resolver incidente
await response.resolve_incident(
    incident.id,
    "Falso alarme - morador esqueceu chave",
    "operador_01"
)
```

---

### 6. GuardianOrchestrator
**Arquivo:** `agents/guardian/orchestrator.py`
**Funcao:** Orquestracao central do sistema

#### Capacidades:
- Gerenciamento de ciclo de vida
- Message Bus centralizado
- Health checks automaticos
- Reinicio automatico de agentes
- API unificada

#### Message Bus:
```python
class MessageBus:
    async def subscribe(topic: str, handler: Callable)
    async def publish(topic: str, payload: Dict)
    async def request(topic: str, payload: Dict) -> Dict
```

#### Topicos Principais:
| Topico | Descricao |
|--------|-----------|
| `alert.*` | Alertas de monitoramento |
| `access.*` | Eventos de acesso |
| `incident.*` | Gerenciamento de incidentes |
| `analytics.*` | Eventos de analytics |
| `notification.*` | Notificacoes |
| `camera.*` | Controle de cameras |

#### Exemplo de Uso:
```python
from agents.guardian import create_guardian_system

# Criar sistema completo
guardian = await create_guardian_system({
    "monitor": {"alert_cooldown": 60},
    "access": {"face_threshold": 0.85}
})

# Iniciar
await guardian.start()

# Obter status
status = await guardian.get_status()

# Usar assistente
response = await guardian.chat(
    message="Status das cameras",
    user_id="admin"
)

# Obter dashboard
dashboard = await guardian.get_dashboard_data()

# Parar
await guardian.stop()
```

---

## INTEGRACAO COM CONECTA PLUS

### Endpoints Sugeridos

```python
# backend/routers/guardian.py

@router.get("/guardian/status")
async def get_guardian_status():
    return await guardian.get_status()

@router.get("/guardian/dashboard")
async def get_dashboard():
    return await guardian.get_dashboard_data()

@router.post("/guardian/chat")
async def chat(request: ChatRequest):
    return await guardian.chat(
        message=request.message,
        user_id=request.user_id
    )

@router.post("/guardian/access/validate")
async def validate_access(request: AccessRequest):
    return await guardian.validate_access(
        credential_type=request.type,
        credential_data=request.data,
        access_point=request.access_point
    )

@router.get("/guardian/incidents")
async def get_incidents():
    return await guardian.get_active_incidents()

@router.get("/guardian/risk")
async def get_risk():
    return await guardian.get_risk_assessment()
```

---

## METRICAS E OBSERVABILIDADE

### Metricas Disponiveis

| Metrica | Descricao |
|---------|-----------|
| `guardian_uptime_seconds` | Tempo de atividade |
| `guardian_agents_running` | Agentes ativos |
| `guardian_total_alerts` | Total de alertas |
| `guardian_total_incidents` | Total de incidentes |
| `guardian_risk_score` | Score de risco atual |
| `guardian_messages_processed` | Mensagens processadas |

### Logs Estruturados

```
2025-12-20 10:30:45 | INFO | guardian_monitor | Alerta criado: INTRUSION_DETECTED
2025-12-20 10:30:46 | WARNING | guardian_response | Incidente INC-20251220103045-A1B2C3 criado
2025-12-20 10:30:47 | INFO | guardian_response | Acao executada: ACTIVATE_ALARM
```

---

## CONFIGURACAO

### Variaveis de Ambiente

```env
# Guardian
GUARDIAN_ALERT_COOLDOWN=60
GUARDIAN_FACE_THRESHOLD=0.85
GUARDIAN_ANOMALY_THRESHOLD=2.5
GUARDIAN_ESCALATION_TIMEOUT=300
```

### Arquivo de Configuracao

```python
guardian_config = {
    "monitor": {
        "alert_cooldown": 60,
        "max_alerts": 1000
    },
    "access": {
        "face_threshold": 0.85,
        "plate_threshold": 0.90,
        "liveness_required": True
    },
    "analytics": {
        "anomaly_z_threshold": 2.5,
        "min_data_points": 30,
        "prediction_horizon_hours": 24
    },
    "response": {
        "auto_acknowledge_timeout": 300,
        "max_escalation_level": 3
    },
    "assistant": {
        "max_context_messages": 20,
        "session_timeout_minutes": 30
    }
}
```

---

## ARQUIVOS CRIADOS

| Arquivo | Linhas | Descricao |
|---------|--------|-----------|
| `agents/guardian/__init__.py` | 31 | Exports do modulo |
| `agents/guardian/monitor_agent.py` | ~450 | Agente de monitoramento |
| `agents/guardian/access_agent.py` | ~650 | Agente de acesso |
| `agents/guardian/analytics_agent.py` | ~700 | Agente de analytics |
| `agents/guardian/assistant_agent.py` | ~600 | Agente conversacional |
| `agents/guardian/response_agent.py` | ~750 | Agente de resposta |
| `agents/guardian/orchestrator.py` | ~500 | Orquestrador central |

**Total:** ~3.700 linhas de codigo

---

## PROXIMOS PASSOS

### Fase 4: MCPs (Model Context Protocols)
1. [ ] MCP para integracao com Frigate NVR
2. [ ] MCP para comunicacao com controladores de acesso
3. [ ] MCP para envio de notificacoes
4. [ ] MCP para integracao com sistemas externos

### Fase 5: Integracao Final
1. [ ] Conectar agentes aos routers existentes
2. [ ] Integrar com frontend React
3. [ ] Configurar webhooks
4. [ ] Testes de integracao completos
5. [ ] Deploy em producao

---

## CONCLUSAO

O sistema Guardian implementa uma arquitetura robusta de agentes de IA para seguranca eletronica:

- **5 Agentes Especializados** trabalhando de forma coordenada
- **Message Bus** para comunicacao assincrona
- **Orquestrador** para gerenciamento centralizado
- **Protocolos de Resposta** pre-configurados
- **Analise Preditiva** com deteccao de anomalias
- **Assistente Conversacional** para operadores

O sistema esta pronto para integracao com o Conecta Plus na **Fase 4 e 5**.

---

*Documento gerado automaticamente pelo Claude Code Guardian*
*Data: 2025-12-20 | Versao: 2.0*
