# Conecta Plus - Sessao de Integracao Guardian
**Data**: 2025-12-20
**Objetivo**: Completar integracao do Guardian com todos os recursos

---

## STATUS ATUAL DO SISTEMA

### Servicos em Producao (Funcionando)

| Servico | Container | Porta | Status |
|---------|-----------|-------|--------|
| Backend FastAPI | conecta-backend | 8000 | Healthy |
| Frontend Next.js | conecta-frontend | 3000 | OK |
| Nginx Proxy | conecta-nginx | 80/443 | Healthy |
| PostgreSQL | conecta-postgres | 5432 | Healthy |
| Redis | conecta-redis | 6379 | Healthy |
| MongoDB | conecta-mongodb | 27017 | Healthy |

### Credenciais de Acesso
- **Email**: admin@conectaplus.com.br
- **Senha**: admin123
- **JWT Secret**: Configurado em /opt/conecta-plus/.env

### Commits Realizados
1. `4b3fcc0` - Sistema completo inicial (416 arquivos)
2. `922d31a` - Correcoes de deploy para producao

---

## GUARDIAN - ESTADO ATUAL

### O que JA EXISTE (Codigo Implementado)

#### 1. Router API - /opt/conecta-plus/backend/routers/guardian.py (761 linhas)
Endpoints implementados:
- `GET /guardian/status` - Status do sistema (SEM AUTH)
- `GET /guardian/dashboard` - Dashboard consolidado
- `GET /guardian/alerts` - Listar alertas
- `POST /guardian/alerts` - Criar alerta manual
- `POST /guardian/alerts/{id}/acknowledge` - Reconhecer alerta
- `DELETE /guardian/alerts/{id}` - Dispensar alerta
- `GET /guardian/incidents` - Listar incidentes
- `POST /guardian/incidents` - Criar incidente
- `PUT /guardian/incidents/{id}` - Atualizar incidente
- `POST /guardian/incidents/{id}/resolve` - Resolver incidente
- `GET /guardian/risk` - Avaliacao de risco
- `POST /guardian/chat` - Assistente conversacional
- `POST /guardian/actions/alarm/trigger` - Disparar alarme
- `POST /guardian/actions/alarm/deactivate` - Desativar alarme
- `POST /guardian/actions/security/dispatch` - Despachar seguranca
- `WebSocket /guardian/ws` - Eventos em tempo real
- `GET /guardian/statistics` - Estatisticas historicas

#### 2. Service Layer - /opt/conecta-plus/backend/services/guardian.py (708 linhas)
- AlertDTO, IncidentDTO, RiskAssessmentDTO, DashboardDTO
- Gerenciamento de alertas e incidentes
- Calculo de score de risco (0-100)
- Cache em memoria
- Broadcasting via WebSocket
- Integracao com orquestrador (fallback quando indisponivel)

#### 3. Agentes IA - /opt/conecta-plus/agents/guardian/ (5.095 linhas total)
```
agents/guardian/
├── __init__.py
├── monitor_agent.py      (716 linhas) - Monitoramento de cameras
├── access_agent.py       (716 linhas) - Controle de acesso
├── analytics_agent.py    (952 linhas) - Analytics preditivo
├── assistant_agent.py    (929 linhas) - Assistente conversacional
├── response_agent.py     (1035 linhas) - Resposta a incidentes
└── orchestrator.py       (715 linhas) - Orquestrador central
```

Caracteristicas dos agentes:
- Level 7 (Transcendent)
- Message Bus com pub/sub
- Prioridades: LOW, NORMAL, HIGH, CRITICAL
- Integracao YOLO v8 para deteccao
- Reconhecimento facial e de placas

#### 4. Integracao Frigate - /opt/conecta-plus/backend/routers/frigate.py
- Endpoints para cameras
- Webhooks de eventos
- Processamento de streams RTSP

---

## O QUE FALTA FAZER

### 1. Criar Container Docker do Guardian
**Arquivo**: /opt/conecta-plus/apps/guardian/Dockerfile
**Problema**: Diretorio esta VAZIO
**Solucao**: Criar Dockerfile e estrutura do servico

```dockerfile
# Estrutura necessaria:
FROM python:3.11-slim
# Instalar YOLO, OpenCV, dependencias IA
# Copiar agentes
# Configurar GPU (opcional)
```

### 2. Corrigir Importacao de Agentes no Backend
**Arquivo**: /opt/conecta-plus/backend/services/guardian.py
**Erro atual**:
```
WARNING | Agentes Guardian nao disponiveis: No module named 'agents'
```
**Solucao**: Adicionar agents ao PYTHONPATH ou instalar como package

### 3. Adicionar Persistencia no Banco de Dados
**Problema**: Alertas e incidentes estao em cache (memoria)
**Solucao**: Criar modelos SQLAlchemy e migrar

Tabelas necessarias:
- guardian_alerts
- guardian_incidents
- guardian_risk_history
- guardian_actions_log

