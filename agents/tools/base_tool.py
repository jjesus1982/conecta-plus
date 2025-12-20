"""
Conecta Plus - Base Tool
Classe base e infraestrutura para ferramentas

Tools são componentes que:
- Executam ações específicas
- Interagem com sistemas externos
- São usadas pelos agentes para realizar tarefas
- Possuem schema de parâmetros definido
"""

import asyncio
import logging
import time
import json
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable, Type, Union
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps

logger = logging.getLogger(__name__)


class ToolStatus(Enum):
    """Status de uma ferramenta"""
    AVAILABLE = "available"
    BUSY = "busy"
    DISABLED = "disabled"
    ERROR = "error"
    RATE_LIMITED = "rate_limited"


class ToolCategory(Enum):
    """Categorias de ferramentas"""
    DATABASE = "database"
    API = "api"
    DEVICE = "device"
    SEARCH = "search"
    FILE = "file"
    COMMUNICATION = "communication"
    SECURITY = "security"
    UTILITY = "utility"


class ParameterType(Enum):
    """Tipos de parâmetros"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    DATE = "date"
    DATETIME = "datetime"
    FILE = "file"
    ENUM = "enum"


@dataclass
class ToolParameter:
    """Definição de parâmetro de ferramenta"""
    name: str
    type: ParameterType
    description: str
    required: bool = True
    default: Any = None
    enum_values: List[Any] = field(default_factory=list)
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None

    def validate(self, value: Any) -> tuple[bool, Optional[str]]:
        """Valida valor do parâmetro"""
        if value is None:
            if self.required:
                return False, f"Parâmetro obrigatório: {self.name}"
            return True, None

        # Validar tipo
        type_validators = {
            ParameterType.STRING: lambda v: isinstance(v, str),
            ParameterType.INTEGER: lambda v: isinstance(v, int) and not isinstance(v, bool),
            ParameterType.FLOAT: lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
            ParameterType.BOOLEAN: lambda v: isinstance(v, bool),
            ParameterType.ARRAY: lambda v: isinstance(v, list),
            ParameterType.OBJECT: lambda v: isinstance(v, dict),
        }

        validator = type_validators.get(self.type)
        if validator and not validator(value):
            return False, f"Tipo inválido para {self.name}: esperado {self.type.value}"

        # Validar enum
        if self.type == ParameterType.ENUM and self.enum_values:
            if value not in self.enum_values:
                return False, f"Valor inválido para {self.name}: deve ser um de {self.enum_values}"

        # Validar range numérico
        if self.type in [ParameterType.INTEGER, ParameterType.FLOAT]:
            if self.min_value is not None and value < self.min_value:
                return False, f"{self.name} deve ser >= {self.min_value}"
            if self.max_value is not None and value > self.max_value:
                return False, f"{self.name} deve ser <= {self.max_value}"

        # Validar comprimento de string
        if self.type == ParameterType.STRING:
            if self.min_length is not None and len(value) < self.min_length:
                return False, f"{self.name} deve ter pelo menos {self.min_length} caracteres"
            if self.max_length is not None and len(value) > self.max_length:
                return False, f"{self.name} deve ter no máximo {self.max_length} caracteres"

        return True, None

    def to_json_schema(self) -> Dict[str, Any]:
        """Converte para JSON Schema"""
        type_mapping = {
            ParameterType.STRING: "string",
            ParameterType.INTEGER: "integer",
            ParameterType.FLOAT: "number",
            ParameterType.BOOLEAN: "boolean",
            ParameterType.ARRAY: "array",
            ParameterType.OBJECT: "object",
            ParameterType.DATE: "string",
            ParameterType.DATETIME: "string",
            ParameterType.FILE: "string",
            ParameterType.ENUM: "string",
        }

        schema = {
            "type": type_mapping.get(self.type, "string"),
            "description": self.description
        }

        if self.default is not None:
            schema["default"] = self.default

        if self.enum_values:
            schema["enum"] = self.enum_values

        if self.min_value is not None:
            schema["minimum"] = self.min_value
        if self.max_value is not None:
            schema["maximum"] = self.max_value

        if self.min_length is not None:
            schema["minLength"] = self.min_length
        if self.max_length is not None:
            schema["maxLength"] = self.max_length

        if self.pattern:
            schema["pattern"] = self.pattern

        if self.type == ParameterType.DATE:
            schema["format"] = "date"
        elif self.type == ParameterType.DATETIME:
            schema["format"] = "date-time"

        return schema


@dataclass
class ToolContext:
    """Contexto de execução de uma ferramenta"""
    agent_id: str
    condominio_id: str

    # Identificação
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None

    # Configurações
    config: Dict[str, Any] = field(default_factory=dict)

    # Timeout e retry
    timeout_seconds: int = 30
    max_retries: int = 3

    # Permissões
    permissions: List[str] = field(default_factory=list)

    # Metadados
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def has_permission(self, permission: str) -> bool:
        """Verifica se tem permissão"""
        return permission in self.permissions or "admin" in self.permissions

    def get_config(self, key: str, default: Any = None) -> Any:
        """Retorna configuração"""
        return self.config.get(key, default)


@dataclass
class ToolResult:
    """Resultado de execução de uma ferramenta"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    error_code: Optional[str] = None

    # Metadados de execução
    execution_time_ms: float = 0
    tool_name: str = ""
    retries: int = 0

    # Dados adicionais
    metadata: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    @classmethod
    def ok(cls, data: Any = None, **kwargs) -> "ToolResult":
        """Cria resultado de sucesso"""
        return cls(success=True, data=data, **kwargs)

    @classmethod
    def fail(cls, error: str, error_code: str = None, **kwargs) -> "ToolResult":
        """Cria resultado de falha"""
        return cls(success=False, error=error, error_code=error_code, **kwargs)

    def to_dict(self) -> Dict[str, Any]:
        """Serializa para dict"""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "error_code": self.error_code,
            "execution_time_ms": self.execution_time_ms,
            "tool_name": self.tool_name,
            "warnings": self.warnings
        }

    def to_json(self) -> str:
        """Serializa para JSON"""
        return json.dumps(self.to_dict(), default=str)


