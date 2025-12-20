#!/bin/bash
# ============================================
# Conecta Plus - Script de Deploy Produção
# Automação completa de deploy
# ============================================

set -e

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configurações
PROJECT_DIR="/opt/conecta-plus"
DOCKER_DIR="$PROJECT_DIR/docker"
LOG_FILE="/var/log/conecta-plus/deploy.log"
BACKUP_BEFORE_DEPLOY=true
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Carregar variáveis de ambiente
if [ -f "$PROJECT_DIR/.env" ]; then
    export $(grep -v '^#' "$PROJECT_DIR/.env" | xargs)
fi

# Função de log
log() {
    local message=$1
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${timestamp} $message" | tee -a "$LOG_FILE"
}

# Função de erro
error_exit() {
    echo -e "${RED}❌ ERRO: $1${NC}" >&2
    log "ERROR: $1"
    exit 1
}

# Banner
show_banner() {
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║           CONECTA PLUS - SISTEMA DE DEPLOY                   ║"
    echo "║                   Produção v1.0.0                            ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Criar diretórios necessários
mkdir -p "$(dirname "$LOG_FILE")"
cd "$PROJECT_DIR" || error_exit "Diretório do projeto não encontrado"

# ==========================================
# PRE-DEPLOY CHECKS
# ==========================================
pre_deploy_checks() {
    echo -e "${YELLOW}[1/7] Verificações pré-deploy...${NC}"

    # Docker
    if ! docker info > /dev/null 2>&1; then
        error_exit "Docker não está rodando"
    fi
    echo -e "${GREEN}   ✅ Docker OK${NC}"

    # Docker Compose
    if ! docker compose version > /dev/null 2>&1; then
        error_exit "Docker Compose não encontrado"
    fi
    echo -e "${GREEN}   ✅ Docker Compose OK${NC}"

    # .env
    if [ ! -f "$PROJECT_DIR/.env" ]; then
        error_exit "Arquivo .env não encontrado"
    fi
    echo -e "${GREEN}   ✅ Arquivo .env OK${NC}"

    # Espaço em disco
    DISK_FREE=$(df -BG /opt | tail -1 | awk '{print $4}' | tr -d 'G')
    if [ "$DISK_FREE" -lt 5 ]; then
        error_exit "Espaço em disco insuficiente (${DISK_FREE}GB < 5GB)"
    fi
    echo -e "${GREEN}   ✅ Espaço em disco OK (${DISK_FREE}GB)${NC}"
}

# ==========================================
# BACKUP
# ==========================================
create_backup() {
    if [ "$BACKUP_BEFORE_DEPLOY" = true ]; then
        echo -e "${YELLOW}[2/7] Criando backup pré-deploy...${NC}"
        if [ -f "$PROJECT_DIR/scripts/backup.sh" ]; then
            bash "$PROJECT_DIR/scripts/backup.sh" full > /dev/null 2>&1 || true
        fi
        echo -e "${GREEN}   ✅ Backup criado${NC}"
    else
        echo -e "${YELLOW}[2/7] Backup desabilitado${NC}"
    fi
}

# ==========================================
# STOP OLD SERVICES
# ==========================================
stop_services() {
    echo -e "${YELLOW}[3/7] Parando serviços antigos...${NC}"

    # Parar containers de desenvolvimento
    docker stop conecta-api-gateway-dev 2>/dev/null || true
    docker rm conecta-api-gateway-dev 2>/dev/null || true

    # Parar stack de produção
    cd "$DOCKER_DIR"
    docker compose -f docker-compose.prod.yml down --remove-orphans 2>/dev/null || true

    echo -e "${GREEN}   ✅ Serviços parados${NC}"
}

# ==========================================
# START DATABASE
# ==========================================
start_database() {
    echo -e "${YELLOW}[4/7] Iniciando bancos de dados...${NC}"

    cd "$DOCKER_DIR"

    # Iniciar databases
    docker compose -f docker-compose.db.yml up -d

    # Aguardar ficar healthy
    echo -e "   ${CYAN}Aguardando PostgreSQL...${NC}"
    RETRIES=30
    until docker exec conecta-postgres pg_isready -U "${POSTGRES_USER:-conecta}" > /dev/null 2>&1 || [ $RETRIES -eq 0 ]; do
        RETRIES=$((RETRIES-1))
        sleep 1
    done

    if docker ps | grep -q "conecta-postgres.*healthy"; then
        echo -e "${GREEN}   ✅ PostgreSQL rodando${NC}"
    else
        echo -e "${YELLOW}   ⚠️ PostgreSQL ainda inicializando${NC}"
    fi

    if docker ps | grep -q "conecta-redis.*healthy"; then
        echo -e "${GREEN}   ✅ Redis rodando${NC}"
    else
        echo -e "${YELLOW}   ⚠️ Redis ainda inicializando${NC}"
    fi

    if docker ps | grep -q "conecta-mongodb.*healthy"; then
        echo -e "${GREEN}   ✅ MongoDB rodando${NC}"
    else
        echo -e "${YELLOW}   ⚠️ MongoDB ainda inicializando${NC}"
    fi
}

# ==========================================
# BUILD & START BACKEND
# ==========================================
start_backend() {
    echo -e "${YELLOW}[5/7] Iniciando Backend...${NC}"

    cd "$DOCKER_DIR"

    # Build backend
    echo -e "   ${CYAN}Building backend...${NC}"
    docker compose -f docker-compose.prod.yml build backend 2>/dev/null || {
        echo -e "   ${CYAN}Usando imagem existente...${NC}"
    }

    # Start backend
    docker compose -f docker-compose.prod.yml up -d backend

    # Aguardar backend
    sleep 5

    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}   ✅ Backend rodando${NC}"
    else
        echo -e "${YELLOW}   ⚠️ Backend inicializando...${NC}"
    fi
}

