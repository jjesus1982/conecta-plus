#!/usr/bin/env python3
"""
Conecta Plus - Script para criar tabelas Q1
Cria as novas tabelas de SLA, DecisionLog e Tranquilidade
"""

import sys
import os

# Adicionar diretório pai ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from database import engine, Base

# Importar TODOS os modelos para registrar no metadata
from models import (
    # Modelos existentes
    Usuario, Condominio, Unidade, Morador, Veiculo,
    RegistroAcesso, PontoAcesso, Ocorrencia, OrdemServico, Fornecedor,
    Lancamento, Boleto, ZonaAlarme, EventoAlarme,
    AreaComum, Reserva, Comunicado, Assembleia, Votacao, Ata,
    # Novos modelos Q1
    SLAConfig, DecisionLog, TranquilidadeSnapshot, RecomendacaoTemplate
)


def create_tables():
    """Cria todas as tabelas no banco de dados."""
    print("=" * 60)
    print("CONECTA PLUS - Criacao de Tabelas Q1")
    print("=" * 60)

    # Verificar conexao
    print("\n1. Verificando conexao com banco de dados...")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"   PostgreSQL: {version[:50]}...")
    except Exception as e:
        print(f"   ERRO: {e}")
        return False

    # Listar tabelas existentes
    print("\n2. Tabelas existentes:")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            tables = [row[0] for row in result]
            for t in tables:
                print(f"   - {t}")
            print(f"   Total: {len(tables)} tabelas")
    except Exception as e:
        print(f"   ERRO: {e}")

    # Criar tabelas novas
    print("\n3. Criando novas tabelas Q1...")

    novas_tabelas = [
        'sla_configs',
        'decision_logs',
        'tranquilidade_snapshots',
        'recomendacao_templates'
    ]

    try:
        # Criar apenas tabelas que nao existem
        Base.metadata.create_all(bind=engine)
        print("   Tabelas criadas/atualizadas com sucesso!")
    except Exception as e:
        print(f"   ERRO ao criar tabelas: {e}")
        return False

    # Verificar tabelas criadas
    print("\n4. Verificando tabelas Q1:")
    try:
        with engine.connect() as conn:
            for tabela in novas_tabelas:
                result = conn.execute(text(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_schema = 'public'
                        AND table_name = '{tabela}'
                    )
                """))
                existe = result.scalar()
                status = "OK" if existe else "NAO ENCONTRADA"
                print(f"   - {tabela}: {status}")
    except Exception as e:
        print(f"   ERRO: {e}")

    # Verificar colunas novas em ocorrencias
    print("\n5. Verificando campos novos em 'ocorrencias':")
    campos_novos = [
        'prazo_estimado', 'prazo_origem', 'sla_config_id',
        'timeline', 'avaliacao_nota', 'avaliacao_comentario',
        'notificacoes_enviadas', 'primeira_resposta_at'
    ]

    try:
        with engine.connect() as conn:
            for campo in campos_novos:
                result = conn.execute(text(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.columns
                        WHERE table_name = 'ocorrencias'
                        AND column_name = '{campo}'
                    )
                """))
                existe = result.scalar()
                status = "OK" if existe else "PENDENTE"
                print(f"   - {campo}: {status}")
    except Exception as e:
        print(f"   ERRO: {e}")

    print("\n" + "=" * 60)
    print("Processo concluido!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = create_tables()
    sys.exit(0 if success else 1)
