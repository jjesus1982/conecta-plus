#!/bin/bash
###############################################################################
# Backup Script - Production - Conecta Plus
# Executa backup completo de todos os bancos de dados e arquivos críticos
###############################################################################

set -euo pipefail

# Configuration
BACKUP_DIR="/opt/conecta-plus/backups"
DATE=$(date +%Y%m%d-%H%M%S)
RETENTION_DAYS=30
S3_BUCKET="${BACKUP_S3_BUCKET:-conecta-plus-backups}"

# Docker containers
POSTGRES_CONTAINER="conecta-postgres-prod"
MONGODB_CONTAINER="conecta-mongodb-prod"
REDIS_CONTAINER="conecta-redis-prod"

# Logging
LOG_FILE="/var/log/conecta-backups.log"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

error() {
    echo "[ERROR] $1" | tee -a "$LOG_FILE" >&2
    exit 1
}

# Create backup directories
mkdir -p "$BACKUP_DIR"/{postgres,mongodb,redis,configs}

###############################################################################
# 1. BACKUP POSTGRESQL
###############################################################################

backup_postgres() {
    log "Iniciando backup PostgreSQL..."

    if ! docker ps | grep -q "$POSTGRES_CONTAINER"; then
        error "Container PostgreSQL não está rodando!"
    fi

    # Full database dump
    docker exec "$POSTGRES_CONTAINER" pg_dumpall -U "${POSTGRES_USER:-conecta_prod_user}" \
        > "$BACKUP_DIR/postgres/dump-$DATE.sql" || error "Falha no backup PostgreSQL"

    # Compress
    gzip "$BACKUP_DIR/postgres/dump-$DATE.sql"

    # Create latest symlink
    ln -sf "dump-$DATE.sql.gz" "$BACKUP_DIR/postgres/latest.sql.gz"

    log "✓ Backup PostgreSQL concluído: dump-$DATE.sql.gz"
}

###############################################################################
# 2. BACKUP MONGODB
###############################################################################

backup_mongodb() {
    log "Iniciando backup MongoDB..."

    if ! docker ps | grep -q "$MONGODB_CONTAINER"; then
        error "Container MongoDB não está rodando!"
    fi

    # MongoDB dump
    docker exec "$MONGODB_CONTAINER" mongodump \
        --out "/backups/mongodb-$DATE" \
        --gzip || error "Falha no backup MongoDB"

    # Move from container to host
    docker cp "$MONGODB_CONTAINER:/backups/mongodb-$DATE" "$BACKUP_DIR/mongodb/"

    # Compress
    tar -czf "$BACKUP_DIR/mongodb/dump-$DATE.tar.gz" -C "$BACKUP_DIR/mongodb" "mongodb-$DATE"
    rm -rf "$BACKUP_DIR/mongodb/mongodb-$DATE"

    # Create latest symlink
    ln -sf "dump-$DATE.tar.gz" "$BACKUP_DIR/mongodb/latest.tar.gz"

    log "✓ Backup MongoDB concluído: dump-$DATE.tar.gz"
}

###############################################################################
# 3. BACKUP REDIS
###############################################################################

backup_redis() {
    log "Iniciando backup Redis..."

    if ! docker ps | grep -q "$REDIS_CONTAINER"; then
        error "Container Redis não está rodando!"
    fi

    # Force Redis to save
    docker exec "$REDIS_CONTAINER" redis-cli SAVE || error "Falha no SAVE do Redis"

    # Copy RDB file
    docker cp "$REDIS_CONTAINER:/data/dump.rdb" "$BACKUP_DIR/redis/dump-$DATE.rdb"

    # Compress
    gzip "$BACKUP_DIR/redis/dump-$DATE.rdb"

    # Create latest symlink
    ln -sf "dump-$DATE.rdb.gz" "$BACKUP_DIR/redis/latest.rdb.gz"

    log "✓ Backup Redis concluído: dump-$DATE.rdb.gz"
}

###############################################################################
# 4. BACKUP CONFIGURATIONS
###############################################################################

backup_configs() {
    log "Iniciando backup de configurações..."

    # Backup critical config files
    tar -czf "$BACKUP_DIR/configs/configs-$DATE.tar.gz" \
        -C /opt/conecta-plus \
        .env.production \
        docker-compose.production.yml \
        monitoring/ \
        config/ \
        scripts/ 2>/dev/null || log "Alguns arquivos de config não encontrados"

    # Create latest symlink
    ln -sf "configs-$DATE.tar.gz" "$BACKUP_DIR/configs/latest.tar.gz"

    log "✓ Backup de configurações concluído: configs-$DATE.tar.gz"
}

###############################################################################
# 5. UPLOAD TO S3 (if configured)
###############################################################################

upload_to_s3() {
    if ! command -v aws &> /dev/null; then
        log "AWS CLI não instalado, pulando upload para S3"
        return 0
    fi

    if [ -z "$S3_BUCKET" ]; then
        log "S3_BUCKET não configurado, pulando upload"
        return 0
    fi

    log "Iniciando upload para S3: s3://$S3_BUCKET..."

    # Upload all backups
    aws s3 sync "$BACKUP_DIR" "s3://$S3_BUCKET/backups/$DATE/" \
        --exclude "*" \
        --include "postgres/dump-$DATE.sql.gz" \
        --include "mongodb/dump-$DATE.tar.gz" \
        --include "redis/dump-$DATE.rdb.gz" \
        --include "configs/configs-$DATE.tar.gz" \
        --storage-class STANDARD_IA || log "Falha no upload para S3"

    log "✓ Upload para S3 concluído"
}

