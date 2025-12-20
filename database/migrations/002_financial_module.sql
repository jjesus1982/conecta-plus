-- ============================================================================
-- CONECTA PLUS - MÓDULO FINANCEIRO COMPLETO
-- Migração: 002_financial_module.sql
-- Data: 2024-12-20
-- Descrição: Schema completo para Agente Financeiro IA
-- ============================================================================

-- Garantir que estamos no schema correto
SET search_path TO conecta, public;

-- ============================================================================
-- 1. EXTENSÕES NECESSÁRIAS
-- ============================================================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- 2. TIPOS ENUMERADOS
-- ============================================================================

-- Status de boleto
DO $$ BEGIN
    CREATE TYPE status_boleto AS ENUM (
        'rascunho', 'emitido', 'registrado', 'pendente', 'pago',
        'pago_parcial', 'vencido', 'cancelado', 'protestado', 'baixado'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Tipo de lançamento
DO $$ BEGIN
    CREATE TYPE tipo_lancamento AS ENUM ('receita', 'despesa', 'transferencia');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Status de lançamento
DO $$ BEGIN
    CREATE TYPE status_lancamento AS ENUM (
        'pendente', 'confirmado', 'conciliado', 'cancelado'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Tipo de conta
DO $$ BEGIN
    CREATE TYPE tipo_conta AS ENUM (
        'conta_corrente', 'poupanca', 'investimento', 'caixa'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Status de conciliação
DO $$ BEGIN
    CREATE TYPE status_conciliacao AS ENUM (
        'pendente', 'conciliado_auto', 'conciliado_manual',
        'divergente', 'ignorado'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Status de acordo
DO $$ BEGIN
    CREATE TYPE status_acordo AS ENUM (
        'proposta', 'ativo', 'quitado', 'quebrado', 'cancelado'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Canal de cobrança
DO $$ BEGIN
    CREATE TYPE canal_cobranca AS ENUM (
        'email', 'sms', 'whatsapp', 'push', 'telefone', 'carta'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Status de cobrança
DO $$ BEGIN
    CREATE TYPE status_cobranca AS ENUM (
        'agendada', 'enviada', 'entregue', 'lida', 'respondida',
        'falha', 'cancelada'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- ============================================================================
-- 3. TABELAS DE CONFIGURAÇÃO
-- ============================================================================

-- Categorias financeiras
CREATE TABLE IF NOT EXISTS categorias_financeiras (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    condominio_id UUID REFERENCES conecta.condominios(id),
    codigo VARCHAR(20) NOT NULL,
    nome VARCHAR(100) NOT NULL,
    tipo tipo_lancamento NOT NULL,
    categoria_pai_id UUID REFERENCES categorias_financeiras(id),
    cor VARCHAR(7) DEFAULT '#6B7280',
    icone VARCHAR(50),
    ativo BOOLEAN DEFAULT true,
    ordem INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(condominio_id, codigo)
);

-- Contas bancárias
CREATE TABLE IF NOT EXISTS contas_bancarias (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    condominio_id UUID NOT NULL REFERENCES conecta.condominios(id),
    banco_codigo VARCHAR(10) NOT NULL,
    banco_nome VARCHAR(100) NOT NULL,
    agencia VARCHAR(10) NOT NULL,
    agencia_digito VARCHAR(2),
    conta VARCHAR(20) NOT NULL,
    conta_digito VARCHAR(2),
    tipo tipo_conta DEFAULT 'conta_corrente',
    titular VARCHAR(200),
    documento VARCHAR(20),
    saldo_inicial DECIMAL(15,2) DEFAULT 0,
    saldo_atual DECIMAL(15,2) DEFAULT 0,
    data_saldo TIMESTAMPTZ DEFAULT NOW(),
    ativo BOOLEAN DEFAULT true,
    principal BOOLEAN DEFAULT false,
    -- Integração bancária
    integracao_ativa BOOLEAN DEFAULT false,
    integracao_tipo VARCHAR(50), -- 'cora', 'inter', 'bradesco', etc
    integracao_ambiente VARCHAR(20) DEFAULT 'sandbox', -- 'sandbox', 'producao'
    integracao_client_id TEXT,
    integracao_client_secret_encrypted TEXT,
    integracao_certificado_encrypted TEXT,
    integracao_webhook_url TEXT,
    integracao_ultimo_sync TIMESTAMPTZ,
    integracao_config JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Configurações do módulo financeiro
CREATE TABLE IF NOT EXISTS config_financeiro (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    condominio_id UUID NOT NULL REFERENCES conecta.condominios(id) UNIQUE,
    -- Taxas e multas
    taxa_juros_mensal DECIMAL(5,4) DEFAULT 0.01, -- 1% ao mês
    taxa_multa DECIMAL(5,4) DEFAULT 0.02, -- 2%
    dias_tolerancia INTEGER DEFAULT 0,
    -- Descontos
    desconto_pontualidade DECIMAL(5,4) DEFAULT 0,
    dias_desconto INTEGER DEFAULT 5,
    -- Cobrança automática
    cobranca_automatica BOOLEAN DEFAULT true,
    dias_antes_vencimento_lembrete INTEGER[] DEFAULT ARRAY[7, 3, 1],
    dias_apos_vencimento_cobranca INTEGER[] DEFAULT ARRAY[1, 3, 7, 15, 30],
    canais_cobranca canal_cobranca[] DEFAULT ARRAY['email'::canal_cobranca, 'whatsapp'::canal_cobranca],
    -- Integração
    banco_principal_id UUID REFERENCES contas_bancarias(id),
    gerar_pix BOOLEAN DEFAULT true,
    gerar_boleto BOOLEAN DEFAULT true,
    -- IA
    ia_previsao_ativa BOOLEAN DEFAULT true,
    ia_cobranca_ativa BOOLEAN DEFAULT true,
    ia_negociacao_ativa BOOLEAN DEFAULT false,
    -- Outros
    dia_vencimento_padrao INTEGER DEFAULT 10,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- 4. EXPANDIR TABELA DE BOLETOS
-- ============================================================================

-- Adicionar novas colunas à tabela de boletos existente
DO $$
BEGIN
    -- Tipo do boleto
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_schema = 'conecta' AND table_name = 'boletos' AND column_name = 'tipo') THEN
        ALTER TABLE conecta.boletos ADD COLUMN tipo VARCHAR(50) DEFAULT 'condominio';
    END IF;

    -- Descrição
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_schema = 'conecta' AND table_name = 'boletos' AND column_name = 'descricao') THEN
        ALTER TABLE conecta.boletos ADD COLUMN descricao TEXT;
    END IF;

    -- Juros e multa
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_schema = 'conecta' AND table_name = 'boletos' AND column_name = 'valor_juros') THEN
        ALTER TABLE conecta.boletos ADD COLUMN valor_juros DECIMAL(10,2) DEFAULT 0;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_schema = 'conecta' AND table_name = 'boletos' AND column_name = 'valor_multa') THEN
        ALTER TABLE conecta.boletos ADD COLUMN valor_multa DECIMAL(10,2) DEFAULT 0;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_schema = 'conecta' AND table_name = 'boletos' AND column_name = 'valor_desconto') THEN
        ALTER TABLE conecta.boletos ADD COLUMN valor_desconto DECIMAL(10,2) DEFAULT 0;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_schema = 'conecta' AND table_name = 'boletos' AND column_name = 'valor_total') THEN
        ALTER TABLE conecta.boletos ADD COLUMN valor_total DECIMAL(10,2);
    END IF;

    -- PIX
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_schema = 'conecta' AND table_name = 'boletos' AND column_name = 'pix_txid') THEN
        ALTER TABLE conecta.boletos ADD COLUMN pix_txid VARCHAR(100);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_schema = 'conecta' AND table_name = 'boletos' AND column_name = 'pix_qrcode') THEN
        ALTER TABLE conecta.boletos ADD COLUMN pix_qrcode TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_schema = 'conecta' AND table_name = 'boletos' AND column_name = 'pix_copia_cola') THEN
        ALTER TABLE conecta.boletos ADD COLUMN pix_copia_cola TEXT;
    END IF;

    -- Nosso número (identificador bancário)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_schema = 'conecta' AND table_name = 'boletos' AND column_name = 'nosso_numero') THEN
        ALTER TABLE conecta.boletos ADD COLUMN nosso_numero VARCHAR(50);
    END IF;

    -- Integração bancária
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_schema = 'conecta' AND table_name = 'boletos' AND column_name = 'banco_id') THEN
        ALTER TABLE conecta.boletos ADD COLUMN banco_id UUID REFERENCES contas_bancarias(id);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_schema = 'conecta' AND table_name = 'boletos' AND column_name = 'banco_boleto_id') THEN
        ALTER TABLE conecta.boletos ADD COLUMN banco_boleto_id VARCHAR(100);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_schema = 'conecta' AND table_name = 'boletos' AND column_name = 'banco_response') THEN
        ALTER TABLE conecta.boletos ADD COLUMN banco_response JSONB;
    END IF;

    -- Acordo relacionado
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_schema = 'conecta' AND table_name = 'boletos' AND column_name = 'acordo_id') THEN
        ALTER TABLE conecta.boletos ADD COLUMN acordo_id UUID;
    END IF;

    -- Parcela
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_schema = 'conecta' AND table_name = 'boletos' AND column_name = 'parcela') THEN
        ALTER TABLE conecta.boletos ADD COLUMN parcela INTEGER;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_schema = 'conecta' AND table_name = 'boletos' AND column_name = 'total_parcelas') THEN
        ALTER TABLE conecta.boletos ADD COLUMN total_parcelas INTEGER;
    END IF;

    -- Competência
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_schema = 'conecta' AND table_name = 'boletos' AND column_name = 'competencia') THEN
        ALTER TABLE conecta.boletos ADD COLUMN competencia DATE;
    END IF;

    -- Forma de pagamento
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_schema = 'conecta' AND table_name = 'boletos' AND column_name = 'forma_pagamento') THEN
        ALTER TABLE conecta.boletos ADD COLUMN forma_pagamento VARCHAR(50);
    END IF;

    -- Dados para conciliação
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_schema = 'conecta' AND table_name = 'boletos' AND column_name = 'conciliacao_id') THEN
        ALTER TABLE conecta.boletos ADD COLUMN conciliacao_id UUID;
    END IF;

