-- ============================================================
-- MIGRATION: Integração Completa Banco Cora
-- Data: 2025-01-22
-- Descrição: Cria estrutura completa para integração com Cora Bank API V2
-- ============================================================

-- Garante que o schema financeiro existe
CREATE SCHEMA IF NOT EXISTS financeiro;

-- ============================================================
-- TABELA 1: financeiro.contas_cora
-- Vínculo entre condomínios e contas Cora
-- ============================================================

CREATE TABLE IF NOT EXISTS financeiro.contas_cora (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Relacionamentos
    condominio_id UUID NOT NULL REFERENCES condominios(id) ON DELETE CASCADE,
    conta_bancaria_id UUID REFERENCES financeiro.contas_bancarias(id) ON DELETE SET NULL,

    -- Dados da Conta Cora
    cora_account_id VARCHAR(100) NOT NULL UNIQUE,
    cora_document VARCHAR(20) NOT NULL, -- CPF/CNPJ sem formatação
    cora_agencia VARCHAR(10),
    cora_conta VARCHAR(20),
    cora_conta_digito VARCHAR(2),

    -- Configuração
    ambiente VARCHAR(20) NOT NULL DEFAULT 'production', -- production ou sandbox
    api_version VARCHAR(10) NOT NULL DEFAULT 'v2', -- v1 ou v2
    ativa BOOLEAN NOT NULL DEFAULT true,

    -- Credenciais OAuth2 (referencia tabela de tokens)
    client_id_encrypted BYTEA,
    client_id_salt BYTEA,
    client_secret_encrypted BYTEA,
    client_secret_salt BYTEA,

    -- Webhook
    webhook_secret_encrypted BYTEA,
    webhook_secret_salt BYTEA,

    -- Auditoria
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES usuarios(id),
    updated_by UUID REFERENCES usuarios(id),

    -- Constraints
    CONSTRAINT contas_cora_ambiente_check CHECK (ambiente IN ('production', 'sandbox')),
    CONSTRAINT contas_cora_api_version_check CHECK (api_version IN ('v1', 'v2'))
);

-- Índices
CREATE INDEX idx_contas_cora_condominio ON financeiro.contas_cora(condominio_id) WHERE ativa = true;
CREATE INDEX idx_contas_cora_account_id ON financeiro.contas_cora(cora_account_id);
CREATE INDEX idx_contas_cora_documento ON financeiro.contas_cora(cora_document);

-- Unique constraint parcial: apenas uma conta ativa por condomínio
CREATE UNIQUE INDEX uq_contas_cora_condominio_ativa ON financeiro.contas_cora(condominio_id)
    WHERE ativa = true;

-- Comentários
COMMENT ON TABLE financeiro.contas_cora IS 'Contas Cora Bank vinculadas aos condomínios';
COMMENT ON COLUMN financeiro.contas_cora.cora_account_id IS 'ID da conta no Banco Cora';
COMMENT ON COLUMN financeiro.contas_cora.ambiente IS 'Ambiente: production (real) ou sandbox (testes)';

-- ============================================================
-- TABELA 2: financeiro.transacoes_cora
-- Movimentações bancárias (extrato Cora)
-- ============================================================

