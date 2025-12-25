"""
Skill: Auto Healer
Corrige problemas automaticamente sem intervenção humana
"""

import os
import json
import subprocess
from typing import Dict, Any, List
from datetime import datetime


class AutoHealer:
    """Sistema de correção automática de problemas"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.fixes_applied = []
        self.fix_history_file = '/opt/conecta-plus/agents/system-monitor/state/fix_history.json'

        # Criar diretório de state se não existir
        os.makedirs(os.path.dirname(self.fix_history_file), exist_ok=True)

    def load_fix_history(self) -> List[Dict[str, Any]]:
        """Carrega histórico de correções"""
        try:
            if os.path.exists(self.fix_history_file):
                with open(self.fix_history_file) as f:
                    return json.load(f)
        except:
            pass
        return []

    def save_fix_history(self):
        """Salva histórico de correções"""
        try:
            history = self.load_fix_history()
            history.extend(self.fixes_applied)

            # Manter apenas últimas 100 correções
            history = history[-100:]

            with open(self.fix_history_file, 'w') as f:
                json.dump(history, f, indent=2)
        except Exception as e:
            print(f"Erro ao salvar histórico: {e}")

    def fix_container_stopped(self, container_name: str) -> Dict[str, Any]:
        """Corrige container parado"""
        result = {
            'problem': f'Container {container_name} parado',
            'action': f'Reiniciar container {container_name}',
            'timestamp': datetime.now().isoformat(),
            'success': False,
            'details': ''
        }

        try:
            # Verificar se está parado
            check = subprocess.run(
                ['docker', 'ps', '-a', '--filter', f'name={container_name}', '--format', '{{.Status}}'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if 'Exited' in check.stdout or 'Created' in check.stdout:
                # Tentar iniciar
                start = subprocess.run(
                    ['docker', 'start', container_name],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                if start.returncode == 0:
                    result['success'] = True
                    result['details'] = f'Container {container_name} reiniciado com sucesso'
                else:
                    result['details'] = f'Erro ao reiniciar: {start.stderr}'
            else:
                result['details'] = 'Container já está rodando'
                result['success'] = True

        except Exception as e:
            result['details'] = f'Erro: {str(e)}'

        return result

    def fix_disk_space(self) -> Dict[str, Any]:
        """Libera espaço em disco"""
        result = {
            'problem': 'Disco com pouco espaço',
            'action': 'Limpar logs antigos e cache',
            'timestamp': datetime.now().isoformat(),
            'success': False,
            'details': ''
        }

        try:
            freed_space = 0

            # 1. Limpar logs do Docker
            cleanup = subprocess.run(
                ['docker', 'system', 'prune', '-f', '--volumes'],
                capture_output=True,
                text=True,
                timeout=60
            )

            if cleanup.returncode == 0:
                # 2. Limpar logs antigos (> 30 dias)
                log_dirs = [
                    '/opt/conecta-plus/logs',
                    '/var/log/conecta-plus',
                    '/opt/conecta-plus/agents/*/logs'
                ]

                for log_dir in log_dirs:
                    if os.path.exists(log_dir):
                        subprocess.run(
                            f'find {log_dir} -name "*.log" -mtime +30 -delete',
                            shell=True,
                            timeout=30
                        )

                result['success'] = True
                result['details'] = f'Limpeza concluída. {cleanup.stdout}'
            else:
                result['details'] = f'Erro na limpeza: {cleanup.stderr}'

        except Exception as e:
            result['details'] = f'Erro: {str(e)}'

        return result

    def fix_high_memory_container(self, container_name: str) -> Dict[str, Any]:
        """Reinicia container com alto uso de memória"""
        result = {
            'problem': f'Container {container_name} com alto uso de memória',
            'action': f'Reiniciar {container_name}',
            'timestamp': datetime.now().isoformat(),
            'success': False,
            'details': ''
        }

        try:
            restart = subprocess.run(
                ['docker', 'restart', container_name],
                capture_output=True,
                text=True,
                timeout=30
            )

            if restart.returncode == 0:
                result['success'] = True
                result['details'] = f'Container {container_name} reiniciado'
            else:
                result['details'] = f'Erro ao reiniciar: {restart.stderr}'

        except Exception as e:
            result['details'] = f'Erro: {str(e)}'

        return result

    def fix_permissions(self, path: str, owner: str = 'root:root', mode: str = '755') -> Dict[str, Any]:
        """Corrige permissões de arquivos"""
        result = {
            'problem': f'Permissões incorretas em {path}',
            'action': f'Ajustar permissões para {mode}',
            'timestamp': datetime.now().isoformat(),
            'success': False,
            'details': ''
        }

        try:
            if os.path.exists(path):
                # Mudar permissões
                subprocess.run(['chmod', mode, path], timeout=5)

                # Mudar dono (se root)
                if os.geteuid() == 0:
                    subprocess.run(['chown', owner, path], timeout=5)

                result['success'] = True
                result['details'] = f'Permissões ajustadas para {mode}'
            else:
                result['details'] = f'Caminho {path} não existe'

        except Exception as e:
            result['details'] = f'Erro: {str(e)}'

        return result

    def fix_log_rotation(self, log_path: str) -> Dict[str, Any]:
        """Rotaciona logs grandes"""
        result = {
            'problem': f'Log muito grande: {log_path}',
            'action': 'Rotacionar log',
            'timestamp': datetime.now().isoformat(),
            'success': False,
            'details': ''
        }

        try:
            if os.path.exists(log_path):
                size_mb = os.path.getsize(log_path) / (1024 * 1024)

                if size_mb > 100:  # Se > 100MB
                    # Rotacionar
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    backup_path = f"{log_path}.{timestamp}"

                    os.rename(log_path, backup_path)

                    # Comprimir
                    subprocess.run(
                        ['gzip', backup_path],
                        timeout=60
                    )

                    result['success'] = True
                    result['details'] = f'Log rotacionado: {size_mb:.2f}MB → {backup_path}.gz'
                else:
                    result['details'] = f'Log pequeno ({size_mb:.2f}MB), rotação não necessária'
                    result['success'] = True

        except Exception as e:
            result['details'] = f'Erro: {str(e)}'

        return result

    def fix_missing_pip_package(self, package: str) -> Dict[str, Any]:
        """Instala pacote pip faltando"""
        result = {
            'problem': f'Missing pip package: {package}',
            'action': f'Install {package}',
            'timestamp': datetime.now().isoformat(),
            'success': False,
            'details': ''
        }

        try:
            install = subprocess.run(
                ['pip3', 'install', package],
                capture_output=True,
                text=True,
                timeout=120
            )

            if install.returncode == 0:
                result['success'] = True
                result['details'] = f'Package {package} installed successfully'
            else:
                result['details'] = f'Error installing: {install.stderr}'

        except Exception as e:
            result['details'] = f'Error: {str(e)}'

        return result

    def fix_outdated_npm_package(self, package: str) -> Dict[str, Any]:
        """Atualiza pacote npm desatualizado"""
        result = {
            'problem': f'Outdated npm package: {package}',
            'action': f'Update {package}',
            'timestamp': datetime.now().isoformat(),
            'success': False,
            'details': ''
        }

        try:
            frontend_dir = '/opt/conecta-plus/frontend'
            if os.path.exists(frontend_dir):
                update = subprocess.run(
                    ['npm', 'install', f'{package}@latest'],
                    capture_output=True,
                    text=True,
                    timeout=180,
                    cwd=frontend_dir
                )

                if update.returncode == 0:
                    result['success'] = True
                    result['details'] = f'Package {package} updated successfully'
                else:
                    result['details'] = f'Error updating: {update.stderr}'
            else:
                result['details'] = 'Frontend directory not found'

        except Exception as e:
            result['details'] = f'Error: {str(e)}'

        return result

    def fix_debug_code(self, file_path: str) -> Dict[str, Any]:
        """Remove console.log de código"""
        result = {
            'problem': f'Debug code in {file_path}',
            'action': 'Remove console.log statements',
            'timestamp': datetime.now().isoformat(),
            'success': False,
            'details': ''
        }

        try:
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    content = f.read()

                original_lines = content.count('\n')
                # Remover console.log mas manter comentários
                import re
                new_content = re.sub(r'^\s*console\.(log|debug|info)\(.*\);\s*$', '', content, flags=re.MULTILINE)

                if new_content != content:
                    with open(file_path, 'w') as f:
                        f.write(new_content)

                    removed = original_lines - new_content.count('\n')
                    result['success'] = True
                    result['details'] = f'Removed {removed} console.log statements'
                else:
                    result['details'] = 'No console.log found'
                    result['success'] = True
            else:
                result['details'] = 'File not found'

        except Exception as e:
            result['details'] = f'Error: {str(e)}'

        return result

    def fix_hardcoded_secret(self, file_path: str) -> Dict[str, Any]:
        """Adiciona comentário alertando sobre secret hardcoded"""
        result = {
            'problem': f'Hardcoded secret in {file_path}',
            'action': 'Add warning comment',
            'timestamp': datetime.now().isoformat(),
            'success': False,
            'details': ''
        }

        try:
            if os.path.exists(file_path):
                # Apenas adicionar comentário de alerta
                with open(file_path, 'r') as f:
                    lines = f.readlines()

                warning = "# WARNING: This file may contain hardcoded secrets. Move to environment variables!\n"
                if warning not in lines[0]:
                    lines.insert(0, warning)

                    with open(file_path, 'w') as f:
                        f.writelines(lines)

                    result['success'] = True
                    result['details'] = 'Warning comment added. Manual review required.'
                else:
                    result['details'] = 'Warning already present'
                    result['success'] = True
            else:
                result['details'] = 'File not found'

        except Exception as e:
            result['details'] = f'Error: {str(e)}'

        return result

    def auto_heal(self, issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aplica correções automáticas para problemas detectados"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'total_issues': len(issues),
            'fixes_attempted': 0,
            'fixes_successful': 0,
            'fixes_failed': 0,
            'fixes': []
        }

        for issue in issues:
            issue_type = issue.get('type', '')
            severity = issue.get('severity', 'low')
            category = issue.get('category', '')

            fix_result = None

            # ========== INFRAESTRUTURA ==========
            # Container parado
            if 'container' in issue_type.lower() and 'stopped' in issue_type.lower():
                container = issue.get('container_name', '')
                if container:
                    fix_result = self.fix_container_stopped(container)

            # Disco cheio
            elif 'disk' in issue_type.lower() and 'space' in issue_type.lower():
                fix_result = self.fix_disk_space()

            # Alto uso de memória
            elif 'memory' in issue_type.lower() and 'high' in issue_type.lower():
                container = issue.get('container_name', '')
                if container:
                    fix_result = self.fix_high_memory_container(container)

            # Log muito grande
            elif 'log' in issue_type.lower() and 'large' in issue_type.lower():
                log_path = issue.get('path', '')
                if log_path:
                    fix_result = self.fix_log_rotation(log_path)

            # ========== DEPENDÊNCIAS ==========
            # Pacote pip faltando
            elif issue_type == 'missing_pip_package':
                package = issue.get('package', '')
                if package and severity in ['high', 'critical']:
                    fix_result = self.fix_missing_pip_package(package)

            # Pacote npm desatualizado (inclui low para manter atualizado)
            elif issue_type == 'outdated_npm' and severity in ['low', 'medium', 'high']:
                package = issue.get('package', '')
                if package:
                    fix_result = self.fix_outdated_npm_package(package)

            # ========== CODE QUALITY ==========
            # Debug code (console.log)
            elif issue_type == 'debug_code':
                file_path = issue.get('file', '')
                if file_path:
                    fix_result = self.fix_debug_code(file_path)

            # ========== SEGURANÇA ==========
            # Hardcoded secret (crítico - apenas alertar)
            elif issue_type == 'hardcoded_secret' and severity == 'critical':
                location = issue.get('location', '')
                if location:
                    fix_result = self.fix_hardcoded_secret(location)

            if fix_result:
                results['fixes_attempted'] += 1
                results['fixes'].append(fix_result)
                self.fixes_applied.append(fix_result)

                if fix_result['success']:
                    results['fixes_successful'] += 1
                else:
                    results['fixes_failed'] += 1

        # Salvar histórico
        if self.fixes_applied:
            self.save_fix_history()

        return results

    def get_fix_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas de correções"""
        history = self.load_fix_history()

        total = len(history)
        successful = sum(1 for fix in history if fix.get('success', False))
        failed = total - successful

        return {
            'total_fixes': total,
            'successful': successful,
            'failed': failed,
            'success_rate': f"{(successful/total*100):.1f}%" if total > 0 else "N/A",
            'recent_fixes': history[-10:]  # Últimas 10
        }


if __name__ == '__main__':
    healer = AutoHealer({})

    # Exemplo de correção
    test_issues = [
        {
            'type': 'container_stopped',
            'severity': 'high',
            'container_name': 'conecta-frontend-fixed'
        }
    ]

    results = healer.auto_heal(test_issues)
    print(json.dumps(results, indent=2))
