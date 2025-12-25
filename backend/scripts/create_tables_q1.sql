-- ============================================
-- CONECTA PLUS - CRIACAO DE TABELAS Q1
-- Fundamentos de Tranquilidade
-- ============================================

-- Usar schema conecta
SET search_path TO conecta, public;

-- ============================================
-- 1. TABELA: sla_configs
-- Configuracao de SLA por tipo e prioridade
-- ============================================

CREATE TABLE IF NOT EXISTS sla_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome VARCHAR(100) NOT NULL,
    descricao VARCHAR(500),
    tipo_entidade VARCHAR(50) NOT NULL,
    subtipo VARCHAR(50),
    prioridade VARCHAR(20) DEFAULT 'media',
    prazo_primeira_resposta INTEGER DEFAULT 60,
    prazo_resolucao INTEGER DEFAULT 1440,
    prazo_alerta_amarelo INTEGER,
    prazo_alerta_vermelho INTEGER,
    escalar_automaticamente BOOLEAN DEFAULT TRUE,
    escalar_para UUID REFERENCES usuarios(id),
    notificar_solicitante BOOLEAN DEFAULT TRUE,
    notificar_responsavel BOOLEAN DEFAULT TRUE,
    notificar_gestor BOOLEAN DEFAULT FALSE,
    template_abertura VARCHAR(500) DEFAULT 'Recebemos sua solicitacao #{numero}. Prazo estimado: {prazo}.',
    template_atualizacao VARCHAR(500) DEFAULT 'Sua solicitacao #{numero} foi atualizada: {status}.',
    template_resolucao VARCHAR(500) DEFAULT 'Sua solicitacao #{numero} foi resolvida. Avalie nosso atendimento!',
    template_sla_proximo VARCHAR(500) DEFAULT 'Atencao: Solicitacao #{numero} com prazo em {tempo_restante}.',
    template_sla_estourado VARCHAR(500) DEFAULT 'URGENTE: SLA estourado na solicitacao #{numero}!',
    condominio_id UUID REFERENCES condominios(id),
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sla_configs_tipo_entidade ON sla_configs(tipo_entidade);
CREATE INDEX IF NOT EXISTS idx_sla_configs_subtipo ON sla_configs(subtipo);
CREATE INDEX IF NOT EXISTS idx_sla_configs_condominio ON sla_configs(condominio_id);

-- ============================================
-- 2. TABELA: decision_logs
-- Registro unificado de decisoes
-- ============================================

