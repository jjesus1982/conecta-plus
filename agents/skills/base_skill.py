"""
Conecta Plus - Base Skill
Classe base e infraestrutura para skills

Skills são unidades modulares de funcionalidade que podem ser:
- Registradas dinamicamente
- Compartilhadas entre agentes
- Versionadas e atualizadas
- Monitoradas e auditadas
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable, Type
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps

logger = logging.getLogger(__name__)


class SkillStatus(Enum):
    """Status de uma skill"""
    ACTIVE = "active"
    DISABLED = "disabled"
    DEPRECATED = "deprecated"
    ERROR = "error"


class SkillCategory(Enum):
    """Categorias de skills"""
    COMMUNICATION = "communication"
    ANALYSIS = "analysis"
    INTEGRATION = "integration"
    DOCUMENT = "document"
    WORKFLOW = "workflow"
    SECURITY = "security"
    DATA = "data"
    UTILITY = "utility"


@dataclass
class SkillContext:
    """Contexto de execução de uma skill"""
    agent_id: str
    condominio_id: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    conversation_id: Optional[str] = None

    # Configurações
    config: Dict[str, Any] = field(default_factory=dict)

    # Dados compartilhados
    shared_data: Dict[str, Any] = field(default_factory=dict)

    # Permissões
    permissions: List[str] = field(default_factory=list)

    # Metadados
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Timestamp
    timestamp: datetime = field(default_factory=datetime.now)

    def has_permission(self, permission: str) -> bool:
        """Verifica se tem permissão"""
        return permission in self.permissions or "admin" in self.permissions

    def get_config(self, key: str, default: Any = None) -> Any:
        """Retorna configuração"""
        return self.config.get(key, default)


@dataclass
class SkillResult:
    """Resultado de execução de uma skill"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    error_code: Optional[str] = None

    # Metadados de execução
    execution_time_ms: float = 0
    skill_name: str = ""
    skill_version: str = ""

    # Ações sugeridas
    suggested_actions: List[str] = field(default_factory=list)

    # Logs e debug
    logs: List[str] = field(default_factory=list)
    debug_info: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def ok(cls, data: Any = None, **kwargs) -> "SkillResult":
        """Cria resultado de sucesso"""
        return cls(success=True, data=data, **kwargs)

    @classmethod
    def fail(cls, error: str, error_code: str = None, **kwargs) -> "SkillResult":
        """Cria resultado de falha"""
        return cls(success=False, error=error, error_code=error_code, **kwargs)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "error_code": self.error_code,
            "execution_time_ms": self.execution_time_ms,
            "skill_name": self.skill_name,
        }


@dataclass
class SkillMetadata:
    """Metadados de uma skill"""
    name: str
    version: str
    description: str
    category: SkillCategory

    # Autor e manutenção
    author: str = "system"
    maintainer: str = ""

    # Dependências
    dependencies: List[str] = field(default_factory=list)
    required_permissions: List[str] = field(default_factory=list)
    required_tools: List[str] = field(default_factory=list)

    # Configuração
    config_schema: Dict[str, Any] = field(default_factory=dict)
    default_config: Dict[str, Any] = field(default_factory=dict)

    # Documentação
    usage_examples: List[str] = field(default_factory=list)
    documentation_url: Optional[str] = None

    # Tags para busca
    tags: List[str] = field(default_factory=list)