### 4. Ativar Integracao Frigate
**Arquivo**: /opt/conecta-plus/backend/routers/frigate.py
**Status**: Codigo existe mas desativado
**Configuracao necessaria em .env**:
```
FRIGATE_URL=http://frigate:5000
FRIGATE_ENABLED=true
```

### 5. Configurar AI Orchestrator
**Arquivo docker-compose.yml** ja tem definicao (linhas 205-272):
```yaml
ai-orchestrator:
  build:
    context: .
    dockerfile: services/ai-orchestrator/Dockerfile
  environment:
    ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
    OPENAI_API_KEY: ${OPENAI_API_KEY}
```
**Problema**: Dockerfile nao existe em services/ai-orchestrator/

### 6. Expor Guardian no API Gateway
**Arquivo**: /opt/conecta-plus/services/api-gateway/main.py
**Problema**: Guardian nao esta roteado pelo gateway (porta 3001)

### 7. Conectar Sistema de Notificacoes
**Servico**: notification-service
**Integracao**: WhatsApp, Telegram, Email
**Configurar em .env**:
```
WHATSAPP_API_URL=
WHATSAPP_API_TOKEN=
TELEGRAM_BOT_TOKEN=
```

---

## ARQUIVOS CHAVE PARA MODIFICAR

```
/opt/conecta-plus/
├── apps/guardian/
│   ├── Dockerfile                    # CRIAR
│   ├── main.py                       # CRIAR
│   └── requirements.txt              # CRIAR
├── backend/
│   ├── models/guardian.py            # CRIAR (modelos DB)
│   └── services/guardian.py          # MODIFICAR (persistencia)
├── services/
│   ├── ai-orchestrator/
│   │   └── Dockerfile                # CRIAR
│   └── api-gateway/
│       └── main.py                   # MODIFICAR (rotas guardian)
├── docker-compose.yml                # MODIFICAR (servicos guardian)
└── .env                              # CONFIGURAR (API keys)
```

---

## ORDEM DE EXECUCAO SUGERIDA

1. **Modelos de Banco de Dados**
   - Criar /opt/conecta-plus/backend/models/guardian.py
   - Rodar migrations

2. **Atualizar Guardian Service**
   - Adicionar persistencia PostgreSQL
   - Manter cache Redis para performance

3. **Criar Container Guardian**
   - Dockerfile com YOLO/OpenCV
   - Copiar agentes
   - Testar localmente

4. **Criar AI Orchestrator Container**
   - Dockerfile para orquestrador
   - Configurar APIs (Anthropic/OpenAI)

5. **Integrar no Docker Compose**
   - Adicionar guardian e ai-orchestrator
   - Configurar redes e volumes

6. **Testar Endpoints**
   - Validar todos os 20 endpoints
   - Testar WebSocket em tempo real

7. **Ativar Frigate (se disponivel)**
   - Configurar cameras
   - Testar deteccao YOLO

8. **Conectar Notificacoes**
   - Configurar WhatsApp/Telegram
   - Testar alertas

---

## COMANDOS UTEIS

```bash
# Status atual
docker ps --filter "name=conecta"

# Logs do backend
docker logs -f conecta-backend

# Testar Guardian status
curl http://localhost:8000/api/v1/guardian/status

# Login para obter token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@conectaplus.com.br&password=admin123"

# Testar endpoint com token
TOKEN="seu_token_aqui"
curl http://localhost:8000/api/v1/guardian/dashboard \
  -H "Authorization: Bearer $TOKEN"

# Rebuild e restart
cd /opt/conecta-plus/docker
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
```

---

## PROXIMA SESSAO

**Objetivo**: Integrar Guardian 100% ao Conecta Plus

**Tarefas**:
1. [ ] Criar modelos de banco para Guardian
2. [ ] Atualizar service com persistencia
3. [ ] Criar Dockerfile do Guardian container
4. [ ] Criar Dockerfile do AI Orchestrator
5. [ ] Atualizar docker-compose com novos servicos
6. [ ] Testar todos os endpoints
7. [ ] Ativar integracao com cameras (se Frigate disponivel)
8. [ ] Configurar notificacoes em tempo real
9. [ ] Testar fluxo completo de alerta/incidente
10. [ ] Documentar API do Guardian

**Estimativa**: Aproximadamente 2-3 horas de trabalho

---

## NOTAS TECNICAS

### Score de Risco (Algoritmo Atual)
```python
base_score = 20
alert_factor = min(30, unacknowledged_alerts * 8)
incident_factor = min(35, open_incidents * 12)
time_factor = 15 if (0 <= hora <= 5) else 0  # Madrugada
total = base_score + alert_factor + incident_factor + time_factor
```

### Niveis de Risco
- 0-30: LOW (verde)
- 31-60: MEDIUM (amarelo)
- 61-80: HIGH (laranja)
- 81-100: CRITICAL (vermelho)

### Roles com Acesso ao Guardian
- admin: Acesso total
- sindico: Acesso total
- seguranca: Criar alertas/incidentes, despachar equipe
- porteiro: Visualizar dashboard e alertas

---

*Documento gerado automaticamente em 2025-12-20 22:21 UTC*
*Versao do Sistema: Conecta Plus v2.0*
