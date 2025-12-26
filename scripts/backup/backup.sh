#!/bin/bash
# ============================================
# Conecta Plus - Backup Automatizado
# ============================================
# Executa backup de:
# - PostgreSQL (dados principais)
# - Redis (cache - opcional)
# - MongoDB (logs e documentos)
# - Uploads (arquivos de midia)
# ============================================

set -e

# Configuracoes
BACKUP_DIR="${BACKUP_DIR:-/opt/conecta-plus/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DATE_DIR=$(date +%Y-%m-%d)

# Containers
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-conecta-postgres}"
REDIS_CONTAINER="${REDIS_CONTAINER:-conecta-redis}"
MONGO_CONTAINER="${MONGO_CONTAINER:-conecta-mongodb}"

# Credenciais (do .env ou variaveis)
POSTGRES_USER="${POSTGRES_USER:-conecta_user}"
POSTGRES_DB="${POSTGRES_DB:-conecta_db}"
MONGO_USER="${MONGO_USER:-conecta}"
MONGO_PASSWORD="${MONGO_PASSWORD:-}"

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging
log_info() { echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"; }
log_ok() { echo -e "${GREEN}[OK]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"; }

# Criar estrutura de diretorios
setup_dirs() {
    mkdir -p "${BACKUP_DIR}/${DATE_DIR}"/{postgres,redis,mongodb,uploads}
    log_info "Diretorio de backup: ${BACKUP_DIR}/${DATE_DIR}"
}

# Backup PostgreSQL
backup_postgres() {
    log_info "Iniciando backup do PostgreSQL..."

    local backup_file="${BACKUP_DIR}/${DATE_DIR}/postgres/db_${TIMESTAMP}.sql.gz"

    if docker exec ${POSTGRES_CONTAINER} pg_dump -U ${POSTGRES_USER} ${POSTGRES_DB} | gzip > "${backup_file}"; then
        local size=$(du -h "${backup_file}" | cut -f1)
        log_ok "PostgreSQL backup concluido: ${backup_file} (${size})"
        echo "${backup_file}"
    else
        log_error "Falha no backup do PostgreSQL"
        return 1
    fi
}

# Backup Redis (RDB snapshot)
backup_redis() {
    log_info "Iniciando backup do Redis..."

    local backup_file="${BACKUP_DIR}/${DATE_DIR}/redis/dump_${TIMESTAMP}.rdb"

    # Forcar save no Redis
    docker exec ${REDIS_CONTAINER} redis-cli -a "${REDIS_PASSWORD}" BGSAVE 2>/dev/null || true
    sleep 2  # Aguardar save

    # Copiar dump.rdb
    if docker cp ${REDIS_CONTAINER}:/data/dump.rdb "${backup_file}" 2>/dev/null; then
        local size=$(du -h "${backup_file}" | cut -f1)
        log_ok "Redis backup concluido: ${backup_file} (${size})"
        echo "${backup_file}"
    else
        log_warn "Redis backup ignorado (sem dados ou container inativo)"
    fi
}

# Backup MongoDB
backup_mongodb() {
    log_info "Iniciando backup do MongoDB..."

    local backup_file="${BACKUP_DIR}/${DATE_DIR}/mongodb/mongo_${TIMESTAMP}.gz"

    if docker exec ${MONGO_CONTAINER} mongodump \
        --username="${MONGO_USER}" \
        --password="${MONGO_PASSWORD}" \
        --authenticationDatabase=admin \
        --archive --gzip 2>/dev/null > "${backup_file}"; then
        local size=$(du -h "${backup_file}" | cut -f1)
        log_ok "MongoDB backup concluido: ${backup_file} (${size})"
        echo "${backup_file}"
    else
        log_warn "MongoDB backup ignorado (container inativo ou sem dados)"
    fi
}

# Backup de uploads/media
backup_uploads() {
    log_info "Iniciando backup de uploads..."

    local src_dir="/opt/conecta-plus/shared/uploads"
    local backup_file="${BACKUP_DIR}/${DATE_DIR}/uploads/uploads_${TIMESTAMP}.tar.gz"

    if [ -d "${src_dir}" ] && [ "$(ls -A ${src_dir} 2>/dev/null)" ]; then
        if tar -czf "${backup_file}" -C "$(dirname ${src_dir})" "$(basename ${src_dir})" 2>/dev/null; then
            local size=$(du -h "${backup_file}" | cut -f1)
            log_ok "Uploads backup concluido: ${backup_file} (${size})"
            echo "${backup_file}"
        else
            log_warn "Falha no backup de uploads"
        fi
    else
        log_warn "Diretorio de uploads vazio ou inexistente"
    fi
}

# Limpeza de backups antigos
cleanup_old_backups() {
    log_info "Limpando backups mais antigos que ${RETENTION_DAYS} dias..."

    local deleted=$(find "${BACKUP_DIR}" -type f -mtime +${RETENTION_DAYS} -delete -print | wc -l)
    local deleted_dirs=$(find "${BACKUP_DIR}" -type d -empty -delete -print 2>/dev/null | wc -l)

    log_ok "Limpeza concluida: ${deleted} arquivos, ${deleted_dirs} diretorios vazios removidos"
}

# Verificar integridade do backup
verify_backup() {
    local backup_file=$1

    if [ -f "${backup_file}" ]; then
        if gzip -t "${backup_file}" 2>/dev/null; then
            log_ok "Verificacao de integridade OK: $(basename ${backup_file})"
            return 0
        else
            log_error "Backup corrompido: ${backup_file}"
            return 1
        fi
    fi
}

# Gerar relatorio
generate_report() {
    local report_file="${BACKUP_DIR}/${DATE_DIR}/backup_report_${TIMESTAMP}.txt"

    cat > "${report_file}" <<EOF
============================================
BACKUP REPORT - Conecta Plus
============================================
Data: $(date '+%Y-%m-%d %H:%M:%S')
Host: $(hostname)
============================================

ARQUIVOS GERADOS:
$(find "${BACKUP_DIR}/${DATE_DIR}" -type f -name "*${TIMESTAMP}*" -exec ls -lh {} \;)

ESPACO EM DISCO:
$(df -h "${BACKUP_DIR}" | tail -1)

TOTAL DO BACKUP:
$(du -sh "${BACKUP_DIR}/${DATE_DIR}" | cut -f1)

============================================
EOF

    log_ok "Relatorio gerado: ${report_file}"
    cat "${report_file}"
}

# Main
main() {
    echo ""
    echo "============================================"
    echo "     Conecta Plus - Backup System"
    echo "============================================"
    echo ""

    setup_dirs

    # Executar backups
    backup_postgres || true
    backup_redis || true
    backup_mongodb || true
    backup_uploads || true

    # Limpeza
    cleanup_old_backups

    # Relatorio
    generate_report

    echo ""
    log_ok "Backup concluido com sucesso!"
    echo ""
}

# Executar
main "$@"
