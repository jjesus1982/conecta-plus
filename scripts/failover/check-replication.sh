#!/bin/bash
# ============================================
# Conecta Plus - Verificar Status da Replicacao
# Monitora health da replicacao PostgreSQL
# ============================================

set -e

# Cores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

MASTER_CONTAINER="conecta-postgres"
REPLICA_CONTAINER="conecta-postgres-replica"
# NOTA: O banco real usa conecta_user/conecta_db (verificado via pg_roles/pg_database)
POSTGRES_USER="${POSTGRES_USER:-conecta_user}"
POSTGRES_DB="${POSTGRES_DB:-conecta_db}"

echo ""
echo "============================================"
echo " Conecta Plus - Status da Replicacao"
echo " $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================"
echo ""

# Funcao para checar container
check_container() {
    local container=$1
    local name=$2

    if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
        if docker exec "$container" pg_isready -q 2>/dev/null; then
            echo -e "${GREEN}[OK]${NC} $name: Online e aceitando conexoes"
            return 0
        else
            echo -e "${YELLOW}[WARN]${NC} $name: Container rodando mas nao responde"
            return 1
        fi
    else
        echo -e "${RED}[ERRO]${NC} $name: Container nao encontrado ou parado"
        return 1
    fi
}

# Verificar Master
echo "1. Status dos Containers:"
echo "   ----------------------"
check_container "$MASTER_CONTAINER" "Master"
MASTER_OK=$?

check_container "$REPLICA_CONTAINER" "Replica"
REPLICA_OK=$?
echo ""

# Se master OK, mostrar info de replicacao
if [ $MASTER_OK -eq 0 ]; then
    echo "2. Informacoes do Master:"
    echo "   ----------------------"

    # Verifica se esta configurado para replicacao
    WAL_LEVEL=$(docker exec "$MASTER_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c \
        "SHOW wal_level;" 2>/dev/null | tr -d ' ')

    MAX_SENDERS=$(docker exec "$MASTER_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c \
        "SHOW max_wal_senders;" 2>/dev/null | tr -d ' ')

    echo "   wal_level: $WAL_LEVEL"
    echo "   max_wal_senders: $MAX_SENDERS"

    # Verificar slots
    echo ""
    echo "   Slots de Replicacao:"
    docker exec "$MASTER_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c \
        "SELECT slot_name, slot_type, active, restart_lsn FROM pg_replication_slots;" 2>/dev/null || echo "   Nenhum slot encontrado"

    # Verificar replicas conectadas
    echo ""
    echo "   Replicas Conectadas:"
    docker exec "$MASTER_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c \
        "SELECT client_addr, state, sent_lsn, write_lsn, flush_lsn, replay_lsn,
                (extract(epoch from now() - backend_start))::int as connected_secs
         FROM pg_stat_replication;" 2>/dev/null || echo "   Nenhuma replica conectada"
    echo ""
fi

# Se replica OK, mostrar info
if [ $REPLICA_OK -eq 0 ]; then
    echo "3. Informacoes da Replica:"
    echo "   -----------------------"

    # Verificar se esta em recovery
    IS_RECOVERY=$(docker exec "$REPLICA_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c \
        "SELECT pg_is_in_recovery();" 2>/dev/null | tr -d ' ')

    if [ "$IS_RECOVERY" = "t" ]; then
        echo -e "   Modo: ${GREEN}Standby (Hot Standby)${NC}"

        # Lag de replicacao
        LAG_BYTES=$(docker exec "$REPLICA_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c \
            "SELECT pg_wal_lsn_diff(pg_last_wal_receive_lsn(), pg_last_wal_replay_lsn());" 2>/dev/null | tr -d ' ')

        LAG_SECONDS=$(docker exec "$REPLICA_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c \
            "SELECT CASE
                WHEN pg_last_wal_receive_lsn() = pg_last_wal_replay_lsn() THEN 0
                ELSE EXTRACT(EPOCH FROM now() - pg_last_xact_replay_timestamp())::int
             END;" 2>/dev/null | tr -d ' ')

        echo "   Lag (bytes): $LAG_BYTES"
        echo "   Lag (segundos): $LAG_SECONDS"

        # Ultima transacao replicada
        LAST_REPLAY=$(docker exec "$REPLICA_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c \
            "SELECT pg_last_xact_replay_timestamp();" 2>/dev/null | tr -d ' ')
        echo "   Ultima transacao: $LAST_REPLAY"
    else
        echo -e "   Modo: ${YELLOW}Master (NAO esta em recovery)${NC}"
        echo "   AVISO: Esta instancia foi promovida!"
    fi
    echo ""
fi

# Resumo
echo "============================================"
echo " RESUMO"
echo "============================================"

if [ $MASTER_OK -eq 0 ] && [ $REPLICA_OK -eq 0 ]; then
    echo -e "${GREEN}Replicacao funcionando normalmente.${NC}"
elif [ $MASTER_OK -ne 0 ] && [ $REPLICA_OK -eq 0 ]; then
    echo -e "${RED}ALERTA: Master offline! Considere failover.${NC}"
    echo "Comando: /opt/conecta-plus/scripts/failover/promote-replica.sh"
elif [ $MASTER_OK -eq 0 ] && [ $REPLICA_OK -ne 0 ]; then
    echo -e "${YELLOW}AVISO: Replica offline. Sistema sem redundancia.${NC}"
else
    echo -e "${RED}CRITICO: Ambos master e replica offline!${NC}"
fi
echo ""