@dataclass
class ToolMetadata:
    """Metadados de uma ferramenta"""
    name: str
    version: str
    description: str
    category: ToolCategory

    # Parâmetros
    parameters: List[ToolParameter] = field(default_factory=list)

    # Autor e manutenção
    author: str = "system"
    maintainer: str = ""

    # Requisitos
    required_permissions: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)

    # Rate limiting
    rate_limit_per_minute: Optional[int] = None
    rate_limit_per_hour: Optional[int] = None

    # Documentação
    examples: List[Dict[str, Any]] = field(default_factory=list)
    documentation_url: Optional[str] = None

    # Tags
    tags: List[str] = field(default_factory=list)

    def get_json_schema(self) -> Dict[str, Any]:
        """Retorna JSON Schema dos parâmetros"""
        properties = {}
        required = []

        for param in self.parameters:
            properties[param.name] = param.to_json_schema()
            if param.required:
                required.append(param.name)

        return {
            "type": "object",
            "properties": properties,
            "required": required
        }


class BaseTool(ABC):
    """
    Classe base para todas as ferramentas.

    Uma ferramenta executa uma ação específica e retorna um resultado.
    Ferramentas são usadas pelos agentes para interagir com o mundo externo.
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self._status = ToolStatus.AVAILABLE
        self._execution_count = 0
        self._error_count = 0
        self._total_execution_time = 0
        self._last_execution: Optional[datetime] = None
        self._initialized = False

        # Rate limiting
        self._rate_limit_calls: List[datetime] = []

    @property
    @abstractmethod
    def metadata(self) -> ToolMetadata:
        """Retorna metadados da ferramenta"""
        pass

    @property
    def name(self) -> str:
        return self.metadata.name

    @property
    def version(self) -> str:
        return self.metadata.version

    @property
    def category(self) -> ToolCategory:
        return self.metadata.category

    @property
    def parameters(self) -> List[ToolParameter]:
        return self.metadata.parameters

    @property
    def status(self) -> ToolStatus:
        return self._status

    @property
    def stats(self) -> Dict[str, Any]:
        """Estatísticas de execução"""
        return {
            "execution_count": self._execution_count,
            "error_count": self._error_count,
            "error_rate": self._error_count / max(self._execution_count, 1),
            "avg_execution_time_ms": self._total_execution_time / max(self._execution_count, 1),
            "last_execution": self._last_execution.isoformat() if self._last_execution else None,
            "status": self._status.value
        }

    async def initialize(self) -> bool:
        """Inicializa a ferramenta"""
        try:
            await self._on_initialize()
            self._initialized = True
            self._status = ToolStatus.AVAILABLE
            logger.info(f"Tool {self.name} inicializada")
            return True
        except Exception as e:
            logger.error(f"Erro ao inicializar tool {self.name}: {e}")
            self._status = ToolStatus.ERROR
            return False

    async def _on_initialize(self):
        """Override para inicialização customizada"""
        pass

    async def shutdown(self):
        """Desliga a ferramenta"""
        try:
            await self._on_shutdown()
            self._initialized = False
            logger.info(f"Tool {self.name} desligada")
        except Exception as e:
            logger.error(f"Erro ao desligar tool {self.name}: {e}")

    async def _on_shutdown(self):
        """Override para shutdown customizado"""
        pass

    def validate_parameters(self, params: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Valida parâmetros de entrada"""
        errors = []

        for param in self.parameters:
            value = params.get(param.name, param.default)
            is_valid, error = param.validate(value)
            if not is_valid:
                errors.append(error)

        return len(errors) == 0, errors

    def _check_rate_limit(self) -> bool:
        """Verifica rate limit"""
        now = datetime.now()

        # Limpar chamadas antigas
        self._rate_limit_calls = [
            t for t in self._rate_limit_calls
            if (now - t).total_seconds() < 3600
        ]

        # Verificar limite por minuto
        if self.metadata.rate_limit_per_minute:
            recent = [t for t in self._rate_limit_calls if (now - t).total_seconds() < 60]
            if len(recent) >= self.metadata.rate_limit_per_minute:
                return False

        # Verificar limite por hora
        if self.metadata.rate_limit_per_hour:
            if len(self._rate_limit_calls) >= self.metadata.rate_limit_per_hour:
                return False

        return True

    async def execute(self, context: ToolContext, **params) -> ToolResult:
        """
        Executa a ferramenta.

        Args:
            context: Contexto de execução
            **params: Parâmetros específicos da ferramenta

        Returns:
            ToolResult com o resultado da execução
        """
        # Verificar status
        if self._status == ToolStatus.DISABLED:
            return ToolResult.fail(
                f"Tool {self.name} está desabilitada",
                error_code="TOOL_DISABLED"
            )

        if self._status == ToolStatus.ERROR:
            return ToolResult.fail(
                f"Tool {self.name} está em estado de erro",
                error_code="TOOL_ERROR"
            )

        # Verificar rate limit
        if not self._check_rate_limit():
            self._status = ToolStatus.RATE_LIMITED
            return ToolResult.fail(
                f"Rate limit excedido para {self.name}",
                error_code="RATE_LIMITED"
            )

        # Inicializar se necessário
        if not self._initialized:
            if not await self.initialize():
                return ToolResult.fail(
                    f"Falha ao inicializar {self.name}",
                    error_code="INIT_FAILED"
                )

        # Verificar permissões
        for perm in self.metadata.required_permissions:
            if not context.has_permission(perm):
                return ToolResult.fail(
                    f"Permissão requerida: {perm}",
                    error_code="PERMISSION_DENIED"
                )

        # Validar parâmetros
        is_valid, errors = self.validate_parameters(params)
        if not is_valid:
            return ToolResult.fail(
                f"Parâmetros inválidos: {'; '.join(errors)}",
                error_code="INVALID_PARAMS"
            )

        # Executar com métricas
        start_time = time.time()
        self._execution_count += 1
        self._last_execution = datetime.now()
        self._rate_limit_calls.append(self._last_execution)
        self._status = ToolStatus.BUSY

        try:
            result = await asyncio.wait_for(
                self._execute(context, **params),
                timeout=context.timeout_seconds
            )
            result.tool_name = self.name

        except asyncio.TimeoutError:
            self._error_count += 1
            result = ToolResult.fail(
                f"Timeout após {context.timeout_seconds}s",
                error_code="TIMEOUT"
            )

        except Exception as e:
            self._error_count += 1
            logger.error(f"Erro na tool {self.name}: {e}")
            result = ToolResult.fail(str(e), error_code="EXECUTION_ERROR")

        finally:
            self._status = ToolStatus.AVAILABLE

        execution_time = (time.time() - start_time) * 1000
        result.execution_time_ms = execution_time
        self._total_execution_time += execution_time

        return result

    @abstractmethod
    async def _execute(self, context: ToolContext, **params) -> ToolResult:
        """Implementação da execução da ferramenta"""
        pass

    def get_config(self, key: str, default: Any = None) -> Any:
        """Retorna configuração"""
        return self.config.get(key, default)

    def to_dict(self) -> Dict[str, Any]:
        """Serializa para dict"""
        return {
            "name": self.name,
            "version": self.version,
            "category": self.category.value,
            "description": self.metadata.description,
            "status": self._status.value,
            "parameters": [
                {
                    "name": p.name,
                    "type": p.type.value,
                    "required": p.required,
                    "description": p.description
                }
                for p in self.parameters
            ],
            "tags": self.metadata.tags,
            "stats": self.stats
        }

    def to_openai_function(self) -> Dict[str, Any]:
        """Converte para formato de função OpenAI"""
        return {
            "name": self.name,
            "description": self.metadata.description,
            "parameters": self.metadata.get_json_schema()
        }