CREATE TABLE IF NOT EXISTS decision_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    modulo VARCHAR(50) NOT NULL,
    tipo_decisao VARCHAR(50) NOT NULL,
    criticidade VARCHAR(20) DEFAULT 'medio',
    entidade_tipo VARCHAR(50),
    entidade_id UUID,
    entidade_descricao VARCHAR(255),
    titulo VARCHAR(255) NOT NULL,
    descricao TEXT,
    justificativa TEXT,
    regra_sistema VARCHAR(100),
    regra_descricao VARCHAR(500),
    usuario_id UUID REFERENCES usuarios(id),
    usuario_nome VARCHAR(100),
    usuario_role VARCHAR(50),
    ip_address INET,
    user_agent VARCHAR(500),
    session_id VARCHAR(100),
    protecao_exibida BOOLEAN DEFAULT FALSE,
    mensagem_protecao VARCHAR(255),
    sucesso BOOLEAN DEFAULT TRUE,
    resultado TEXT,
    erro TEXT,
    dados_antes JSONB,
    dados_depois JSONB,
    metadata JSONB DEFAULT '{}',
    condominio_id UUID REFERENCES condominios(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_decision_logs_modulo ON decision_logs(modulo);
CREATE INDEX IF NOT EXISTS idx_decision_logs_tipo ON decision_logs(tipo_decisao);
CREATE INDEX IF NOT EXISTS idx_decision_logs_usuario ON decision_logs(usuario_id);
CREATE INDEX IF NOT EXISTS idx_decision_logs_entidade ON decision_logs(entidade_id);
CREATE INDEX IF NOT EXISTS idx_decision_logs_condominio ON decision_logs(condominio_id);
CREATE INDEX IF NOT EXISTS idx_decision_logs_created ON decision_logs(created_at);

-- ============================================
-- 3. TABELA: tranquilidade_snapshots
-- Estado de tranquilidade por perfil
-- ============================================

CREATE TABLE IF NOT EXISTS tranquilidade_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    perfil VARCHAR(50) NOT NULL,
    usuario_id UUID REFERENCES usuarios(id),
    estado VARCHAR(20) NOT NULL DEFAULT 'verde',
    score FLOAT DEFAULT 100.0,
    mensagem_principal VARCHAR(255),
    mensagem_secundaria VARCHAR(500),
    alertas_criticos INTEGER DEFAULT 0,
    alertas_medios INTEGER DEFAULT 0,
    ocorrencias_abertas INTEGER DEFAULT 0,
    ocorrencias_sla_proximo INTEGER DEFAULT 0,
    ocorrencias_sla_estourado INTEGER DEFAULT 0,
    cameras_offline INTEGER DEFAULT 0,
    inadimplencia_percentual FLOAT DEFAULT 0.0,
    precisa_de_voce JSONB DEFAULT '[]',
    resolvido_hoje INTEGER DEFAULT 0,
    recomendacao VARCHAR(500),
    recomendacao_tipo VARCHAR(50),
    saude_condominio JSONB DEFAULT '{}',
    proxima_tarefa JSONB,
    condominio_id UUID NOT NULL REFERENCES condominios(id),
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tranquilidade_perfil ON tranquilidade_snapshots(perfil);
CREATE INDEX IF NOT EXISTS idx_tranquilidade_usuario ON tranquilidade_snapshots(usuario_id);
CREATE INDEX IF NOT EXISTS idx_tranquilidade_condominio ON tranquilidade_snapshots(condominio_id);
CREATE INDEX IF NOT EXISTS idx_tranquilidade_calculated ON tranquilidade_snapshots(calculated_at);

-- ============================================
-- 4. TABELA: recomendacao_templates
-- Templates de recomendacoes
-- ============================================

CREATE TABLE IF NOT EXISTS recomendacao_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    codigo VARCHAR(50) UNIQUE NOT NULL,
    nome VARCHAR(100) NOT NULL,
    perfil VARCHAR(50),
    condicao JSONB NOT NULL,
    prioridade INTEGER DEFAULT 50,
    tipo VARCHAR(50) DEFAULT 'informativo',
    mensagem VARCHAR(500) NOT NULL,
    mensagem_curta VARCHAR(100),
    icone VARCHAR(50),
    cor VARCHAR(20),
    link VARCHAR(255),
    link_texto VARCHAR(50),
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_recomendacao_codigo ON recomendacao_templates(codigo);
CREATE INDEX IF NOT EXISTS idx_recomendacao_perfil ON recomendacao_templates(perfil);

-- ============================================
-- 5. ALTERACOES: ocorrencias
-- Adicionar campos novos Q1
-- ============================================

-- Adicionar campos se nao existirem
DO $$
BEGIN
    -- prazo_estimado
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'conecta' AND table_name = 'ocorrencias' AND column_name = 'prazo_estimado') THEN
        ALTER TABLE ocorrencias ADD COLUMN prazo_estimado TIMESTAMP;
        CREATE INDEX IF NOT EXISTS idx_ocorrencias_prazo ON ocorrencias(prazo_estimado);
    END IF;

    -- prazo_origem
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'conecta' AND table_name = 'ocorrencias' AND column_name = 'prazo_origem') THEN
        ALTER TABLE ocorrencias ADD COLUMN prazo_origem VARCHAR(20) DEFAULT 'sla';
    END IF;

    -- sla_config_id
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'conecta' AND table_name = 'ocorrencias' AND column_name = 'sla_config_id') THEN
        ALTER TABLE ocorrencias ADD COLUMN sla_config_id UUID REFERENCES sla_configs(id);
    END IF;

    -- sla_notificado_amarelo
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'conecta' AND table_name = 'ocorrencias' AND column_name = 'sla_notificado_amarelo') THEN
        ALTER TABLE ocorrencias ADD COLUMN sla_notificado_amarelo BOOLEAN DEFAULT FALSE;
    END IF;

    -- sla_notificado_vermelho
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'conecta' AND table_name = 'ocorrencias' AND column_name = 'sla_notificado_vermelho') THEN
        ALTER TABLE ocorrencias ADD COLUMN sla_notificado_vermelho BOOLEAN DEFAULT FALSE;
    END IF;

    -- sla_estourado
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'conecta' AND table_name = 'ocorrencias' AND column_name = 'sla_estourado') THEN
        ALTER TABLE ocorrencias ADD COLUMN sla_estourado BOOLEAN DEFAULT FALSE;
        CREATE INDEX IF NOT EXISTS idx_ocorrencias_sla_estourado ON ocorrencias(sla_estourado);
    END IF;

    -- timeline
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'conecta' AND table_name = 'ocorrencias' AND column_name = 'timeline') THEN
        ALTER TABLE ocorrencias ADD COLUMN timeline JSONB DEFAULT '[]';
    END IF;

    -- avaliacao_nota
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'conecta' AND table_name = 'ocorrencias' AND column_name = 'avaliacao_nota') THEN
        ALTER TABLE ocorrencias ADD COLUMN avaliacao_nota INTEGER;
    END IF;

    -- avaliacao_comentario
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'conecta' AND table_name = 'ocorrencias' AND column_name = 'avaliacao_comentario') THEN
        ALTER TABLE ocorrencias ADD COLUMN avaliacao_comentario TEXT;
    END IF;

    -- avaliacao_data
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'conecta' AND table_name = 'ocorrencias' AND column_name = 'avaliacao_data') THEN
        ALTER TABLE ocorrencias ADD COLUMN avaliacao_data TIMESTAMP;
    END IF;

    -- avaliacao_solicitada
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'conecta' AND table_name = 'ocorrencias' AND column_name = 'avaliacao_solicitada') THEN
        ALTER TABLE ocorrencias ADD COLUMN avaliacao_solicitada BOOLEAN DEFAULT FALSE;
    END IF;

    -- notificacoes_enviadas
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'conecta' AND table_name = 'ocorrencias' AND column_name = 'notificacoes_enviadas') THEN
        ALTER TABLE ocorrencias ADD COLUMN notificacoes_enviadas JSONB DEFAULT '[]';
    END IF;

    -- primeira_resposta_at
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'conecta' AND table_name = 'ocorrencias' AND column_name = 'primeira_resposta_at') THEN
        ALTER TABLE ocorrencias ADD COLUMN primeira_resposta_at TIMESTAMP;
    END IF;

    -- primeira_resposta_por
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'conecta' AND table_name = 'ocorrencias' AND column_name = 'primeira_resposta_por') THEN
        ALTER TABLE ocorrencias ADD COLUMN primeira_resposta_por UUID REFERENCES usuarios(id);
    END IF;
