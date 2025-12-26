#!/bin/bash
# ============================================
# Conecta Plus - Sistema de Backup Automatizado
# Inclui: PostgreSQL, Redis, MongoDB, Configs
# ============================================

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configurações
BACKUP_DIR="/opt/conecta-plus/backups"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30
LOG_FILE="/var/log/conecta-plus/backup.log"

# Carregar variáveis de ambiente
if [ -f /opt/conecta-plus/.env ]; then
    export $(grep -v '^#' /opt/conecta-plus/.env | xargs)
fi

# Função de log
log() {
    local level=$1
    local message=$2
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${timestamp} [${level}] ${message}" | tee -a "$LOG_FILE"
}

# Banner
show_banner() {
    echo -e "${BLUE}"
    echo "============================================"
    echo "    Conecta Plus - Sistema de Backup"
    echo "============================================"
    echo -e "${NC}"
}

# Criar diretórios de backup
mkdir -p "$BACKUP_DIR"/{database,redis,mongodb,configs,uploads}
mkdir -p "$(dirname "$LOG_FILE")"

# ==========================================
# BACKUP POSTGRESQL
# ==========================================
backup_postgres() {
    echo -e "${YELLOW}[PostgreSQL] Realizando backup...${NC}"

    POSTGRES_BACKUP="$BACKUP_DIR/database/postgres_${DATE}.sql.gz"

    if docker ps | grep -q conecta-postgres; then
        # NOTA: O banco real usa conecta_user/conecta_db (verificado via pg_roles/pg_database)
        docker exec conecta-postgres pg_dump \
            -U "${POSTGRES_USER:-conecta_user}" \
            -d "${POSTGRES_DB:-conecta_db}" \
            --format=plain \
            --no-owner \
            --no-privileges \
            2>/dev/null | gzip > "$POSTGRES_BACKUP"

        if [ -f "$POSTGRES_BACKUP" ] && [ -s "$POSTGRES_BACKUP" ]; then
            POSTGRES_SIZE=$(du -h "$POSTGRES_BACKUP" | cut -f1)
            log "INFO" "Backup PostgreSQL: $POSTGRES_BACKUP ($POSTGRES_SIZE)"
            echo -e "${GREEN}   ✅ PostgreSQL backup concluído ($POSTGRES_SIZE)${NC}"
        else
            log "WARN" "Backup PostgreSQL vazio"
            echo -e "${YELLOW}   ⚠️ PostgreSQL backup vazio${NC}"
        fi
    else
        log "WARN" "Container PostgreSQL não encontrado"
        echo -e "${YELLOW}   ⚠️ Container PostgreSQL não encontrado${NC}"
    fi
}

# ==========================================
# BACKUP REDIS
# ==========================================
backup_redis() {
    echo -e "${YELLOW}[Redis] Realizando backup...${NC}"

    REDIS_BACKUP="$BACKUP_DIR/redis/redis_${DATE}.rdb"

    if docker ps | grep -q conecta-redis; then
        # Forçar save do Redis
        docker exec conecta-redis redis-cli \
            -a "${REDIS_PASSWORD:-redis_secret_2024}" \
            BGSAVE 2>/dev/null || true
        sleep 3

        # Copiar arquivo de dump
        docker cp conecta-redis:/data/dump.rdb "$REDIS_BACKUP" 2>/dev/null || true

        if [ -f "$REDIS_BACKUP" ]; then
            gzip "$REDIS_BACKUP"
            REDIS_SIZE=$(du -h "${REDIS_BACKUP}.gz" | cut -f1)
            log "INFO" "Backup Redis: ${REDIS_BACKUP}.gz ($REDIS_SIZE)"
            echo -e "${GREEN}   ✅ Redis backup concluído ($REDIS_SIZE)${NC}"
        else
            log "WARN" "Backup Redis não disponível"
            echo -e "${YELLOW}   ⚠️ Redis backup não disponível${NC}"
        fi
    else
        log "WARN" "Container Redis não encontrado"
        echo -e "${YELLOW}   ⚠️ Container Redis não encontrado${NC}"
    fi
}