CREATE TABLE IF NOT EXISTS financeiro.transacoes_cora (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Relacionamentos
    conta_cora_id UUID NOT NULL REFERENCES financeiro.contas_cora(id) ON DELETE CASCADE,
    condominio_id UUID NOT NULL REFERENCES condominios(id) ON DELETE CASCADE,

    -- Dados da Transação Cora
    cora_transaction_id VARCHAR(100) NOT NULL UNIQUE,
    data_transacao DATE NOT NULL,
    tipo VARCHAR(1) NOT NULL, -- C=Crédito, D=Débito
    valor DECIMAL(12, 2) NOT NULL,

    -- Descrição
    descricao TEXT NOT NULL,
    categoria VARCHAR(50), -- INVOICE_PAYMENT, PIX_RECEIVED, TRANSFER, etc

    -- Contrapartida (quem pagou/recebeu)
    contrapartida_nome VARCHAR(255),
    contrapartida_documento VARCHAR(20),

    -- PIX
    end_to_end_id VARCHAR(100), -- ID único PIX (para conciliação)
    pix_txid VARCHAR(50),

    -- Boleto
    nosso_numero VARCHAR(20),
    codigo_barras VARCHAR(60),

    -- Conciliação
    conciliado BOOLEAN NOT NULL DEFAULT false,
    boleto_id UUID REFERENCES financeiro.boletos(id),
    pagamento_id UUID REFERENCES financeiro.pagamentos(id),
    lancamento_id UUID REFERENCES financeiro.lancamentos(id),
    confianca_match DECIMAL(5, 2), -- 0-100 (percentual de confiança da conciliação automática)
    conciliado_em TIMESTAMP,
    conciliado_por UUID REFERENCES usuarios(id),
    conciliacao_manual BOOLEAN DEFAULT false,

    -- Metadados
    raw_data JSONB, -- Dados originais da API

    -- Auditoria
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT transacoes_cora_tipo_check CHECK (tipo IN ('C', 'D')),
    CONSTRAINT transacoes_cora_valor_check CHECK (valor >= 0),
    CONSTRAINT transacoes_cora_confianca_check CHECK (confianca_match IS NULL OR (confianca_match >= 0 AND confianca_match <= 100))
);

-- Índices
CREATE INDEX idx_transacoes_cora_conta ON financeiro.transacoes_cora(conta_cora_id);
CREATE INDEX idx_transacoes_cora_condominio ON financeiro.transacoes_cora(condominio_id);
CREATE INDEX idx_transacoes_cora_data ON financeiro.transacoes_cora(data_transacao DESC);
CREATE INDEX idx_transacoes_cora_tipo ON financeiro.transacoes_cora(tipo);
CREATE INDEX idx_transacoes_cora_conciliado ON financeiro.transacoes_cora(conciliado) WHERE conciliado = false;
CREATE INDEX idx_transacoes_cora_end_to_end ON financeiro.transacoes_cora(end_to_end_id) WHERE end_to_end_id IS NOT NULL;
CREATE INDEX idx_transacoes_cora_nosso_numero ON financeiro.transacoes_cora(nosso_numero) WHERE nosso_numero IS NOT NULL;
CREATE INDEX idx_transacoes_cora_categoria ON financeiro.transacoes_cora(categoria);

-- Comentários
COMMENT ON TABLE financeiro.transacoes_cora IS 'Transações do extrato bancário Cora (sincronizadas da API)';
COMMENT ON COLUMN financeiro.transacoes_cora.end_to_end_id IS 'ID único PIX para rastreamento ponta-a-ponta';
COMMENT ON COLUMN financeiro.transacoes_cora.confianca_match IS 'Percentual de confiança da conciliação automática (0-100)';

-- ============================================================
-- TABELA 3: financeiro.cobrancas_cora
-- Boletos e PIX criados no Cora
-- ============================================================