END $$;

-- ============================================
-- 6. DADOS INICIAIS
-- Configuracoes padrao de SLA
-- ============================================

INSERT INTO sla_configs (nome, tipo_entidade, subtipo, prioridade, prazo_resolucao)
SELECT * FROM (VALUES
    ('SLA Seguranca Critica', 'ocorrencia', 'seguranca', 'critica', 15),
    ('SLA Seguranca Urgente', 'ocorrencia', 'seguranca', 'urgente', 30),
    ('SLA Seguranca Alta', 'ocorrencia', 'seguranca', 'alta', 60),
    ('SLA Seguranca Media', 'ocorrencia', 'seguranca', 'media', 120),
    ('SLA Vazamento Critica', 'ocorrencia', 'vazamento', 'critica', 30),
    ('SLA Vazamento Urgente', 'ocorrencia', 'vazamento', 'urgente', 60),
    ('SLA Vazamento Alta', 'ocorrencia', 'vazamento', 'alta', 120),
    ('SLA Manutencao Alta', 'ocorrencia', 'manutencao', 'alta', 480),
    ('SLA Manutencao Media', 'ocorrencia', 'manutencao', 'media', 1440),
    ('SLA Barulho Alta', 'ocorrencia', 'barulho', 'alta', 240),
    ('SLA Barulho Media', 'ocorrencia', 'barulho', 'media', 720),
    ('SLA Padrao', 'ocorrencia', 'outros', 'media', 1440)
) AS v(nome, tipo_entidade, subtipo, prioridade, prazo_resolucao)
WHERE NOT EXISTS (SELECT 1 FROM sla_configs LIMIT 1);

-- Recomendacoes padrao
INSERT INTO recomendacao_templates (codigo, nome, prioridade, tipo, mensagem)
SELECT * FROM (VALUES
    ('TUDO_OK', 'Tudo sob controle', 10, 'parabens', 'Nenhuma acao necessaria agora. Tudo esta sob controle!'),
    ('INADIMPLENCIA_ALTA', 'Inadimplencia alta', 80, 'acao', 'Inadimplencia acima do ideal. Acoes recomendadas disponiveis.'),
    ('SLA_ESTOURADO', 'SLA estourado', 90, 'alerta', 'Ocorrencia(s) com SLA estourado. Priorize imediatamente!'),
    ('CAMERAS_OFFLINE', 'Cameras offline', 85, 'alerta', 'Cameras offline. Seguranca comprometida.')
) AS v(codigo, nome, prioridade, tipo, mensagem)
WHERE NOT EXISTS (SELECT 1 FROM recomendacao_templates LIMIT 1);

-- ============================================
-- FIM DA MIGRACAO Q1
-- ============================================

SELECT 'Migracao Q1 concluida com sucesso!' AS resultado;
