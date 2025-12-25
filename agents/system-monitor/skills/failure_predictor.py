"""
Skill: Failure Predictor (Preditor de Falhas)
Sistema preditivo que analisa tendências e prevê falhas antes que ocorram

Princípios:
- Análise de tendências históricas
- Detecção de degradação progressiva
- Correlação de padrões preditivos
- Alertas antecipados
"""

import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
import statistics
import math


class FailurePredictor:
    """
    Preditor de Falhas

    Analisa:
    - Tendências de métricas
    - Padrões de degradação
    - Frequência de erros
    - Correlações temporais

    Prevê:
    - Tempo estimado até falha
    - Probabilidade de falha
    - Tipo provável de falha
    """

    # Thresholds críticos
    CRITICAL_THRESHOLDS = {
        'cpu': 95,
        'memory': 95,
        'disk': 90,
        'response_time_ms': 5000,
        'error_rate': 10,  # %
    }

    # Thresholds de alerta
    WARNING_THRESHOLDS = {
        'cpu': 80,
        'memory': 80,
        'disk': 75,
        'response_time_ms': 2000,
        'error_rate': 5,
    }

    # Padrões preditivos conhecidos
    PREDICTIVE_PATTERNS = [
        {
            'id': 'memory_exhaustion',
            'name': 'Esgotamento de Memória',
            'indicators': ['memory_increasing', 'memory_high'],
            'prediction': 'Sistema ficará sem memória',
            'severity': 'critical'
        },
        {
            'id': 'disk_full',
            'name': 'Disco Cheio',
            'indicators': ['disk_increasing', 'disk_high'],
            'prediction': 'Disco ficará cheio',
            'severity': 'critical'
        },
        {
            'id': 'cascade_failure',
            'name': 'Falha em Cascata',
            'indicators': ['error_rate_increasing', 'response_time_increasing', 'cpu_high'],
            'prediction': 'Possível falha em cascata',
            'severity': 'high'
        },
        {
            'id': 'resource_contention',
            'name': 'Contenção de Recursos',
            'indicators': ['cpu_high', 'memory_high', 'response_time_increasing'],
            'prediction': 'Contenção de recursos iminente',
            'severity': 'high'
        },
        {
            'id': 'slow_degradation',
            'name': 'Degradação Lenta',
            'indicators': ['response_time_increasing', 'error_rate_slight_increase'],
            'prediction': 'Degradação progressiva do serviço',
            'severity': 'medium'
        }
    ]

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.state_dir = Path('/opt/conecta-plus/agents/system-monitor/state')
        self.state_dir.mkdir(parents=True, exist_ok=True)

        self.history_file = self.state_dir / 'metrics_history.json'
        self.predictions_file = self.state_dir / 'predictions.json'

        self.history = self._load_history()
        self.predictions = self._load_predictions()

        # Configuração
        self.prediction_config = {
            'history_window_hours': 24,    # Janela de análise
            'min_samples': 5,              # Mínimo de amostras para predição
            'trend_sensitivity': 0.05,     # Sensibilidade para detectar tendência
            'prediction_horizon_hours': 6, # Horizonte de predição
        }

    def _load_history(self) -> Dict[str, Any]:
        """Carrega histórico de métricas"""
        try:
            if self.history_file.exists():
                with open(self.history_file) as f:
                    return json.load(f)
        except:
            pass
        return {
            'metrics': {},      # {metric_name: [{value, timestamp}]}
            'events': [],       # Eventos importantes
            'anomalies': [],    # Anomalias detectadas
        }

    def _save_history(self):
        """Salva histórico"""
        with open(self.history_file, 'w') as f:
            json.dump(self.history, f, indent=2, default=str)

    def _load_predictions(self) -> Dict[str, Any]:
        """Carrega predições anteriores"""
        try:
            if self.predictions_file.exists():
                with open(self.predictions_file) as f:
                    return json.load(f)
        except:
            pass
        return {
            'active': [],       # Predições ativas
            'past': [],         # Predições passadas (para validação)
            'accuracy': {       # Acurácia histórica
                'total': 0,
                'correct': 0,
                'rate': 0
            }
        }

    def _save_predictions(self):
        """Salva predições"""
        with open(self.predictions_file, 'w') as f:
            json.dump(self.predictions, f, indent=2, default=str)

    def record_metrics(self, metrics: Dict[str, Any]):
        """
        Registra métricas para análise de tendência

        Args:
            metrics: Dicionário de métricas atuais
        """
        now = datetime.now()

        for metric_name, value in metrics.items():
            # Extrair valor numérico
            if isinstance(value, dict):
                numeric_value = value.get('percent', value.get('value', 0))
            else:
                numeric_value = value

            if not isinstance(numeric_value, (int, float)):
                continue

            # Inicializar se necessário
            if metric_name not in self.history['metrics']:
                self.history['metrics'][metric_name] = []

            # Adicionar ponto
            self.history['metrics'][metric_name].append({
                'value': numeric_value,
                'timestamp': now.isoformat()
            })

            # Manter apenas últimas 1000 amostras por métrica
            self.history['metrics'][metric_name] = \
                self.history['metrics'][metric_name][-1000:]

        self._save_history()

    def predict(self, current_metrics: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Gera predições de falhas

        Returns:
            Análise preditiva completa
        """
        now = datetime.now()

        # Registrar métricas atuais se fornecidas
        if current_metrics:
            self.record_metrics(current_metrics)

        prediction_result = {
            'timestamp': now.isoformat(),
            'predictions': [],
            'trends': {},
            'time_to_failure': {},
            'risk_level': 'low',
            'warnings': [],
            'recommendations': []
        }

        # 1. Analisar tendências
        trends = self._analyze_trends()
        prediction_result['trends'] = trends

        # 2. Calcular tempo até falha
        ttf = self._calculate_time_to_failure(trends)
        prediction_result['time_to_failure'] = ttf

        # 3. Detectar padrões preditivos
        patterns = self._match_predictive_patterns(trends)
        prediction_result['predictions'].extend(patterns)

        # 4. Detectar anomalias
        anomalies = self._detect_anomalies()
        if anomalies:
            prediction_result['predictions'].extend(anomalies)

        # 5. Determinar nível de risco
        prediction_result['risk_level'] = self._calculate_risk_level(
            prediction_result['predictions'],
            ttf
        )

        # 6. Gerar recomendações
        prediction_result['recommendations'] = self._generate_recommendations(
            prediction_result
        )

        # 7. Gerar warnings
        prediction_result['warnings'] = self._generate_warnings(
            prediction_result
        )

        # Salvar predição ativa
        self._save_active_prediction(prediction_result)

        return prediction_result

    def _analyze_trends(self) -> Dict[str, Any]:
        """Analisa tendências em todas as métricas"""
        trends = {}
        now = datetime.now()
        window = timedelta(hours=self.prediction_config['history_window_hours'])
        cutoff = now - window

        for metric_name, data_points in self.history['metrics'].items():
            # Filtrar pontos dentro da janela
            recent_points = []
            for point in data_points:
                try:
                    ts = datetime.fromisoformat(point['timestamp'])
                    if ts >= cutoff:
                        recent_points.append({
                            'value': point['value'],
                            'timestamp': ts
                        })
                except:
                    pass

            if len(recent_points) < self.prediction_config['min_samples']:
                trends[metric_name] = {
                    'trend': 'insufficient_data',
                    'samples': len(recent_points)
                }
                continue

            # Calcular tendência
            trend_info = self._calculate_trend(recent_points)
            trends[metric_name] = trend_info

        return trends

    def _calculate_trend(self, points: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calcula tendência para uma série de pontos"""
        values = [p['value'] for p in points]

        # Estatísticas básicas
        current = values[-1]
        mean = statistics.mean(values)
        std = statistics.stdev(values) if len(values) >= 2 else 0

        # Regressão linear simples para tendência
        n = len(values)
        x = list(range(n))
        x_mean = sum(x) / n
        y_mean = mean

        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

        if denominator != 0:
            slope = numerator / denominator
        else:
            slope = 0

        # Determinar direção
        sensitivity = self.prediction_config['trend_sensitivity']
        if abs(slope) < sensitivity:
            direction = 'stable'
        elif slope > 0:
            direction = 'increasing'
        else:
            direction = 'decreasing'

        # Calcular taxa de mudança (% por hora)
        if mean != 0:
            rate_per_sample = slope / mean * 100
        else:
            rate_per_sample = 0

        # Estimar tempo de amostragem
        if len(points) >= 2:
            time_span = (points[-1]['timestamp'] - points[0]['timestamp']).total_seconds() / 3600
            samples_per_hour = n / max(time_span, 1)
            rate_per_hour = rate_per_sample * samples_per_hour
        else:
            rate_per_hour = 0

        return {
            'direction': direction,
            'slope': round(slope, 4),
            'rate_per_hour': round(rate_per_hour, 2),
            'current': round(current, 2),
            'mean': round(mean, 2),
            'std': round(std, 2),
            'min': round(min(values), 2),
            'max': round(max(values), 2),
            'samples': n
        }

    def _calculate_time_to_failure(
        self,
        trends: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calcula tempo estimado até falha para cada métrica"""
        ttf = {}

        for metric_name, trend in trends.items():
            if trend.get('trend') == 'insufficient_data':
                continue

            direction = trend.get('direction')
            current = trend.get('current', 0)
            rate = trend.get('rate_per_hour', 0)

            # Verificar threshold crítico
            critical = self.CRITICAL_THRESHOLDS.get(metric_name)
            warning = self.WARNING_THRESHOLDS.get(metric_name)

            if critical is None:
                continue

            # Se está aumentando em direção ao threshold
            if direction == 'increasing' and current < critical and rate > 0:
                remaining = critical - current
                hours_to_critical = remaining / rate if rate > 0 else float('inf')

                if hours_to_critical < float('inf'):
                    ttf[metric_name] = {
                        'hours_to_critical': round(hours_to_critical, 1),
                        'current': current,
                        'threshold': critical,
                        'rate': f"+{rate:.1f}%/h",
                        'severity': 'critical' if hours_to_critical < 2 else (
                            'high' if hours_to_critical < 6 else 'medium'
                        )
                    }

                # Warning threshold
                if warning and current < warning:
                    remaining_warn = warning - current
                    hours_to_warning = remaining_warn / rate if rate > 0 else float('inf')
                    if hours_to_warning < hours_to_critical:
                        ttf[metric_name]['hours_to_warning'] = round(hours_to_warning, 1)

        return ttf

    def _match_predictive_patterns(
        self,
        trends: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Identifica padrões preditivos ativados"""
        matched = []

        # Gerar indicadores ativos
        active_indicators = set()

        for metric, trend in trends.items():
            if isinstance(trend, dict):
                direction = trend.get('direction', '')
                current = trend.get('current', 0)

                # Verificar thresholds
                warning = self.WARNING_THRESHOLDS.get(metric, 100)
                critical = self.CRITICAL_THRESHOLDS.get(metric, 100)

                if current >= critical:
                    active_indicators.add(f'{metric}_critical')
                elif current >= warning:
                    active_indicators.add(f'{metric}_high')

                if direction == 'increasing':
                    active_indicators.add(f'{metric}_increasing')
                elif direction == 'decreasing':
                    active_indicators.add(f'{metric}_decreasing')

        # Verificar padrões
        for pattern in self.PREDICTIVE_PATTERNS:
            matching_indicators = 0
            required = len(pattern['indicators'])

            for indicator in pattern['indicators']:
                if indicator in active_indicators:
                    matching_indicators += 1
                # Verificar variações (high == critical || high)
                if indicator.endswith('_high'):
                    base = indicator.replace('_high', '')
                    if f'{base}_critical' in active_indicators:
                        matching_indicators += 1

            # Padrão ativado se maioria dos indicadores presentes
            if matching_indicators >= required * 0.6:
                confidence = matching_indicators / required
                matched.append({
                    'pattern_id': pattern['id'],
                    'pattern_name': pattern['name'],
                    'prediction': pattern['prediction'],
                    'severity': pattern['severity'],
                    'confidence': round(confidence, 2),
                    'matching_indicators': matching_indicators,
                    'required_indicators': required
                })

        return matched

    def _detect_anomalies(self) -> List[Dict[str, Any]]:
        """Detecta anomalias nas métricas"""
        anomalies = []

        for metric_name, data_points in self.history['metrics'].items():
            if len(data_points) < 10:
                continue

            values = [p['value'] for p in data_points[-50:]]  # Últimos 50
            current = values[-1]
            mean = statistics.mean(values[:-1])
            std = statistics.stdev(values[:-1]) if len(values) > 2 else 1

            # Z-score
            if std > 0:
                z_score = (current - mean) / std
            else:
                z_score = 0

            # Anomalia se z-score > 3 (muito fora do normal)
            if abs(z_score) > 3:
                anomalies.append({
                    'type': 'anomaly',
                    'metric': metric_name,
                    'current': current,
                    'expected_range': f"{mean - 2*std:.1f} - {mean + 2*std:.1f}",
                    'z_score': round(z_score, 2),
                    'severity': 'high' if abs(z_score) > 4 else 'medium',
                    'prediction': f'Valor anômalo em {metric_name}'
                })

        return anomalies

    def _calculate_risk_level(
        self,
        predictions: List[Dict[str, Any]],
        ttf: Dict[str, Any]
    ) -> str:
        """Calcula nível de risco geral"""
        risk_score = 0

        # Pontuação por predições
        for pred in predictions:
            severity = pred.get('severity', 'low')
            confidence = pred.get('confidence', 0.5)

            if severity == 'critical':
                risk_score += 30 * confidence
            elif severity == 'high':
                risk_score += 20 * confidence
            elif severity == 'medium':
                risk_score += 10 * confidence

        # Pontuação por tempo até falha
        for metric, info in ttf.items():
            hours = info.get('hours_to_critical', float('inf'))
            if hours < 1:
                risk_score += 40
            elif hours < 2:
                risk_score += 30
            elif hours < 6:
                risk_score += 20
            elif hours < 24:
                risk_score += 10

        # Determinar nível
        if risk_score >= 60:
            return 'critical'
        elif risk_score >= 40:
            return 'high'
        elif risk_score >= 20:
            return 'medium'
        else:
            return 'low'

    def _generate_recommendations(
        self,
        prediction_result: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Gera recomendações baseadas nas predições"""
        recommendations = []

        # Recomendações por tempo até falha
        for metric, info in prediction_result.get('time_to_failure', {}).items():
            hours = info.get('hours_to_critical', float('inf'))

            if hours < 2:
                recommendations.append({
                    'priority': 'critical',
                    'action': f'Ação imediata necessária para {metric}',
                    'reason': f'{metric} atingirá nível crítico em {hours:.1f}h',
                    'suggestions': self._get_metric_actions(metric)
                })
            elif hours < 6:
                recommendations.append({
                    'priority': 'high',
                    'action': f'Investigar {metric}',
                    'reason': f'{metric} em tendência de alta',
                    'suggestions': self._get_metric_actions(metric)
                })

        # Recomendações por padrões
        for pred in prediction_result.get('predictions', []):
            if pred.get('confidence', 0) >= 0.7:
                pattern_id = pred.get('pattern_id', '')
                recommendations.append({
                    'priority': pred.get('severity', 'medium'),
                    'action': f"Prevenir {pred.get('pattern_name', 'problema')}",
                    'reason': pred.get('prediction', ''),
                    'suggestions': self._get_pattern_actions(pattern_id)
                })

        return recommendations

    def _generate_warnings(
        self,
        prediction_result: Dict[str, Any]
    ) -> List[str]:
        """Gera warnings em texto"""
        warnings = []

        risk = prediction_result.get('risk_level', 'low')
        if risk in ['critical', 'high']:
            warnings.append(f"RISCO {risk.upper()}: Sistema requer atenção")

        for pred in prediction_result.get('predictions', []):
            if pred.get('confidence', 0) >= 0.8:
                warnings.append(
                    f"Predição: {pred.get('prediction')} "
                    f"(confiança: {pred.get('confidence'):.0%})"
                )

        for metric, info in prediction_result.get('time_to_failure', {}).items():
            hours = info.get('hours_to_critical')
            if hours and hours < 6:
                warnings.append(
                    f"{metric.upper()} crítico em ~{hours:.1f}h "
                    f"(atual: {info.get('current')}, limite: {info.get('threshold')})"
                )

        return warnings

    def _get_metric_actions(self, metric: str) -> List[str]:
        """Retorna ações sugeridas para uma métrica"""
        actions = {
            'cpu': [
                'Identificar processos consumindo CPU',
                'Considerar escalar horizontalmente',
                'Otimizar código hotspots'
            ],
            'memory': [
                'Verificar memory leaks',
                'Reiniciar serviços com alto consumo',
                'Aumentar memória disponível'
            ],
            'disk': [
                'Limpar logs antigos',
                'Remover arquivos temporários',
                'Expandir storage'
            ],
            'response_time_ms': [
                'Verificar queries lentas',
                'Analisar gargalos de rede',
                'Verificar cache'
            ]
        }
        return actions.get(metric, ['Investigar causa raiz'])

    def _get_pattern_actions(self, pattern_id: str) -> List[str]:
        """Retorna ações sugeridas para um padrão"""
        actions = {
            'memory_exhaustion': [
                'Reiniciar serviço afetado',
                'Analisar heap dump',
                'Aumentar limites de memória'
            ],
            'disk_full': [
                'Rotacionar logs',
                'Limpar cache',
                'Arquivar dados antigos'
            ],
            'cascade_failure': [
                'Ativar circuit breaker',
                'Isolar componente falho',
                'Escalar recursos'
            ],
            'resource_contention': [
                'Limitar requisições',
                'Escalar horizontalmente',
                'Otimizar alocação'
            ],
            'slow_degradation': [
                'Monitorar de perto',
                'Identificar causa raiz',
                'Preparar plano de mitigação'
            ]
        }
        return actions.get(pattern_id, ['Investigar e monitorar'])

    def _save_active_prediction(self, prediction: Dict[str, Any]):
        """Salva predição ativa para validação futura"""
        # Mover predições antigas para histórico
        now = datetime.now()
        cutoff = now - timedelta(hours=24)

        active = []
        for pred in self.predictions.get('active', []):
            try:
                ts = datetime.fromisoformat(pred.get('timestamp', '2000-01-01'))
                if ts >= cutoff:
                    active.append(pred)
                else:
                    self.predictions['past'].append(pred)
            except:
                pass

        # Adicionar nova predição
        active.append({
            'timestamp': prediction['timestamp'],
            'risk_level': prediction['risk_level'],
            'predictions_count': len(prediction.get('predictions', [])),
            'ttf_count': len(prediction.get('time_to_failure', {})),
            'warnings': prediction.get('warnings', [])
        })

        self.predictions['active'] = active[-100:]  # Últimas 100
        self.predictions['past'] = self.predictions['past'][-500:]  # Últimas 500

        self._save_predictions()

    def get_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas do preditor"""
        metrics_tracked = len(self.history.get('metrics', {}))
        total_samples = sum(
            len(v) for v in self.history.get('metrics', {}).values()
        )

        return {
            'metrics_tracked': metrics_tracked,
            'total_samples': total_samples,
            'active_predictions': len(self.predictions.get('active', [])),
            'past_predictions': len(self.predictions.get('past', [])),
            'prediction_accuracy': self.predictions.get('accuracy', {})
        }


if __name__ == '__main__':
    # Teste
    predictor = FailurePredictor({})

    # Simular métricas crescentes
    import time
    for i in range(20):
        predictor.record_metrics({
            'cpu': {'percent': 50 + i * 2},  # Crescendo
            'memory': {'percent': 60 + i * 1.5},  # Crescendo
            'disk': {'percent': 70}  # Estável
        })

    # Gerar predição
    result = predictor.predict()

    print("=== Predição de Falhas ===\n")
    print(f"Nível de Risco: {result['risk_level'].upper()}")
    print(f"\nTendências:")
    for metric, trend in result['trends'].items():
        if isinstance(trend, dict) and trend.get('direction') != 'insufficient_data':
            print(f"  {metric}: {trend['direction']} ({trend['rate_per_hour']:+.1f}%/h)")

    print(f"\nTempo até Falha:")
    for metric, ttf in result['time_to_failure'].items():
        print(f"  {metric}: {ttf['hours_to_critical']:.1f}h até crítico")

    print(f"\nWarnings:")
    for warning in result['warnings']:
        print(f"  - {warning}")

    print(f"\nRecomendações:")
    for rec in result['recommendations']:
        print(f"  [{rec['priority'].upper()}] {rec['action']}")
