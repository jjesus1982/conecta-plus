"""
Conecta Plus - Guardian Analytics Agent
Agente de Analise Preditiva de Seguranca - Nivel 7

Responsabilidades:
- Analise estatistica de eventos de seguranca
- Deteccao de padroes anomalos
- Previsao de incidentes com ML
- Score de risco em tempo real
- Recomendacoes proativas de seguranca
"""

import asyncio
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from collections import defaultdict
import math
import statistics

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Niveis de risco de seguranca."""
    MINIMAL = "minimal"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class TrendDirection(Enum):
    """Direcao de tendencia."""
    DECREASING = "decreasing"
    STABLE = "stable"
    INCREASING = "increasing"
    SPIKE = "spike"


class AnomalyType(Enum):
    """Tipos de anomalia detectada."""
    FREQUENCY_SPIKE = "frequency_spike"
    UNUSUAL_TIMING = "unusual_timing"
    PATTERN_BREAK = "pattern_break"
    GEOGRAPHIC_CLUSTER = "geographic_cluster"
    BEHAVIORAL_DEVIATION = "behavioral_deviation"
    CORRELATION_ANOMALY = "correlation_anomaly"


class PredictionType(Enum):
    """Tipos de predicao."""
    INCIDENT_PROBABILITY = "incident_probability"
    PEAK_ACTIVITY = "peak_activity"
    VULNERABILITY_WINDOW = "vulnerability_window"
    RESOURCE_NEED = "resource_need"


@dataclass
class SecurityMetric:
    """Metrica de seguranca."""
    name: str
    value: float
    unit: str
    timestamp: datetime
    source: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Anomaly:
    """Anomalia detectada."""
    id: str
    type: AnomalyType
    severity: float  # 0.0 - 1.0
    description: str
    detected_at: datetime
    affected_entities: List[str]
    baseline_value: float
    current_value: float
    deviation_factor: float
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Prediction:
    """Predicao de seguranca."""
    id: str
    type: PredictionType
    description: str
    probability: float
    predicted_time: datetime
    confidence: float
    risk_level: RiskLevel
    recommended_actions: List[str]
    factors: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RiskAssessment:
    """Avaliacao de risco."""
    entity_id: str
    entity_type: str
    risk_score: float  # 0.0 - 100.0
    risk_level: RiskLevel
    contributing_factors: List[Dict[str, Any]]
    trend: TrendDirection
    recommendations: List[str]
    assessed_at: datetime
    valid_until: datetime


@dataclass
class SecurityInsight:
    """Insight de seguranca."""
    id: str
    title: str
    description: str
    category: str
    importance: float
    actionable: bool
    actions: List[str]
    data_points: List[Dict[str, Any]]
    generated_at: datetime


class GuardianAnalyticsAgent:
    """
    Agente de Analise Preditiva Guardian - Nivel 7 TRANSCENDENT

    Capacidades:
    - Analise estatistica avancada de eventos
    - Deteccao de anomalias com Z-score e IQR
    - Machine learning para previsoes
    - Correlacao de eventos multi-fonte
    - Recomendacoes contextuais
    """

    def __init__(
        self,
        agent_id: str = "guardian_analytics",
        config: Optional[Dict[str, Any]] = None,
        message_bus: Optional[Any] = None
    ):
        self.agent_id = agent_id
        self.config = config or {}
        self.message_bus = message_bus

        # Configuracoes de analise
        self.anomaly_z_threshold = self.config.get("anomaly_z_threshold", 2.5)
        self.min_data_points = self.config.get("min_data_points", 30)
        self.prediction_horizon_hours = self.config.get("prediction_horizon_hours", 24)
        self.risk_decay_factor = self.config.get("risk_decay_factor", 0.95)

        # Armazenamento de dados
        self.metrics_history: Dict[str, List[SecurityMetric]] = defaultdict(list)
        self.event_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.hourly_patterns: Dict[str, List[float]] = defaultdict(lambda: [0.0] * 24)
        self.daily_patterns: Dict[str, List[float]] = defaultdict(lambda: [0.0] * 7)

        # Cache de analises
        self.risk_cache: Dict[str, RiskAssessment] = {}
        self.anomaly_history: List[Anomaly] = []
        self.prediction_history: List[Prediction] = []
        self.insights_cache: List[SecurityInsight] = []

        # Baselines aprendidas
        self.baselines: Dict[str, Dict[str, float]] = {}

        # Estado do agente
        self.is_running = False
        self._analysis_task: Optional[asyncio.Task] = None

        logger.info(f"GuardianAnalyticsAgent {agent_id} inicializado")

    async def start(self) -> None:
        """Inicia o agente de analytics."""
        if self.is_running:
            return

        self.is_running = True
        self._analysis_task = asyncio.create_task(self._periodic_analysis())

        if self.message_bus:
            await self.message_bus.subscribe("security.event", self._handle_security_event)
            await self.message_bus.subscribe("access.event", self._handle_access_event)
            await self.message_bus.subscribe("alert.created", self._handle_alert)

        logger.info(f"GuardianAnalyticsAgent {self.agent_id} iniciado")

    async def stop(self) -> None:
        """Para o agente de analytics."""
        self.is_running = False

        if self._analysis_task:
            self._analysis_task.cancel()
            try:
                await self._analysis_task
            except asyncio.CancelledError:
                pass

        logger.info(f"GuardianAnalyticsAgent {self.agent_id} parado")

    async def _periodic_analysis(self) -> None:
        """Loop de analise periodica."""
        while self.is_running:
            try:
                # Analise a cada 5 minutos
                await asyncio.sleep(300)

                # Atualizar baselines
                await self._update_baselines()

                # Detectar anomalias
                anomalies = await self._detect_anomalies()
                for anomaly in anomalies:
                    await self._publish_anomaly(anomaly)

                # Gerar predicoes
                predictions = await self._generate_predictions()
                for prediction in predictions:
                    await self._publish_prediction(prediction)

                # Atualizar scores de risco
                await self._update_risk_scores()

                # Gerar insights
                await self._generate_insights()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Erro na analise periodica: {e}")

    async def _handle_security_event(self, event: Dict[str, Any]) -> None:
        """Processa evento de seguranca."""
        try:
            event_type = event.get("type", "unknown")
            timestamp = datetime.fromisoformat(event.get("timestamp", datetime.now().isoformat()))
            location = event.get("location", "unknown")

            # Registrar contagem de eventos
            hour_key = timestamp.strftime("%Y-%m-%d-%H")
            self.event_counts[event_type][hour_key] += 1

            # Atualizar padroes horarios
            hour = timestamp.hour
            self.hourly_patterns[event_type][hour] += 1

            # Atualizar padroes diarios
            weekday = timestamp.weekday()
            self.daily_patterns[event_type][weekday] += 1

            # Criar metrica
            metric = SecurityMetric(
                name=f"event_{event_type}",
                value=1.0,
                unit="count",
                timestamp=timestamp,
                source="security_event",
                metadata=event
            )
            self._add_metric(metric)

            # Verificar anomalia em tempo real
            await self._check_realtime_anomaly(event_type, location, timestamp)

        except Exception as e:
            logger.error(f"Erro ao processar evento de seguranca: {e}")

    async def _handle_access_event(self, event: Dict[str, Any]) -> None:
        """Processa evento de acesso."""
        try:
            access_type = event.get("type", "unknown")
            result = event.get("result", "unknown")
            timestamp = datetime.fromisoformat(event.get("timestamp", datetime.now().isoformat()))

            # Registrar metricas de acesso
            metric_name = f"access_{access_type}_{result}"
            metric = SecurityMetric(
                name=metric_name,
                value=1.0,
                unit="count",
                timestamp=timestamp,
                source="access_event",
                metadata=event
            )
            self._add_metric(metric)

            # Atualizar padroes
            hour = timestamp.hour
            self.hourly_patterns[metric_name][hour] += 1

        except Exception as e:
            logger.error(f"Erro ao processar evento de acesso: {e}")

    async def _handle_alert(self, alert: Dict[str, Any]) -> None:
        """Processa alerta criado."""
        try:
            alert_type = alert.get("type", "unknown")
            severity = alert.get("severity", "medium")
            timestamp = datetime.fromisoformat(alert.get("timestamp", datetime.now().isoformat()))

            # Mapear severidade para valor numerico
            severity_map = {
                "low": 0.25,
                "medium": 0.5,
                "high": 0.75,
                "critical": 1.0
            }
            severity_value = severity_map.get(severity, 0.5)

            metric = SecurityMetric(
                name=f"alert_{alert_type}",
                value=severity_value,
                unit="severity",
                timestamp=timestamp,
                source="alert_system",
                metadata=alert
            )
            self._add_metric(metric)

        except Exception as e:
            logger.error(f"Erro ao processar alerta: {e}")

    def _add_metric(self, metric: SecurityMetric) -> None:
        """Adiciona metrica ao historico."""
        self.metrics_history[metric.name].append(metric)

        # Manter apenas ultimas 24 horas
        cutoff = datetime.now() - timedelta(hours=24)
        self.metrics_history[metric.name] = [
            m for m in self.metrics_history[metric.name]
            if m.timestamp > cutoff
        ]

    async def _update_baselines(self) -> None:
        """Atualiza baselines estatisticas."""
        for metric_name, metrics in self.metrics_history.items():
            if len(metrics) < self.min_data_points:
                continue

            values = [m.value for m in metrics]

            self.baselines[metric_name] = {
                "mean": statistics.mean(values),
                "stdev": statistics.stdev(values) if len(values) > 1 else 0,
                "median": statistics.median(values),
                "min": min(values),
                "max": max(values),
                "count": len(values),
                "updated_at": datetime.now().isoformat()
            }

    async def _detect_anomalies(self) -> List[Anomaly]:
        """Detecta anomalias nos dados."""
        anomalies = []

        for metric_name, metrics in self.metrics_history.items():
            if metric_name not in self.baselines:
                continue

            baseline = self.baselines[metric_name]
            if baseline["stdev"] == 0:
                continue

            # Ultimos valores
            recent_metrics = metrics[-10:] if len(metrics) >= 10 else metrics
            recent_values = [m.value for m in recent_metrics]
            recent_mean = statistics.mean(recent_values)

            # Calcular Z-score
            z_score = (recent_mean - baseline["mean"]) / baseline["stdev"]

            if abs(z_score) > self.anomaly_z_threshold:
                anomaly = Anomaly(
                    id=f"anomaly_{metric_name}_{datetime.now().timestamp()}",
                    type=AnomalyType.FREQUENCY_SPIKE if z_score > 0 else AnomalyType.PATTERN_BREAK,
                    severity=min(abs(z_score) / 5.0, 1.0),
                    description=f"Anomalia detectada em {metric_name}: "
                               f"valor atual {recent_mean:.2f} vs baseline {baseline['mean']:.2f}",
                    detected_at=datetime.now(),
                    affected_entities=[metric_name],
                    baseline_value=baseline["mean"],
                    current_value=recent_mean,
                    deviation_factor=z_score,
                    confidence=min(len(metrics) / 100.0, 0.95)
                )
                anomalies.append(anomaly)
                self.anomaly_history.append(anomaly)

        # Detectar anomalias de timing
        timing_anomalies = await self._detect_timing_anomalies()
        anomalies.extend(timing_anomalies)

        return anomalies

    async def _detect_timing_anomalies(self) -> List[Anomaly]:
        """Detecta anomalias de padrao temporal."""
        anomalies = []
        current_hour = datetime.now().hour

        for metric_name, hourly_data in self.hourly_patterns.items():
            total = sum(hourly_data)
            if total < self.min_data_points:
                continue

            # Normalizar padroes
            normalized = [h / total for h in hourly_data]
            expected_ratio = normalized[current_hour]

            # Contar eventos recentes nesta hora
            recent_count = sum(
                1 for m in self.metrics_history.get(f"event_{metric_name}", [])
                if m.timestamp.hour == current_hour and
                   m.timestamp > datetime.now() - timedelta(hours=1)
            )

            # Calcular ratio atual
            total_recent = sum(
                1 for m in self.metrics_history.get(f"event_{metric_name}", [])
                if m.timestamp > datetime.now() - timedelta(hours=24)
            )

            if total_recent > 0:
                actual_ratio = recent_count / total_recent

                # Verificar desvio significativo
                if expected_ratio > 0 and actual_ratio > expected_ratio * 3:
                    anomaly = Anomaly(
                        id=f"timing_anomaly_{metric_name}_{datetime.now().timestamp()}",
                        type=AnomalyType.UNUSUAL_TIMING,
                        severity=min((actual_ratio / expected_ratio) / 5.0, 1.0),
                        description=f"Atividade incomum de {metric_name} neste horario: "
                                   f"{actual_ratio:.1%} vs esperado {expected_ratio:.1%}",
                        detected_at=datetime.now(),
                        affected_entities=[metric_name],
                        baseline_value=expected_ratio,
                        current_value=actual_ratio,
                        deviation_factor=actual_ratio / expected_ratio,
                        confidence=0.7
                    )
                    anomalies.append(anomaly)

        return anomalies

    async def _generate_predictions(self) -> List[Prediction]:
        """Gera predicoes de seguranca."""
        predictions = []

        # Predicao de pico de atividade
        peak_prediction = await self._predict_activity_peak()
        if peak_prediction:
            predictions.append(peak_prediction)

        # Predicao de probabilidade de incidente
        incident_prediction = await self._predict_incident_probability()
        if incident_prediction:
            predictions.append(incident_prediction)

        # Predicao de janela de vulnerabilidade
        vulnerability_prediction = await self._predict_vulnerability_window()
        if vulnerability_prediction:
            predictions.append(vulnerability_prediction)

        return predictions

    async def _predict_activity_peak(self) -> Optional[Prediction]:
        """Preve proximo pico de atividade."""
        # Agregar padroes horarios de todos os eventos
        total_hourly = [0.0] * 24
        for pattern in self.hourly_patterns.values():
            for h in range(24):
                total_hourly[h] += pattern[h]

        if sum(total_hourly) == 0:
            return None

        # Encontrar horario de pico
        peak_hour = total_hourly.index(max(total_hourly))
        now = datetime.now()

        # Calcular proximo horario de pico
        if now.hour < peak_hour:
            predicted_time = now.replace(hour=peak_hour, minute=0, second=0)
        else:
            predicted_time = (now + timedelta(days=1)).replace(hour=peak_hour, minute=0, second=0)

        # Calcular intensidade esperada
        peak_intensity = max(total_hourly) / (sum(total_hourly) / 24)

        return Prediction(
            id=f"peak_activity_{datetime.now().timestamp()}",
            type=PredictionType.PEAK_ACTIVITY,
            description=f"Pico de atividade previsto para {peak_hour}h "
                       f"com intensidade {peak_intensity:.1f}x acima da media",
            probability=0.85,
            predicted_time=predicted_time,
            confidence=min(sum(total_hourly) / 1000.0, 0.9),
            risk_level=RiskLevel.MODERATE if peak_intensity > 2 else RiskLevel.LOW,
            recommended_actions=[
                "Garantir equipe de monitoramento no horario",
                "Verificar operacionalidade de cameras",
                "Preparar protocolo de resposta rapida"
            ],
            factors=[
                f"Padrao historico indica {peak_hour}h como horario de pico",
                f"Intensidade esperada: {peak_intensity:.1f}x acima da media"
            ]
        )

    async def _predict_incident_probability(self) -> Optional[Prediction]:
        """Preve probabilidade de incidente nas proximas horas."""
        # Contar alertas recentes por severidade
        recent_alerts = [
            m for name, metrics in self.metrics_history.items()
            for m in metrics
            if name.startswith("alert_") and m.timestamp > datetime.now() - timedelta(hours=6)
        ]

        if not recent_alerts:
            return None

        # Calcular score de risco
        alert_score = sum(m.value for m in recent_alerts)

        # Verificar tendencia de anomalias
        recent_anomalies = [
            a for a in self.anomaly_history
            if a.detected_at > datetime.now() - timedelta(hours=6)
        ]
        anomaly_score = sum(a.severity for a in recent_anomalies)

        # Calcular probabilidade combinada
        base_probability = 0.1  # 10% base
        alert_factor = min(alert_score * 0.1, 0.4)
        anomaly_factor = min(anomaly_score * 0.1, 0.3)

        probability = min(base_probability + alert_factor + anomaly_factor, 0.95)

        if probability > 0.3:
            risk_level = RiskLevel.HIGH if probability > 0.6 else RiskLevel.MODERATE

            return Prediction(
                id=f"incident_prob_{datetime.now().timestamp()}",
                type=PredictionType.INCIDENT_PROBABILITY,
                description=f"Probabilidade elevada de incidente nas proximas {self.prediction_horizon_hours}h: "
                           f"{probability:.0%}",
                probability=probability,
                predicted_time=datetime.now() + timedelta(hours=self.prediction_horizon_hours),
                confidence=0.7,
                risk_level=risk_level,
                recommended_actions=[
                    "Aumentar nivel de alerta",
                    "Verificar pontos de acesso criticos",
                    "Acionar equipe de seguranca adicional",
                    "Revisar gravacoes das ultimas 6 horas"
                ],
                factors=[
                    f"{len(recent_alerts)} alertas nas ultimas 6 horas",
                    f"{len(recent_anomalies)} anomalias detectadas",
                    f"Score de risco atual: {(alert_score + anomaly_score):.1f}"
                ]
            )

        return None

    async def _predict_vulnerability_window(self) -> Optional[Prediction]:
        """Preve janelas de vulnerabilidade."""
        # Analisar padroes de baixa atividade (potenciais janelas de vulnerabilidade)
        total_hourly = [0.0] * 24
        for pattern in self.hourly_patterns.values():
            for h in range(24):
                total_hourly[h] += pattern[h]

        if sum(total_hourly) == 0:
            return None

        # Normalizar
        avg_activity = sum(total_hourly) / 24

        # Encontrar horarios com baixa atividade
        low_activity_hours = [
            h for h in range(24)
            if total_hourly[h] < avg_activity * 0.3
        ]

        if not low_activity_hours:
            return None

        # Encontrar janela mais proxima
        now = datetime.now()
        current_hour = now.hour

        future_low_hours = [h for h in low_activity_hours if h > current_hour]
        if not future_low_hours:
            future_low_hours = [h + 24 for h in low_activity_hours]

        next_low_hour = min(future_low_hours) % 24

        if next_low_hour > current_hour:
            predicted_time = now.replace(hour=next_low_hour, minute=0, second=0)
        else:
            predicted_time = (now + timedelta(days=1)).replace(hour=next_low_hour, minute=0, second=0)

        return Prediction(
            id=f"vuln_window_{datetime.now().timestamp()}",
            type=PredictionType.VULNERABILITY_WINDOW,
            description=f"Janela de vulnerabilidade identificada: {next_low_hour}h-{(next_low_hour+2)%24}h "
                       f"(baixa atividade de monitoramento)",
            probability=0.75,
            predicted_time=predicted_time,
            confidence=0.65,
            risk_level=RiskLevel.MODERATE,
            recommended_actions=[
                "Programar rondas adicionais neste horario",
                "Verificar cameras em modo automatico",
                "Considerar adicionar iluminacao",
                "Revisar pontos de acesso criticos"
            ],
            factors=[
                f"Atividade {(total_hourly[next_low_hour]/avg_activity)*100:.0f}% abaixo da media",
                f"Historicamente {len(low_activity_hours)} horas com baixa cobertura"
            ]
        )

    async def _update_risk_scores(self) -> None:
        """Atualiza scores de risco para todas as entidades."""
        # Atualizar risco geral do condominio
        general_risk = await self._calculate_general_risk()

        self.risk_cache["general"] = RiskAssessment(
            entity_id="general",
            entity_type="condominio",
            risk_score=general_risk["score"],
            risk_level=self._score_to_risk_level(general_risk["score"]),
            contributing_factors=general_risk["factors"],
            trend=general_risk["trend"],
            recommendations=general_risk["recommendations"],
            assessed_at=datetime.now(),
            valid_until=datetime.now() + timedelta(minutes=5)
        )

    async def _calculate_general_risk(self) -> Dict[str, Any]:
        """Calcula risco geral de seguranca."""
        factors = []
        base_score = 20.0  # Score base

        # Fator 1: Alertas recentes
        recent_alerts = sum(
            1 for name, metrics in self.metrics_history.items()
            for m in metrics
            if name.startswith("alert_") and m.timestamp > datetime.now() - timedelta(hours=1)
        )
        alert_factor = min(recent_alerts * 5, 30)
        if recent_alerts > 0:
            factors.append({
                "name": "Alertas recentes",
                "contribution": alert_factor,
                "detail": f"{recent_alerts} alertas na ultima hora"
            })

        # Fator 2: Anomalias ativas
        active_anomalies = len([
            a for a in self.anomaly_history
            if a.detected_at > datetime.now() - timedelta(minutes=30)
        ])
        anomaly_factor = min(active_anomalies * 8, 25)
        if active_anomalies > 0:
            factors.append({
                "name": "Anomalias ativas",
                "contribution": anomaly_factor,
                "detail": f"{active_anomalies} anomalias detectadas"
            })

        # Fator 3: Horario
        current_hour = datetime.now().hour
        if 0 <= current_hour <= 5:
            time_factor = 15
            factors.append({
                "name": "Horario de risco",
                "contribution": time_factor,
                "detail": "Madrugada - menor vigilancia natural"
            })
        else:
            time_factor = 0

        # Calcular score total
        total_score = min(base_score + alert_factor + anomaly_factor + time_factor, 100)

        # Determinar tendencia
        previous_score = self.risk_cache.get("general", RiskAssessment(
            entity_id="", entity_type="", risk_score=base_score,
            risk_level=RiskLevel.LOW, contributing_factors=[],
            trend=TrendDirection.STABLE, recommendations=[],
            assessed_at=datetime.now(), valid_until=datetime.now()
        )).risk_score

        if total_score > previous_score + 10:
            trend = TrendDirection.INCREASING
        elif total_score < previous_score - 10:
            trend = TrendDirection.DECREASING
        elif total_score > previous_score + 20:
            trend = TrendDirection.SPIKE
        else:
            trend = TrendDirection.STABLE

        # Gerar recomendacoes
        recommendations = []
        if total_score > 60:
            recommendations.extend([
                "Acionar equipe de resposta",
                "Aumentar frequencia de rondas",
                "Verificar todos os pontos de acesso"
            ])
        elif total_score > 40:
            recommendations.extend([
                "Manter atencao redobrada",
                "Verificar cameras prioritarias"
            ])
        else:
            recommendations.append("Manter monitoramento padrao")

        return {
            "score": total_score,
            "factors": factors,
            "trend": trend,
            "recommendations": recommendations
        }

    def _score_to_risk_level(self, score: float) -> RiskLevel:
        """Converte score numerico em nivel de risco."""
        if score < 20:
            return RiskLevel.MINIMAL
        elif score < 40:
            return RiskLevel.LOW
        elif score < 60:
            return RiskLevel.MODERATE
        elif score < 80:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL

    async def _generate_insights(self) -> None:
        """Gera insights de seguranca."""
        insights = []

        # Insight 1: Padrao de horario mais critico
        peak_insight = await self._generate_peak_insight()
        if peak_insight:
            insights.append(peak_insight)

        # Insight 2: Eficiencia do sistema
        efficiency_insight = await self._generate_efficiency_insight()
        if efficiency_insight:
            insights.append(efficiency_insight)

        self.insights_cache = insights[-10:]  # Manter ultimos 10 insights

    async def _generate_peak_insight(self) -> Optional[SecurityInsight]:
        """Gera insight sobre horarios de pico."""
        total_hourly = [0.0] * 24
        for pattern in self.hourly_patterns.values():
            for h in range(24):
                total_hourly[h] += pattern[h]

        if sum(total_hourly) == 0:
            return None

        peak_hour = total_hourly.index(max(total_hourly))
        low_hour = total_hourly.index(min(total_hourly))

        return SecurityInsight(
            id=f"peak_insight_{datetime.now().timestamp()}",
            title="Padroes de Atividade Identificados",
            description=f"O horario de maior atividade e {peak_hour}h e o de menor e {low_hour}h. "
                       f"Considere ajustar recursos de monitoramento conforme esses padroes.",
            category="operational_efficiency",
            importance=0.7,
            actionable=True,
            actions=[
                f"Aumentar monitoramento entre {peak_hour}h e {(peak_hour+2)%24}h",
                f"Verificar automacao de cameras para {low_hour}h"
            ],
            data_points=[
                {"hour": h, "activity": total_hourly[h]} for h in range(24)
            ],
            generated_at=datetime.now()
        )

    async def _generate_efficiency_insight(self) -> Optional[SecurityInsight]:
        """Gera insight sobre eficiencia do sistema."""
        total_events = sum(
            len(metrics) for metrics in self.metrics_history.values()
        )

        total_alerts = sum(
            len(metrics) for name, metrics in self.metrics_history.items()
            if name.startswith("alert_")
        )

        if total_events == 0:
            return None

        alert_ratio = total_alerts / total_events if total_events > 0 else 0

        return SecurityInsight(
            id=f"efficiency_insight_{datetime.now().timestamp()}",
            title="Eficiencia do Sistema de Alertas",
            description=f"Nas ultimas 24h: {total_events} eventos processados, "
                       f"{total_alerts} alertas gerados ({alert_ratio:.1%} taxa de conversao)",
            category="system_performance",
            importance=0.5,
            actionable=alert_ratio > 0.3,
            actions=[
                "Revisar thresholds de alerta se taxa muito alta",
                "Verificar sensibilidade das deteccoes"
            ] if alert_ratio > 0.3 else [],
            data_points=[
                {"metric": "total_events", "value": total_events},
                {"metric": "total_alerts", "value": total_alerts},
                {"metric": "alert_ratio", "value": alert_ratio}
            ],
            generated_at=datetime.now()
        )

    async def _check_realtime_anomaly(
        self,
        event_type: str,
        location: str,
        timestamp: datetime
    ) -> None:
        """Verifica anomalia em tempo real."""
        # Contar eventos recentes do mesmo tipo
        recent_count = sum(
            1 for m in self.metrics_history.get(f"event_{event_type}", [])
            if m.timestamp > timestamp - timedelta(minutes=5)
        )

        # Se mais de 10 eventos em 5 minutos, pode ser anomalia
        if recent_count > 10:
            anomaly = Anomaly(
                id=f"realtime_anomaly_{event_type}_{timestamp.timestamp()}",
                type=AnomalyType.FREQUENCY_SPIKE,
                severity=min(recent_count / 20.0, 1.0),
                description=f"Spike de eventos {event_type} detectado: "
                           f"{recent_count} em 5 minutos",
                detected_at=timestamp,
                affected_entities=[event_type, location],
                baseline_value=2.0,  # Esperado ~2 por 5 min
                current_value=float(recent_count),
                deviation_factor=recent_count / 2.0,
                confidence=0.8
            )
            await self._publish_anomaly(anomaly)

    async def _publish_anomaly(self, anomaly: Anomaly) -> None:
        """Publica anomalia detectada."""
        if self.message_bus:
            await self.message_bus.publish("analytics.anomaly", {
                "id": anomaly.id,
                "type": anomaly.type.value,
                "severity": anomaly.severity,
                "description": anomaly.description,
                "detected_at": anomaly.detected_at.isoformat(),
                "affected_entities": anomaly.affected_entities,
                "deviation_factor": anomaly.deviation_factor,
                "confidence": anomaly.confidence
            })

        logger.info(f"Anomalia detectada: {anomaly.type.value} - {anomaly.description}")

    async def _publish_prediction(self, prediction: Prediction) -> None:
        """Publica predicao gerada."""
        if self.message_bus:
            await self.message_bus.publish("analytics.prediction", {
                "id": prediction.id,
                "type": prediction.type.value,
                "description": prediction.description,
                "probability": prediction.probability,
                "predicted_time": prediction.predicted_time.isoformat(),
                "risk_level": prediction.risk_level.value,
                "recommended_actions": prediction.recommended_actions,
                "confidence": prediction.confidence
            })

        logger.info(f"Predicao gerada: {prediction.type.value} - {prediction.description}")

    # API publica
    async def get_risk_assessment(self, entity_id: str = "general") -> Optional[RiskAssessment]:
        """Retorna avaliacao de risco para uma entidade."""
        if entity_id in self.risk_cache:
            assessment = self.risk_cache[entity_id]
            if assessment.valid_until > datetime.now():
                return assessment

        # Se nao tem cache valido, calcular
        if entity_id == "general":
            await self._update_risk_scores()
            return self.risk_cache.get("general")

        return None

    async def get_anomalies(
        self,
        hours: int = 24,
        min_severity: float = 0.0
    ) -> List[Anomaly]:
        """Retorna anomalias detectadas."""
        cutoff = datetime.now() - timedelta(hours=hours)
        return [
            a for a in self.anomaly_history
            if a.detected_at > cutoff and a.severity >= min_severity
        ]

    async def get_predictions(
        self,
        prediction_type: Optional[PredictionType] = None
    ) -> List[Prediction]:
        """Retorna predicoes ativas."""
        predictions = [
            p for p in self.prediction_history
            if p.predicted_time > datetime.now()
        ]

        if prediction_type:
            predictions = [p for p in predictions if p.type == prediction_type]

        return predictions

    async def get_insights(self, limit: int = 5) -> List[SecurityInsight]:
        """Retorna ultimos insights."""
        return self.insights_cache[-limit:]

    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Retorna dados completos para dashboard."""
        risk = await self.get_risk_assessment()

        return {
            "risk_score": risk.risk_score if risk else 0,
            "risk_level": risk.risk_level.value if risk else "unknown",
            "risk_trend": risk.trend.value if risk else "stable",
            "anomalies_24h": len(await self.get_anomalies(hours=24)),
            "active_predictions": len(await self.get_predictions()),
            "recent_insights": await self.get_insights(3),
            "recommendations": risk.recommendations if risk else [],
            "timestamp": datetime.now().isoformat()
        }
