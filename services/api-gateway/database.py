"""
Conecta Plus - Database Module
Conexão com PostgreSQL usando asyncpg
"""

import asyncpg
import os
from typing import Optional
from contextlib import asynccontextmanager

# Configurações do banco
DATABASE_CONFIG = {
    "host": os.getenv("DB_HOST", "conecta-postgres"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "user": os.getenv("DB_USER", "conecta"),
    "password": os.getenv("DB_PASSWORD", "conecta_pass_2024"),
    "database": os.getenv("DB_NAME", "conecta_plus"),
}

# Pool de conexões global
_pool: Optional[asyncpg.Pool] = None


async def get_pool() -> asyncpg.Pool:
    """Retorna o pool de conexões, criando se necessário"""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            **DATABASE_CONFIG,
            min_size=5,
            max_size=20,
            command_timeout=60,
        )
    return _pool


async def close_pool():
    """Fecha o pool de conexões"""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


@asynccontextmanager
async def get_connection():
    """Context manager para obter uma conexão do pool"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        yield conn


async def execute(query: str, *args):
    """Executa uma query sem retorno"""
    async with get_connection() as conn:
        return await conn.execute(query, *args)


async def fetch(query: str, *args) -> list:
    """Executa uma query e retorna todas as linhas"""
    async with get_connection() as conn:
        return await conn.fetch(query, *args)


async def fetchrow(query: str, *args) -> Optional[asyncpg.Record]:
    """Executa uma query e retorna uma linha"""
    async with get_connection() as conn:
        return await conn.fetchrow(query, *args)


async def fetchval(query: str, *args):
    """Executa uma query e retorna um valor"""
    async with get_connection() as conn:
        return await conn.fetchval(query, *args)


def record_to_dict(record: asyncpg.Record) -> dict:
    """Converte um Record do asyncpg para dict"""
    if record is None:
        return None
    return dict(record)


def records_to_list(records: list) -> list:
    """Converte lista de Records para lista de dicts"""
    return [record_to_dict(r) for r in records]
