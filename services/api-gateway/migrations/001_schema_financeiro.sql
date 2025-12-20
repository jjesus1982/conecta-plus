-- =============================================================================
-- CONECTA PLUS - Schema do Módulo Financeiro
-- Migration: 001_schema_financeiro.sql
-- Data: 2024-12
-- =============================================================================

-- Cria schema se não existir
CREATE SCHEMA IF NOT EXISTS financeiro;

-- =============================================================================
-- TABELAS PRINCIPAIS
-- =============================================================================

-- Condominios
CREATE TABLE IF NOT EXISTS financeiro.condominios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome VARCHAR(255) NOT NULL,
    cnpj VARCHAR(18) UNIQUE,
    endereco TEXT,
    cidade VARCHAR(100),
    estado CHAR(2),
    cep VARCHAR(10),
    telefone VARCHAR(20),
    email VARCHAR(255),
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Unidades (apartamentos, casas, etc.)
CREATE TABLE IF NOT EXISTS financeiro.unidades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    condominio_id UUID REFERENCES financeiro.condominios(id) ON DELETE CASCADE,
    bloco VARCHAR(10),
    numero VARCHAR(20) NOT NULL,
    tipo VARCHAR(50), -- apartamento, casa, loja, garagem
    area_m2 DECIMAL(10,2),
    fracao_ideal DECIMAL(10,6),
    proprietario_nome VARCHAR(255),
    proprietario_cpf VARCHAR(14),
    proprietario_email VARCHAR(255),
    proprietario_telefone VARCHAR(20),
    morador_nome VARCHAR(255),
    morador_cpf VARCHAR(14),
    morador_email VARCHAR(255),
    morador_telefone VARCHAR(20),
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Categorias de lançamento
CREATE TABLE IF NOT EXISTS financeiro.categorias (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome VARCHAR(100) NOT NULL,
    tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('receita', 'despesa')),
    descricao TEXT,
    cor VARCHAR(7), -- hex color
    icone VARCHAR(50),
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Boletos
CREATE TABLE IF NOT EXISTS financeiro.boletos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    condominio_id UUID REFERENCES financeiro.condominios(id),
    unidade_id UUID REFERENCES financeiro.unidades(id),
    categoria_id UUID REFERENCES financeiro.categorias(id),

    -- Dados do boleto
    numero VARCHAR(50) UNIQUE,
    nosso_numero VARCHAR(50),
    linha_digitavel VARCHAR(60),
    codigo_barras VARCHAR(50),

    -- Valores
    valor DECIMAL(12,2) NOT NULL,
    valor_desconto DECIMAL(12,2) DEFAULT 0,
    valor_juros DECIMAL(12,2) DEFAULT 0,
    valor_multa DECIMAL(12,2) DEFAULT 0,
    valor_pago DECIMAL(12,2),

    -- Datas
    vencimento DATE NOT NULL,
    data_emissao DATE DEFAULT CURRENT_DATE,
    data_pagamento DATE,
    data_credito DATE,

    -- Status
    status VARCHAR(20) DEFAULT 'pendente' CHECK (status IN ('pendente', 'pago', 'vencido', 'cancelado', 'protestado')),

    -- Pagador
    pagador_nome VARCHAR(255),
    pagador_cpf_cnpj VARCHAR(18),
    pagador_email VARCHAR(255),

    -- Descrição
    descricao TEXT,
    referencia VARCHAR(20), -- MM/YYYY

    -- PIX
    pix_txid VARCHAR(100),
    pix_qrcode TEXT,

    -- Metadados
    metadata JSONB,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Pagamentos
CREATE TABLE IF NOT EXISTS financeiro.pagamentos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    boleto_id UUID REFERENCES financeiro.boletos(id),
    unidade_id UUID REFERENCES financeiro.unidades(id),

    valor DECIMAL(12,2) NOT NULL,
    data_pagamento TIMESTAMP WITH TIME ZONE NOT NULL,
    data_credito TIMESTAMP WITH TIME ZONE,

    forma_pagamento VARCHAR(30) CHECK (forma_pagamento IN ('boleto', 'pix', 'cartao', 'debito_automatico', 'transferencia', 'dinheiro')),

    -- Dados bancários
    banco_origem VARCHAR(10),
    agencia_origem VARCHAR(10),
    conta_origem VARCHAR(20),

    -- Autenticação
    autenticacao VARCHAR(100),
    comprovante_url TEXT,

    -- Status
    status VARCHAR(20) DEFAULT 'confirmado' CHECK (status IN ('pendente', 'confirmado', 'rejeitado', 'estornado')),

    -- Webhook
    webhook_id VARCHAR(100),
    webhook_data JSONB,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Acordos de pagamento
