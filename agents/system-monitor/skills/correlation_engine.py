"""
Skill: Correlation Engine (Motor de Correlação Inteligente)
O "cérebro" do Monitoriza - correlaciona eventos, detecta padrões e identifica causa raiz

Princípios:
- Nada é analisado isoladamente
- Correlação temporal de eventos
- Detecção de padrões recorrentes
- Diferenciação causa raiz vs sintomas
"""

import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
import statistics


class CorrelationEngine:
    """
    Motor de Correlação Inteligente

    Correlaciona: logs, métricas, gaps, testes, eventos
    Detecta: padrões, anomalias, causa raiz
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.state_dir = Path('/opt/conecta-plus/agents/system-monitor/state')
        self.state_dir.mkdir(parents=True, exist_ok=True)

        self.correlation_file = self.state_dir / 'correlations.json'
        self.patterns_file = self.state_dir / 'detected_patterns.json'

        # Janelas temporais para correlação
        self.time_windows = {
            'immediate': timedelta(seconds=30),
            'short': timedelta(minutes=5),
            'medium': timedelta(minutes=30),
            'long': timedelta(hours=2)
        }

        # Buffer de eventos recentes
        self.event_buffer: List[Dict[str, Any]] = []
        self.max_buffer_size = 1000

        # Padrões conhecidos
        self.known_patterns = self._load_patterns()

        # Regras de correlação
        self.correlation_rules = self._init_correlation_rules()

    def _load_patterns(self) -> Dict[str, Any]:
        """Carrega padrões detectados anteriormente"""
        try:
            if self.patterns_file.exists():
                with open(self.patterns_file) as f:
                    return json.load(f)
        except:
            pass
        return {
            'recurring': [],
            'false_positives': [],
            'root_causes': {},
            'symptom_chains': []
        }

    def _save_patterns(self):
        """Salva padrões detectados"""
        with open(self.patterns_file, 'w') as f:
            json.dump(self.known_patterns, f, indent=2, default=str)

    def _init_correlation_rules(self) -> List[Dict[str, Any]]:
        """Inicializa regras de correlação conhecidas"""
        return [
            {
                'id': 'api_overload',
                'name': 'API Overload Pattern',
                'conditions': [
                    {'type': 'metric', 'metric': 'cpu', 'operator': '>', 'value': 80},
                    {'type': 'log', 'pattern': 'HTTP 5[0-9]{2}'},
                    {'type': 'test', 'result': 'failed', 'category': 'load'}
                ],
                'conclusion': 'API está sobrecarregada - possível gargalo',
                'root_cause': 'high_load',
                'recommended_actions': ['scale_up', 'rate_limit', 'cache_optimize']
            },
            {
                'id': 'memory_leak',
                'name': 'Memory Leak Pattern',
                'conditions': [
                    {'type': 'metric', 'metric': 'memory', 'operator': '>', 'value': 85},
                    {'type': 'trend', 'metric': 'memory', 'direction': 'increasing'},
                    {'type': 'gap', 'category': 'performance'}
                ],
                'conclusion': 'Possível memory leak detectado',
                'root_cause': 'memory_leak',
                'recommended_actions': ['restart_service', 'analyze_heap']
            },
            {
                'id': 'database_bottleneck',
                'name': 'Database Bottleneck Pattern',
                'conditions': [
                    {'type': 'log', 'pattern': 'slow query|timeout|connection refused'},
                    {'type': 'metric', 'metric': 'disk', 'operator': '>', 'value': 80},
                    {'type': 'test', 'result': 'failed', 'category': 'integration'}
                ],
                'conclusion': 'Gargalo no banco de dados',
                'root_cause': 'database_bottleneck',
                'recommended_actions': ['optimize_queries', 'add_indexes', 'scale_db']
            },
            {
                'id': 'cascade_failure',
                'name': 'Cascade Failure Pattern',
                'conditions': [
                    {'type': 'gap', 'severity': 'high', 'count': '>=3'},
                    {'type': 'log', 'pattern': 'error|exception|failed', 'count': '>=10'},
                    {'type': 'test', 'result': 'failed', 'count': '>=5'}
                ],
                'conclusion': 'Falha em cascata detectada - múltiplos componentes afetados',
                'root_cause': 'cascade_failure',
                'recommended_actions': ['isolate_component', 'circuit_breaker', 'alert_human']
            },
            {
                'id': 'network_issue',
                'name': 'Network Issue Pattern',
                'conditions': [
                    {'type': 'log', 'pattern': 'connection timeout|network unreachable|ECONNREFUSED'},
                    {'type': 'test', 'result': 'failed', 'category': 'network'}
                ],
                'conclusion': 'Problema de rede detectado',
                'root_cause': 'network_issue',
                'recommended_actions': ['check_dns', 'check_firewall', 'restart_network']
            }
        ]

    def add_event(self, event: Dict[str, Any]):
        """Adiciona evento ao buffer para análise"""
        event['timestamp'] = event.get('timestamp', datetime.now().isoformat())
        event['processed'] = False

        self.event_buffer.append(event)

        # Manter buffer limitado
        if len(self.event_buffer) > self.max_buffer_size:
            self.event_buffer = self.event_buffer[-self.max_buffer_size:]

    def correlate(
        self,
        logs: Dict[str, Any],
        metrics: Dict[str, Any],
        gaps: Dict[str, Any],
        test_results: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Executa correlação completa de todos os dados

        Returns:
            Análise correlacionada com insights e recomendações
        """
        correlation_result = {
            'timestamp': datetime.now().isoformat(),
            'events_analyzed': 0,
            'correlations_found': [],
            'patterns_detected': [],
            'root_causes': [],
            'false_positives': [],
            'insights': [],
            'risk_assessment': {},
            'recommended_actions': []
        }

        # 1. Normalizar e indexar eventos
        events = self._normalize_events(logs, metrics, gaps, test_results)
        correlation_result['events_analyzed'] = len(events)

        # 2. Detectar correlações temporais
        temporal_correlations = self._find_temporal_correlations(events)
        correlation_result['correlations_found'].extend(temporal_correlations)

        # 3. Aplicar regras de correlação
        rule_matches = self._apply_correlation_rules(events, metrics, gaps)
        correlation_result['patterns_detected'].extend(rule_matches)

        # 4. Identificar causa raiz
        root_causes = self._identify_root_causes(events, rule_matches)
        correlation_result['root_causes'] = root_causes

        # 5. Detectar falsos positivos
        false_positives = self._detect_false_positives(events)
        correlation_result['false_positives'] = false_positives

        # 6. Detectar padrões recorrentes
        recurring = self._detect_recurring_patterns(events)
        if recurring:
            correlation_result['patterns_detected'].extend(recurring)

        # 7. Avaliar risco
        correlation_result['risk_assessment'] = self._assess_risk(
            events, rule_matches, root_causes
        )

        # 8. Gerar insights
        correlation_result['insights'] = self._generate_insights(
            correlation_result
        )

        # 9. Recomendar ações
        correlation_result['recommended_actions'] = self._recommend_actions(
            correlation_result
        )

        # Salvar padrões atualizados
        self._save_patterns()

        return correlation_result

    def _normalize_events(
        self,
        logs: Dict[str, Any],
        metrics: Dict[str, Any],
        gaps: Dict[str, Any],
        test_results: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Normaliza todos os eventos para formato comum"""
        events = []
        now = datetime.now()

        # Normalizar logs
        for log_type, log_data in logs.get('logs', {}).items():
            if isinstance(log_data, dict):
                for error in log_data.get('errors', []):
                    events.append({
                        'type': 'log_error',
                        'source': log_type,
                        'severity': log_data.get('severity', 'unknown'),
                        'message': error.get('message', str(error)),
                        'timestamp': now.isoformat(),
                        'category': 'log'
                    })

        # Normalizar métricas
        for metric_name, metric_data in metrics.items():
            if isinstance(metric_data, dict) and 'percent' in metric_data:
                events.append({
                    'type': 'metric',
                    'source': metric_name,
                    'value': metric_data.get('percent', 0),
                    'timestamp': metric_data.get('timestamp', now.isoformat()),
                    'category': 'metric'
                })

        # Normalizar gaps
        for gap in gaps.get('gaps', []):
            events.append({
                'type': 'gap',
                'source': gap.get('category', 'unknown'),
                'severity': gap.get('severity', 'low'),
                'priority': gap.get('priority', 'P4'),
                'description': gap.get('description', ''),
                'gap_type': gap.get('type', ''),
                'timestamp': now.isoformat(),
                'category': 'gap'
            })

        # Normalizar testes
        if test_results:
            for test_type, test_data in test_results.items():
                if isinstance(test_data, dict) and test_type != 'summary':
                    passed = test_data.get('passed', test_data.get('success', True))
                    events.append({
                        'type': 'test',
                        'source': test_type,
                        'passed': passed,
                        'result': 'passed' if passed else 'failed',
                        'timestamp': now.isoformat(),
                        'category': 'test'
                    })

        return events

    def _find_temporal_correlations(
        self,
        events: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Encontra correlações temporais entre eventos"""
        correlations = []

        # Agrupar eventos por janela temporal
        for window_name, window_delta in self.time_windows.items():
            window_events = self._filter_events_by_window(events, window_delta)

            if len(window_events) >= 2:
                # Verificar se há mix de categorias (indica correlação)
                categories = set(e.get('category') for e in window_events)

                if len(categories) >= 2:
                    correlations.append({
                        'window': window_name,
                        'event_count': len(window_events),
                        'categories': list(categories),
                        'summary': f"{len(window_events)} eventos em {window_name} window",
                        'events': window_events[:5]  # Primeiros 5
                    })

        return correlations

    def _filter_events_by_window(
        self,
        events: List[Dict[str, Any]],
        window: timedelta
    ) -> List[Dict[str, Any]]:
        """Filtra eventos dentro de uma janela temporal"""
        now = datetime.now()
        cutoff = now - window

        filtered = []
        for event in events:
            try:
                event_time = datetime.fromisoformat(
                    event.get('timestamp', now.isoformat()).replace('Z', '+00:00')
                )
                if event_time >= cutoff:
                    filtered.append(event)
            except:
                filtered.append(event)  # Incluir se não conseguir parsear

        return filtered

    def _apply_correlation_rules(
        self,
        events: List[Dict[str, Any]],
        metrics: Dict[str, Any],
        gaps: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Aplica regras de correlação definidas"""
        matches = []

        for rule in self.correlation_rules:
            conditions_met = 0
            total_conditions = len(rule['conditions'])

            for condition in rule['conditions']:
                if self._check_condition(condition, events, metrics, gaps):
                    conditions_met += 1

            # Regra ativada se maioria das condições satisfeitas
            if conditions_met >= (total_conditions * 0.6):
                matches.append({
                    'rule_id': rule['id'],
                    'rule_name': rule['name'],
                    'conditions_met': f"{conditions_met}/{total_conditions}",
                    'confidence': conditions_met / total_conditions,
                    'conclusion': rule['conclusion'],
                    'root_cause': rule['root_cause'],
                    'recommended_actions': rule['recommended_actions']
                })

        return matches

    def _check_condition(
        self,
        condition: Dict[str, Any],
        events: List[Dict[str, Any]],
        metrics: Dict[str, Any],
        gaps: Dict[str, Any]
    ) -> bool:
        """Verifica se uma condição é satisfeita"""
        cond_type = condition.get('type')

        if cond_type == 'metric':
            metric_name = condition.get('metric')
            metric_data = metrics.get(metric_name, {})
            value = metric_data.get('percent', 0)

            operator = condition.get('operator', '>')
            threshold = condition.get('value', 0)

            if operator == '>':
                return value > threshold
            elif operator == '<':
                return value < threshold
            elif operator == '>=':
                return value >= threshold
            elif operator == '<=':
                return value <= threshold

        elif cond_type == 'log':
            import re
            pattern = condition.get('pattern', '')
            log_events = [e for e in events if e.get('category') == 'log']

            for event in log_events:
                if re.search(pattern, str(event.get('message', '')), re.IGNORECASE):
                    return True

        elif cond_type == 'gap':
            gap_events = [e for e in events if e.get('category') == 'gap']

            if 'severity' in condition:
                severity = condition['severity']
                matching = [e for e in gap_events if e.get('severity') == severity]

                if 'count' in condition:
                    count_str = condition['count']
                    if count_str.startswith('>='):
                        return len(matching) >= int(count_str[2:])
                    else:
                        return len(matching) > 0
                return len(matching) > 0

            if 'category' in condition:
                return any(e.get('source') == condition['category'] for e in gap_events)

        elif cond_type == 'test':
            test_events = [e for e in events if e.get('category') == 'test']

            if 'result' in condition:
                result = condition['result']
                matching = [e for e in test_events if e.get('result') == result]

                if 'count' in condition:
                    count_str = str(condition['count'])
                    if count_str.startswith('>='):
                        return len(matching) >= int(count_str[2:])
                return len(matching) > 0

        return False

    def _identify_root_causes(
        self,
        events: List[Dict[str, Any]],
        rule_matches: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Identifica causa raiz vs sintomas"""
        root_causes = []

        # Causas identificadas por regras
        for match in rule_matches:
            if match.get('confidence', 0) >= 0.7:
                root_causes.append({
                    'cause': match.get('root_cause'),
                    'confidence': match.get('confidence'),
                    'source': 'rule_match',
                    'rule': match.get('rule_name'),
                    'evidence': match.get('conclusion')
                })

        # Análise estatística de eventos
        category_counts = defaultdict(int)
        for event in events:
            if event.get('severity') in ['high', 'critical']:
                category_counts[event.get('source', 'unknown')] += 1

        # Fonte com mais eventos críticos provavelmente é causa raiz
        if category_counts:
            max_source = max(category_counts, key=category_counts.get)
            if category_counts[max_source] >= 3:
                root_causes.append({
                    'cause': f'component_failure_{max_source}',
                    'confidence': 0.6,
                    'source': 'statistical',
                    'evidence': f"{category_counts[max_source]} eventos críticos em {max_source}"
                })

        return root_causes

    def _detect_false_positives(
        self,
        events: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Detecta prováveis falsos positivos"""
        false_positives = []

        # Gaps que são conhecidos falsos positivos
        known_fp = self.known_patterns.get('false_positives', [])

        for event in events:
            if event.get('category') == 'gap':
                gap_type = event.get('gap_type', '')

                # Verificar se já foi marcado como falso positivo
                if gap_type in known_fp:
                    false_positives.append({
                        'event': event,
                        'reason': 'Previously marked as false positive'
                    })

                # Heurística: gaps de unused_dependency frequentemente são FP
                if gap_type == 'unused_dependency':
                    false_positives.append({
                        'event': event,
                        'reason': 'Common false positive - may be used indirectly'
                    })

        return false_positives

    def _detect_recurring_patterns(
        self,
        events: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Detecta padrões recorrentes"""
        recurring = []

        # Agrupar por tipo de evento
        event_types = defaultdict(list)
        for event in events:
            key = f"{event.get('category')}_{event.get('type')}"
            event_types[key].append(event)

        # Detectar recorrência
        for event_type, type_events in event_types.items():
            if len(type_events) >= 3:
                recurring.append({
                    'pattern_type': 'recurring',
                    'event_type': event_type,
                    'occurrences': len(type_events),
                    'description': f"Padrão recorrente: {event_type} ({len(type_events)}x)"
                })

                # Adicionar ao conhecimento
                if event_type not in [p.get('event_type') for p in self.known_patterns.get('recurring', [])]:
                    self.known_patterns['recurring'].append({
                        'event_type': event_type,
                        'first_detected': datetime.now().isoformat(),
                        'count': len(type_events)
                    })

        return recurring

    def _assess_risk(
        self,
        events: List[Dict[str, Any]],
        rule_matches: List[Dict[str, Any]],
        root_causes: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Avalia risco geral do sistema"""
        risk_score = 0
        risk_factors = []

        # Fator 1: Número de eventos críticos
        critical_events = [e for e in events if e.get('severity') in ['high', 'critical']]
        if critical_events:
            risk_score += len(critical_events) * 10
            risk_factors.append(f"{len(critical_events)} eventos críticos")

        # Fator 2: Regras de correlação ativadas
        if rule_matches:
            high_confidence = [m for m in rule_matches if m.get('confidence', 0) >= 0.7]
            risk_score += len(high_confidence) * 15
            risk_factors.append(f"{len(high_confidence)} padrões de falha detectados")

        # Fator 3: Causa raiz identificada
        if root_causes:
            risk_score += len(root_causes) * 10
            risk_factors.append(f"{len(root_causes)} causas raiz identificadas")

        # Determinar nível de risco
        if risk_score >= 50:
            risk_level = 'critical'
        elif risk_score >= 30:
            risk_level = 'high'
        elif risk_score >= 15:
            risk_level = 'medium'
        else:
            risk_level = 'low'

        return {
            'score': risk_score,
            'level': risk_level,
            'factors': risk_factors,
            'requires_attention': risk_level in ['high', 'critical']
        }

    def _generate_insights(
        self,
        correlation_result: Dict[str, Any]
    ) -> List[str]:
        """Gera insights a partir da correlação"""
        insights = []

        # Insight sobre correlações
        correlations = correlation_result.get('correlations_found', [])
        if correlations:
            insights.append(
                f"Detectadas {len(correlations)} correlações temporais entre eventos"
            )

        # Insight sobre padrões
        patterns = correlation_result.get('patterns_detected', [])
        if patterns:
            for pattern in patterns:
                if pattern.get('pattern_type') == 'recurring':
                    insights.append(
                        f"Padrão recorrente: {pattern.get('event_type')} "
                        f"({pattern.get('occurrences')}x)"
                    )
                else:
                    insights.append(
                        f"Padrão detectado: {pattern.get('rule_name', 'unknown')} "
                        f"(confiança: {pattern.get('confidence', 0):.0%})"
                    )

        # Insight sobre causa raiz
        root_causes = correlation_result.get('root_causes', [])
        if root_causes:
            primary = max(root_causes, key=lambda x: x.get('confidence', 0))
            insights.append(
                f"Causa raiz provável: {primary.get('cause')} "
                f"(confiança: {primary.get('confidence', 0):.0%})"
            )

        # Insight sobre falsos positivos
        fps = correlation_result.get('false_positives', [])
        if fps:
            insights.append(
                f"{len(fps)} prováveis falsos positivos identificados"
            )

        # Insight sobre risco
        risk = correlation_result.get('risk_assessment', {})
        if risk.get('requires_attention'):
            insights.append(
                f"ATENÇÃO: Risco {risk.get('level')} - {', '.join(risk.get('factors', []))}"
            )

        return insights

    def _recommend_actions(
        self,
        correlation_result: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Recomenda ações baseadas na correlação"""
        actions = []

        # Ações baseadas em regras
        for pattern in correlation_result.get('patterns_detected', []):
            if 'recommended_actions' in pattern:
                for action in pattern['recommended_actions']:
                    actions.append({
                        'action': action,
                        'reason': pattern.get('rule_name', 'pattern_match'),
                        'priority': 'high' if pattern.get('confidence', 0) >= 0.8 else 'medium',
                        'confidence': pattern.get('confidence', 0)
                    })

        # Ações baseadas em causa raiz
        for cause in correlation_result.get('root_causes', []):
            cause_type = cause.get('cause', '')
            if 'memory' in cause_type:
                actions.append({
                    'action': 'analyze_memory_usage',
                    'reason': 'Memory-related root cause detected',
                    'priority': 'high'
                })
            elif 'database' in cause_type:
                actions.append({
                    'action': 'optimize_database',
                    'reason': 'Database-related root cause detected',
                    'priority': 'high'
                })

        # Deduplica ações
        seen = set()
        unique_actions = []
        for action in actions:
            key = action.get('action')
            if key not in seen:
                seen.add(key)
                unique_actions.append(action)

        return unique_actions


if __name__ == '__main__':
    # Teste
    engine = CorrelationEngine({})

    test_logs = {
        'logs': {
            'backend': {
                'errors': [{'message': 'HTTP 500 Internal Server Error'}],
                'severity': 'error'
            }
        }
    }

    test_metrics = {
        'cpu': {'percent': 85},
        'memory': {'percent': 70},
        'disk': {'percent': 60}
    }

    test_gaps = {
        'gaps': [
            {'type': 'high_cpu', 'severity': 'high', 'category': 'performance'},
            {'type': 'outdated_npm', 'severity': 'low', 'category': 'dependencies'}
        ]
    }

    result = engine.correlate(test_logs, test_metrics, test_gaps)
    print(json.dumps(result, indent=2, default=str))
