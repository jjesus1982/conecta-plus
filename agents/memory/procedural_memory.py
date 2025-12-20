"""
Conecta Plus - Procedural Memory
Memória de procedimentos e habilidades aprendidas

Funcionalidades:
- Armazenamento de procedimentos passo a passo
- Rastreamento de execuções e resultados
- Aprendizado por refinamento
- Sugestão de procedimentos por contexto
- Detecção de padrões de sucesso/falha
"""

import asyncio
import json
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


class SkillLevel(Enum):
    """Nível de habilidade"""
    NOVICE = 1
    BEGINNER = 2
    INTERMEDIATE = 3
    ADVANCED = 4
    EXPERT = 5


class ProcedureType(Enum):
    """Tipos de procedimento"""
    STANDARD = "standard"
    EMERGENCY = "emergency"
    MAINTENANCE = "maintenance"
    TROUBLESHOOTING = "troubleshooting"
    WORKFLOW = "workflow"
    CHECKLIST = "checklist"
    AUTOMATION = "automation"


class StepType(Enum):
    """Tipos de passo"""
    ACTION = "action"
    DECISION = "decision"
    VERIFICATION = "verification"
    WAIT = "wait"
    NOTIFICATION = "notification"
    SUBPROCESS = "subprocess"
    LOOP = "loop"


