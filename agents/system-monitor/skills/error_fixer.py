"""
Skill: Error Fixer
Corrige automaticamente erros comuns do sistema
"""

import subprocess
import time
import os
import signal
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json


class ErrorFixer:
    """Corrige automaticamente erros detectados no sistema"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.fix_history = []
        self.cooldown_tracker = {}
        self.max_attempts = config.get('auto_fixes', {}).get('max_attempts', 3)
        self.cooldown = config.get('auto_fixes', {}).get('cooldown', 300)

    def can_fix(self, error_type: str) -> bool:
        """Verifica se pode tentar corrigir (respeita cooldown)"""
        if error_type not in self.cooldown_tracker:
            return True

        last_fix = self.cooldown_tracker[error_type]
        if datetime.now() - last_fix['timestamp'] > timedelta(seconds=self.cooldown):
            return True

        if last_fix['attempts'] < self.max_attempts:
            return True

        return False

    def record_fix_attempt(self, error_type: str, success: bool, details: Dict[str, Any]):
        """Registra tentativa de correção"""
        if error_type not in self.cooldown_tracker:
            self.cooldown_tracker[error_type] = {
                'timestamp': datetime.now(),
                'attempts': 0,
                'successes': 0,
                'failures': 0
            }

        tracker = self.cooldown_tracker[error_type]
        tracker['attempts'] += 1
        tracker['timestamp'] = datetime.now()

        if success:
            tracker['successes'] += 1
        else:
            tracker['failures'] += 1

        # Registrar no histórico
        self.fix_history.append({
            'timestamp': datetime.now().isoformat(),
            'error_type': error_type,
            'success': success,
            'details': details
        })

    def fix_error(self, error: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tenta corrigir um erro automaticamente

        Args:
            error: Dicionário com informações do erro

        Returns:
            Resultado da correção
        """
        error_type = error.get('type', 'unknown')
        error_message = error.get('message', '')

        if not self.can_fix(error_type):
            return {
                'success': False,
                'error_type': error_type,
                'reason': 'Cooldown active or max attempts reached',
                'cooldown_until': (
                    self.cooldown_tracker[error_type]['timestamp'] +
                    timedelta(seconds=self.cooldown)
                ).isoformat()
            }

        # Determinar fix apropriado
        fix_result = None

        if error_type == 'network':
            fix_result = self._fix_network_error(error)
        elif error_type == 'timeout':
            fix_result = self._fix_timeout_error(error)
        elif error_type == 'lock':
            fix_result = self._fix_lock_error(error)
        elif error_type == 'dependency':
            fix_result = self._fix_dependency_error(error)
        elif error_type == 'disk':
            fix_result = self._fix_disk_error(error)
        elif error_type == 'memory':
            fix_result = self._fix_memory_error(error)
        elif 'port' in error_message.lower():
            fix_result = self._fix_port_conflict(error)
        else:
            fix_result = {
                'success': False,
                'reason': f'No automatic fix available for error type: {error_type}'
            }

        # Registrar tentativa
        self.record_fix_attempt(error_type, fix_result.get('success', False), fix_result)

        return fix_result

    def _fix_network_error(self, error: Dict[str, Any]) -> Dict[str, Any]:
        """Corrige erros de rede (ECONNRESET, socket hang up)"""
        try:
            # Verificar se é erro do Next.js proxy
            if 'next' in error['message'].lower():
                # Já criamos o proxy robusto, verificar se está ativo
                proxy_file = '/opt/conecta-plus/frontend/src/app/api/[[...proxy]]/route.ts'

                if os.path.exists(proxy_file):
                    # Proxy já existe, reiniciar Next.js
                    result = self._restart_nextjs()
                    return {
                        'success': result['success'],
                        'action': 'restart_nextjs',
                        'details': result
                    }
                else:
                    return {
                        'success': False,
                        'reason': 'Proxy route not found',
                        'recommendation': 'Create robust proxy route handler'
                    }

            # Para outros erros de rede, tentar restart do serviço
            return {
                'success': True,
                'action': 'monitor',
                'details': 'Network error logged for monitoring'
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _fix_timeout_error(self, error: Dict[str, Any]) -> Dict[str, Any]:
        """Corrige erros de timeout"""
        # Timeout geralmente indica API lenta, verificar processos
        try:
            # Verificar uso de CPU/memória da API
            result = subprocess.run(
                ['ps', 'aux'],
                capture_output=True,
                text=True
            )

            # Procurar processos da API com alto uso
            high_cpu_processes = []
            for line in result.stdout.splitlines():
                if 'uvicorn' in line or 'python' in line:
                    parts = line.split()
                    cpu = float(parts[2])
                    if cpu > 50:
                        high_cpu_processes.append({
                            'pid': parts[1],
                            'cpu': cpu,
                            'command': ' '.join(parts[10:])
                        })

            if high_cpu_processes:
                return {
                    'success': True,
                    'action': 'monitor',
                    'high_cpu_processes': high_cpu_processes,
                    'recommendation': 'Consider restarting high CPU processes'
                }

            return {
                'success': True,
                'action': 'logged',
                'details': 'Timeout logged for analysis'
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _fix_lock_error(self, error: Dict[str, Any]) -> Dict[str, Any]:
        """Corrige erros de lock file"""
        try:
            # Detectar qual lock (Next.js, npm, etc)
            if 'next' in error['message'].lower():
                lock_file = '/opt/conecta-plus/frontend/.next/dev/lock'

                if os.path.exists(lock_file):
                    os.remove(lock_file)
                    return {
                        'success': True,
                        'action': 'removed_lock',
                        'file': lock_file
                    }

            return {
                'success': False,
                'reason': 'Lock file not found or unknown lock type'
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _fix_dependency_error(self, error: Dict[str, Any]) -> Dict[str, Any]:
        """Corrige erros de dependências faltando"""
        try:
            # Detectar se é npm ou pip
            if 'node' in error['message'].lower() or 'module' in error['message'].lower():
                # Executar npm install
                result = subprocess.run(
                    ['npm', 'install'],
                    cwd='/opt/conecta-plus/frontend',
                    capture_output=True,
                    text=True,
                    timeout=300
                )

                return {
                    'success': result.returncode == 0,
                    'action': 'npm_install',
                    'output': result.stdout[-500:] if result.stdout else '',
                    'error': result.stderr[-500:] if result.stderr else ''
                }

            elif 'python' in error['message'].lower() or 'import' in error['message'].lower():
                # Executar pip install
                result = subprocess.run(
                    ['pip3', 'install', '-r', 'requirements.txt'],
                    cwd='/opt/conecta-plus/backend',
                    capture_output=True,
                    text=True,
                    timeout=300
                )

                return {
                    'success': result.returncode == 0,
                    'action': 'pip_install',
                    'output': result.stdout[-500:] if result.stdout else '',
                    'error': result.stderr[-500:] if result.stderr else ''
                }

            return {
                'success': False,
                'reason': 'Unknown dependency type'
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _fix_disk_error(self, error: Dict[str, Any]) -> Dict[str, Any]:
        """Corrige erros de disco cheio"""
        try:
            # Limpar arquivos temporários
            cleaned = []

            # Limpar logs antigos
            log_dirs = [
                '/opt/conecta-plus/frontend/.next',
                '/tmp',
                '/var/log/nginx'
            ]

            for log_dir in log_dirs:
                if os.path.exists(log_dir):
                    # Remover arquivos .log mais antigos que 7 dias
                    result = subprocess.run(
                        ['find', log_dir, '-name', '*.log', '-mtime', '+7', '-delete'],
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0:
                        cleaned.append(log_dir)

            return {
                'success': True,
                'action': 'cleaned_old_logs',
                'cleaned_dirs': cleaned
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _fix_memory_error(self, error: Dict[str, Any]) -> Dict[str, Any]:
        """Corrige erros de memória"""
        try:
            # Identificar processos com alto uso de memória
            result = subprocess.run(
                ['ps', 'aux', '--sort', '-rss'],
                capture_output=True,
                text=True
            )

            high_mem_processes = []
            for line in result.stdout.splitlines()[1:11]:  # Top 10
                parts = line.split()
                high_mem_processes.append({
                    'pid': parts[1],
                    'memory_mb': int(parts[5]) // 1024,
                    'command': ' '.join(parts[10:])
                })

            return {
                'success': True,
                'action': 'identified_high_memory',
                'processes': high_mem_processes,
                'recommendation': 'Review and optimize memory-intensive processes'
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _fix_port_conflict(self, error: Dict[str, Any]) -> Dict[str, Any]:
        """Corrige conflitos de porta"""
        try:
            # Extrair número da porta da mensagem
            import re
            port_match = re.search(r'port\s+(\d+)', error['message'], re.IGNORECASE)

            if not port_match:
                return {
                    'success': False,
                    'reason': 'Could not extract port number'
                }

            port = port_match.group(1)

            # Encontrar processo usando a porta
            result = subprocess.run(
                ['lsof', '-i', f':{port}', '-t'],
                capture_output=True,
                text=True
            )

            if result.returncode == 0 and result.stdout.strip():
                pids = result.stdout.strip().split('\n')

                # Verificar se é Next.js (pode matar)
                for pid in pids:
                    ps_result = subprocess.run(
                        ['ps', '-p', pid, '-o', 'comm='],
                        capture_output=True,
                        text=True
                    )

                    if 'node' in ps_result.stdout or 'next' in ps_result.stdout:
                        # Matar processo
                        os.kill(int(pid), signal.SIGKILL)
                        time.sleep(1)

                        return {
                            'success': True,
                            'action': 'killed_process',
                            'port': port,
                            'pid': pid
                        }

            return {
                'success': False,
                'reason': f'No process found on port {port} or unable to kill'
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _restart_nextjs(self) -> Dict[str, Any]:
        """Reinicia Next.js dev server"""
        try:
            # Matar processos Next.js
            subprocess.run(['pkill', '-9', '-f', 'next'], check=False)
            time.sleep(2)

            # Remover lock
            lock_file = '/opt/conecta-plus/frontend/.next/dev/lock'
            if os.path.exists(lock_file):
                os.remove(lock_file)

            # Iniciar novamente
            subprocess.Popen(
                ['nohup', 'npm', 'run', 'dev'],
                cwd='/opt/conecta-plus/frontend',
                stdout=open('/tmp/nextjs-debug.log', 'w'),
                stderr=subprocess.STDOUT,
                preexec_fn=os.setpgrp
            )

            # Esperar inicializar
            time.sleep(5)

            return {
                'success': True,
                'action': 'restarted',
                'service': 'next-server'
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def get_fix_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas de correções"""
        total_fixes = len(self.fix_history)
        successful_fixes = sum(1 for fix in self.fix_history if fix['success'])

        error_type_stats = {}
        for fix in self.fix_history:
            error_type = fix['error_type']
            if error_type not in error_type_stats:
                error_type_stats[error_type] = {
                    'total': 0,
                    'successful': 0,
                    'failed': 0
                }

            error_type_stats[error_type]['total'] += 1
            if fix['success']:
                error_type_stats[error_type]['successful'] += 1
            else:
                error_type_stats[error_type]['failed'] += 1

        return {
            'total_fixes': total_fixes,
            'successful_fixes': successful_fixes,
            'failed_fixes': total_fixes - successful_fixes,
            'success_rate': (successful_fixes / total_fixes * 100) if total_fixes > 0 else 0,
            'by_error_type': error_type_stats,
            'recent_fixes': self.fix_history[-10:]
        }


if __name__ == '__main__':
    # Teste
    import yaml

    with open('/opt/conecta-plus/agents/system-monitor/config.yaml') as f:
        config = yaml.safe_load(f)

    fixer = ErrorFixer(config)

    # Testar correção de lock
    test_error = {
        'type': 'lock',
        'message': 'Unable to acquire lock at /opt/conecta-plus/frontend/.next/dev/lock'
    }

    result = fixer.fix_error(test_error)
    print(json.dumps(result, indent=2))
