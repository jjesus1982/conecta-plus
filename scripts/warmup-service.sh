#!/bin/bash
#
# Conecta Plus - Warmup Service
# ==============================
# Script de servico para executar warmup periodico ou no startup.
#
# Instalacao como systemd service:
#   sudo cp /opt/conecta-plus/config/systemd/conecta-warmup.service /etc/systemd/system/
#   sudo systemctl daemon-reload
#   sudo systemctl enable conecta-warmup
#   sudo systemctl start conecta-warmup
#

set -e

# Configuracoes
BASE_DIR="/opt/conecta-plus"
SCRIPTS_DIR="${BASE_DIR}/scripts"
LOGS_DIR="${BASE_DIR}/logs"
BACKEND_URL=${BACKEND_URL:-"http://localhost:8000"}
REDIS_HOST=${REDIS_HOST:-"localhost"}
REDIS_PORT=${REDIS_PORT:-6379}

# Funcao de log
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Aguarda servicos estarem prontos
wait_for_services() {
    local max_wait=120
    local waited=0

    log "Aguardando servicos ficarem disponiveis..."

    # Aguarda Redis
    while ! nc -z "$REDIS_HOST" "$REDIS_PORT" 2>/dev/null && [ $waited -lt $max_wait ]; do
        sleep 2
        waited=$((waited + 2))
    done

    if [ $waited -ge $max_wait ]; then
        log "WARN: Timeout aguardando Redis"
    else
        log "Redis disponivel"
    fi

    # Aguarda Backend
    waited=0
    while ! curl -sf "${BACKEND_URL}/health" > /dev/null 2>&1 && [ $waited -lt $max_wait ]; do
        sleep 2
        waited=$((waited + 2))
    done

    if [ $waited -ge $max_wait ]; then
        log "WARN: Timeout aguardando Backend"
    else
        log "Backend disponivel"
    fi
}

# Executa warmup
run_warmup() {
    log "Executando warmup..."

    cd "$BASE_DIR"

    # Executa localmente com Python3 (warmup acessa endpoints HTTP, nao precisa estar no container)
    if command -v python3 &> /dev/null && python3 -c "import requests, redis" 2>/dev/null; then
        log "Executando warmup localmente com Python3..."
        python3 "${SCRIPTS_DIR}/warmup.py" --verbose 2>&1 | tee -a "${LOGS_DIR}/warmup.log"
    else
        log "ERROR: Python3 ou dependencias (requests, redis) nao disponivel"
        return 1
    fi

    log "Warmup concluido"
}

# Main
main() {
    mkdir -p "$LOGS_DIR"

    log "=========================================="
    log "Conecta Plus - Warmup Service"
    log "=========================================="

    # Aguarda servicos
    wait_for_services

    # Executa warmup
    run_warmup

    log "Servico finalizado"
}

main "$@"
