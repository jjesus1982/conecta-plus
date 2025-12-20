"""
Conecta Plus - Agent Tools System
Sistema de ferramentas para agentes executarem ações

Categorias:
- Database Tools: CRUD em PostgreSQL
- API Tools: Chamadas a serviços externos
- Notification Tools: Envio de notificações
- Analysis Tools: Análise de dados
- Integration Tools: Integração com MCPs
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Callable, Type
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import asyncio
import json
import logging
import httpx

logger = logging.getLogger(__name__)


class ToolCategory(Enum):
    """Categorias de ferramentas"""
    DATABASE = "database"
    API = "api"
    NOTIFICATION = "notification"
    ANALYSIS = "analysis"
    INTEGRATION = "integration"
    UTILITY = "utility"


@dataclass
class ToolParameter:
    """Parâmetro de ferramenta"""
    name: str
    param_type: str  # string, number, boolean, array, object
    description: str
    required: bool = True
    default: Any = None
    enum: List[Any] = None


@dataclass
class ToolDefinition:
    """Definição de ferramenta"""
    name: str
    description: str
    category: ToolCategory
    parameters: List[ToolParameter] = field(default_factory=list)
    returns: str = "any"
    requires_approval: bool = False
    risk_level: int = 1  # 1-5


@dataclass
class ToolResult:
    """Resultado de execução de ferramenta"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    execution_time_ms: float = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseTool(ABC):
    """Interface base para ferramentas"""

    def __init__(self):
        self._execution_count = 0
        self._last_execution = None

    @property
    @abstractmethod
    def definition(self) -> ToolDefinition:
        """Retorna definição da ferramenta"""
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Executa a ferramenta"""
        pass

    def to_llm_schema(self) -> Dict[str, Any]:
        """Converte para schema de LLM (function calling)"""
        properties = {}
        required = []

        for param in self.definition.parameters:
            prop = {
                "type": param.param_type,
                "description": param.description
            }
            if param.enum:
                prop["enum"] = param.enum
            if param.default is not None:
                prop["default"] = param.default

            properties[param.name] = prop

            if param.required:
                required.append(param.name)

        return {
            "name": self.definition.name,
            "description": self.definition.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required
            }
        }


# ==================== DATABASE TOOLS ====================

class DatabaseQueryTool(BaseTool):
    """Ferramenta para consultas SQL seguras"""

    def __init__(self, db_pool):
        super().__init__()
        self.db_pool = db_pool

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="database_query",
            description="Executa consulta SELECT no banco de dados",
            category=ToolCategory.DATABASE,
            parameters=[
                ToolParameter(
                    name="table",
                    param_type="string",
                    description="Nome da tabela"
                ),
                ToolParameter(
                    name="columns",
                    param_type="array",
                    description="Colunas a selecionar",
                    required=False,
                    default=["*"]
                ),
                ToolParameter(
                    name="where",
                    param_type="object",
                    description="Condições WHERE como {coluna: valor}",
                    required=False
                ),
                ToolParameter(
                    name="limit",
                    param_type="number",
                    description="Limite de resultados",
                    required=False,
                    default=100
                ),
                ToolParameter(
                    name="order_by",
                    param_type="string",
                    description="Coluna para ordenação",
                    required=False
                )
            ],
            returns="array",
            risk_level=2
        )

    async def execute(
        self,
        table: str,
        columns: List[str] = None,
        where: Dict[str, Any] = None,
        limit: int = 100,
        order_by: str = None,
        **kwargs
    ) -> ToolResult:
        """Executa query SELECT"""
        start_time = datetime.now()

        try:
            # Validar tabela (whitelist)
            allowed_tables = [
                'condominios', 'unidades', 'moradores', 'veiculos',
                'financeiro_contas', 'financeiro_lancamentos', 'financeiro_boletos',
                'ocorrencias', 'reservas', 'encomendas', 'comunicados',
                'cameras', 'eventos_acesso', 'alertas'
            ]

            if table not in allowed_tables:
                return ToolResult(
                    success=False,
                    error=f"Tabela '{table}' não permitida"
                )

            # Construir query
            cols = ", ".join(columns) if columns else "*"
            query = f"SELECT {cols} FROM {table}"

            params = []
            if where:
                conditions = []
                for i, (col, val) in enumerate(where.items()):
                    conditions.append(f"{col} = ${i+1}")
                    params.append(val)
                query += " WHERE " + " AND ".join(conditions)

            if order_by:
                query += f" ORDER BY {order_by}"

            query += f" LIMIT {min(limit, 1000)}"

            # Executar
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch(query, *params)
                data = [dict(row) for row in rows]

            execution_time = (datetime.now() - start_time).total_seconds() * 1000

            return ToolResult(
                success=True,
                data=data,
                execution_time_ms=execution_time,
                metadata={"rows_returned": len(data)}
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e)
            )


class DatabaseInsertTool(BaseTool):
    """Ferramenta para inserção no banco"""

    def __init__(self, db_pool):
        super().__init__()
        self.db_pool = db_pool

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="database_insert",
            description="Insere registro no banco de dados",
            category=ToolCategory.DATABASE,
            parameters=[
                ToolParameter(
                    name="table",
                    param_type="string",
                    description="Nome da tabela"
                ),
                ToolParameter(
                    name="data",
                    param_type="object",
                    description="Dados a inserir {coluna: valor}"
                )
            ],
            returns="object",
            requires_approval=True,
            risk_level=3
        )

    async def execute(self, table: str, data: Dict[str, Any], **kwargs) -> ToolResult:
        """Executa INSERT"""
        start_time = datetime.now()

        try:
            columns = list(data.keys())
            values = list(data.values())
            placeholders = [f"${i+1}" for i in range(len(values))]

            query = f"""
                INSERT INTO {table} ({', '.join(columns)})
                VALUES ({', '.join(placeholders)})
                RETURNING id
            """

            async with self.db_pool.acquire() as conn:
                result = await conn.fetchrow(query, *values)

            execution_time = (datetime.now() - start_time).total_seconds() * 1000

            return ToolResult(
                success=True,
                data={"id": result["id"]},
                execution_time_ms=execution_time
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))


class DatabaseUpdateTool(BaseTool):
    """Ferramenta para atualização no banco"""

    def __init__(self, db_pool):
        super().__init__()
        self.db_pool = db_pool

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="database_update",
            description="Atualiza registros no banco de dados",
            category=ToolCategory.DATABASE,
            parameters=[
                ToolParameter(
                    name="table",
                    param_type="string",
                    description="Nome da tabela"
                ),
                ToolParameter(
                    name="data",
                    param_type="object",
                    description="Dados a atualizar {coluna: valor}"
                ),
                ToolParameter(
                    name="where",
                    param_type="object",
                    description="Condições WHERE {coluna: valor}"
                )
            ],
            returns="object",
            requires_approval=True,
            risk_level=4
        )

    async def execute(
        self,
        table: str,
        data: Dict[str, Any],
        where: Dict[str, Any],
        **kwargs
    ) -> ToolResult:
        """Executa UPDATE"""
        start_time = datetime.now()

        try:
            # SET clause
            set_parts = []
            values = []
            for i, (col, val) in enumerate(data.items()):
                set_parts.append(f"{col} = ${i+1}")
                values.append(val)

            # WHERE clause
            where_parts = []
            for i, (col, val) in enumerate(where.items(), len(values) + 1):
                where_parts.append(f"{col} = ${i}")
                values.append(val)

            query = f"""
                UPDATE {table}
                SET {', '.join(set_parts)}
                WHERE {' AND '.join(where_parts)}
            """

            async with self.db_pool.acquire() as conn:
                result = await conn.execute(query, *values)
                rows_affected = int(result.split()[-1])

            execution_time = (datetime.now() - start_time).total_seconds() * 1000

            return ToolResult(
                success=True,
                data={"rows_affected": rows_affected},
                execution_time_ms=execution_time
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))


# ==================== NOTIFICATION TOOLS ====================

class NotificationTool(BaseTool):
    """Ferramenta para enviar notificações"""

    def __init__(self, notification_service_url: str):
        super().__init__()
        self.service_url = notification_service_url

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="send_notification",
            description="Envia notificação para usuários",
            category=ToolCategory.NOTIFICATION,
            parameters=[
                ToolParameter(
                    name="user_ids",
                    param_type="array",
                    description="IDs dos usuários destinatários"
                ),
                ToolParameter(
                    name="title",
                    param_type="string",
                    description="Título da notificação"
                ),
                ToolParameter(
                    name="message",
                    param_type="string",
                    description="Conteúdo da mensagem"
                ),
                ToolParameter(
                    name="channels",
                    param_type="array",
                    description="Canais de envio",
                    required=False,
                    default=["push", "app"],
                    enum=["push", "email", "sms", "whatsapp", "telegram", "app"]
                ),
                ToolParameter(
                    name="priority",
                    param_type="string",
                    description="Prioridade",
                    required=False,
                    default="normal",
                    enum=["low", "normal", "high", "urgent"]
                )
            ],
            returns="object",
            risk_level=2
        )

    async def execute(
        self,
        user_ids: List[str],
        title: str,
        message: str,
        channels: List[str] = None,
        priority: str = "normal",
        **kwargs
    ) -> ToolResult:
        """Envia notificação"""
        start_time = datetime.now()

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.service_url}/notifications/send",
                    json={
                        "user_ids": user_ids,
                        "title": title,
                        "message": message,
                        "channels": channels or ["push", "app"],
                        "priority": priority
                    },
                    timeout=30
                )
                response.raise_for_status()
                data = response.json()

            execution_time = (datetime.now() - start_time).total_seconds() * 1000

            return ToolResult(
                success=True,
                data=data,
                execution_time_ms=execution_time
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))


class WhatsAppTool(BaseTool):
    """Ferramenta para enviar WhatsApp"""

    def __init__(self, whatsapp_api_url: str, api_token: str):
        super().__init__()
        self.api_url = whatsapp_api_url
        self.api_token = api_token

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="send_whatsapp",
            description="Envia mensagem via WhatsApp",
            category=ToolCategory.NOTIFICATION,
            parameters=[
                ToolParameter(
                    name="phone",
                    param_type="string",
                    description="Número do telefone (com DDD)"
                ),
                ToolParameter(
                    name="message",
                    param_type="string",
                    description="Mensagem a enviar"
                ),
                ToolParameter(
                    name="template",
                    param_type="string",
                    description="Nome do template (opcional)",
                    required=False
                )
            ],
            returns="object",
            risk_level=2
        )

    async def execute(
        self,
        phone: str,
        message: str,
        template: str = None,
        **kwargs
    ) -> ToolResult:
        """Envia WhatsApp"""
        start_time = datetime.now()

        try:
            # Formatar número
            phone = phone.replace("-", "").replace(" ", "").replace("(", "").replace(")", "")
            if not phone.startswith("55"):
                phone = "55" + phone

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/messages",
                    headers={"Authorization": f"Bearer {self.api_token}"},
                    json={
                        "to": phone,
                        "type": "text",
                        "text": {"body": message}
                    } if not template else {
                        "to": phone,
                        "type": "template",
                        "template": {"name": template}
                    },
                    timeout=30
                )
                response.raise_for_status()
                data = response.json()

            execution_time = (datetime.now() - start_time).total_seconds() * 1000

            return ToolResult(
                success=True,
                data=data,
                execution_time_ms=execution_time
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))


# ==================== ANALYSIS TOOLS ====================

class DataAnalysisTool(BaseTool):
    """Ferramenta para análise de dados"""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="analyze_data",
            description="Analisa dados e gera estatísticas",
            category=ToolCategory.ANALYSIS,
            parameters=[
                ToolParameter(
                    name="data",
                    param_type="array",
                    description="Array de dados a analisar"
                ),
                ToolParameter(
                    name="analysis_type",
                    param_type="string",
                    description="Tipo de análise",
                    enum=["summary", "trend", "anomaly", "distribution", "correlation"]
                ),
                ToolParameter(
                    name="value_field",
                    param_type="string",
                    description="Campo com valores numéricos"
                ),
                ToolParameter(
                    name="date_field",
                    param_type="string",
                    description="Campo com datas (para trend)",
                    required=False
                )
            ],
            returns="object",
            risk_level=1
        )

    async def execute(
        self,
        data: List[Dict],
        analysis_type: str,
        value_field: str,
        date_field: str = None,
        **kwargs
    ) -> ToolResult:
        """Executa análise"""
        start_time = datetime.now()

        try:
            import statistics

            # Extrair valores
            values = [float(d.get(value_field, 0)) for d in data if d.get(value_field) is not None]

            if not values:
                return ToolResult(
                    success=False,
                    error="Nenhum valor válido encontrado"
                )

            result = {}

            if analysis_type == "summary":
                result = {
                    "count": len(values),
                    "sum": sum(values),
                    "mean": statistics.mean(values),
                    "median": statistics.median(values),
                    "min": min(values),
                    "max": max(values),
                    "stdev": statistics.stdev(values) if len(values) > 1 else 0
                }

            elif analysis_type == "trend":
                # Calcular tendência simples
                if len(values) > 1:
                    first_half = statistics.mean(values[:len(values)//2])
                    second_half = statistics.mean(values[len(values)//2:])
                    trend = "up" if second_half > first_half else "down" if second_half < first_half else "stable"
                    change = ((second_half - first_half) / first_half) * 100 if first_half != 0 else 0

                    result = {
                        "trend": trend,
                        "change_percent": round(change, 2),
                        "first_period_avg": round(first_half, 2),
                        "second_period_avg": round(second_half, 2)
                    }

            elif analysis_type == "anomaly":
                # Detectar anomalias (fora de 2 desvios padrão)
                mean = statistics.mean(values)
                stdev = statistics.stdev(values) if len(values) > 1 else 0

                anomalies = []
                for i, v in enumerate(values):
                    if abs(v - mean) > 2 * stdev:
                        anomalies.append({
                            "index": i,
                            "value": v,
                            "deviation": (v - mean) / stdev if stdev > 0 else 0
                        })

                result = {
                    "anomalies_count": len(anomalies),
                    "anomalies": anomalies,
                    "mean": round(mean, 2),
                    "stdev": round(stdev, 2)
                }

            elif analysis_type == "distribution":
                # Distribuição em quartis
                sorted_values = sorted(values)
                n = len(sorted_values)

                result = {
                    "q1": sorted_values[n//4] if n > 3 else sorted_values[0],
                    "q2": statistics.median(sorted_values),
                    "q3": sorted_values[3*n//4] if n > 3 else sorted_values[-1],
                    "iqr": (sorted_values[3*n//4] - sorted_values[n//4]) if n > 3 else 0
                }

            execution_time = (datetime.now() - start_time).total_seconds() * 1000

            return ToolResult(
                success=True,
                data=result,
                execution_time_ms=execution_time
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))


class PredictionTool(BaseTool):
    """Ferramenta para previsões simples"""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="predict_values",
            description="Faz previsões baseadas em dados históricos",
            category=ToolCategory.ANALYSIS,
            parameters=[
                ToolParameter(
                    name="historical_data",
                    param_type="array",
                    description="Dados históricos [{date: string, value: number}]"
                ),
                ToolParameter(
                    name="periods_ahead",
                    param_type="number",
                    description="Quantos períodos à frente prever",
                    default=3
                ),
                ToolParameter(
                    name="method",
                    param_type="string",
                    description="Método de previsão",
                    enum=["moving_average", "linear", "exponential"],
                    default="moving_average"
                )
            ],
            returns="object",
            risk_level=1
        )

    async def execute(
        self,
        historical_data: List[Dict],
        periods_ahead: int = 3,
        method: str = "moving_average",
        **kwargs
    ) -> ToolResult:
        """Executa previsão"""
        start_time = datetime.now()

        try:
            values = [d.get("value", 0) for d in historical_data]

            if len(values) < 3:
                return ToolResult(
                    success=False,
                    error="Necessário ao menos 3 pontos de dados"
                )

            predictions = []

            if method == "moving_average":
                # Média móvel simples
                window = min(3, len(values))
                last_avg = sum(values[-window:]) / window

                for i in range(periods_ahead):
                    predictions.append(round(last_avg, 2))

            elif method == "linear":
                # Regressão linear simples
                n = len(values)
                x = list(range(n))
                x_mean = sum(x) / n
                y_mean = sum(values) / n

                numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
                denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

                slope = numerator / denominator if denominator != 0 else 0
                intercept = y_mean - slope * x_mean

                for i in range(periods_ahead):
                    pred = intercept + slope * (n + i)
                    predictions.append(round(pred, 2))

            elif method == "exponential":
                # Suavização exponencial
                alpha = 0.3
                smoothed = values[0]

                for v in values[1:]:
                    smoothed = alpha * v + (1 - alpha) * smoothed

                for i in range(periods_ahead):
                    predictions.append(round(smoothed, 2))

            execution_time = (datetime.now() - start_time).total_seconds() * 1000

            return ToolResult(
                success=True,
                data={
                    "predictions": predictions,
                    "method": method,
                    "confidence": 0.7 if len(values) > 10 else 0.5
                },
                execution_time_ms=execution_time
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))


# ==================== INTEGRATION TOOLS ====================

class MCPCallTool(BaseTool):
    """Ferramenta para chamar MCPs de integração"""

    def __init__(self, integration_hub_url: str):
        super().__init__()
        self.hub_url = integration_hub_url

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="call_mcp",
            description="Chama um MCP de integração",
            category=ToolCategory.INTEGRATION,
            parameters=[
                ToolParameter(
                    name="mcp_name",
                    param_type="string",
                    description="Nome do MCP (ex: mcp-intelbras-cftv)"
                ),
                ToolParameter(
                    name="method",
                    param_type="string",
                    description="Método do MCP a chamar"
                ),
                ToolParameter(
                    name="params",
                    param_type="object",
                    description="Parâmetros da chamada",
                    required=False
                )
            ],
            returns="object",
            requires_approval=True,
            risk_level=4
        )

    async def execute(
        self,
        mcp_name: str,
        method: str,
        params: Dict[str, Any] = None,
        **kwargs
    ) -> ToolResult:
        """Chama MCP"""
        start_time = datetime.now()

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.hub_url}/mcp/{mcp_name}/{method}",
                    json=params or {},
                    timeout=60
                )
                response.raise_for_status()
                data = response.json()

            execution_time = (datetime.now() - start_time).total_seconds() * 1000

            return ToolResult(
                success=True,
                data=data,
                execution_time_ms=execution_time
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e))


# ==================== TOOL REGISTRY ====================

class ToolRegistry:
    """Registro e gerenciamento de ferramentas"""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._categories: Dict[ToolCategory, List[str]] = {cat: [] for cat in ToolCategory}

    def register(self, tool: BaseTool) -> None:
        """Registra ferramenta"""
        name = tool.definition.name
        self._tools[name] = tool
        self._categories[tool.definition.category].append(name)
        logger.info(f"Ferramenta '{name}' registrada")

    def get(self, name: str) -> Optional[BaseTool]:
        """Obtém ferramenta por nome"""
        return self._tools.get(name)

    def get_by_category(self, category: ToolCategory) -> List[BaseTool]:
        """Obtém ferramentas por categoria"""
        return [self._tools[name] for name in self._categories.get(category, [])]

    def list_all(self) -> List[ToolDefinition]:
        """Lista todas as definições"""
        return [tool.definition for tool in self._tools.values()]

    def to_llm_tools(self) -> List[Dict[str, Any]]:
        """Exporta todas as tools para formato LLM"""
        return [tool.to_llm_schema() for tool in self._tools.values()]

    async def execute(self, tool_name: str, **params) -> ToolResult:
        """Executa ferramenta por nome"""
        tool = self.get(tool_name)
        if not tool:
            return ToolResult(
                success=False,
                error=f"Ferramenta '{tool_name}' não encontrada"
            )

        return await tool.execute(**params)


# Função factory
def create_standard_tools(
    db_pool=None,
    notification_url: str = None,
    whatsapp_url: str = None,
    whatsapp_token: str = None,
    integration_hub_url: str = None
) -> ToolRegistry:
    """Cria registry com ferramentas padrão"""
    registry = ToolRegistry()

    # Database tools
    if db_pool:
        registry.register(DatabaseQueryTool(db_pool))
        registry.register(DatabaseInsertTool(db_pool))
        registry.register(DatabaseUpdateTool(db_pool))

    # Notification tools
    if notification_url:
        registry.register(NotificationTool(notification_url))
    if whatsapp_url and whatsapp_token:
        registry.register(WhatsAppTool(whatsapp_url, whatsapp_token))

    # Analysis tools (sempre disponíveis)
    registry.register(DataAnalysisTool())
    registry.register(PredictionTool())

    # Integration tools
    if integration_hub_url:
        registry.register(MCPCallTool(integration_hub_url))

    return registry
