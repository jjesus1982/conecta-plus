"""
Skill: Evolutionary Health Score (Health Score Evolutivo)
Sistema de pontuação de saúde que evolui com o tempo e considera múltiplos fatores

Princípios:
- Score multidimensional (não apenas gaps)
- Pesos dinâmicos baseados em contexto
- Tendência temporal (melhorando ou piorando)
- Benchmarks adaptativos
"""

import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
import statistics
import math


class EvolutionaryHealthScore:
    """
    Health Score Evolutivo

    Dimensões do Score:
    - Infrastructure (CPU, Memory, Disk)
    - Application (Response Time, Error Rate)
    - Code Quality (Gaps, Technical Debt)
    - Security (Vulnerabilities, Compliance)
    - Reliability (Uptime, Recovery)

    Evolução:
    - Tendência temporal
    - Comparação com baseline
    - Benchmarks adaptativos
    """

    # Dimensões e seus pesos default
    DIMENSIONS = {
        'infrastructure': {
            'weight': 0.25,
            'components': ['cpu', 'memory', 'disk', 'network']
        },
        'application': {
            'weight': 0.25,
            'components': ['response_time', 'error_rate', 'throughput']
        },
        'code_quality': {
            'weight': 0.20,
            'components': ['gaps', 'technical_debt', 'test_coverage']
        },
        'security': {
            'weight': 0.15,
            'components': ['vulnerabilities', 'compliance', 'access_control']
        },
        'reliability': {
            'weight': 0.15,
            'components': ['uptime', 'mttr', 'healing_success']
        }
    }

    # Thresholds para classificação
    SCORE_LEVELS = {
        'excellent': (90, 100),
        'good': (75, 89),
        'fair': (60, 74),
        'poor': (40, 59),
        'critical': (0, 39)
    }

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.state_dir = Path('/opt/conecta-plus/agents/system-monitor/state')
        self.state_dir.mkdir(parents=True, exist_ok=True)

        self.history_file = self.state_dir / 'health_score_history.json'
        self.baseline_file = self.state_dir / 'health_baseline.json'

        self.history = self._load_history()
        self.baseline = self._load_baseline()

        # Configuração de evolução
        self.evolution_config = {
            'history_days': 30,           # Dias de histórico
            'baseline_samples': 50,       # Amostras para baseline
            'trend_window_hours': 24,     # Janela para cálculo de tendência
            'improvement_threshold': 5,   # Melhoria mínima significativa
        }

    def _load_history(self) -> Dict[str, Any]:
        """Carrega histórico de scores"""
        try:
            if self.history_file.exists():
                with open(self.history_file) as f:
                    return json.load(f)
        except:
            pass
        return {
            'scores': [],           # Histórico de scores
            'dimension_scores': {}, # Scores por dimensão
            'daily_averages': {},   # Médias diárias
            'trends': {},           # Tendências calculadas
        }

    def _save_history(self):
        """Salva histórico"""
        with open(self.history_file, 'w') as f:
            json.dump(self.history, f, indent=2, default=str)

    def _load_baseline(self) -> Dict[str, Any]:
        """Carrega baseline"""
        try:
            if self.baseline_file.exists():
                with open(self.baseline_file) as f:
                    return json.load(f)
        except:
            pass
        return {
            'overall': 70,  # Score baseline default
            'dimensions': {},
            'last_updated': None,
            'samples': 0
        }

    def _save_baseline(self):
        """Salva baseline"""
        with open(self.baseline_file, 'w') as f:
            json.dump(self.baseline, f, indent=2, default=str)

    def calculate(
        self,
        metrics: Dict[str, Any],
        gaps: Dict[str, Any],
        correlation_data: Dict[str, Any] = None,
        prediction_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Calcula o Health Score evolutivo

        Args:
            metrics: Métricas atuais do sistema
            gaps: Gaps detectados
            correlation_data: Dados de correlação
            prediction_data: Dados de predição

        Returns:
            Score completo com dimensões, tendência e recomendações
        """
        now = datetime.now()

        # 1. Calcular score por dimensão
        dimension_scores = {}

        dimension_scores['infrastructure'] = self._calc_infrastructure_score(metrics)
        dimension_scores['application'] = self._calc_application_score(metrics)
        dimension_scores['code_quality'] = self._calc_code_quality_score(gaps)
        dimension_scores['security'] = self._calc_security_score(gaps)
        dimension_scores['reliability'] = self._calc_reliability_score(
            correlation_data, prediction_data
        )

        # 2. Ajustar pesos dinamicamente
        adjusted_weights = self._adjust_weights_dynamically(
            dimension_scores, prediction_data
        )

        # 3. Calcular score geral ponderado
        overall_score = self._calculate_weighted_score(
            dimension_scores, adjusted_weights
        )

        # 4. Calcular tendência
        trend = self._calculate_trend(overall_score)

        # 5. Comparar com baseline
        comparison = self._compare_with_baseline(overall_score, dimension_scores)

        # 6. Determinar nível e cor
        level, color = self._determine_level(overall_score)

        # 7. Gerar insights
        insights = self._generate_insights(
            overall_score, dimension_scores, trend, comparison
        )

        # 8. Montar resultado
        result = {
            'timestamp': now.isoformat(),
            'overall_score': round(overall_score, 1),
            'level': level,
            'color': color,
            'dimensions': {
                name: {
                    'score': round(score, 1),
                    'weight': adjusted_weights.get(name, self.DIMENSIONS[name]['weight']),
                    'level': self._determine_level(score)[0]
                }
                for name, score in dimension_scores.items()
            },
            'trend': trend,
            'baseline_comparison': comparison,
            'insights': insights,
            'metadata': {
                'samples_in_history': len(self.history.get('scores', [])),
                'baseline_score': self.baseline.get('overall', 70),
                'weights_adjusted': adjusted_weights != {
                    d: self.DIMENSIONS[d]['weight'] for d in self.DIMENSIONS
                }
            }
        }

        # 9. Salvar no histórico
        self._record_score(result)

        # 10. Atualizar baseline se necessário
        self._update_baseline(overall_score, dimension_scores)

        return result

    def _calc_infrastructure_score(self, metrics: Dict[str, Any]) -> float:
        """Calcula score de infraestrutura"""
        scores = []

        # CPU (invertido - menor é melhor)
        cpu = metrics.get('cpu', {})
        cpu_percent = cpu.get('percent', 0) if isinstance(cpu, dict) else cpu
        scores.append(max(0, 100 - cpu_percent))

        # Memory
        memory = metrics.get('memory', {})
        memory_percent = memory.get('percent', 0) if isinstance(memory, dict) else memory
        scores.append(max(0, 100 - memory_percent))

        # Disk
        disk = metrics.get('disk', {})
        disk_percent = disk.get('percent', 0) if isinstance(disk, dict) else disk
        scores.append(max(0, 100 - disk_percent))

        return statistics.mean(scores) if scores else 50

    def _calc_application_score(self, metrics: Dict[str, Any]) -> float:
        """Calcula score de aplicação"""
        scores = []

        # Response time (< 200ms = 100, > 5000ms = 0)
        response_time = metrics.get('response_time_ms', 200)
        if response_time <= 200:
            scores.append(100)
        elif response_time >= 5000:
            scores.append(0)
        else:
            scores.append(100 - ((response_time - 200) / 48))  # Linear entre 200-5000

        # Error rate (0% = 100, 10%+ = 0)
        error_rate = metrics.get('error_rate', 0)
        scores.append(max(0, 100 - error_rate * 10))

        # Throughput (normalizado)
        # Default alto se não houver dados
        throughput_score = metrics.get('throughput_score', 80)
        scores.append(throughput_score)

        return statistics.mean(scores) if scores else 70

    def _calc_code_quality_score(self, gaps: Dict[str, Any]) -> float:
        """Calcula score de qualidade de código"""
        gap_list = gaps.get('gaps', [])

        if not gap_list:
            return 95  # Excelente se sem gaps

        # Penalidades por severidade
        penalties = {
            'critical': 20,
            'high': 10,
            'medium': 5,
            'low': 2
        }

        total_penalty = 0
        for gap in gap_list:
            severity = gap.get('severity', 'low')
            total_penalty += penalties.get(severity, 2)

        # Limitar penalidade máxima
        total_penalty = min(total_penalty, 80)

        return max(20, 100 - total_penalty)

    def _calc_security_score(self, gaps: Dict[str, Any]) -> float:
        """Calcula score de segurança"""
        gap_list = gaps.get('gaps', [])

        # Filtrar gaps de segurança
        security_gaps = [
            g for g in gap_list
            if g.get('category') == 'security' or
               'security' in g.get('type', '').lower() or
               'vulnerability' in g.get('type', '').lower()
        ]

        if not security_gaps:
            return 95  # Excelente se sem issues de segurança

        # Penalidade por issue de segurança
        penalty = len(security_gaps) * 15
        penalty = min(penalty, 80)

        return max(20, 100 - penalty)

    def _calc_reliability_score(
        self,
        correlation_data: Dict[str, Any],
        prediction_data: Dict[str, Any]
    ) -> float:
        """Calcula score de confiabilidade"""
        scores = []

        # Baseado em correlação
        if correlation_data:
            risk = correlation_data.get('risk_assessment', {})
            risk_level = risk.get('level', 'low')

            risk_scores = {
                'low': 95,
                'medium': 70,
                'high': 45,
                'critical': 20
            }
            scores.append(risk_scores.get(risk_level, 70))

        # Baseado em predição
        if prediction_data:
            pred_risk = prediction_data.get('risk_level', 'low')
            pred_scores = {
                'low': 95,
                'medium': 70,
                'high': 45,
                'critical': 20
            }
            scores.append(pred_scores.get(pred_risk, 70))

        # Histórico de healing
        healing_score = self._get_healing_score()
        if healing_score:
            scores.append(healing_score * 10)  # Converter 0-10 para 0-100

        return statistics.mean(scores) if scores else 70

    def _get_healing_score(self) -> Optional[float]:
        """Obtém score de healing do estado"""
        try:
            healing_file = self.state_dir / 'healing_score.json'
            if healing_file.exists():
                with open(healing_file) as f:
                    data = json.load(f)
                    return data.get('score', 0)
        except:
            pass
        return None

    def _adjust_weights_dynamically(
        self,
        dimension_scores: Dict[str, float],
        prediction_data: Dict[str, Any]
    ) -> Dict[str, float]:
        """Ajusta pesos dinamicamente baseado no contexto"""
        weights = {d: self.DIMENSIONS[d]['weight'] for d in self.DIMENSIONS}

        # Se há predição de falha crítica, aumentar peso de reliability
        if prediction_data:
            risk_level = prediction_data.get('risk_level', 'low')
            if risk_level in ['high', 'critical']:
                weights['reliability'] += 0.10
                weights['infrastructure'] += 0.05
                # Redistribuir dos outros
                weights['code_quality'] -= 0.08
                weights['security'] -= 0.07

        # Se infrastructure está crítica, aumentar seu peso
        if dimension_scores.get('infrastructure', 100) < 50:
            weights['infrastructure'] += 0.10
            weights['code_quality'] -= 0.05
            weights['security'] -= 0.05

        # Se security está crítica, aumentar seu peso
        if dimension_scores.get('security', 100) < 50:
            weights['security'] += 0.15
            weights['code_quality'] -= 0.08
            weights['reliability'] -= 0.07

        # Normalizar para soma = 1
        total = sum(weights.values())
        return {k: v / total for k, v in weights.items()}

    def _calculate_weighted_score(
        self,
        dimension_scores: Dict[str, float],
        weights: Dict[str, float]
    ) -> float:
        """Calcula score ponderado"""
        weighted_sum = sum(
            dimension_scores.get(dim, 50) * weight
            for dim, weight in weights.items()
        )
        return weighted_sum

    def _calculate_trend(self, current_score: float) -> Dict[str, Any]:
        """Calcula tendência do score"""
        now = datetime.now()
        window = timedelta(hours=self.evolution_config['trend_window_hours'])
        cutoff = now - window

        # Coletar scores recentes
        recent_scores = []
        for entry in self.history.get('scores', []):
            try:
                ts = datetime.fromisoformat(entry.get('timestamp', '2000-01-01'))
                if ts >= cutoff:
                    recent_scores.append(entry.get('overall_score', 50))
            except:
                pass

        if len(recent_scores) < 2:
            return {
                'direction': 'stable',
                'change': 0,
                'rate_per_hour': 0,
                'samples': len(recent_scores)
            }

        # Calcular tendência
        old_mean = statistics.mean(recent_scores[:-1]) if len(recent_scores) > 1 else recent_scores[0]
        change = current_score - old_mean

        # Determinar direção
        threshold = self.evolution_config['improvement_threshold']
        if change > threshold:
            direction = 'improving'
        elif change < -threshold:
            direction = 'degrading'
        else:
            direction = 'stable'

        return {
            'direction': direction,
            'change': round(change, 1),
            'previous_mean': round(old_mean, 1),
            'samples': len(recent_scores)
        }

    def _compare_with_baseline(
        self,
        overall_score: float,
        dimension_scores: Dict[str, float]
    ) -> Dict[str, Any]:
        """Compara com baseline"""
        baseline_overall = self.baseline.get('overall', 70)
        diff = overall_score - baseline_overall

        dimension_comparison = {}
        for dim, score in dimension_scores.items():
            baseline_dim = self.baseline.get('dimensions', {}).get(dim, 70)
            dimension_comparison[dim] = {
                'current': round(score, 1),
                'baseline': baseline_dim,
                'diff': round(score - baseline_dim, 1)
            }

        return {
            'overall_diff': round(diff, 1),
            'above_baseline': diff > 0,
            'percentage': round((overall_score / baseline_overall - 1) * 100, 1) if baseline_overall > 0 else 0,
            'dimensions': dimension_comparison
        }

    def _determine_level(self, score: float) -> Tuple[str, str]:
        """Determina nível e cor do score"""
        colors = {
            'excellent': '#22c55e',  # Green
            'good': '#84cc16',       # Lime
            'fair': '#eab308',       # Yellow
            'poor': '#f97316',       # Orange
            'critical': '#ef4444'    # Red
        }

        for level, (min_score, max_score) in self.SCORE_LEVELS.items():
            if min_score <= score <= max_score:
                return level, colors[level]

        return 'critical', colors['critical']

    def _generate_insights(
        self,
        overall_score: float,
        dimension_scores: Dict[str, float],
        trend: Dict[str, Any],
        comparison: Dict[str, Any]
    ) -> List[str]:
        """Gera insights sobre o score"""
        insights = []

        # Insight geral
        level, _ = self._determine_level(overall_score)
        if level == 'excellent':
            insights.append(f"Sistema em excelente estado (score: {overall_score:.0f})")
        elif level == 'critical':
            insights.append(f"ATENÇÃO: Sistema em estado crítico (score: {overall_score:.0f})")

        # Insight de tendência
        direction = trend.get('direction', 'stable')
        change = trend.get('change', 0)
        if direction == 'improving':
            insights.append(f"Tendência de melhoria (+{change:.1f} pontos)")
        elif direction == 'degrading':
            insights.append(f"Tendência de degradação ({change:.1f} pontos)")

        # Insight de baseline
        if comparison.get('above_baseline', False):
            diff = comparison.get('overall_diff', 0)
            insights.append(f"Acima do baseline (+{diff:.1f} pontos)")
        elif comparison.get('overall_diff', 0) < -10:
            diff = comparison.get('overall_diff', 0)
            insights.append(f"ALERTA: Abaixo do baseline ({diff:.1f} pontos)")

        # Dimensão mais fraca
        weakest = min(dimension_scores.items(), key=lambda x: x[1])
        if weakest[1] < 60:
            insights.append(f"Dimensão mais fraca: {weakest[0]} ({weakest[1]:.0f})")

        # Dimensão mais forte
        strongest = max(dimension_scores.items(), key=lambda x: x[1])
        if strongest[1] >= 85:
            insights.append(f"Destaque: {strongest[0]} ({strongest[1]:.0f})")

        return insights

    def _record_score(self, result: Dict[str, Any]):
        """Registra score no histórico"""
        entry = {
            'timestamp': result['timestamp'],
            'overall_score': result['overall_score'],
            'level': result['level'],
            'dimensions': {
                k: v['score'] for k, v in result['dimensions'].items()
            }
        }

        self.history['scores'].append(entry)

        # Manter últimas 1000 entradas
        self.history['scores'] = self.history['scores'][-1000:]

        # Atualizar média diária
        today = datetime.now().strftime('%Y-%m-%d')
        if today not in self.history['daily_averages']:
            self.history['daily_averages'][today] = []
        self.history['daily_averages'][today].append(result['overall_score'])

        # Limpar médias antigas (manter últimos 30 dias)
        cutoff = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        self.history['daily_averages'] = {
            k: v for k, v in self.history['daily_averages'].items()
            if k >= cutoff
        }

        self._save_history()

    def _update_baseline(
        self,
        overall_score: float,
        dimension_scores: Dict[str, float]
    ):
        """Atualiza baseline adaptativamente"""
        self.baseline['samples'] = self.baseline.get('samples', 0) + 1

        # Média móvel exponencial para baseline
        alpha = 0.05  # Peso baixo para mudança lenta

        old_baseline = self.baseline.get('overall', overall_score)
        new_baseline = alpha * overall_score + (1 - alpha) * old_baseline
        self.baseline['overall'] = round(new_baseline, 1)

        # Atualizar dimensões
        if 'dimensions' not in self.baseline:
            self.baseline['dimensions'] = {}

        for dim, score in dimension_scores.items():
            old = self.baseline['dimensions'].get(dim, score)
            self.baseline['dimensions'][dim] = round(
                alpha * score + (1 - alpha) * old, 1
            )

        self.baseline['last_updated'] = datetime.now().isoformat()
        self._save_baseline()

    def get_history_summary(self, days: int = 7) -> Dict[str, Any]:
        """Retorna resumo do histórico"""
        cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        daily_data = {
            k: v for k, v in self.history.get('daily_averages', {}).items()
            if k >= cutoff
        }

        if not daily_data:
            return {'error': 'Insufficient data'}

        daily_means = {
            day: statistics.mean(scores)
            for day, scores in daily_data.items()
        }

        all_scores = [s for scores in daily_data.values() for s in scores]

        return {
            'period_days': days,
            'total_samples': len(all_scores),
            'daily_averages': {k: round(v, 1) for k, v in daily_means.items()},
            'overall_mean': round(statistics.mean(all_scores), 1),
            'min': round(min(all_scores), 1),
            'max': round(max(all_scores), 1),
            'std': round(statistics.stdev(all_scores), 1) if len(all_scores) > 1 else 0
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas do health score"""
        scores = self.history.get('scores', [])

        if not scores:
            return {'error': 'No data'}

        recent_scores = [s['overall_score'] for s in scores[-100:]]

        return {
            'total_samples': len(scores),
            'current_baseline': self.baseline.get('overall', 70),
            'baseline_samples': self.baseline.get('samples', 0),
            'recent_mean': round(statistics.mean(recent_scores), 1),
            'recent_std': round(statistics.stdev(recent_scores), 1) if len(recent_scores) > 1 else 0,
            'recent_min': round(min(recent_scores), 1),
            'recent_max': round(max(recent_scores), 1),
            'dimension_baselines': self.baseline.get('dimensions', {})
        }


if __name__ == '__main__':
    # Teste
    health = EvolutionaryHealthScore({})

    test_metrics = {
        'cpu': {'percent': 45},
        'memory': {'percent': 60},
        'disk': {'percent': 70},
        'response_time_ms': 300,
        'error_rate': 1.5
    }

    test_gaps = {
        'gaps': [
            {'type': 'unused_dependency', 'severity': 'low', 'category': 'dependencies'},
            {'type': 'high_cpu', 'severity': 'medium', 'category': 'performance'},
        ]
    }

    result = health.calculate(test_metrics, test_gaps)

    print("=== Health Score Evolutivo ===\n")
    print(f"Score Geral: {result['overall_score']}/100 ({result['level'].upper()})")
    print(f"\nDimensões:")
    for dim, data in result['dimensions'].items():
        print(f"  {dim}: {data['score']}/100 ({data['level']})")

    print(f"\nTendência: {result['trend']['direction']}")
    print(f"Baseline: {result['baseline_comparison']['overall_diff']:+.1f}")

    print(f"\nInsights:")
    for insight in result['insights']:
        print(f"  - {insight}")
