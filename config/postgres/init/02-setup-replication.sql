-- ============================================
-- Conecta Plus - Setup para Streaming Replication
-- Cria usuario de replicacao e slot
-- ============================================

-- Criar usuario de replicacao (se nao existir)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'replicator') THEN
        CREATE ROLE replicator WITH REPLICATION LOGIN PASSWORD 'repl_conecta_2024_secure';
        RAISE NOTICE 'Usuario replicator criado com sucesso!';
    ELSE
        RAISE NOTICE 'Usuario replicator ja existe.';
    END IF;
END $$;

-- Criar slot de replicacao fisica (se nao existir)
-- O slot garante que WAL nao seja removido antes de ser consumido pela replica
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_replication_slots WHERE slot_name = 'replica_slot') THEN
        PERFORM pg_create_physical_replication_slot('replica_slot');
        RAISE NOTICE 'Slot de replicacao replica_slot criado com sucesso!';
    ELSE
        RAISE NOTICE 'Slot replica_slot ja existe.';
    END IF;
END $$;

-- Verificar configuracao
SELECT
    'wal_level' as parametro,
    setting as valor
FROM pg_settings
WHERE name = 'wal_level'
UNION ALL
SELECT
    'max_wal_senders' as parametro,
    setting as valor
FROM pg_settings
WHERE name = 'max_wal_senders'
UNION ALL
SELECT
    'max_replication_slots' as parametro,
    setting as valor
FROM pg_settings
WHERE name = 'max_replication_slots';

-- Listar slots de replicacao
SELECT slot_name, slot_type, active FROM pg_replication_slots;

-- Mensagem de sucesso
DO $$
BEGIN
    RAISE NOTICE 'Setup de replicacao concluido! Master pronto para receber replicas.';
END $$;