CREATE TABLE IF NOT EXISTS financeiro.acordos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    unidade_id UUID REFERENCES financeiro.unidades(id),

    -- Valores
    valor_original DECIMAL(12,2) NOT NULL,
    valor_negociado DECIMAL(12,2) NOT NULL,
    desconto_concedido DECIMAL(12,2) DEFAULT 0,

    -- Parcelamento
    numero_parcelas INTEGER NOT NULL,
    valor_parcela DECIMAL(12,2) NOT NULL,
    dia_vencimento INTEGER CHECK (dia_vencimento BETWEEN 1 AND 28),

    -- Datas
    data_acordo DATE NOT NULL DEFAULT CURRENT_DATE,
    primeira_parcela DATE NOT NULL,

    -- Status
    status VARCHAR(20) DEFAULT 'ativo' CHECK (status IN ('ativo', 'quitado', 'quebrado', 'cancelado')),
    parcelas_pagas INTEGER DEFAULT 0,

    -- Observações
    observacoes TEXT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Boletos do acordo
CREATE TABLE IF NOT EXISTS financeiro.acordo_boletos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    acordo_id UUID REFERENCES financeiro.acordos(id) ON DELETE CASCADE,
    boleto_id UUID REFERENCES financeiro.boletos(id),
    parcela_numero INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Lançamentos (receitas e despesas)
CREATE TABLE IF NOT EXISTS financeiro.lancamentos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    condominio_id UUID REFERENCES financeiro.condominios(id),
    categoria_id UUID REFERENCES financeiro.categorias(id),

    tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('receita', 'despesa')),
    descricao TEXT NOT NULL,
    valor DECIMAL(12,2) NOT NULL,

    data_competencia DATE NOT NULL,
    data_pagamento DATE,

    status VARCHAR(20) DEFAULT 'pendente' CHECK (status IN ('pendente', 'pago', 'cancelado')),

    -- Rateio
    rateio BOOLEAN DEFAULT FALSE,
    boleto_id UUID REFERENCES financeiro.boletos(id),

    -- Fornecedor (para despesas)
    fornecedor_nome VARCHAR(255),
    fornecedor_cnpj VARCHAR(18),

    -- Comprovantes
    comprovante_url TEXT,
    nota_fiscal VARCHAR(50),

    metadata JSONB,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Bancos integrados
CREATE TABLE IF NOT EXISTS financeiro.bancos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    condominio_id UUID REFERENCES financeiro.condominios(id),

    codigo VARCHAR(10) NOT NULL,
    nome VARCHAR(100) NOT NULL,
    agencia VARCHAR(10),
    conta VARCHAR(20),

    -- Credenciais (criptografadas)
    client_id_encrypted TEXT,
    client_secret_encrypted TEXT,
    certificado_path TEXT,

    -- Status
    ativo BOOLEAN DEFAULT TRUE,
    ultima_sincronizacao TIMESTAMP WITH TIME ZONE,
    status_integracao VARCHAR(20) DEFAULT 'pendente',

    -- Configurações
    ambiente VARCHAR(20) DEFAULT 'sandbox' CHECK (ambiente IN ('sandbox', 'production')),
    webhook_url TEXT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =============================================================================
-- TABELAS DE AUDITORIA
-- =============================================================================

-- Log de auditoria
CREATE TABLE IF NOT EXISTS financeiro.audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Ação
    acao VARCHAR(50) NOT NULL, -- CREATE, UPDATE, DELETE, LOGIN, etc.
    tabela VARCHAR(100),
    registro_id UUID,

    -- Usuário
    usuario_id UUID,
    usuario_email VARCHAR(255),
    ip_address VARCHAR(45),
    user_agent TEXT,

    -- Dados
    dados_anteriores JSONB,
    dados_novos JSONB,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Log de transações financeiras