class BaseSkill(ABC):
    """
    Classe base para todas as skills.

    Uma skill encapsula uma funcionalidade específica que pode ser
    reutilizada por diferentes agentes.
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self._status = SkillStatus.ACTIVE
        self._execution_count = 0
        self._error_count = 0
        self._total_execution_time = 0
        self._last_execution: Optional[datetime] = None
        self._initialized = False

    @property
    @abstractmethod
    def metadata(self) -> SkillMetadata:
        """Retorna metadados da skill"""
        pass

    @property
    def name(self) -> str:
        return self.metadata.name

    @property
    def version(self) -> str:
        return self.metadata.version

    @property
    def category(self) -> SkillCategory:
        return self.metadata.category

    @property
    def status(self) -> SkillStatus:
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
        }

    async def initialize(self) -> bool:
        """Inicializa a skill (conexões, recursos, etc.)"""
        try:
            await self._on_initialize()
            self._initialized = True
            logger.info(f"Skill {self.name} inicializada")
            return True
        except Exception as e:
            logger.error(f"Erro ao inicializar skill {self.name}: {e}")
            self._status = SkillStatus.ERROR
            return False

    async def _on_initialize(self):
        """Override para inicialização customizada"""
        pass

    async def shutdown(self):
        """Desliga a skill"""
        try:
            await self._on_shutdown()
            self._initialized = False
            logger.info(f"Skill {self.name} desligada")
        except Exception as e:
            logger.error(f"Erro ao desligar skill {self.name}: {e}")

    async def _on_shutdown(self):
        """Override para shutdown customizado"""
        pass

    async def execute(self, context: SkillContext, **params) -> SkillResult:
        """
        Executa a skill.

        Args:
            context: Contexto de execução
            **params: Parâmetros específicos da skill

        Returns:
            SkillResult com o resultado da execução
        """
        if self._status != SkillStatus.ACTIVE:
            return SkillResult.fail(
                f"Skill {self.name} não está ativa (status: {self._status.value})",
                error_code="SKILL_INACTIVE"
            )

        if not self._initialized:
            await self.initialize()

        # Verificar permissões
        for perm in self.metadata.required_permissions:
            if not context.has_permission(perm):
                return SkillResult.fail(
                    f"Permissão requerida: {perm}",
                    error_code="PERMISSION_DENIED"
                )

        # Executar com métricas
        start_time = time.time()
        self._execution_count += 1
        self._last_execution = datetime.now()

        try:
            result = await self._execute(context, **params)
            result.skill_name = self.name
            result.skill_version = self.version

        except Exception as e:
            self._error_count += 1
            logger.error(f"Erro na skill {self.name}: {e}")
            result = SkillResult.fail(str(e), error_code="EXECUTION_ERROR")

        execution_time = (time.time() - start_time) * 1000
        result.execution_time_ms = execution_time
        self._total_execution_time += execution_time

        return result

    @abstractmethod
    async def _execute(self, context: SkillContext, **params) -> SkillResult:
        """Implementação da execução da skill"""
        pass

    def validate_params(self, params: Dict[str, Any]) -> Optional[str]:
        """Valida parâmetros de entrada"""
        # Override para validação customizada
        return None

    def get_config(self, key: str, default: Any = None) -> Any:
        """Retorna configuração"""
        return self.config.get(key, self.metadata.default_config.get(key, default))

    def to_dict(self) -> Dict[str, Any]:
        """Serializa skill para dict"""
        return {
            "name": self.name,
            "version": self.version,
            "category": self.category.value,
            "description": self.metadata.description,
            "status": self._status.value,
            "tags": self.metadata.tags,
            "stats": self.stats,
        }


class SkillRegistry:
    """
    Registro central de skills.
    Gerencia descoberta, carregamento e acesso às skills.
    """

    _instance = None
    _skills: Dict[str, BaseSkill] = {}
    _by_category: Dict[SkillCategory, List[str]] = {}
    _by_tag: Dict[str, List[str]] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._skills = {}
            cls._by_category = {cat: [] for cat in SkillCategory}
            cls._by_tag = {}
        return cls._instance

    @classmethod
    def register(cls, skill: BaseSkill) -> bool:
        """Registra uma skill"""
        registry = cls()

        if skill.name in registry._skills:
            logger.warning(f"Skill {skill.name} já registrada, substituindo...")

        registry._skills[skill.name] = skill
        registry._by_category[skill.category].append(skill.name)

        for tag in skill.metadata.tags:
            if tag not in registry._by_tag:
                registry._by_tag[tag] = []
            registry._by_tag[tag].append(skill.name)

        logger.info(f"Skill registrada: {skill.name} v{skill.version}")
        return True

    @classmethod
    def get(cls, name: str) -> Optional[BaseSkill]:
        """Retorna skill por nome"""
        return cls()._skills.get(name)

    @classmethod
    def get_by_category(cls, category: SkillCategory) -> List[BaseSkill]:
        """Retorna skills por categoria"""
        registry = cls()
        names = registry._by_category.get(category, [])
        return [registry._skills[n] for n in names if n in registry._skills]

    @classmethod
    def get_by_tag(cls, tag: str) -> List[BaseSkill]:
        """Retorna skills por tag"""
        registry = cls()
        names = registry._by_tag.get(tag, [])
        return [registry._skills[n] for n in names if n in registry._skills]

    @classmethod
    def search(cls, query: str) -> List[BaseSkill]:
        """Busca skills por nome ou descrição"""
        registry = cls()
        query_lower = query.lower()

        results = []
        for skill in registry._skills.values():
            if (query_lower in skill.name.lower() or
                query_lower in skill.metadata.description.lower() or
                any(query_lower in tag for tag in skill.metadata.tags)):
                results.append(skill)

        return results

    @classmethod
    def list_all(cls) -> List[Dict[str, Any]]:
        """Lista todas as skills"""
        return [skill.to_dict() for skill in cls()._skills.values()]

    @classmethod
    async def initialize_all(cls):
        """Inicializa todas as skills"""
        for skill in cls()._skills.values():
            await skill.initialize()

    @classmethod
    async def shutdown_all(cls):
        """Desliga todas as skills"""
        for skill in cls()._skills.values():
            await skill.shutdown()


def skill(
    name: str,
    version: str = "1.0.0",
    category: SkillCategory = SkillCategory.UTILITY,
    description: str = "",
    auto_register: bool = True,
    **metadata_kwargs
):
    """
    Decorator para registrar uma classe como skill.

    Exemplo:
        @skill("my_skill", version="1.0.0", category=SkillCategory.ANALYSIS)
        class MySkill(BaseSkill):
            async def _execute(self, context, **params):
                return SkillResult.ok({"result": "done"})
    """
    def decorator(cls: Type[BaseSkill]):
        # Criar metadata
        meta = SkillMetadata(
            name=name,
            version=version,
            category=category,
            description=description or cls.__doc__ or "",
            **metadata_kwargs
        )

        # Armazenar metadata na classe
        cls._skill_metadata = meta

        # Sobrescrever property de metadata para retornar o metadata armazenado
        @property
        def metadata_property(self) -> SkillMetadata:
            return self.__class__._skill_metadata

        cls.metadata = metadata_property

        # Registrar automaticamente se solicitado
        if auto_register:
            try:
                instance = cls()
                SkillRegistry.register(instance)
            except Exception as e:
                logger.warning(f"Não foi possível auto-registrar skill {name}: {e}")

        return cls

    return decorator


class CompositeSkill(BaseSkill):
    """
    Skill composta que combina múltiplas skills.
    Útil para criar pipelines de processamento.
    """

    def __init__(self, skills: List[BaseSkill], config: Dict[str, Any] = None):
        super().__init__(config)
        self.skills = skills
        self._skill_names = [s.name for s in skills]

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name=f"composite_{'_'.join(self._skill_names[:3])}",
            version="1.0.0",
            description=f"Composite skill: {', '.join(self._skill_names)}",
            category=SkillCategory.UTILITY,
            dependencies=self._skill_names,
        )

    async def _execute(self, context: SkillContext, **params) -> SkillResult:
        """Executa skills em sequência, passando resultado entre elas"""
        current_data = params.get("input")
        all_logs = []
        total_time = 0

        for skill in self.skills:
            result = await skill.execute(context, input=current_data, **params)

            all_logs.extend(result.logs)
            total_time += result.execution_time_ms

            if not result.success:
                return SkillResult.fail(
                    f"Falha em {skill.name}: {result.error}",
                    error_code=f"{skill.name}_FAILED",
                    logs=all_logs
                )

            current_data = result.data

        return SkillResult.ok(
            data=current_data,
            logs=all_logs,
            execution_time_ms=total_time
        )


class ConditionalSkill(BaseSkill):
    """
    Skill que executa condicionalmente baseado em uma condição.
    """

    def __init__(
        self,
        condition: Callable[[SkillContext, Dict], bool],
        if_true: BaseSkill,
        if_false: BaseSkill = None,
        config: Dict[str, Any] = None
    ):
        super().__init__(config)
        self.condition = condition
        self.if_true = if_true
        self.if_false = if_false

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name=f"conditional_{self.if_true.name}",
            version="1.0.0",
            description=f"Conditional execution of {self.if_true.name}",
            category=SkillCategory.UTILITY,
        )

    async def _execute(self, context: SkillContext, **params) -> SkillResult:
        if self.condition(context, params):
            return await self.if_true.execute(context, **params)
        elif self.if_false:
            return await self.if_false.execute(context, **params)
        else:
            return SkillResult.ok(data=None, logs=["Condition not met, skipped"])


class RetryableSkill(BaseSkill):
    """
    Wrapper que adiciona retry a uma skill.
    """

    def __init__(
        self,
        skill: BaseSkill,
        max_retries: int = 3,
        delay_seconds: float = 1.0,
        backoff_multiplier: float = 2.0,
        config: Dict[str, Any] = None
    ):
        super().__init__(config)
        self.wrapped_skill = skill
        self.max_retries = max_retries
        self.delay_seconds = delay_seconds
        self.backoff_multiplier = backoff_multiplier

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name=f"retryable_{self.wrapped_skill.name}",
            version=self.wrapped_skill.version,
            description=f"Retryable wrapper for {self.wrapped_skill.name}",
            category=self.wrapped_skill.category,
        )

    async def _execute(self, context: SkillContext, **params) -> SkillResult:
        last_error = None
        delay = self.delay_seconds

        for attempt in range(self.max_retries + 1):
            result = await self.wrapped_skill.execute(context, **params)

            if result.success:
                if attempt > 0:
                    result.logs.append(f"Succeeded after {attempt} retries")
                return result

            last_error = result.error

            if attempt < self.max_retries:
                await asyncio.sleep(delay)
                delay *= self.backoff_multiplier

        return SkillResult.fail(
            f"Failed after {self.max_retries} retries: {last_error}",
            error_code="MAX_RETRIES_EXCEEDED"
        )
