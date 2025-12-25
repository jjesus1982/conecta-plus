#!/usr/bin/env python3
"""
Conecta Plus System Monitor Agent
Agente autônomo de monitoramento e correção do sistema
"""

import os
import sys
import time
import json
import yaml
import logging
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path

# Adicionar diretório ao path
sys.path.insert(0, str(Path(__file__).parent))

# Importar skills
from skills.log_analyzer import LogAnalyzer
from skills.error_fixer import ErrorFixer
from skills.gap_detector import GapDetector
from skills.reporter import Reporter
from skills.load_tester import LoadTester
from skills.integration_tester import IntegrationTester
from skills.edge_case_tester import EdgeCaseTester
from skills.security_auditor import SecurityAuditor
from skills.production_validator import ProductionValidator
from skills.database_monitor import DatabaseMonitor
from skills.container_monitor import ContainerMonitor
from skills.agent_monitor import AgentMonitor
from skills.network_monitor import NetworkMonitor
from skills.frontend_monitor import FrontendMonitor
from skills.backup_validator import BackupValidator
from skills.filesystem_watcher import FileSystemWatcher
from skills.api_profiler import APIProfiler
from skills.cache_monitor import CacheMonitor
from skills.auto_healer import AutoHealer
from skills.safe_healer import SafeHealer
from skills.health_scorer import HealthScorer
from skills.batch_fixer import BatchFixer

# Importar skills vNEXT (Reengenharia Avançada)
from skills.correlation_engine import CorrelationEngine
from skills.dynamic_severity import DynamicSeverityClassifier
from skills.operational_memory import OperationalMemory
from skills.failure_predictor import FailurePredictor
from skills.health_score_evolutivo import EvolutionaryHealthScore
from skills.forensic_audit import ForensicAudit
from skills.contextual_healer import ContextualHealer

# Importar MCPs
from mcps.logs_mcp import LogsMCP
from mcps.metrics_mcp import MetricsMCP
from mcps.code_analyzer_mcp import CodeAnalyzerMCP


