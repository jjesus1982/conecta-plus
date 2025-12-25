# Conecta Plus - Memória do Projeto

*Gerado automaticamente em 2025-12-24*

## Visão Geral
Sistema integrado de gestão condominial com inteligência artificial. Inclui módulos de segurança, financeiro, acesso, CFTV, comunicação e IA proativa.

## Arquitetura

### Stack Tecnológica
- **Frontend:** Next.js 16 + TypeScript + Tailwind CSS
- **Backend Python:** FastAPI (porta 8000) - Q1/Q2 features
- **Backend Node.js:** API Gateway Express (porta 3001)
- **Banco:** PostgreSQL 16 (schema: conecta)
- **Cache:** Redis 7
- **Proxy:** Nginx (porta 80)
- **Containers:** Docker + Docker Compose

### Serviços Principais
| Serviço | Container | Porta |
|---------|-----------|-------|
| Frontend | conecta-frontend | 3000 |
| Backend Q1/Q2 | conecta-backend-q1 | 8000 |
| API Gateway | conecta-api-gateway-dev | 3001 |
| PostgreSQL | conecta-postgres | 5432 |
| Redis | conecta-redis | 6379 |
| Nginx | conecta-nginx | 80, 443 |

## Estrutura de Diretórios
```
/opt/conecta-plus/
├── frontend/               # Next.js 16 App
│   └── src/
│       ├── app/           # App Router pages
│       ├── components/    # React components
│       └── services/      # API clients
├── backend/               # FastAPI Python
│   ├── routers/          # API endpoints
│   ├── models/           # SQLAlchemy models
│   └── services/         # Business logic
├── services/             # Microserviços
│   ├── api-gateway/      # Node.js Gateway
│   └── ai-orchestrator/  # IA Orchestrator
├── config/
│   └── nginx/conf.d/     # Nginx configs
└── docker-compose.yml
```

## Comandos Importantes

### Docker
```bash
# Status containers
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Rebuild frontend
cd /opt/conecta-plus && docker compose build frontend --no-cache
docker stop conecta-frontend && docker rm conecta-frontend
docker run -d --name conecta-frontend --network conecta-network -p 3000:3000 -e HOSTNAME=0.0.0.0 conecta-plus-frontend:latest

# Rebuild backend
cd /opt/conecta-plus/backend && docker build -t conecta-backend:q2 .
docker restart conecta-backend-q1

# Logs
docker logs -f conecta-frontend
docker logs -f conecta-backend-q1
```

### Banco de Dados
```bash
# Acessar PostgreSQL
docker exec -it conecta-postgres psql -U conecta_user -d conecta_plus

# Schema conecta
SET search_path TO conecta, public;
```

### API Testing
```bash
# Health check
curl http://localhost:8000/health

# API Q2 - Previsões
TOKEN="..."
curl "http://localhost:8000/api/v1/inteligencia/previsoes?condominio_id=a1b2c3d4-e5f6-7890-abcd-ef1234567890" -H "Authorization: Bearer $TOKEN"
```

## Dependências Principais

### Python (backend)
- FastAPI, Uvicorn, Pydantic
- SQLAlchemy, psycopg2
- Redis, httpx

### Node.js (frontend)
- Next.js 16, React 19
- TypeScript, Tailwind CSS
- Zustand, Axios

## Configurações

### Variáveis de Ambiente
- `DATABASE_URL`: postgresql://conecta_user:conecta_pass_2024@conecta-postgres:5432/conecta_plus
- `REDIS_URL`: redis://conecta-redis:6379
- `SECRET_KEY`: JWT secret

### Credenciais de Teste
- Admin: admin@conectaplus.com.br / admin123
- Condomínio ID: a1b2c3d4-e5f6-7890-abcd-ef1234567890

## Módulos Implementados

### Q1 - Fundamentos de Tranquilidade
- [x] Tranquilidade Widget
- [x] SLA Inteligente
- [x] Decision Logs
- [x] Recomendações

### Q2 - Inteligência Proativa
- [x] Previsão de Problemas (RF-05)
- [x] Sugestões Automáticas (RF-06)
- [x] Comunicação Inteligente (RF-07)
- [x] Aprendizado Contínuo (RF-08)

## Problemas Conhecidos
- Banco pode ser resetado se postgres container for recriado
- Autenticação está desabilitada para testes (reativar em produção)