CREATE TABLE IF NOT EXISTS financeiro.transacao_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    tipo VARCHAR(50) NOT NULL, -- BOLETO_EMITIDO, PAGAMENTO_RECEBIDO, etc.

    boleto_id UUID REFERENCES financeiro.boletos(id),
    pagamento_id UUID REFERENCES financeiro.pagamentos(id),
    acordo_id UUID REFERENCES financeiro.acordos(id),

    valor DECIMAL(12,2),
    status VARCHAR(20),

    detalhes JSONB,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =============================================================================
-- ÍNDICES
-- =============================================================================

-- Boletos
CREATE INDEX IF NOT EXISTS idx_boletos_unidade ON financeiro.boletos(unidade_id);
CREATE INDEX IF NOT EXISTS idx_boletos_condominio ON financeiro.boletos(condominio_id);
CREATE INDEX IF NOT EXISTS idx_boletos_vencimento ON financeiro.boletos(vencimento);
CREATE INDEX IF NOT EXISTS idx_boletos_status ON financeiro.boletos(status);
CREATE INDEX IF NOT EXISTS idx_boletos_referencia ON financeiro.boletos(referencia);
CREATE INDEX IF NOT EXISTS idx_boletos_numero ON financeiro.boletos(numero);

-- Pagamentos
CREATE INDEX IF NOT EXISTS idx_pagamentos_boleto ON financeiro.pagamentos(boleto_id);
CREATE INDEX IF NOT EXISTS idx_pagamentos_unidade ON financeiro.pagamentos(unidade_id);
CREATE INDEX IF NOT EXISTS idx_pagamentos_data ON financeiro.pagamentos(data_pagamento);

-- Acordos
CREATE INDEX IF NOT EXISTS idx_acordos_unidade ON financeiro.acordos(unidade_id);
CREATE INDEX IF NOT EXISTS idx_acordos_status ON financeiro.acordos(status);

-- Lançamentos
CREATE INDEX IF NOT EXISTS idx_lancamentos_condominio ON financeiro.lancamentos(condominio_id);
CREATE INDEX IF NOT EXISTS idx_lancamentos_tipo ON financeiro.lancamentos(tipo);
CREATE INDEX IF NOT EXISTS idx_lancamentos_data ON financeiro.lancamentos(data_competencia);

-- Unidades
CREATE INDEX IF NOT EXISTS idx_unidades_condominio ON financeiro.unidades(condominio_id);
CREATE INDEX IF NOT EXISTS idx_unidades_bloco_numero ON financeiro.unidades(bloco, numero);

-- Auditoria
CREATE INDEX IF NOT EXISTS idx_audit_usuario ON financeiro.audit_log(usuario_id);
CREATE INDEX IF NOT EXISTS idx_audit_created ON financeiro.audit_log(created_at);
CREATE INDEX IF NOT EXISTS idx_transacao_created ON financeiro.transacao_log(created_at);

-- =============================================================================
-- TRIGGERS
-- =============================================================================

-- Função para atualizar updated_at
CREATE OR REPLACE FUNCTION financeiro.update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers de updated_at
CREATE TRIGGER trg_condominios_updated_at
    BEFORE UPDATE ON financeiro.condominios
    FOR EACH ROW EXECUTE FUNCTION financeiro.update_updated_at();

CREATE TRIGGER trg_unidades_updated_at
    BEFORE UPDATE ON financeiro.unidades
    FOR EACH ROW EXECUTE FUNCTION financeiro.update_updated_at();

CREATE TRIGGER trg_boletos_updated_at
    BEFORE UPDATE ON financeiro.boletos
    FOR EACH ROW EXECUTE FUNCTION financeiro.update_updated_at();

CREATE TRIGGER trg_acordos_updated_at
    BEFORE UPDATE ON financeiro.acordos
    FOR EACH ROW EXECUTE FUNCTION financeiro.update_updated_at();

CREATE TRIGGER trg_lancamentos_updated_at
    BEFORE UPDATE ON financeiro.lancamentos
    FOR EACH ROW EXECUTE FUNCTION financeiro.update_updated_at();

CREATE TRIGGER trg_bancos_updated_at
    BEFORE UPDATE ON financeiro.bancos
    FOR EACH ROW EXECUTE FUNCTION financeiro.update_updated_at();

-- =============================================================================
-- DADOS INICIAIS
-- =============================================================================