class ToolRegistry:
    """
    Registro central de ferramentas.
    Gerencia descoberta, carregamento e acesso às ferramentas.
    """

    _instance = None
    _tools: Dict[str, BaseTool] = {}
    _by_category: Dict[ToolCategory, List[str]] = {}
    _by_tag: Dict[str, List[str]] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._tools = {}
            cls._by_category = {cat: [] for cat in ToolCategory}
            cls._by_tag = {}
        return cls._instance

    @classmethod
    def register(cls, tool: BaseTool) -> bool:
        """Registra uma ferramenta"""
        registry = cls()

        if tool.name in registry._tools:
            logger.warning(f"Tool {tool.name} já registrada, substituindo...")
            # Remover das categorias antigas
            old_tool = registry._tools[tool.name]
            if old_tool.name in registry._by_category.get(old_tool.category, []):
                registry._by_category[old_tool.category].remove(old_tool.name)

        registry._tools[tool.name] = tool
        registry._by_category[tool.category].append(tool.name)

        for tag in tool.metadata.tags:
            if tag not in registry._by_tag:
                registry._by_tag[tag] = []
            if tool.name not in registry._by_tag[tag]:
                registry._by_tag[tag].append(tool.name)

        logger.info(f"Tool registrada: {tool.name} v{tool.version}")
        return True

    @classmethod
    def unregister(cls, name: str) -> bool:
        """Remove registro de ferramenta"""
        registry = cls()

        if name not in registry._tools:
            return False

        tool = registry._tools[name]

        # Remover de categorias
        if name in registry._by_category.get(tool.category, []):
            registry._by_category[tool.category].remove(name)

        # Remover de tags
        for tag in tool.metadata.tags:
            if tag in registry._by_tag and name in registry._by_tag[tag]:
                registry._by_tag[tag].remove(name)

        del registry._tools[name]
        logger.info(f"Tool removida: {name}")
        return True

    @classmethod
    def get(cls, name: str) -> Optional[BaseTool]:
        """Retorna ferramenta por nome"""
        return cls()._tools.get(name)

    @classmethod
    def get_by_category(cls, category: ToolCategory) -> List[BaseTool]:
        """Retorna ferramentas por categoria"""
        registry = cls()
        names = registry._by_category.get(category, [])
        return [registry._tools[n] for n in names if n in registry._tools]

    @classmethod
    def get_by_tag(cls, tag: str) -> List[BaseTool]:
        """Retorna ferramentas por tag"""
        registry = cls()
        names = registry._by_tag.get(tag, [])
        return [registry._tools[n] for n in names if n in registry._tools]

    @classmethod
    def search(cls, query: str) -> List[BaseTool]:
        """Busca ferramentas por nome ou descrição"""
        registry = cls()
        query_lower = query.lower()

        results = []
        for tool in registry._tools.values():
            if (query_lower in tool.name.lower() or
                query_lower in tool.metadata.description.lower() or
                any(query_lower in tag for tag in tool.metadata.tags)):
                results.append(tool)

        return results

    @classmethod
    def list_all(cls) -> List[Dict[str, Any]]:
        """Lista todas as ferramentas"""
        return [tool.to_dict() for tool in cls()._tools.values()]

    @classmethod
    def list_available(cls) -> List[Dict[str, Any]]:
        """Lista ferramentas disponíveis"""
        return [
            tool.to_dict() for tool in cls()._tools.values()
            if tool.status == ToolStatus.AVAILABLE
        ]

    @classmethod
    def get_openai_functions(cls) -> List[Dict[str, Any]]:
        """Retorna todas as ferramentas em formato OpenAI"""
        return [
            tool.to_openai_function() for tool in cls()._tools.values()
            if tool.status == ToolStatus.AVAILABLE
        ]

    @classmethod
    async def initialize_all(cls):
        """Inicializa todas as ferramentas"""
        for tool in cls()._tools.values():
            await tool.initialize()

    @classmethod
    async def shutdown_all(cls):
        """Desliga todas as ferramentas"""
        for tool in cls()._tools.values():
            await tool.shutdown()