CREATE TABLE IF NOT EXISTS financeiro.cobrancas_cora (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Relacionamentos
    conta_cora_id UUID NOT NULL REFERENCES financeiro.contas_cora(id) ON DELETE CASCADE,
    condominio_id UUID NOT NULL REFERENCES condominios(id) ON DELETE CASCADE,
    boleto_id UUID REFERENCES financeiro.boletos(id), -- Boleto interno do sistema
    carne_id UUID, -- Se faz parte de um carnê

    -- IDs Cora
    cora_invoice_id VARCHAR(100) UNIQUE, -- ID do boleto na Cora
    cora_pix_txid VARCHAR(50) UNIQUE, -- TXID do PIX Cora

    -- Tipo de Cobrança
    tipo VARCHAR(20) NOT NULL, -- boleto, pix, hibrido

    -- Valores
    valor DECIMAL(12, 2) NOT NULL,
    valor_pago DECIMAL(12, 2),

    -- Datas
    data_vencimento DATE,
    data_criacao TIMESTAMP NOT NULL DEFAULT NOW(),
    data_pagamento TIMESTAMP,
    data_cancelamento TIMESTAMP,

    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'pendente', -- pendente, pago, vencido, cancelado, expirado

    -- Dados do Pagador (CRIPTOGRAFADOS)
    pagador_nome VARCHAR(255),
    pagador_documento_encrypted BYTEA,
    pagador_documento_salt BYTEA,
    pagador_email_encrypted BYTEA,
    pagador_email_salt BYTEA,

    -- PIX
    pix_qrcode TEXT, -- QR Code em base64 ou URL
    pix_copia_cola TEXT, -- EMV do PIX (copia e cola)
    pix_expiracao TIMESTAMP,

    -- Boleto
    codigo_barras VARCHAR(60),
    linha_digitavel VARCHAR(60),
    nosso_numero VARCHAR(20),
    url_pdf TEXT,

    -- Carnê (se aplicável)
    numero_parcela INTEGER,
    total_parcelas INTEGER,

    -- Metadados
    descricao TEXT,
    raw_data JSONB, -- Response original da API

    -- Auditoria
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES usuarios(id),
    updated_by UUID REFERENCES usuarios(id),

    -- Constraints
    CONSTRAINT cobrancas_cora_tipo_check CHECK (tipo IN ('boleto', 'pix', 'hibrido')),
    CONSTRAINT cobrancas_cora_status_check CHECK (status IN ('pendente', 'pago', 'vencido', 'cancelado', 'expirado')),
    CONSTRAINT cobrancas_cora_valor_check CHECK (valor > 0),
    CONSTRAINT cobrancas_cora_valor_pago_check CHECK (valor_pago IS NULL OR valor_pago >= 0),
    CONSTRAINT cobrancas_cora_parcela_check CHECK (
        (numero_parcela IS NULL AND total_parcelas IS NULL) OR
        (numero_parcela > 0 AND total_parcelas > 0 AND numero_parcela <= total_parcelas)
    )
);

-- Índices
CREATE INDEX idx_cobrancas_cora_conta ON financeiro.cobrancas_cora(conta_cora_id);
CREATE INDEX idx_cobrancas_cora_condominio ON financeiro.cobrancas_cora(condominio_id);
CREATE INDEX idx_cobrancas_cora_boleto ON financeiro.cobrancas_cora(boleto_id);
CREATE INDEX idx_cobrancas_cora_invoice_id ON financeiro.cobrancas_cora(cora_invoice_id) WHERE cora_invoice_id IS NOT NULL;
CREATE INDEX idx_cobrancas_cora_pix_txid ON financeiro.cobrancas_cora(cora_pix_txid) WHERE cora_pix_txid IS NOT NULL;
CREATE INDEX idx_cobrancas_cora_status ON financeiro.cobrancas_cora(status);
CREATE INDEX idx_cobrancas_cora_vencimento ON financeiro.cobrancas_cora(data_vencimento) WHERE status = 'pendente';
CREATE INDEX idx_cobrancas_cora_carne ON financeiro.cobrancas_cora(carne_id) WHERE carne_id IS NOT NULL;
CREATE INDEX idx_cobrancas_cora_nosso_numero ON financeiro.cobrancas_cora(nosso_numero) WHERE nosso_numero IS NOT NULL;

-- Comentários
COMMENT ON TABLE financeiro.cobrancas_cora IS 'Cobranças (boletos e PIX) criadas no Banco Cora';
COMMENT ON COLUMN financeiro.cobrancas_cora.tipo IS 'boleto: só boleto, pix: só PIX, hibrido: boleto + PIX';
COMMENT ON COLUMN financeiro.cobrancas_cora.pagador_documento_encrypted IS 'CPF/CNPJ criptografado (AES-256)';

-- ============================================================
-- TABELA 4: financeiro.webhooks_cora
-- Eventos recebidos do Cora (IMUTÁVEL - audit log)
-- ============================================================

