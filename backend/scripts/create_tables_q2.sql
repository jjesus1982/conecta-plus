-- ============================================
-- Conecta Plus - Q2: Inteligencia Proativa
-- Script de Criacao de Tabelas
-- Data: 2025-12-23
-- ============================================

-- Definir schema
SET search_path TO conecta, public;

-- ============================================
-- TIPOS ENUM Q2
-- ============================================

-- Previsao
DO $$ BEGIN
    CREATE TYPE conecta.tipo_previsao AS ENUM ('financeiro', 'manutencao', 'seguranca', 'convivencia');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE conecta.subtipo_previsao AS ENUM (
        'inadimplencia_risco', 'fluxo_caixa_alerta',
        'equipamento_risco', 'area_comum_desgaste',
        'horario_vulneravel', 'padrao_anomalo',
        'conflito_potencial'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE conecta.status_previsao AS ENUM ('pendente', 'confirmada', 'evitada', 'falso_positivo', 'expirada');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE conecta.tipo_entidade_previsao AS ENUM ('morador', 'unidade', 'equipamento', 'area', 'condominio');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Sugestao
DO $$ BEGIN
    CREATE TYPE conecta.tipo_sugestao AS ENUM ('operacional', 'financeira', 'convivencia', 'seguranca', 'manutencao');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE conecta.codigo_sugestao AS ENUM (
        'otimizar_ronda', 'reagendar_manutencao', 'consolidar_comunicados',
        'renegociar_contrato', 'antecipar_cobranca', 'reserva_emergencia', 'reduzir_custos',
        'mediar_conflito', 'reconhecer_colaborador', 'evento_integracao',
        'reforcar_horario', 'atualizar_cadastro',
        'preventiva_urgente', 'substituir_equipamento'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE conecta.status_sugestao AS ENUM ('pendente', 'visualizada', 'aceita', 'rejeitada', 'expirada', 'em_andamento', 'concluida');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE conecta.perfil_destino_sugestao AS ENUM ('sindico', 'admin', 'porteiro', 'zelador', 'morador', 'conselho');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Comunicacao
DO $$ BEGIN
    CREATE TYPE conecta.canal_comunicacao AS ENUM ('push', 'email', 'whatsapp', 'sms', 'in_app');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE conecta.tipo_comunicacao AS ENUM ('alerta', 'comunicado', 'lembrete', 'sugestao', 'notificacao', 'boletim');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE conecta.urgencia_comunicacao AS ENUM ('critica', 'alta', 'media', 'baixa');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Feedback
DO $$ BEGIN
    CREATE TYPE conecta.tipo_origem_feedback AS ENUM ('previsao', 'sugestao', 'comunicacao', 'ocorrencia', 'atendimento', 'geral');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE conecta.tipo_feedback AS ENUM ('explicito', 'implicito');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE conecta.valor_feedback AS ENUM ('util', 'nao_util', 'aceito', 'rejeitado', 'confirmado', 'falso_positivo', 'ignorado', 'spam');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- ============================================
-- TABELA: previsoes
-- RF-05: Previsao de Problemas
-- ============================================
CREATE TABLE IF NOT EXISTS conecta.previsoes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Classificacao
    tipo conecta.tipo_previsao NOT NULL,
    subtipo conecta.subtipo_previsao NOT NULL,

    -- Entidade relacionada
    entidade_tipo conecta.tipo_entidade_previsao NOT NULL,
    entidade_id UUID,
    entidade_nome VARCHAR(255),

    -- Analise
    probabilidade FLOAT NOT NULL CHECK (probabilidade >= 0 AND probabilidade <= 1),
    confianca FLOAT NOT NULL DEFAULT 0.5 CHECK (confianca >= 0 AND confianca <= 1),
    horizonte_dias INTEGER NOT NULL,

    -- Sinais
    sinais JSONB DEFAULT '[]'::jsonb,
    dados_entrada JSONB DEFAULT '{}'::jsonb,

    -- Acao
    acao_recomendada TEXT NOT NULL,
    acao_url VARCHAR(500),
    acao_params JSONB DEFAULT '{}'::jsonb,
    acao_tomada BOOLEAN DEFAULT FALSE,
    acao_tomada_em TIMESTAMP,
    acao_tomada_por UUID REFERENCES conecta.usuarios(id),
    acao_resultado VARCHAR(500),

    -- Status
    status conecta.status_previsao DEFAULT 'pendente' NOT NULL,
    validada_em TIMESTAMP,
    validada_por UUID REFERENCES conecta.usuarios(id),
    motivo_validacao VARCHAR(500),

    -- Impacto
    impacto_estimado VARCHAR(255),
    impacto_real VARCHAR(255),

    -- Relacionamentos
    condominio_id UUID NOT NULL REFERENCES conecta.condominios(id),

    -- Modelo
    modelo_versao VARCHAR(50),
    modelo_score FLOAT,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP
);

-- Indices para previsoes
CREATE INDEX IF NOT EXISTS idx_previsoes_tipo ON conecta.previsoes(tipo);
CREATE INDEX IF NOT EXISTS idx_previsoes_subtipo ON conecta.previsoes(subtipo);
CREATE INDEX IF NOT EXISTS idx_previsoes_status ON conecta.previsoes(status);
CREATE INDEX IF NOT EXISTS idx_previsoes_condominio ON conecta.previsoes(condominio_id);
CREATE INDEX IF NOT EXISTS idx_previsoes_created ON conecta.previsoes(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_previsoes_probabilidade ON conecta.previsoes(probabilidade DESC);

-- ============================================
-- TABELA: sugestoes
-- RF-06: Sugestoes Automaticas
-- ============================================
CREATE TABLE IF NOT EXISTS conecta.sugestoes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Classificacao
    tipo conecta.tipo_sugestao NOT NULL,
    codigo conecta.codigo_sugestao NOT NULL,

    -- Conteudo
    titulo VARCHAR(255) NOT NULL,
    descricao TEXT NOT NULL,
    contexto TEXT,
    beneficio_estimado VARCHAR(255),

    -- Dados
    dados_entrada JSONB DEFAULT '{}'::jsonb,
    regra_aplicada VARCHAR(100),

    -- Destinatario
    perfil_destino conecta.perfil_destino_sugestao NOT NULL,
    usuario_destino_id UUID REFERENCES conecta.usuarios(id),

    -- Acao
    acao_url VARCHAR(500),
    acao_params JSONB DEFAULT '{}'::jsonb,
    acao_automatica BOOLEAN DEFAULT FALSE,

    -- Status
    status conecta.status_sugestao DEFAULT 'pendente' NOT NULL,
    visualizada_em TIMESTAMP,
    respondida_em TIMESTAMP,
    respondida_por UUID REFERENCES conecta.usuarios(id),
    motivo_rejeicao VARCHAR(500),

    -- Execucao
    executada_em TIMESTAMP,
    resultado_execucao TEXT,

    -- Feedback
    foi_util BOOLEAN,
    feedback TEXT,
    avaliacao INTEGER CHECK (avaliacao >= 1 AND avaliacao <= 5),

    -- Prioridade
    prioridade INTEGER DEFAULT 50 CHECK (prioridade >= 1 AND prioridade <= 100),
    score_relevancia FLOAT DEFAULT 0.5,

    -- Relacionamentos
    condominio_id UUID NOT NULL REFERENCES conecta.condominios(id),
    previsao_id UUID REFERENCES conecta.previsoes(id),

    -- Modelo
    modelo_versao VARCHAR(50),

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP
);

-- Indices para sugestoes
CREATE INDEX IF NOT EXISTS idx_sugestoes_tipo ON conecta.sugestoes(tipo);
CREATE INDEX IF NOT EXISTS idx_sugestoes_codigo ON conecta.sugestoes(codigo);
CREATE INDEX IF NOT EXISTS idx_sugestoes_status ON conecta.sugestoes(status);
CREATE INDEX IF NOT EXISTS idx_sugestoes_perfil ON conecta.sugestoes(perfil_destino);
CREATE INDEX IF NOT EXISTS idx_sugestoes_usuario ON conecta.sugestoes(usuario_destino_id);
CREATE INDEX IF NOT EXISTS idx_sugestoes_condominio ON conecta.sugestoes(condominio_id);
CREATE INDEX IF NOT EXISTS idx_sugestoes_prioridade ON conecta.sugestoes(prioridade DESC);
CREATE INDEX IF NOT EXISTS idx_sugestoes_created ON conecta.sugestoes(created_at DESC);

-- ============================================
-- TABELA: preferencias_comunicacao
-- RF-07: Comunicacao Inteligente
-- ============================================
CREATE TABLE IF NOT EXISTS conecta.preferencias_comunicacao (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id UUID UNIQUE NOT NULL REFERENCES conecta.usuarios(id),

    -- Horarios
    horario_preferido_inicio TIME DEFAULT '08:00',
    horario_preferido_fim TIME DEFAULT '21:00',
    dias_preferidos INTEGER[] DEFAULT ARRAY[1,2,3,4,5],
    fuso_horario VARCHAR(50) DEFAULT 'America/Sao_Paulo',

    -- Canais
    canal_primario conecta.canal_comunicacao DEFAULT 'push',
    canal_secundario conecta.canal_comunicacao DEFAULT 'email',
    canal_emergencia conecta.canal_comunicacao DEFAULT 'sms',

    -- Contatos
    email VARCHAR(255),
    telefone_whatsapp VARCHAR(20),
    telefone_sms VARCHAR(20),
    push_token VARCHAR(500),

    -- Frequencia
    max_notificacoes_dia INTEGER DEFAULT 5,
    agrupar_similares BOOLEAN DEFAULT TRUE,
    intervalo_minimo_minutos INTEGER DEFAULT 30,

    -- Categorias
    receber_financeiro BOOLEAN DEFAULT TRUE,
    receber_manutencao BOOLEAN DEFAULT TRUE,
    receber_seguranca BOOLEAN DEFAULT TRUE,
    receber_comunicados BOOLEAN DEFAULT TRUE,
    receber_assembleias BOOLEAN DEFAULT TRUE,
    receber_reservas BOOLEAN DEFAULT TRUE,
    receber_sugestoes BOOLEAN DEFAULT TRUE,
    receber_marketing BOOLEAN DEFAULT FALSE,

    -- Nao perturbe
    nao_perturbe_ativo BOOLEAN DEFAULT FALSE,
    nao_perturbe_inicio TIME DEFAULT '22:00',
    nao_perturbe_fim TIME DEFAULT '07:00',
    nao_perturbe_exceto_emergencias BOOLEAN DEFAULT TRUE,

    -- Metricas aprendidas
    taxa_abertura_push FLOAT DEFAULT 0,
    taxa_abertura_email FLOAT DEFAULT 0,
    taxa_abertura_whatsapp FLOAT DEFAULT 0,
    tempo_medio_resposta_segundos INTEGER DEFAULT 0,
    horario_mais_engajado TIME,
    dia_mais_engajado INTEGER,

    -- Contadores
    total_enviadas INTEGER DEFAULT 0,
    total_abertas INTEGER DEFAULT 0,
    total_clicadas INTEGER DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indices para preferencias_comunicacao
CREATE INDEX IF NOT EXISTS idx_pref_com_usuario ON conecta.preferencias_comunicacao(usuario_id);

-- ============================================
-- TABELA: historico_comunicacao
-- RF-07: Comunicacao Inteligente
-- ============================================
CREATE TABLE IF NOT EXISTS conecta.historico_comunicacao (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id UUID NOT NULL REFERENCES conecta.usuarios(id),

    -- Mensagem
    tipo conecta.tipo_comunicacao NOT NULL,
    titulo VARCHAR(255) NOT NULL,
    conteudo_resumo VARCHAR(1000),
    conteudo_completo TEXT,
    urgencia conecta.urgencia_comunicacao DEFAULT 'media',

    -- Canal e envio
    canal conecta.canal_comunicacao NOT NULL,
    enviado_em TIMESTAMP DEFAULT NOW() NOT NULL,
    horario_otimizado BOOLEAN DEFAULT FALSE,
    canal_otimizado BOOLEAN DEFAULT FALSE,

    -- Entrega
    entregue BOOLEAN DEFAULT FALSE,
    entregue_em TIMESTAMP,
    falha_entrega VARCHAR(255),

    -- Engajamento
    aberto BOOLEAN DEFAULT FALSE,
    aberto_em TIMESTAMP,
    clicou BOOLEAN DEFAULT FALSE,
    clicou_em TIMESTAMP,
    respondeu BOOLEAN DEFAULT FALSE,
    respondeu_em TIMESTAMP,

    -- Tempo de resposta
    tempo_ate_abertura_segundos INTEGER,
    tempo_ate_clique_segundos INTEGER,

    -- Feedback
    foi_util BOOLEAN,
    marcou_spam BOOLEAN DEFAULT FALSE,
    silenciou_tipo BOOLEAN DEFAULT FALSE,

    -- Contexto
    origem_id UUID,
    origem_tipo VARCHAR(50),
    categoria VARCHAR(50),

    -- Relacionamentos
    condominio_id UUID NOT NULL REFERENCES conecta.condominios(id),

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW() NOT NULL
);

-- Indices para historico_comunicacao
CREATE INDEX IF NOT EXISTS idx_hist_com_usuario ON conecta.historico_comunicacao(usuario_id);
CREATE INDEX IF NOT EXISTS idx_hist_com_tipo ON conecta.historico_comunicacao(tipo);
CREATE INDEX IF NOT EXISTS idx_hist_com_enviado ON conecta.historico_comunicacao(enviado_em DESC);
CREATE INDEX IF NOT EXISTS idx_hist_com_condominio ON conecta.historico_comunicacao(condominio_id);
CREATE INDEX IF NOT EXISTS idx_hist_com_origem ON conecta.historico_comunicacao(origem_tipo, origem_id);

-- ============================================
-- TABELA: fila_comunicacao
-- RF-07: Comunicacao Inteligente
-- ============================================
CREATE TABLE IF NOT EXISTS conecta.fila_comunicacao (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id UUID NOT NULL REFERENCES conecta.usuarios(id),

    -- Mensagem
    tipo conecta.tipo_comunicacao NOT NULL,
    titulo VARCHAR(255) NOT NULL,
    conteudo TEXT NOT NULL,
    urgencia conecta.urgencia_comunicacao DEFAULT 'media',
    canal conecta.canal_comunicacao NOT NULL,

    -- Agendamento
    agendar_para TIMESTAMP,
    prioridade INTEGER DEFAULT 50,

    -- Agrupamento
    pode_agrupar BOOLEAN DEFAULT TRUE,
    grupo_id UUID,

    -- Status
    processado BOOLEAN DEFAULT FALSE,
    processado_em TIMESTAMP,
    historico_id UUID REFERENCES conecta.historico_comunicacao(id),
    erro VARCHAR(500),

    -- Contexto
    origem_id UUID,
    origem_tipo VARCHAR(50),
    categoria VARCHAR(50),

    -- Relacionamentos
    condominio_id UUID NOT NULL REFERENCES conecta.condominios(id),

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW() NOT NULL
);

-- Indices para fila_comunicacao
CREATE INDEX IF NOT EXISTS idx_fila_com_processado ON conecta.fila_comunicacao(processado) WHERE processado = FALSE;
CREATE INDEX IF NOT EXISTS idx_fila_com_agendar ON conecta.fila_comunicacao(agendar_para) WHERE processado = FALSE;
CREATE INDEX IF NOT EXISTS idx_fila_com_usuario ON conecta.fila_comunicacao(usuario_id);
CREATE INDEX IF NOT EXISTS idx_fila_com_grupo ON conecta.fila_comunicacao(grupo_id) WHERE grupo_id IS NOT NULL;

-- ============================================
-- TABELA: feedback_modelo
-- RF-08: Aprendizado Continuo
-- ============================================
CREATE TABLE IF NOT EXISTS conecta.feedback_modelo (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Origem
    tipo_origem conecta.tipo_origem_feedback NOT NULL,
    origem_id UUID NOT NULL,

    -- Feedback
    tipo_feedback conecta.tipo_feedback NOT NULL,
    valor conecta.valor_feedback NOT NULL,
    comentario TEXT,
    avaliacao INTEGER CHECK (avaliacao >= 1 AND avaliacao <= 5),
    tags JSONB DEFAULT '[]'::jsonb,

    -- Usuario
    usuario_id UUID REFERENCES conecta.usuarios(id),
    perfil_usuario VARCHAR(50),

    -- Contexto
    contexto JSONB DEFAULT '{}'::jsonb,

    -- Treinamento
    usado_treinamento BOOLEAN DEFAULT FALSE,
    data_treinamento TIMESTAMP,
    versao_modelo VARCHAR(50),
    peso FLOAT DEFAULT 1.0,

    -- Relacionamentos
    condominio_id UUID NOT NULL REFERENCES conecta.condominios(id),

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW() NOT NULL
);

-- Indices para feedback_modelo
CREATE INDEX IF NOT EXISTS idx_feedback_tipo_origem ON conecta.feedback_modelo(tipo_origem);
CREATE INDEX IF NOT EXISTS idx_feedback_origem ON conecta.feedback_modelo(origem_id);
CREATE INDEX IF NOT EXISTS idx_feedback_valor ON conecta.feedback_modelo(valor);
CREATE INDEX IF NOT EXISTS idx_feedback_usuario ON conecta.feedback_modelo(usuario_id);
CREATE INDEX IF NOT EXISTS idx_feedback_condominio ON conecta.feedback_modelo(condominio_id);
CREATE INDEX IF NOT EXISTS idx_feedback_treinamento ON conecta.feedback_modelo(usado_treinamento) WHERE usado_treinamento = FALSE;
CREATE INDEX IF NOT EXISTS idx_feedback_created ON conecta.feedback_modelo(created_at DESC);

-- ============================================
-- TABELA: metricas_modelo
-- RF-08: Aprendizado Continuo
-- ============================================
CREATE TABLE IF NOT EXISTS conecta.metricas_modelo (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Modelo
    modelo VARCHAR(100) NOT NULL,
    versao VARCHAR(50) NOT NULL,

    -- Periodo
    periodo_inicio TIMESTAMP NOT NULL,
    periodo_fim TIMESTAMP NOT NULL,

    -- Metricas de classificacao
    total_predicoes INTEGER DEFAULT 0,
    verdadeiros_positivos INTEGER DEFAULT 0,
    falsos_positivos INTEGER DEFAULT 0,
    verdadeiros_negativos INTEGER DEFAULT 0,
    falsos_negativos INTEGER DEFAULT 0,

    -- Metricas calculadas
    "precision" FLOAT,
    recall FLOAT,
    f1_score FLOAT,
    accuracy FLOAT,

    -- Metricas de negocio
    taxa_aceitacao FLOAT,
    taxa_utilidade FLOAT,
    nps FLOAT,
    economia_gerada FLOAT,
    problemas_evitados INTEGER,

    -- Metricas de comunicacao
    taxa_entrega FLOAT,
    taxa_abertura FLOAT,
    taxa_clique FLOAT,
    tempo_medio_resposta FLOAT,

    -- Detalhes
    detalhes JSONB DEFAULT '{}'::jsonb,
    notas TEXT,

    -- Relacionamentos
    condominio_id UUID REFERENCES conecta.condominios(id),

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW() NOT NULL
);

-- Indices para metricas_modelo
CREATE INDEX IF NOT EXISTS idx_metricas_modelo ON conecta.metricas_modelo(modelo);
CREATE INDEX IF NOT EXISTS idx_metricas_versao ON conecta.metricas_modelo(versao);
CREATE INDEX IF NOT EXISTS idx_metricas_periodo ON conecta.metricas_modelo(periodo_inicio, periodo_fim);
CREATE INDEX IF NOT EXISTS idx_metricas_condominio ON conecta.metricas_modelo(condominio_id);

-- ============================================
-- TABELA: historico_treinamento
-- RF-08: Aprendizado Continuo
-- ============================================
CREATE TABLE IF NOT EXISTS conecta.historico_treinamento (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Modelo
    modelo VARCHAR(100) NOT NULL,
    versao_anterior VARCHAR(50),
    versao_nova VARCHAR(50) NOT NULL,

    -- Dados de treinamento
    total_amostras INTEGER NOT NULL,
    amostras_positivas INTEGER,
    amostras_negativas INTEGER,
    periodo_dados_inicio TIMESTAMP,
    periodo_dados_fim TIMESTAMP,

    -- Parametros
    parametros JSONB DEFAULT '{}'::jsonb,
    features JSONB DEFAULT '[]'::jsonb,

    -- Resultados
    metricas_validacao JSONB DEFAULT '{}'::jsonb,
    melhorou BOOLEAN,
    delta_f1 FLOAT,

    -- Deploy
    deployed BOOLEAN DEFAULT FALSE,
    deployed_em TIMESTAMP,
    rollback BOOLEAN DEFAULT FALSE,
    rollback_motivo VARCHAR(500),

    -- Metadata
    duracao_segundos INTEGER,
    executado_por VARCHAR(100),
    notas TEXT,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW() NOT NULL
);

-- Indices para historico_treinamento
CREATE INDEX IF NOT EXISTS idx_hist_trein_modelo ON conecta.historico_treinamento(modelo);
CREATE INDEX IF NOT EXISTS idx_hist_trein_versao ON conecta.historico_treinamento(versao_nova);
CREATE INDEX IF NOT EXISTS idx_hist_trein_deployed ON conecta.historico_treinamento(deployed);
CREATE INDEX IF NOT EXISTS idx_hist_trein_created ON conecta.historico_treinamento(created_at DESC);

-- ============================================
-- DADOS INICIAIS Q2
-- ============================================

-- Nenhum dado inicial necessario por enquanto
-- Os modelos serao populados conforme o sistema aprende

-- ============================================
-- FIM DO SCRIPT Q2
-- ============================================

SELECT 'Q2 Migration Complete!' as status;