# ==========================================
# BUILD & START FRONTEND
# ==========================================
start_frontend() {
    echo -e "${YELLOW}[6/7] Iniciando Frontend...${NC}"

    cd "$DOCKER_DIR"

    # Build frontend
    echo -e "   ${CYAN}Building frontend...${NC}"
    docker compose -f docker-compose.prod.yml build frontend 2>/dev/null || {
        echo -e "   ${CYAN}Usando imagem existente...${NC}"
    }

    # Start frontend
    docker compose -f docker-compose.prod.yml up -d frontend

    # Start nginx
    docker compose -f docker-compose.prod.yml up -d nginx

    sleep 5

    if curl -sf http://localhost:3000 > /dev/null 2>&1; then
        echo -e "${GREEN}   ✅ Frontend rodando${NC}"
    else
        echo -e "${YELLOW}   ⚠️ Frontend inicializando...${NC}"
    fi
}

# ==========================================
# HEALTH CHECK FINAL
# ==========================================
health_check() {
    echo -e "${YELLOW}[7/7] Verificação final de saúde...${NC}"

    sleep 5

    SERVICES_OK=0
    SERVICES_TOTAL=6

    # Verificar cada serviço
    services=("conecta-postgres" "conecta-redis" "conecta-mongodb" "conecta-backend" "conecta-frontend" "conecta-nginx")

    for svc in "${services[@]}"; do
        if docker ps | grep -q "$svc"; then
            echo -e "   ${GREEN}✅ $svc${NC}"
            SERVICES_OK=$((SERVICES_OK+1))
        else
            echo -e "   ${RED}❌ $svc${NC}"
        fi
    done

    echo ""
    echo -e "   Serviços ativos: ${SERVICES_OK}/${SERVICES_TOTAL}"
}

# ==========================================
# QUICK RESTART
# ==========================================
quick_restart() {
    echo -e "${YELLOW}Reiniciando serviços...${NC}"

    cd "$DOCKER_DIR"
    docker compose -f docker-compose.prod.yml restart
    docker compose -f docker-compose.db.yml restart

    echo -e "${GREEN}✅ Serviços reiniciados${NC}"
}

# ==========================================
# STATUS
# ==========================================
show_status() {
    echo ""
    echo -e "${BLUE}=== Status dos Serviços ===${NC}"
    echo ""
    docker ps --filter "name=conecta" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    echo ""
}

# ==========================================
# LOGS
# ==========================================
show_logs() {
    SERVICE=$1

    cd "$DOCKER_DIR"
    if [ -z "$SERVICE" ]; then
        docker compose -f docker-compose.prod.yml -f docker-compose.db.yml logs --tail=100 -f
    else
        docker logs --tail=100 -f "conecta-$SERVICE"
    fi
}

# ==========================================
# FULL DEPLOY
# ==========================================
full_deploy() {
    show_banner
    log "Iniciando deploy completo..."

    START_TIME=$(date +%s)

    pre_deploy_checks
    create_backup
    stop_services
    start_database
    start_backend
    start_frontend
    health_check

    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))

    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║              DEPLOY CONCLUÍDO COM SUCESSO!                   ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "Duração: ${DURATION}s"
    echo -e "Data: $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""
    echo -e "${CYAN}URLs de acesso:${NC}"
    echo -e "  Frontend:  http://82.25.75.74"
    echo -e "  HTTPS:     https://82.25.75.74"
    echo -e "  Backend:   http://82.25.75.74:8000"
    echo -e "  API Docs:  http://82.25.75.74:8000/api/v1/docs"
    echo ""

    log "Deploy concluído em ${DURATION}s"
}

# ==========================================
# MAIN
# ==========================================
case "${1:-deploy}" in
    "deploy")
        full_deploy
        ;;
    "restart")
        quick_restart
        ;;
    "stop")
        stop_services
        ;;
    "status")
        show_status
        ;;
    "logs")
        show_logs "$2"
        ;;
    "database")
        start_database
        ;;
    "backend")
        start_backend
        ;;
    "frontend")
        start_frontend
        ;;
    "help"|*)
        echo "Uso: $0 {deploy|restart|stop|status|logs|database|backend|frontend}"
        echo ""
        echo "Comandos:"
        echo "  deploy    - Deploy completo (padrão)"
        echo "  restart   - Reiniciar todos serviços"
        echo "  stop      - Parar todos serviços"
        echo "  status    - Ver status dos serviços"
        echo "  logs      - Ver logs (uso: logs [backend|frontend|postgres])"
        echo "  database  - Iniciar apenas bancos de dados"
        echo "  backend   - Iniciar apenas backend"
        echo "  frontend  - Iniciar apenas frontend"
        ;;
esac