###############################################################################
# 6. CLEANUP OLD BACKUPS
###############################################################################

cleanup_old_backups() {
    log "Removendo backups antigos (> $RETENTION_DAYS dias)..."

    # Delete local backups older than retention period
    find "$BACKUP_DIR/postgres" -name "dump-*.sql.gz" -mtime +$RETENTION_DAYS -delete
    find "$BACKUP_DIR/mongodb" -name "dump-*.tar.gz" -mtime +$RETENTION_DAYS -delete
    find "$BACKUP_DIR/redis" -name "dump-*.rdb.gz" -mtime +$RETENTION_DAYS -delete
    find "$BACKUP_DIR/configs" -name "configs-*.tar.gz" -mtime +$RETENTION_DAYS -delete

    # Delete S3 backups if AWS CLI is available
    if command -v aws &> /dev/null && [ -n "$S3_BUCKET" ]; then
        CUTOFF_DATE=$(date -d "$RETENTION_DAYS days ago" +%Y%m%d)
        aws s3 ls "s3://$S3_BUCKET/backups/" | while read -r line; do
            BACKUP_DATE=$(echo "$line" | awk '{print $2}' | cut -d'-' -f1 | tr -d '/')
            if [ "$BACKUP_DATE" -lt "$CUTOFF_DATE" ]; then
                FOLDER=$(echo "$line" | awk '{print $2}' | tr -d '/')
                aws s3 rm "s3://$S3_BUCKET/backups/$FOLDER" --recursive || true
            fi
        done
    fi

    log "✓ Cleanup concluído"
}

###############################################################################
# 7. VERIFY BACKUPS
###############################################################################

verify_backups() {
    log "Verificando integridade dos backups..."

    # Check if files exist and are not empty
    for file in \
        "$BACKUP_DIR/postgres/dump-$DATE.sql.gz" \
        "$BACKUP_DIR/mongodb/dump-$DATE.tar.gz" \
        "$BACKUP_DIR/redis/dump-$DATE.rdb.gz" \
        "$BACKUP_DIR/configs/configs-$DATE.tar.gz"
    do
        if [ ! -s "$file" ]; then
            error "Backup inválido ou vazio: $file"
        fi
    done

    # Test gzip integrity
    gzip -t "$BACKUP_DIR/postgres/dump-$DATE.sql.gz" || error "Arquivo PostgreSQL corrompido"
    gzip -t "$BACKUP_DIR/redis/dump-$DATE.rdb.gz" || error "Arquivo Redis corrompido"
    tar -tzf "$BACKUP_DIR/mongodb/dump-$DATE.tar.gz" > /dev/null || error "Arquivo MongoDB corrompido"
    tar -tzf "$BACKUP_DIR/configs/configs-$DATE.tar.gz" > /dev/null || error "Arquivo configs corrompido"

    log "✓ Todos os backups verificados com sucesso"
}

###############################################################################
# 8. SEND NOTIFICATION
###############################################################################

send_notification() {
    local status=$1
    local message=$2

    # Send email notification (if configured)
    if command -v mail &> /dev/null && [ -n "${ADMIN_EMAIL:-}" ]; then
        echo "$message" | mail -s "Conecta Plus Backup - $status" "$ADMIN_EMAIL"
    fi

    # Send Slack notification (if configured)
    if [ -n "${SLACK_WEBHOOK:-}" ]; then
        curl -X POST "$SLACK_WEBHOOK" \
            -H 'Content-Type: application/json' \
            -d "{\"text\":\"🔒 Backup $status: $message\"}" 2>/dev/null || true
    fi

    # Log to syslog
    logger -t conecta-backup "$status: $message"
}

###############################################################################
# MAIN EXECUTION
###############################################################################

main() {
    log "╔═══════════════════════════════════════════════════════════════╗"
    log "║           CONECTA PLUS - BACKUP PRODUCTION                    ║"
    log "║           $(date +'%Y-%m-%d %H:%M:%S')                                    ║"
    log "╚═══════════════════════════════════════════════════════════════╝"

    START_TIME=$(date +%s)

    # Execute backup steps
    backup_postgres
    backup_mongodb
    backup_redis
    backup_configs
    upload_to_s3
    cleanup_old_backups
    verify_backups

    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))

    # Calculate backup sizes
    TOTAL_SIZE=$(du -sh "$BACKUP_DIR" | awk '{print $1}')

    log "╔═══════════════════════════════════════════════════════════════╗"
    log "║  ✅ BACKUP CONCLUÍDO COM SUCESSO!                             ║"
    log "║                                                               ║"
    log "║  Duração: ${DURATION}s                                        ║"
    log "║  Tamanho total: $TOTAL_SIZE                                   ║"
    log "║  Data: $DATE                                                  ║"
    log "║  Localização: $BACKUP_DIR                                     ║"
    log "╚═══════════════════════════════════════════════════════════════╝"

    # Send success notification
    send_notification "SUCCESS" "Backup concluído em ${DURATION}s. Tamanho: $TOTAL_SIZE"
}

# Error handler
trap 'send_notification "FAILED" "Backup falhou na linha $LINENO"; error "Backup falhou"' ERR

# Run main
main "$@"
