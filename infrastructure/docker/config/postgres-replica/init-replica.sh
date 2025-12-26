#!/bin/bash
# ============================================
# Conecta Plus - Script de Inicializacao da Replica
# ============================================

set -e

MASTER_HOST="${MASTER_HOST:-conecta-postgres}"
MASTER_PORT="${MASTER_PORT:-5432}"
REPLICATOR_USER="${REPLICATOR_USER:-replicator}"
REPLICATOR_PASS="${REPLICATOR_PASS:-repl_conecta_2024_secure}"
DATA_DIR="/var/lib/postgresql/data"
CONFIG_FILE="/etc/postgresql/postgresql.conf"

echo "============================================"
echo " Conecta Plus - Inicializando Replica"
echo " $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================"

# Verifica se ja foi inicializado como replica
if [ -f "${DATA_DIR}/standby.signal" ]; then
    echo "[INFO] Replica ja inicializada. Iniciando PostgreSQL..."
    exec docker-entrypoint.sh postgres -c config_file=${CONFIG_FILE}
fi

echo "[INFO] Primeira execucao - configurando replica..."

# Limpa diretorio de dados
echo "[INFO] Limpando diretorio de dados..."
rm -rf ${DATA_DIR}/*

# Aguarda o master estar pronto
echo "[INFO] Aguardando master (${MASTER_HOST}:${MASTER_PORT})..."
until pg_isready -h ${MASTER_HOST} -p ${MASTER_PORT} -U ${POSTGRES_USER:-conecta_user}; do
    echo "[INFO] Master nao disponivel, aguardando..."
    sleep 2
done
echo "[OK] Master disponivel!"

# Copia os dados do master via pg_basebackup
echo "[INFO] Iniciando pg_basebackup (pode demorar alguns minutos)..."
PGPASSWORD=${REPLICATOR_PASS} pg_basebackup \
    -h ${MASTER_HOST} \
    -p ${MASTER_PORT} \
    -U ${REPLICATOR_USER} \
    -D ${DATA_DIR} \
    -Fp -Xs -P -R

# Cria arquivo standby.signal (PostgreSQL 12+)
echo "[INFO] Criando standby.signal..."
touch ${DATA_DIR}/standby.signal

# Configura conexao com o master
echo "[INFO] Configurando conexao com master..."
cat >> ${DATA_DIR}/postgresql.auto.conf << AUTOCONF
primary_conninfo = 'host=${MASTER_HOST} port=${MASTER_PORT} user=${REPLICATOR_USER} password=${REPLICATOR_PASS} application_name=postgres_replica'
primary_slot_name = 'replica_slot'
hot_standby = on
hot_standby_feedback = on
AUTOCONF

echo "[OK] Replica inicializada com sucesso!"
echo ""

# Inicia PostgreSQL
echo "[INFO] Iniciando PostgreSQL como replica..."
exec docker-entrypoint.sh postgres -c config_file=${CONFIG_FILE}