CREATE TABLE IF NOT EXISTS financeiro.webhooks_cora (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Dados do Webhook
    event_type VARCHAR(100) NOT NULL,
    event_id VARCHAR(100) NOT NULL UNIQUE, -- ID único do evento na Cora

    -- Payload
    body JSONB NOT NULL, -- Corpo completo do webhook

    -- Assinatura (validação)
    signature VARCHAR(255) NOT NULL,
    signature_valid BOOLEAN NOT NULL,

    -- Processamento
    processado BOOLEAN NOT NULL DEFAULT false,
    processado_em TIMESTAMP,
    resultado JSONB, -- Resultado do processamento
    erro_mensagem TEXT,
    tentativas_processamento INTEGER DEFAULT 0,

    -- Metadados
    ip_origem INET,
    user_agent TEXT,

    -- Auditoria (SEM updated_at - tabela imutável)
    received_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT webhooks_cora_tentativas_check CHECK (tentativas_processamento >= 0)
);

-- Índices
CREATE INDEX idx_webhooks_cora_event_type ON financeiro.webhooks_cora(event_type);
CREATE INDEX idx_webhooks_cora_processado ON financeiro.webhooks_cora(processado) WHERE processado = false;
CREATE INDEX idx_webhooks_cora_received_at ON financeiro.webhooks_cora(received_at DESC);
CREATE INDEX idx_webhooks_cora_event_id ON financeiro.webhooks_cora(event_id);

-- Comentários
COMMENT ON TABLE financeiro.webhooks_cora IS 'Log IMUTÁVEL de webhooks recebidos do Banco Cora (não permite UPDATE)';
COMMENT ON COLUMN financeiro.webhooks_cora.signature_valid IS 'Se a assinatura HMAC-SHA256 foi validada com sucesso';

-- ============================================================
-- TABELA 5: financeiro.cora_tokens
-- Tokens OAuth2 (criptografados)
-- ============================================================

CREATE TABLE IF NOT EXISTS financeiro.cora_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Relacionamento
    conta_cora_id UUID NOT NULL REFERENCES financeiro.contas_cora(id) ON DELETE CASCADE,

    -- Tokens Criptografados (AES-256)
    access_token_encrypted BYTEA NOT NULL,
    access_token_salt BYTEA NOT NULL,
    refresh_token_encrypted BYTEA,
    refresh_token_salt BYTEA,

    -- Expiração
    expires_at TIMESTAMP NOT NULL,
    token_type VARCHAR(20) DEFAULT 'Bearer',

    -- Status
    ativo BOOLEAN NOT NULL DEFAULT true,
    revogado BOOLEAN DEFAULT false,
    revogado_em TIMESTAMP,
    revogado_motivo TEXT,

    -- Auditoria
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT cora_tokens_expires_check CHECK (expires_at > created_at)
);

-- Índices
CREATE INDEX idx_cora_tokens_conta ON financeiro.cora_tokens(conta_cora_id);
CREATE INDEX idx_cora_tokens_ativo ON financeiro.cora_tokens(conta_cora_id, ativo) WHERE ativo = true;
CREATE INDEX idx_cora_tokens_expires ON financeiro.cora_tokens(expires_at);

-- Unique constraint parcial: apenas um token ativo por conta
CREATE UNIQUE INDEX uq_cora_tokens_conta_ativa ON financeiro.cora_tokens(conta_cora_id)
    WHERE ativo = true;

-- Comentários
COMMENT ON TABLE financeiro.cora_tokens IS 'Tokens OAuth2 do Banco Cora (criptografados)';
COMMENT ON COLUMN financeiro.cora_tokens.access_token_encrypted IS 'Access token criptografado com AES-256';

-- ============================================================
-- TABELA 6: financeiro.saldos_cora
-- Cache de saldo (evita chamadas excessivas à API)
-- ============================================================

CREATE TABLE IF NOT EXISTS financeiro.saldos_cora (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Relacionamento
    conta_cora_id UUID NOT NULL UNIQUE REFERENCES financeiro.contas_cora(id) ON DELETE CASCADE,

    -- Saldos
    saldo_disponivel DECIMAL(12, 2) NOT NULL,
    saldo_bloqueado DECIMAL(12, 2) NOT NULL DEFAULT 0,
    saldo_total DECIMAL(12, 2) NOT NULL,

    -- Referência
    data_referencia TIMESTAMP NOT NULL, -- Data/hora do saldo na API

    -- Cache
    valido_ate TIMESTAMP NOT NULL, -- Quando o cache expira (ex: 10 minutos)

    -- Auditoria
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Constraints
    CONSTRAINT saldos_cora_total_check CHECK (saldo_total = saldo_disponivel + saldo_bloqueado),
    CONSTRAINT saldos_cora_validade_check CHECK (valido_ate > data_referencia)
);