# ==========================================
# BACKUP MONGODB
# ==========================================
backup_mongodb() {
    echo -e "${YELLOW}[MongoDB] Realizando backup...${NC}"

    MONGO_BACKUP="$BACKUP_DIR/mongodb/mongodb_${DATE}"

    if docker ps | grep -q conecta-mongodb; then
        docker exec conecta-mongodb mongodump \
            --username="${MONGO_USER:-conecta}" \
            --password="${MONGO_PASSWORD:-mongo_secret_2024}" \
            --authenticationDatabase=admin \
            --db=conecta_plus \
            --out=/tmp/mongodump 2>/dev/null || true

        docker cp conecta-mongodb:/tmp/mongodump "$MONGO_BACKUP" 2>/dev/null || true
        docker exec conecta-mongodb rm -rf /tmp/mongodump 2>/dev/null || true

        if [ -d "$MONGO_BACKUP" ]; then
            tar -czf "${MONGO_BACKUP}.tar.gz" -C "$BACKUP_DIR/mongodb" "mongodb_${DATE}"
            rm -rf "$MONGO_BACKUP"
            MONGO_SIZE=$(du -h "${MONGO_BACKUP}.tar.gz" | cut -f1)
            log "INFO" "Backup MongoDB: ${MONGO_BACKUP}.tar.gz ($MONGO_SIZE)"
            echo -e "${GREEN}   ✅ MongoDB backup concluído ($MONGO_SIZE)${NC}"
        else
            log "WARN" "Backup MongoDB não disponível"
            echo -e "${YELLOW}   ⚠️ MongoDB backup não disponível${NC}"
        fi
    else
        log "WARN" "Container MongoDB não encontrado"
        echo -e "${YELLOW}   ⚠️ Container MongoDB não encontrado${NC}"
    fi
}

# ==========================================
# BACKUP CONFIGURAÇÕES
# ==========================================
backup_configs() {
    echo -e "${YELLOW}[Configs] Realizando backup...${NC}"

    CONFIG_BACKUP="$BACKUP_DIR/configs/configs_${DATE}.tar.gz"

    tar -czf "$CONFIG_BACKUP" \
        -C /opt/conecta-plus \
        --exclude='*.log' \
        --exclude='node_modules' \
        --exclude='__pycache__' \
        --exclude='.git' \
        --exclude='backups' \
        --exclude='.next' \
        .env \
        docker/ \
        scripts/ \
        2>/dev/null || true

    if [ -f "$CONFIG_BACKUP" ]; then
        CONFIG_SIZE=$(du -h "$CONFIG_BACKUP" | cut -f1)
        log "INFO" "Backup Configs: $CONFIG_BACKUP ($CONFIG_SIZE)"
        echo -e "${GREEN}   ✅ Configurações backup concluído ($CONFIG_SIZE)${NC}"
    else
        log "WARN" "Backup de configurações falhou"
        echo -e "${YELLOW}   ⚠️ Backup de configurações falhou${NC}"
    fi
}

# ==========================================
# BACKUP UPLOADS
# ==========================================
backup_uploads() {
    echo -e "${YELLOW}[Uploads] Realizando backup...${NC}"

    UPLOADS_DIR="/opt/conecta-plus/data/uploads"
    UPLOADS_BACKUP="$BACKUP_DIR/uploads/uploads_${DATE}.tar.gz"

    if [ -d "$UPLOADS_DIR" ] && [ "$(ls -A $UPLOADS_DIR 2>/dev/null)" ]; then
        tar -czf "$UPLOADS_BACKUP" -C "$UPLOADS_DIR" . 2>/dev/null || true

        if [ -f "$UPLOADS_BACKUP" ]; then
            UPLOADS_SIZE=$(du -h "$UPLOADS_BACKUP" | cut -f1)
            log "INFO" "Backup Uploads: $UPLOADS_BACKUP ($UPLOADS_SIZE)"
            echo -e "${GREEN}   ✅ Uploads backup concluído ($UPLOADS_SIZE)${NC}"
        fi
    else
        log "INFO" "Diretório de uploads vazio ou não existe"
        echo -e "${YELLOW}   ⚠️ Uploads vazio ou não existe${NC}"
    fi
}

# ==========================================
# LIMPEZA DE BACKUPS ANTIGOS
# ==========================================
cleanup_old_backups() {
    echo -e "${YELLOW}[Limpeza] Removendo backups antigos (>${RETENTION_DAYS} dias)...${NC}"

    DELETED=$(find "$BACKUP_DIR" -type f -mtime +$RETENTION_DAYS -delete -print 2>/dev/null | wc -l)
    log "INFO" "Backups antigos removidos: $DELETED arquivos"
    echo -e "${GREEN}   ✅ Limpeza concluída ($DELETED arquivos removidos)${NC}"
}

