#!/bin/bash
# ============================================
# Conecta Plus - Configurar Master para Replicacao
# Executa apos o container postgres estar rodando
# ============================================

set -e

# Cores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

MASTER_CONTAINER="conecta-postgres"
# NOTA: O banco real usa conecta_user/conecta_db (verificado via pg_roles/pg_database)
POSTGRES_USER="${POSTGRES_USER:-conecta_user}"
POSTGRES_DB="${POSTGRES_DB:-conecta_db}"
REPLICATOR_PASSWORD="${REPLICATOR_PASSWORD:-repl_conecta_2024_secure}"

echo ""
echo "============================================"
echo " Conecta Plus - Setup Master para Replicacao"
echo " $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================"
echo ""

# Verifica se master esta rodando
echo -e "${BLUE}[INFO]${NC} Verificando container master..."
if ! docker exec "$MASTER_CONTAINER" pg_isready -q 2>/dev/null; then
    echo -e "${RED}[ERRO]${NC} Container $MASTER_CONTAINER nao esta respondendo!"
    echo "Execute primeiro: docker compose up -d postgres"
    exit 1
fi
echo -e "${GREEN}[OK]${NC} Master online"

# Criar usuario de replicacao
echo ""
echo -e "${BLUE}[INFO]${NC} Criando usuario de replicacao..."
docker exec "$MASTER_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'replicator') THEN
        CREATE ROLE replicator WITH REPLICATION LOGIN PASSWORD '$REPLICATOR_PASSWORD';
        RAISE NOTICE 'Usuario replicator criado!';
    ELSE
        ALTER ROLE replicator WITH PASSWORD '$REPLICATOR_PASSWORD';
        RAISE NOTICE 'Senha do replicator atualizada.';
    END IF;
END \$\$;
"
echo -e "${GREEN}[OK]${NC} Usuario replicator configurado"

# Criar slot de replicacao
echo ""
echo -e "${BLUE}[INFO]${NC} Criando slot de replicacao..."
docker exec "$MASTER_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "
SELECT CASE
    WHEN EXISTS (SELECT FROM pg_replication_slots WHERE slot_name = 'replica_slot')
    THEN 'Slot replica_slot ja existe'
    ELSE pg_create_physical_replication_slot('replica_slot')::text
END AS resultado;
"
echo -e "${GREEN}[OK]${NC} Slot de replicacao configurado"

# Verificar configuracoes WAL
echo ""
echo -e "${BLUE}[INFO]${NC} Verificando configuracoes de WAL..."
docker exec "$MASTER_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "
SELECT name, setting, context
FROM pg_settings
WHERE name IN ('wal_level', 'max_wal_senders', 'max_replication_slots', 'wal_keep_size')
ORDER BY name;
"

# Verificar se precisa reiniciar
WAL_LEVEL=$(docker exec "$MASTER_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c "SHOW wal_level;" | tr -d ' ')

if [ "$WAL_LEVEL" != "replica" ] && [ "$WAL_LEVEL" != "logical" ]; then
    echo ""
    echo -e "${YELLOW}[WARN]${NC} wal_level atual: $WAL_LEVEL"
    echo -e "${YELLOW}[WARN]${NC} Necessario wal_level=replica para replicacao!"
    echo ""
    echo "Para aplicar a configuracao, reinicie o container:"
    echo "  docker compose restart postgres"
    echo ""
    echo "IMPORTANTE: Certifique-se que postgresql.conf esta montado:"
    echo "  - ./config/postgres/postgresql.conf:/etc/postgresql/postgresql.conf"
    echo ""
else
    echo -e "${GREEN}[OK]${NC} wal_level=$WAL_LEVEL (correto)"
fi

# Verificar pg_hba.conf
echo ""
echo -e "${BLUE}[INFO]${NC} Verificando regras de acesso (pg_hba.conf)..."
docker exec "$MASTER_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "
SELECT type, database, user_name, address, auth_method
FROM pg_hba_file_rules
WHERE database::text LIKE '%replication%' OR user_name::text LIKE '%replicator%';
"

echo ""
echo "============================================"
echo -e "${GREEN}SETUP DO MASTER CONCLUIDO!${NC}"
echo "============================================"
echo ""
echo "PROXIMOS PASSOS:"
echo ""
echo "1. Adicione os volumes de configuracao ao docker-compose.yml:"
echo "   volumes:"
echo "     - ./config/postgres/postgresql.conf:/etc/postgresql/postgresql.conf:ro"
echo "     - ./config/postgres/pg_hba.conf:/etc/postgresql/pg_hba.conf:ro"
echo ""
echo "2. Adicione o comando para usar a config customizada:"
echo "   command: postgres -c config_file=/etc/postgresql/postgresql.conf -c hba_file=/etc/postgresql/pg_hba.conf"
echo ""
echo "3. Reinicie o container postgres:"
echo "   docker compose restart postgres"
echo ""
echo "4. Para iniciar a replica:"
echo "   cd /opt/conecta-plus/infrastructure/docker"
echo "   docker compose -f docker-compose.replica.yml up -d"
echo ""
