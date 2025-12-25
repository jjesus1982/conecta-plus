"""
Skill: Operational Memory (Memória Operacional)
Sistema de aprendizado contínuo que mantém conhecimento sobre ações passadas,
seus resultados e usa esse conhecimento para melhorar decisões futuras.

Princípios:
- Aprender com cada ação (sucesso e falha)
- Construir base de conhecimento progressiva
- Usar histórico para prever resultados
- Detectar padrões de sucesso/falha
"""

import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
import statistics
import hashlib


class OperationalMemory:
    """
    Sistema de Memória Operacional

    Armazena e aprende:
    - Ações executadas e seus resultados
    - Contextos que levaram a sucesso/falha
    - Padrões de correlação ação-resultado
    - Conhecimento acumulado sobre o sistema
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.state_dir = Path('/opt/conecta-plus/agents/system-monitor/state')
        self.state_dir.mkdir(parents=True, exist_ok=True)

        self.memory_file = self.state_dir / 'operational_memory.json'
        self.knowledge_file = self.state_dir / 'system_knowledge.json'

        self.memory = self._load_memory()
        self.knowledge = self._load_knowledge()

        # Configuração de aprendizado
        self.learning_config = {
            'min_samples_for_confidence': 5,    # Mínimo de amostras para confiar
            'decay_factor': 0.95,               # Fator de decay para conhecimento antigo
            'success_weight': 1.0,              # Peso de sucesso
            'failure_weight': 1.5,              # Peso de falha (aprender mais com erros)
            'max_memory_entries': 10000,        # Máximo de entradas na memória
        }

    def _load_memory(self) -> Dict[str, Any]:
        """Carrega memória operacional"""
        try:
            if self.memory_file.exists():
                with open(self.memory_file) as f:
                    return json.load(f)
        except:
            pass
        return {
            'actions': [],          # Histórico de ações
            'outcomes': {},         # {action_hash: [outcomes]}
            'contexts': {},         # Contextos de execução
            'patterns': [],         # Padrões detectados
            'metadata': {
                'created_at': datetime.now().isoformat(),
                'total_actions': 0,
                'total_successes': 0,
                'total_failures': 0
            }
        }

    def _save_memory(self):
        """Salva memória"""
        with open(self.memory_file, 'w') as f:
            json.dump(self.memory, f, indent=2, default=str)

    def _load_knowledge(self) -> Dict[str, Any]:
        """Carrega base de conhecimento"""
        try:
            if self.knowledge_file.exists():
                with open(self.knowledge_file) as f:
                    return json.load(f)
        except:
            pass
        return {
            'action_effectiveness': {},   # {action_type: effectiveness_score}
            'context_correlations': {},   # {context_hash: {action: success_rate}}
            'known_issues': {},           # Issues conhecidas e soluções
            'best_practices': [],         # Melhores práticas aprendidas
            'anti_patterns': [],          # Anti-padrões a evitar
            'system_baseline': {},        # Baseline do sistema
        }

    def _save_knowledge(self):
        """Salva conhecimento"""
        with open(self.knowledge_file, 'w') as f:
            json.dump(self.knowledge, f, indent=2, default=str)

    def _hash_action(self, action: Dict[str, Any]) -> str:
        """Gera hash único para uma ação"""
        key_parts = [
            action.get('type', ''),
            action.get('target', ''),
            action.get('category', '')
        ]
        return hashlib.md5('|'.join(key_parts).encode()).hexdigest()[:12]

    def _hash_context(self, context: Dict[str, Any]) -> str:
        """Gera hash para um contexto"""
        relevant_parts = [
            str(context.get('cpu_range', '')),
            str(context.get('memory_range', '')),
            context.get('time_of_day', ''),
            str(context.get('concurrent_issues', 0))
        ]
        return hashlib.md5('|'.join(relevant_parts).encode()).hexdigest()[:12]

    def record_action(
        self,
        action: Dict[str, Any],
        context: Dict[str, Any],
        outcome: Dict[str, Any]
    ):
        """
        Registra uma ação e seu resultado para aprendizado

        Args:
            action: A ação executada
            context: Contexto do sistema quando a ação foi executada
            outcome: Resultado da ação (success, failure, metrics)
        """
        now = datetime.now()
        action_hash = self._hash_action(action)
        context_hash = self._hash_context(context)

        # Criar registro
        record = {
            'action_hash': action_hash,
            'action': action,
            'context_hash': context_hash,
            'context': context,
            'outcome': outcome,
            'timestamp': now.isoformat(),
            'success': outcome.get('success', False)
        }

        # Adicionar à memória
        self.memory['actions'].append(record)

        # Atualizar outcomes
        if action_hash not in self.memory['outcomes']:
            self.memory['outcomes'][action_hash] = []
        self.memory['outcomes'][action_hash].append({
            'success': outcome.get('success', False),
            'context_hash': context_hash,
            'timestamp': now.isoformat(),
            'details': outcome.get('details', {})
        })

        # Atualizar contextos
        if context_hash not in self.memory['contexts']:
            self.memory['contexts'][context_hash] = {
                'context': context,
                'actions': []
            }
        self.memory['contexts'][context_hash]['actions'].append({
            'action_hash': action_hash,
            'success': outcome.get('success', False),
            'timestamp': now.isoformat()
        })

        # Atualizar metadados
        self.memory['metadata']['total_actions'] += 1
        if outcome.get('success', False):
            self.memory['metadata']['total_successes'] += 1
        else:
            self.memory['metadata']['total_failures'] += 1

        # Limitar tamanho da memória
        if len(self.memory['actions']) > self.learning_config['max_memory_entries']:
            self.memory['actions'] = self.memory['actions'][-self.learning_config['max_memory_entries']:]

        # Aprender com a ação
        self._learn_from_action(record)

        # Salvar
        self._save_memory()
        self._save_knowledge()

    def _learn_from_action(self, record: Dict[str, Any]):
        """Aprende com uma ação registrada"""
        action_hash = record['action_hash']
        action_type = record['action'].get('type', 'unknown')
        success = record.get('success', False)

        # 1. Atualizar efetividade da ação
        if action_type not in self.knowledge['action_effectiveness']:
            self.knowledge['action_effectiveness'][action_type] = {
                'total': 0,
                'successes': 0,
                'score': 0.5,  # Neutro inicial
                'samples': []
            }

        eff = self.knowledge['action_effectiveness'][action_type]
        eff['total'] += 1
        if success:
            eff['successes'] += 1
        eff['score'] = eff['successes'] / eff['total'] if eff['total'] > 0 else 0.5

        # Manter últimas 100 amostras para análise
        eff['samples'].append({
            'success': success,
            'timestamp': record['timestamp'],
            'context_hash': record['context_hash']
        })
        eff['samples'] = eff['samples'][-100:]

        # 2. Correlacionar contexto com resultado
        context_hash = record['context_hash']
        if context_hash not in self.knowledge['context_correlations']:
            self.knowledge['context_correlations'][context_hash] = {}

        if action_type not in self.knowledge['context_correlations'][context_hash]:
            self.knowledge['context_correlations'][context_hash][action_type] = {
                'attempts': 0,
                'successes': 0,
                'success_rate': 0.5
            }

        corr = self.knowledge['context_correlations'][context_hash][action_type]
        corr['attempts'] += 1
        if success:
            corr['successes'] += 1
        corr['success_rate'] = corr['successes'] / corr['attempts']

        # 3. Detectar padrões
        self._detect_patterns()

        # 4. Atualizar melhores práticas / anti-padrões
        if success:
            self._update_best_practices(record)
        else:
            self._update_anti_patterns(record)

    def _detect_patterns(self):
        """Detecta padrões nos dados de memória"""
        patterns = []

        # Padrão 1: Ações que sempre falham em certo contexto
        for context_hash, actions in self.knowledge['context_correlations'].items():
            for action_type, stats in actions.items():
                if stats['attempts'] >= 3:
                    if stats['success_rate'] < 0.2:
                        patterns.append({
                            'type': 'consistent_failure',
                            'action': action_type,
                            'context': context_hash,
                            'success_rate': stats['success_rate'],
                            'recommendation': f'Evitar {action_type} neste contexto'
                        })
                    elif stats['success_rate'] > 0.9:
                        patterns.append({
                            'type': 'consistent_success',
                            'action': action_type,
                            'context': context_hash,
                            'success_rate': stats['success_rate'],
                            'recommendation': f'{action_type} é seguro neste contexto'
                        })

        # Padrão 2: Ações com tendência de piora
        for action_type, eff in self.knowledge['action_effectiveness'].items():
            samples = eff.get('samples', [])
            if len(samples) >= 10:
                recent = samples[-5:]
                older = samples[-10:-5]

                recent_rate = sum(1 for s in recent if s['success']) / 5
                older_rate = sum(1 for s in older if s['success']) / 5

                if recent_rate < older_rate - 0.3:  # Queda de 30%+
                    patterns.append({
                        'type': 'degrading_action',
                        'action': action_type,
                        'recent_rate': recent_rate,
                        'older_rate': older_rate,
                        'recommendation': f'{action_type} está ficando menos efetivo'
                    })

        self.memory['patterns'] = patterns

    def _update_best_practices(self, record: Dict[str, Any]):
        """Atualiza melhores práticas baseado em sucesso"""
        action_type = record['action'].get('type', 'unknown')

        # Verificar se é consistentemente bem sucedido
        eff = self.knowledge['action_effectiveness'].get(action_type, {})
        if eff.get('total', 0) >= 5 and eff.get('score', 0) >= 0.9:
            practice = {
                'action': action_type,
                'success_rate': eff['score'],
                'total_executions': eff['total'],
                'description': f'{action_type} é altamente efetivo ({eff["score"]:.0%} sucesso)'
            }

            # Verificar se já existe
            existing = [p for p in self.knowledge['best_practices']
                       if p.get('action') == action_type]
            if not existing:
                self.knowledge['best_practices'].append(practice)
            else:
                # Atualizar existente
                idx = self.knowledge['best_practices'].index(existing[0])
                self.knowledge['best_practices'][idx] = practice

        # Manter apenas top 20
        self.knowledge['best_practices'] = sorted(
            self.knowledge['best_practices'],
            key=lambda x: x.get('success_rate', 0),
            reverse=True
        )[:20]

    def _update_anti_patterns(self, record: Dict[str, Any]):
        """Atualiza anti-padrões baseado em falha"""
        action_type = record['action'].get('type', 'unknown')
        context_hash = record['context_hash']

        # Verificar se é consistentemente falho
        eff = self.knowledge['action_effectiveness'].get(action_type, {})
        if eff.get('total', 0) >= 3 and eff.get('score', 1) <= 0.3:
            anti_pattern = {
                'action': action_type,
                'context_hash': context_hash,
                'failure_rate': 1 - eff.get('score', 0),
                'total_failures': eff['total'] - eff.get('successes', 0),
                'description': f'{action_type} tem alta taxa de falha ({1-eff["score"]:.0%})'
            }

            # Verificar se já existe
            existing = [p for p in self.knowledge['anti_patterns']
                       if p.get('action') == action_type]
            if not existing:
                self.knowledge['anti_patterns'].append(anti_pattern)
            else:
                idx = self.knowledge['anti_patterns'].index(existing[0])
                self.knowledge['anti_patterns'][idx] = anti_pattern

    def predict_outcome(
        self,
        action: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Prevê o resultado de uma ação dado o contexto

        Returns:
            Predição com probabilidade de sucesso e confiança
        """
        action_type = action.get('type', 'unknown')
        context_hash = self._hash_context(context)

        # Coletar evidências
        evidence = {
            'action_history': None,
            'context_history': None,
            'patterns': []
        }

        # 1. Efetividade geral da ação
        action_eff = self.knowledge['action_effectiveness'].get(action_type, {})
        if action_eff:
            evidence['action_history'] = {
                'success_rate': action_eff.get('score', 0.5),
                'total_samples': action_eff.get('total', 0)
            }

        # 2. Histórico no contexto específico
        context_corr = self.knowledge['context_correlations'].get(context_hash, {})
        if action_type in context_corr:
            evidence['context_history'] = {
                'success_rate': context_corr[action_type]['success_rate'],
                'attempts': context_corr[action_type]['attempts']
            }

        # 3. Padrões relevantes
        for pattern in self.memory.get('patterns', []):
            if pattern.get('action') == action_type:
                evidence['patterns'].append(pattern)

        # Calcular predição
        prediction = self._calculate_prediction(evidence)

        # Verificar anti-padrões
        for anti in self.knowledge.get('anti_patterns', []):
            if anti.get('action') == action_type:
                prediction['warnings'].append(
                    f"Anti-padrão detectado: {anti.get('description')}"
                )
                prediction['recommended'] = False

        return prediction

    def _calculate_prediction(self, evidence: Dict[str, Any]) -> Dict[str, Any]:
        """Calcula predição baseada em evidências"""
        probabilities = []
        weights = []

        # Peso da efetividade geral
        if evidence['action_history']:
            prob = evidence['action_history']['success_rate']
            samples = evidence['action_history']['total_samples']
            weight = min(samples / 10, 1.0)  # Máximo peso com 10+ amostras
            probabilities.append(prob)
            weights.append(weight)

        # Peso do contexto específico (mais importante)
        if evidence['context_history']:
            prob = evidence['context_history']['success_rate']
            attempts = evidence['context_history']['attempts']
            weight = min(attempts / 5, 1.5)  # Contexto específico vale mais
            probabilities.append(prob)
            weights.append(weight)

        # Ajuste por padrões
        pattern_adjustment = 0
        for pattern in evidence.get('patterns', []):
            if pattern['type'] == 'consistent_failure':
                pattern_adjustment -= 0.2
            elif pattern['type'] == 'consistent_success':
                pattern_adjustment += 0.1
            elif pattern['type'] == 'degrading_action':
                pattern_adjustment -= 0.15

        # Calcular probabilidade ponderada
        if probabilities and weights:
            total_weight = sum(weights)
            weighted_prob = sum(p * w for p, w in zip(probabilities, weights)) / total_weight
            weighted_prob = max(0, min(1, weighted_prob + pattern_adjustment))
        else:
            weighted_prob = 0.5  # Sem dados, assume 50%

        # Calcular confiança
        total_samples = sum([
            evidence['action_history']['total_samples'] if evidence['action_history'] else 0,
            evidence['context_history']['attempts'] if evidence['context_history'] else 0
        ])
        confidence = min(total_samples / self.learning_config['min_samples_for_confidence'], 1.0)

        return {
            'success_probability': round(weighted_prob, 3),
            'confidence': round(confidence, 3),
            'total_evidence_samples': total_samples,
            'recommended': weighted_prob >= 0.6 and confidence >= 0.5,
            'warnings': [],
            'evidence_summary': {
                'has_action_history': evidence['action_history'] is not None,
                'has_context_history': evidence['context_history'] is not None,
                'pattern_count': len(evidence.get('patterns', []))
            }
        }

    def get_recommendations(
        self,
        issue_type: str,
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Obtém recomendações para um tipo de issue

        Returns:
            Lista de ações recomendadas ordenadas por probabilidade de sucesso
        """
        recommendations = []

        # Buscar issue conhecida
        known = self.knowledge.get('known_issues', {}).get(issue_type)
        if known:
            for solution in known.get('solutions', []):
                prediction = self.predict_outcome(
                    {'type': solution['action']},
                    context
                )
                recommendations.append({
                    'action': solution['action'],
                    'source': 'known_solution',
                    **prediction
                })

        # Buscar melhores práticas relacionadas
        for practice in self.knowledge.get('best_practices', []):
            if issue_type.lower() in practice.get('action', '').lower():
                prediction = self.predict_outcome(
                    {'type': practice['action']},
                    context
                )
                recommendations.append({
                    'action': practice['action'],
                    'source': 'best_practice',
                    **prediction
                })

        # Ordenar por probabilidade de sucesso
        recommendations.sort(
            key=lambda x: (x.get('success_probability', 0), x.get('confidence', 0)),
            reverse=True
        )

        return recommendations[:5]  # Top 5

    def learn_from_known_issue(
        self,
        issue_type: str,
        solution: Dict[str, Any],
        success: bool
    ):
        """Aprende sobre solução para issue conhecida"""
        if issue_type not in self.knowledge['known_issues']:
            self.knowledge['known_issues'][issue_type] = {
                'first_seen': datetime.now().isoformat(),
                'solutions': [],
                'attempts': 0
            }

        known = self.knowledge['known_issues'][issue_type]
        known['attempts'] += 1

        # Atualizar ou adicionar solução
        existing = [s for s in known['solutions'] if s.get('action') == solution.get('action')]
        if existing:
            sol = existing[0]
            sol['attempts'] = sol.get('attempts', 0) + 1
            if success:
                sol['successes'] = sol.get('successes', 0) + 1
            sol['success_rate'] = sol['successes'] / sol['attempts']
        else:
            known['solutions'].append({
                'action': solution.get('action'),
                'attempts': 1,
                'successes': 1 if success else 0,
                'success_rate': 1.0 if success else 0.0,
                'first_used': datetime.now().isoformat()
            })

        self._save_knowledge()

    def update_system_baseline(self, metrics: Dict[str, Any]):
        """Atualiza baseline do sistema"""
        baseline = self.knowledge.get('system_baseline', {})

        for metric, value in metrics.items():
            if metric not in baseline:
                baseline[metric] = {
                    'values': [],
                    'mean': value,
                    'std': 0,
                    'min': value,
                    'max': value
                }

            b = baseline[metric]
            b['values'].append(value)
            b['values'] = b['values'][-100:]  # Últimos 100 valores

            if len(b['values']) >= 2:
                b['mean'] = statistics.mean(b['values'])
                b['std'] = statistics.stdev(b['values'])
                b['min'] = min(b['values'])
                b['max'] = max(b['values'])

        self.knowledge['system_baseline'] = baseline
        self._save_knowledge()

    def get_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas da memória operacional"""
        meta = self.memory.get('metadata', {})

        success_rate = 0
        if meta.get('total_actions', 0) > 0:
            success_rate = meta['total_successes'] / meta['total_actions']

        return {
            'total_actions_recorded': meta.get('total_actions', 0),
            'total_successes': meta.get('total_successes', 0),
            'total_failures': meta.get('total_failures', 0),
            'overall_success_rate': round(success_rate, 3),
            'known_action_types': len(self.knowledge.get('action_effectiveness', {})),
            'known_contexts': len(self.knowledge.get('context_correlations', {})),
            'known_issues': len(self.knowledge.get('known_issues', {})),
            'best_practices_count': len(self.knowledge.get('best_practices', [])),
            'anti_patterns_count': len(self.knowledge.get('anti_patterns', [])),
            'detected_patterns': len(self.memory.get('patterns', [])),
            'memory_created': meta.get('created_at', 'unknown')
        }


if __name__ == '__main__':
    # Teste
    memory = OperationalMemory({})

    # Simular algumas ações
    test_action = {
        'type': 'clear_cache',
        'target': 'redis',
        'category': 'performance'
    }

    test_context = {
        'cpu_range': 'high',
        'memory_range': 'medium',
        'time_of_day': 'peak',
        'concurrent_issues': 2
    }

    # Registrar sucesso
    memory.record_action(test_action, test_context, {'success': True})
    memory.record_action(test_action, test_context, {'success': True})
    memory.record_action(test_action, test_context, {'success': False})
    memory.record_action(test_action, test_context, {'success': True})
    memory.record_action(test_action, test_context, {'success': True})

    # Prever resultado
    prediction = memory.predict_outcome(test_action, test_context)

    print("=== Memória Operacional ===\n")
    print("Predição para clear_cache:")
    print(json.dumps(prediction, indent=2))

    print("\n=== Estatísticas ===")
    print(json.dumps(memory.get_statistics(), indent=2))
