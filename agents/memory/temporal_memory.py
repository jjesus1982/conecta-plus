"""
Conecta Plus - Temporal Memory
Memória baseada em tempo e eventos

Funcionalidades:
- Armazenamento de eventos temporais
- Detecção de padrões recorrentes
- Agendamento e lembretes
- Timeline de eventos
- Previsão baseada em histórico
"""

import asyncio
import json
import logging
import hashlib
from datetime import datetime, timedelta, time, date
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import calendar

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Tipos de eventos temporais"""
    # Eventos pontuais
    APPOINTMENT = "appointment"
    MEETING = "meeting"
    DEADLINE = "deadline"
    REMINDER = "reminder"

    # Eventos recorrentes
    RECURRING = "recurring"
    SCHEDULED = "scheduled"

    # Eventos do sistema
    SYSTEM = "system"
    MAINTENANCE = "maintenance"
    REPORT = "report"

    # Eventos de condomínio
    ASSEMBLY = "assembly"
    RESERVATION = "reservation"
    DELIVERY = "delivery"
    VISITOR = "visitor"
    ACCESS = "access"

    # Outros
    CUSTOM = "custom"


class RecurrenceType(Enum):
    """Tipos de recorrência"""
    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    CUSTOM = "custom"


class EventStatus(Enum):
    """Status do evento"""
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    MISSED = "missed"
    RESCHEDULED = "rescheduled"


@dataclass
class TimeSlot:
    """Slot de tempo"""
    start: datetime
    end: datetime
    available: bool = True
    event_id: Optional[str] = None

    @property
    def duration_minutes(self) -> int:
        return int((self.end - self.start).total_seconds() / 60)

    def overlaps(self, other: "TimeSlot") -> bool:
        return self.start < other.end and other.start < self.end

    def to_dict(self) -> Dict[str, Any]:
        return {
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "duration_minutes": self.duration_minutes,
            "available": self.available,
            "event_id": self.event_id,
        }


@dataclass
class RecurringPattern:
    """Padrão de recorrência"""
    pattern_id: str
    recurrence_type: RecurrenceType
    interval: int = 1  # A cada N períodos

    # Para recorrência semanal
    days_of_week: List[int] = field(default_factory=list)  # 0=segunda, 6=domingo

    # Para recorrência mensal
    day_of_month: Optional[int] = None
    week_of_month: Optional[int] = None  # 1-4 ou -1 para última

    # Limites
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    max_occurrences: Optional[int] = None

    # Exceções
    exceptions: List[date] = field(default_factory=list)

    # Contagem
    occurrences_count: int = 0

    def get_next_occurrence(self, after: datetime = None) -> Optional[datetime]:
        """Calcula próxima ocorrência"""
        after = after or datetime.now()

        if self.end_date and after.date() > self.end_date:
            return None

        if self.max_occurrences and self.occurrences_count >= self.max_occurrences:
            return None

        if self.recurrence_type == RecurrenceType.DAILY:
            next_date = after.date() + timedelta(days=self.interval)
        elif self.recurrence_type == RecurrenceType.WEEKLY:
            # Encontrar próximo dia da semana válido
            next_date = after.date()
            for _ in range(8):
                next_date += timedelta(days=1)
                if next_date.weekday() in self.days_of_week:
                    break
        elif self.recurrence_type == RecurrenceType.MONTHLY:
            if self.day_of_month:
                next_month = after.month + self.interval
                next_year = after.year + (next_month - 1) // 12
                next_month = ((next_month - 1) % 12) + 1
                day = min(self.day_of_month, calendar.monthrange(next_year, next_month)[1])
                next_date = date(next_year, next_month, day)
            else:
                next_date = after.date() + timedelta(days=30 * self.interval)
        elif self.recurrence_type == RecurrenceType.YEARLY:
            next_date = date(after.year + self.interval, after.month, after.day)
        else:
            return None

        # Verificar exceções
        while next_date in self.exceptions:
            next_date += timedelta(days=1)

        return datetime.combine(next_date, after.time())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "recurrence_type": self.recurrence_type.value,
            "interval": self.interval,
            "days_of_week": self.days_of_week,
            "day_of_month": self.day_of_month,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "max_occurrences": self.max_occurrences,
            "occurrences_count": self.occurrences_count,
        }


@dataclass
class TemporalEvent:
    """Evento temporal"""
    event_id: str
    title: str
    event_type: EventType
    status: EventStatus = EventStatus.SCHEDULED

    # Tempo
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    duration_minutes: int = 60
    all_day: bool = False

    # Recorrência
    recurring: bool = False
    recurrence_pattern: Optional[RecurringPattern] = None
    parent_event_id: Optional[str] = None  # Para instâncias de eventos recorrentes

    # Localização
    location: Optional[str] = None
    location_id: Optional[str] = None

    # Participantes
    organizer: Optional[str] = None
    participants: List[str] = field(default_factory=list)

    # Notificações
    reminders: List[int] = field(default_factory=list)  # minutos antes
    notifications_sent: List[datetime] = field(default_factory=list)

    # Contexto
    description: str = ""
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Relacionamentos
    related_events: List[str] = field(default_factory=list)
    related_entities: List[str] = field(default_factory=list)

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        if self.end_time is None:
            self.end_time = self.start_time + timedelta(minutes=self.duration_minutes)

    @property
    def is_past(self) -> bool:
        return self.end_time < datetime.now()

    @property
    def is_ongoing(self) -> bool:
        now = datetime.now()
        return self.start_time <= now <= self.end_time

    @property
    def is_upcoming(self) -> bool:
        return self.start_time > datetime.now()

    def get_time_slot(self) -> TimeSlot:
        return TimeSlot(
            start=self.start_time,
            end=self.end_time,
            available=False,
            event_id=self.event_id
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "title": self.title,
            "event_type": self.event_type.value,
            "status": self.status.value,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_minutes": self.duration_minutes,
            "all_day": self.all_day,
            "recurring": self.recurring,
            "location": self.location,
            "organizer": self.organizer,
            "participants": self.participants,
            "reminders": self.reminders,
            "description": self.description,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TemporalEvent":
        event = cls(
            event_id=data["event_id"],
            title=data["title"],
            event_type=EventType(data["event_type"]),
            status=EventStatus(data.get("status", "scheduled")),
            start_time=datetime.fromisoformat(data["start_time"]),
            duration_minutes=data.get("duration_minutes", 60),
            all_day=data.get("all_day", False),
            recurring=data.get("recurring", False),
            location=data.get("location"),
            organizer=data.get("organizer"),
            participants=data.get("participants", []),
            reminders=data.get("reminders", []),
            description=data.get("description", ""),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
        )

        if data.get("end_time"):
            event.end_time = datetime.fromisoformat(data["end_time"])

        return event


@dataclass
class CalendarEntry:
    """Entrada de calendário (wrapper para visualização)"""
    date: date
    events: List[TemporalEvent] = field(default_factory=list)
    is_holiday: bool = False
    holiday_name: Optional[str] = None

    @property
    def has_events(self) -> bool:
        return len(self.events) > 0

    @property
    def event_count(self) -> int:
        return len(self.events)


class TemporalMemory:
    """
    Sistema de memória temporal.
    Gerencia eventos, padrões e agendamentos.
    """

    def __init__(
        self,
        redis_client=None,
        notification_callback: Callable = None,
    ):
        self.redis = redis_client
        self.notify = notification_callback

        # Cache
        self._events: Dict[str, TemporalEvent] = {}
        self._patterns: Dict[str, RecurringPattern] = {}

        # Índices
        self._by_date: Dict[date, List[str]] = defaultdict(list)
        self._by_type: Dict[EventType, set] = defaultdict(set)
        self._by_participant: Dict[str, set] = defaultdict(set)
        self._by_location: Dict[str, set] = defaultdict(set)

        # Padrões detectados
        self._detected_patterns: Dict[str, Dict[str, Any]] = {}

        # Feriados
        self._holidays: Dict[date, str] = {}

        # Task de reminder
        self._reminder_task: Optional[asyncio.Task] = None

    # ========================================================================
    # GESTÃO DE EVENTOS
    # ========================================================================

    def create_event(
        self,
        title: str,
        start_time: datetime,
        event_type: EventType = EventType.APPOINTMENT,
        duration_minutes: int = 60,
        **kwargs
    ) -> TemporalEvent:
        """Cria novo evento"""
        event_id = self._generate_id(title, start_time)

        event = TemporalEvent(
            event_id=event_id,
            title=title,
            event_type=event_type,
            start_time=start_time,
            duration_minutes=duration_minutes,
            **kwargs
        )

        self._store_event(event)
        logger.info(f"Evento criado: {event_id} - {title}")
        return event

    def create_recurring_event(
        self,
        title: str,
        start_time: datetime,
        recurrence_type: RecurrenceType,
        event_type: EventType = EventType.RECURRING,
        **kwargs
    ) -> TemporalEvent:
        """Cria evento recorrente"""
        event = self.create_event(
            title=title,
            start_time=start_time,
            event_type=event_type,
            recurring=True,
            **kwargs
        )

        # Criar padrão de recorrência
        pattern = RecurringPattern(
            pattern_id=f"pattern_{event.event_id}",
            recurrence_type=recurrence_type,
            interval=kwargs.get("interval", 1),
            days_of_week=kwargs.get("days_of_week", []),
            day_of_month=kwargs.get("day_of_month"),
            start_date=start_time.date(),
            end_date=kwargs.get("end_date"),
            max_occurrences=kwargs.get("max_occurrences"),
        )

        event.recurrence_pattern = pattern
        self._patterns[pattern.pattern_id] = pattern
        self._store_event(event)

        return event

    def get_event(self, event_id: str) -> Optional[TemporalEvent]:
        """Recupera evento"""
        if event_id in self._events:
            return self._events[event_id]
        return asyncio.get_event_loop().run_until_complete(
            self._load_event(event_id)
        )

    def update_event(
        self,
        event_id: str,
        **kwargs
    ) -> Optional[TemporalEvent]:
        """Atualiza evento"""
        event = self.get_event(event_id)
        if not event:
            return None

        # Remover dos índices antigos
        self._remove_from_indices(event)

        # Atualizar
        for key, value in kwargs.items():
            if hasattr(event, key):
                setattr(event, key, value)

        event.updated_at = datetime.now()

        # Recalcular end_time se necessário
        if "start_time" in kwargs or "duration_minutes" in kwargs:
            event.end_time = event.start_time + timedelta(minutes=event.duration_minutes)

        self._store_event(event)
        return event

    def cancel_event(self, event_id: str, reason: str = None) -> bool:
        """Cancela evento"""
        event = self.get_event(event_id)
        if not event:
            return False

        event.status = EventStatus.CANCELLED
        if reason:
            event.metadata["cancel_reason"] = reason

        self._store_event(event)
        return True

    def reschedule_event(
        self,
        event_id: str,
        new_start: datetime
    ) -> Optional[TemporalEvent]:
        """Reagenda evento"""
        event = self.get_event(event_id)
        if not event:
            return None

        old_start = event.start_time
        event.start_time = new_start
        event.end_time = new_start + timedelta(minutes=event.duration_minutes)
        event.status = EventStatus.RESCHEDULED
        event.metadata["original_start"] = old_start.isoformat()

        # Atualizar índices
        self._remove_from_indices(event)
        self._store_event(event)

        return event

    # ========================================================================
    # CONSULTAS
    # ========================================================================

    def get_events_for_date(self, target_date: date) -> List[TemporalEvent]:
        """Lista eventos de uma data"""
        event_ids = self._by_date.get(target_date, [])
        events = []

        for eid in event_ids:
            event = self.get_event(eid)
            if event and event.status != EventStatus.CANCELLED:
                events.append(event)

        # Ordenar por horário
        events.sort(key=lambda e: e.start_time)
        return events

    def get_events_for_range(
        self,
        start_date: date,
        end_date: date
    ) -> List[TemporalEvent]:
        """Lista eventos em um período"""
        events = []
        current = start_date

        while current <= end_date:
            events.extend(self.get_events_for_date(current))
            current += timedelta(days=1)

        return events

    def get_upcoming_events(
        self,
        hours: int = 24,
        event_type: EventType = None
    ) -> List[TemporalEvent]:
        """Lista eventos próximos"""
        now = datetime.now()
        end = now + timedelta(hours=hours)

        events = []
        for event in self._events.values():
            if event.status == EventStatus.CANCELLED:
                continue
            if event_type and event.event_type != event_type:
                continue
            if now <= event.start_time <= end:
                events.append(event)

        events.sort(key=lambda e: e.start_time)
        return events

    def get_events_by_participant(self, participant_id: str) -> List[TemporalEvent]:
        """Lista eventos de um participante"""
        event_ids = self._by_participant.get(participant_id, set())
        return [
            self.get_event(eid)
            for eid in event_ids
            if self.get_event(eid) and self.get_event(eid).status != EventStatus.CANCELLED
        ]

    def get_calendar(
        self,
        year: int,
        month: int
    ) -> List[CalendarEntry]:
        """Retorna calendário do mês"""
        entries = []
        first_day = date(year, month, 1)
        last_day = date(year, month, calendar.monthrange(year, month)[1])

        current = first_day
        while current <= last_day:
            events = self.get_events_for_date(current)
            holiday = self._holidays.get(current)

            entry = CalendarEntry(
                date=current,
                events=events,
                is_holiday=holiday is not None,
                holiday_name=holiday
            )
            entries.append(entry)
            current += timedelta(days=1)

        return entries

    # ========================================================================
    # DISPONIBILIDADE E CONFLITOS
    # ========================================================================

    def check_availability(
        self,
        start_time: datetime,
        end_time: datetime,
        location_id: str = None
    ) -> Dict[str, Any]:
        """Verifica disponibilidade de horário"""
        slot = TimeSlot(start=start_time, end=end_time)
        conflicts = []

        for event in self._events.values():
            if event.status == EventStatus.CANCELLED:
                continue

            # Verificar localização se especificada
            if location_id and event.location_id != location_id:
                continue

            event_slot = event.get_time_slot()
            if slot.overlaps(event_slot):
                conflicts.append(event)

        return {
            "available": len(conflicts) == 0,
            "conflicts": [e.to_dict() for e in conflicts],
            "conflict_count": len(conflicts)
        }

    def find_available_slots(
        self,
        target_date: date,
        duration_minutes: int,
        start_hour: int = 8,
        end_hour: int = 18,
        location_id: str = None
    ) -> List[TimeSlot]:
        """Encontra slots disponíveis em uma data"""
        available = []

        # Gerar slots de 30 em 30 minutos
        current = datetime.combine(target_date, time(start_hour, 0))
        end = datetime.combine(target_date, time(end_hour, 0))

        while current + timedelta(minutes=duration_minutes) <= end:
            slot_end = current + timedelta(minutes=duration_minutes)
            result = self.check_availability(current, slot_end, location_id)

            if result["available"]:
                available.append(TimeSlot(
                    start=current,
                    end=slot_end,
                    available=True
                ))

            current += timedelta(minutes=30)

        return available

    def get_next_available_slot(
        self,
        duration_minutes: int,
        after: datetime = None,
        location_id: str = None
    ) -> Optional[TimeSlot]:
        """Encontra próximo slot disponível"""
        after = after or datetime.now()
        current_date = after.date()

        # Procurar nos próximos 30 dias
        for _ in range(30):
            slots = self.find_available_slots(
                current_date,
                duration_minutes,
                location_id=location_id
            )

            for slot in slots:
                if slot.start > after:
                    return slot

            current_date += timedelta(days=1)

        return None

    # ========================================================================
    # DETECÇÃO DE PADRÕES
    # ========================================================================

    def detect_patterns(
        self,
        event_type: EventType = None,
        min_occurrences: int = 3
    ) -> List[Dict[str, Any]]:
        """Detecta padrões nos eventos"""
        patterns = []

        # Agrupar eventos por tipo e características
        by_characteristics = defaultdict(list)

        for event in self._events.values():
            if event.status == EventStatus.CANCELLED:
                continue
            if event_type and event.event_type != event_type:
                continue

            # Criar chave baseada em características
            hour = event.start_time.hour
            weekday = event.start_time.weekday()
            key = f"{event.event_type.value}:{weekday}:{hour}"

            by_characteristics[key].append(event)

        # Analisar grupos
        for key, events in by_characteristics.items():
            if len(events) >= min_occurrences:
                event_type_str, weekday, hour = key.split(":")
                weekday_name = calendar.day_name[int(weekday)]

                pattern = {
                    "type": "time_pattern",
                    "event_type": event_type_str,
                    "weekday": int(weekday),
                    "weekday_name": weekday_name,
                    "hour": int(hour),
                    "occurrences": len(events),
                    "confidence": min(len(events) / 10, 1.0),
                    "description": f"Eventos de {event_type_str} às {weekday_name}s às {hour}h"
                }
                patterns.append(pattern)

        return sorted(patterns, key=lambda p: p["occurrences"], reverse=True)

    def predict_next_events(
        self,
        days: int = 7
    ) -> List[Dict[str, Any]]:
        """Prevê eventos baseado em padrões"""
        predictions = []
        patterns = self.detect_patterns()

        for pattern in patterns[:5]:  # Top 5 padrões
            if pattern["confidence"] >= 0.5:
                # Gerar previsões
                for d in range(days):
                    target_date = datetime.now().date() + timedelta(days=d)
                    if target_date.weekday() == pattern["weekday"]:
                        prediction = {
                            "predicted_time": datetime.combine(
                                target_date,
                                time(pattern["hour"], 0)
                            ).isoformat(),
                            "event_type": pattern["event_type"],
                            "confidence": pattern["confidence"],
                            "based_on_pattern": pattern["description"]
                        }
                        predictions.append(prediction)

        return predictions

    # ========================================================================
    # LEMBRETES E NOTIFICAÇÕES
    # ========================================================================

    async def start_reminder_service(self):
        """Inicia serviço de lembretes"""
        self._reminder_task = asyncio.create_task(self._reminder_loop())

    async def _reminder_loop(self):
        """Loop de verificação de lembretes"""
        while True:
            try:
                await self._check_reminders()
                await asyncio.sleep(60)  # Verificar a cada minuto
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Erro no serviço de lembretes: {e}")

    async def _check_reminders(self):
        """Verifica e envia lembretes pendentes"""
        now = datetime.now()

        for event in self._events.values():
            if event.status == EventStatus.CANCELLED:
                continue
            if event.is_past:
                continue

            for minutes_before in event.reminders:
                reminder_time = event.start_time - timedelta(minutes=minutes_before)

                # Verificar se está na hora e ainda não foi enviado
                if now >= reminder_time and reminder_time not in event.notifications_sent:
                    await self._send_reminder(event, minutes_before)
                    event.notifications_sent.append(reminder_time)

    async def _send_reminder(self, event: TemporalEvent, minutes_before: int):
        """Envia lembrete de evento"""
        if self.notify:
            message = f"Lembrete: {event.title} em {minutes_before} minutos"
            if event.location:
                message += f" - Local: {event.location}"

            await self.notify(
                event_id=event.event_id,
                title="Lembrete de Evento",
                message=message,
                participants=event.participants,
                minutes_before=minutes_before
            )

        logger.info(f"Lembrete enviado: {event.event_id} ({minutes_before}min antes)")

    def stop_reminder_service(self):
        """Para serviço de lembretes"""
        if self._reminder_task:
            self._reminder_task.cancel()

    # ========================================================================
    # FERIADOS
    # ========================================================================

    def add_holiday(self, holiday_date: date, name: str):
        """Adiciona feriado"""
        self._holidays[holiday_date] = name

    def load_brazilian_holidays(self, year: int):
        """Carrega feriados brasileiros"""
        holidays = {
            date(year, 1, 1): "Ano Novo",
            date(year, 4, 21): "Tiradentes",
            date(year, 5, 1): "Dia do Trabalho",
            date(year, 9, 7): "Independência",
            date(year, 10, 12): "Nossa Senhora Aparecida",
            date(year, 11, 2): "Finados",
            date(year, 11, 15): "Proclamação da República",
            date(year, 12, 25): "Natal",
        }
        self._holidays.update(holidays)

    def is_holiday(self, check_date: date) -> Tuple[bool, Optional[str]]:
        """Verifica se é feriado"""
        name = self._holidays.get(check_date)
        return (name is not None, name)

    # ========================================================================
    # PERSISTÊNCIA
    # ========================================================================

    def _store_event(self, event: TemporalEvent):
        """Armazena evento"""
        self._events[event.event_id] = event
        self._update_indices(event)
        asyncio.create_task(self._persist_event(event))

    async def _persist_event(self, event: TemporalEvent):
        """Persiste evento"""
        if self.redis:
            data = json.dumps(event.to_dict())
            await self.redis.set(f"event:{event.event_id}", data)

    async def _load_event(self, event_id: str) -> Optional[TemporalEvent]:
        """Carrega evento"""
        if self.redis:
            data = await self.redis.get(f"event:{event_id}")
            if data:
                event = TemporalEvent.from_dict(json.loads(data))
                self._events[event_id] = event
                self._update_indices(event)
                return event
        return None

    def _update_indices(self, event: TemporalEvent):
        """Atualiza índices"""
        # Por data
        event_date = event.start_time.date()
        if event.event_id not in self._by_date[event_date]:
            self._by_date[event_date].append(event.event_id)

        # Por tipo
        self._by_type[event.event_type].add(event.event_id)

        # Por participante
        for participant in event.participants:
            self._by_participant[participant].add(event.event_id)

        # Por localização
        if event.location_id:
            self._by_location[event.location_id].add(event.event_id)

    def _remove_from_indices(self, event: TemporalEvent):
        """Remove dos índices"""
        event_date = event.start_time.date()
        if event.event_id in self._by_date.get(event_date, []):
            self._by_date[event_date].remove(event.event_id)

        self._by_type[event.event_type].discard(event.event_id)

        for participant in event.participants:
            self._by_participant[participant].discard(event.event_id)

        if event.location_id:
            self._by_location[event.location_id].discard(event.event_id)

    # ========================================================================
    # UTILITÁRIOS
    # ========================================================================

    def _generate_id(self, title: str, start_time: datetime) -> str:
        timestamp = start_time.strftime("%Y%m%d%H%M%S")
        return hashlib.sha256(f"{title}:{timestamp}".encode()).hexdigest()[:16]

    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas"""
        now = datetime.now()

        return {
            "total_events": len(self._events),
            "upcoming_events": len([e for e in self._events.values() if e.is_upcoming]),
            "past_events": len([e for e in self._events.values() if e.is_past]),
            "recurring_patterns": len(self._patterns),
            "holidays_loaded": len(self._holidays),
            "events_today": len(self.get_events_for_date(now.date())),
        }
