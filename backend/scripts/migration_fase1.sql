-- =====================================================
-- Conecta Plus - Migration FASE 1: Fundações
-- Event Sourcing + Audit Log
-- =====================================================

-- Usar schema conecta
SET search_path TO conecta, public;

-- =====================================================
-- TABELA: domain_events
-- Armazena todos os eventos de domínio para Event Sourcing
-- =====================================================
CREATE TABLE IF NOT EXISTS domain_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aggregate_id VARCHAR(100) NOT NULL,
    aggregate_type VARCHAR(50) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    causation_id VARCHAR(100),
    correlation_id VARCHAR(100),
    version INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índices para domain_events
CREATE INDEX IF NOT EXISTS idx_domain_events_aggregate
    ON domain_events(aggregate_id, aggregate_type);
CREATE INDEX IF NOT EXISTS idx_domain_events_type
    ON domain_events(event_type);
CREATE INDEX IF NOT EXISTS idx_domain_events_timestamp
    ON domain_events(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_domain_events_correlation
    ON domain_events(correlation_id);

-- Comentários
COMMENT ON TABLE domain_events IS 'Event Store para Event Sourcing';
COMMENT ON COLUMN domain_events.aggregate_id IS 'ID da entidade (visitante, alarme, etc)';
COMMENT ON COLUMN domain_events.aggregate_type IS 'Tipo da entidade (Visitante, Alarme, etc)';
COMMENT ON COLUMN domain_events.event_type IS 'Tipo do evento (VisitanteAutorizado, AlarmeArmado, etc)';
COMMENT ON COLUMN domain_events.payload IS 'Dados do evento em JSON';
COMMENT ON COLUMN domain_events.causation_id IS 'ID do comando que causou este evento';
COMMENT ON COLUMN domain_events.correlation_id IS 'ID para rastrear fluxo completo de eventos';

-- =====================================================
-- TABELA: audit_logs
-- Log de auditoria para compliance e debugging
-- =====================================================
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id VARCHAR(100) NOT NULL,
    user_id VARCHAR(100),
    user_email VARCHAR(255),
    user_role VARCHAR(50),
    ip_address INET,
    user_agent TEXT,
    details JSONB DEFAULT '{}',
    old_values JSONB,
    new_values JSONB,
    status VARCHAR(20) DEFAULT 'success',
    error_message TEXT,
    duration_ms INTEGER,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    correlation_id VARCHAR(100)
);

-- Índices para audit_logs
CREATE INDEX IF NOT EXISTS idx_audit_logs_entity
    ON audit_logs(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user
    ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action
    ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp
    ON audit_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_correlation
    ON audit_logs(correlation_id);

-- Comentários
COMMENT ON TABLE audit_logs IS 'Log de auditoria para compliance';
COMMENT ON COLUMN audit_logs.action IS 'Ação realizada (CREATE, UPDATE, DELETE, LOGIN, etc)';
COMMENT ON COLUMN audit_logs.old_values IS 'Valores anteriores (para UPDATE)';
COMMENT ON COLUMN audit_logs.new_values IS 'Novos valores (para CREATE/UPDATE)';
COMMENT ON COLUMN audit_logs.status IS 'success, failure, error';

-- =====================================================
-- TABELA: system_health_snapshots
-- Snapshots periódicos de saúde do sistema
-- =====================================================
CREATE TABLE IF NOT EXISTS system_health_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    status VARCHAR(20) NOT NULL,
    components JSONB NOT NULL,
    circuit_breakers JSONB,
    metrics JSONB,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Índice por timestamp
CREATE INDEX IF NOT EXISTS idx_health_snapshots_timestamp
    ON system_health_snapshots(timestamp DESC);

-- Retenção: manter apenas últimos 7 dias
-- (Executar via cron job ou pg_cron)
-- DELETE FROM system_health_snapshots WHERE timestamp < NOW() - INTERVAL '7 days';

-- =====================================================
-- VIEW: recent_domain_events
-- Eventos recentes para debugging
-- =====================================================
CREATE OR REPLACE VIEW recent_domain_events AS
SELECT
    id,
    aggregate_type,
    aggregate_id,
    event_type,
    payload,
    timestamp,
    correlation_id
FROM domain_events
ORDER BY timestamp DESC
LIMIT 100;

-- =====================================================
-- VIEW: audit_summary
-- Resumo de auditoria por dia
-- =====================================================
CREATE OR REPLACE VIEW audit_summary AS
SELECT
    DATE(timestamp) as date,
    action,
    entity_type,
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE status = 'success') as success_count,
    COUNT(*) FILTER (WHERE status = 'failure') as failure_count,
    AVG(duration_ms) as avg_duration_ms
FROM audit_logs
WHERE timestamp > NOW() - INTERVAL '30 days'
GROUP BY DATE(timestamp), action, entity_type
ORDER BY date DESC, total DESC;

-- =====================================================
-- FUNÇÃO: append_domain_event
-- Função helper para inserir eventos
-- =====================================================
CREATE OR REPLACE FUNCTION append_domain_event(
    p_aggregate_id VARCHAR(100),
    p_aggregate_type VARCHAR(50),
    p_event_type VARCHAR(100),
    p_payload JSONB,
    p_correlation_id VARCHAR(100) DEFAULT NULL,
    p_causation_id VARCHAR(100) DEFAULT NULL
) RETURNS UUID AS $$
DECLARE
    v_event_id UUID;
BEGIN
    INSERT INTO domain_events (
        aggregate_id,
        aggregate_type,
        event_type,
        payload,
        correlation_id,
        causation_id
    ) VALUES (
        p_aggregate_id,
        p_aggregate_type,
        p_event_type,
        p_payload,
        p_correlation_id,
        p_causation_id
    ) RETURNING id INTO v_event_id;

    RETURN v_event_id;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- FUNÇÃO: log_audit
-- Função helper para inserir logs de auditoria
-- =====================================================
CREATE OR REPLACE FUNCTION log_audit(
    p_action VARCHAR(100),
    p_entity_type VARCHAR(50),
    p_entity_id VARCHAR(100),
    p_user_id VARCHAR(100) DEFAULT NULL,
    p_details JSONB DEFAULT '{}',
    p_correlation_id VARCHAR(100) DEFAULT NULL
) RETURNS UUID AS $$
DECLARE
    v_log_id UUID;
BEGIN
    INSERT INTO audit_logs (
        action,
        entity_type,
        entity_id,
        user_id,
        details,
        correlation_id
    ) VALUES (
        p_action,
        p_entity_type,
        p_entity_id,
        p_user_id,
        p_details,
        p_correlation_id
    ) RETURNING id INTO v_log_id;

    RETURN v_log_id;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- Verificação
-- =====================================================
DO $$
BEGIN
    RAISE NOTICE 'Migration FASE 1 concluída com sucesso!';
    RAISE NOTICE 'Tabelas criadas: domain_events, audit_logs, system_health_snapshots';
    RAISE NOTICE 'Views criadas: recent_domain_events, audit_summary';
    RAISE NOTICE 'Funções criadas: append_domain_event, log_audit';
END $$;