# ==========================================
# LISTAR BACKUPS
# ==========================================
list_backups() {
    echo ""
    echo -e "${BLUE}=== Backups Disponíveis ===${NC}"
    echo ""

    echo -e "${YELLOW}PostgreSQL:${NC}"
    ls -lh "$BACKUP_DIR/database/"*.gz 2>/dev/null | tail -5 || echo "  Nenhum backup"
    echo ""

    echo -e "${YELLOW}Redis:${NC}"
    ls -lh "$BACKUP_DIR/redis/"*.gz 2>/dev/null | tail -5 || echo "  Nenhum backup"
    echo ""

    echo -e "${YELLOW}MongoDB:${NC}"
    ls -lh "$BACKUP_DIR/mongodb/"*.tar.gz 2>/dev/null | tail -5 || echo "  Nenhum backup"
    echo ""

    echo -e "${YELLOW}Configurações:${NC}"
    ls -lh "$BACKUP_DIR/configs/"*.tar.gz 2>/dev/null | tail -5 || echo "  Nenhum backup"
    echo ""

    echo -e "${YELLOW}Uploads:${NC}"
    ls -lh "$BACKUP_DIR/uploads/"*.tar.gz 2>/dev/null | tail -5 || echo "  Nenhum backup"
    echo ""

    TOTAL=$(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1)
    echo -e "Total: ${GREEN}$TOTAL${NC}"
}

# ==========================================
# RESTAURAR POSTGRESQL
# ==========================================
restore_postgres() {
    BACKUP_FILE=$1

    if [ -z "$BACKUP_FILE" ]; then
        echo "Uso: $0 restore-postgres <arquivo.sql.gz>"
        exit 1
    fi

    echo -e "${YELLOW}Restaurando PostgreSQL de: $BACKUP_FILE${NC}"

    # NOTA: O banco real usa conecta_user/conecta_db (verificado via pg_roles/pg_database)
    gunzip -c "$BACKUP_FILE" | docker exec -i conecta-postgres psql \
        -U "${POSTGRES_USER:-conecta_user}" \
        -d "${POSTGRES_DB:-conecta_db}"

    echo -e "${GREEN}✅ Restauração do PostgreSQL concluída${NC}"
}

# ==========================================
# BACKUP COMPLETO
# ==========================================
full_backup() {
    show_banner
    log "INFO" "Iniciando backup completo..."

    START_TIME=$(date +%s)

    backup_postgres
    backup_redis
    backup_mongodb
    backup_configs
    backup_uploads
    cleanup_old_backups

    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))

    echo ""
    echo -e "${BLUE}============================================${NC}"
    echo -e "${GREEN}       BACKUP CONCLUÍDO COM SUCESSO!${NC}"
    echo -e "${BLUE}============================================${NC}"
    echo ""
    echo -e "Data: $(date '+%Y-%m-%d %H:%M:%S')"
    echo -e "Duração: ${DURATION}s"
    echo -e "Diretório: $BACKUP_DIR"

    TOTAL_SIZE=$(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1)
    echo -e "Tamanho total: ${GREEN}$TOTAL_SIZE${NC}"
    echo ""

    log "INFO" "Backup completo finalizado em ${DURATION}s"
}

# ==========================================
# MAIN
# ==========================================
case "${1:-full}" in
    "full")
        full_backup
        ;;
    "postgres")
        backup_postgres
        ;;
    "redis")
        backup_redis
        ;;
    "mongodb")
        backup_mongodb
        ;;
    "configs")
        backup_configs
        ;;
    "uploads")
        backup_uploads
        ;;
    "list")
        list_backups
        ;;
    "restore-postgres")
        restore_postgres "$2"
        ;;
    "cleanup")
        cleanup_old_backups
        ;;
    "help"|*)
        echo "Uso: $0 {full|postgres|redis|mongodb|configs|uploads|list|cleanup|restore-postgres}"
        echo ""
        echo "Comandos:"
        echo "  full             - Backup completo (padrão)"
        echo "  postgres         - Backup apenas PostgreSQL"
        echo "  redis            - Backup apenas Redis"
        echo "  mongodb          - Backup apenas MongoDB"
        echo "  configs          - Backup configurações"
        echo "  uploads          - Backup arquivos enviados"
        echo "  list             - Listar backups"
        echo "  cleanup          - Limpar backups antigos"
        echo "  restore-postgres - Restaurar PostgreSQL"
        ;;
esac