END $$;

-- ============================================================================
-- 5. TABELA DE PAGAMENTOS
-- ============================================================================

CREATE TABLE IF NOT EXISTS pagamentos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    condominio_id UUID NOT NULL REFERENCES conecta.condominios(id),
    boleto_id UUID REFERENCES conecta.boletos(id),
    unidade_id UUID REFERENCES conecta.unidades(id),
    conta_bancaria_id UUID REFERENCES contas_bancarias(id),
    -- Valores
    valor_original DECIMAL(15,2) NOT NULL,
    valor_juros DECIMAL(15,2) DEFAULT 0,
    valor_multa DECIMAL(15,2) DEFAULT 0,
    valor_desconto DECIMAL(15,2) DEFAULT 0,
    valor_pago DECIMAL(15,2) NOT NULL,
    -- Datas
    data_pagamento TIMESTAMPTZ NOT NULL,
    data_credito TIMESTAMPTZ,
    data_vencimento_original DATE,
    -- Forma de pagamento
    forma_pagamento VARCHAR(50) NOT NULL, -- 'pix', 'boleto', 'ted', 'debito', 'dinheiro', 'cartao'
    -- Identificadores bancários
    autenticacao VARCHAR(100),
    txid VARCHAR(100),
    nosso_numero VARCHAR(50),
    -- Comprovante
    comprovante_url TEXT,
    comprovante_base64 TEXT,
    -- Origem
    origem VARCHAR(50) DEFAULT 'manual', -- 'manual', 'webhook', 'conciliacao', 'importacao'
    -- Dados extras
    observacao TEXT,
    metadata JSONB DEFAULT '{}',
    -- Auditoria
    registrado_por UUID REFERENCES conecta.usuarios(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índices para pagamentos
CREATE INDEX IF NOT EXISTS idx_pagamentos_boleto ON pagamentos(boleto_id);
CREATE INDEX IF NOT EXISTS idx_pagamentos_unidade ON pagamentos(unidade_id);
CREATE INDEX IF NOT EXISTS idx_pagamentos_data ON pagamentos(data_pagamento);
CREATE INDEX IF NOT EXISTS idx_pagamentos_condominio ON pagamentos(condominio_id);

-- ============================================================================
-- 6. LANÇAMENTOS FINANCEIROS (Receitas e Despesas)
-- ============================================================================

CREATE TABLE IF NOT EXISTS lancamentos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    condominio_id UUID NOT NULL REFERENCES conecta.condominios(id),
    conta_bancaria_id UUID REFERENCES contas_bancarias(id),
    categoria_id UUID REFERENCES categorias_financeiras(id),
    unidade_id UUID REFERENCES conecta.unidades(id),
    -- Tipo e valores
    tipo tipo_lancamento NOT NULL,
    valor DECIMAL(15,2) NOT NULL,
    -- Datas
    data_lancamento DATE NOT NULL,
    data_vencimento DATE,
    data_pagamento DATE,
    data_competencia DATE,
    -- Descrição
    descricao TEXT NOT NULL,
    observacao TEXT,
    -- Fornecedor/Beneficiário
    fornecedor_nome VARCHAR(200),
    fornecedor_documento VARCHAR(20),
    -- Documento fiscal
    documento_tipo VARCHAR(50), -- 'nf', 'nfse', 'recibo', 'contrato', 'outros'
    documento_numero VARCHAR(50),
    documento_url TEXT,
    -- Rateio
    rateio BOOLEAN DEFAULT false,
    rateio_config JSONB, -- Configuração de rateio por unidade
    -- Status
    status status_lancamento DEFAULT 'pendente',
    -- Recorrência
    recorrente BOOLEAN DEFAULT false,
    recorrencia_config JSONB, -- {'tipo': 'mensal', 'dia': 10, 'fim': '2025-12-31'}
    lancamento_pai_id UUID REFERENCES lancamentos(id),
    -- Conciliação
    conciliado BOOLEAN DEFAULT false,
    conciliacao_id UUID,
    -- Aprovação
    aprovado BOOLEAN DEFAULT false,
    aprovado_por UUID REFERENCES conecta.usuarios(id),
    aprovado_em TIMESTAMPTZ,
    -- Auditoria
    criado_por UUID REFERENCES conecta.usuarios(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índices para lançamentos
CREATE INDEX IF NOT EXISTS idx_lancamentos_condominio ON lancamentos(condominio_id);
CREATE INDEX IF NOT EXISTS idx_lancamentos_data ON lancamentos(data_lancamento);
CREATE INDEX IF NOT EXISTS idx_lancamentos_categoria ON lancamentos(categoria_id);
CREATE INDEX IF NOT EXISTS idx_lancamentos_tipo ON lancamentos(tipo);
CREATE INDEX IF NOT EXISTS idx_lancamentos_status ON lancamentos(status);

-- ============================================================================
-- 7. CONCILIAÇÃO BANCÁRIA
-- ============================================================================

-- Importações de extratos
CREATE TABLE IF NOT EXISTS extrato_importacoes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    condominio_id UUID NOT NULL REFERENCES conecta.condominios(id),
    conta_bancaria_id UUID NOT NULL REFERENCES contas_bancarias(id),
    -- Arquivo
    arquivo_nome VARCHAR(255),
    arquivo_tipo VARCHAR(20), -- 'ofx', 'cnab240', 'cnab400', 'csv', 'pdf'
    arquivo_url TEXT,
    arquivo_hash VARCHAR(64),
    -- Período
    data_inicio DATE,
    data_fim DATE,
    -- Estatísticas
    total_transacoes INTEGER DEFAULT 0,
    total_conciliadas INTEGER DEFAULT 0,
    total_pendentes INTEGER DEFAULT 0,
    total_divergentes INTEGER DEFAULT 0,
    -- Saldos
    saldo_inicial DECIMAL(15,2),
    saldo_final DECIMAL(15,2),
    -- Status
    status VARCHAR(50) DEFAULT 'processando', -- 'processando', 'concluido', 'erro'
    erro_mensagem TEXT,
    -- Auditoria
    importado_por UUID REFERENCES conecta.usuarios(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Transações do extrato bancário
CREATE TABLE IF NOT EXISTS extrato_transacoes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    importacao_id UUID NOT NULL REFERENCES extrato_importacoes(id) ON DELETE CASCADE,
    condominio_id UUID NOT NULL REFERENCES conecta.condominios(id),
    conta_bancaria_id UUID NOT NULL REFERENCES contas_bancarias(id),
    -- Dados da transação
    data_transacao DATE NOT NULL,
    data_balancete DATE,
    tipo VARCHAR(10) NOT NULL, -- 'C' credito, 'D' debito
    valor DECIMAL(15,2) NOT NULL,
    descricao TEXT,
    -- Identificadores bancários
    numero_documento VARCHAR(50),
    codigo_transacao VARCHAR(20),
    -- Conciliação
    status status_conciliacao DEFAULT 'pendente',
    confianca_match DECIMAL(5,2), -- 0 a 100
    -- Matches
    boleto_id UUID REFERENCES conecta.boletos(id),
    lancamento_id UUID REFERENCES lancamentos(id),
    pagamento_id UUID REFERENCES pagamentos(id),
    -- Match manual
    match_manual BOOLEAN DEFAULT false,
    match_por UUID REFERENCES conecta.usuarios(id),
    match_em TIMESTAMPTZ,
    match_observacao TEXT,
    -- Sugestões da IA
    sugestoes_match JSONB, -- [{'tipo': 'boleto', 'id': '...', 'confianca': 95}]
    -- Dados originais
    dados_originais JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índices para extrato
CREATE INDEX IF NOT EXISTS idx_extrato_trans_importacao ON extrato_transacoes(importacao_id);
CREATE INDEX IF NOT EXISTS idx_extrato_trans_data ON extrato_transacoes(data_transacao);
CREATE INDEX IF NOT EXISTS idx_extrato_trans_status ON extrato_transacoes(status);
CREATE INDEX IF NOT EXISTS idx_extrato_trans_condominio ON extrato_transacoes(condominio_id);

-- ============================================================================
-- 8. ACORDOS DE PAGAMENTO
-- ============================================================================

CREATE TABLE IF NOT EXISTS acordos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    condominio_id UUID NOT NULL REFERENCES conecta.condominios(id),
    unidade_id UUID NOT NULL REFERENCES conecta.unidades(id),
    -- Dívida original
    boletos_originais UUID[], -- IDs dos boletos incluídos
    valor_original DECIMAL(15,2) NOT NULL,
    valor_juros DECIMAL(15,2) DEFAULT 0,
    valor_multa DECIMAL(15,2) DEFAULT 0,
    valor_desconto DECIMAL(15,2) DEFAULT 0,
    valor_total DECIMAL(15,2) NOT NULL,
    -- Parcelamento
    entrada DECIMAL(15,2) DEFAULT 0,
    parcelas INTEGER NOT NULL,
    valor_parcela DECIMAL(15,2) NOT NULL,
    dia_vencimento INTEGER NOT NULL,
    primeira_parcela DATE NOT NULL,
    -- Status
    status status_acordo DEFAULT 'proposta',
    -- Pagamentos
    parcelas_pagas INTEGER DEFAULT 0,
    valor_pago DECIMAL(15,2) DEFAULT 0,
    ultima_parcela_paga DATE,
    -- Quebra de acordo
    quebra_motivo TEXT,
    quebra_data TIMESTAMPTZ,
    -- Contrato
    contrato_url TEXT,
    contrato_assinado BOOLEAN DEFAULT false,
    contrato_assinado_em TIMESTAMPTZ,
    -- Negociação
    negociado_por VARCHAR(50), -- 'ia', 'atendente', 'sindico'
    canal_negociacao VARCHAR(50),
    historico_negociacao JSONB DEFAULT '[]',
    -- Auditoria
    criado_por UUID REFERENCES conecta.usuarios(id),
    aprovado_por UUID REFERENCES conecta.usuarios(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índices para acordos
CREATE INDEX IF NOT EXISTS idx_acordos_unidade ON acordos(unidade_id);
CREATE INDEX IF NOT EXISTS idx_acordos_status ON acordos(status);
CREATE INDEX IF NOT EXISTS idx_acordos_condominio ON acordos(condominio_id);

-- ============================================================================
-- 9. HISTÓRICO DE COBRANÇA
-- ============================================================================

CREATE TABLE IF NOT EXISTS cobrancas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    condominio_id UUID NOT NULL REFERENCES conecta.condominios(id),
    unidade_id UUID NOT NULL REFERENCES conecta.unidades(id),
    boleto_id UUID REFERENCES conecta.boletos(id),
    acordo_id UUID REFERENCES acordos(id),
    -- Canal e status
    canal canal_cobranca NOT NULL,
    status status_cobranca DEFAULT 'agendada',
    -- Destinatário
    destinatario_nome VARCHAR(200),
    destinatario_contato VARCHAR(200), -- email, telefone, etc
    -- Conteúdo
    template_id VARCHAR(100),
    assunto TEXT,
    mensagem TEXT,
    mensagem_html TEXT,
    -- Datas
    agendado_para TIMESTAMPTZ,
    enviado_em TIMESTAMPTZ,
    entregue_em TIMESTAMPTZ,
    lido_em TIMESTAMPTZ,
    respondido_em TIMESTAMPTZ,
    -- Resposta
    resposta TEXT,
    sentimento_resposta VARCHAR(20), -- 'positivo', 'neutro', 'negativo'
    intencao_pagamento DECIMAL(5,2), -- 0-100 probabilidade
    -- Erro
    erro_codigo VARCHAR(50),
    erro_mensagem TEXT,
    tentativas INTEGER DEFAULT 0,
    -- IDs externos
    provedor VARCHAR(50), -- 'evolution', 'sendgrid', 'twilio'
    provedor_id VARCHAR(200),
    -- Metadata
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índices para cobrança
CREATE INDEX IF NOT EXISTS idx_cobrancas_unidade ON cobrancas(unidade_id);
CREATE INDEX IF NOT EXISTS idx_cobrancas_boleto ON cobrancas(boleto_id);
CREATE INDEX IF NOT EXISTS idx_cobrancas_status ON cobrancas(status);
CREATE INDEX IF NOT EXISTS idx_cobrancas_agendado ON cobrancas(agendado_para);

-- ============================================================================
-- 10. PREVISÕES E ANÁLISES DE IA
-- ============================================================================

CREATE TABLE IF NOT EXISTS ia_previsoes_inadimplencia (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    condominio_id UUID NOT NULL REFERENCES conecta.condominios(id),
    unidade_id UUID NOT NULL REFERENCES conecta.unidades(id),
    boleto_id UUID REFERENCES conecta.boletos(id),
    -- Previsão
    probabilidade_atraso DECIMAL(5,4) NOT NULL, -- 0.0000 a 1.0000
    dias_atraso_previsto INTEGER,
    valor_em_risco DECIMAL(15,2),
    -- Modelo
    modelo_versao VARCHAR(50),
    modelo_acuracia DECIMAL(5,4),
    -- Features usadas
    features JSONB,
    -- Ação recomendada
    acao_recomendada VARCHAR(100),
    acao_executada BOOLEAN DEFAULT false,
    acao_resultado TEXT,
    -- Resultado real
    resultado_real VARCHAR(50), -- 'em_dia', 'atrasou', 'pendente'
    dias_atraso_real INTEGER,
    -- Timestamps
    data_previsao TIMESTAMPTZ DEFAULT NOW(),
    data_vencimento DATE,
    data_resultado TIMESTAMPTZ
);

-- Índices para previsões
CREATE INDEX IF NOT EXISTS idx_previsoes_unidade ON ia_previsoes_inadimplencia(unidade_id);
CREATE INDEX IF NOT EXISTS idx_previsoes_boleto ON ia_previsoes_inadimplencia(boleto_id);
CREATE INDEX IF NOT EXISTS idx_previsoes_prob ON ia_previsoes_inadimplencia(probabilidade_atraso);

-- Score de inadimplência por unidade
CREATE TABLE IF NOT EXISTS ia_scores_unidade (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    condominio_id UUID NOT NULL REFERENCES conecta.condominios(id),
    unidade_id UUID NOT NULL REFERENCES conecta.unidades(id),
    -- Score
    score INTEGER NOT NULL CHECK (score >= 0 AND score <= 1000),
    classificacao VARCHAR(20), -- 'excelente', 'bom', 'regular', 'ruim', 'critico'
    -- Componentes do score
    componentes JSONB, -- Detalhamento do cálculo
    -- Histórico
    score_anterior INTEGER,
    variacao INTEGER,
    -- Recomendações
    recomendacoes JSONB DEFAULT '[]',
    -- Timestamps
    calculado_em TIMESTAMPTZ DEFAULT NOW(),
    valido_ate TIMESTAMPTZ,
    UNIQUE(unidade_id) -- Apenas um score ativo por unidade
);

-- ============================================================================
-- 11. WEBHOOKS E INTEGRAÇÕES
-- ============================================================================

CREATE TABLE IF NOT EXISTS webhooks_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    condominio_id UUID REFERENCES conecta.condominios(id),
    -- Origem
    origem VARCHAR(50) NOT NULL, -- 'cora', 'inter', 'pix', etc
    tipo VARCHAR(100), -- 'payment.confirmed', 'boleto.paid', etc
    -- Request
    url TEXT,
    method VARCHAR(10),
    headers JSONB,
    body JSONB,
    -- Processamento
    processado BOOLEAN DEFAULT false,
    processado_em TIMESTAMPTZ,
    resultado VARCHAR(50), -- 'sucesso', 'erro', 'ignorado'
    erro_mensagem TEXT,
    -- Entidades afetadas
    boleto_id UUID REFERENCES conecta.boletos(id),
    pagamento_id UUID REFERENCES pagamentos(id),
    -- Timestamps
    recebido_em TIMESTAMPTZ DEFAULT NOW()
);

-- Índices para webhooks
CREATE INDEX IF NOT EXISTS idx_webhooks_origem ON webhooks_log(origem);
CREATE INDEX IF NOT EXISTS idx_webhooks_processado ON webhooks_log(processado);
CREATE INDEX IF NOT EXISTS idx_webhooks_data ON webhooks_log(recebido_em);

-- ============================================================================
-- 12. RELATÓRIOS E CACHE
-- ============================================================================

CREATE TABLE IF NOT EXISTS relatorios_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    condominio_id UUID NOT NULL REFERENCES conecta.condominios(id),
    tipo VARCHAR(100) NOT NULL, -- 'resumo_mensal', 'inadimplencia', 'fluxo_caixa'
    periodo_inicio DATE,
    periodo_fim DATE,
    parametros JSONB DEFAULT '{}',
    dados JSONB NOT NULL,
    gerado_em TIMESTAMPTZ DEFAULT NOW(),
    expira_em TIMESTAMPTZ,
    UNIQUE(condominio_id, tipo, periodo_inicio, periodo_fim, parametros)
);

-- ============================================================================
-- 13. TRIGGERS E FUNCTIONS
-- ============================================================================

-- Função para atualizar updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Aplicar triggers de updated_at
DO $$
DECLARE
    t text;
BEGIN
    FOR t IN
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'conecta'
        AND table_name IN (
            'categorias_financeiras', 'contas_bancarias', 'config_financeiro',
            'pagamentos', 'lancamentos', 'extrato_importacoes', 'extrato_transacoes',
            'acordos', 'cobrancas'
        )
    LOOP
        EXECUTE format('
            DROP TRIGGER IF EXISTS trigger_update_%I ON conecta.%I;
            CREATE TRIGGER trigger_update_%I
            BEFORE UPDATE ON conecta.%I
            FOR EACH ROW EXECUTE FUNCTION update_updated_at();
        ', t, t, t, t);
    END LOOP;
END $$;

-- Função para calcular valor total do boleto
CREATE OR REPLACE FUNCTION calcular_valor_boleto()
RETURNS TRIGGER AS $$
BEGIN
    NEW.valor_total := NEW.valor + COALESCE(NEW.valor_juros, 0) + COALESCE(NEW.valor_multa, 0) - COALESCE(NEW.valor_desconto, 0);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger para valor total do boleto
DROP TRIGGER IF EXISTS trigger_calc_valor_boleto ON conecta.boletos;
CREATE TRIGGER trigger_calc_valor_boleto
BEFORE INSERT OR UPDATE OF valor, valor_juros, valor_multa, valor_desconto ON conecta.boletos
FOR EACH ROW EXECUTE FUNCTION calcular_valor_boleto();

-- Função para atualizar saldo da conta bancária
CREATE OR REPLACE FUNCTION atualizar_saldo_conta()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' AND NEW.status = 'confirmado' THEN
        IF NEW.tipo = 'receita' THEN
            UPDATE contas_bancarias SET saldo_atual = saldo_atual + NEW.valor WHERE id = NEW.conta_bancaria_id;
        ELSIF NEW.tipo = 'despesa' THEN
            UPDATE contas_bancarias SET saldo_atual = saldo_atual - NEW.valor WHERE id = NEW.conta_bancaria_id;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 14. DADOS INICIAIS - CATEGORIAS PADRÃO
-- ============================================================================

INSERT INTO categorias_financeiras (codigo, nome, tipo, cor, icone, ordem) VALUES
-- Receitas
('REC001', 'Taxa de Condomínio', 'receita', '#10B981', 'home', 1),
('REC002', 'Taxa Extra', 'receita', '#3B82F6', 'plus-circle', 2),
('REC003', 'Fundo de Reserva', 'receita', '#8B5CF6', 'shield', 3),
('REC004', 'Fundo de Obras', 'receita', '#F59E0B', 'tool', 4),
('REC005', 'Multa de Atraso', 'receita', '#EF4444', 'alert-circle', 5),
('REC006', 'Juros de Atraso', 'receita', '#EF4444', 'percent', 6),
('REC007', 'Aluguel Área Comum', 'receita', '#06B6D4', 'key', 7),
('REC008', 'Taxa de Mudança', 'receita', '#84CC16', 'truck', 8),
('REC009', 'Multa Regimento', 'receita', '#F97316', 'file-text', 9),
('REC010', 'Rendimentos Aplicação', 'receita', '#22C55E', 'trending-up', 10),
('REC011', 'Recuperação Judicial', 'receita', '#6366F1', 'gavel', 11),
('REC012', 'Outras Receitas', 'receita', '#6B7280', 'dollar-sign', 99),
-- Despesas
('DES001', 'Folha de Pagamento', 'despesa', '#EF4444', 'users', 1),
('DES002', 'Encargos Sociais (INSS/FGTS)', 'despesa', '#DC2626', 'file-text', 2),
('DES003', 'Energia Elétrica', 'despesa', '#F59E0B', 'zap', 3),
('DES004', 'Água e Esgoto', 'despesa', '#3B82F6', 'droplet', 4),
('DES005', 'Gás', 'despesa', '#F97316', 'flame', 5),
('DES006', 'Manutenção Predial', 'despesa', '#8B5CF6', 'wrench', 6),
('DES007', 'Limpeza e Conservação', 'despesa', '#06B6D4', 'sparkles', 7),
('DES008', 'Segurança/Portaria', 'despesa', '#1F2937', 'shield', 8),
('DES009', 'Elevadores', 'despesa', '#4B5563', 'arrow-up', 9),
('DES010', 'Jardinagem', 'despesa', '#22C55E', 'leaf', 10),
('DES011', 'Piscina', 'despesa', '#0EA5E9', 'waves', 11),
('DES012', 'Seguro Predial', 'despesa', '#7C3AED', 'shield-check', 12),
('DES013', 'Taxas Bancárias', 'despesa', '#6B7280', 'credit-card', 13),
('DES014', 'Honorários Síndico', 'despesa', '#1E40AF', 'user-check', 14),
('DES015', 'Honorários Administradora', 'despesa', '#1E3A8A', 'building', 15),
('DES016', 'Assessoria Jurídica', 'despesa', '#4338CA', 'briefcase', 16),
('DES017', 'Assessoria Contábil', 'despesa', '#5B21B6', 'calculator', 17),
('DES018', 'Material de Limpeza', 'despesa', '#0891B2', 'package', 18),
('DES019', 'Material de Escritório', 'despesa', '#64748B', 'file', 19),
('DES020', 'Internet/Telefone', 'despesa', '#0284C7', 'wifi', 20),
('DES021', 'Dedetização', 'despesa', '#84CC16', 'bug', 21),
('DES022', 'Obras e Reformas', 'despesa', '#EA580C', 'hard-hat', 22),
('DES023', 'Equipamentos', 'despesa', '#0F766E', 'cpu', 23),
('DES024', 'Outras Despesas', 'despesa', '#6B7280', 'more-horizontal', 99)
ON CONFLICT DO NOTHING;

-- ============================================================================
-- 15. GRANTS E PERMISSÕES
-- ============================================================================

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA conecta TO conecta;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA conecta TO conecta;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA conecta TO conecta;

-- ============================================================================
-- MIGRAÇÃO CONCLUÍDA
-- ============================================================================

SELECT 'Migração 002_financial_module.sql executada com sucesso!' as status;