-- Categorias padrão
INSERT INTO financeiro.categorias (id, nome, tipo, descricao, cor, icone) VALUES
    ('a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'Taxa de Condomínio', 'receita', 'Taxa mensal ordinária', '#4CAF50', 'home'),
    ('b2c3d4e5-f6a7-8901-bcde-f12345678901', 'Taxa Extra', 'receita', 'Taxa extraordinária', '#2196F3', 'plus-circle'),
    ('c3d4e5f6-a7b8-9012-cdef-123456789012', 'Reserva de Área', 'receita', 'Aluguel de áreas comuns', '#9C27B0', 'calendar'),
    ('d4e5f6a7-b8c9-0123-defa-234567890123', 'Multa', 'receita', 'Multas por atraso ou infração', '#F44336', 'alert-triangle'),
    ('e5f6a7b8-c9d0-1234-efab-345678901234', 'Água', 'despesa', 'Conta de água', '#03A9F4', 'droplet'),
    ('f6a7b8c9-d0e1-2345-fabc-456789012345', 'Energia', 'despesa', 'Conta de energia elétrica', '#FFC107', 'zap'),
    ('a7b8c9d0-e1f2-3456-abcd-567890123456', 'Manutenção', 'despesa', 'Serviços de manutenção', '#795548', 'tool'),
    ('b8c9d0e1-f2a3-4567-bcde-678901234567', 'Funcionários', 'despesa', 'Folha de pagamento', '#607D8B', 'users'),
    ('c9d0e1f2-a3b4-5678-cdef-789012345678', 'Segurança', 'despesa', 'Serviços de segurança', '#3F51B5', 'shield'),
    ('d0e1f2a3-b4c5-6789-defa-890123456789', 'Limpeza', 'despesa', 'Serviços de limpeza', '#00BCD4', 'trash-2')
ON CONFLICT (id) DO NOTHING;

-- =============================================================================
-- VIEWS
-- =============================================================================

-- View de inadimplência por unidade
CREATE OR REPLACE VIEW financeiro.v_inadimplencia AS
SELECT
    u.id as unidade_id,
    u.bloco,
    u.numero,
    u.proprietario_nome,
    COUNT(CASE WHEN b.status = 'vencido' THEN 1 END) as boletos_vencidos,
    COALESCE(SUM(CASE WHEN b.status = 'vencido' THEN b.valor END), 0) as valor_vencido,
    MAX(b.vencimento) FILTER (WHERE b.status = 'vencido') as vencimento_mais_antigo,
    CURRENT_DATE - MAX(b.vencimento) FILTER (WHERE b.status = 'vencido') as dias_atraso_max
FROM financeiro.unidades u
LEFT JOIN financeiro.boletos b ON b.unidade_id = u.id
WHERE u.ativo = true
GROUP BY u.id, u.bloco, u.numero, u.proprietario_nome;

-- View de resumo financeiro mensal
CREATE OR REPLACE VIEW financeiro.v_resumo_mensal AS
SELECT
    c.id as condominio_id,
    DATE_TRUNC('month', b.vencimento) as mes,
    COUNT(b.id) as total_boletos,
    COUNT(CASE WHEN b.status = 'pago' THEN 1 END) as boletos_pagos,
    COUNT(CASE WHEN b.status = 'vencido' THEN 1 END) as boletos_vencidos,
    COALESCE(SUM(b.valor), 0) as valor_total,
    COALESCE(SUM(CASE WHEN b.status = 'pago' THEN b.valor_pago END), 0) as valor_recebido,
    COALESCE(SUM(CASE WHEN b.status = 'vencido' THEN b.valor END), 0) as valor_inadimplente
FROM financeiro.condominios c
LEFT JOIN financeiro.boletos b ON b.condominio_id = c.id
WHERE b.vencimento >= CURRENT_DATE - INTERVAL '12 months'
GROUP BY c.id, DATE_TRUNC('month', b.vencimento);

-- =============================================================================
-- COMENTÁRIOS
-- =============================================================================

COMMENT ON SCHEMA financeiro IS 'Schema do módulo financeiro do Conecta Plus';
COMMENT ON TABLE financeiro.boletos IS 'Boletos emitidos para cobrança de taxas condominiais';
COMMENT ON TABLE financeiro.pagamentos IS 'Registro de pagamentos recebidos';
COMMENT ON TABLE financeiro.acordos IS 'Acordos de parcelamento de dívidas';
COMMENT ON TABLE financeiro.audit_log IS 'Log de auditoria de todas as ações';

-- =============================================================================
-- FIM DA MIGRATION
-- =============================================================================
