#!/usr/bin/env python3
"""
Script para inserir dados de teste do Q2 no banco de dados
"""

import os
import sys
from datetime import datetime, timedelta
from uuid import uuid4
import random

# Adicionar path do backend
sys.path.insert(0, '/opt/conecta-plus/backend')

# Configurar DATABASE_URL
os.environ['DATABASE_URL'] = 'postgresql://conecta_user:conecta_secret_2024@localhost:5432/conecta_db'

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# IDs fixos para testes
CONDOMINIO_ID = 'a1b2c3d4-e5f6-7890-abcd-ef1234567890'
USUARIO_ID = 'b2c3d4e5-f6a7-8901-bcde-f12345678901'

# Conectar ao banco
engine = create_engine(os.environ['DATABASE_URL'])
Session = sessionmaker(bind=engine)

def criar_schema():
    """Cria schema conecta se nao existir"""
    with engine.connect() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS conecta"))
        conn.commit()
    print("Schema 'conecta' verificado/criado")

def criar_tabelas_q2():
    """Cria tabelas do Q2 se nao existirem"""

    tabelas_sql = """
    -- Tipos ENUM
    DO $$ BEGIN
        CREATE TYPE conecta.tipo_previsao AS ENUM ('financeiro', 'manutencao', 'seguranca', 'convivencia');
    EXCEPTION WHEN duplicate_object THEN null; END $$;

    DO $$ BEGIN
        CREATE TYPE conecta.subtipo_previsao AS ENUM (
            'inadimplencia_risco', 'fluxo_caixa_alerta', 'equipamento_risco',
            'area_comum_desgaste', 'horario_vulneravel', 'padrao_anomalo', 'conflito_potencial'
        );
    EXCEPTION WHEN duplicate_object THEN null; END $$;

    DO $$ BEGIN
        CREATE TYPE conecta.status_previsao AS ENUM ('pendente', 'confirmada', 'evitada', 'falso_positivo', 'expirada');
    EXCEPTION WHEN duplicate_object THEN null; END $$;

    DO $$ BEGIN
        CREATE TYPE conecta.tipo_entidade_previsao AS ENUM ('morador', 'unidade', 'equipamento', 'area', 'condominio');
    EXCEPTION WHEN duplicate_object THEN null; END $$;

    DO $$ BEGIN
        CREATE TYPE conecta.tipo_sugestao AS ENUM ('operacional', 'financeira', 'convivencia', 'seguranca', 'manutencao');
    EXCEPTION WHEN duplicate_object THEN null; END $$;

    DO $$ BEGIN
        CREATE TYPE conecta.codigo_sugestao AS ENUM (
            'otimizar_ronda', 'reagendar_manutencao', 'consolidar_comunicados',
            'renegociar_contrato', 'antecipar_cobranca', 'reserva_emergencia', 'reduzir_custos',
            'mediar_conflito', 'reconhecer_colaborador', 'evento_integracao',
            'reforcar_horario', 'atualizar_cadastro', 'preventiva_urgente', 'substituir_equipamento'
        );
    EXCEPTION WHEN duplicate_object THEN null; END $$;

    DO $$ BEGIN
        CREATE TYPE conecta.status_sugestao AS ENUM ('pendente', 'visualizada', 'aceita', 'rejeitada', 'expirada', 'em_andamento', 'concluida');
    EXCEPTION WHEN duplicate_object THEN null; END $$;

    DO $$ BEGIN
        CREATE TYPE conecta.perfil_destino_sugestao AS ENUM ('sindico', 'admin', 'porteiro', 'zelador', 'morador', 'conselho');
    EXCEPTION WHEN duplicate_object THEN null; END $$;

    -- Tabela Previsoes
    CREATE TABLE IF NOT EXISTS conecta.previsoes (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        tipo conecta.tipo_previsao NOT NULL,
        subtipo conecta.subtipo_previsao NOT NULL,
        entidade_tipo conecta.tipo_entidade_previsao NOT NULL,
        entidade_id UUID,
        entidade_nome VARCHAR(255),
        probabilidade FLOAT NOT NULL,
        confianca FLOAT NOT NULL DEFAULT 0.5,
        horizonte_dias INTEGER NOT NULL,
        sinais JSONB DEFAULT '[]',
        dados_entrada JSONB DEFAULT '{}',
        acao_recomendada TEXT NOT NULL,
        acao_url VARCHAR(500),
        acao_params JSONB DEFAULT '{}',
        acao_tomada BOOLEAN DEFAULT FALSE,
        acao_tomada_em TIMESTAMP,
        acao_tomada_por UUID,
        acao_resultado VARCHAR(500),
        status conecta.status_previsao DEFAULT 'pendente',
        validada_em TIMESTAMP,
        validada_por UUID,
        motivo_validacao VARCHAR(500),
        impacto_estimado VARCHAR(255),
        impacto_real VARCHAR(255),
        condominio_id UUID NOT NULL,
        modelo_versao VARCHAR(50),
        modelo_score FLOAT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP
    );

    -- Tabela Sugestoes
    CREATE TABLE IF NOT EXISTS conecta.sugestoes (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        tipo conecta.tipo_sugestao NOT NULL,
        codigo conecta.codigo_sugestao NOT NULL,
        titulo VARCHAR(255) NOT NULL,
        descricao TEXT NOT NULL,
        contexto TEXT,
        beneficio_estimado VARCHAR(255),
        dados_entrada JSONB DEFAULT '{}',
        regra_aplicada VARCHAR(100),
        perfil_destino conecta.perfil_destino_sugestao NOT NULL,
        usuario_destino_id UUID,
        acao_url VARCHAR(500),
        acao_params JSONB DEFAULT '{}',
        acao_automatica BOOLEAN DEFAULT FALSE,
        status conecta.status_sugestao DEFAULT 'pendente',
        visualizada_em TIMESTAMP,
        respondida_em TIMESTAMP,
        respondida_por UUID,
        motivo_rejeicao VARCHAR(500),
        executada_em TIMESTAMP,
        resultado_execucao TEXT,
        foi_util BOOLEAN,
        feedback TEXT,
        avaliacao INTEGER,
        prioridade INTEGER DEFAULT 50,
        score_relevancia FLOAT DEFAULT 0.5,
        condominio_id UUID NOT NULL,
        previsao_id UUID,
        modelo_versao VARCHAR(50),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP
    );

    -- Indices
    CREATE INDEX IF NOT EXISTS idx_previsoes_condominio ON conecta.previsoes(condominio_id);
    CREATE INDEX IF NOT EXISTS idx_previsoes_tipo ON conecta.previsoes(tipo);
    CREATE INDEX IF NOT EXISTS idx_previsoes_status ON conecta.previsoes(status);
    CREATE INDEX IF NOT EXISTS idx_sugestoes_condominio ON conecta.sugestoes(condominio_id);
    CREATE INDEX IF NOT EXISTS idx_sugestoes_tipo ON conecta.sugestoes(tipo);
    CREATE INDEX IF NOT EXISTS idx_sugestoes_status ON conecta.sugestoes(status);
    """

    with engine.connect() as conn:
        for statement in tabelas_sql.split(';'):
            if statement.strip():
                try:
                    conn.execute(text(statement))
                except Exception as e:
                    print(f"Aviso: {e}")
        conn.commit()
    print("Tabelas Q2 verificadas/criadas")

