"""
Conecta Plus - Workflow Skills
Habilidades de automação de fluxos de trabalho
"""

import asyncio
import logging
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

from .base_skill import (
    BaseSkill, SkillContext, SkillResult, SkillMetadata,
    SkillCategory, skill
)

logger = logging.getLogger(__name__)


# ============================================================
# Approval Workflow Skill
# ============================================================

class ApprovalStatus(Enum):
    """Status de aprovação"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELED = "canceled"


class ApprovalType(Enum):
    """Tipos de aprovação"""
    SINGLE = "single"  # Uma pessoa aprova
    ALL = "all"  # Todos devem aprovar
    MAJORITY = "majority"  # Maioria aprova
    THRESHOLD = "threshold"  # Percentual mínimo


@dataclass
class ApprovalStep:
    """Etapa de aprovação"""
    step_id: str
    name: str
    approvers: List[str]  # IDs dos aprovadores
    approval_type: ApprovalType = ApprovalType.SINGLE
    threshold: float = 0.5  # Para THRESHOLD
    timeout_hours: int = 48

    # Estado
    status: ApprovalStatus = ApprovalStatus.PENDING
    responses: Dict[str, Dict] = field(default_factory=dict)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class ApprovalWorkflow:
    """Fluxo de aprovação"""
    workflow_id: str
    name: str
    description: str
    steps: List[ApprovalStep]

    # Contexto
    request_type: str = ""
    request_data: Dict[str, Any] = field(default_factory=dict)
    requester_id: str = ""

    # Estado
    current_step: int = 0
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    # Configurações
    notify_on_action: bool = True
    auto_expire: bool = True


@skill(
    name="approval_workflow",
    version="1.0.0",
    category=SkillCategory.WORKFLOW,
    description="Fluxos de aprovação multinível",
    tags=["workflow", "approval", "authorization"]
)
class ApprovalWorkflowSkill(BaseSkill):
    """
    Skill para gerenciamento de fluxos de aprovação.
    Suporta múltiplos níveis e tipos de aprovação.
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self._workflows: Dict[str, ApprovalWorkflow] = {}
        self._workflow_templates: Dict[str, Dict] = self._load_templates()

    def _load_templates(self) -> Dict[str, Dict]:
        """Carrega templates de workflow"""
        return {
            "reserva_area_comum": {
                "name": "Aprovação de Reserva",
                "steps": [
                    {"name": "Administração", "approvers": ["admin"], "type": "single"}
                ]
            },
            "obra_unidade": {
                "name": "Aprovação de Obra",
                "steps": [
                    {"name": "Síndico", "approvers": ["sindico"], "type": "single"},
                    {"name": "Corpo Técnico", "approvers": ["engenheiro"], "type": "single"}
                ]
            },
            "despesa_extra": {
                "name": "Aprovação de Despesa",
                "steps": [
                    {"name": "Síndico", "approvers": ["sindico"], "type": "single", "max_value": 5000},
                    {"name": "Conselho", "approvers": ["conselho"], "type": "majority"}
                ]
            },
            "mudanca": {
                "name": "Autorização de Mudança",
                "steps": [
                    {"name": "Portaria", "approvers": ["portaria"], "type": "single"},
                    {"name": "Administração", "approvers": ["admin"], "type": "single"}
                ]
            }
        }

    async def _execute(self, context: SkillContext, **params) -> SkillResult:
        """Executa ação de workflow"""
        action = params.get("action", "create")

        if action == "create":
            return await self._create_workflow(context, params)
        elif action == "create_from_template":
            return await self._create_from_template(context, params)
        elif action == "approve":
            return await self._approve(context, params)
        elif action == "reject":
            return await self._reject(context, params)
        elif action == "cancel":
            return await self._cancel(context, params)
        elif action == "get_status":
            return await self._get_status(context, params)
        elif action == "list_pending":
            return await self._list_pending(context, params)
        elif action == "get_history":
            return await self._get_history(context, params)
        else:
            return SkillResult.fail(f"Ação desconhecida: {action}")

    async def _create_workflow(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Cria novo workflow de aprovação"""
        name = params.get("name")
        steps_config = params.get("steps", [])
        request_type = params.get("request_type", "")
        request_data = params.get("request_data", {})

        if not name or not steps_config:
            return SkillResult.fail("'name' e 'steps' são obrigatórios")

        workflow_id = f"wf_{uuid.uuid4().hex[:12]}"

        steps = []
        for i, step_cfg in enumerate(steps_config):
            step = ApprovalStep(
                step_id=f"{workflow_id}_step_{i}",
                name=step_cfg.get("name", f"Etapa {i+1}"),
                approvers=step_cfg.get("approvers", []),
                approval_type=ApprovalType(step_cfg.get("type", "single")),
                threshold=step_cfg.get("threshold", 0.5),
                timeout_hours=step_cfg.get("timeout_hours", 48)
            )
            steps.append(step)

        workflow = ApprovalWorkflow(
            workflow_id=workflow_id,
            name=name,
            description=params.get("description", ""),
            steps=steps,
            request_type=request_type,
            request_data=request_data,
            requester_id=context.user_id or ""
        )

        # Iniciar primeira etapa
        if steps:
            steps[0].started_at = datetime.now()

        self._workflows[workflow_id] = workflow

        return SkillResult.ok({
            "workflow_id": workflow_id,
            "name": name,
            "steps": len(steps),
            "current_step": 0,
            "status": "pending",
            "created_at": workflow.created_at.isoformat()
        })

    async def _create_from_template(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Cria workflow a partir de template"""
        template_name = params.get("template")
        request_data = params.get("request_data", {})

        if not template_name:
            return SkillResult.fail("'template' é obrigatório")

        template = self._workflow_templates.get(template_name)
        if not template:
            return SkillResult.fail(f"Template não encontrado: {template_name}")

        return await self._create_workflow(context, {
            "name": template["name"],
            "steps": template["steps"],
            "request_type": template_name,
            "request_data": request_data
        })

    async def _approve(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Aprova etapa atual"""
        workflow_id = params.get("workflow_id")
        approver_id = params.get("approver_id") or context.user_id
        comments = params.get("comments", "")

        if not workflow_id:
            return SkillResult.fail("'workflow_id' é obrigatório")

        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return SkillResult.fail(f"Workflow não encontrado: {workflow_id}")

        if workflow.status != ApprovalStatus.PENDING:
            return SkillResult.fail(f"Workflow não está pendente: {workflow.status.value}")

        current_step = workflow.steps[workflow.current_step]

        # Verificar se é aprovador válido
        if approver_id not in current_step.approvers and "admin" not in context.permissions:
            return SkillResult.fail("Usuário não é aprovador desta etapa")

        # Registrar aprovação
        current_step.responses[approver_id] = {
            "action": "approved",
            "comments": comments,
            "timestamp": datetime.now().isoformat()
        }

        # Verificar se etapa está completa
        step_complete = self._check_step_complete(current_step)

        if step_complete:
            current_step.status = ApprovalStatus.APPROVED
            current_step.completed_at = datetime.now()

            # Avançar para próxima etapa ou concluir
            if workflow.current_step < len(workflow.steps) - 1:
                workflow.current_step += 1
                workflow.steps[workflow.current_step].started_at = datetime.now()
            else:
                workflow.status = ApprovalStatus.APPROVED
                workflow.completed_at = datetime.now()

        return SkillResult.ok({
            "workflow_id": workflow_id,
            "step": current_step.name,
            "step_status": current_step.status.value,
            "workflow_status": workflow.status.value,
            "current_step": workflow.current_step,
            "approved_by": approver_id
        })

    async def _reject(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Rejeita etapa"""
        workflow_id = params.get("workflow_id")
        approver_id = params.get("approver_id") or context.user_id
        reason = params.get("reason", "")

        if not workflow_id:
            return SkillResult.fail("'workflow_id' é obrigatório")

        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return SkillResult.fail(f"Workflow não encontrado: {workflow_id}")

        current_step = workflow.steps[workflow.current_step]

        # Registrar rejeição
        current_step.responses[approver_id] = {
            "action": "rejected",
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        }

        current_step.status = ApprovalStatus.REJECTED
        current_step.completed_at = datetime.now()

        workflow.status = ApprovalStatus.REJECTED
        workflow.completed_at = datetime.now()

        return SkillResult.ok({
            "workflow_id": workflow_id,
            "status": "rejected",
            "rejected_by": approver_id,
            "reason": reason,
            "step": current_step.name
        })

    async def _cancel(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Cancela workflow"""
        workflow_id = params.get("workflow_id")
        reason = params.get("reason", "")

        if not workflow_id:
            return SkillResult.fail("'workflow_id' é obrigatório")

        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return SkillResult.fail(f"Workflow não encontrado: {workflow_id}")

        workflow.status = ApprovalStatus.CANCELED
        workflow.completed_at = datetime.now()

        return SkillResult.ok({
            "workflow_id": workflow_id,
            "status": "canceled",
            "reason": reason
        })

    async def _get_status(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Obtém status do workflow"""
        workflow_id = params.get("workflow_id")

        if not workflow_id:
            return SkillResult.fail("'workflow_id' é obrigatório")

        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return SkillResult.fail(f"Workflow não encontrado: {workflow_id}")

        return SkillResult.ok({
            "workflow_id": workflow_id,
            "name": workflow.name,
            "status": workflow.status.value,
            "current_step": workflow.current_step,
            "total_steps": len(workflow.steps),
            "requester": workflow.requester_id,
            "request_type": workflow.request_type,
            "created_at": workflow.created_at.isoformat(),
            "completed_at": workflow.completed_at.isoformat() if workflow.completed_at else None,
            "steps": [
                {
                    "name": s.name,
                    "status": s.status.value,
                    "approvers": s.approvers,
                    "responses": s.responses
                }
                for s in workflow.steps
            ]
        })

    async def _list_pending(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Lista workflows pendentes"""
        approver_id = params.get("approver_id") or context.user_id

        pending = []
        for workflow in self._workflows.values():
            if workflow.status != ApprovalStatus.PENDING:
                continue

            current_step = workflow.steps[workflow.current_step]

            if approver_id in current_step.approvers or approver_id not in current_step.responses:
                pending.append({
                    "workflow_id": workflow.workflow_id,
                    "name": workflow.name,
                    "request_type": workflow.request_type,
                    "current_step": current_step.name,
                    "created_at": workflow.created_at.isoformat()
                })

        return SkillResult.ok({
            "pending": pending,
            "count": len(pending)
        })

    async def _get_history(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Obtém histórico de workflows"""
        limit = params.get("limit", 50)
        status_filter = params.get("status")

        workflows = []
        for workflow in sorted(
            self._workflows.values(),
            key=lambda w: w.created_at,
            reverse=True
        )[:limit]:
            if status_filter and workflow.status.value != status_filter:
                continue

            workflows.append({
                "workflow_id": workflow.workflow_id,
                "name": workflow.name,
                "status": workflow.status.value,
                "request_type": workflow.request_type,
                "created_at": workflow.created_at.isoformat(),
                "completed_at": workflow.completed_at.isoformat() if workflow.completed_at else None
            })

        return SkillResult.ok({
            "workflows": workflows,
            "count": len(workflows)
        })

    def _check_step_complete(self, step: ApprovalStep) -> bool:
        """Verifica se etapa está completa"""
        approved_count = sum(
            1 for r in step.responses.values()
            if r.get("action") == "approved"
        )

        if step.approval_type == ApprovalType.SINGLE:
            return approved_count >= 1

        elif step.approval_type == ApprovalType.ALL:
            return approved_count == len(step.approvers)

        elif step.approval_type == ApprovalType.MAJORITY:
            return approved_count > len(step.approvers) / 2

        elif step.approval_type == ApprovalType.THRESHOLD:
            return approved_count / len(step.approvers) >= step.threshold

        return False


# ============================================================
# Scheduling Skill
# ============================================================

class RecurrenceType(Enum):
    """Tipos de recorrência"""
    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    CUSTOM = "custom"


@dataclass
class ScheduledEvent:
    """Evento agendado"""
    event_id: str
    title: str
    description: str

    # Tempo
    start_time: datetime
    end_time: Optional[datetime] = None
    all_day: bool = False

    # Recorrência
    recurrence: RecurrenceType = RecurrenceType.NONE
    recurrence_interval: int = 1
    recurrence_end: Optional[datetime] = None
    recurrence_days: List[int] = field(default_factory=list)

    # Contexto
    location: str = ""
    category: str = "general"
    participants: List[str] = field(default_factory=list)

    # Estado
    status: str = "scheduled"
    created_at: datetime = field(default_factory=datetime.now)

    # Notificações
    reminders: List[int] = field(default_factory=list)  # Minutos antes


@skill(
    name="scheduling",
    version="1.0.0",
    category=SkillCategory.WORKFLOW,
    description="Agendamento de eventos e reservas",
    tags=["scheduling", "calendar", "reservation"]
)
class SchedulingSkill(BaseSkill):
    """
    Skill para agendamento de eventos.
    Suporta recorrência, conflitos e reservas.
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self._events: Dict[str, ScheduledEvent] = {}
        self._resources: Dict[str, Dict] = {}  # Recursos reserváveis

    async def _execute(self, context: SkillContext, **params) -> SkillResult:
        """Executa ação de agendamento"""
        action = params.get("action", "create")

        if action == "create":
            return await self._create_event(context, params)
        elif action == "update":
            return await self._update_event(context, params)
        elif action == "cancel":
            return await self._cancel_event(context, params)
        elif action == "get":
            return await self._get_event(context, params)
        elif action == "list":
            return await self._list_events(context, params)
        elif action == "check_availability":
            return await self._check_availability(context, params)
        elif action == "reserve":
            return await self._reserve_resource(context, params)
        elif action == "get_schedule":
            return await self._get_schedule(context, params)
        else:
            return SkillResult.fail(f"Ação desconhecida: {action}")

    async def _create_event(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Cria novo evento"""
        title = params.get("title")
        start_time = params.get("start_time")

        if not title or not start_time:
            return SkillResult.fail("'title' e 'start_time' são obrigatórios")

        # Converter para datetime
        if isinstance(start_time, str):
            start_time = datetime.fromisoformat(start_time)

        end_time = params.get("end_time")
        if end_time and isinstance(end_time, str):
            end_time = datetime.fromisoformat(end_time)

        event_id = f"evt_{uuid.uuid4().hex[:12]}"

        # Verificar conflitos se houver recurso
        resource_id = params.get("resource_id")
        if resource_id:
            conflicts = await self._check_conflicts(resource_id, start_time, end_time)
            if conflicts:
                return SkillResult.fail(
                    f"Conflito com evento existente: {conflicts[0]['title']}",
                    error_code="CONFLICT"
                )

        event = ScheduledEvent(
            event_id=event_id,
            title=title,
            description=params.get("description", ""),
            start_time=start_time,
            end_time=end_time,
            all_day=params.get("all_day", False),
            recurrence=RecurrenceType(params.get("recurrence", "none")),
            recurrence_interval=params.get("recurrence_interval", 1),
            location=params.get("location", ""),
            category=params.get("category", "general"),
            participants=params.get("participants", []),
            reminders=params.get("reminders", [30, 1440])  # 30min e 1 dia
        )

        self._events[event_id] = event

        return SkillResult.ok({
            "event_id": event_id,
            "title": title,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat() if end_time else None,
            "status": "scheduled"
        })

    async def _update_event(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Atualiza evento"""
        event_id = params.get("event_id")

        if not event_id:
            return SkillResult.fail("'event_id' é obrigatório")

        event = self._events.get(event_id)
        if not event:
            return SkillResult.fail(f"Evento não encontrado: {event_id}")

        # Atualizar campos
        if "title" in params:
            event.title = params["title"]
        if "description" in params:
            event.description = params["description"]
        if "start_time" in params:
            event.start_time = datetime.fromisoformat(params["start_time"])
        if "end_time" in params:
            event.end_time = datetime.fromisoformat(params["end_time"]) if params["end_time"] else None
        if "location" in params:
            event.location = params["location"]
        if "participants" in params:
            event.participants = params["participants"]

        return SkillResult.ok({
            "event_id": event_id,
            "updated": True
        })

    async def _cancel_event(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Cancela evento"""
        event_id = params.get("event_id")
        reason = params.get("reason", "")

        if not event_id:
            return SkillResult.fail("'event_id' é obrigatório")

        event = self._events.get(event_id)
        if not event:
            return SkillResult.fail(f"Evento não encontrado: {event_id}")

        event.status = "canceled"

        return SkillResult.ok({
            "event_id": event_id,
            "status": "canceled",
            "reason": reason
        })

    async def _get_event(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Obtém detalhes do evento"""
        event_id = params.get("event_id")

        if not event_id:
            return SkillResult.fail("'event_id' é obrigatório")

        event = self._events.get(event_id)
        if not event:
            return SkillResult.fail(f"Evento não encontrado: {event_id}")

        return SkillResult.ok({
            "event_id": event.event_id,
            "title": event.title,
            "description": event.description,
            "start_time": event.start_time.isoformat(),
            "end_time": event.end_time.isoformat() if event.end_time else None,
            "all_day": event.all_day,
            "location": event.location,
            "category": event.category,
            "participants": event.participants,
            "recurrence": event.recurrence.value,
            "status": event.status
        })

    async def _list_events(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Lista eventos"""
        start_date = params.get("start_date")
        end_date = params.get("end_date")
        category = params.get("category")

        if start_date and isinstance(start_date, str):
            start_date = datetime.fromisoformat(start_date)
        if end_date and isinstance(end_date, str):
            end_date = datetime.fromisoformat(end_date)

        events = []
        for event in self._events.values():
            if event.status == "canceled":
                continue

            if start_date and event.start_time < start_date:
                continue
            if end_date and event.start_time > end_date:
                continue
            if category and event.category != category:
                continue

            events.append({
                "event_id": event.event_id,
                "title": event.title,
                "start_time": event.start_time.isoformat(),
                "end_time": event.end_time.isoformat() if event.end_time else None,
                "location": event.location,
                "category": event.category
            })

        events.sort(key=lambda e: e["start_time"])

        return SkillResult.ok({
            "events": events,
            "count": len(events)
        })

    async def _check_availability(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Verifica disponibilidade"""
        resource_id = params.get("resource_id")
        date = params.get("date")

        if not date:
            return SkillResult.fail("'date' é obrigatório")

        if isinstance(date, str):
            date = datetime.fromisoformat(date).date()

        # Buscar eventos do dia
        day_start = datetime.combine(date, datetime.min.time())
        day_end = datetime.combine(date, datetime.max.time())

        busy_slots = []
        for event in self._events.values():
            if event.status == "canceled":
                continue
            if event.start_time.date() != date:
                continue

            busy_slots.append({
                "start": event.start_time.strftime("%H:%M"),
                "end": event.end_time.strftime("%H:%M") if event.end_time else None,
                "event": event.title
            })

        # Calcular slots livres (exemplo: horário comercial)
        available_slots = self._calculate_available_slots(busy_slots)

        return SkillResult.ok({
            "date": str(date),
            "resource_id": resource_id,
            "busy_slots": busy_slots,
            "available_slots": available_slots
        })

    async def _reserve_resource(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Reserva recurso (área comum, equipamento, etc.)"""
        resource_id = params.get("resource_id")
        start_time = params.get("start_time")
        end_time = params.get("end_time")
        requester = params.get("requester") or context.user_id

        if not all([resource_id, start_time, end_time]):
            return SkillResult.fail("'resource_id', 'start_time' e 'end_time' são obrigatórios")

        if isinstance(start_time, str):
            start_time = datetime.fromisoformat(start_time)
        if isinstance(end_time, str):
            end_time = datetime.fromisoformat(end_time)

        # Verificar conflitos
        conflicts = await self._check_conflicts(resource_id, start_time, end_time)
        if conflicts:
            return SkillResult.fail(
                f"Recurso já reservado neste horário",
                error_code="CONFLICT"
            )

        # Criar reserva como evento
        return await self._create_event(context, {
            "title": f"Reserva: {resource_id}",
            "start_time": start_time,
            "end_time": end_time,
            "category": "reservation",
            "resource_id": resource_id,
            "participants": [requester]
        })

    async def _get_schedule(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Obtém agenda de um participante ou recurso"""
        participant = params.get("participant")
        resource_id = params.get("resource_id")
        days = params.get("days", 7)

        start_date = datetime.now()
        end_date = start_date + timedelta(days=days)

        events = []
        for event in self._events.values():
            if event.status == "canceled":
                continue
            if event.start_time < start_date or event.start_time > end_date:
                continue

            if participant and participant not in event.participants:
                continue

            events.append({
                "event_id": event.event_id,
                "title": event.title,
                "start_time": event.start_time.isoformat(),
                "end_time": event.end_time.isoformat() if event.end_time else None,
                "location": event.location
            })

        events.sort(key=lambda e: e["start_time"])

        return SkillResult.ok({
            "participant": participant,
            "resource_id": resource_id,
            "period": f"{start_date.date()} a {end_date.date()}",
            "events": events,
            "count": len(events)
        })

    async def _check_conflicts(
        self,
        resource_id: str,
        start_time: datetime,
        end_time: Optional[datetime]
    ) -> List[Dict]:
        """Verifica conflitos de horário"""
        conflicts = []

        for event in self._events.values():
            if event.status == "canceled":
                continue

            # Verificar sobreposição
            event_end = event.end_time or (event.start_time + timedelta(hours=1))

            if end_time:
                if start_time < event_end and end_time > event.start_time:
                    conflicts.append({
                        "event_id": event.event_id,
                        "title": event.title,
                        "start_time": event.start_time.isoformat()
                    })

        return conflicts

    def _calculate_available_slots(self, busy_slots: List[Dict]) -> List[Dict]:
        """Calcula slots disponíveis"""
        # Horário comercial: 8h às 22h
        work_start = 8
        work_end = 22

        available = []
        current_hour = work_start

        for slot in sorted(busy_slots, key=lambda s: s["start"]):
            slot_start = int(slot["start"].split(":")[0])
            slot_end = int(slot["end"].split(":")[0]) if slot["end"] else slot_start + 1

            if current_hour < slot_start:
                available.append({
                    "start": f"{current_hour:02d}:00",
                    "end": f"{slot_start:02d}:00"
                })

            current_hour = max(current_hour, slot_end)

        if current_hour < work_end:
            available.append({
                "start": f"{current_hour:02d}:00",
                "end": f"{work_end:02d}:00"
            })

        return available


# ============================================================
# Reminder Skill
# ============================================================

class ReminderPriority(Enum):
    """Prioridade do lembrete"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class Reminder:
    """Lembrete"""
    reminder_id: str
    title: str
    message: str

    # Tempo
    remind_at: datetime
    repeat: Optional[str] = None  # daily, weekly, monthly

    # Destinatário
    user_id: str = ""
    channel: str = "push"  # push, email, sms, whatsapp

    # Estado
    status: str = "pending"  # pending, sent, dismissed, snoozed
    priority: ReminderPriority = ReminderPriority.NORMAL

    # Contexto
    related_entity: Optional[str] = None  # ID de entidade relacionada
    entity_type: Optional[str] = None  # Tipo da entidade

    created_at: datetime = field(default_factory=datetime.now)
    sent_at: Optional[datetime] = None


@skill(
    name="reminder",
    version="1.0.0",
    category=SkillCategory.WORKFLOW,
    description="Lembretes e notificações programadas",
    tags=["reminder", "notification", "alert"]
)
class ReminderSkill(BaseSkill):
    """
    Skill para gerenciamento de lembretes.
    Suporta múltiplos canais e recorrência.
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self._reminders: Dict[str, Reminder] = {}

    async def _execute(self, context: SkillContext, **params) -> SkillResult:
        """Executa ação de lembrete"""
        action = params.get("action", "create")

        if action == "create":
            return await self._create_reminder(context, params)
        elif action == "update":
            return await self._update_reminder(context, params)
        elif action == "dismiss":
            return await self._dismiss_reminder(context, params)
        elif action == "snooze":
            return await self._snooze_reminder(context, params)
        elif action == "list":
            return await self._list_reminders(context, params)
        elif action == "get_pending":
            return await self._get_pending(context, params)
        elif action == "process":
            return await self._process_reminders(context, params)
        else:
            return SkillResult.fail(f"Ação desconhecida: {action}")

    async def _create_reminder(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Cria lembrete"""
        title = params.get("title")
        remind_at = params.get("remind_at")

        if not title or not remind_at:
            return SkillResult.fail("'title' e 'remind_at' são obrigatórios")

        if isinstance(remind_at, str):
            remind_at = datetime.fromisoformat(remind_at)

        reminder_id = f"rem_{uuid.uuid4().hex[:12]}"

        reminder = Reminder(
            reminder_id=reminder_id,
            title=title,
            message=params.get("message", title),
            remind_at=remind_at,
            repeat=params.get("repeat"),
            user_id=params.get("user_id") or context.user_id or "",
            channel=params.get("channel", "push"),
            priority=ReminderPriority(params.get("priority", "normal")),
            related_entity=params.get("related_entity"),
            entity_type=params.get("entity_type")
        )

        self._reminders[reminder_id] = reminder

        return SkillResult.ok({
            "reminder_id": reminder_id,
            "title": title,
            "remind_at": remind_at.isoformat(),
            "channel": reminder.channel,
            "status": "pending"
        })

    async def _update_reminder(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Atualiza lembrete"""
        reminder_id = params.get("reminder_id")

        if not reminder_id:
            return SkillResult.fail("'reminder_id' é obrigatório")

        reminder = self._reminders.get(reminder_id)
        if not reminder:
            return SkillResult.fail(f"Lembrete não encontrado: {reminder_id}")

        if "title" in params:
            reminder.title = params["title"]
        if "message" in params:
            reminder.message = params["message"]
        if "remind_at" in params:
            reminder.remind_at = datetime.fromisoformat(params["remind_at"])
        if "channel" in params:
            reminder.channel = params["channel"]
        if "priority" in params:
            reminder.priority = ReminderPriority(params["priority"])

        return SkillResult.ok({
            "reminder_id": reminder_id,
            "updated": True
        })

    async def _dismiss_reminder(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Descarta lembrete"""
        reminder_id = params.get("reminder_id")

        if not reminder_id:
            return SkillResult.fail("'reminder_id' é obrigatório")

        reminder = self._reminders.get(reminder_id)
        if not reminder:
            return SkillResult.fail(f"Lembrete não encontrado: {reminder_id}")

        reminder.status = "dismissed"

        return SkillResult.ok({
            "reminder_id": reminder_id,
            "status": "dismissed"
        })

    async def _snooze_reminder(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Adia lembrete"""
        reminder_id = params.get("reminder_id")
        minutes = params.get("minutes", 15)

        if not reminder_id:
            return SkillResult.fail("'reminder_id' é obrigatório")

        reminder = self._reminders.get(reminder_id)
        if not reminder:
            return SkillResult.fail(f"Lembrete não encontrado: {reminder_id}")

        reminder.remind_at = datetime.now() + timedelta(minutes=minutes)
        reminder.status = "snoozed"

        return SkillResult.ok({
            "reminder_id": reminder_id,
            "status": "snoozed",
            "new_time": reminder.remind_at.isoformat()
        })

    async def _list_reminders(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Lista lembretes"""
        user_id = params.get("user_id") or context.user_id
        status_filter = params.get("status")

        reminders = []
        for reminder in self._reminders.values():
            if user_id and reminder.user_id != user_id:
                continue
            if status_filter and reminder.status != status_filter:
                continue

            reminders.append({
                "reminder_id": reminder.reminder_id,
                "title": reminder.title,
                "remind_at": reminder.remind_at.isoformat(),
                "channel": reminder.channel,
                "priority": reminder.priority.value,
                "status": reminder.status
            })

        reminders.sort(key=lambda r: r["remind_at"])

        return SkillResult.ok({
            "reminders": reminders,
            "count": len(reminders)
        })

    async def _get_pending(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Obtém lembretes pendentes para envio"""
        now = datetime.now()

        pending = []
        for reminder in self._reminders.values():
            if reminder.status != "pending":
                continue
            if reminder.remind_at > now:
                continue

            pending.append({
                "reminder_id": reminder.reminder_id,
                "title": reminder.title,
                "message": reminder.message,
                "user_id": reminder.user_id,
                "channel": reminder.channel,
                "priority": reminder.priority.value,
                "remind_at": reminder.remind_at.isoformat()
            })

        return SkillResult.ok({
            "pending": pending,
            "count": len(pending)
        })

    async def _process_reminders(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Processa lembretes pendentes"""
        result = await self._get_pending(context, {})

        if not result.success:
            return result

        processed = []
        for reminder_data in result.data["pending"]:
            reminder = self._reminders.get(reminder_data["reminder_id"])
            if not reminder:
                continue

            # Marcar como enviado
            reminder.status = "sent"
            reminder.sent_at = datetime.now()

            # Criar próximo se for recorrente
            if reminder.repeat:
                await self._create_next_occurrence(reminder)

            processed.append({
                "reminder_id": reminder.reminder_id,
                "title": reminder.title,
                "sent_to": reminder.user_id,
                "channel": reminder.channel
            })

        return SkillResult.ok({
            "processed": processed,
            "count": len(processed)
        })

    async def _create_next_occurrence(self, reminder: Reminder):
        """Cria próxima ocorrência de lembrete recorrente"""
        next_time = reminder.remind_at

        if reminder.repeat == "daily":
            next_time += timedelta(days=1)
        elif reminder.repeat == "weekly":
            next_time += timedelta(weeks=1)
        elif reminder.repeat == "monthly":
            next_time += timedelta(days=30)

        await self._create_reminder(
            SkillContext(agent_id="system", condominio_id=""),
            {
                "title": reminder.title,
                "message": reminder.message,
                "remind_at": next_time,
                "repeat": reminder.repeat,
                "user_id": reminder.user_id,
                "channel": reminder.channel,
                "priority": reminder.priority.value
            }
        )


# ============================================================
# Task Management Skill
# ============================================================

class TaskStatus(Enum):
    """Status de tarefa"""
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"
    CANCELED = "canceled"


class TaskPriority(Enum):
    """Prioridade de tarefa"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class Task:
    """Tarefa"""
    task_id: str
    title: str
    description: str

    # Atribuição
    assignee: Optional[str] = None
    reporter: str = ""
    watchers: List[str] = field(default_factory=list)

    # Estado
    status: TaskStatus = TaskStatus.TODO
    priority: TaskPriority = TaskPriority.NORMAL

    # Tempo
    due_date: Optional[datetime] = None
    estimated_hours: Optional[float] = None
    logged_hours: float = 0

    # Organização
    category: str = "general"
    tags: List[str] = field(default_factory=list)
    parent_task: Optional[str] = None
    subtasks: List[str] = field(default_factory=list)

    # Contexto
    related_entity: Optional[str] = None
    entity_type: Optional[str] = None

    # Histórico
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    # Comentários
    comments: List[Dict] = field(default_factory=list)


@skill(
    name="task_management",
    version="1.0.0",
    category=SkillCategory.WORKFLOW,
    description="Gerenciamento de tarefas e atividades",
    tags=["task", "todo", "project", "management"]
)
class TaskManagementSkill(BaseSkill):
    """
    Skill para gerenciamento de tarefas.
    Suporta subtarefas, prioridades e tracking de tempo.
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self._tasks: Dict[str, Task] = {}

    async def _execute(self, context: SkillContext, **params) -> SkillResult:
        """Executa ação de tarefa"""
        action = params.get("action", "create")

        if action == "create":
            return await self._create_task(context, params)
        elif action == "update":
            return await self._update_task(context, params)
        elif action == "update_status":
            return await self._update_status(context, params)
        elif action == "assign":
            return await self._assign_task(context, params)
        elif action == "add_comment":
            return await self._add_comment(context, params)
        elif action == "log_time":
            return await self._log_time(context, params)
        elif action == "get":
            return await self._get_task(context, params)
        elif action == "list":
            return await self._list_tasks(context, params)
        elif action == "get_board":
            return await self._get_board(context, params)
        elif action == "get_metrics":
            return await self._get_metrics(context, params)
        else:
            return SkillResult.fail(f"Ação desconhecida: {action}")

    async def _create_task(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Cria tarefa"""
        title = params.get("title")

        if not title:
            return SkillResult.fail("'title' é obrigatório")

        task_id = f"task_{uuid.uuid4().hex[:12]}"

        due_date = params.get("due_date")
        if due_date and isinstance(due_date, str):
            due_date = datetime.fromisoformat(due_date)

        task = Task(
            task_id=task_id,
            title=title,
            description=params.get("description", ""),
            assignee=params.get("assignee"),
            reporter=params.get("reporter") or context.user_id or "",
            priority=TaskPriority(params.get("priority", 2)),
            due_date=due_date,
            estimated_hours=params.get("estimated_hours"),
            category=params.get("category", "general"),
            tags=params.get("tags", []),
            parent_task=params.get("parent_task"),
            related_entity=params.get("related_entity"),
            entity_type=params.get("entity_type")
        )

        self._tasks[task_id] = task

        # Adicionar como subtarefa se tiver pai
        if task.parent_task and task.parent_task in self._tasks:
            self._tasks[task.parent_task].subtasks.append(task_id)

        return SkillResult.ok({
            "task_id": task_id,
            "title": title,
            "status": "todo",
            "assignee": task.assignee,
            "due_date": due_date.isoformat() if due_date else None
        })

    async def _update_task(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Atualiza tarefa"""
        task_id = params.get("task_id")

        if not task_id:
            return SkillResult.fail("'task_id' é obrigatório")

        task = self._tasks.get(task_id)
        if not task:
            return SkillResult.fail(f"Tarefa não encontrada: {task_id}")

        if "title" in params:
            task.title = params["title"]
        if "description" in params:
            task.description = params["description"]
        if "priority" in params:
            task.priority = TaskPriority(params["priority"])
        if "due_date" in params:
            task.due_date = datetime.fromisoformat(params["due_date"]) if params["due_date"] else None
        if "tags" in params:
            task.tags = params["tags"]
        if "estimated_hours" in params:
            task.estimated_hours = params["estimated_hours"]

        task.updated_at = datetime.now()

        return SkillResult.ok({
            "task_id": task_id,
            "updated": True
        })

    async def _update_status(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Atualiza status da tarefa"""
        task_id = params.get("task_id")
        status = params.get("status")

        if not task_id or not status:
            return SkillResult.fail("'task_id' e 'status' são obrigatórios")

        task = self._tasks.get(task_id)
        if not task:
            return SkillResult.fail(f"Tarefa não encontrada: {task_id}")

        old_status = task.status
        task.status = TaskStatus(status)
        task.updated_at = datetime.now()

        if task.status == TaskStatus.DONE:
            task.completed_at = datetime.now()

        return SkillResult.ok({
            "task_id": task_id,
            "old_status": old_status.value,
            "new_status": status
        })

    async def _assign_task(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Atribui tarefa"""
        task_id = params.get("task_id")
        assignee = params.get("assignee")

        if not task_id:
            return SkillResult.fail("'task_id' é obrigatório")

        task = self._tasks.get(task_id)
        if not task:
            return SkillResult.fail(f"Tarefa não encontrada: {task_id}")

        old_assignee = task.assignee
        task.assignee = assignee
        task.updated_at = datetime.now()

        return SkillResult.ok({
            "task_id": task_id,
            "old_assignee": old_assignee,
            "new_assignee": assignee
        })

    async def _add_comment(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Adiciona comentário"""
        task_id = params.get("task_id")
        comment = params.get("comment")

        if not task_id or not comment:
            return SkillResult.fail("'task_id' e 'comment' são obrigatórios")

        task = self._tasks.get(task_id)
        if not task:
            return SkillResult.fail(f"Tarefa não encontrada: {task_id}")

        comment_data = {
            "id": f"cmt_{uuid.uuid4().hex[:8]}",
            "text": comment,
            "author": params.get("author") or context.user_id,
            "created_at": datetime.now().isoformat()
        }

        task.comments.append(comment_data)
        task.updated_at = datetime.now()

        return SkillResult.ok({
            "task_id": task_id,
            "comment_id": comment_data["id"],
            "added": True
        })

    async def _log_time(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Registra tempo trabalhado"""
        task_id = params.get("task_id")
        hours = params.get("hours", 0)

        if not task_id or hours <= 0:
            return SkillResult.fail("'task_id' e 'hours' (> 0) são obrigatórios")

        task = self._tasks.get(task_id)
        if not task:
            return SkillResult.fail(f"Tarefa não encontrada: {task_id}")

        task.logged_hours += hours
        task.updated_at = datetime.now()

        return SkillResult.ok({
            "task_id": task_id,
            "hours_logged": hours,
            "total_logged": task.logged_hours,
            "estimated": task.estimated_hours
        })

    async def _get_task(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Obtém detalhes da tarefa"""
        task_id = params.get("task_id")

        if not task_id:
            return SkillResult.fail("'task_id' é obrigatório")

        task = self._tasks.get(task_id)
        if not task:
            return SkillResult.fail(f"Tarefa não encontrada: {task_id}")

        return SkillResult.ok({
            "task_id": task.task_id,
            "title": task.title,
            "description": task.description,
            "status": task.status.value,
            "priority": task.priority.value,
            "assignee": task.assignee,
            "reporter": task.reporter,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "estimated_hours": task.estimated_hours,
            "logged_hours": task.logged_hours,
            "category": task.category,
            "tags": task.tags,
            "subtasks": task.subtasks,
            "comments": task.comments,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat(),
            "completed_at": task.completed_at.isoformat() if task.completed_at else None
        })

    async def _list_tasks(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Lista tarefas"""
        assignee = params.get("assignee")
        status_filter = params.get("status")
        category = params.get("category")

        tasks = []
        for task in self._tasks.values():
            if assignee and task.assignee != assignee:
                continue
            if status_filter and task.status.value != status_filter:
                continue
            if category and task.category != category:
                continue

            tasks.append({
                "task_id": task.task_id,
                "title": task.title,
                "status": task.status.value,
                "priority": task.priority.value,
                "assignee": task.assignee,
                "due_date": task.due_date.isoformat() if task.due_date else None
            })

        # Ordenar por prioridade e data
        tasks.sort(key=lambda t: (-t["priority"], t.get("due_date") or "9999"))

        return SkillResult.ok({
            "tasks": tasks,
            "count": len(tasks)
        })

    async def _get_board(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Obtém visão de board (Kanban)"""
        assignee = params.get("assignee")
        category = params.get("category")

        board = {
            "todo": [],
            "in_progress": [],
            "review": [],
            "done": []
        }

        for task in self._tasks.values():
            if task.status == TaskStatus.CANCELED:
                continue
            if assignee and task.assignee != assignee:
                continue
            if category and task.category != category:
                continue

            task_data = {
                "task_id": task.task_id,
                "title": task.title,
                "priority": task.priority.value,
                "assignee": task.assignee,
                "due_date": task.due_date.isoformat() if task.due_date else None
            }

            board[task.status.value].append(task_data)

        return SkillResult.ok({
            "board": board,
            "totals": {k: len(v) for k, v in board.items()}
        })

    async def _get_metrics(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Obtém métricas das tarefas"""
        assignee = params.get("assignee")

        total = 0
        by_status = {}
        by_priority = {}
        overdue = 0
        total_estimated = 0
        total_logged = 0

        now = datetime.now()

        for task in self._tasks.values():
            if assignee and task.assignee != assignee:
                continue

            total += 1

            status = task.status.value
            by_status[status] = by_status.get(status, 0) + 1

            priority = task.priority.name
            by_priority[priority] = by_priority.get(priority, 0) + 1

            if task.due_date and task.due_date < now and task.status not in [TaskStatus.DONE, TaskStatus.CANCELED]:
                overdue += 1

            if task.estimated_hours:
                total_estimated += task.estimated_hours
            total_logged += task.logged_hours

        return SkillResult.ok({
            "total_tasks": total,
            "by_status": by_status,
            "by_priority": by_priority,
            "overdue": overdue,
            "total_estimated_hours": total_estimated,
            "total_logged_hours": total_logged,
            "efficiency": total_logged / total_estimated if total_estimated > 0 else None
        })


# Função de inicialização
def register_workflow_skills():
    """Registra todas as skills de workflow"""
    pass
