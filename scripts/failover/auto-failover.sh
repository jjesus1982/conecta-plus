#!/bin/bash
# ============================================
# Conecta Plus - Auto Failover PostgreSQL
# Monitora master e promove replica automaticamente
# ============================================
#
# USO: ./auto-failover.sh [--daemon] [--interval SECONDS]
#
# OPCOES:
#   --daemon     Executa em background como daemon
#   --interval   Intervalo de verificacao (default: 10s)
#
# IMPORTANTE: Use com cautela! Failover automatico pode
#             causar split-brain se mal configurado.
# ============================================

set -e

# Configuracoes
MASTER_CONTAINER="conecta-postgres"
REPLICA_CONTAINER="conecta-postgres-replica"
CHECK_INTERVAL="${CHECK_INTERVAL:-10}"
FAILURE_THRESHOLD=3  # Numero de falhas antes de failover
LOG_DIR="/opt/conecta-plus/logs"
LOG_FILE="$LOG_DIR/auto-failover.log"
PID_FILE="/var/run/conecta-failover.pid"
LOCK_FILE="/tmp/conecta-failover.lock"

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Contadores
failure_count=0
last_status="unknown"

# Funcoes de log
log() {
    local level=$1
    local msg=$2
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $msg" >> "$LOG_FILE"

    case $level in
        INFO)  echo -e "${BLUE}[INFO]${NC} $msg" ;;
        OK)    echo -e "${GREEN}[OK]${NC} $msg" ;;
        WARN)  echo -e "${YELLOW}[WARN]${NC} $msg" ;;
        ERROR) echo -e "${RED}[ERRO]${NC} $msg" ;;
    esac
}

# Verifica se master esta respondendo
check_master() {
    if docker exec "$MASTER_CONTAINER" pg_isready -q 2>/dev/null; then
        return 0
    else
        return 1
    fi
}

# Verifica se replica esta respondendo
check_replica() {
    if docker exec "$REPLICA_CONTAINER" pg_isready -q 2>/dev/null; then
        return 0
    else
        return 1
    fi
}

# Verifica se replica esta em modo standby
is_replica_standby() {
    local result=$(docker exec "$REPLICA_CONTAINER" psql -U conecta_user -d conecta_db -t -c \
        "SELECT pg_is_in_recovery();" 2>/dev/null | tr -d ' ')

    if [ "$result" = "t" ]; then
        return 0
    else
        return 1
    fi
}

# Obtem lag de replicacao em segundos
get_replication_lag() {
    docker exec "$REPLICA_CONTAINER" psql -U conecta_user -d conecta_db -t -c \
        "SELECT COALESCE(EXTRACT(EPOCH FROM now() - pg_last_xact_replay_timestamp())::int, 0);" 2>/dev/null | tr -d ' '
}

# Promove replica para master
promote_replica() {
    log "WARN" "============================================"
    log "WARN" "INICIANDO FAILOVER AUTOMATICO!"
    log "WARN" "============================================"

    # Verifica se replica esta disponivel
    if ! check_replica; then
        log "ERROR" "Replica nao esta respondendo! Failover impossivel."
        return 1
    fi

    # Verifica lag
    local lag=$(get_replication_lag)
    if [ -n "$lag" ] && [ "$lag" -gt 300 ]; then
        log "WARN" "Lag de replicacao alto: ${lag}s. Pode haver perda de dados!"
    fi

    # Promove replica
    log "INFO" "Executando pg_ctl promote..."
    docker exec "$REPLICA_CONTAINER" su postgres -c "pg_ctl promote -D /var/lib/postgresql/data" 2>&1 | while read line; do
        log "INFO" "$line"
    done

    sleep 5

    # Verifica se promocao foi bem sucedida
    if ! is_replica_standby; then
        log "OK" "Replica promovida com sucesso!"
        log "WARN" "ATENCAO: Atualize as conexoes dos servicos manualmente!"
        log "WARN" "Novo master: $REPLICA_CONTAINER (porta 5433)"

        # Notifica (pode integrar com alertmanager/slack)
        notify_failover

        return 0
    else
        log "ERROR" "Falha ao promover replica!"
        return 1
    fi
}