def inserir_previsoes():
    """Insere previsoes de teste"""

    previsoes = [
        {
            'tipo': 'financeiro',
            'subtipo': 'inadimplencia_risco',
            'entidade_tipo': 'unidade',
            'entidade_nome': 'Unidade 101 - Bloco A',
            'probabilidade': 0.85,
            'confianca': 0.78,
            'horizonte_dias': 15,
            'sinais': '["3 boletos atrasados nos ultimos 6 meses", "Padrao de atraso crescente", "Ultimo pagamento com 45 dias de atraso"]',
            'acao_recomendada': 'Entrar em contato preventivo com o morador para negociacao antes do vencimento',
            'impacto_estimado': 'R$ 2.500 em inadimplencia',
            'status': 'pendente',
        },
        {
            'tipo': 'financeiro',
            'subtipo': 'inadimplencia_risco',
            'entidade_tipo': 'unidade',
            'entidade_nome': 'Unidade 305 - Bloco B',
            'probabilidade': 0.72,
            'confianca': 0.65,
            'horizonte_dias': 30,
            'sinais': '["Historico de atrasos esporadicos", "Mudanca recente de emprego informada"]',
            'acao_recomendada': 'Oferecer opcao de debito automatico ou parcelamento preventivo',
            'impacto_estimado': 'R$ 1.800 em inadimplencia',
            'status': 'pendente',
        },
        {
            'tipo': 'manutencao',
            'subtipo': 'equipamento_risco',
            'entidade_tipo': 'equipamento',
            'entidade_nome': 'Elevador Social 1',
            'probabilidade': 0.68,
            'confianca': 0.82,
            'horizonte_dias': 20,
            'sinais': '["5 chamados de manutencao em 3 meses", "Ultimo reparo em componente critico", "Equipamento com 8 anos de uso"]',
            'acao_recomendada': 'Agendar manutencao preventiva completa e avaliar necessidade de modernizacao',
            'impacto_estimado': 'Parada de 3-5 dias se falhar',
            'status': 'pendente',
        },
        {
            'tipo': 'manutencao',
            'subtipo': 'area_comum_desgaste',
            'entidade_tipo': 'area',
            'entidade_nome': 'Piscina',
            'probabilidade': 0.55,
            'confianca': 0.70,
            'horizonte_dias': 45,
            'sinais': '["Ultima troca de bomba ha 4 anos", "Aumento no consumo de energia", "Reclamacoes de pressao baixa"]',
            'acao_recomendada': 'Inspecionar sistema de filtragem e bomba, considerar substituicao preventiva',
            'impacto_estimado': 'R$ 8.000 em reparo emergencial',
            'status': 'pendente',
        },
        {
            'tipo': 'seguranca',
            'subtipo': 'horario_vulneravel',
            'entidade_tipo': 'condominio',
            'entidade_nome': 'Portaria Principal',
            'probabilidade': 0.62,
            'confianca': 0.75,
            'horizonte_dias': 7,
            'sinais': '["Aumento de 40% em acessos nao autorizados entre 2h-5h", "Camera 3 com angulo cego identificado", "2 tentativas de acesso forcado no mes"]',
            'acao_recomendada': 'Reforcar seguranca no periodo da madrugada e ajustar posicionamento da camera 3',
            'impacto_estimado': 'Risco de invasao',
            'status': 'pendente',
        },
        {
            'tipo': 'convivencia',
            'subtipo': 'conflito_potencial',
            'entidade_tipo': 'unidade',
            'entidade_nome': 'Unidade 402 x 502',
            'probabilidade': 0.58,
            'confianca': 0.60,
            'horizonte_dias': 14,
            'sinais': '["3 reclamacoes mutuas em 2 meses", "Discussao registrada na portaria", "Tema recorrente: barulho"]',
            'acao_recomendada': 'Agendar mediacao com sindico antes que escale para processo formal',
            'impacto_estimado': 'Processo juridico potencial',
            'status': 'pendente',
        },
    ]

    with engine.connect() as conn:
        # Limpar dados antigos de teste
        conn.execute(text(f"DELETE FROM conecta.previsoes WHERE condominio_id = '{CONDOMINIO_ID}'"))

        for p in previsoes:
            sql = text("""
                INSERT INTO conecta.previsoes (
                    tipo, subtipo, entidade_tipo, entidade_nome, probabilidade, confianca,
                    horizonte_dias, sinais, acao_recomendada, impacto_estimado, status,
                    condominio_id, modelo_versao, created_at, expires_at
                ) VALUES (
                    :tipo, :subtipo, :entidade_tipo, :entidade_nome, :probabilidade, :confianca,
                    :horizonte_dias, :sinais::jsonb, :acao_recomendada, :impacto_estimado, :status,
                    :condominio_id, 'v1.0.0', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP + INTERVAL '30 days'
                )
            """)
            conn.execute(sql, {**p, 'condominio_id': CONDOMINIO_ID})

        conn.commit()
    print(f"Inseridas {len(previsoes)} previsoes de teste")

