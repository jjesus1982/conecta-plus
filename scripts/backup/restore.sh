#!/bin/bash
# ============================================
# Conecta Plus - Restore de Backup
# ============================================

set -e

# Configuracoes
BACKUP_DIR="${BACKUP_DIR:-/opt/conecta-plus/backups}"
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-conecta-postgres}"
POSTGRES_USER="${POSTGRES_USER:-conecta_user}"
POSTGRES_DB="${POSTGRES_DB:-conecta_db}"

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "[INFO] $1"; }
log_ok() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Listar backups disponiveis
list_backups() {
    echo "============================================"
    echo "     Backups Disponiveis"
    echo "============================================"
    echo ""

    local i=1
    for dir in $(ls -dr ${BACKUP_DIR}/*/postgres/*.sql.gz 2>/dev/null | head -10); do
        echo "  [$i] $(basename $dir) - $(du -h $dir | cut -f1)"
        ((i++))
    done

    if [ $i -eq 1 ]; then
        log_warn "Nenhum backup encontrado em ${BACKUP_DIR}"
        exit 1
    fi
}

# Restore PostgreSQL
restore_postgres() {
    local backup_file=$1

    if [ ! -f "${backup_file}" ]; then
        log_error "Arquivo nao encontrado: ${backup_file}"
        exit 1
    fi

    log_warn "ATENCAO: Isso ira sobrescrever o banco de dados atual!"
    echo -n "Confirma restore de $(basename ${backup_file})? [y/N] "
    read confirm

    if [ "${confirm}" != "y" ] && [ "${confirm}" != "Y" ]; then
        log_info "Restore cancelado"
        exit 0
    fi

    log_info "Iniciando restore..."

    # Desconectar usuarios ativos
    docker exec ${POSTGRES_CONTAINER} psql -U ${POSTGRES_USER} -d postgres -c \
        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='${POSTGRES_DB}' AND pid <> pg_backend_pid();" 2>/dev/null || true

    # Drop e recreate database
    docker exec ${POSTGRES_CONTAINER} psql -U ${POSTGRES_USER} -d postgres -c \
        "DROP DATABASE IF EXISTS ${POSTGRES_DB};"
    docker exec ${POSTGRES_CONTAINER} psql -U ${POSTGRES_USER} -d postgres -c \
        "CREATE DATABASE ${POSTGRES_DB} OWNER ${POSTGRES_USER};"

    # Restore
    gunzip -c "${backup_file}" | docker exec -i ${POSTGRES_CONTAINER} psql -U ${POSTGRES_USER} -d ${POSTGRES_DB}

    log_ok "Restore concluido com sucesso!"
    log_info "Reinicie os containers para aplicar as mudancas: docker-compose restart"
}

# Main
case "${1:-list}" in
    list)
        list_backups
        ;;
    postgres)
        if [ -z "$2" ]; then
            log_error "Uso: $0 postgres <arquivo_backup.sql.gz>"
            exit 1
        fi
        restore_postgres "$2"
        ;;
    *)
        echo "Uso: $0 {list|postgres <arquivo>}"
        echo ""
        echo "Comandos:"
        echo "  list              - Lista backups disponiveis"
        echo "  postgres <file>   - Restore do PostgreSQL"
        exit 0
        ;;
esac
