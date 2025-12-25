"""
Skill: Dynamic Severity Classification (Classificação Dinâmica de Severidade)
Classifica problemas com base em impacto real, frequência histórica e probabilidade de escalada

Conceitos:
- P4 Recorrente: P4 que ocorre 3x+ se torna P3
- P3 Latente: P3 não tratado em 24h se torna P2
- Falha Silenciosa: Problema detectado por correlação sem alerta explícito
"""

import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict


class DynamicSeverityClassifier:
    """
    Classificador Dinâmico de Severidade

    Fatores de classificação:
    - Impacto no negócio (Business Impact)
    - Frequência histórica
    - Probabilidade de escalada
    - Contexto temporal (horário de pico, etc)
    """

    # Pesos dos fatores
    FACTOR_WEIGHTS = {
        'business_impact': 0.35,
        'historical_frequency': 0.25,
        'escalation_probability': 0.20,
        'temporal_context': 0.10,
        'correlation_severity': 0.10
    }

    # Mapeamento de impacto no negócio
    BUSINESS_IMPACT = {
        # P1 - Crítico (impacto total)
        'payment_system_down': 100,
        'authentication_failed': 100,
        'database_unreachable': 100,
        'api_gateway_down': 100,

        # P2 - Alto (impacto significativo)
        'slow_response_time': 70,
        'partial_service_degradation': 70,
        'backup_system_failed': 70,
        'memory_critical': 70,

        # P3 - Médio (impacto moderado)
        'high_cpu': 50,
        'disk_warning': 50,
        'deprecated_api_usage': 40,
        'log_errors_high': 45,

        # P4 - Baixo (impacto mínimo)
        'unused_dependency': 15,
        'outdated_package': 20,
        'code_style_violation': 10,
        'excessive_any': 10,
        'missing_type': 15,
    }

    # Probabilidade de escalada por tipo
    ESCALATION_PROBABILITY = {
        'memory_leak': 0.85,          # Alta - sempre escala
        'disk_filling': 0.80,         # Alta - espaço acaba
        'high_cpu': 0.60,             # Média - pode estabilizar
        'slow_queries': 0.70,         # Alta - degradação progressiva
        'deprecated_api': 0.40,       # Média - risco futuro
        'security_vulnerability': 0.90,  # Muito alta
        'outdated_package': 0.30,     # Baixa - mas acumula
        'code_style': 0.05,           # Muito baixa
    }

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.state_dir = Path('/opt/conecta-plus/agents/system-monitor/state')
        self.state_dir.mkdir(parents=True, exist_ok=True)

        self.history_file = self.state_dir / 'severity_history.json'
        self.escalations_file = self.state_dir / 'escalations.json'

        self.history = self._load_history()
        self.escalations = self._load_escalations()

        # Configuração de escalada
        self.escalation_config = {
            'p4_to_p3_occurrences': 3,      # P4 vira P3 após 3 ocorrências
            'p3_to_p2_hours': 24,           # P3 vira P2 após 24h sem tratamento
            'p2_to_p1_hours': 6,            # P2 vira P1 após 6h em horário crítico
            'recurrence_window_hours': 72,  # Janela para contar recorrência
        }

        # Horários de pico (impacto maior)
        self.peak_hours = list(range(8, 12)) + list(range(14, 18))  # 8-12 e 14-18

    def _load_history(self) -> Dict[str, Any]:
        """Carrega histórico de severidades"""
        try:
            if self.history_file.exists():
                with open(self.history_file) as f:
                    return json.load(f)
        except:
            pass
        return {
            'occurrences': {},  # {issue_type: [timestamps]}
            'escalations': [],   # Histórico de escaladas
            'treated': [],       # Issues tratadas
            'silent_failures': []  # Falhas silenciosas detectadas
        }

    def _save_history(self):
        """Salva histórico"""
        with open(self.history_file, 'w') as f:
            json.dump(self.history, f, indent=2, default=str)

    def _load_escalations(self) -> Dict[str, Any]:
        """Carrega estado de escalações pendentes"""
        try:
            if self.escalations_file.exists():
                with open(self.escalations_file) as f:
                    return json.load(f)
        except:
            pass
        return {
            'pending_p3': {},  # {issue_id: first_seen_timestamp}
            'pending_p2': {},
            'escalated': []
        }

    def _save_escalations(self):
        """Salva estado de escalações"""
        with open(self.escalations_file, 'w') as f:
            json.dump(self.escalations, f, indent=2, default=str)

    def classify(
        self,
        issues: List[Dict[str, Any]],
        correlation_data: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Classifica dinamicamente todas as issues

        Returns:
            Lista de issues com severidade dinâmica calculada
        """
        classified_issues = []
        now = datetime.now()

        for issue in issues:
            classified = self._classify_single(issue, correlation_data, now)
            classified_issues.append(classified)

            # Registrar ocorrência
            self._record_occurrence(issue, now)

        # Verificar escalações pendentes
        self._check_pending_escalations(now)

        # Salvar estado
        self._save_history()
        self._save_escalations()

        return classified_issues

    def _classify_single(
        self,
        issue: Dict[str, Any],
        correlation_data: Dict[str, Any],
        now: datetime
    ) -> Dict[str, Any]:
        """Classifica uma única issue"""
        issue_type = issue.get('type', 'unknown')
        original_priority = issue.get('priority', 'P4')
        original_severity = issue.get('severity', 'low')

        # Calcular fatores
        factors = {
            'business_impact': self._calc_business_impact(issue),
            'historical_frequency': self._calc_historical_frequency(issue_type, now),
            'escalation_probability': self._calc_escalation_probability(issue_type),
            'temporal_context': self._calc_temporal_context(now),
            'correlation_severity': self._calc_correlation_severity(issue, correlation_data)
        }

        # Calcular score composto
        composite_score = sum(
            factors[factor] * weight
            for factor, weight in self.FACTOR_WEIGHTS.items()
        )

        # Determinar nova prioridade
        new_priority, new_severity, escalation_reason = self._determine_priority(
            issue, composite_score, factors, original_priority, now
        )

        # Detectar se é falha silenciosa
        is_silent = self._is_silent_failure(issue, correlation_data)

        # Criar issue classificada
        classified = {
            **issue,
            'original_priority': original_priority,
            'original_severity': original_severity,
            'dynamic_priority': new_priority,
            'dynamic_severity': new_severity,
            'composite_score': round(composite_score, 2),
            'factors': factors,
            'escalated': new_priority != original_priority,
            'escalation_reason': escalation_reason,
            'is_silent_failure': is_silent,
            'classification_timestamp': now.isoformat()
        }

        # Se escalou, registrar
        if classified['escalated']:
            self._record_escalation(classified, now)

        return classified

    def _calc_business_impact(self, issue: Dict[str, Any]) -> float:
        """Calcula impacto no negócio (0-100)"""
        issue_type = issue.get('type', 'unknown')

        # Buscar impacto direto
        if issue_type in self.BUSINESS_IMPACT:
            return self.BUSINESS_IMPACT[issue_type]

        # Estimar por categoria
        category = issue.get('category', '')
        if category == 'security':
            return 80
        elif category == 'performance':
            return 50
        elif category == 'dependencies':
            return 25
        elif category == 'code_quality':
            return 15

        return 20  # Default baixo

    def _calc_historical_frequency(self, issue_type: str, now: datetime) -> float:
        """Calcula frequência histórica (0-100)"""
        occurrences = self.history.get('occurrences', {}).get(issue_type, [])

        if not occurrences:
            return 0

        # Contar ocorrências na janela de recorrência
        window_hours = self.escalation_config['recurrence_window_hours']
        cutoff = now - timedelta(hours=window_hours)

        recent_count = 0
        for occ in occurrences:
            try:
                occ_time = datetime.fromisoformat(occ)
                if occ_time >= cutoff:
                    recent_count += 1
            except:
                pass

        # Score baseado em frequência
        # 1 ocorrência = 10, 3+ = 50, 10+ = 100
        if recent_count >= 10:
            return 100
        elif recent_count >= 5:
            return 75
        elif recent_count >= 3:
            return 50
        elif recent_count >= 1:
            return 25
        return 0

    def _calc_escalation_probability(self, issue_type: str) -> float:
        """Calcula probabilidade de escalada (0-100)"""
        if issue_type in self.ESCALATION_PROBABILITY:
            return self.ESCALATION_PROBABILITY[issue_type] * 100

        # Estimar por padrões no nome
        if 'memory' in issue_type or 'leak' in issue_type:
            return 80
        elif 'disk' in issue_type or 'storage' in issue_type:
            return 75
        elif 'security' in issue_type or 'vuln' in issue_type:
            return 90
        elif 'deprecated' in issue_type:
            return 40
        elif 'style' in issue_type or 'lint' in issue_type:
            return 5

        return 30  # Default moderado

    def _calc_temporal_context(self, now: datetime) -> float:
        """Calcula contexto temporal (0-100)"""
        score = 50  # Base

        # Horário de pico
        if now.hour in self.peak_hours:
            score += 30

        # Dia da semana (seg-sex mais crítico)
        if now.weekday() < 5:  # Segunda a sexta
            score += 20

        # Fim de mês (mais crítico para sistemas financeiros)
        if now.day >= 25:
            score += 10

        return min(score, 100)

    def _calc_correlation_severity(
        self,
        issue: Dict[str, Any],
        correlation_data: Dict[str, Any]
    ) -> float:
        """Calcula severidade baseada em correlação (0-100)"""
        if not correlation_data:
            return 30  # Neutro sem dados

        issue_type = issue.get('type', '')

        # Verificar se é parte de causa raiz
        root_causes = correlation_data.get('root_causes', [])
        for cause in root_causes:
            if issue_type in str(cause.get('cause', '')):
                return 90  # Alta - é causa raiz

        # Verificar padrões correlacionados
        patterns = correlation_data.get('patterns_detected', [])
        for pattern in patterns:
            if pattern.get('confidence', 0) >= 0.7:
                return 70  # Média-alta - parte de padrão

        # Verificar risco geral
        risk = correlation_data.get('risk_assessment', {})
        risk_level = risk.get('level', 'low')

        if risk_level == 'critical':
            return 80
        elif risk_level == 'high':
            return 60
        elif risk_level == 'medium':
            return 40

        return 30

    def _determine_priority(
        self,
        issue: Dict[str, Any],
        score: float,
        factors: Dict[str, float],
        original: str,
        now: datetime
    ) -> Tuple[str, str, str]:
        """
        Determina nova prioridade baseada no score

        Returns:
            (new_priority, new_severity, escalation_reason)
        """
        issue_type = issue.get('type', 'unknown')
        issue_id = f"{issue_type}_{issue.get('file', 'unknown')}"

        escalation_reason = None

        # Verificar P4 recorrente -> P3
        if original == 'P4':
            frequency = factors.get('historical_frequency', 0)
            if frequency >= 50:  # 3+ ocorrências
                return 'P3', 'medium', 'P4 recorrente (3+ ocorrências)'

        # Verificar P3 latente -> P2
        if original == 'P3':
            if issue_id in self.escalations.get('pending_p3', {}):
                first_seen = self.escalations['pending_p3'][issue_id]
                try:
                    first_time = datetime.fromisoformat(first_seen)
                    hours_pending = (now - first_time).total_seconds() / 3600
                    if hours_pending >= self.escalation_config['p3_to_p2_hours']:
                        return 'P2', 'high', f'P3 latente (não tratado por {int(hours_pending)}h)'
                except:
                    pass
            else:
                # Registrar como pendente
                self.escalations['pending_p3'][issue_id] = now.isoformat()

        # Verificar P2 em horário crítico -> P1
        if original == 'P2':
            if now.hour in self.peak_hours and factors.get('business_impact', 0) >= 70:
                if issue_id in self.escalations.get('pending_p2', {}):
                    first_seen = self.escalations['pending_p2'][issue_id]
                    try:
                        first_time = datetime.fromisoformat(first_seen)
                        hours_pending = (now - first_time).total_seconds() / 3600
                        if hours_pending >= self.escalation_config['p2_to_p1_hours']:
                            return 'P1', 'critical', f'P2 crítico em horário de pico ({int(hours_pending)}h)'
                    except:
                        pass
                else:
                    self.escalations['pending_p2'][issue_id] = now.isoformat()

        # Classificação por score composto
        if score >= 80:
            new_priority = 'P1'
            new_severity = 'critical'
            if original != 'P1':
                escalation_reason = f'Score crítico ({score:.0f})'
        elif score >= 60:
            new_priority = 'P2'
            new_severity = 'high'
            if original not in ['P1', 'P2']:
                escalation_reason = f'Score alto ({score:.0f})'
        elif score >= 40:
            new_priority = 'P3'
            new_severity = 'medium'
            if original == 'P4':
                escalation_reason = f'Score médio ({score:.0f})'
        else:
            new_priority = 'P4'
            new_severity = 'low'

        return new_priority, new_severity, escalation_reason

    def _is_silent_failure(
        self,
        issue: Dict[str, Any],
        correlation_data: Dict[str, Any]
    ) -> bool:
        """Detecta se é uma falha silenciosa"""
        if not correlation_data:
            return False

        # Falha silenciosa = detectada por correlação mas sem alerta explícito
        issue_type = issue.get('type', '')

        # Se aparece em root causes mas não tem severidade alta
        root_causes = correlation_data.get('root_causes', [])
        for cause in root_causes:
            if issue_type in str(cause.get('cause', '')):
                original_severity = issue.get('severity', 'low')
                if original_severity == 'low':
                    # Registrar como falha silenciosa
                    self.history['silent_failures'].append({
                        'issue_type': issue_type,
                        'detected_at': datetime.now().isoformat(),
                        'correlation_evidence': cause
                    })
                    return True

        return False

    def _record_occurrence(self, issue: Dict[str, Any], now: datetime):
        """Registra ocorrência de issue"""
        issue_type = issue.get('type', 'unknown')

        if issue_type not in self.history['occurrences']:
            self.history['occurrences'][issue_type] = []

        self.history['occurrences'][issue_type].append(now.isoformat())

        # Manter apenas últimas 100 ocorrências por tipo
        self.history['occurrences'][issue_type] = \
            self.history['occurrences'][issue_type][-100:]

    def _record_escalation(self, issue: Dict[str, Any], now: datetime):
        """Registra escalação"""
        self.history['escalations'].append({
            'issue_type': issue.get('type'),
            'from_priority': issue.get('original_priority'),
            'to_priority': issue.get('dynamic_priority'),
            'reason': issue.get('escalation_reason'),
            'timestamp': now.isoformat()
        })

        # Manter últimas 500 escalações
        self.history['escalations'] = self.history['escalations'][-500:]

    def _check_pending_escalations(self, now: datetime):
        """Verifica e processa escalações pendentes"""
        # Limpar P3 pendentes que foram tratadas
        p3_pending = self.escalations.get('pending_p3', {})
        for issue_id in list(p3_pending.keys()):
            if issue_id in [t.get('id') for t in self.history.get('treated', [])]:
                del p3_pending[issue_id]

        # Limpar pendentes antigos (mais de 1 semana)
        week_ago = now - timedelta(days=7)
        for pending_dict in [self.escalations.get('pending_p3', {}),
                            self.escalations.get('pending_p2', {})]:
            for issue_id in list(pending_dict.keys()):
                try:
                    timestamp = datetime.fromisoformat(pending_dict[issue_id])
                    if timestamp < week_ago:
                        del pending_dict[issue_id]
                except:
                    pass

    def mark_as_treated(self, issue_id: str):
        """Marca issue como tratada"""
        self.history['treated'].append({
            'id': issue_id,
            'treated_at': datetime.now().isoformat()
        })

        # Remover de pendentes
        for pending_dict in [self.escalations.get('pending_p3', {}),
                            self.escalations.get('pending_p2', {})]:
            if issue_id in pending_dict:
                del pending_dict[issue_id]

        self._save_history()
        self._save_escalations()

    def get_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas de classificação"""
        now = datetime.now()
        last_24h = now - timedelta(hours=24)

        # Contar escalações recentes
        recent_escalations = [
            e for e in self.history.get('escalations', [])
            if datetime.fromisoformat(e.get('timestamp', '2000-01-01')) >= last_24h
        ]

        # Contar por tipo
        escalation_types = defaultdict(int)
        for e in recent_escalations:
            reason = e.get('reason', 'unknown')
            if 'recorrente' in reason.lower():
                escalation_types['p4_recorrente'] += 1
            elif 'latente' in reason.lower():
                escalation_types['p3_latente'] += 1
            elif 'pico' in reason.lower():
                escalation_types['horario_pico'] += 1
            else:
                escalation_types['score_alto'] += 1

        return {
            'total_escalations_24h': len(recent_escalations),
            'escalation_types': dict(escalation_types),
            'pending_p3': len(self.escalations.get('pending_p3', {})),
            'pending_p2': len(self.escalations.get('pending_p2', {})),
            'silent_failures_detected': len(self.history.get('silent_failures', [])),
            'total_issues_tracked': sum(
                len(v) for v in self.history.get('occurrences', {}).values()
            )
        }


if __name__ == '__main__':
    # Teste
    classifier = DynamicSeverityClassifier({})

    test_issues = [
        {
            'type': 'unused_dependency',
            'priority': 'P4',
            'severity': 'low',
            'category': 'dependencies',
            'file': 'package.json'
        },
        {
            'type': 'high_cpu',
            'priority': 'P3',
            'severity': 'medium',
            'category': 'performance',
            'file': 'system'
        },
        {
            'type': 'memory_leak',
            'priority': 'P3',
            'severity': 'medium',
            'category': 'performance',
            'file': 'backend'
        }
    ]

    # Simular múltiplas ocorrências de unused_dependency
    for _ in range(5):
        classifier._record_occurrence(test_issues[0], datetime.now())

    classified = classifier.classify(test_issues)

    print("=== Classificação Dinâmica ===\n")
    for issue in classified:
        print(f"Tipo: {issue['type']}")
        print(f"  Original: {issue['original_priority']} ({issue['original_severity']})")
        print(f"  Dinâmica: {issue['dynamic_priority']} ({issue['dynamic_severity']})")
        print(f"  Score: {issue['composite_score']}")
        print(f"  Escalado: {issue['escalated']}")
        if issue['escalation_reason']:
            print(f"  Razão: {issue['escalation_reason']}")
        print()

    print("\n=== Estatísticas ===")
    print(json.dumps(classifier.get_statistics(), indent=2))
