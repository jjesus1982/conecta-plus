"""
Conecta Plus - Database Tools
Ferramentas para operações de banco de dados
"""

import asyncio
import logging
import json
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum

from .base_tool import (
    BaseTool, ToolContext, ToolResult, ToolMetadata,
    ToolCategory, ToolParameter, ParameterType, tool
)

logger = logging.getLogger(__name__)


class DatabaseType(Enum):
    """Tipos de banco de dados"""
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    MONGODB = "mongodb"
    REDIS = "redis"
    SQLITE = "sqlite"


@dataclass
class QueryResult:
    """Resultado de query"""
    rows: List[Dict[str, Any]]
    row_count: int
    columns: List[str]
    execution_time_ms: float


# ============================================================
# Query Tool
# ============================================================

@tool(
    name="db_query",
    version="1.0.0",
    category=ToolCategory.DATABASE,
    description="Executa consultas SELECT no banco de dados",
    parameters=[
        ToolParameter("query", ParameterType.STRING, "Query SQL", required=True),
        ToolParameter("params", ParameterType.OBJECT, "Parâmetros da query", required=False),
        ToolParameter("database", ParameterType.STRING, "Nome do banco", required=False, default="default"),
        ToolParameter("limit", ParameterType.INTEGER, "Limite de registros", required=False, default=100, max_value=1000),
    ],
    tags=["database", "query", "select", "read"]
)
class QueryTool(BaseTool):
    """
    Ferramenta para executar consultas SELECT.
    Suporta queries parametrizadas e paginação.
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self._connection_pool: Dict[str, Any] = {}

    async def _execute(self, context: ToolContext, **params) -> ToolResult:
        """Executa query SELECT"""
        query = params.get("query", "")
        query_params = params.get("params", {})
        database = params.get("database", "default")
        limit = params.get("limit", 100)

        # Validar query (apenas SELECT permitido)
        query_upper = query.strip().upper()
        if not query_upper.startswith("SELECT"):
            return ToolResult.fail(
                "Apenas queries SELECT são permitidas nesta ferramenta",
                error_code="INVALID_QUERY"
            )

        # Prevenir SQL injection básico
        forbidden = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE", "--", ";"]
        for word in forbidden:
            if word in query_upper:
                return ToolResult.fail(
                    f"Query contém palavra proibida: {word}",
                    error_code="SQL_INJECTION_ATTEMPT"
                )

        # Adicionar LIMIT se não existir
        if "LIMIT" not in query_upper:
            query = f"{query} LIMIT {limit}"

        # Simular execução (em produção, usaria conexão real)
        result = await self._simulate_query(query, query_params, database)

        return ToolResult.ok({
            "rows": result.rows,
            "row_count": result.row_count,
            "columns": result.columns,
            "query": query,
            "database": database
        })

    async def _simulate_query(
        self,
        query: str,
        params: Dict,
        database: str
    ) -> QueryResult:
        """Simula execução de query"""
        # Em produção, conectaria ao banco real
        sample_rows = [
            {"id": 1, "nome": "Exemplo 1", "status": "ativo"},
            {"id": 2, "nome": "Exemplo 2", "status": "inativo"}
        ]

        return QueryResult(
            rows=sample_rows,
            row_count=len(sample_rows),
            columns=["id", "nome", "status"],
            execution_time_ms=15.5
        )


# ============================================================
# Insert Tool
# ============================================================

@tool(
    name="db_insert",
    version="1.0.0",
    category=ToolCategory.DATABASE,
    description="Insere registros no banco de dados",
    parameters=[
        ToolParameter("table", ParameterType.STRING, "Nome da tabela", required=True),
        ToolParameter("data", ParameterType.OBJECT, "Dados a inserir", required=True),
        ToolParameter("database", ParameterType.STRING, "Nome do banco", required=False, default="default"),
        ToolParameter("returning", ParameterType.ARRAY, "Colunas para retornar", required=False),
    ],
    tags=["database", "insert", "write"],
    required_permissions=["db_write"]
)
class InsertTool(BaseTool):
    """
    Ferramenta para inserir registros.
    Suporta insert único e em lote.
    """

    async def _execute(self, context: ToolContext, **params) -> ToolResult:
        """Executa INSERT"""
        table = params.get("table")
        data = params.get("data")
        database = params.get("database", "default")
        returning = params.get("returning", ["id"])

        if not table or not data:
            return ToolResult.fail("'table' e 'data' são obrigatórios")

        # Validar nome da tabela (prevenir injection)
        if not table.replace("_", "").isalnum():
            return ToolResult.fail("Nome de tabela inválido", error_code="INVALID_TABLE")

        # Verificar se é insert em lote
        is_batch = isinstance(data, list)
        records = data if is_batch else [data]

        # Simular insert
        inserted_ids = []
        for i, record in enumerate(records):
            inserted_id = hash(f"{table}{json.dumps(record, sort_keys=True)}{datetime.now()}") % 1000000
            inserted_ids.append(inserted_id)

        result = {
            "table": table,
            "inserted_count": len(records),
            "database": database
        }

        if returning:
            if is_batch:
                result["inserted_ids"] = inserted_ids
            else:
                result["inserted_id"] = inserted_ids[0]

        return ToolResult.ok(result)


# ============================================================
# Update Tool
# ============================================================

@tool(
    name="db_update",
    version="1.0.0",
    category=ToolCategory.DATABASE,
    description="Atualiza registros no banco de dados",
    parameters=[
        ToolParameter("table", ParameterType.STRING, "Nome da tabela", required=True),
        ToolParameter("data", ParameterType.OBJECT, "Dados a atualizar", required=True),
        ToolParameter("where", ParameterType.OBJECT, "Condições WHERE", required=True),
        ToolParameter("database", ParameterType.STRING, "Nome do banco", required=False, default="default"),
    ],
    tags=["database", "update", "write"],
    required_permissions=["db_write"]
)
class UpdateTool(BaseTool):
    """
    Ferramenta para atualizar registros.
    Requer condição WHERE para evitar updates acidentais.
    """

    async def _execute(self, context: ToolContext, **params) -> ToolResult:
        """Executa UPDATE"""
        table = params.get("table")
        data = params.get("data")
        where = params.get("where")
        database = params.get("database", "default")

        if not table or not data or not where:
            return ToolResult.fail("'table', 'data' e 'where' são obrigatórios")

        # Validar nome da tabela
        if not table.replace("_", "").isalnum():
            return ToolResult.fail("Nome de tabela inválido")

        # WHERE obrigatório para segurança
        if not where:
            return ToolResult.fail(
                "WHERE é obrigatório para UPDATE",
                error_code="MISSING_WHERE"
            )

        # Simular update
        affected_rows = 1  # Simulado

        return ToolResult.ok({
            "table": table,
            "affected_rows": affected_rows,
            "where": where,
            "database": database
        })


# ============================================================
# Delete Tool
# ============================================================

@tool(
    name="db_delete",
    version="1.0.0",
    category=ToolCategory.DATABASE,
    description="Remove registros do banco de dados",
    parameters=[
        ToolParameter("table", ParameterType.STRING, "Nome da tabela", required=True),
        ToolParameter("where", ParameterType.OBJECT, "Condições WHERE", required=True),
        ToolParameter("database", ParameterType.STRING, "Nome do banco", required=False, default="default"),
        ToolParameter("soft_delete", ParameterType.BOOLEAN, "Soft delete (marcar como deletado)", required=False, default=True),
    ],
    tags=["database", "delete", "write"],
    required_permissions=["db_delete"]
)
class DeleteTool(BaseTool):
    """
    Ferramenta para remover registros.
    Suporta soft delete (marca como deletado) por padrão.
    """

    async def _execute(self, context: ToolContext, **params) -> ToolResult:
        """Executa DELETE"""
        table = params.get("table")
        where = params.get("where")
        database = params.get("database", "default")
        soft_delete = params.get("soft_delete", True)

        if not table or not where:
            return ToolResult.fail("'table' e 'where' são obrigatórios")

        # Validar nome da tabela
        if not table.replace("_", "").isalnum():
            return ToolResult.fail("Nome de tabela inválido")

        # WHERE obrigatório
        if not where:
            return ToolResult.fail(
                "WHERE é obrigatório para DELETE",
                error_code="MISSING_WHERE"
            )

        # Simular delete
        affected_rows = 1  # Simulado

        action = "soft_deleted" if soft_delete else "deleted"

        return ToolResult.ok({
            "table": table,
            "affected_rows": affected_rows,
            "action": action,
            "where": where,
            "database": database
        })


# ============================================================
# Transaction Tool
# ============================================================

@dataclass
class Transaction:
    """Transação de banco de dados"""
    transaction_id: str
    database: str
    operations: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "open"
    created_at: datetime = field(default_factory=datetime.now)


@tool(
    name="db_transaction",
    version="1.0.0",
    category=ToolCategory.DATABASE,
    description="Gerencia transações de banco de dados",
    parameters=[
        ToolParameter("action", ParameterType.ENUM, "Ação da transação",
                     required=True, enum_values=["begin", "commit", "rollback", "execute"]),
        ToolParameter("transaction_id", ParameterType.STRING, "ID da transação", required=False),
        ToolParameter("operations", ParameterType.ARRAY, "Operações a executar", required=False),
        ToolParameter("database", ParameterType.STRING, "Nome do banco", required=False, default="default"),
    ],
    tags=["database", "transaction", "acid"],
    required_permissions=["db_write"]
)
class TransactionTool(BaseTool):
    """
    Ferramenta para gerenciar transações.
    Suporta begin, commit, rollback e execução atômica.
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self._transactions: Dict[str, Transaction] = {}

    async def _execute(self, context: ToolContext, **params) -> ToolResult:
        """Gerencia transação"""
        action = params.get("action")
        transaction_id = params.get("transaction_id")
        database = params.get("database", "default")

        if action == "begin":
            return await self._begin_transaction(database)

        elif action == "commit":
            if not transaction_id:
                return ToolResult.fail("'transaction_id' é obrigatório para commit")
            return await self._commit_transaction(transaction_id)

        elif action == "rollback":
            if not transaction_id:
                return ToolResult.fail("'transaction_id' é obrigatório para rollback")
            return await self._rollback_transaction(transaction_id)

        elif action == "execute":
            operations = params.get("operations", [])
            if not operations:
                return ToolResult.fail("'operations' é obrigatório para execute")
            return await self._execute_atomic(database, operations)

        else:
            return ToolResult.fail(f"Ação desconhecida: {action}")

    async def _begin_transaction(self, database: str) -> ToolResult:
        """Inicia transação"""
        tx_id = f"tx_{hashlib.md5(f'{database}{datetime.now()}'.encode()).hexdigest()[:12]}"

        transaction = Transaction(
            transaction_id=tx_id,
            database=database
        )

        self._transactions[tx_id] = transaction

        return ToolResult.ok({
            "transaction_id": tx_id,
            "database": database,
            "status": "open"
        })

    async def _commit_transaction(self, transaction_id: str) -> ToolResult:
        """Commita transação"""
        tx = self._transactions.get(transaction_id)
        if not tx:
            return ToolResult.fail(f"Transação não encontrada: {transaction_id}")

        if tx.status != "open":
            return ToolResult.fail(f"Transação não está aberta: {tx.status}")

        tx.status = "committed"

        return ToolResult.ok({
            "transaction_id": transaction_id,
            "status": "committed",
            "operations_count": len(tx.operations)
        })

    async def _rollback_transaction(self, transaction_id: str) -> ToolResult:
        """Rollback de transação"""
        tx = self._transactions.get(transaction_id)
        if not tx:
            return ToolResult.fail(f"Transação não encontrada: {transaction_id}")

        tx.status = "rolled_back"

        return ToolResult.ok({
            "transaction_id": transaction_id,
            "status": "rolled_back"
        })

    async def _execute_atomic(
        self,
        database: str,
        operations: List[Dict]
    ) -> ToolResult:
        """Executa operações atomicamente"""
        # Iniciar transação
        begin_result = await self._begin_transaction(database)
        if not begin_result.success:
            return begin_result

        tx_id = begin_result.data["transaction_id"]
        tx = self._transactions[tx_id]

        results = []
        try:
            for op in operations:
                # Simular execução de cada operação
                op_result = {
                    "type": op.get("type"),
                    "success": True,
                    "affected_rows": 1
                }
                results.append(op_result)
                tx.operations.append(op)

            # Commit
            await self._commit_transaction(tx_id)

            return ToolResult.ok({
                "transaction_id": tx_id,
                "status": "committed",
                "operations": results
            })

        except Exception as e:
            # Rollback em caso de erro
            await self._rollback_transaction(tx_id)
            return ToolResult.fail(
                f"Erro na transação, rollback executado: {str(e)}",
                error_code="TRANSACTION_FAILED"
            )


