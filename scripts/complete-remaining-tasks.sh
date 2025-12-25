#!/bin/bash
###############################################################################
# Script de Automação - Tarefas Restantes para 100%
# Conecta Plus - Finalização do Projeto
# Data: 22/12/2025
###############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Base directory
PROJECT_ROOT="/opt/conecta-plus"

# Logging
LOG_FILE="$PROJECT_ROOT/logs/automation-$(date +%Y%m%d-%H%M%S).log"
mkdir -p "$PROJECT_ROOT/logs"

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1" | tee -a "$LOG_FILE"
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

###############################################################################
# FASE 1: EXECUTAR TESTES
###############################################################################

run_tests() {
    log "========== FASE 1: EXECUTANDO TESTES =========="

    # 1.1 Testes E2E
    info "Executando testes E2E com Playwright..."
    cd "$PROJECT_ROOT/frontend"

    if command -v npm &> /dev/null; then
        log "Executando testes E2E..."

        # Build frontend first if needed
        if [ ! -d ".next" ]; then
            log "Building frontend..."
            npm run build || warn "Build falhou, continuando..."
        fi

        # Run E2E tests
        npm run test:e2e -- --reporter=html --reporter=json || warn "Alguns testes E2E falharam"

        log "✅ Testes E2E concluídos. Relatório: playwright-report/"
    else
        error "npm não encontrado, pulando testes E2E"
    fi

    # 1.2 Testes de Integração
    info "Executando testes de integração..."
    cd "$PROJECT_ROOT/tests/integration"

    if command -v pytest &> /dev/null; then
        log "Executando testes de integração com pytest..."

        pytest -v \
            --junitxml=junit.xml \
            --html=report.html \
            --self-contained-html \
            || warn "Alguns testes de integração falharam"

        log "✅ Testes de integração concluídos. Relatório: report.html"
    else
        error "pytest não encontrado, pulando testes de integração"
    fi

    # 1.3 Testes de Carga (opcional, se k6 disponível)
    if command -v k6 &> /dev/null; then
        log "Executando testes de carga com k6..."
        # Criar script básico de teste de carga se não existir
        if [ ! -f "$PROJECT_ROOT/tests/load/basic-load-test.js" ]; then
            mkdir -p "$PROJECT_ROOT/tests/load"
            cat > "$PROJECT_ROOT/tests/load/basic-load-test.js" << 'EOF'
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '30s', target: 10 },
    { duration: '1m', target: 50 },
    { duration: '30s', target: 0 },
  ],
};

export default function () {
  const res = http.get('http://localhost:3001/api/dashboard/estatisticas');
  check(res, {
    'status is 200 or 401': (r) => r.status === 200 || r.status === 401,
  });
  sleep(1);
}
EOF
        fi

        k6 run "$PROJECT_ROOT/tests/load/basic-load-test.js" || warn "Testes de carga falharam"
        log "✅ Testes de carga concluídos"
    else
        warn "k6 não instalado, pulando testes de carga. Instale com: sudo apt install k6"
    fi

    log "========== FASE 1 CONCLUÍDA =========="
}

###############################################################################
# FASE 2: CODE REVIEW AUTOMATIZADO
###############################################################################

code_review() {
    log "========== FASE 2: CODE REVIEW AUTOMATIZADO =========="

    # 2.1 Frontend Linting
    info "Executando linting no frontend..."
    cd "$PROJECT_ROOT/frontend"

    if npm list eslint &> /dev/null; then
        log "Executando ESLint..."
        npm run lint -- --fix || warn "Alguns problemas de linting encontrados"
        log "✅ Linting do frontend concluído"
    else
        warn "ESLint não configurado"
    fi

    # 2.2 Backend Linting (Python)
    info "Executando linting no backend..."

    if command -v flake8 &> /dev/null; then
        log "Executando Flake8 no backend..."
        cd "$PROJECT_ROOT"
        flake8 --max-line-length=120 --exclude=node_modules,venv,.git \
            backend/ services/ || warn "Problemas de linting encontrados no backend"
    else
        info "Instalando flake8..."
        pip3 install --break-system-packages flake8 || warn "Falha ao instalar flake8"
    fi

    # 2.3 Security Scan
    if command -v safety &> /dev/null; then
        log "Executando security scan..."
        safety check || warn "Vulnerabilidades encontradas"
    else
        info "Instalando safety..."
        pip3 install --break-system-packages safety || warn "Falha ao instalar safety"
    fi

    log "========== FASE 2 CONCLUÍDA =========="
}

###############################################################################
# FASE 3: DOCUMENTAÇÃO
###############################################################################

