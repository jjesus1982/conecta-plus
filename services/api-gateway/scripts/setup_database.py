#!/usr/bin/env python3
"""
Conecta Plus - Script de Setup do Banco de Dados
Cria schema, tabelas e dados iniciais
"""

import os
import sys
import asyncio

# Adiciona diretório pai ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine

# URL do banco
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://conecta:conecta123@conecta-postgres:5432/conecta_plus'
)


def setup_sync():
    """Setup síncrono para criação de schema e tabelas"""
    print("[SETUP] Conectando ao banco de dados...")

    # Remove asyncpg se presente
    sync_url = DATABASE_URL.replace('+asyncpg', '')

    engine = create_engine(sync_url, echo=True)

    with engine.connect() as conn:
        # Cria schema
        print("[SETUP] Criando schema financeiro...")
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS financeiro"))
        conn.commit()

        # Verifica se tabelas existem
        result = conn.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'financeiro'
        """))
        existing_tables = [row[0] for row in result.fetchall()]

        print(f"[SETUP] Tabelas existentes: {existing_tables}")

    # Importa modelos e cria tabelas
    print("[SETUP] Importando modelos...")
    from models.financeiro import Base, create_tables

    print("[SETUP] Criando tabelas...")
    create_tables(engine)

    # Verifica tabelas criadas
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'financeiro'
            ORDER BY table_name
        """))
        tables = [row[0] for row in result.fetchall()]

        print(f"[SETUP] Tabelas criadas: {tables}")

    print("[SETUP] Setup concluído com sucesso!")
    return True


def create_indexes():
    """Cria índices adicionais para performance"""
    sync_url = DATABASE_URL.replace('+asyncpg', '')
    engine = create_engine(sync_url)

    indexes = [
        # Índices compostos para queries frequentes
        """
        CREATE INDEX IF NOT EXISTS ix_boletos_condominio_status
        ON financeiro.boletos (condominio_id, status)
        WHERE deleted_at IS NULL
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_boletos_condominio_vencimento
        ON financeiro.boletos (condominio_id, vencimento)
        WHERE deleted_at IS NULL
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_boletos_pagador_hash
        ON financeiro.boletos (pagador_documento_hash)
        WHERE deleted_at IS NULL
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_pagamentos_data_status
        ON financeiro.pagamentos (data_pagamento, status)
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_lancamentos_competencia
        ON financeiro.lancamentos (condominio_id, data_competencia)
        WHERE deleted_at IS NULL
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_audit_logs_created
        ON financeiro.audit_logs (created_at DESC)
        """,
    ]

    with engine.connect() as conn:
        for idx_sql in indexes:
            try:
                conn.execute(text(idx_sql))
                conn.commit()
                print(f"[INDEX] OK: {idx_sql[:50]}...")
            except Exception as e:
                print(f"[INDEX] Erro (pode já existir): {e}")

    print("[SETUP] Índices criados!")


def insert_sample_data():
    """Insere dados de exemplo para desenvolvimento"""
    sync_url = DATABASE_URL.replace('+asyncpg', '')
    engine = create_engine(sync_url)

    with engine.connect() as conn:
        # Verifica se já tem dados
        result = conn.execute(text("SELECT COUNT(*) FROM financeiro.boletos"))
        count = result.scalar()

        if count > 0:
            print(f"[SAMPLE] Já existem {count} boletos. Pulando inserção de dados de exemplo.")
            return

        print("[SAMPLE] Inserindo dados de exemplo...")

        # Insere configuração bancária de exemplo
        conn.execute(text("""
            INSERT INTO financeiro.configuracoes_bancarias
            (id, condominio_id, banco_codigo, banco_nome, agencia, conta, tipo_conta,
             carteira, chave_pix, tipo_chave_pix, beneficiario_nome, beneficiario_documento,
             ativo, homologado, created_at, updated_at)
            VALUES
            (gen_random_uuid(), 'cond_001', '077', 'Banco Inter', '0001', '12345678', 'corrente',
             '112', '12345678901234', 'cnpj', 'Condomínio Residencial Conecta', '12345678000190',
             true, false, NOW(), NOW())
            ON CONFLICT DO NOTHING
        """))
        conn.commit()

        print("[SAMPLE] Dados de exemplo inseridos!")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Setup do banco de dados Conecta Plus')
    parser.add_argument('--indexes', action='store_true', help='Criar índices adicionais')
    parser.add_argument('--sample', action='store_true', help='Inserir dados de exemplo')
    parser.add_argument('--all', action='store_true', help='Executar tudo')

    args = parser.parse_args()

    try:
        # Sempre executa setup básico
        setup_sync()

        if args.indexes or args.all:
            create_indexes()

        if args.sample or args.all:
            insert_sample_data()

        print("\n✅ Setup concluído com sucesso!")

    except Exception as e:
        print(f"\n❌ Erro no setup: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
