-- ============================================
-- Conecta Plus - Migration v2.0.1
-- Adição de colunas faltantes para produção
-- ============================================

-- ============ USUARIOS ============
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS auth_provider VARCHAR(50) DEFAULT 'LOCAL';
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS oauth_id VARCHAR(255);
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS oauth_access_token TEXT;
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS oauth_refresh_token TEXT;
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS oauth_token_expires TIMESTAMP;
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS ldap_dn VARCHAR(500);
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS ldap_groups TEXT[];
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS last_login TIMESTAMP;

-- Corrigir valores enum para uppercase
UPDATE usuarios SET role = UPPER(role) WHERE role IS NOT NULL AND role != UPPER(role);
UPDATE usuarios SET auth_provider = 'LOCAL' WHERE auth_provider = 'local' OR auth_provider IS NULL;

-- ============ OCORRENCIAS ============
ALTER TABLE ocorrencias ADD COLUMN IF NOT EXISTS prazo_estimado TIMESTAMP;
ALTER TABLE ocorrencias ADD COLUMN IF NOT EXISTS prazo_origem VARCHAR(20) DEFAULT 'sla';
ALTER TABLE ocorrencias ADD COLUMN IF NOT EXISTS sla_config_id UUID;
ALTER TABLE ocorrencias ADD COLUMN IF NOT EXISTS sla_notificado_amarelo BOOLEAN DEFAULT FALSE;
ALTER TABLE ocorrencias ADD COLUMN IF NOT EXISTS sla_notificado_vermelho BOOLEAN DEFAULT FALSE;
ALTER TABLE ocorrencias ADD COLUMN IF NOT EXISTS sla_estourado BOOLEAN DEFAULT FALSE;
ALTER TABLE ocorrencias ADD COLUMN IF NOT EXISTS timeline JSONB DEFAULT '[]';
ALTER TABLE ocorrencias ADD COLUMN IF NOT EXISTS avaliacao_nota INTEGER;
ALTER TABLE ocorrencias ADD COLUMN IF NOT EXISTS avaliacao_comentario TEXT;
ALTER TABLE ocorrencias ADD COLUMN IF NOT EXISTS avaliacao_data TIMESTAMP;
ALTER TABLE ocorrencias ADD COLUMN IF NOT EXISTS avaliacao_solicitada BOOLEAN DEFAULT FALSE;
ALTER TABLE ocorrencias ADD COLUMN IF NOT EXISTS notificacoes_enviadas JSONB DEFAULT '[]';
ALTER TABLE ocorrencias ADD COLUMN IF NOT EXISTS primeira_resposta_at TIMESTAMP;
ALTER TABLE ocorrencias ADD COLUMN IF NOT EXISTS primeira_resposta_por UUID;
ALTER TABLE ocorrencias ADD COLUMN IF NOT EXISTS tempo_resolucao_minutos INTEGER;

-- Criar índices se não existirem
CREATE INDEX IF NOT EXISTS idx_ocorrencias_prazo_estimado ON ocorrencias(prazo_estimado);
CREATE INDEX IF NOT EXISTS idx_ocorrencias_sla_estourado ON ocorrencias(sla_estourado);

-- ============ CONFIRMAÇÃO ============
SELECT 'Migration v2.0.1 completed successfully' AS status;