# Envia notificacao de failover
notify_failover() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local hostname=$(hostname)

    # Se tiver webhook do Slack configurado
    if [ -n "$SLACK_WEBHOOK_URL" ]; then
        curl -s -X POST "$SLACK_WEBHOOK_URL" \
            -H 'Content-type: application/json' \
            --data "{
                \"text\": \":warning: *FAILOVER PostgreSQL* - Conecta Plus\",
                \"attachments\": [{
                    \"color\": \"danger\",
                    \"fields\": [
                        {\"title\": \"Host\", \"value\": \"$hostname\", \"short\": true},
                        {\"title\": \"Timestamp\", \"value\": \"$timestamp\", \"short\": true},
                        {\"title\": \"Acao\", \"value\": \"Replica promovida para master\", \"short\": false}
                    ]
                }]
            }" 2>/dev/null || true
    fi

    # Cria arquivo de alerta
    echo "$timestamp - FAILOVER EXECUTADO" >> "$LOG_DIR/failover-alerts.log"
}

# Loop principal de monitoramento
monitor_loop() {
    log "INFO" "Iniciando monitoramento..."
    log "INFO" "Master: $MASTER_CONTAINER"
    log "INFO" "Replica: $REPLICA_CONTAINER"
    log "INFO" "Intervalo: ${CHECK_INTERVAL}s"
    log "INFO" "Threshold de falhas: $FAILURE_THRESHOLD"

    while true; do
        if check_master; then
            if [ "$last_status" != "ok" ]; then
                log "OK" "Master online e respondendo."
            fi
            failure_count=0
            last_status="ok"
        else
            failure_count=$((failure_count + 1))
            log "WARN" "Master nao responde! Falha $failure_count de $FAILURE_THRESHOLD"

            if [ $failure_count -ge $FAILURE_THRESHOLD ]; then
                log "ERROR" "Threshold de falhas atingido! Iniciando failover..."

                # Adquire lock para evitar failover duplo
                if ( set -o noclobber; echo $$ > "$LOCK_FILE" ) 2>/dev/null; then
                    promote_replica
                    rm -f "$LOCK_FILE"

                    # Sai do loop apos failover
                    log "INFO" "Monitoramento encerrado apos failover."
                    exit 0
                else
                    log "WARN" "Outro processo ja esta executando failover."
                fi
            fi

            last_status="fail"
        fi

        sleep "$CHECK_INTERVAL"
    done
}

# Parse argumentos
DAEMON=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --daemon)
            DAEMON=true
            shift
            ;;
        --interval)
            CHECK_INTERVAL="$2"
            shift 2
            ;;
        --help|-h)
            echo "Uso: $0 [--daemon] [--interval SECONDS]"
            echo ""
            echo "Opcoes:"
            echo "  --daemon     Executa em background"
            echo "  --interval   Intervalo de verificacao (default: 10s)"
            exit 0
            ;;
        *)
            echo "Opcao desconhecida: $1"
            exit 1
            ;;
    esac
done

# Cria diretorio de logs
mkdir -p "$LOG_DIR"

# Header
echo ""
echo "============================================"
echo " Conecta Plus - Auto Failover Monitor"
echo " $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================"
echo ""

# Verificacao inicial
log "INFO" "Verificando status inicial..."

if ! check_replica; then
    log "ERROR" "Replica nao esta disponivel. Auto-failover requer replica ativa."
    exit 1
fi

if ! is_replica_standby; then
    log "ERROR" "Replica nao esta em modo standby. Pode ja ter sido promovida."
    exit 1
fi

log "OK" "Replica em modo standby. Monitoramento pode iniciar."

# Modo daemon
if [ "$DAEMON" = true ]; then
    log "INFO" "Iniciando em modo daemon..."
    echo $$ > "$PID_FILE"
    nohup bash -c "$(declare -f check_master check_replica is_replica_standby get_replication_lag promote_replica notify_failover log monitor_loop); monitor_loop" >> "$LOG_FILE" 2>&1 &
    echo "PID: $!"
    echo "Log: $LOG_FILE"
else
    monitor_loop
fi