-- Índices
CREATE INDEX idx_saldos_cora_conta ON financeiro.saldos_cora(conta_cora_id);
CREATE INDEX idx_saldos_cora_validade ON financeiro.saldos_cora(valido_ate);

-- Comentários
COMMENT ON TABLE financeiro.saldos_cora IS 'Cache de saldo do Banco Cora (TTL: 10 minutos)';
COMMENT ON COLUMN financeiro.saldos_cora.valido_ate IS 'Timestamp de expiração do cache';

-- ============================================================
-- TABELA 7: financeiro.cora_sync_logs
-- Logs de sincronização (extrato, saldo, cobranças)
-- ============================================================

CREATE TABLE IF NOT EXISTS financeiro.cora_sync_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Relacionamento
    conta_cora_id UUID NOT NULL REFERENCES financeiro.contas_cora(id) ON DELETE CASCADE,
    condominio_id UUID NOT NULL REFERENCES condominios(id) ON DELETE CASCADE,

    -- Tipo de Sincronização
    tipo VARCHAR(20) NOT NULL, -- extrato, cobrancas, saldo

    -- Status
    status VARCHAR(20) NOT NULL, -- iniciado, concluido, erro

    -- Período (para extrato)
    data_inicio DATE,
    data_fim DATE,

    -- Resultados
    registros_processados INTEGER DEFAULT 0,
    registros_novos INTEGER DEFAULT 0,
    registros_atualizados INTEGER DEFAULT 0,
    registros_erro INTEGER DEFAULT 0,

    -- Performance
    duracao_segundos DECIMAL(8, 2),

    -- Erro
    erro_mensagem TEXT,
    erro_stack_trace TEXT,

    -- Metadados
    parametros JSONB, -- Parâmetros usados na sincronização
    resultado JSONB, -- Resultado detalhado

    -- Auditoria
    iniciado_em TIMESTAMP NOT NULL DEFAULT NOW(),
    finalizado_em TIMESTAMP,
    iniciado_por UUID REFERENCES usuarios(id), -- NULL se automático

    -- Constraints
    CONSTRAINT cora_sync_logs_tipo_check CHECK (tipo IN ('extrato', 'cobrancas', 'saldo')),
    CONSTRAINT cora_sync_logs_status_check CHECK (status IN ('iniciado', 'concluido', 'erro')),
    CONSTRAINT cora_sync_logs_registros_check CHECK (
        registros_processados >= 0 AND
        registros_novos >= 0 AND
        registros_atualizados >= 0 AND
        registros_erro >= 0
    )
);

-- Índices
CREATE INDEX idx_cora_sync_logs_conta ON financeiro.cora_sync_logs(conta_cora_id);
CREATE INDEX idx_cora_sync_logs_condominio ON financeiro.cora_sync_logs(condominio_id);
CREATE INDEX idx_cora_sync_logs_tipo ON financeiro.cora_sync_logs(tipo);
CREATE INDEX idx_cora_sync_logs_status ON financeiro.cora_sync_logs(status);
CREATE INDEX idx_cora_sync_logs_iniciado_em ON financeiro.cora_sync_logs(iniciado_em DESC);

-- Comentários
COMMENT ON TABLE financeiro.cora_sync_logs IS 'Logs de sincronização de dados com o Banco Cora';
COMMENT ON COLUMN financeiro.cora_sync_logs.tipo IS 'Tipo: extrato, cobrancas ou saldo';

-- ============================================================
-- VIEWS
-- ============================================================