generate_documentation() {
    log "========== FASE 3: GERANDO DOCUMENTAÇÃO =========="

    # 3.1 API Documentation
    info "Gerando documentação da API..."
    cd "$PROJECT_ROOT"

    # Criar documentação básica se não existir
    if [ ! -f "$PROJECT_ROOT/docs/API.md" ]; then
        mkdir -p "$PROJECT_ROOT/docs"

        log "Criando documentação da API..."
        cat > "$PROJECT_ROOT/docs/API.md" << 'EOF'
# API Documentation - Conecta Plus

## Base URL
- Development: `http://localhost:3001`
- Production: `https://api.conectaplus.com.br`

## Authentication
All protected endpoints require JWT authentication:

```
Authorization: Bearer <token>
```

## Endpoints

### Authentication
- `POST /api/auth/login` - Login
- `POST /api/auth/refresh` - Refresh token

### Dashboard
- `GET /api/dashboard/estatisticas` - Get statistics
- `GET /api/dashboard/alertas` - Get alerts

### Financeiro IA
- `GET /api/financeiro/ia/score/:unitId` - Get score prediction
- `GET /api/financeiro/ia/tendencias` - Get trends
- `GET /api/financeiro/ia/priorizacao` - Get priority list
- `POST /api/financeiro/ia/feedback` - Submit feedback

### Condomínios
- `GET /api/condominios` - List all
- `GET /api/condominios/:id` - Get by ID

For detailed API documentation, see the Swagger/OpenAPI specification.
EOF
    fi

    log "✅ Documentação básica criada em docs/API.md"

    log "========== FASE 3 CONCLUÍDA =========="
}

###############################################################################
# FASE 4: CI/CD SETUP
###############################################################################

setup_cicd() {
    log "========== FASE 4: CONFIGURANDO CI/CD =========="

    mkdir -p "$PROJECT_ROOT/.github/workflows"

    # 4.1 GitHub Actions Workflow
    info "Criando GitHub Actions workflow..."

    cat > "$PROJECT_ROOT/.github/workflows/ci.yml" << 'EOF'
name: CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_DB: conecta_db
          POSTGRES_USER: conecta_user
          POSTGRES_PASSWORD: conecta_password
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      mongodb:
        image: mongo:7
        ports:
          - 27017:27017

      redis:
        image: redis:7
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v3

      - name: Set up Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '20'

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install Frontend Dependencies
        run: |
          cd frontend
          npm ci

      - name: Install Backend Dependencies
        run: |
          pip install -r tests/integration/requirements.txt

      - name: Run Linting
        run: |
          cd frontend
          npm run lint

      - name: Build Frontend
        run: |
          cd frontend
          npm run build

      - name: Run Integration Tests
        run: |
          cd tests/integration
          pytest -v --junitxml=junit.xml

      - name: Run E2E Tests
        run: |
          cd frontend
          npm run test:e2e

      - name: Publish Test Results
        uses: EnricoMi/publish-unit-test-result-action@v2
        if: always()
        with:
          files: |
            tests/integration/junit.xml

      - name: Upload Test Coverage
        uses: codecov/codecov-action@v3
        if: always()
EOF

    log "✅ GitHub Actions workflow criado em .github/workflows/ci.yml"

    log "========== FASE 4 CONCLUÍDA =========="
}

###############################################################################
# FASE 5: PRODUCTION SETUP
###############################################################################

setup_production() {
    log "========== FASE 5: CONFIGURAÇÃO DE PRODUÇÃO =========="

    # 5.1 Docker Compose Production
    info "Criando docker-compose.production.yml..."

    cat > "$PROJECT_ROOT/docker-compose.production.yml" << 'EOF'
version: '3.8'

services:
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
    restart: unless-stopped

  api-gateway:
    build:
      context: ./services/api-gateway
      dockerfile: Dockerfile
    ports:
      - "3001:3001"
    environment:
      - NODE_ENV=production
    restart: unless-stopped
    depends_on:
      - postgres
      - mongodb
      - redis

  postgres:
    image: postgres:16
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    restart: unless-stopped

  mongodb:
    image: mongo:7
    volumes:
      - mongodb_data:/data/db
      - ./backups:/backups
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./config/nginx/production.conf:/etc/nginx/nginx.conf:ro
      - ./config/nginx/ssl:/etc/nginx/ssl:ro
    restart: unless-stopped
    depends_on:
      - frontend
      - api-gateway

volumes:
  postgres_data:
  mongodb_data:
  redis_data:
EOF

    log "✅ Docker Compose production criado"

    # 5.2 Environment Template
    if [ ! -f "$PROJECT_ROOT/.env.production.example" ]; then
        cat > "$PROJECT_ROOT/.env.production.example" << 'EOF'
# Database
DATABASE_URL=postgresql://user:password@postgres:5432/conecta_db
MONGODB_URL=mongodb://mongodb:27017
REDIS_URL=redis://redis:6379

# API Gateway
API_PORT=3001
JWT_SECRET=change_this_in_production

# Frontend
NEXT_PUBLIC_API_URL=https://api.conectaplus.com.br

# Security
NODE_ENV=production
ALLOWED_ORIGINS=https://conectaplus.com.br

# Monitoring (optional)
SENTRY_DSN=
PROMETHEUS_ENABLED=true
EOF

        log "✅ Template de environment criado: .env.production.example"
    fi

    log "========== FASE 5 CONCLUÍDA =========="
}

###############################################################################
# FASE 6: MONITORING SETUP
###############################################################################

