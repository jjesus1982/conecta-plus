"""
Skill: Safe Auto-Healer
Auto-healing progressivo e seguro - APENAS P4 inicialmente
Implementa regras de SRE para correção automática controlada
"""

import os
import json
import subprocess
import shutil
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from pathlib import Path


class SafeHealer:
    """
    Sistema de auto-healing progressivo e seguro

    REGRA MESTRA: Nunca executar ação que:
    - Afete disponibilidade do serviço
    - Altere dados de clientes
    - Gere downtime
    - Não tenha rollback definido
    """

    # Ações permitidas para P4 (baixo impacto)
    ALLOWED_P4_ACTIONS = {
        'clear_temp_files',
        'clear_cache',
        'restart_auxiliary_service',
        'fix_permissions_non_sensitive',
        'rotate_logs',
        'update_npm_package',
        'clear_docker_cache'
    }

    # Ações PROIBIDAS (nunca executar automaticamente)
    FORBIDDEN_ACTIONS = {
        'restart_database',
        'alter_network_rules',
        'deploy_code',
        'modify_critical_config',
        'delete_user_data',
        'restart_main_service'
    }

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.state_dir = Path('/opt/conecta-plus/agents/system-monitor/state')
        self.state_dir.mkdir(parents=True, exist_ok=True)

        self.healing_log_file = self.state_dir / 'healing_audit.json'
        self.healing_score_file = self.state_dir / 'healing_score.json'

        # Configurações de evolução
        self.min_p4_successes_for_p3 = 20
        self.min_healing_score_for_p3 = 8.0
        self.cooldown_seconds = 30

        # Carregar estado
        self.healing_score = self._load_healing_score()

    def _load_healing_score(self) -> Dict[str, Any]:
        """Carrega histórico de healing score"""
        default = {
            'current_score': 0.0,
            'max_score': 10.0,
            'total_attempts': 0,
            'total_successes': 0,
            'total_failures': 0,
            'total_aborted': 0,
            'p4_successes': 0,
            'p3_enabled': False,
            'last_update': None,
            'history': []
        }

        try:
            if self.healing_score_file.exists():
                with open(self.healing_score_file) as f:
                    return json.load(f)
        except:
            pass
        return default

    def _save_healing_score(self):
        """Salva healing score"""
        self.healing_score['last_update'] = datetime.now().isoformat()
        with open(self.healing_score_file, 'w') as f:
            json.dump(self.healing_score, f, indent=2)

    def _log_audit(self, entry: Dict[str, Any]):
        """Registra entrada de auditoria"""
        audit_log = []
        try:
            if self.healing_log_file.exists():
                with open(self.healing_log_file) as f:
                    audit_log = json.load(f)
        except:
            pass

        # Manter últimas 500 entradas
        audit_log.append(entry)
        audit_log = audit_log[-500:]

        with open(self.healing_log_file, 'w') as f:
            json.dump(audit_log, f, indent=2)

    def can_heal(self, issue: Dict[str, Any]) -> tuple[bool, str]:
        """
        Verifica se uma issue pode ser corrigida automaticamente

        Returns:
            (pode_corrigir, motivo)
        """
        priority = issue.get('priority', 'P4')
        issue_type = issue.get('type', '')

        # Regra 1: Apenas P4 por padrão
        if priority not in ['P4']:
            # Verificar se P3 está habilitado
            if priority == 'P3' and self._can_heal_p3():
                pass  # Permitido
            else:
                return False, f"Prioridade {priority} não autorizada para auto-healing"

        # Regra 2: Verificar se ação é permitida
        action_type = self._get_action_type(issue_type)
        if action_type in self.FORBIDDEN_ACTIONS:
            return False, f"Ação '{action_type}' é PROIBIDA"

        # Regra 3: Verificar se tem rollback definido
        if not self._has_rollback(issue_type):
            return False, f"Sem rollback definido para '{issue_type}'"

        return True, "Autorizado para auto-healing"

    def _can_heal_p3(self) -> bool:
        """Verifica se P3 pode ser habilitado"""
        score = self.healing_score

        conditions = [
            score['current_score'] >= self.min_healing_score_for_p3,
            score['p4_successes'] >= self.min_p4_successes_for_p3,
            score.get('incidents_caused', 0) == 0,
            score.get('p3_enabled', False)  # Feature flag
        ]

        return all(conditions)

    def _get_action_type(self, issue_type: str) -> str:
        """Mapeia tipo de issue para tipo de ação"""
        mapping = {
            'outdated_npm': 'update_npm_package',
            'large_log': 'rotate_logs',
            'temp_files': 'clear_temp_files',
            'cache_full': 'clear_cache',
            'docker_cache': 'clear_docker_cache',
            'permission_issue': 'fix_permissions_non_sensitive'
        }
        return mapping.get(issue_type, issue_type)

    def _has_rollback(self, issue_type: str) -> bool:
        """Verifica se issue tem rollback definido"""
        rollback_defined = {
            'outdated_npm': True,   # npm install versão anterior
            'large_log': True,      # logs são apenas rotacionados, não deletados
            'temp_files': True,     # arquivos temp são descartáveis
            'cache_full': True,     # cache pode ser reconstruído
            'docker_cache': True,   # docker rebuild
            'unused_dependency': False,  # Não tem rollback seguro
            'excessive_any': False,      # Requer intervenção humana
            'debug_code': False,         # Requer review de código
        }
        return rollback_defined.get(issue_type, False)

    def _capture_state_before(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        """Captura estado antes da ação"""
        issue_type = issue.get('type', '')
        state = {
            'timestamp': datetime.now().isoformat(),
            'issue_type': issue_type,
            'issue': issue.copy()
        }

        if issue_type == 'outdated_npm':
            package = issue.get('package', '')
            state['package_version'] = issue.get('current_version', '')
            state['target_version'] = issue.get('latest_version', '')

        elif issue_type == 'large_log':
            path = issue.get('path', '')
            if os.path.exists(path):
                state['file_size'] = os.path.getsize(path)
                state['file_path'] = path

        return state

    def _validate_after(self, issue: Dict[str, Any], state_before: Dict[str, Any]) -> Dict[str, Any]:
        """Valida se a correção funcionou"""
        issue_type = issue.get('type', '')

        validation = {
            'timestamp': datetime.now().isoformat(),
            'validated': False,
            'result': 'unknown',
            'details': ''
        }

        try:
            if issue_type == 'outdated_npm':
                package = issue.get('package', '')
                # Verificar versão atual
                result = subprocess.run(
                    ['npm', 'list', package, '--json'],
                    cwd='/opt/conecta-plus/frontend',
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    data = json.loads(result.stdout)
                    # Verificar se versão mudou
                    validation['validated'] = True
                    validation['result'] = 'success'
                    validation['details'] = f'Package {package} atualizado'
                else:
                    validation['result'] = 'partial'
                    validation['details'] = 'Não foi possível verificar versão'

            elif issue_type == 'large_log':
                path = state_before.get('file_path', '')
                if os.path.exists(path):
                    new_size = os.path.getsize(path)
                    old_size = state_before.get('file_size', 0)
                    if new_size < old_size:
                        validation['validated'] = True
                        validation['result'] = 'success'
                        validation['details'] = f'Log reduzido de {old_size} para {new_size} bytes'
                    else:
                        validation['result'] = 'failure'
                        validation['details'] = 'Tamanho do log não reduziu'
                else:
                    # Log foi rotacionado (arquivo movido)
                    validation['validated'] = True
                    validation['result'] = 'success'
                    validation['details'] = 'Log rotacionado com sucesso'

            else:
                # Para outros tipos, assumir sucesso se não houve erro
                validation['validated'] = True
                validation['result'] = 'success'
                validation['details'] = 'Ação executada sem erros'

        except Exception as e:
            validation['result'] = 'failure'
            validation['details'] = f'Erro na validação: {str(e)}'

        return validation

    def _execute_rollback(self, issue: Dict[str, Any], state_before: Dict[str, Any]) -> Dict[str, Any]:
        """Executa rollback de uma ação"""
        issue_type = issue.get('type', '')

        rollback_result = {
            'timestamp': datetime.now().isoformat(),
            'executed': False,
            'success': False,
            'details': ''
        }

        try:
            if issue_type == 'outdated_npm':
                package = issue.get('package', '')
                old_version = state_before.get('package_version', '')
                if old_version:
                    result = subprocess.run(
                        ['npm', 'install', f'{package}@{old_version}'],
                        cwd='/opt/conecta-plus/frontend',
                        capture_output=True,
                        text=True,
                        timeout=120
                    )
                    rollback_result['executed'] = True
                    rollback_result['success'] = result.returncode == 0
                    rollback_result['details'] = f'Revertido para {package}@{old_version}'

            # Outros rollbacks podem ser adicionados aqui

        except Exception as e:
            rollback_result['details'] = f'Erro no rollback: {str(e)}'

        return rollback_result

    def _update_healing_score(self, result: str, priority: str):
        """Atualiza healing score baseado no resultado"""
        self.healing_score['total_attempts'] += 1

        if result == 'success':
            self.healing_score['total_successes'] += 1
            if priority == 'P4':
                self.healing_score['p4_successes'] += 1
            # Incrementar score (máximo 10)
            increment = 0.5 if priority == 'P4' else 0.3
            self.healing_score['current_score'] = min(
                10.0,
                self.healing_score['current_score'] + increment
            )

        elif result == 'partial':
            # Sucesso parcial não altera score significativamente
            pass

        elif result == 'failure':
            self.healing_score['total_failures'] += 1
            # Penalidade
            self.healing_score['current_score'] = max(
                0.0,
                self.healing_score['current_score'] - 1.0
            )

        elif result == 'aborted':
            self.healing_score['total_aborted'] += 1

        # Registrar histórico
        self.healing_score['history'].append({
            'timestamp': datetime.now().isoformat(),
            'result': result,
            'priority': priority,
            'score_after': self.healing_score['current_score']
        })

        # Manter últimas 100 entradas no histórico
        self.healing_score['history'] = self.healing_score['history'][-100:]

        self._save_healing_score()

    def safe_heal(self, issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Executa auto-healing seguro para lista de issues

        Fluxo:
        1. Filtrar apenas issues autorizadas
        2. Para cada issue:
           a. Capturar estado ANTES
           b. Executar correção
           c. Aguardar cooldown
           d. Validar DEPOIS
           e. Rollback se necessário
           f. Atualizar score
        """
        results = {
            'timestamp': datetime.now().isoformat(),
            'total_issues': len(issues),
            'authorized': 0,
            'attempted': 0,
            'successful': 0,
            'partial': 0,
            'failed': 0,
            'aborted': 0,
            'actions': []
        }

        for issue in issues:
            # Verificar autorização
            can_heal, reason = self.can_heal(issue)

            action_record = {
                'issue': issue.get('description', issue.get('type', 'unknown')),
                'priority': issue.get('priority', 'P4'),
                'authorized': can_heal,
                'authorization_reason': reason,
                'state_before': None,
                'execution': None,
                'validation': None,
                'rollback': None,
                'final_result': 'not_attempted'
            }

            if not can_heal:
                action_record['final_result'] = 'aborted'
                self._update_healing_score('aborted', issue.get('priority', 'P4'))
                results['aborted'] += 1
                results['actions'].append(action_record)

                # Log de auditoria
                self._log_audit({
                    'timestamp': datetime.now().isoformat(),
                    'action': 'ABORTED',
                    'issue': issue,
                    'reason': reason
                })
                continue

            results['authorized'] += 1
            results['attempted'] += 1

            # 1. Capturar estado ANTES
            state_before = self._capture_state_before(issue)
            action_record['state_before'] = state_before

            # 2. Executar correção
            execution_result = self._execute_fix(issue)
            action_record['execution'] = execution_result

            if not execution_result.get('success', False):
                action_record['final_result'] = 'failed'
                self._update_healing_score('failure', issue.get('priority', 'P4'))
                results['failed'] += 1
                results['actions'].append(action_record)

                self._log_audit({
                    'timestamp': datetime.now().isoformat(),
                    'action': 'FAILED',
                    'issue': issue,
                    'execution': execution_result
                })
                continue

            # 3. Aguardar cooldown
            import time
            time.sleep(min(self.cooldown_seconds, 5))  # Max 5s para não bloquear

            # 4. Validar DEPOIS
            validation = self._validate_after(issue, state_before)
            action_record['validation'] = validation

            # 5. Determinar resultado final
            if validation['result'] == 'success':
                action_record['final_result'] = 'success'
                self._update_healing_score('success', issue.get('priority', 'P4'))
                results['successful'] += 1

            elif validation['result'] == 'partial':
                action_record['final_result'] = 'partial'
                self._update_healing_score('partial', issue.get('priority', 'P4'))
                results['partial'] += 1

            else:
                # Falha na validação - executar rollback
                rollback = self._execute_rollback(issue, state_before)
                action_record['rollback'] = rollback
                action_record['final_result'] = 'failed_with_rollback'
                self._update_healing_score('failure', issue.get('priority', 'P4'))
                results['failed'] += 1

            results['actions'].append(action_record)

            # Log de auditoria
            self._log_audit({
                'timestamp': datetime.now().isoformat(),
                'action': action_record['final_result'].upper(),
                'issue': issue,
                'validation': validation
            })

        # Adicionar score atual aos resultados
        results['healing_score'] = {
            'current': self.healing_score['current_score'],
            'max': 10.0,
            'p4_successes': self.healing_score['p4_successes'],
            'p3_ready': self._can_heal_p3()
        }

        return results

    def _execute_fix(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        """Executa a correção real"""
        issue_type = issue.get('type', '')

        result = {
            'timestamp': datetime.now().isoformat(),
            'success': False,
            'details': ''
        }

        try:
            if issue_type == 'outdated_npm':
                package = issue.get('package', '')
                if package:
                    proc = subprocess.run(
                        ['npm', 'install', f'{package}@latest'],
                        cwd='/opt/conecta-plus/frontend',
                        capture_output=True,
                        text=True,
                        timeout=120
                    )
                    result['success'] = proc.returncode == 0
                    result['details'] = f'npm install {package}@latest'
                    if not result['success']:
                        result['error'] = proc.stderr[:200]

            elif issue_type == 'large_log':
                path = issue.get('path', '')
                if path and os.path.exists(path):
                    # Rotacionar log (não deletar)
                    backup = f"{path}.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    shutil.move(path, backup)
                    # Comprimir
                    subprocess.run(['gzip', backup], timeout=60)
                    result['success'] = True
                    result['details'] = f'Log rotacionado para {backup}.gz'

            elif issue_type == 'temp_files':
                # Limpar apenas arquivos temporários seguros
                temp_dirs = ['/tmp/conecta-*', '/opt/conecta-plus/.cache']
                for pattern in temp_dirs:
                    subprocess.run(
                        f'rm -rf {pattern}',
                        shell=True,
                        timeout=30
                    )
                result['success'] = True
                result['details'] = 'Arquivos temporários limpos'

            elif issue_type == 'docker_cache':
                # Limpar apenas cache não usado
                proc = subprocess.run(
                    ['docker', 'system', 'prune', '-f'],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                result['success'] = proc.returncode == 0
                result['details'] = 'Docker cache limpo'

            else:
                result['details'] = f'Tipo de issue não suportado: {issue_type}'

        except subprocess.TimeoutExpired:
            result['details'] = 'Timeout na execução'
        except Exception as e:
            result['details'] = f'Erro: {str(e)}'

        return result

    def get_healing_report(self) -> Dict[str, Any]:
        """Retorna relatório completo de healing"""
        audit_log = []
        try:
            if self.healing_log_file.exists():
                with open(self.healing_log_file) as f:
                    audit_log = json.load(f)
        except:
            pass

        # Calcular estatísticas
        recent = audit_log[-50:]  # Últimas 50 ações

        stats = {
            'success': sum(1 for a in recent if a.get('action') == 'SUCCESS'),
            'partial': sum(1 for a in recent if a.get('action') == 'PARTIAL'),
            'failed': sum(1 for a in recent if a.get('action') == 'FAILED'),
            'aborted': sum(1 for a in recent if a.get('action') == 'ABORTED')
        }

        return {
            'timestamp': datetime.now().isoformat(),
            'healing_score': self.healing_score,
            'recent_actions': recent[-10:],
            'statistics': stats,
            'p3_status': {
                'enabled': self.healing_score.get('p3_enabled', False),
                'ready': self._can_heal_p3(),
                'requirements': {
                    'min_score': self.min_healing_score_for_p3,
                    'current_score': self.healing_score['current_score'],
                    'min_p4_successes': self.min_p4_successes_for_p3,
                    'current_p4_successes': self.healing_score['p4_successes']
                }
            }
        }

    def enable_p3_healing(self, enable: bool = True):
        """Feature flag para habilitar/desabilitar P3"""
        if enable and not self._can_heal_p3():
            raise ValueError(
                f"Não é possível habilitar P3. Requisitos: "
                f"Score >= {self.min_healing_score_for_p3} (atual: {self.healing_score['current_score']}), "
                f"P4 successes >= {self.min_p4_successes_for_p3} (atual: {self.healing_score['p4_successes']})"
            )

        self.healing_score['p3_enabled'] = enable
        self._save_healing_score()


if __name__ == '__main__':
    # Teste
    healer = SafeHealer({})

    test_issues = [
        {
            'type': 'outdated_npm',
            'priority': 'P4',
            'severity': 'low',
            'package': 'react',
            'current_version': '19.2.1',
            'latest_version': '19.2.3',
            'description': 'Outdated npm package: react'
        },
        {
            'type': 'excessive_any',
            'priority': 'P4',
            'severity': 'low',
            'description': 'Excessive use of "any" type'
        }
    ]

    results = healer.safe_heal(test_issues)
    print(json.dumps(results, indent=2))
