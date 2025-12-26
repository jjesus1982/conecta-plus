#!/bin/bash
# ============================================
# Conecta Plus - Reconstruir Replica PostgreSQL
# Reconstroi replica a partir do master atual
# ============================================
#
# USO: ./rebuild-replica.sh [--force]
#
# Este script deve ser usado apos:
# - Failover (antigo master vira nova replica)
# - Replica dessincronizada
# - Primeira configuracao da replica
#
# ============================================

set -e

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuracoes
MASTER_CONTAINER="conecta-postgres"
REPLICA_CONTAINER="conecta-postgres-replica"
REPLICA_VOLUME="conecta-postgres-replica-data"
REPLICATOR_PASSWORD="${REPLICATOR_PASSWORD:-repl_conecta_2024_secure}"
COMPOSE_FILE="/opt/conecta-plus/docker-compose.yml"
LOG_FILE="/opt/conecta-plus/logs/rebuild-replica-$(date +%Y%m%d-%H%M%S).log"

# Funcoes de log
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1" | tee -a "$LOG_FILE"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERRO]${NC} $1" | tee -a "$LOG_FILE"
}

# Verifica argumentos
FORCE=false

for arg in "$@"; do
    case $arg in
        --force)
            FORCE=true
            ;;
        --help|-h)
            echo "Uso: $0 [--force]"
            echo ""
            echo "Reconstroi a replica PostgreSQL a partir do master."
            echo ""
            echo "Opcoes:"
            echo "  --force   Nao pede confirmacao"
            exit 0
            ;;
    esac
done

# Header
echo ""
echo "============================================"
echo " Conecta Plus - Reconstruir Replica"
echo " $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================"
echo ""

# Criar diretorio de logs
mkdir -p "$(dirname "$LOG_FILE")"

log_info "Iniciando processo de reconstrucao da replica..."

# ============================================
# ETAPA 1: Verificar master
# ============================================
log_info "Etapa 1: Verificando master..."

if ! docker exec "$MASTER_CONTAINER" pg_isready -q 2>/dev/null; then
    log_error "Master nao esta respondendo!"
    log_error "A replica so pode ser reconstruida com master ativo."
    exit 1
fi

log_success "Master online."

# Verifica se master aceita replicacao
WAL_LEVEL=$(docker exec "$MASTER_CONTAINER" psql -U conecta_user -d conecta_db -t -c \
    "SHOW wal_level;" 2>/dev/null | tr -d ' ')

if [ "$WAL_LEVEL" != "replica" ] && [ "$WAL_LEVEL" != "logical" ]; then
    log_error "Master nao esta configurado para replicacao!"
    log_error "wal_level atual: $WAL_LEVEL (necessario: replica ou logical)"
    exit 1
fi

log_success "Master configurado para replicacao (wal_level: $WAL_LEVEL)"

# ============================================
# ETAPA 2: Verificar/criar usuario replicator
# ============================================
log_info "Etapa 2: Verificando usuario de replicacao..."

REPLICATOR_EXISTS=$(docker exec "$MASTER_CONTAINER" psql -U conecta_user -d conecta_db -t -c \
    "SELECT 1 FROM pg_roles WHERE rolname = 'replicator';" 2>/dev/null | tr -d ' ')

if [ "$REPLICATOR_EXISTS" != "1" ]; then
    log_warn "Usuario replicator nao existe. Criando..."
    docker exec "$MASTER_CONTAINER" psql -U conecta_user -d conecta_db -c \
        "CREATE ROLE replicator WITH REPLICATION LOGIN PASSWORD '$REPLICATOR_PASSWORD';" 2>&1 | tee -a "$LOG_FILE"
    log_success "Usuario replicator criado."
else
    log_success "Usuario replicator existe."
fi

# ============================================
# ETAPA 3: Verificar/criar slot de replicacao
# ============================================
log_info "Etapa 3: Verificando slot de replicacao..."

SLOT_EXISTS=$(docker exec "$MASTER_CONTAINER" psql -U conecta_user -d conecta_db -t -c \
    "SELECT 1 FROM pg_replication_slots WHERE slot_name = 'replica_slot';" 2>/dev/null | tr -d ' ')

if [ "$SLOT_EXISTS" != "1" ]; then
    log_warn "Slot de replicacao nao existe. Criando..."
    docker exec "$MASTER_CONTAINER" psql -U conecta_user -d conecta_db -c \
        "SELECT pg_create_physical_replication_slot('replica_slot');" 2>&1 | tee -a "$LOG_FILE"
    log_success "Slot replica_slot criado."