## Decisões de Arquitetura
- Next.js 16 com App Router para SSR
- FastAPI para APIs de IA (melhor async)
- SQLAlchemy com schema PostgreSQL "conecta"
- Nginx como reverse proxy para todos os serviços

## TODO
- [ ] Reativar autenticação
- [ ] Testes E2E com Playwright
- [ ] Documentação OpenAPI completa
- [ ] Monitoramento com Prometheus/Grafana

## Aliases Shell Disponíveis

### Claude Code
```bash
cc              # Alias para claude
claude-yolo     # Sem confirmação de permissões
claude-plan     # Modo planejamento
claude-doc      # Auto-documentação
```

### Navegação Rápida
```bash
cdp             # cd /opt/conecta-plus
cdb             # cd /opt/conecta-plus/backend
cdf             # cd /opt/conecta-plus/frontend
```

### Docker e Serviços
```bash
health          # Health check de todos os serviços
dlog <container> # Logs em tempo real
drestart <container> # Restart de container
rebuild <service>    # Rebuild + restart
```

### Banco de Dados
```bash
dbshell         # Acesso ao PostgreSQL
dbquery 'SQL'   # Executar query
redis-shell     # Acesso ao Redis
```

### API
```bash
api /endpoint   # Testar endpoint
routes          # Listar todas as rotas
gentoken        # Gerar token JWT de teste
```

## Comandos Claude Personalizados

Execute com `/nome-do-comando`:

| Comando | Descrição |
|---------|-----------|
| `/deploy` | Deploy completo com validação |
| `/debug-expert` | Debug avançado com investigação metódica |
| `/feature` | Implementação de feature com planejamento |
| `/fix` | Correção de bug seguindo processo |
| `/review` | Code review completo |
| `/optimize` | Otimização de performance |
| `/security-audit` | Auditoria de segurança OWASP |
| `/analise` | Análise completa do código |

## Templates Disponíveis

Localizados em `~/.claude/templates/`:

- `fastapi-endpoint.py` - Endpoint FastAPI completo com CRUD
- `react-component.tsx` - Componente React com boas práticas
- `pytest-test.py` - Testes pytest estruturados

## Arquitetura FASE 1 - Implementada

### Componentes Criados (Backend Python)

| Componente | Arquivo | Função |
|------------|---------|--------|
| Logger Estruturado | `services/observability/logger.py` | Logs JSON com correlation ID |
| Circuit Breaker | `services/resilience/circuit_breaker.py` | Proteção contra falhas em cascata |
| Event Bus | `services/events/event_bus.py` | Pub/Sub para eventos do sistema |
| Health Router | `routers/health.py` | Endpoints /health, /health/live, /health/ready |
| Events Router | `routers/events.py` | SSE streaming em /api/v1/events/stream |

### Tabelas Criadas (PostgreSQL)

| Tabela | Função |
|--------|--------|
| `domain_events` | Event Sourcing - histórico de eventos |
| `audit_logs` | Log de auditoria para compliance |
| `system_health_snapshots` | Snapshots de saúde do sistema |

### Componentes Criados (Frontend Next.js)

| Componente | Arquivo | Função |
|------------|---------|--------|
| SystemStateProvider | `lib/state/SystemStateProvider.tsx` | Single Source of Truth + SSE |
| useOptimisticMutation | `hooks/useOptimisticMutation.ts` | Updates otimistas com rollback |

### Endpoints Novos

```bash
# Health Check
GET /health           # Status completo de todos os componentes
GET /health/live      # Liveness probe (Kubernetes)
GET /health/ready     # Readiness probe (Kubernetes)

# Events
GET /api/v1/events/stream  # SSE stream de eventos
GET /api/v1/events/stats   # Estatísticas do event bus
POST /api/v1/events/test   # Emitir evento de teste
```

## Histórico de Mudanças
- 2025-12-24: **Remoção Guardian** - Módulo Guardian completamente removido do sistema
- 2025-12-24: **FASE 1 Arquitetural** - Fundações de resiliência implementadas
- 2025-12-24: Configuração Expert do Claude Code (aliases, comandos, templates)
- 2025-12-24: Recriação do banco de dados após reset
- 2025-12-23: Implementação Q2 (Inteligência Proativa)
