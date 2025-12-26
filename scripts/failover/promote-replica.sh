#!/bin/bash
# ============================================
# Conecta Plus - Script de Failover PostgreSQL
# Promove replica para master
# ============================================
#
# USO: ./promote-replica.sh [--force] [--dry-run]
#
# OPCOES:
#   --force    Executa sem confirmacao
#   --dry-run  Apenas mostra o que seria feito
#
# ATENCAO: Execute apenas em caso de falha do master!
#          Este processo NAO e reversivel automaticamente.
#
# ============================================

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuracoes
MASTER_CONTAINER="conecta-postgres"
REPLICA_CONTAINER="conecta-postgres-replica"
MASTER_PORT=5432
REPLICA_PORT=5433
LOG_FILE="/opt/conecta-plus/logs/failover-$(date +%Y%m%d-%H%M%S).log"

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
DRY_RUN=false

for arg in "$@"; do
    case $arg in
        --force)
            FORCE=true
            ;;
        --dry-run)
            DRY_RUN=true
            ;;
        --help|-h)
            echo "Uso: $0 [--force] [--dry-run]"
            echo ""
            echo "Opcoes:"
            echo "  --force    Executa sem confirmacao"
            echo "  --dry-run  Apenas mostra o que seria feito"
            exit 0
            ;;
    esac
done

# Header
echo ""
echo "============================================"
echo " Conecta Plus - Failover PostgreSQL"
echo " $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================"
echo ""

# Criar diretorio de logs
mkdir -p "$(dirname "$LOG_FILE")"

log_info "Iniciando processo de failover..."
log_info "Log salvo em: $LOG_FILE"

# ============================================
# ETAPA 1: Verificar status dos containers
# ============================================
log_info "Etapa 1: Verificando status dos containers..."

check_master_status() {
    if docker exec "$MASTER_CONTAINER" pg_isready -q 2>/dev/null; then
        return 0
    else
        return 1
    fi
}

check_replica_status() {
    if docker exec "$REPLICA_CONTAINER" pg_isready -q 2>/dev/null; then
        return 0
    else
        return 1
    fi
}

# Verifica master
if check_master_status; then
    log_warn "ATENCAO: Master parece estar ONLINE!"
    log_warn "Container: $MASTER_CONTAINER"

    if [ "$FORCE" = false ]; then
        echo ""
        echo -e "${YELLOW}O master ainda esta respondendo.${NC}"
        echo "Promover a replica pode causar SPLIT-BRAIN."
        echo ""
        read -p "Tem certeza que deseja continuar? (digite 'SIM' para confirmar): " confirm
        if [ "$confirm" != "SIM" ]; then
            log_info "Operacao cancelada pelo usuario."
            exit 0
        fi
    fi
else
    log_error "Master OFFLINE - Failover necessario!"
fi

# Verifica replica
if ! check_replica_status; then
    log_error "Replica nao esta respondendo!"
    log_error "Container: $REPLICA_CONTAINER"
    log_error "Impossivel realizar failover."
    exit 1
fi

log_success "Replica esta online e respondendo."

# ============================================
# ETAPA 2: Verificar lag de replicacao
# ============================================
log_info "Etapa 2: Verificando lag de replicacao..."

if [ "$DRY_RUN" = false ]; then
    # Verifica se replica esta em sync
    REPLICA_LAG=$(docker exec "$REPLICA_CONTAINER" psql -U conecta_user -d conecta_db -t -c \
        "SELECT CASE
            WHEN pg_last_wal_receive_lsn() = pg_last_wal_replay_lsn() THEN 0
            ELSE EXTRACT(EPOCH FROM now() - pg_last_xact_replay_timestamp())::int
         END;" 2>/dev/null || echo "ERRO")

    if [ "$REPLICA_LAG" = "ERRO" ]; then
        log_warn "Nao foi possivel verificar o lag. Continuando..."
    elif [ "$REPLICA_LAG" -gt 60 ]; then
        log_warn "Lag de replicacao: ${REPLICA_LAG}s"
        log_warn "Pode haver perda de dados!"

        if [ "$FORCE" = false ]; then
            read -p "Deseja continuar? (s/n): " confirm
            if [ "$confirm" != "s" ]; then
                exit 0
            fi
        fi
    else
        log_success "Lag de replicacao: ${REPLICA_LAG}s (aceitavel)"
    fi
fi

# ============================================
# ETAPA 3: Promover replica
# ============================================
log_info "Etapa 3: Promovendo replica para master..."

if [ "$DRY_RUN" = true ]; then
    echo ""
    echo -e "${YELLOW}=== MODO DRY-RUN ===${NC}"
    echo "Comandos que seriam executados:"
    echo ""
    echo "1. docker exec $REPLICA_CONTAINER pg_ctl promote -D /var/lib/postgresql/data"
    echo "2. Remover standby.signal"
    echo "3. Atualizar configuracoes de conexao dos servicos"
    echo "4. Reiniciar servicos dependentes"
    echo ""
    exit 0
fi

# Promove a replica
log_info "Executando pg_ctl promote..."
docker exec "$REPLICA_CONTAINER" su postgres -c "pg_ctl promote -D /var/lib/postgresql/data" 2>&1 | tee -a "$LOG_FILE"

if [ $? -eq 0 ]; then
    log_success "Replica promovida com sucesso!"
else
    log_error "Falha ao promover replica!"
    exit 1
fi

# Aguarda a promocao completar
log_info "Aguardando replica assumir como master..."
sleep 5

# Verifica se a replica esta aceitando escrita
WRITE_TEST=$(docker exec "$REPLICA_CONTAINER" psql -U conecta_user -d conecta_db -t -c \
    "SELECT pg_is_in_recovery();" 2>/dev/null | tr -d ' ')

if [ "$WRITE_TEST" = "f" ]; then
    log_success "Nova instancia esta aceitando escrita!"
else
    log_error "Nova instancia ainda em modo recovery!"
    log_error "Verifique manualmente."
    exit 1
fi

# ============================================
# ETAPA 4: Atualizar conexoes
# ============================================
log_info "Etapa 4: Atualizando conexoes dos servicos..."

echo ""
echo "============================================"
echo -e "${GREEN}FAILOVER CONCLUIDO COM SUCESSO!${NC}"
echo "============================================"
echo ""
echo "PROXIMOS PASSOS (MANUAIS):"
echo ""
echo "1. Atualizar DATABASE_URL nos servicos:"
echo "   - Alterar host de 'postgres:5432' para 'postgres-replica:5432'"
echo "   - OU alterar porta de 5432 para 5433 se usando IP direto"
echo ""
echo "2. Reiniciar servicos dependentes:"
echo "   docker compose restart api-gateway auth-service ai-orchestrator"
echo ""
echo "3. Verificar conexao dos servicos:"
echo "   docker compose logs -f api-gateway | grep -i postgres"
echo ""
echo "4. Parar o antigo master (se ainda rodando):"
echo "   docker stop $MASTER_CONTAINER"
echo ""
echo "5. Planejar reconstrucao do master como nova replica"
echo ""
echo "============================================"
echo ""

log_info "Log completo salvo em: $LOG_FILE"