def tool(
    name: str,
    version: str = "1.0.0",
    category: ToolCategory = ToolCategory.UTILITY,
    description: str = "",
    parameters: List[ToolParameter] = None,
    auto_register: bool = True,
    **metadata_kwargs
):
    """
    Decorator para registrar uma classe como ferramenta.

    Exemplo:
        @tool(
            "my_tool",
            version="1.0.0",
            category=ToolCategory.DATABASE,
            parameters=[
                ToolParameter("query", ParameterType.STRING, "SQL query")
            ]
        )
        class MyTool(BaseTool):
            async def _execute(self, context, **params):
                return ToolResult.ok({"result": "done"})
    """
    def decorator(cls: Type[BaseTool]):
        # Criar metadata
        meta = ToolMetadata(
            name=name,
            version=version,
            category=category,
            description=description or cls.__doc__ or "",
            parameters=parameters or [],
            **metadata_kwargs
        )

        # Armazenar metadata na classe
        cls._tool_metadata = meta

        # Sobrescrever property de metadata para retornar o metadata armazenado
        @property
        def metadata_property(self) -> ToolMetadata:
            return self.__class__._tool_metadata

        cls.metadata = metadata_property

        # Registrar automaticamente se solicitado
        if auto_register:
            try:
                instance = cls()
                ToolRegistry.register(instance)
            except Exception as e:
                logger.warning(f"Não foi possível auto-registrar tool {name}: {e}")

        return cls

    return decorator