class ExecutionStatus(Enum):
    """Status de execução"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


@dataclass
class ProcedureStep:
    """Um passo de um procedimento"""
    step_id: str
    order: int
    name: str
    description: str
    step_type: StepType = StepType.ACTION

    # Configuração
    required: bool = True
    timeout_seconds: int = 0
    retry_count: int = 0

    # Condições
    preconditions: List[str] = field(default_factory=list)
    expected_outcomes: List[str] = field(default_factory=list)

    # Ramificação (para decisões)
    on_success: Optional[str] = None  # próximo step_id
    on_failure: Optional[str] = None  # step_id em caso de falha
    branches: Dict[str, str] = field(default_factory=dict)  # condição -> step_id

    # Automação
    tool_name: Optional[str] = None
    tool_params: Dict[str, Any] = field(default_factory=dict)

    # Métricas
    avg_duration_seconds: float = 0
    success_rate: float = 1.0
    execution_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "order": self.order,
            "name": self.name,
            "description": self.description,
            "step_type": self.step_type.value,
            "required": self.required,
            "timeout_seconds": self.timeout_seconds,
            "preconditions": self.preconditions,
            "expected_outcomes": self.expected_outcomes,
            "on_success": self.on_success,
            "on_failure": self.on_failure,
            "branches": self.branches,
            "tool_name": self.tool_name,
            "tool_params": self.tool_params,
            "success_rate": self.success_rate,
        }


@dataclass
class StepExecution:
    """Execução de um passo"""
    step_id: str
    status: ExecutionStatus = ExecutionStatus.NOT_STARTED
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Any = None
    error: Optional[str] = None
    notes: str = ""
    retries: int = 0


@dataclass
class ProcedureExecution:
    """Execução de um procedimento completo"""
    execution_id: str
    procedure_id: str
    agent_id: str

    # Status
    status: ExecutionStatus = ExecutionStatus.NOT_STARTED
    current_step: int = 0

    # Passos
    step_executions: Dict[str, StepExecution] = field(default_factory=dict)

    # Contexto
    context: Dict[str, Any] = field(default_factory=dict)
    variables: Dict[str, Any] = field(default_factory=dict)

    # Timestamps
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    # Resultado
    success: bool = False
    error_message: Optional[str] = None
    outcome: Dict[str, Any] = field(default_factory=dict)

    # Métricas
    duration_seconds: float = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "procedure_id": self.procedure_id,
            "agent_id": self.agent_id,
            "status": self.status.value,
            "current_step": self.current_step,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "success": self.success,
            "duration_seconds": self.duration_seconds,
        }


@dataclass
class Procedure:
    """Representa um procedimento completo"""
    procedure_id: str
    name: str
    description: str
    procedure_type: ProcedureType = ProcedureType.STANDARD

    # Passos
    steps: List[ProcedureStep] = field(default_factory=list)

    # Configuração
    required_skills: List[str] = field(default_factory=list)
    required_tools: List[str] = field(default_factory=list)
    min_skill_level: SkillLevel = SkillLevel.NOVICE

    # Aplicabilidade
    triggers: List[str] = field(default_factory=list)  # Palavras-chave que ativam
    contexts: List[str] = field(default_factory=list)  # Contextos aplicáveis
    preconditions: List[str] = field(default_factory=list)

    # Versionamento
    version: int = 1
    active: bool = True

    # Métricas
    execution_count: int = 0
    success_count: int = 0
    avg_duration_seconds: float = 0
    last_executed: Optional[datetime] = None

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    created_by: str = "system"

    # Histórico de execuções
    recent_executions: List[str] = field(default_factory=list)  # execution_ids

    @property
    def success_rate(self) -> float:
        if self.execution_count == 0:
            return 0.0
        return self.success_count / self.execution_count

    def add_step(
        self,
        name: str,
        description: str,
        step_type: StepType = StepType.ACTION,
        **kwargs
    ) -> ProcedureStep:
        """Adiciona passo ao procedimento"""
        step = ProcedureStep(
            step_id=f"{self.procedure_id}_step_{len(self.steps)}",
            order=len(self.steps),
            name=name,
            description=description,
            step_type=step_type,
            **kwargs
        )
        self.steps.append(step)
        return step

    def get_step(self, step_id: str) -> Optional[ProcedureStep]:
        """Retorna passo por ID"""
        for step in self.steps:
            if step.step_id == step_id:
                return step
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "procedure_id": self.procedure_id,
            "name": self.name,
            "description": self.description,
            "procedure_type": self.procedure_type.value,
            "steps": [s.to_dict() for s in self.steps],
            "required_skills": self.required_skills,
            "required_tools": self.required_tools,
            "min_skill_level": self.min_skill_level.value,
            "triggers": self.triggers,
            "contexts": self.contexts,
            "version": self.version,
            "active": self.active,
            "execution_count": self.execution_count,
            "success_rate": self.success_rate,
            "avg_duration_seconds": self.avg_duration_seconds,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Procedure":
        """Cria procedimento a partir de dict"""
        proc = cls(
            procedure_id=data["procedure_id"],
            name=data["name"],
            description=data["description"],
            procedure_type=ProcedureType(data.get("procedure_type", "standard")),
            required_skills=data.get("required_skills", []),
            required_tools=data.get("required_tools", []),
            min_skill_level=SkillLevel(data.get("min_skill_level", 1)),
            triggers=data.get("triggers", []),
            contexts=data.get("contexts", []),
            version=data.get("version", 1),
            active=data.get("active", True),
            execution_count=data.get("execution_count", 0),
            success_count=data.get("success_count", 0),
            created_by=data.get("created_by", "system"),
        )

        # Reconstruir steps
        for step_data in data.get("steps", []):
            step = ProcedureStep(
                step_id=step_data["step_id"],
                order=step_data["order"],
                name=step_data["name"],
                description=step_data["description"],
                step_type=StepType(step_data.get("step_type", "action")),
                required=step_data.get("required", True),
                timeout_seconds=step_data.get("timeout_seconds", 0),
                preconditions=step_data.get("preconditions", []),
                expected_outcomes=step_data.get("expected_outcomes", []),
                on_success=step_data.get("on_success"),
                on_failure=step_data.get("on_failure"),
                branches=step_data.get("branches", {}),
                tool_name=step_data.get("tool_name"),
                tool_params=step_data.get("tool_params", {}),
            )
            proc.steps.append(step)

        return proc


class ProceduralMemory:
    """
    Sistema de memória para procedimentos.
    Gerencia armazenamento, execução e aprendizado de procedimentos.
    """

    def __init__(
        self,
        redis_client=None,
        vector_store=None,
        tool_registry=None,
    ):
        self.redis = redis_client
        self.vector_store = vector_store
        self.tools = tool_registry

        # Cache
        self._procedures: Dict[str, Procedure] = {}
        self._executions: Dict[str, ProcedureExecution] = {}

        # Índices
        self._by_type: Dict[ProcedureType, set] = defaultdict(set)
        self._by_trigger: Dict[str, set] = defaultdict(set)
        self._by_context: Dict[str, set] = defaultdict(set)

        # Habilidades aprendidas
        self._agent_skills: Dict[str, Dict[str, SkillLevel]] = defaultdict(dict)

    # ========================================================================
    # GESTÃO DE PROCEDIMENTOS
    # ========================================================================

    def create_procedure(
        self,
        name: str,
        description: str,
        procedure_type: ProcedureType = ProcedureType.STANDARD,
        created_by: str = "system",
        **kwargs
    ) -> Procedure:
        """Cria novo procedimento"""
        procedure_id = self._generate_id(name)

        procedure = Procedure(
            procedure_id=procedure_id,
            name=name,
            description=description,
            procedure_type=procedure_type,
            created_by=created_by,
            **kwargs
        )

        self._store_procedure(procedure)
        logger.info(f"Procedimento criado: {procedure_id} - {name}")
        return procedure

    def get_procedure(self, procedure_id: str) -> Optional[Procedure]:
        """Recupera procedimento"""
        if procedure_id in self._procedures:
            return self._procedures[procedure_id]
        return asyncio.get_event_loop().run_until_complete(
            self._load_procedure(procedure_id)
        )

    def update_procedure(
        self,
        procedure_id: str,
        **kwargs
    ) -> Optional[Procedure]:
        """Atualiza procedimento"""
        procedure = self.get_procedure(procedure_id)
        if not procedure:
            return None

        for key, value in kwargs.items():
            if hasattr(procedure, key):
                setattr(procedure, key, value)

        procedure.updated_at = datetime.now()
        procedure.version += 1

        self._store_procedure(procedure)
        return procedure

    def add_step_to_procedure(
        self,
        procedure_id: str,
        name: str,
        description: str,
        **kwargs
    ) -> Optional[ProcedureStep]:
        """Adiciona passo a um procedimento"""
        procedure = self.get_procedure(procedure_id)
        if not procedure:
            return None

        step = procedure.add_step(name, description, **kwargs)
        procedure.updated_at = datetime.now()

        self._store_procedure(procedure)
        return step

    # ========================================================================
    # EXECUÇÃO DE PROCEDIMENTOS
    # ========================================================================

    def start_execution(
        self,
        procedure_id: str,
        agent_id: str,
        context: Dict[str, Any] = None
    ) -> Optional[ProcedureExecution]:
        """Inicia execução de um procedimento"""
        procedure = self.get_procedure(procedure_id)
        if not procedure or not procedure.active:
            return None

        execution_id = self._generate_execution_id(procedure_id, agent_id)

        execution = ProcedureExecution(
            execution_id=execution_id,
            procedure_id=procedure_id,
            agent_id=agent_id,
            context=context or {},
            status=ExecutionStatus.IN_PROGRESS
        )

        # Inicializar execução dos passos
        for step in procedure.steps:
            execution.step_executions[step.step_id] = StepExecution(
                step_id=step.step_id
            )

        self._executions[execution_id] = execution
        logger.info(f"Execução iniciada: {execution_id}")
        return execution

    async def execute_step(
        self,
        execution_id: str,
        step_id: str = None,
        result: Any = None,
        success: bool = True,
        notes: str = ""
    ) -> Dict[str, Any]:
        """Executa um passo do procedimento"""
        execution = self._executions.get(execution_id)
        if not execution:
            return {"error": "Execução não encontrada"}

        procedure = self.get_procedure(execution.procedure_id)
        if not procedure:
            return {"error": "Procedimento não encontrado"}

        # Determinar passo atual
        if step_id is None:
            if execution.current_step >= len(procedure.steps):
                return {"error": "Procedimento já finalizado"}
            step = procedure.steps[execution.current_step]
            step_id = step.step_id
        else:
            step = procedure.get_step(step_id)

        if not step:
            return {"error": "Passo não encontrado"}

        # Atualizar execução do passo
        step_exec = execution.step_executions.get(step_id)
        if not step_exec:
            step_exec = StepExecution(step_id=step_id)
            execution.step_executions[step_id] = step_exec

        step_exec.started_at = step_exec.started_at or datetime.now()
        step_exec.completed_at = datetime.now()
        step_exec.result = result
        step_exec.notes = notes
        step_exec.status = ExecutionStatus.COMPLETED if success else ExecutionStatus.FAILED

        # Executar tool se configurado
        if step.tool_name and self.tools and success:
            try:
                tool_result = await self.tools.execute(
                    step.tool_name,
                    **step.tool_params,
                    **execution.variables
                )
                step_exec.result = tool_result
            except Exception as e:
                step_exec.status = ExecutionStatus.FAILED
                step_exec.error = str(e)
                success = False

        # Determinar próximo passo
        next_step_id = None
        if success and step.on_success:
            next_step_id = step.on_success
        elif not success and step.on_failure:
            next_step_id = step.on_failure
        elif step.branches and result in step.branches:
            next_step_id = step.branches[result]
        else:
            # Próximo passo sequencial
            execution.current_step += 1

        # Atualizar métricas do passo
        duration = (step_exec.completed_at - step_exec.started_at).total_seconds()
        step.execution_count += 1
        step.avg_duration_seconds = (
            step.avg_duration_seconds * (step.execution_count - 1) + duration
        ) / step.execution_count
        if success:
            step.success_rate = (
                step.success_rate * (step.execution_count - 1) + 1
            ) / step.execution_count
        else:
            step.success_rate = (
                step.success_rate * (step.execution_count - 1)
            ) / step.execution_count

        # Verificar se procedimento terminou
        if execution.current_step >= len(procedure.steps) or next_step_id == "END":
            await self._complete_execution(execution, success)

        return {
            "step_id": step_id,
            "status": step_exec.status.value,
            "next_step": next_step_id or (
                procedure.steps[execution.current_step].step_id
                if execution.current_step < len(procedure.steps)
                else None
            ),
            "procedure_completed": execution.status == ExecutionStatus.COMPLETED,
            "result": step_exec.result
        }

    async def _complete_execution(
        self,
        execution: ProcedureExecution,
        success: bool
    ):
        """Finaliza execução de procedimento"""
        execution.completed_at = datetime.now()
        execution.status = ExecutionStatus.COMPLETED if success else ExecutionStatus.FAILED
        execution.success = success
        execution.duration_seconds = (
            execution.completed_at - execution.started_at
        ).total_seconds()

        # Atualizar métricas do procedimento
        procedure = self.get_procedure(execution.procedure_id)
        if procedure:
            procedure.execution_count += 1
            if success:
                procedure.success_count += 1
            procedure.avg_duration_seconds = (
                procedure.avg_duration_seconds * (procedure.execution_count - 1)
                + execution.duration_seconds
            ) / procedure.execution_count
            procedure.last_executed = datetime.now()
            procedure.recent_executions.append(execution.execution_id)
            procedure.recent_executions = procedure.recent_executions[-100:]

            self._store_procedure(procedure)

        # Atualizar skill do agente
        self._update_agent_skill(
            execution.agent_id,
            execution.procedure_id,
            success
        )

        logger.info(
            f"Execução finalizada: {execution.execution_id} - "
            f"{'Sucesso' if success else 'Falha'}"
        )

    def cancel_execution(self, execution_id: str) -> bool:
        """Cancela execução em andamento"""
        execution = self._executions.get(execution_id)
        if not execution:
            return False

        execution.status = ExecutionStatus.CANCELLED
        execution.completed_at = datetime.now()
        return True

    # ========================================================================
    # BUSCA E SUGESTÃO
    # ========================================================================

    def find_procedure_for_context(
        self,
        context: str,
        agent_id: str = None
    ) -> List[Tuple[Procedure, float]]:
        """Encontra procedimentos adequados para o contexto"""
        results = []
        context_lower = context.lower()

        for procedure in self._procedures.values():
            if not procedure.active:
                continue

            score = 0

            # Match em triggers
            for trigger in procedure.triggers:
                if trigger.lower() in context_lower:
                    score += 5

            # Match em contextos
            for ctx in procedure.contexts:
                if ctx.lower() in context_lower:
                    score += 3

            # Match no nome/descrição
            if any(word in procedure.name.lower() for word in context_lower.split()):
                score += 2
            if any(word in procedure.description.lower() for word in context_lower.split()):
                score += 1

            # Bonus por taxa de sucesso
            score += procedure.success_rate * 2

            # Verificar skill level do agente
            if agent_id:
                agent_skill = self._agent_skills.get(agent_id, {}).get(
                    procedure.procedure_id,
                    SkillLevel.NOVICE
                )
                if agent_skill.value >= procedure.min_skill_level.value:
                    score += 1

            if score > 0:
                results.append((procedure, score))

        results.sort(key=lambda x: x[1], reverse=True)
        return results

    async def semantic_search(
        self,
        query: str,
        procedure_type: ProcedureType = None,
        limit: int = 5
    ) -> List[Tuple[Procedure, float]]:
        """Busca semântica de procedimentos"""
        if not self.vector_store:
            results = self.find_procedure_for_context(query)
            return results[:limit]

        filters = {"type": "procedure"}
        if procedure_type:
            filters["procedure_type"] = procedure_type.value

        results = await self.vector_store.search(
            agent_id="procedural_memory",
            query=query,
            limit=limit,
            filter_metadata=filters
        )

        procedures_with_scores = []
        for result in results:
            proc_id = result.get("metadata", {}).get("procedure_id")
            if proc_id:
                proc = self.get_procedure(proc_id)
                if proc and proc.active:
                    score = 1 - result.get("distance", 0)
                    procedures_with_scores.append((proc, score))

        return procedures_with_scores

    def get_by_type(self, procedure_type: ProcedureType) -> List[Procedure]:
        """Lista procedimentos por tipo"""
        proc_ids = self._by_type.get(procedure_type, set())
        return [
            self.get_procedure(pid)
            for pid in proc_ids
            if self.get_procedure(pid) and self.get_procedure(pid).active
        ]

    # ========================================================================
    # APRENDIZADO E HABILIDADES
    # ========================================================================

    def _update_agent_skill(
        self,
        agent_id: str,
        procedure_id: str,
        success: bool
    ):
        """Atualiza nível de habilidade do agente"""
        current_level = self._agent_skills[agent_id].get(
            procedure_id,
            SkillLevel.NOVICE
        )

        # Progressão baseada em execuções bem-sucedidas
        if success and current_level.value < SkillLevel.EXPERT.value:
            # Verificar execuções recentes
            proc = self.get_procedure(procedure_id)
            if proc:
                recent_success = sum(
                    1 for eid in proc.recent_executions[-10:]
                    if self._executions.get(eid, {}).get("success", False)
                )
                if recent_success >= 8 and current_level.value < 5:
                    self._agent_skills[agent_id][procedure_id] = SkillLevel(
                        current_level.value + 1
                    )

    def get_agent_skill(
        self,
        agent_id: str,
        procedure_id: str
    ) -> SkillLevel:
        """Retorna nível de habilidade do agente"""
        return self._agent_skills.get(agent_id, {}).get(
            procedure_id,
            SkillLevel.NOVICE
        )

    def get_agent_skills(self, agent_id: str) -> Dict[str, SkillLevel]:
        """Retorna todas habilidades do agente"""
        return dict(self._agent_skills.get(agent_id, {}))

    # ========================================================================
    # CRIAÇÃO DE PROCEDIMENTOS A PARTIR DE EXEMPLOS
    # ========================================================================

    async def learn_from_execution(
        self,
        execution_id: str,
        name: str = None
    ) -> Optional[Procedure]:
        """Aprende procedimento a partir de uma execução bem-sucedida"""
        execution = self._executions.get(execution_id)
        if not execution or not execution.success:
            return None

        # Criar novo procedimento baseado na execução
        name = name or f"Procedimento aprendido de {execution.procedure_id}"
        proc = self.create_procedure(
            name=name,
            description=f"Procedimento aprendido automaticamente",
            procedure_type=ProcedureType.WORKFLOW,
            created_by="system_learning"
        )

        # Adicionar passos baseados na execução
        original_proc = self.get_procedure(execution.procedure_id)
        if original_proc:
            for step_exec in execution.step_executions.values():
                if step_exec.status == ExecutionStatus.COMPLETED:
                    original_step = original_proc.get_step(step_exec.step_id)
                    if original_step:
                        proc.add_step(
                            name=original_step.name,
                            description=original_step.description,
                            step_type=original_step.step_type,
                            tool_name=original_step.tool_name,
                            tool_params=original_step.tool_params
                        )

        return proc

    # ========================================================================
    # PERSISTÊNCIA
    # ========================================================================

    def _store_procedure(self, procedure: Procedure):
        """Armazena procedimento"""
        self._procedures[procedure.procedure_id] = procedure
        self._update_indices(procedure)
        asyncio.create_task(self._persist_procedure(procedure))

    async def _persist_procedure(self, procedure: Procedure):
        """Persiste procedimento"""
        if self.redis:
            data = json.dumps(procedure.to_dict())
            await self.redis.set(f"procedure:{procedure.procedure_id}", data)

        if self.vector_store:
            searchable = f"{procedure.name} {procedure.description} {' '.join(procedure.triggers)}"
            await self.vector_store.store(
                agent_id="procedural_memory",
                content=searchable,
                metadata={
                    "type": "procedure",
                    "procedure_id": procedure.procedure_id,
                    "procedure_type": procedure.procedure_type.value,
                }
            )

    async def _load_procedure(self, procedure_id: str) -> Optional[Procedure]:
        """Carrega procedimento"""
        if self.redis:
            data = await self.redis.get(f"procedure:{procedure_id}")
            if data:
                proc = Procedure.from_dict(json.loads(data))
                self._procedures[procedure_id] = proc
                self._update_indices(proc)
                return proc
        return None

    def _update_indices(self, procedure: Procedure):
        """Atualiza índices"""
        self._by_type[procedure.procedure_type].add(procedure.procedure_id)
        for trigger in procedure.triggers:
            self._by_trigger[trigger.lower()].add(procedure.procedure_id)
        for ctx in procedure.contexts:
            self._by_context[ctx.lower()].add(procedure.procedure_id)

    # ========================================================================
    # UTILITÁRIOS
    # ========================================================================

    def _generate_id(self, name: str) -> str:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        return hashlib.sha256(f"{name}:{timestamp}".encode()).hexdigest()[:16]

    def _generate_execution_id(self, procedure_id: str, agent_id: str) -> str:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        return hashlib.sha256(
            f"{procedure_id}:{agent_id}:{timestamp}".encode()
        ).hexdigest()[:16]

    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas"""
        type_counts = defaultdict(int)
        for proc in self._procedures.values():
            if proc.active:
                type_counts[proc.procedure_type.value] += 1

        return {
            "total_procedures": len(self._procedures),
            "active_procedures": sum(1 for p in self._procedures.values() if p.active),
            "by_type": dict(type_counts),
            "total_executions": len(self._executions),
            "agents_with_skills": len(self._agent_skills),
        }