-- View 1: Transações Conciliadas (com detalhes completos)
CREATE OR REPLACE VIEW financeiro.vw_cora_transacoes_conciliadas AS
SELECT
    t.id,
    t.conta_cora_id,
    t.condominio_id,
    t.cora_transaction_id,
    t.data_transacao,
    t.tipo,
    t.valor,
    t.descricao,
    t.categoria,
    t.contrapartida_nome,
    t.contrapartida_documento,
    t.conciliado,
    t.confianca_match,
    t.conciliacao_manual,
    t.conciliado_em,

    -- Dados do boleto (se conciliado)
    b.id AS boleto_id,
    b.nosso_numero AS boleto_nosso_numero,
    b.valor AS boleto_valor,
    b.vencimento AS boleto_vencimento,

    -- Dados do pagamento
    p.id AS pagamento_id,
    p.valor AS pagamento_valor,
    p.data_pagamento,

    -- Dados do lançamento
    l.id AS lancamento_id,
    l.descricao AS lancamento_descricao,
    l.tipo AS lancamento_tipo
FROM financeiro.transacoes_cora t
LEFT JOIN financeiro.boletos b ON t.boleto_id = b.id
LEFT JOIN financeiro.pagamentos p ON t.pagamento_id = p.id
LEFT JOIN financeiro.lancamentos l ON t.lancamento_id = l.id
WHERE t.conciliado = true;

COMMENT ON VIEW financeiro.vw_cora_transacoes_conciliadas IS 'Transações Cora conciliadas com boletos/pagamentos/lançamentos';

-- View 2: Cobranças Pendentes/Vencidas
CREATE OR REPLACE VIEW financeiro.vw_cora_cobrancas_pendentes AS
SELECT
    c.id,
    c.conta_cora_id,
    c.condominio_id,
    c.cora_invoice_id,
    c.tipo,
    c.valor,
    c.data_vencimento,
    c.status,
    c.pagador_nome,
    c.nosso_numero,
    c.codigo_barras,
    c.linha_digitavel,
    c.pix_copia_cola,

    -- Dias de atraso
    CASE
        WHEN c.data_vencimento < CURRENT_DATE THEN CURRENT_DATE - c.data_vencimento
        ELSE 0
    END AS dias_atraso,

    -- Classificação
    CASE
        WHEN c.data_vencimento < CURRENT_DATE THEN 'vencido'
        WHEN c.data_vencimento = CURRENT_DATE THEN 'vence_hoje'
        WHEN c.data_vencimento <= CURRENT_DATE + 7 THEN 'vence_em_7_dias'
        ELSE 'a_vencer'
    END AS classificacao,

    -- Boleto interno
    b.id AS boleto_interno_id,
    b.unidade_id,
    u.numero AS unidade_numero
FROM financeiro.cobrancas_cora c
LEFT JOIN financeiro.boletos b ON c.boleto_id = b.id
LEFT JOIN unidades u ON b.unidade_id = u.id
WHERE c.status IN ('pendente', 'vencido')
ORDER BY c.data_vencimento ASC;

COMMENT ON VIEW financeiro.vw_cora_cobrancas_pendentes IS 'Cobranças pendentes ou vencidas com classificação de urgência';

-- View 3: Webhooks Não Processados
CREATE OR REPLACE VIEW financeiro.vw_cora_webhooks_pendentes AS
SELECT
    id,
    event_type,
    event_id,
    body,
    signature_valid,
    tentativas_processamento,
    erro_mensagem,
    received_at,

    -- Tempo de espera
    EXTRACT(EPOCH FROM (NOW() - received_at)) / 60 AS minutos_aguardando
FROM financeiro.webhooks_cora
WHERE processado = false
  AND signature_valid = true  -- Só processa se assinatura válida
ORDER BY received_at ASC
LIMIT 100;  -- Limita para evitar sobrecarga

COMMENT ON VIEW financeiro.vw_cora_webhooks_pendentes IS 'Webhooks pendentes de processamento (máximo 100)';

-- ============================================================
-- TRIGGERS
-- ============================================================

