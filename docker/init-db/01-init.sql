-- Conecta Plus - Inicialização do Banco de Dados
-- Executado automaticamente na criação do container

-- Extensões
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Schema principal
CREATE SCHEMA IF NOT EXISTS conecta;

-- Tabela de Condominios
CREATE TABLE IF NOT EXISTS conecta.condominios (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nome VARCHAR(255) NOT NULL,
    cnpj VARCHAR(18) UNIQUE,
    endereco JSONB,
    telefone VARCHAR(20),
    email VARCHAR(255),
    configuracoes JSONB DEFAULT '{}',
    ativo BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabela de Usuários
CREATE TABLE IF NOT EXISTS conecta.usuarios (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    senha_hash VARCHAR(255) NOT NULL,
    nome VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'morador',
    condominio_id UUID REFERENCES conecta.condominios(id),
    avatar_url VARCHAR(500),
    telefone VARCHAR(20),
    ativo BOOLEAN DEFAULT true,
    ultimo_acesso TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabela de Unidades
CREATE TABLE IF NOT EXISTS conecta.unidades (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    condominio_id UUID REFERENCES conecta.condominios(id) NOT NULL,
    bloco VARCHAR(50),
    numero VARCHAR(20) NOT NULL,
    tipo VARCHAR(50) DEFAULT 'apartamento',
    area_m2 DECIMAL(10,2),
    proprietario_id UUID REFERENCES conecta.usuarios(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(condominio_id, bloco, numero)
);

-- Tabela de Moradores (relação usuário-unidade)
CREATE TABLE IF NOT EXISTS conecta.moradores (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    usuario_id UUID REFERENCES conecta.usuarios(id) NOT NULL,
    unidade_id UUID REFERENCES conecta.unidades(id) NOT NULL,
    tipo VARCHAR(50) DEFAULT 'morador', -- proprietario, inquilino, morador
    principal BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(usuario_id, unidade_id)
);

-- Tabela de Visitantes
CREATE TABLE IF NOT EXISTS conecta.visitantes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    condominio_id UUID REFERENCES conecta.condominios(id) NOT NULL,
    nome VARCHAR(255) NOT NULL,
    documento VARCHAR(20),
    tipo_documento VARCHAR(20) DEFAULT 'cpf',
    telefone VARCHAR(20),
    foto_url VARCHAR(500),
    unidade_destino_id UUID REFERENCES conecta.unidades(id),
    status VARCHAR(50) DEFAULT 'aguardando', -- aguardando, autorizado, negado, finalizado
    data_entrada TIMESTAMP WITH TIME ZONE,
    data_saida TIMESTAMP WITH TIME ZONE,
    autorizado_por UUID REFERENCES conecta.usuarios(id),
    observacoes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabela de Acessos
CREATE TABLE IF NOT EXISTS conecta.acessos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    condominio_id UUID REFERENCES conecta.condominios(id) NOT NULL,
    tipo VARCHAR(50) NOT NULL, -- entrada, saida
    pessoa_tipo VARCHAR(50) NOT NULL, -- morador, visitante, prestador, entregador
    pessoa_id UUID,
    pessoa_nome VARCHAR(255),
    dispositivo VARCHAR(100), -- portaria, tag, facial, app
    local VARCHAR(100),
    foto_url VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabela de Câmeras
CREATE TABLE IF NOT EXISTS conecta.cameras (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    condominio_id UUID REFERENCES conecta.condominios(id) NOT NULL,
    nome VARCHAR(100) NOT NULL,
    descricao TEXT,
    url_stream VARCHAR(500),
    url_snapshot VARCHAR(500),
    tipo VARCHAR(50) DEFAULT 'ip', -- ip, analogica, frigate
    fabricante VARCHAR(100),
    modelo VARCHAR(100),
    local VARCHAR(100),
    ativo BOOLEAN DEFAULT true,
    configuracoes JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabela de Ocorrências
CREATE TABLE IF NOT EXISTS conecta.ocorrencias (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    condominio_id UUID REFERENCES conecta.condominios(id) NOT NULL,
    titulo VARCHAR(255) NOT NULL,
    descricao TEXT,
    tipo VARCHAR(50), -- reclamacao, sugestao, manutencao, seguranca
    prioridade VARCHAR(20) DEFAULT 'media', -- baixa, media, alta, critica
    status VARCHAR(50) DEFAULT 'aberta', -- aberta, em_andamento, resolvida, fechada
    reportado_por UUID REFERENCES conecta.usuarios(id),
    unidade_id UUID REFERENCES conecta.unidades(id),
    responsavel_id UUID REFERENCES conecta.usuarios(id),
    anexos JSONB DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolvido_at TIMESTAMP WITH TIME ZONE
);

-- Tabela de Reservas
CREATE TABLE IF NOT EXISTS conecta.areas_comuns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    condominio_id UUID REFERENCES conecta.condominios(id) NOT NULL,
    nome VARCHAR(100) NOT NULL,
    descricao TEXT,
    capacidade INTEGER,
    valor DECIMAL(10,2) DEFAULT 0,
    regras TEXT,
    horario_abertura TIME,
    horario_fechamento TIME,
    dias_funcionamento INTEGER[] DEFAULT '{1,2,3,4,5,6,0}',
    ativo BOOLEAN DEFAULT true,
    fotos JSONB DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS conecta.reservas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    area_id UUID REFERENCES conecta.areas_comuns(id) NOT NULL,
    usuario_id UUID REFERENCES conecta.usuarios(id) NOT NULL,
    unidade_id UUID REFERENCES conecta.unidades(id),
    data_reserva DATE NOT NULL,
    horario_inicio TIME NOT NULL,
    horario_fim TIME NOT NULL,
    status VARCHAR(50) DEFAULT 'pendente', -- pendente, confirmada, cancelada
    valor_pago DECIMAL(10,2) DEFAULT 0,
    observacoes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabela de Encomendas
CREATE TABLE IF NOT EXISTS conecta.encomendas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    condominio_id UUID REFERENCES conecta.condominios(id) NOT NULL,
    unidade_id UUID REFERENCES conecta.unidades(id) NOT NULL,
    tipo VARCHAR(50) DEFAULT 'pacote', -- pacote, carta, documento, outros
    remetente VARCHAR(255),
    codigo_rastreio VARCHAR(100),
    descricao TEXT,
    foto_url VARCHAR(500),
    recebido_por UUID REFERENCES conecta.usuarios(id),
    retirado_por UUID REFERENCES conecta.usuarios(id),
    status VARCHAR(50) DEFAULT 'aguardando', -- aguardando, notificado, retirado
    data_recebimento TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    data_retirada TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabela de Comunicados
CREATE TABLE IF NOT EXISTS conecta.comunicados (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    condominio_id UUID REFERENCES conecta.condominios(id) NOT NULL,
    titulo VARCHAR(255) NOT NULL,
    conteudo TEXT NOT NULL,
    tipo VARCHAR(50) DEFAULT 'informativo', -- informativo, urgente, manutencao, evento
    autor_id UUID REFERENCES conecta.usuarios(id),
    data_publicacao TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    data_expiracao TIMESTAMP WITH TIME ZONE,
    anexos JSONB DEFAULT '[]',
    destinatarios JSONB DEFAULT '{"todos": true}',
    ativo BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabela Financeira - Boletos
CREATE TABLE IF NOT EXISTS conecta.boletos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    condominio_id UUID REFERENCES conecta.condominios(id) NOT NULL,
    unidade_id UUID REFERENCES conecta.unidades(id) NOT NULL,
    referencia VARCHAR(20) NOT NULL, -- 2024-01, 2024-02
    valor DECIMAL(10,2) NOT NULL,
    data_vencimento DATE NOT NULL,
    data_pagamento DATE,
    valor_pago DECIMAL(10,2),
    status VARCHAR(50) DEFAULT 'aberto', -- aberto, pago, vencido, cancelado
    linha_digitavel VARCHAR(100),
    codigo_barras VARCHAR(100),
    pdf_url VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabela de Alertas
CREATE TABLE IF NOT EXISTS conecta.alertas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    condominio_id UUID REFERENCES conecta.condominios(id),
    tipo VARCHAR(50) NOT NULL, -- seguranca, sistema, manutencao, financeiro
    prioridade VARCHAR(20) DEFAULT 'media',
    titulo VARCHAR(255) NOT NULL,
    mensagem TEXT,
    origem VARCHAR(100), -- camera, sensor, sistema, usuario
    dados JSONB DEFAULT '{}',
    lido BOOLEAN DEFAULT false,
    lido_por UUID REFERENCES conecta.usuarios(id),
    lido_em TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_usuarios_email ON conecta.usuarios(email);
CREATE INDEX IF NOT EXISTS idx_usuarios_condominio ON conecta.usuarios(condominio_id);
CREATE INDEX IF NOT EXISTS idx_unidades_condominio ON conecta.unidades(condominio_id);
CREATE INDEX IF NOT EXISTS idx_visitantes_condominio ON conecta.visitantes(condominio_id);
CREATE INDEX IF NOT EXISTS idx_visitantes_status ON conecta.visitantes(status);
CREATE INDEX IF NOT EXISTS idx_acessos_condominio ON conecta.acessos(condominio_id);
CREATE INDEX IF NOT EXISTS idx_acessos_created ON conecta.acessos(created_at);
CREATE INDEX IF NOT EXISTS idx_ocorrencias_status ON conecta.ocorrencias(status);
CREATE INDEX IF NOT EXISTS idx_reservas_data ON conecta.reservas(data_reserva);
CREATE INDEX IF NOT EXISTS idx_encomendas_status ON conecta.encomendas(status);
CREATE INDEX IF NOT EXISTS idx_boletos_vencimento ON conecta.boletos(data_vencimento);
CREATE INDEX IF NOT EXISTS idx_alertas_created ON conecta.alertas(created_at);

-- Função para atualizar updated_at
CREATE OR REPLACE FUNCTION conecta.update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers para updated_at
DO $$
DECLARE
    t text;
BEGIN
    FOR t IN
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'conecta'
        AND table_name IN ('condominios', 'usuarios', 'unidades', 'visitantes', 'cameras', 'ocorrencias', 'areas_comuns', 'reservas', 'encomendas', 'comunicados', 'boletos')
    LOOP
        EXECUTE format('
            DROP TRIGGER IF EXISTS trigger_update_%I ON conecta.%I;
            CREATE TRIGGER trigger_update_%I
            BEFORE UPDATE ON conecta.%I
            FOR EACH ROW EXECUTE FUNCTION conecta.update_updated_at();
        ', t, t, t, t);
    END LOOP;
END;
$$;

-- Dados iniciais
INSERT INTO conecta.condominios (id, nome, cnpj, endereco, telefone, email, configuracoes)
VALUES (
    'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
    'Residencial Conecta Plus',
    '12.345.678/0001-90',
    '{"logradouro": "Rua das Palmeiras", "numero": "500", "bairro": "Jardim América", "cidade": "São Paulo", "estado": "SP", "cep": "01234-567"}',
    '(11) 3456-7890',
    'contato@residencialconecta.com.br',
    '{"corPrimaria": "#2563eb", "corSecundaria": "#1e40af", "modulosAtivos": ["cftv", "acesso", "financeiro", "ocorrencias", "reservas", "encomendas", "comunicados"]}'
) ON CONFLICT DO NOTHING;

-- Usuário admin (senha: admin123)
INSERT INTO conecta.usuarios (id, email, senha_hash, nome, role, condominio_id)
VALUES (
    'b2c3d4e5-f6a7-8901-bcde-f12345678901',
    'admin@conectaplus.com.br',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.3Ud2uXVQ.3Oeji', -- admin123
    'Administrador',
    'admin',
    'a1b2c3d4-e5f6-7890-abcd-ef1234567890'
) ON CONFLICT DO NOTHING;

-- Usuário síndico
INSERT INTO conecta.usuarios (id, email, senha_hash, nome, role, condominio_id)
VALUES (
    'c3d4e5f6-a7b8-9012-cdef-123456789012',
    'sindico@conectaplus.com.br',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.3Ud2uXVQ.3Oeji', -- sindico123
    'João Silva',
    'sindico',
    'a1b2c3d4-e5f6-7890-abcd-ef1234567890'
) ON CONFLICT DO NOTHING;

-- Usuário porteiro
INSERT INTO conecta.usuarios (id, email, senha_hash, nome, role, condominio_id)
VALUES (
    'd4e5f6a7-b8c9-0123-def0-234567890123',
    'porteiro@conectaplus.com.br',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.3Ud2uXVQ.3Oeji', -- porteiro123
    'Carlos Santos',
    'porteiro',
    'a1b2c3d4-e5f6-7890-abcd-ef1234567890'
) ON CONFLICT DO NOTHING;

-- Unidades de exemplo
INSERT INTO conecta.unidades (condominio_id, bloco, numero, tipo)
SELECT
    'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
    'A',
    n::text,
    'apartamento'
FROM generate_series(101, 110) n
ON CONFLICT DO NOTHING;

INSERT INTO conecta.unidades (condominio_id, bloco, numero, tipo)
SELECT
    'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
    'B',
    n::text,
    'apartamento'
FROM generate_series(101, 110) n
ON CONFLICT DO NOTHING;

-- Áreas comuns
INSERT INTO conecta.areas_comuns (condominio_id, nome, descricao, capacidade, valor)
VALUES
    ('a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'Salão de Festas', 'Salão amplo com cozinha', 100, 500.00),
    ('a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'Churrasqueira', 'Área de churrasqueira coberta', 30, 200.00),
    ('a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'Piscina', 'Piscina adulto e infantil', 50, 0.00),
    ('a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'Academia', 'Academia completa', 20, 0.00)
ON CONFLICT DO NOTHING;

-- Câmeras
INSERT INTO conecta.cameras (condominio_id, nome, local, tipo, ativo)
VALUES
    ('a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'Portaria Principal', 'Entrada', 'frigate', true),
    ('a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'Estacionamento A', 'Garagem', 'frigate', true),
    ('a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'Estacionamento B', 'Garagem', 'frigate', false),
    ('a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'Hall Social', 'Interno', 'frigate', true),
    ('a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'Piscina', 'Área de Lazer', 'frigate', true),
    ('a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'Academia', 'Área de Lazer', 'frigate', true)
ON CONFLICT DO NOTHING;

COMMIT;