# ============================================================
# Migration Tool
# ============================================================

@dataclass
class Migration:
    """Migração de banco de dados"""
    migration_id: str
    name: str
    version: str
    up_sql: str
    down_sql: str
    status: str = "pending"
    executed_at: Optional[datetime] = None


@tool(
    name="db_migration",
    version="1.0.0",
    category=ToolCategory.DATABASE,
    description="Gerencia migrações de banco de dados",
    parameters=[
        ToolParameter("action", ParameterType.ENUM, "Ação de migração",
                     required=True, enum_values=["status", "up", "down", "create", "history"]),
        ToolParameter("migration_name", ParameterType.STRING, "Nome da migração", required=False),
        ToolParameter("steps", ParameterType.INTEGER, "Número de passos", required=False, default=1),
        ToolParameter("database", ParameterType.STRING, "Nome do banco", required=False, default="default"),
    ],
    tags=["database", "migration", "schema"],
    required_permissions=["db_admin"]
)
class MigrationTool(BaseTool):
    """
    Ferramenta para gerenciar migrações de schema.
    Suporta up, down, status e criação de migrações.
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self._migrations: Dict[str, Migration] = {}
        self._executed: List[str] = []

    async def _execute(self, context: ToolContext, **params) -> ToolResult:
        """Executa ação de migração"""
        action = params.get("action")
        database = params.get("database", "default")

        if action == "status":
            return await self._get_status(database)
        elif action == "up":
            steps = params.get("steps", 1)
            return await self._migrate_up(database, steps)
        elif action == "down":
            steps = params.get("steps", 1)
            return await self._migrate_down(database, steps)
        elif action == "create":
            name = params.get("migration_name")
            if not name:
                return ToolResult.fail("'migration_name' é obrigatório para criar migração")
            return await self._create_migration(name)
        elif action == "history":
            return await self._get_history(database)
        else:
            return ToolResult.fail(f"Ação desconhecida: {action}")

    async def _get_status(self, database: str) -> ToolResult:
        """Retorna status das migrações"""
        pending = [
            {"id": m.migration_id, "name": m.name, "version": m.version}
            for m in self._migrations.values()
            if m.status == "pending"
        ]

        executed = [
            {"id": mid, "executed_at": datetime.now().isoformat()}
            for mid in self._executed
        ]

        return ToolResult.ok({
            "database": database,
            "pending_count": len(pending),
            "executed_count": len(executed),
            "pending": pending,
            "last_executed": executed[-1] if executed else None
        })

    async def _migrate_up(self, database: str, steps: int) -> ToolResult:
        """Executa migrações pendentes"""
        pending = [
            m for m in self._migrations.values()
            if m.status == "pending"
        ][:steps]

        executed = []
        for migration in pending:
            migration.status = "executed"
            migration.executed_at = datetime.now()
            self._executed.append(migration.migration_id)
            executed.append({
                "id": migration.migration_id,
                "name": migration.name
            })

        return ToolResult.ok({
            "database": database,
            "executed_count": len(executed),
            "executed": executed
        })

    async def _migrate_down(self, database: str, steps: int) -> ToolResult:
        """Reverte migrações"""
        to_revert = self._executed[-steps:] if self._executed else []

        reverted = []
        for mid in reversed(to_revert):
            if mid in self._migrations:
                self._migrations[mid].status = "pending"
                self._migrations[mid].executed_at = None
            self._executed.remove(mid)
            reverted.append(mid)

        return ToolResult.ok({
            "database": database,
            "reverted_count": len(reverted),
            "reverted": reverted
        })

    async def _create_migration(self, name: str) -> ToolResult:
        """Cria nova migração"""
        version = datetime.now().strftime("%Y%m%d%H%M%S")
        migration_id = f"{version}_{name}"

        migration = Migration(
            migration_id=migration_id,
            name=name,
            version=version,
            up_sql=f"-- Migration: {name}\n-- Up\n\n",
            down_sql=f"-- Migration: {name}\n-- Down\n\n"
        )

        self._migrations[migration_id] = migration

        return ToolResult.ok({
            "migration_id": migration_id,
            "name": name,
            "version": version,
            "file": f"migrations/{migration_id}.sql"
        })

    async def _get_history(self, database: str) -> ToolResult:
        """Retorna histórico de migrações"""
        history = []
        for mid in self._executed:
            if mid in self._migrations:
                m = self._migrations[mid]
                history.append({
                    "id": m.migration_id,
                    "name": m.name,
                    "version": m.version,
                    "executed_at": m.executed_at.isoformat() if m.executed_at else None
                })

        return ToolResult.ok({
            "database": database,
            "history": history,
            "total": len(history)
        })


# Funções auxiliares
def register_database_tools():
    """Registra todas as ferramentas de banco de dados"""
    pass