-- Trigger 1: Prevent UPDATE on webhooks_cora (imutável)
CREATE OR REPLACE FUNCTION financeiro.prevent_webhook_update()
RETURNS TRIGGER AS $$
BEGIN
    -- Permite apenas UPDATE do campo processado e relacionados
    IF (OLD.processado = false AND NEW.processado = true) THEN
        -- Permite marcar como processado
        RETURN NEW;
    ELSE
        RAISE EXCEPTION 'Webhooks são imutáveis. Use INSERT para novos eventos.';
    END IF;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_prevent_webhook_update
BEFORE UPDATE ON financeiro.webhooks_cora
FOR EACH ROW
EXECUTE FUNCTION financeiro.prevent_webhook_update();

COMMENT ON FUNCTION financeiro.prevent_webhook_update() IS 'Impede UPDATE em webhooks (exceto marcar como processado)';

-- Trigger 2: Auto-update updated_at
CREATE OR REPLACE FUNCTION financeiro.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Aplica trigger em todas as tabelas com updated_at
CREATE TRIGGER trg_contas_cora_updated_at
BEFORE UPDATE ON financeiro.contas_cora
FOR EACH ROW
EXECUTE FUNCTION financeiro.update_updated_at_column();

CREATE TRIGGER trg_transacoes_cora_updated_at
BEFORE UPDATE ON financeiro.transacoes_cora
FOR EACH ROW
EXECUTE FUNCTION financeiro.update_updated_at_column();

CREATE TRIGGER trg_cobrancas_cora_updated_at
BEFORE UPDATE ON financeiro.cobrancas_cora
FOR EACH ROW
EXECUTE FUNCTION financeiro.update_updated_at_column();

CREATE TRIGGER trg_cora_tokens_updated_at
BEFORE UPDATE ON financeiro.cora_tokens
FOR EACH ROW
EXECUTE FUNCTION financeiro.update_updated_at_column();

CREATE TRIGGER trg_saldos_cora_updated_at
BEFORE UPDATE ON financeiro.saldos_cora
FOR EACH ROW
EXECUTE FUNCTION financeiro.update_updated_at_column();

-- Trigger 3: Atualizar status de cobrança quando vencer
CREATE OR REPLACE FUNCTION financeiro.auto_update_cobranca_vencida()
RETURNS TRIGGER AS $$
BEGIN
    -- Atualiza cobranças que venceram (executa diariamente via CRON)
    UPDATE financeiro.cobrancas_cora
    SET status = 'vencido'
    WHERE status = 'pendente'
      AND data_vencimento < CURRENT_DATE;

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- GRANTS (Permissões)
-- ============================================================

-- Permissões para role 'conecta_app' (aplicação)
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA financeiro TO conecta_app;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA financeiro TO conecta_app;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA financeiro TO conecta_app;

-- Webhooks: Apenas INSERT e SELECT (não permite UPDATE direto, só via trigger)
REVOKE UPDATE ON financeiro.webhooks_cora FROM conecta_app;
GRANT UPDATE (processado, processado_em, resultado, erro_mensagem, tentativas_processamento)
    ON financeiro.webhooks_cora TO conecta_app;

-- ============================================================
-- DADOS INICIAIS (se necessário)
-- ============================================================

-- Nenhum dado inicial necessário (será criado pela aplicação)

-- ============================================================
-- FIM DA MIGRATION
-- ============================================================

-- Verifica estrutura criada
DO $$
DECLARE
    table_count INTEGER;
    view_count INTEGER;
    trigger_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO table_count
    FROM information_schema.tables
    WHERE table_schema = 'financeiro'
      AND table_name LIKE '%cora%';

    SELECT COUNT(*) INTO view_count
    FROM information_schema.views
    WHERE table_schema = 'financeiro'
      AND table_name LIKE 'vw_cora%';

    SELECT COUNT(*) INTO trigger_count
    FROM information_schema.triggers
    WHERE trigger_schema = 'financeiro'
      AND trigger_name LIKE '%cora%';

    RAISE NOTICE '✅ Migration concluída com sucesso!';
    RAISE NOTICE '   Tabelas criadas: %', table_count;
    RAISE NOTICE '   Views criadas: %', view_count;
    RAISE NOTICE '   Triggers criados: %', trigger_count;
END $$;