class SystemMonitorAgent:
    """Agente autônomo de monitoramento do sistema"""

    def __init__(self, config_path: str = '/opt/conecta-plus/agents/system-monitor/config.yaml'):
        # Carregar configuração
        with open(config_path) as f:
            self.config = yaml.safe_load(f)

        # Setup logging
        self._setup_logging()

        # Inicializar skills
        self.log_analyzer = LogAnalyzer(self.config)
        self.error_fixer = ErrorFixer(self.config)
        self.gap_detector = GapDetector(self.config)
        self.reporter = Reporter(self.config)
        self.load_tester = LoadTester(self.config)
        self.integration_tester = IntegrationTester(self.config)
        self.edge_case_tester = EdgeCaseTester(self.config)
        self.security_auditor = SecurityAuditor(self.config)
        self.production_validator = ProductionValidator(self.config)

        # Novas skills de monitoramento completo
        self.database_monitor = DatabaseMonitor(self.config)
        self.container_monitor = ContainerMonitor(self.config)
        self.agent_monitor = AgentMonitor(self.config)
        self.network_monitor = NetworkMonitor(self.config)
        self.frontend_monitor = FrontendMonitor(self.config)
        self.backup_validator = BackupValidator(self.config)
        self.filesystem_watcher = FileSystemWatcher(self.config)
        self.api_profiler = APIProfiler(self.config)
        self.cache_monitor = CacheMonitor(self.config)
        self.auto_healer = AutoHealer(self.config)
        self.safe_healer = SafeHealer(self.config)  # Novo sistema seguro
        self.health_scorer = HealthScorer(self.config)
        self.batch_fixer = BatchFixer(self.config)

        # Inicializar skills vNEXT (Reengenharia Avançada)
        self.correlation_engine = CorrelationEngine(self.config)
        self.severity_classifier = DynamicSeverityClassifier(self.config)
        self.operational_memory = OperationalMemory(self.config)
        self.failure_predictor = FailurePredictor(self.config)
        self.health_score_evolutivo = EvolutionaryHealthScore(self.config)
        self.forensic_audit = ForensicAudit(self.config)
        self.contextual_healer = ContextualHealer(self.config)

        # Inicializar MCPs
        self.logs_mcp = LogsMCP()
        self.metrics_mcp = MetricsMCP()
        self.code_mcp = CodeAnalyzerMCP()

        # Estado
        self.running = False
        self.iteration = 0
        self.total_errors_fixed = 0
        self.total_gaps_detected = 0
        self.total_tests_run = 0
        self.total_tests_passed = 0

        self.logger.info(f"System Monitor Agent v{self.config['agent']['version']} initialized")
        self.logger.info("Loaded 28 skills + 3 MCPs (vNEXT: Correlation, Prediction, Contextual Healing enabled!)")

    def _setup_logging(self):
        """Configura sistema de logging"""
        log_dir = '/opt/conecta-plus/agents/system-monitor/logs'
        os.makedirs(log_dir, exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f'{log_dir}/agent.log'),
                logging.StreamHandler()
            ]
        )

        self.logger = logging.getLogger('SystemMonitor')

    def run_monitoring_cycle(self) -> Dict[str, Any]:
        """
        Executa um ciclo completo de monitoramento

        Returns:
            Resultado do ciclo
        """
        self.iteration += 1
        cycle_start = datetime.now()

        self.logger.info(f"=== Monitoring Cycle #{self.iteration} Started ===")

        cycle_result = {
            'iteration': self.iteration,
            'timestamp': cycle_start.isoformat(),
            'log_analysis': {},
            'gaps': {},
            'fixes_applied': [],
            'metrics': {},
            'actions_taken': []
        }

        try:
            # 1. Analisar logs
            self.logger.info("1. Analyzing logs...")
            cycle_result['log_analysis'] = self.log_analyzer.analyze_all_logs()

            log_summary = cycle_result['log_analysis']
            self.logger.info(
                f"   Found {log_summary.get('total_errors', 0)} errors, "
                f"{log_summary.get('total_warnings', 0)} warnings"
            )

            # 2. Detectar gaps
            if self.config.get('gap_detection', {}).get('enabled', True):
                self.logger.info("2. Detecting gaps...")
                cycle_result['gaps'] = self.gap_detector.detect_all_gaps()

                # 2.1 Aplicar priorização inteligente (P1-P4)
                gaps_list = cycle_result['gaps'].get('gaps', [])
                prioritized = self.gap_detector.prioritize_gaps(gaps_list)
                cycle_result['gaps']['gaps'] = prioritized

                # Contar gaps por prioridade
                priority_counts = {'P1': 0, 'P2': 0, 'P3': 0, 'P4': 0}
                for gap in prioritized:
                    p = gap.get('priority', 'P4')
                    if p in priority_counts:
                        priority_counts[p] += 1
                cycle_result['gaps']['by_priority'] = priority_counts

                self.total_gaps_detected += cycle_result['gaps'].get('total_gaps', 0)
                self.logger.info(
                    f"   Detected {cycle_result['gaps'].get('total_gaps', 0)} gaps "
                    f"(P1:{priority_counts['P1']} P2:{priority_counts['P2']} P3:{priority_counts['P3']} P4:{priority_counts['P4']})"
                )

            # 3. VNEXT: Correlação e Análise Inteligente
            self.logger.info("3. vNEXT: Intelligent correlation analysis...")

            # 3.1 Correlacionar eventos (logs, métricas, gaps)
            correlation_data = self.correlation_engine.correlate(
                logs=cycle_result['log_analysis'],
                metrics=cycle_result.get('metrics', {}),
                gaps=cycle_result.get('gaps', {}),
                test_results=cycle_result.get('test_results')
            )
            cycle_result['correlation'] = {
                'patterns_detected': len(correlation_data.get('patterns_detected', [])),
                'root_causes': len(correlation_data.get('root_causes', [])),
                'risk_level': correlation_data.get('risk_assessment', {}).get('level', 'unknown'),
                'insights': correlation_data.get('insights', [])[:5]
            }
            self.logger.info(
                f"   Correlation: {cycle_result['correlation']['patterns_detected']} patterns, "
                f"{cycle_result['correlation']['root_causes']} root causes, "
                f"risk: {cycle_result['correlation']['risk_level']}"
            )

            # 3.2 Classificação Dinâmica de Severidade
            if cycle_result.get('gaps', {}).get('gaps'):
                self.logger.info("3.2 Dynamic severity classification...")
                classified_gaps = self.severity_classifier.classify(
                    cycle_result['gaps']['gaps'],
                    correlation_data
                )
                cycle_result['gaps']['gaps'] = classified_gaps

                # Contar escalações
                escalated = sum(1 for g in classified_gaps if g.get('escalated', False))
                silent_failures = sum(1 for g in classified_gaps if g.get('is_silent_failure', False))

                if escalated > 0 or silent_failures > 0:
                    self.logger.info(
                        f"   Dynamic classification: {escalated} escalated, {silent_failures} silent failures"
                    )

            # 3.3 Predição de Falhas
            self.logger.info("3.3 Failure prediction...")
            prediction_data = self.failure_predictor.predict(cycle_result.get('metrics', {}))
            cycle_result['prediction'] = {
                'risk_level': prediction_data.get('risk_level', 'unknown'),
                'warnings': prediction_data.get('warnings', []),
                'time_to_failure': prediction_data.get('time_to_failure', {}),
                'recommendations': prediction_data.get('recommendations', [])[:3]
            }
            if prediction_data.get('warnings'):
                self.logger.warning(f"   Prediction warnings: {prediction_data['warnings'][:2]}")

            # 4. Aplicar correções automáticas (CONTEXTUAL HEALER - vNEXT)
            if self.config.get('auto_fixes', {}).get('enabled', True):
                self.logger.info("4. vNEXT: Contextual intelligent healing...")

                # 4.1 Correções baseadas em logs (mantido)
                fixes = self._apply_auto_fixes(cycle_result['log_analysis'])

                # 4.2 CONTEXTUAL Healing - usa correlação, predição e memória
                if cycle_result.get('gaps', {}).get('gaps'):
                    self.logger.info("4.2 Contextual healing with correlation...")

                    # Usar ContextualHealer (integra tudo)
                    contextual_result = self.contextual_healer.heal(
                        issues=cycle_result['gaps']['gaps'],
                        metrics=cycle_result.get('metrics', {}),
                        logs=cycle_result['log_analysis'],
                        test_results=cycle_result.get('test_results')
                    )

                    # Converter resultado para formato compatível
                    for healing in contextual_result.get('healings', []):
                        if healing.get('action') == 'healed':
                            fixes.append({
                                'action': healing.get('issue_type', 'unknown'),
                                'success': True,
                                'validated': True,
                                'details': healing.get('details', {})
                            })

                    # Log detalhado do ContextualHealer
                    self.logger.info(
                        f"   Contextual healing: {contextual_result.get('issues_healed', 0)}/{contextual_result.get('issues_received', 0)} healed "
                        f"(skipped: {contextual_result.get('issues_skipped', 0)}, failed: {contextual_result.get('issues_failed', 0)})"
                    )

                    # Salvar resultado
                    cycle_result['contextual_healing'] = contextual_result

                    # Log das decisões tomadas
                    decisions = [d for d in contextual_result.get('decisions', []) if d]
                    if decisions:
                        self.logger.info(f"   Decisions made: {len(decisions)}")

                    # Também manter safe_healing para compatibilidade
                    safe_result = self.safe_healer.safe_heal([])  # Apenas para obter score
                    hs = safe_result.get('healing_score', {})
                    self.logger.info(
                        f"   Healing Score: {hs.get('current', 0):.1f}/10 "
                        f"(P4 successes: {hs.get('p4_successes', 0)}, P3 ready: {hs.get('p3_ready', False)})"
                    )
                    cycle_result['safe_healing'] = safe_result

                cycle_result['fixes_applied'] = fixes

                # Contabilizar apenas fixes validados com sucesso
                validated_fixes = sum(
                    1 for f in fixes
                    if f.get('success', False) and f.get('validated', False)
                )
                self.total_errors_fixed += validated_fixes

                self.logger.info(
                    f"   Applied {len(fixes)} total fixes ({validated_fixes} validated)"
                )

            # 5. Coletar métricas
            self.logger.info("5. Collecting system metrics...")
            cycle_result['metrics'] = self.metrics_mcp.get_system_info()

            # Verificar thresholds
            self._check_metric_thresholds(cycle_result['metrics'])

            # 6. Executar testes (a cada 5 minutos = 10 ciclos)
            if self.iteration % 10 == 0:
                self.logger.info("6. Running comprehensive tests...")
                cycle_result['test_results'] = self._run_comprehensive_tests()

                # Contabilizar testes
                test_summary = cycle_result['test_results'].get('summary', {})
                self.total_tests_run += test_summary.get('total_tests', 0)
                self.total_tests_passed += test_summary.get('passed_tests', 0)

                self.logger.info(
                    f"   Tests: {test_summary.get('passed_tests', 0)}/{test_summary.get('total_tests', 0)} passed "
                    f"(Score: {test_summary.get('overall_score', 0)}%)"
                )

            # 7. Calcular Health Score EVOLUTIVO (vNEXT!)
            self.logger.info("7. Calculating evolutionary health score...")

            # Usar Health Score Evolutivo (multidimensional, com tendência)
            health_evolutivo = self.health_score_evolutivo.calculate(
                metrics=cycle_result.get('metrics', {}),
                gaps=cycle_result.get('gaps', {}),
                correlation_data=correlation_data if 'correlation_data' in dir() else None,
                prediction_data=prediction_data if 'prediction_data' in dir() else None
            )

            # Também calcular o score tradicional para compatibilidade
            health_tradicional = self.health_scorer.calculate_health_score(
                gaps=cycle_result.get('gaps', {}),
                metrics=cycle_result.get('metrics', {}),
                test_results=cycle_result.get('test_results'),
                fixes_applied=cycle_result.get('fixes_applied', [])
            )

            cycle_result['health_score'] = health_tradicional
            cycle_result['health_score_evolutivo'] = {
                'score': health_evolutivo.get('overall_score', 0),
                'level': health_evolutivo.get('level', 'unknown'),
                'trend': health_evolutivo.get('trend', {}),
                'dimensions': health_evolutivo.get('dimensions', {}),
                'insights': health_evolutivo.get('insights', [])
            }

            self.logger.info(
                f"   Health Score Evolutivo: {health_evolutivo.get('overall_score', 0):.0f}/100 "
                f"({health_evolutivo.get('level', 'unknown').upper()}, "
                f"trend: {health_evolutivo.get('trend', {}).get('direction', 'unknown')})"
            )
            self.logger.info(
                f"   Health Score Tradicional: {health_tradicional['overall_score']}/100 "
                f"({health_tradicional['health_level']})"
            )

            # 8. Gerar relatórios (se configurado)
            if self.iteration % (3600 // self.config['agent']['interval']) == 0:
                # A cada hora
                self.logger.info("8. Generating periodic report...")
                self._generate_report(cycle_result)

            # 9. Registrar ações tomadas e auditar
            cycle_result['actions_taken'] = self._summarize_actions(cycle_result)

            # 9.1 Auditoria Forense (vNEXT)
            self.forensic_audit.log_action(
                action="Monitoring cycle completed",
                result=f"Cycle #{self.iteration} finished",
                details={
                    'gaps_detected': cycle_result.get('gaps', {}).get('total_gaps', 0),
                    'fixes_applied': len(cycle_result.get('fixes_applied', [])),
                    'correlation_patterns': cycle_result.get('correlation', {}).get('patterns_detected', 0),
                    'prediction_risk': cycle_result.get('prediction', {}).get('risk_level', 'unknown'),
                    'health_score': health_evolutivo.get('overall_score', 0) if 'health_evolutivo' in dir() else 0
                },
                success=True
            )

            # Duração do ciclo
            cycle_end = datetime.now()
            cycle_result['duration_seconds'] = (cycle_end - cycle_start).total_seconds()

            self.logger.info(
                f"=== Cycle completed in {cycle_result['duration_seconds']:.2f}s ==="
            )

            return cycle_result

        except Exception as e:
            self.logger.error(f"Error in monitoring cycle: {str(e)}", exc_info=True)
            return {
                'error': str(e),
                'iteration': self.iteration,
                'timestamp': datetime.now().isoformat()
            }

    def _apply_auto_fixes(self, log_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Aplica correções automáticas para erros detectados"""
        fixes = []

        # Coletar todos os erros
        all_errors = []
        for log_type, log_data in log_analysis.get('logs', {}).items():
            all_errors.extend(log_data.get('errors', []))

        # Aplicar correção para cada erro único
        seen_hashes = set()

        for error in all_errors:
            error_hash = error.get('hash')

            # Evitar corrigir o mesmo erro múltiplas vezes
            if error_hash in seen_hashes:
                continue

            seen_hashes.add(error_hash)

            # Tentar corrigir
            fix_result = self.error_fixer.fix_error(error)

            if fix_result.get('success'):
                self.logger.info(
                    f"   ✓ Fixed: {error.get('type', 'unknown')} - "
                    f"{fix_result.get('action', 'unknown')}"
                )
            else:
                self.logger.warning(
                    f"   ✗ Could not fix: {error.get('type', 'unknown')} - "
                    f"{fix_result.get('reason', 'unknown')}"
                )

            fixes.append({
                'error': error,
                'result': fix_result
            })

        return fixes

    def _check_metric_thresholds(self, metrics: Dict[str, Any]):
        """Verifica se métricas ultrapassaram thresholds"""
        thresholds = self.config.get('monitoring', {}).get('metrics', {})

        # CPU
        cpu_percent = metrics['cpu']['percent']
        cpu_threshold = thresholds.get('cpu_threshold', 90)

        if cpu_percent > cpu_threshold:
            self.logger.warning(f"   ⚠ High CPU usage: {cpu_percent:.1f}%")

        # Memory
        mem_percent = metrics['memory']['percent']
        mem_threshold = thresholds.get('memory_threshold', 85)

        if mem_percent > mem_threshold:
            self.logger.warning(f"   ⚠ High memory usage: {mem_percent:.1f}%")

        # Disk
        disk_percent = metrics['disk']['percent']
        disk_threshold = thresholds.get('disk_threshold', 90)

        if disk_percent > disk_threshold:
            self.logger.warning(f"   ⚠ High disk usage: {disk_percent:.1f}%")

    def _generate_report(self, cycle_result: Dict[str, Any]):
        """Gera relatório completo"""
        try:
            fix_stats = self.error_fixer.get_fix_statistics()

            report_paths = self.reporter.generate_report(
                log_analysis=cycle_result['log_analysis'],
                gaps=cycle_result['gaps'],
                fixes=fix_stats
            )

            self.logger.info(f"   Reports generated:")
            for format_type, path in report_paths.items():
                self.logger.info(f"     - {format_type}: {path}")

        except Exception as e:
            self.logger.error(f"   Error generating report: {str(e)}")

    def _summarize_actions(self, cycle_result: Dict[str, Any]) -> List[str]:
        """Resumo das ações tomadas"""
        actions = []

        # Erros corrigidos
        fixes = cycle_result.get('fixes_applied', [])
        if fixes:
            successful = sum(
                1 for f in fixes
                if isinstance(f, dict) and f.get('result', {}).get('success', False)
            )
            actions.append(f"Applied {successful}/{len(fixes)} automatic fixes")

        # Gaps detectados
        gaps = cycle_result.get('gaps', {})
        if gaps.get('critical_gaps', 0) > 0:
            actions.append(
                f"Detected {gaps['critical_gaps']} critical gaps requiring attention"
            )

        # Alertas de métricas
        metrics = cycle_result.get('metrics', {})
        if metrics:
            if metrics['cpu']['percent'] > 80:
                actions.append(f"High CPU usage: {metrics['cpu']['percent']:.1f}%")
            if metrics['memory']['percent'] > 80:
                actions.append(f"High memory usage: {metrics['memory']['percent']:.1f}%")

        return actions

    def _run_comprehensive_tests(self) -> Dict[str, Any]:
        """Executa bateria completa de testes"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'load_tests': {},
            'integration_tests': {},
            'edge_case_tests': {},
            'security_audit': {},
            'production_validation': {},
            'database_health': {},
            'container_health': {},
            'agent_health': {},
            'network_health': {},
            'frontend_health': {},
            'backup_status': {},
            'filesystem_status': {},
            'api_performance': {},
            'cache_health': {}
        }

        # 1. Load Tests
        self.logger.info("   → Load testing...")
        try:
            results['load_tests'] = self.load_tester.test_endpoints()
        except Exception as e:
            self.logger.error(f"   Load tests failed: {str(e)}")
            results['load_tests'] = {'error': str(e)}

        # 2. Integration Tests
        self.logger.info("   → Integration testing...")
        try:
            results['integration_tests'] = self.integration_tester.run_all_tests()
        except Exception as e:
            self.logger.error(f"   Integration tests failed: {str(e)}")
            results['integration_tests'] = {'error': str(e)}

        # 3. Edge Case Tests
        self.logger.info("   → Edge case testing...")
        try:
            results['edge_case_tests'] = self.edge_case_tester.run_all_tests()
        except Exception as e:
            self.logger.error(f"   Edge case tests failed: {str(e)}")
            results['edge_case_tests'] = {'error': str(e)}

        # 4. Security Audit
        self.logger.info("   → Security audit...")
        try:
            results['security_audit'] = self.security_auditor.run_all_audits()
        except Exception as e:
            self.logger.error(f"   Security audit failed: {str(e)}")
            results['security_audit'] = {'error': str(e)}

        # 5. Production Validation
        self.logger.info("   → Production validation...")
        try:
            results['production_validation'] = self.production_validator.run_all_validations()
        except Exception as e:
            self.logger.error(f"   Production validation failed: {str(e)}")
            results['production_validation'] = {'error': str(e)}

        # === MONITORAMENTO COMPLETO 100% ===

        # 6. Database Health Monitoring
        self.logger.info("   → Database health check...")
        try:
            results['database_health'] = self.database_monitor.check_all_databases()
        except Exception as e:
            self.logger.error(f"   Database check failed: {str(e)}")
            results['database_health'] = {'error': str(e)}

        # 7. Container Health Monitoring
        self.logger.info("   → Container health check...")
        try:
            results['container_health'] = self.container_monitor.run_full_check()
        except Exception as e:
            self.logger.error(f"   Container check failed: {str(e)}")
            results['container_health'] = {'error': str(e)}

        # 8. Agent Health Monitoring (TODOS os 15+ agentes)
        self.logger.info("   → Agent health check...")
        try:
            results['agent_health'] = self.agent_monitor.run_full_check()
        except Exception as e:
            self.logger.error(f"   Agent check failed: {str(e)}")
            results['agent_health'] = {'error': str(e)}

        # 9. Network & Connectivity Monitoring
        self.logger.info("   → Network health check...")
        try:
            results['network_health'] = self.network_monitor.run_full_check()
        except Exception as e:
            self.logger.error(f"   Network check failed: {str(e)}")
            results['network_health'] = {'error': str(e)}

        # 10. Frontend Health Monitoring
        self.logger.info("   → Frontend health check...")
        try:
            results['frontend_health'] = self.frontend_monitor.run_full_check()
        except Exception as e:
            self.logger.error(f"   Frontend check failed: {str(e)}")
            results['frontend_health'] = {'error': str(e)}

        # 11. Backup & Recovery Validation
        self.logger.info("   → Backup validation...")
        try:
            results['backup_status'] = self.backup_validator.run_full_validation()
        except Exception as e:
            self.logger.error(f"   Backup validation failed: {str(e)}")
            results['backup_status'] = {'error': str(e)}

        # 12. FileSystem & Disk Monitoring
        self.logger.info("   → Filesystem check...")
        try:
            results['filesystem_status'] = self.filesystem_watcher.run_full_check()
        except Exception as e:
            self.logger.error(f"   Filesystem check failed: {str(e)}")
            results['filesystem_status'] = {'error': str(e)}

        # 13. API Performance Profiling
        self.logger.info("   → API performance profiling...")
        try:
            results['api_performance'] = self.api_profiler.run_full_profile()
        except Exception as e:
            self.logger.error(f"   API profiling failed: {str(e)}")
            results['api_performance'] = {'error': str(e)}

        # 14. Cache Effectiveness Monitoring
        self.logger.info("   → Cache health check...")
        try:
            results['cache_health'] = self.cache_monitor.run_full_check()
        except Exception as e:
            self.logger.error(f"   Cache check failed: {str(e)}")
            results['cache_health'] = {'error': str(e)}

        # Gerar resumo geral
        results['summary'] = self._summarize_test_results(results)

        return results

    def _summarize_test_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Gera resumo dos resultados de testes"""
        summary = {
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'overall_score': 0,
            'critical_issues': []
        }

        # Load tests
        load_summary = results.get('load_tests', {}).get('summary', {})
        summary['load_health'] = load_summary.get('overall_health', 'unknown')
        summary['total_tests'] += load_summary.get('total_endpoints_tested', 0)
        summary['passed_tests'] += load_summary.get('passing', 0)

        # Integration tests
        for test_type in ['database_tests', 'crud_tests', 'external_services']:
            test_data = results.get('integration_tests', {}).get(test_type, {})
            test_summary = test_data.get('summary', {})
            summary['total_tests'] += test_summary.get('total_tests', 0)
            summary['passed_tests'] += test_summary.get('passed', 0)

        # Edge case tests
        for test_type in ['null_empty_tests', 'invalid_types_tests', 'boundary_tests', 'concurrent_tests']:
            test_data = results.get('edge_case_tests', {}).get(test_type, {})
            test_summary = test_data.get('summary', {})
            summary['total_tests'] += test_summary.get('total', 0)
            summary['passed_tests'] += test_summary.get('passed', 0)

        # Security audit
        security = results.get('security_audit', {})
        for audit_type in security.keys():
            if audit_type == 'timestamp':
                continue
            audit_summary = security[audit_type].get('summary', {})
            if 'security_score' in audit_summary:
                summary['security_score'] = audit_summary['security_score']
            if audit_summary.get('critical', 0) > 0 or audit_summary.get('high', 0) > 0:
                summary['critical_issues'].append({
                    'type': audit_type,
                    'critical': audit_summary.get('critical', 0),
                    'high': audit_summary.get('high', 0)
                })

        # Production validation
        prod_val = results.get('production_validation', {})
        for val_type in prod_val.keys():
            if val_type == 'timestamp':
                continue
            val_summary = prod_val[val_type].get('summary', {})
            if 'readiness_score' in val_summary:
                summary['production_readiness'] = val_summary['readiness_score']

        # Calcular score geral
        summary['failed_tests'] = summary['total_tests'] - summary['passed_tests']

        if summary['total_tests'] > 0:
            summary['overall_score'] = int((summary['passed_tests'] / summary['total_tests']) * 100)
        else:
            summary['overall_score'] = 0

        return summary

    def run(self):
        """Executa agente em loop contínuo"""
        self.running = True
        interval = self.config['agent']['interval']

        self.logger.info(f"Starting continuous monitoring (interval: {interval}s)")

        try:
            while self.running:
                # Executar ciclo
                cycle_result = self.run_monitoring_cycle()

                # Salvar estado
                self._save_state(cycle_result)

                # Aguardar próximo ciclo
                time.sleep(interval)

        except KeyboardInterrupt:
            self.logger.info("Received shutdown signal")
            self.stop()
        except Exception as e:
            self.logger.error(f"Fatal error: {str(e)}", exc_info=True)
            self.stop()

    def stop(self):
        """Para o agente"""
        self.logger.info("Shutting down System Monitor Agent...")

        # Gerar relatório final
        self.logger.info("Generating final report...")

        final_stats = {
            'total_iterations': self.iteration,
            'total_errors_fixed': self.total_errors_fixed,
            'total_gaps_detected': self.total_gaps_detected,
            'fix_statistics': self.error_fixer.get_fix_statistics()
        }

        self.logger.info(f"Final statistics: {json.dumps(final_stats, indent=2)}")

        self.running = False

    def _save_state(self, cycle_result: Dict[str, Any]):
        """Salva estado atual"""
        state_file = '/opt/conecta-plus/agents/system-monitor/state.json'

        state = {
            'last_update': datetime.now().isoformat(),
            'iteration': self.iteration,
            'total_errors_fixed': self.total_errors_fixed,
            'total_gaps_detected': self.total_gaps_detected,
            'total_tests_run': self.total_tests_run,
            'total_tests_passed': self.total_tests_passed,
            'last_cycle': cycle_result
        }

        try:
            with open(state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            self.logger.error(f"Could not save state: {str(e)}")


def main():
    """Função principal"""
    import argparse

    parser = argparse.ArgumentParser(description='Conecta Plus System Monitor Agent')
    parser.add_argument('--config', default='/opt/conecta-plus/agents/system-monitor/config.yaml',
                        help='Path to config file')
    parser.add_argument('--once', action='store_true',
                        help='Run once and exit')

    args = parser.parse_args()

    # Criar agente
    agent = SystemMonitorAgent(args.config)

    if args.once:
        # Executar uma vez
        result = agent.run_monitoring_cycle()
        print(json.dumps(result, indent=2))
    else:
        # Executar continuamente
        agent.run()


if __name__ == '__main__':
    main()
