"""
Skill: Health Scorer
Calcula pontuação geral de saúde do sistema (0-100)
"""

from typing import Dict, Any
from datetime import datetime


class HealthScorer:
    """Calcula score de saúde do sistema"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def calculate_health_score(
        self,
        gaps: Dict[str, Any],
        metrics: Dict[str, Any],
        test_results: Dict[str, Any] = None,
        fixes_applied: list = None
    ) -> Dict[str, Any]:
        """
        Calcula pontuação geral de saúde (0-100)

        Fatores considerados:
        - Gaps detectados (40 pontos)
        - Métricas de sistema (30 pontos)
        - Testes (20 pontos)
        - Auto-correção (10 pontos)
        """

        score_breakdown = {}

        # 1. GAPS (40 pontos) - Quanto menos gaps, melhor
        gaps_score = self._score_gaps(gaps)
        score_breakdown['gaps'] = gaps_score

        # 2. MÉTRICAS (30 pontos) - CPU, Memória, Disco
        metrics_score = self._score_metrics(metrics)
        score_breakdown['metrics'] = metrics_score

        # 3. TESTES (20 pontos) - Taxa de aprovação
        if test_results:
            tests_score = self._score_tests(test_results)
            score_breakdown['tests'] = tests_score
        else:
            tests_score = 20  # Assume OK se não testou
            score_breakdown['tests'] = {'score': 20, 'reason': 'No tests run this cycle'}

        # 4. AUTO-CORREÇÃO (10 pontos) - Capacidade de auto-healing
        if fixes_applied:
            healing_score = self._score_healing(fixes_applied)
            score_breakdown['healing'] = healing_score
        else:
            healing_score = 5  # Score neutro
            score_breakdown['healing'] = {'score': 5, 'reason': 'No fixes attempted'}

        # SCORE TOTAL
        total_score = (
            gaps_score.get('score', 0) +
            metrics_score.get('score', 0) +
            (tests_score.get('score', 0) if isinstance(tests_score, dict) else tests_score) +
            (healing_score.get('score', 0) if isinstance(healing_score, dict) else healing_score)
        )

        # Garantir range 0-100
        total_score = max(0, min(100, total_score))

        # Determinar nível de saúde
        health_level = self._get_health_level(total_score)

        return {
            'timestamp': datetime.now().isoformat(),
            'overall_score': round(total_score, 1),
            'health_level': health_level,
            'breakdown': score_breakdown,
            'recommendations': self._get_recommendations(score_breakdown, total_score)
        }

    def _score_gaps(self, gaps: Dict[str, Any]) -> Dict[str, Any]:
        """
        Pontua gaps detectados (0-40 pontos)
        Menos gaps = mais pontos
        """
        total_gaps = gaps.get('total_gaps', 0)
        critical_gaps = gaps.get('critical_gaps', 0)

        # Penalidades
        if total_gaps == 0:
            score = 40
            status = "Perfect - No gaps detected"
        elif total_gaps <= 5:
            score = 35
            status = "Excellent - Minimal gaps"
        elif total_gaps <= 15:
            score = 30
            status = "Good - Few gaps"
        elif total_gaps <= 30:
            score = 25
            status = "Fair - Moderate gaps"
        elif total_gaps <= 50:
            score = 20
            status = "Poor - Many gaps"
        else:
            score = 10
            status = "Critical - Too many gaps"

        # Penalidade extra para gaps críticos
        score -= critical_gaps * 2
        score = max(0, score)

        return {
            'score': score,
            'max': 40,
            'total_gaps': total_gaps,
            'critical_gaps': critical_gaps,
            'status': status
        }

    def _score_metrics(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Pontua métricas de sistema (0-30 pontos)
        CPU, Memória, Disco saudáveis = mais pontos
        """
        cpu_percent = metrics.get('cpu', {}).get('percent', 0)
        mem_percent = metrics.get('memory', {}).get('percent', 0)
        disk_percent = metrics.get('disk', {}).get('percent', 0)

        # Calcular score individual (0-10 cada)
        cpu_score = self._score_resource(cpu_percent, 'cpu')
        mem_score = self._score_resource(mem_percent, 'memory')
        disk_score = self._score_resource(disk_percent, 'disk')

        total = cpu_score + mem_score + disk_score

        return {
            'score': total,
            'max': 30,
            'cpu': {'value': f"{cpu_percent}%", 'score': cpu_score},
            'memory': {'value': f"{mem_percent}%", 'score': mem_score},
            'disk': {'value': f"{disk_percent}%", 'score': disk_score}
        }

    def _score_resource(self, percent: float, resource_type: str) -> float:
        """Score individual de recurso (0-10)"""
        if percent < 50:
            return 10  # Excelente
        elif percent < 70:
            return 8   # Bom
        elif percent < 85:
            return 6   # Aceitável
        elif percent < 95:
            return 3   # Crítico
        else:
            return 0   # Emergência

    def _score_tests(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Pontua resultados de testes (0-20 pontos)
        Mais testes aprovados = mais pontos
        """
        summary = test_results.get('summary', {})
        total_tests = summary.get('total_tests', 0)
        passed_tests = summary.get('passed_tests', 0)

        if total_tests == 0:
            return {'score': 20, 'reason': 'No tests available'}

        pass_rate = (passed_tests / total_tests) * 100

        if pass_rate >= 95:
            score = 20
            status = "Excellent"
        elif pass_rate >= 85:
            score = 17
            status = "Good"
        elif pass_rate >= 70:
            score = 14
            status = "Fair"
        elif pass_rate >= 50:
            score = 10
            status = "Poor"
        else:
            score = 5
            status = "Critical"

        return {
            'score': score,
            'max': 20,
            'pass_rate': f"{pass_rate:.1f}%",
            'passed': passed_tests,
            'total': total_tests,
            'status': status
        }

    def _score_healing(self, fixes_applied: list) -> Dict[str, Any]:
        """
        Pontua capacidade de auto-healing (0-10 pontos)
        Mais correções bem-sucedidas = mais pontos
        """
        if not fixes_applied:
            return {'score': 5, 'reason': 'No healing attempted'}

        total_fixes = len(fixes_applied)
        successful_fixes = sum(1 for f in fixes_applied if f.get('success', False))

        if total_fixes == 0:
            success_rate = 0
        else:
            success_rate = (successful_fixes / total_fixes) * 100

        if success_rate >= 90:
            score = 10
            status = "Excellent healing"
        elif success_rate >= 70:
            score = 8
            status = "Good healing"
        elif success_rate >= 50:
            score = 6
            status = "Fair healing"
        else:
            score = 3
            status = "Poor healing"

        return {
            'score': score,
            'max': 10,
            'success_rate': f"{success_rate:.1f}%",
            'successful': successful_fixes,
            'total': total_fixes,
            'status': status
        }

    def _get_health_level(self, score: float) -> str:
        """Determina nível de saúde baseado no score"""
        if score >= 90:
            return "Excellent"
        elif score >= 75:
            return "Good"
        elif score >= 60:
            return "Fair"
        elif score >= 40:
            return "Poor"
        else:
            return "Critical"

    def _get_recommendations(self, breakdown: Dict[str, Any], total_score: float) -> list:
        """Gera recomendações baseadas no score"""
        recommendations = []

        # Recomendações baseadas em gaps
        gaps_score = breakdown.get('gaps', {})
        if gaps_score.get('score', 0) < 30:
            critical = gaps_score.get('critical_gaps', 0)
            if critical > 0:
                recommendations.append(f"🔴 URGENT: Fix {critical} critical gaps immediately")
            recommendations.append(f"⚠️ Address {gaps_score.get('total_gaps', 0)} total gaps detected")

        # Recomendações baseadas em métricas
        metrics = breakdown.get('metrics', {})
        for resource in ['cpu', 'memory', 'disk']:
            res_data = metrics.get(resource, {})
            if res_data.get('score', 10) < 5:
                recommendations.append(f"⚠️ High {resource} usage: {res_data.get('value', 'N/A')}")

        # Recomendações baseadas em testes
        tests = breakdown.get('tests', {})
        if isinstance(tests, dict) and tests.get('score', 20) < 15:
            recommendations.append(f"⚠️ Low test pass rate: {tests.get('pass_rate', 'N/A')}")

        # Recomendação geral
        if total_score < 60:
            recommendations.append("🔴 System health is below acceptable levels - immediate action required")
        elif total_score < 75:
            recommendations.append("⚠️ System health needs improvement - plan corrective actions")

        if not recommendations:
            recommendations.append("✅ System health is optimal - continue monitoring")

        return recommendations


if __name__ == '__main__':
    # Teste
    scorer = HealthScorer({})

    test_data = {
        'gaps': {'total_gaps': 27, 'critical_gaps': 1},
        'metrics': {
            'cpu': {'percent': 17.2},
            'memory': {'percent': 24.3},
            'disk': {'percent': 49.1}
        },
        'test_results': {
            'summary': {
                'total_tests': 92,
                'passed_tests': 21
            }
        },
        'fixes_applied': [
            {'success': True},
            {'success': True},
            {'success': False}
        ]
    }

    result = scorer.calculate_health_score(**test_data)

    print("=== SYSTEM HEALTH SCORE ===")
    print(f"Overall Score: {result['overall_score']}/100")
    print(f"Health Level: {result['health_level']}")
    print(f"\nBreakdown:")
    for key, value in result['breakdown'].items():
        print(f"  {key}: {value}")
    print(f"\nRecommendations:")
    for rec in result['recommendations']:
        print(f"  {rec}")