class CompositeTool(BaseTool):
    """
    Ferramenta composta que executa múltiplas ferramentas em sequência.
    """

    def __init__(self, tools: List[BaseTool], config: Dict[str, Any] = None):
        super().__init__(config)
        self.tools = tools
        self._tool_names = [t.name for t in tools]

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name=f"composite_{'_'.join(self._tool_names[:3])}",
            version="1.0.0",
            description=f"Composite tool: {', '.join(self._tool_names)}",
            category=ToolCategory.UTILITY,
            dependencies=self._tool_names
        )

    async def _execute(self, context: ToolContext, **params) -> ToolResult:
        """Executa ferramentas em sequência"""
        results = []
        current_data = params.get("input")

        for tool in self.tools:
            result = await tool.execute(context, input=current_data, **params)

            results.append({
                "tool": tool.name,
                "success": result.success,
                "data": result.data
            })

            if not result.success:
                return ToolResult.fail(
                    f"Falha em {tool.name}: {result.error}",
                    error_code=f"{tool.name}_FAILED",
                    metadata={"partial_results": results}
                )

            current_data = result.data

        return ToolResult.ok(
            data=current_data,
            metadata={"results": results}
        )


class ParallelTool(BaseTool):
    """
    Ferramenta que executa múltiplas ferramentas em paralelo.
    """

    def __init__(self, tools: List[BaseTool], config: Dict[str, Any] = None):
        super().__init__(config)
        self.tools = tools
        self._tool_names = [t.name for t in tools]

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name=f"parallel_{'_'.join(self._tool_names[:3])}",
            version="1.0.0",
            description=f"Parallel tool: {', '.join(self._tool_names)}",
            category=ToolCategory.UTILITY
        )

    async def _execute(self, context: ToolContext, **params) -> ToolResult:
        """Executa ferramentas em paralelo"""
        tasks = [
            tool.execute(context, **params)
            for tool in self.tools
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        tool_results = {}
        errors = []

        for tool, result in zip(self.tools, results):
            if isinstance(result, Exception):
                errors.append(f"{tool.name}: {str(result)}")
                tool_results[tool.name] = {"success": False, "error": str(result)}
            else:
                tool_results[tool.name] = {
                    "success": result.success,
                    "data": result.data,
                    "error": result.error
                }
                if not result.success:
                    errors.append(f"{tool.name}: {result.error}")

        success = len(errors) == 0

        return ToolResult(
            success=success,
            data=tool_results,
            error="; ".join(errors) if errors else None,
            warnings=[f"{len(errors)} ferramentas falharam"] if errors else []
        )


class ConditionalTool(BaseTool):
    """
    Ferramenta que executa condicionalmente baseado em uma condição.
    """

    def __init__(
        self,
        condition: Callable[[ToolContext, Dict], bool],
        if_true: BaseTool,
        if_false: BaseTool = None,
        config: Dict[str, Any] = None
    ):
        super().__init__(config)
        self.condition = condition
        self.if_true = if_true
        self.if_false = if_false

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name=f"conditional_{self.if_true.name}",
            version="1.0.0",
            description=f"Conditional execution of {self.if_true.name}",
            category=ToolCategory.UTILITY
        )

    async def _execute(self, context: ToolContext, **params) -> ToolResult:
        if self.condition(context, params):
            return await self.if_true.execute(context, **params)
        elif self.if_false:
            return await self.if_false.execute(context, **params)
        else:
            return ToolResult.ok(data=None, metadata={"skipped": True})