def inserir_sugestoes():
    """Insere sugestoes de teste"""

    sugestoes = [
        {
            'tipo': 'financeira',
            'codigo': 'antecipar_cobranca',
            'titulo': 'Antecipar cobranca de inadimplentes',
            'descricao': 'Identificamos 3 unidades com alto risco de inadimplencia. Recomendamos contato preventivo antes do vencimento.',
            'contexto': 'Baseado no historico de pagamentos e padroes detectados pelo sistema de IA.',
            'beneficio_estimado': 'Reducao de 40% na inadimplencia',
            'perfil_destino': 'sindico',
            'prioridade': 85,
        },
        {
            'tipo': 'financeira',
            'codigo': 'renegociar_contrato',
            'titulo': 'Renegociar contrato de limpeza',
            'descricao': 'O contrato atual de limpeza esta 15% acima da media de mercado. Sugerimos cotacao com outros fornecedores.',
            'contexto': 'Analise comparativa de contratos similares em condominios da regiao.',
            'beneficio_estimado': 'Economia de R$ 800/mes',
            'perfil_destino': 'sindico',
            'prioridade': 70,
        },
        {
            'tipo': 'operacional',
            'codigo': 'otimizar_ronda',
            'titulo': 'Otimizar rota de ronda noturna',
            'descricao': 'A rota atual da ronda noturna pode ser otimizada para cobrir areas de maior risco identificadas.',
            'contexto': 'Analise de incidentes e pontos cegos detectados nas ultimas semanas.',
            'beneficio_estimado': 'Cobertura 30% mais eficiente',
            'perfil_destino': 'admin',
            'prioridade': 75,
        },
        {
            'tipo': 'operacional',
            'codigo': 'reagendar_manutencao',
            'titulo': 'Reagendar manutencao do elevador',
            'descricao': 'A manutencao programada coincide com dia de mudanca. Sugerimos antecipar para evitar transtornos.',
            'contexto': 'Cruzamento de agenda de manutencoes com reservas de mudanca.',
            'beneficio_estimado': 'Evitar reclamacoes de moradores',
            'perfil_destino': 'admin',
            'prioridade': 65,
        },
        {
            'tipo': 'convivencia',
            'codigo': 'evento_integracao',
            'titulo': 'Organizar evento de integracao',
            'descricao': 'Detectamos baixa participacao em assembleias e pouca interacao entre moradores. Um evento social pode melhorar a convivencia.',
            'contexto': 'Indice de participacao em assembleias abaixo de 20% nos ultimos 6 meses.',
            'beneficio_estimado': 'Melhoria no clima condominial',
            'perfil_destino': 'sindico',
            'prioridade': 50,
        },
        {
            'tipo': 'manutencao',
            'codigo': 'preventiva_urgente',
            'titulo': 'Agendar preventiva do gerador',
            'descricao': 'O gerador nao recebe manutencao ha 8 meses. Recomendamos inspecao preventiva urgente.',
            'contexto': 'Periodo sem manutencao acima do recomendado pelo fabricante.',
            'beneficio_estimado': 'Evitar falha em emergencia',
            'perfil_destino': 'admin',
            'prioridade': 90,
        },
        {
            'tipo': 'seguranca',
            'codigo': 'atualizar_cadastro',
            'titulo': 'Atualizar cadastros desatualizados',
            'descricao': '12 moradores estao com cadastro desatualizado ha mais de 1 ano. Isso pode comprometer a seguranca.',
            'contexto': 'Auditoria automatica de cadastros do sistema de acesso.',
            'beneficio_estimado': 'Controle de acesso mais seguro',
            'perfil_destino': 'porteiro',
            'prioridade': 80,
        },
    ]

    with engine.connect() as conn:
        # Limpar dados antigos de teste
        conn.execute(text(f"DELETE FROM conecta.sugestoes WHERE condominio_id = '{CONDOMINIO_ID}'"))

        for s in sugestoes:
            sql = text("""
                INSERT INTO conecta.sugestoes (
                    tipo, codigo, titulo, descricao, contexto, beneficio_estimado,
                    perfil_destino, prioridade, status, condominio_id, modelo_versao,
                    created_at, expires_at
                ) VALUES (
                    :tipo, :codigo, :titulo, :descricao, :contexto, :beneficio_estimado,
                    :perfil_destino, :prioridade, 'pendente', :condominio_id, 'v1.0.0',
                    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP + INTERVAL '30 days'
                )
            """)
            conn.execute(sql, {**s, 'condominio_id': CONDOMINIO_ID})

        conn.commit()
    print(f"Inseridas {len(sugestoes)} sugestoes de teste")

def main():
    print("=" * 50)
    print("Seed de Dados Q2 - Conecta Plus")
    print("=" * 50)

    try:
        criar_schema()
        criar_tabelas_q2()
        inserir_previsoes()
        inserir_sugestoes()
        print("\n" + "=" * 50)
        print("Dados de teste inseridos com sucesso!")
        print("=" * 50)
    except Exception as e:
        print(f"\nErro: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