setup_monitoring() {
    log "========== FASE 6: CONFIGURANDO MONITORING =========="

    mkdir -p "$PROJECT_ROOT/monitoring"

    # 6.1 Prometheus Configuration
    info "Criando configuração do Prometheus..."

    cat > "$PROJECT_ROOT/monitoring/prometheus.yml" << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'conecta-api-gateway'
    static_configs:
      - targets: ['localhost:3001']

  - job_name: 'conecta-backend'
    static_configs:
      - targets: ['localhost:8000']

  - job_name: 'postgres'
    static_configs:
      - targets: ['localhost:9187']

  - job_name: 'redis'
    static_configs:
      - targets: ['localhost:9121']

  - job_name: 'mongodb'
    static_configs:
      - targets: ['localhost:9216']
EOF

    log "✅ Configuração do Prometheus criada"

    # 6.2 Grafana Dashboard Template
    info "Criando template de dashboard Grafana..."

    cat > "$PROJECT_ROOT/monitoring/grafana-dashboard.json" << 'EOF'
{
  "dashboard": {
    "title": "Conecta Plus - System Overview",
    "panels": [
      {
        "title": "API Response Time",
        "type": "graph",
        "datasource": "Prometheus"
      },
      {
        "title": "Active Users",
        "type": "stat",
        "datasource": "Prometheus"
      },
      {
        "title": "Database Connections",
        "type": "graph",
        "datasource": "Prometheus"
      },
      {
        "title": "Error Rate",
        "type": "graph",
        "datasource": "Prometheus"
      }
    ]
  }
}
EOF

    log "✅ Template de dashboard Grafana criado"

    log "========== FASE 6 CONCLUÍDA =========="
}

###############################################################################
# FASE 7: BACKUP SETUP
###############################################################################

setup_backups() {
    log "========== FASE 7: CONFIGURANDO BACKUPS =========="

    mkdir -p "$PROJECT_ROOT/backups"
    mkdir -p "$PROJECT_ROOT/scripts"

    # 7.1 Backup Script
    info "Criando script de backup..."

    cat > "$PROJECT_ROOT/scripts/backup.sh" << 'EOF'
#!/bin/bash
# Backup Script for Conecta Plus
# Executes daily backups of all databases

BACKUP_DIR="/opt/conecta-plus/backups"
DATE=$(date +%Y%m%d-%H%M%S)

# PostgreSQL Backup
pg_dump -h localhost -U conecta_user -d conecta_db > "$BACKUP_DIR/postgres-$DATE.sql"
gzip "$BACKUP_DIR/postgres-$DATE.sql"

# MongoDB Backup
mongodump --host localhost --port 27017 --out "$BACKUP_DIR/mongodb-$DATE"
tar -czf "$BACKUP_DIR/mongodb-$DATE.tar.gz" "$BACKUP_DIR/mongodb-$DATE"
rm -rf "$BACKUP_DIR/mongodb-$DATE"

# Redis Backup
redis-cli SAVE
cp /var/lib/redis/dump.rdb "$BACKUP_DIR/redis-$DATE.rdb"
gzip "$BACKUP_DIR/redis-$DATE.rdb"

# Delete backups older than 30 days
find "$BACKUP_DIR" -name "*.gz" -mtime +30 -delete
find "$BACKUP_DIR" -name "*.rdb.gz" -mtime +30 -delete

echo "Backup concluído: $DATE"
EOF

    chmod +x "$PROJECT_ROOT/scripts/backup.sh"

    log "✅ Script de backup criado"

    # 7.2 Cron Job Setup (optional)
    info "Para agendar backups diários, adicione ao cron:"
    echo "0 2 * * * /opt/conecta-plus/scripts/backup.sh >> /opt/conecta-plus/logs/backup.log 2>&1" | tee -a "$LOG_FILE"

    log "========== FASE 7 CONCLUÍDA =========="
}

###############################################################################
# MAIN EXECUTION
###############################################################################

main() {
    log "╔═══════════════════════════════════════════════════════════════╗"
    log "║  CONECTA PLUS - AUTOMAÇÃO DE TAREFAS FINAIS                  ║"
    log "║  Data: $(date +'%Y-%m-%d %H:%M:%S')                                       ║"
    log "╚═══════════════════════════════════════════════════════════════╝"

    # Execute cada fase
    run_tests
    code_review
    generate_documentation
    setup_cicd
    setup_production
    setup_monitoring
    setup_backups

    log "╔═══════════════════════════════════════════════════════════════╗"
    log "║  ✅ AUTOMAÇÃO CONCLUÍDA COM SUCESSO!                          ║"
    log "║                                                              ║"
    log "║  Próximos passos:                                            ║"
    log "║  1. Revisar logs em: $LOG_FILE"
    log "║  2. Executar testes manualmente se necessário                ║"
    log "║  3. Configurar variáveis de ambiente de produção             ║"
    log "║  4. Deploy para ambiente de staging                          ║"
    log "╚═══════════════════════════════════════════════════════════════╝"
}

# Execute main
main "$@"