class RetryableTool(BaseTool):
    """
    Wrapper que adiciona retry automático a uma ferramenta.
    """

    def __init__(
        self,
        tool: BaseTool,
        max_retries: int = 3,
        delay_seconds: float = 1.0,
        backoff_multiplier: float = 2.0,
        config: Dict[str, Any] = None
    ):
        super().__init__(config)
        self.wrapped_tool = tool
        self.max_retries = max_retries
        self.delay_seconds = delay_seconds
        self.backoff_multiplier = backoff_multiplier

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name=f"retryable_{self.wrapped_tool.name}",
            version=self.wrapped_tool.version,
            description=f"Retryable wrapper for {self.wrapped_tool.name}",
            category=self.wrapped_tool.category,
            parameters=self.wrapped_tool.parameters
        )

    async def _execute(self, context: ToolContext, **params) -> ToolResult:
        last_error = None
        delay = self.delay_seconds

        for attempt in range(self.max_retries + 1):
            result = await self.wrapped_tool.execute(context, **params)

            if result.success:
                result.retries = attempt
                return result

            last_error = result.error

            if attempt < self.max_retries:
                await asyncio.sleep(delay)
                delay *= self.backoff_multiplier

        return ToolResult.fail(
            f"Falha após {self.max_retries} tentativas: {last_error}",
            error_code="MAX_RETRIES_EXCEEDED",
            metadata={"retries": self.max_retries}
        )
