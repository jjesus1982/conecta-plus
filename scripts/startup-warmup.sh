#!/bin/bash
#
# Conecta Plus - Startup Warmup Script
# =====================================
# Script para executar warmup durante startup do container/sistema.
#
# Uso:
#   ./startup-warmup.sh [--wait SECONDS] [--retries COUNT]
#
# Este script aguarda os servicos ficarem disponiveis e executa o warmup.
#

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuracoes padrao
WAIT_SECONDS=${WAIT_SECONDS:-30}
MAX_RETRIES=${MAX_RETRIES:-10}
RETRY_DELAY=${RETRY_DELAY:-5}
BACKEND_URL=${BACKEND_URL:-"http://localhost:8000"}
REDIS_HOST=${REDIS_HOST:-"localhost"}
REDIS_PORT=${REDIS_PORT:-6379}

# Diretorio base
BASE_DIR="/opt/conecta-plus"
SCRIPTS_DIR="${BASE_DIR}/scripts"
LOGS_DIR="${BASE_DIR}/logs"

# Funcao de log
log() {
    local level=$1
    local message=$2
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    case $level in
        "INFO")
            echo -e "${BLUE}[${timestamp}]${NC} ${GREEN}[INFO]${NC} $message"
            ;;
        "WARN")
            echo -e "${BLUE}[${timestamp}]${NC} ${YELLOW}[WARN]${NC} $message"
            ;;
        "ERROR")
            echo -e "${BLUE}[${timestamp}]${NC} ${RED}[ERROR]${NC} $message"
            ;;
        *)
            echo -e "${BLUE}[${timestamp}]${NC} $message"
            ;;
    esac
}

# Aguarda servico TCP ficar disponivel
wait_for_service() {
    local host=$1
    local port=$2
    local service_name=$3
    local retries=0

    log "INFO" "Aguardando $service_name ($host:$port)..."

    while ! nc -z "$host" "$port" 2>/dev/null; do
        retries=$((retries + 1))
        if [ $retries -ge $MAX_RETRIES ]; then
            log "ERROR" "$service_name nao disponivel apos $MAX_RETRIES tentativas"
            return 1
        fi
        log "WARN" "Tentativa $retries/$MAX_RETRIES - aguardando ${RETRY_DELAY}s..."
        sleep $RETRY_DELAY
    done

    log "INFO" "$service_name disponivel!"
    return 0
}

# Aguarda endpoint HTTP responder
wait_for_http() {
    local url=$1
    local service_name=$2
    local retries=0

    log "INFO" "Aguardando $service_name ($url)..."

    while ! curl -sf "$url" > /dev/null 2>&1; do
        retries=$((retries + 1))
        if [ $retries -ge $MAX_RETRIES ]; then
            log "ERROR" "$service_name nao respondeu apos $MAX_RETRIES tentativas"
            return 1
        fi
        log "WARN" "Tentativa $retries/$MAX_RETRIES - aguardando ${RETRY_DELAY}s..."
        sleep $RETRY_DELAY
    done

    log "INFO" "$service_name respondendo!"
    return 0
}

# Executa o warmup Python
run_warmup() {
    log "INFO" "Executando cache warmup..."

    # Verifica se o script existe
    if [ ! -f "${SCRIPTS_DIR}/warmup.py" ]; then
        log "ERROR" "Script warmup.py nao encontrado em ${SCRIPTS_DIR}"
        return 1
    fi

    # Executa o warmup
    cd "$BASE_DIR"

    if python3 "${SCRIPTS_DIR}/warmup.py" --verbose 2>&1 | tee -a "${LOGS_DIR}/warmup.log"; then
        log "INFO" "Warmup concluido com sucesso!"
        return 0
    else
        log "WARN" "Warmup teve alguns erros - verifique o log"
        return 0  # Nao falha o startup por causa do warmup
    fi
}

# Parse de argumentos
while [[ $# -gt 0 ]]; do
    case $1 in
        --wait)
            WAIT_SECONDS="$2"
            shift 2
            ;;
        --retries)
            MAX_RETRIES="$2"
            shift 2
            ;;
        --backend-url)
            BACKEND_URL="$2"
            shift 2
            ;;
        --redis-host)
            REDIS_HOST="$2"
            shift 2
            ;;
        --help)
            echo "Uso: $0 [--wait SECONDS] [--retries COUNT] [--backend-url URL] [--redis-host HOST]"
            exit 0
            ;;
        *)
            log "WARN" "Argumento desconhecido: $1"
            shift
            ;;
    esac
done

# Main
main() {
    log "INFO" "=========================================="
    log "INFO" "Conecta Plus - Startup Warmup"
    log "INFO" "=========================================="
    log "INFO" "Backend URL: $BACKEND_URL"
    log "INFO" "Redis: $REDIS_HOST:$REDIS_PORT"
    log "INFO" "Max retries: $MAX_RETRIES"
    log "INFO" "=========================================="

    # Cria diretorio de logs se nao existir
    mkdir -p "$LOGS_DIR"

    # Aguarda tempo inicial (opcional)
    if [ "$WAIT_SECONDS" -gt 0 ]; then
        log "INFO" "Aguardando ${WAIT_SECONDS}s antes de iniciar..."
        sleep "$WAIT_SECONDS"
    fi

    # Aguarda Redis
    if wait_for_service "$REDIS_HOST" "$REDIS_PORT" "Redis"; then
        log "INFO" "Redis OK"
    else
        log "WARN" "Redis nao disponivel - warmup de cache pode falhar"
    fi

    # Aguarda Backend
    if wait_for_http "${BACKEND_URL}/health" "Backend API"; then
        log "INFO" "Backend OK"
    else
        log "WARN" "Backend nao disponivel - warmup de endpoints pode falhar"
    fi

    # Executa warmup
    run_warmup

    log "INFO" "=========================================="
    log "INFO" "Startup warmup finalizado!"
    log "INFO" "=========================================="

    return 0
}

# Executa
main "$@"
