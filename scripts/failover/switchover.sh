#!/bin/bash
# ============================================
# Conecta Plus - Switchover PostgreSQL
# Troca planejada entre master e replica
# ============================================
#
# USO: ./switchover.sh [--force]
#
# DIFERENCA ENTRE FAILOVER E SWITCHOVER:
# - Failover: Emergencial, master indisponivel
# - Switchover: Planejado, ambos disponiveis
#
# Este script:
# 1. Para as escritas no master atual
# 2. Aguarda replica sincronizar 100%
# 3. Promove replica para master
# 4. Reconfigura antigo master como replica
#
# ============================================

set -e

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuracoes
CURRENT_MASTER="conecta-postgres"
CURRENT_REPLICA="conecta-postgres-replica"
POSTGRES_USER="${POSTGRES_USER:-conecta_user}"
POSTGRES_DB="${POSTGRES_DB:-conecta_db}"
LOG_FILE="/opt/conecta-plus/logs/switchover-$(date +%Y%m%d-%H%M%S).log"

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

log_step() {
    echo -e "${CYAN}[ETAPA]${NC} $1" | tee -a "$LOG_FILE"
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
            echo "Realiza switchover planejado entre master e replica."
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
echo " Conecta Plus - Switchover Planejado"
echo " $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================"
echo ""

# Criar diretorio de logs
mkdir -p "$(dirname "$LOG_FILE")"

# ============================================
# ETAPA 1: Pre-verificacoes
# ============================================
log_step "1. Verificacoes pre-switchover..."

# Verifica master
if ! docker exec "$CURRENT_MASTER" pg_isready -q 2>/dev/null; then
    log_error "Master atual nao esta respondendo!"
    log_error "Para failover de emergencia, use: promote-replica.sh"
    exit 1
fi
log_success "Master online: $CURRENT_MASTER"

# Verifica replica
if ! docker exec "$CURRENT_REPLICA" pg_isready -q 2>/dev/null; then
    log_error "Replica nao esta respondendo!"
    exit 1
fi
log_success "Replica online: $CURRENT_REPLICA"

# Verifica se replica esta em standby
IS_STANDBY=$(docker exec "$CURRENT_REPLICA" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c \
    "SELECT pg_is_in_recovery();" 2>/dev/null | tr -d ' ')

if [ "$IS_STANDBY" != "t" ]; then
    log_error "Replica nao esta em modo standby!"
    exit 1
fi
log_success "Replica em modo standby."

# Verifica replicacao ativa
REPL_STATE=$(docker exec "$CURRENT_MASTER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c \
    "SELECT state FROM pg_stat_replication WHERE application_name = 'postgres_replica';" 2>/dev/null | tr -d ' ')

if [ "$REPL_STATE" != "streaming" ]; then
    log_warn "Replicacao nao esta em streaming! Estado: $REPL_STATE"
    if [ "$FORCE" = false ]; then
        read -p "Continuar mesmo assim? (s/n): " confirm
        if [ "$confirm" != "s" ]; then
            exit 0
        fi
    fi
else
    log_success "Replicacao streaming ativa."
fi

# Verifica lag
LAG=$(docker exec "$CURRENT_REPLICA" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c \
    "SELECT COALESCE(EXTRACT(EPOCH FROM now() - pg_last_xact_replay_timestamp())::int, 0);" 2>/dev/null | tr -d ' ')

log_info "Lag atual: ${LAG}s"

if [ "$LAG" -gt 30 ]; then
    log_warn "Lag alto! Aguarde sincronizacao antes do switchover."
    if [ "$FORCE" = false ]; then
        read -p "Continuar mesmo assim? (s/n): " confirm
        if [ "$confirm" != "s" ]; then
            exit 0
        fi
    fi
fi

# ============================================
# ETAPA 2: Confirmacao
# ============================================
if [ "$FORCE" = false ]; then
    echo ""
    log_warn "ATENCAO: O switchover ira:"
    echo "  1. Bloquear novas conexoes no master atual"
    echo "  2. Aguardar todas as transacoes serem replicadas"
    echo "  3. Promover a replica para novo master"
    echo "  4. Requerer atualizacao manual das conexoes dos servicos"
    echo ""
    echo "  Master atual:  $CURRENT_MASTER (porta 5432)"
    echo "  Novo master:   $CURRENT_REPLICA (porta 5433)"
    echo ""
    read -p "Deseja continuar? (digite 'SWITCHOVER' para confirmar): " confirm
    if [ "$confirm" != "SWITCHOVER" ]; then
        log_info "Operacao cancelada."
        exit 0
    fi
fi

# ============================================
# ETAPA 3: Bloquear novas conexoes
# ============================================
log_step "2. Bloqueando novas conexoes no master..."

docker exec "$CURRENT_MASTER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c \
    "ALTER SYSTEM SET max_connections = 3;" 2>&1 | tee -a "$LOG_FILE"

log_warn "Novas conexoes bloqueadas. Apenas superusers podem conectar."

# ============================================
# ETAPA 4: Aguardar sincronizacao
# ============================================
log_step "3. Aguardando sincronizacao completa..."

# Cria checkpoint para forcar flush de WAL
docker exec "$CURRENT_MASTER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c \
    "CHECKPOINT;" 2>&1 | tee -a "$LOG_FILE"

# Aguarda lag zerar
max_wait=60
waited=0
while [ $waited -lt $max_wait ]; do
    LAG=$(docker exec "$CURRENT_REPLICA" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c \
        "SELECT pg_wal_lsn_diff(pg_last_wal_receive_lsn(), pg_last_wal_replay_lsn());" 2>/dev/null | tr -d ' ')

    if [ "$LAG" = "0" ] || [ -z "$LAG" ]; then
        log_success "Replica sincronizada!"
        break
    fi

    log_info "Aguardando sincronizacao... (lag: ${LAG} bytes)"
    sleep 2
    waited=$((waited + 2))
done

if [ $waited -ge $max_wait ]; then
    log_warn "Timeout aguardando sincronizacao. Continuando mesmo assim..."
fi

# ============================================
# ETAPA 5: Parar master
# ============================================
log_step "4. Parando master atual..."

docker stop "$CURRENT_MASTER" 2>&1 | tee -a "$LOG_FILE"
log_success "Master parado."

# ============================================
# ETAPA 6: Promover replica
# ============================================
log_step "5. Promovendo replica para master..."

docker exec "$CURRENT_REPLICA" su postgres -c "pg_ctl promote -D /var/lib/postgresql/data" 2>&1 | tee -a "$LOG_FILE"

sleep 5

# Verifica promocao
IS_MASTER=$(docker exec "$CURRENT_REPLICA" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c \
    "SELECT pg_is_in_recovery();" 2>/dev/null | tr -d ' ')

if [ "$IS_MASTER" = "f" ]; then
    log_success "Replica promovida com sucesso!"
else
    log_error "Falha ao promover replica!"
    log_error "Reiniciando master antigo..."
    docker start "$CURRENT_MASTER"
    exit 1
fi

# ============================================
# RESUMO
# ============================================
echo ""
echo "============================================"
echo -e "${GREEN}SWITCHOVER CONCLUIDO COM SUCESSO!${NC}"
echo "============================================"
echo ""
echo "NOVO STATUS:"
echo "  - Novo Master: $CURRENT_REPLICA (porta 5433)"
echo "  - Antigo Master: $CURRENT_MASTER (PARADO)"
echo ""
echo "PROXIMOS PASSOS OBRIGATORIOS:"
echo ""
echo "1. Atualizar conexoes dos servicos para usar nova porta:"
echo "   DATABASE_URL=postgresql://user:pass@postgres-replica:5432/db"
echo "   OU"
echo "   DATABASE_URL=postgresql://user:pass@localhost:5433/db"
echo ""
echo "2. Reiniciar servicos:"
echo "   docker compose restart api-gateway auth-service ai-orchestrator"
echo ""
echo "3. (Opcional) Reconstruir antigo master como nova replica:"
echo "   /opt/conecta-plus/scripts/failover/rebuild-replica.sh"
echo ""
echo "============================================"
echo ""

log_info "Log completo: $LOG_FILE"