else
    log_success "Slot replica_slot existe."
fi

# ============================================
# ETAPA 4: Confirmacao
# ============================================
if [ "$FORCE" = false ]; then
    echo ""
    log_warn "ATENCAO: Este processo ira:"
    echo "  - Parar o container da replica"
    echo "  - APAGAR todos os dados da replica"
    echo "  - Fazer novo basebackup do master"
    echo "  - Reconfigurar a replica"
    echo ""
    read -p "Deseja continuar? (digite 'SIM' para confirmar): " confirm
    if [ "$confirm" != "SIM" ]; then
        log_info "Operacao cancelada."
        exit 0
    fi
fi

# ============================================
# ETAPA 5: Parar replica
# ============================================
log_info "Etapa 5: Parando container da replica..."

if docker ps --format '{{.Names}}' | grep -q "^${REPLICA_CONTAINER}$"; then
    docker stop "$REPLICA_CONTAINER" 2>&1 | tee -a "$LOG_FILE"
    log_success "Container parado."
else
    log_info "Container ja estava parado."
fi

# ============================================
# ETAPA 6: Limpar volume da replica
# ============================================
log_info "Etapa 6: Limpando volume da replica..."

# Remove container para liberar volume
docker rm "$REPLICA_CONTAINER" 2>/dev/null || true

# Remove volume
if docker volume ls --format '{{.Name}}' | grep -q "^${REPLICA_VOLUME}$"; then
    docker volume rm "$REPLICA_VOLUME" 2>&1 | tee -a "$LOG_FILE"
    log_success "Volume removido."
else
    log_info "Volume nao existia."
fi

# ============================================
# ETAPA 7: Recriar replica
# ============================================
log_info "Etapa 7: Recriando container da replica..."

cd /opt/conecta-plus

# Recria apenas o container da replica
docker compose up -d postgres-replica 2>&1 | tee -a "$LOG_FILE"

log_info "Aguardando replica inicializar (pode levar alguns minutos)..."

# Aguarda container estar healthy
timeout=300
elapsed=0
while [ $elapsed -lt $timeout ]; do
    if docker exec "$REPLICA_CONTAINER" pg_isready -q 2>/dev/null; then
        break
    fi
    echo -n "."
    sleep 5
    elapsed=$((elapsed + 5))
done
echo ""

if [ $elapsed -ge $timeout ]; then
    log_error "Timeout aguardando replica inicializar!"
    log_error "Verifique os logs: docker logs $REPLICA_CONTAINER"
    exit 1
fi

log_success "Container da replica iniciado."

# ============================================
# ETAPA 8: Verificar replicacao
# ============================================
log_info "Etapa 8: Verificando status da replicacao..."

sleep 10

# Verifica se esta em modo recovery
IS_RECOVERY=$(docker exec "$REPLICA_CONTAINER" psql -U conecta_user -d conecta_db -t -c \
    "SELECT pg_is_in_recovery();" 2>/dev/null | tr -d ' ')

if [ "$IS_RECOVERY" = "t" ]; then
    log_success "Replica em modo standby!"
else
    log_error "Replica NAO esta em modo standby!"
    exit 1
fi

# Verifica conexao com master
REPLICATION_STATUS=$(docker exec "$MASTER_CONTAINER" psql -U conecta_user -d conecta_db -t -c \
    "SELECT state FROM pg_stat_replication WHERE application_name = 'postgres_replica';" 2>/dev/null | tr -d ' ')

if [ "$REPLICATION_STATUS" = "streaming" ]; then
    log_success "Replicacao streaming ativa!"
else
    log_warn "Status da replicacao: $REPLICATION_STATUS"
fi

# ============================================
# RESUMO
# ============================================
echo ""
echo "============================================"
echo -e "${GREEN}REPLICA RECONSTRUIDA COM SUCESSO!${NC}"
echo "============================================"
echo ""
echo "Status:"
docker exec "$MASTER_CONTAINER" psql -U conecta_user -d conecta_db -c \
    "SELECT client_addr, state, sent_lsn, replay_lsn FROM pg_stat_replication;" 2>/dev/null
echo ""
echo "Para monitorar: /opt/conecta-plus/scripts/failover/check-replication.sh"
echo ""

log_info "Log completo: $LOG_FILE"
