"""
Skill: Contextual Healer (Auto-Healing Contextual)
Sistema de auto-healing que usa contexto, correlação e predição para decisões inteligentes

Princípios:
- Decisões baseadas em contexto completo
- Integração com correlação e predição
- Aprendizado com histórico
- Guardrails avançados
"""

import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

# Imports dos outros módulos vNEXT
from skills.safe_healer import SafeHealer
from skills.correlation_engine import CorrelationEngine
from skills.dynamic_severity import DynamicSeverityClassifier
from skills.operational_memory import OperationalMemory
from skills.failure_predictor import FailurePredictor
from skills.forensic_audit import ForensicAudit


class ContextualHealer:
    """
    Auto-Healing Contextual

    Integra:
    - SafeHealer (base segura)
    - CorrelationEngine (contexto)
    - DynamicSeverity (priorização)
    - OperationalMemory (aprendizado)
    - FailurePredictor (predição)
    - ForensicAudit (auditoria)

    Adiciona:
    - Decisão contextual
    - Error budget
    - Circuit breaker
    - Feature flags
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.state_dir = Path('/opt/conecta-plus/agents/system-monitor/state')
        self.state_dir.mkdir(parents=True, exist_ok=True)

        self.state_file = self.state_dir / 'contextual_healer.json'

        # Inicializar componentes
        self.safe_healer = SafeHealer(config)
        self.correlation = CorrelationEngine(config)
        self.severity = DynamicSeverityClassifier(config)
        self.memory = OperationalMemory(config)
        self.predictor = FailurePredictor(config)
        self.audit = ForensicAudit(config)

        # Estado do healer
        self.state = self._load_state()

        # Configuração contextual
        self.context_config = {
            # Error budget
            'error_budget_window_hours': 24,
            'max_failed_healings': 5,
            'budget_reset_on_success_streak': 3,

            # Circuit breaker
            'circuit_breaker_threshold': 3,  # Falhas consecutivas
            'circuit_breaker_timeout_minutes': 30,

            # Feature flags
            'enable_p3_healing': False,  # Começa desabilitado
            'enable_predictive_healing': True,
            'enable_correlation_based_healing': True,
            'enable_aggressive_mode': False,  # Para emergências

            # Thresholds
            'min_prediction_confidence': 0.7,
            'min_memory_confidence': 0.6,
            'cooldown_between_healings_seconds': 60,
        }

    def _load_state(self) -> Dict[str, Any]:
        """Carrega estado do healer"""
        try:
            if self.state_file.exists():
                with open(self.state_file) as f:
                    return json.load(f)
        except:
            pass
        return {
            'error_budget': {
                'failures': [],
                'available': True
            },
            'circuit_breaker': {
                'state': 'closed',  # closed, open, half-open
                'consecutive_failures': 0,
                'last_failure': None,
                'opened_at': None
            },
            'last_healing': None,
            'healings_today': 0,
            'p3_unlocked': False,
            'feature_flags': {}
        }

    def _save_state(self):
        """Salva estado"""
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2, default=str)

    def heal(
        self,
        issues: List[Dict[str, Any]],
        metrics: Dict[str, Any],
        logs: Dict[str, Any] = None,
        test_results: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Executa healing contextual inteligente

        Args:
            issues: Lista de issues/gaps detectados
            metrics: Métricas atuais do sistema
            logs: Logs recentes
            test_results: Resultados de testes

        Returns:
            Resultado do healing com análise completa
        """
        now = datetime.now()

        result = {
            'timestamp': now.isoformat(),
            'issues_received': len(issues),
            'issues_healed': 0,
            'issues_skipped': 0,
            'issues_failed': 0,
            'healings': [],
            'skipped_reasons': [],
            'context_analysis': {},
            'decisions': []
        }

        # 1. Verificar circuit breaker
        if not self._check_circuit_breaker():
            result['skipped_reasons'].append('Circuit breaker is OPEN')
            self.audit.log_decision(
                decision="Healing blocked by circuit breaker",
                reason=f"Circuit breaker is OPEN since {self.state['circuit_breaker'].get('opened_at')}",
                chosen_action="skip_all"
            )
            return result

        # 2. Verificar error budget
        if not self._check_error_budget():
            result['skipped_reasons'].append('Error budget exhausted')
            self.audit.log_decision(
                decision="Healing blocked by error budget",
                reason="Too many recent failures",
                chosen_action="skip_all"
            )
            return result

        # 3. Verificar cooldown
        if not self._check_cooldown():
            result['skipped_reasons'].append('Cooldown period active')
            return result

        # 4. Obter contexto completo
        context = self._build_context(metrics, logs, test_results)
        result['context_analysis'] = context

        # 5. Correlacionar para entender situação
        correlation_data = self.correlation.correlate(
            logs or {'logs': {}},
            metrics,
            {'gaps': issues},
            test_results
        )
        result['correlation'] = {
            'patterns_detected': len(correlation_data.get('patterns_detected', [])),
            'root_causes': len(correlation_data.get('root_causes', [])),
            'risk_level': correlation_data.get('risk_assessment', {}).get('level', 'unknown')
        }

        # 6. Classificar dinamicamente
        classified_issues = self.severity.classify(issues, correlation_data)

        # 7. Obter predições
        prediction_data = self.predictor.predict(metrics)
        result['prediction'] = {
            'risk_level': prediction_data.get('risk_level', 'unknown'),
            'warnings': prediction_data.get('warnings', [])
        }

        # 8. Decidir e executar healing para cada issue
        for issue in classified_issues:
            healing_result = self._heal_single_issue(
                issue, context, correlation_data, prediction_data
            )

            if healing_result['action'] == 'healed':
                result['issues_healed'] += 1
            elif healing_result['action'] == 'skipped':
                result['issues_skipped'] += 1
            else:
                result['issues_failed'] += 1

            result['healings'].append(healing_result)
            result['decisions'].append(healing_result.get('decision'))

        # 9. Atualizar estado
        self.state['last_healing'] = now.isoformat()
        self.state['healings_today'] += result['issues_healed']
        self._save_state()

        # 10. Auditar resultado geral
        self.audit.log_action(
            action="Contextual healing cycle completed",
            result=f"Healed: {result['issues_healed']}, Skipped: {result['issues_skipped']}, Failed: {result['issues_failed']}",
            details=result,
            success=result['issues_failed'] == 0
        )

        return result

    def _heal_single_issue(
        self,
        issue: Dict[str, Any],
        context: Dict[str, Any],
        correlation_data: Dict[str, Any],
        prediction_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Decide e executa healing para uma issue específica"""
        issue_type = issue.get('type', 'unknown')
        priority = issue.get('dynamic_priority', issue.get('priority', 'P4'))

        result = {
            'issue_type': issue_type,
            'original_priority': issue.get('original_priority', 'P4'),
            'dynamic_priority': priority,
            'action': 'skipped',
            'decision': {},
            'details': {}
        }

        # 1. Verificar se prioridade é permitida
        if priority == 'P3' and not self._is_p3_enabled():
            result['decision'] = {
                'decision': f'Skip P3 issue: {issue_type}',
                'reason': 'P3 healing not yet unlocked'
            }
            return result

        if priority in ['P1', 'P2']:
            result['decision'] = {
                'decision': f'Skip {priority} issue: {issue_type}',
                'reason': f'{priority} requires human intervention'
            }
            self.audit.log_decision(**result['decision'])
            return result

        # 2. Consultar memória operacional
        memory_prediction = self.memory.predict_outcome(
            {'type': issue_type, 'category': issue.get('category', '')},
            context
        )

        if not memory_prediction.get('recommended', True):
            if memory_prediction.get('warnings'):
                result['decision'] = {
                    'decision': f'Skip issue based on memory: {issue_type}',
                    'reason': memory_prediction['warnings'][0]
                }
                self.audit.log_decision(**result['decision'])
                return result

        # 3. Verificar se é causa raiz ou sintoma
        is_root_cause = self._is_root_cause(issue_type, correlation_data)
        if not is_root_cause and self._has_root_cause_identified(correlation_data):
            result['decision'] = {
                'decision': f'Skip symptom: {issue_type}',
                'reason': 'Issue is symptom, treating root cause first'
            }
            self.audit.log_decision(**result['decision'])
            return result

        # 4. Verificar predição de impacto
        if self.context_config['enable_predictive_healing']:
            should_heal = self._predict_healing_impact(issue, prediction_data)
            if not should_heal:
                result['decision'] = {
                    'decision': f'Skip based on prediction: {issue_type}',
                    'reason': 'Predicted negative impact or low benefit'
                }
                return result

        # 5. Executar healing via SafeHealer
        can_heal, reason = self.safe_healer.can_heal(issue)

        if not can_heal:
            result['action'] = 'skipped'
            result['decision'] = {
                'decision': f'Cannot heal: {issue_type}',
                'reason': reason
            }
            return result

        # 6. Decidir executar
        result['decision'] = {
            'decision': f'Execute healing: {issue_type}',
            'reason': f'All checks passed (memory confidence: {memory_prediction.get("confidence", 0):.0%})',
            'alternatives': ['skip', 'defer'],
            'chosen_action': 'heal'
        }
        self.audit.log_decision(**result['decision'])

        # 7. Capturar estado antes
        state_before = self._capture_state(context)

        # 8. Executar healing
        healing_result = self.safe_healer.safe_heal([issue])

        # 9. Capturar estado depois
        state_after = self._capture_state(self._build_context({}, None, None))

        # 10. Registrar resultado
        success = healing_result.get('healed_count', 0) > 0

        if success:
            result['action'] = 'healed'
            self._record_success(issue)
        else:
            result['action'] = 'failed'
            self._record_failure(issue)

        result['details'] = healing_result

        # 11. Registrar no memory
        self.memory.record_action(
            action={'type': issue_type, 'category': issue.get('category', '')},
            context=context,
            outcome={
                'success': success,
                'details': healing_result
            }
        )

        # 12. Auditar healing
        self.audit.log_healing(
            issue=issue,
            action_taken=f"heal_{issue_type}",
            result=healing_result,
            state_before=state_before,
            state_after=state_after,
            rollback_executed=healing_result.get('rollback_executed', False)
        )

        return result

    def _build_context(
        self,
        metrics: Dict[str, Any],
        logs: Dict[str, Any],
        test_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Constrói contexto completo do sistema"""
        now = datetime.now()

        # Determinar ranges
        cpu = metrics.get('cpu', {})
        cpu_val = cpu.get('percent', 0) if isinstance(cpu, dict) else cpu
        cpu_range = 'critical' if cpu_val > 90 else ('high' if cpu_val > 70 else ('medium' if cpu_val > 50 else 'low'))

        memory = metrics.get('memory', {})
        mem_val = memory.get('percent', 0) if isinstance(memory, dict) else memory
        memory_range = 'critical' if mem_val > 90 else ('high' if mem_val > 70 else ('medium' if mem_val > 50 else 'low'))

        # Determinar período do dia
        hour = now.hour
        if 8 <= hour < 12:
            time_of_day = 'morning_peak'
        elif 12 <= hour < 14:
            time_of_day = 'lunch'
        elif 14 <= hour < 18:
            time_of_day = 'afternoon_peak'
        elif 18 <= hour < 22:
            time_of_day = 'evening'
        else:
            time_of_day = 'night'

        # Contar issues concorrentes
        concurrent_issues = len(logs.get('logs', {}).get('errors', [])) if logs else 0

        return {
            'cpu_range': cpu_range,
            'memory_range': memory_range,
            'disk_range': 'unknown',
            'time_of_day': time_of_day,
            'day_of_week': now.strftime('%A'),
            'is_business_hours': 8 <= hour < 18 and now.weekday() < 5,
            'concurrent_issues': concurrent_issues,
            'healings_today': self.state.get('healings_today', 0),
            'circuit_breaker_state': self.state['circuit_breaker']['state'],
            'error_budget_available': self._check_error_budget()
        }

    def _capture_state(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Captura estado atual para comparação"""
        return {
            'timestamp': datetime.now().isoformat(),
            'cpu_range': context.get('cpu_range', 'unknown'),
            'memory_range': context.get('memory_range', 'unknown'),
            'healings_today': context.get('healings_today', 0)
        }

    def _check_circuit_breaker(self) -> bool:
        """Verifica estado do circuit breaker"""
        cb = self.state['circuit_breaker']

        if cb['state'] == 'closed':
            return True

        if cb['state'] == 'open':
            # Verificar timeout
            if cb.get('opened_at'):
                opened = datetime.fromisoformat(cb['opened_at'])
                timeout = timedelta(minutes=self.context_config['circuit_breaker_timeout_minutes'])
                if datetime.now() - opened > timeout:
                    # Transição para half-open
                    cb['state'] = 'half-open'
                    self._save_state()
                    return True
            return False

        # half-open permite uma tentativa
        return True

    def _check_error_budget(self) -> bool:
        """Verifica se error budget está disponível"""
        eb = self.state['error_budget']
        now = datetime.now()
        window = timedelta(hours=self.context_config['error_budget_window_hours'])

        # Limpar failures antigas
        recent_failures = []
        for failure in eb.get('failures', []):
            try:
                fail_time = datetime.fromisoformat(failure.get('timestamp', '2000-01-01'))
                if now - fail_time < window:
                    recent_failures.append(failure)
            except:
                pass

        eb['failures'] = recent_failures

        # Verificar limite
        if len(recent_failures) >= self.context_config['max_failed_healings']:
            eb['available'] = False
            return False

        eb['available'] = True
        return True

    def _check_cooldown(self) -> bool:
        """Verifica cooldown entre healings"""
        last = self.state.get('last_healing')
        if not last:
            return True

        try:
            last_time = datetime.fromisoformat(last)
            cooldown = timedelta(seconds=self.context_config['cooldown_between_healings_seconds'])
            return datetime.now() - last_time >= cooldown
        except:
            return True

    def _is_p3_enabled(self) -> bool:
        """Verifica se P3 healing está habilitado"""
        if self.context_config.get('enable_aggressive_mode'):
            return True

        if self.state.get('p3_unlocked'):
            return True

        # Verificar condições para desbloquear
        healing_score = self.safe_healer.healing_score.get('current_score', 0)
        p4_successes = self.safe_healer.healing_score.get('p4_successes', 0)

        if healing_score >= 8 and p4_successes >= 20:
            self.state['p3_unlocked'] = True
            self._save_state()
            self.audit.log_action(
                action="P3 healing unlocked",
                result="Feature flag enabled",
                details={'healing_score': healing_score, 'p4_successes': p4_successes},
                success=True
            )
            return True

        return False

    def _is_root_cause(
        self,
        issue_type: str,
        correlation_data: Dict[str, Any]
    ) -> bool:
        """Verifica se issue é causa raiz"""
        root_causes = correlation_data.get('root_causes', [])

        for cause in root_causes:
            if issue_type in str(cause.get('cause', '')):
                return True

        return False

    def _has_root_cause_identified(
        self,
        correlation_data: Dict[str, Any]
    ) -> bool:
        """Verifica se há causa raiz identificada"""
        root_causes = correlation_data.get('root_causes', [])
        return len(root_causes) > 0

    def _predict_healing_impact(
        self,
        issue: Dict[str, Any],
        prediction_data: Dict[str, Any]
    ) -> bool:
        """Prediz impacto do healing"""
        risk_level = prediction_data.get('risk_level', 'low')

        # Em risco alto/crítico, ser mais conservador
        if risk_level in ['high', 'critical']:
            priority = issue.get('dynamic_priority', 'P4')
            if priority == 'P4':
                # P4 não vale a pena durante risco alto
                return False

        return True

    def _record_success(self, issue: Dict[str, Any]):
        """Registra sucesso no healing"""
        cb = self.state['circuit_breaker']

        # Reset consecutive failures
        cb['consecutive_failures'] = 0

        # Se estava half-open, fechar
        if cb['state'] == 'half-open':
            cb['state'] = 'closed'
            cb['opened_at'] = None

        self._save_state()

    def _record_failure(self, issue: Dict[str, Any]):
        """Registra falha no healing"""
        now = datetime.now()

        # Error budget
        eb = self.state['error_budget']
        eb['failures'].append({
            'issue_type': issue.get('type'),
            'timestamp': now.isoformat()
        })

        # Circuit breaker
        cb = self.state['circuit_breaker']
        cb['consecutive_failures'] += 1
        cb['last_failure'] = now.isoformat()

        # Verificar threshold
        if cb['consecutive_failures'] >= self.context_config['circuit_breaker_threshold']:
            cb['state'] = 'open'
            cb['opened_at'] = now.isoformat()

            self.audit.log_action(
                action="Circuit breaker opened",
                result=f"Consecutive failures: {cb['consecutive_failures']}",
                details={'threshold': self.context_config['circuit_breaker_threshold']},
                success=False
            )

        self._save_state()

    def get_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas do contextual healer"""
        return {
            'circuit_breaker': self.state['circuit_breaker'],
            'error_budget': {
                'available': self.state['error_budget'].get('available', True),
                'recent_failures': len(self.state['error_budget'].get('failures', []))
            },
            'healings_today': self.state.get('healings_today', 0),
            'p3_unlocked': self.state.get('p3_unlocked', False),
            'last_healing': self.state.get('last_healing'),
            'safe_healer': self.safe_healer.healing_state,
            'memory_stats': self.memory.get_statistics(),
            'predictor_stats': self.predictor.get_statistics(),
            'audit_stats': self.audit.get_statistics()
        }


if __name__ == '__main__':
    # Teste
    healer = ContextualHealer({})

    test_issues = [
        {
            'type': 'unused_dependency',
            'priority': 'P4',
            'severity': 'low',
            'category': 'dependencies'
        },
        {
            'type': 'high_cpu',
            'priority': 'P3',
            'severity': 'medium',
            'category': 'performance'
        }
    ]

    test_metrics = {
        'cpu': {'percent': 65},
        'memory': {'percent': 70},
        'disk': {'percent': 50}
    }

    result = healer.heal(test_issues, test_metrics)

    print("=== Contextual Healer ===\n")
    print(f"Issues recebidas: {result['issues_received']}")
    print(f"Issues curadas: {result['issues_healed']}")
    print(f"Issues ignoradas: {result['issues_skipped']}")
    print(f"Issues falharam: {result['issues_failed']}")

    print(f"\nDecisões:")
    for decision in result['decisions']:
        if decision:
            print(f"  - {decision.get('decision', 'N/A')}")
            print(f"    Razão: {decision.get('reason', 'N/A')}")

    print(f"\n=== Estatísticas ===")
    print(json.dumps(healer.get_statistics(), indent=2, default=str))
