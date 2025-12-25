"""
Skill: Gap Detector
Detecta gaps, problemas potenciais e oportunidades de melhoria no sistema
"""

import os
import json
import subprocess
from typing import Dict, Any, List
from datetime import datetime
import re


class GapDetector:
    """Detecta gaps e oportunidades de melhoria no sistema"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.detected_gaps = []

    def detect_all_gaps(self) -> Dict[str, Any]:
        """
        Executa todas as verificações de gaps configuradas

        Returns:
            Dicionário com todos os gaps detectados
        """
        results = {
            'timestamp': datetime.now().isoformat(),
            'gaps': [],
            'total_gaps': 0,
            'critical_gaps': 0,
            'by_category': {}
        }

        gap_checks = self.config.get('gap_detection', {}).get('checks', [])

        for check in gap_checks:
            check_type = check['type']
            check_result = None

            if check_type == 'missing_dependencies':
                check_result = self._check_missing_dependencies()
            elif check_type == 'outdated_packages':
                check_result = self._check_outdated_packages()
            elif check_type == 'security_vulnerabilities':
                check_result = self._check_security_vulnerabilities()
            elif check_type == 'performance_bottlenecks':
                check_result = self._check_performance_bottlenecks()
            elif check_type == 'code_quality':
                check_result = self._check_code_quality()
            elif check_type == 'unused_code':
                check_result = self._check_unused_code()

            if check_result and check_result.get('gaps'):
                results['gaps'].extend(check_result['gaps'])

        # Calcular estatísticas
        results['total_gaps'] = len(results['gaps'])
        results['critical_gaps'] = sum(
            1 for gap in results['gaps']
            if gap.get('severity') == 'critical'
        )

        # Agrupar por categoria
        for gap in results['gaps']:
            category = gap.get('category', 'unknown')
            if category not in results['by_category']:
                results['by_category'][category] = []
            results['by_category'][category].append(gap)

        return results

    def _check_missing_dependencies(self) -> Dict[str, Any]:
        """Verifica dependências faltando"""
        gaps = []

        # Verificar package.json vs node_modules
        try:
            package_json_path = '/opt/conecta-plus/frontend/package.json'
            if os.path.exists(package_json_path):
                with open(package_json_path) as f:
                    package_data = json.load(f)

                dependencies = {
                    **package_data.get('dependencies', {}),
                    **package_data.get('devDependencies', {})
                }

                node_modules_path = '/opt/conecta-plus/frontend/node_modules'

                for dep_name in dependencies.keys():
                    dep_path = os.path.join(node_modules_path, dep_name)
                    if not os.path.exists(dep_path):
                        gaps.append({
                            'category': 'dependencies',
                            'type': 'missing_npm_package',
                            'severity': 'high',
                            'description': f'Missing npm package: {dep_name}',
                            'solution': 'Run: npm install',
                            'package': dep_name
                        })

        except Exception as e:
            gaps.append({
                'category': 'dependencies',
                'type': 'check_failed',
                'severity': 'low',
                'description': f'Failed to check npm dependencies: {str(e)}'
            })

        # Verificar requirements.txt vs pip freeze (Python) - DENTRO DO CONTAINER
        try:
            requirements_path = '/opt/conecta-plus/backend/requirements.txt'
            if os.path.exists(requirements_path):
                with open(requirements_path) as f:
                    required_packages = {
                        line.split('==')[0].split('[')[0].strip()
                        for line in f
                        if line.strip() and not line.startswith('#') and not line.startswith('-')
                    }

                # Verificar dentro do container Docker (onde realmente roda)
                result = subprocess.run(
                    ['docker', 'exec', 'conecta-backend-q1', 'pip3', 'list', '--format=json'],
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                if result.returncode == 0:
                    installed_packages = {
                        pkg['name'].lower().replace('-', '_').replace('_', '-')
                        for pkg in json.loads(result.stdout)
                    }
                    # Normalizar nomes de pacotes
                    installed_normalized = set()
                    for pkg in installed_packages:
                        installed_normalized.add(pkg.lower())
                        installed_normalized.add(pkg.lower().replace('-', '_'))
                        installed_normalized.add(pkg.lower().replace('_', '-'))

                    for req_pkg in required_packages:
                        req_normalized = req_pkg.lower().replace('-', '_')
                        req_normalized2 = req_pkg.lower().replace('_', '-')
                        if req_normalized not in installed_normalized and req_normalized2 not in installed_normalized:
                            gaps.append({
                                'category': 'dependencies',
                                'type': 'missing_pip_package',
                                'severity': 'high',
                                'description': f'Missing pip package: {req_pkg}',
                                'solution': 'Run: docker exec conecta-backend-q1 pip3 install -r requirements.txt',
                                'package': req_pkg
                            })

        except Exception as e:
            pass  # Container pode não estar rodando

        return {'gaps': gaps}

    def _check_outdated_packages(self) -> Dict[str, Any]:
        """Verifica pacotes desatualizados"""
        gaps = []

        # NPM outdated
        try:
            result = subprocess.run(
                ['npm', 'outdated', '--json'],
                cwd='/opt/conecta-plus/frontend',
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.stdout:
                outdated = json.loads(result.stdout)

                for package, info in outdated.items():
                    # Verificar se é major version (breaking changes)
                    current = info.get('current', '')
                    latest = info.get('latest', '')

                    severity = 'low'
                    if current.split('.')[0] != latest.split('.')[0]:
                        severity = 'medium'  # Major version change

                    gaps.append({
                        'category': 'outdated_packages',
                        'type': 'outdated_npm',
                        'severity': severity,
                        'description': f'Outdated npm package: {package}',
                        'current_version': current,
                        'latest_version': latest,
                        'solution': f'Run: npm install {package}@latest',
                        'package': package
                    })

        except Exception:
            pass

        return {'gaps': gaps}

    def _check_security_vulnerabilities(self) -> Dict[str, Any]:
        """Verifica vulnerabilidades de segurança"""
        gaps = []

        # npm audit
        try:
            result = subprocess.run(
                ['npm', 'audit', '--json'],
                cwd='/opt/conecta-plus/frontend',
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.stdout:
                audit_data = json.loads(result.stdout)
                vulnerabilities = audit_data.get('vulnerabilities', {})

                for pkg_name, vuln_info in vulnerabilities.items():
                    severity = vuln_info.get('severity', 'low')

                    gaps.append({
                        'category': 'security',
                        'type': 'vulnerability',
                        'severity': severity,
                        'description': f'Security vulnerability in {pkg_name}',
                        'package': pkg_name,
                        'solution': 'Run: npm audit fix',
                        'details': vuln_info.get('via', [])
                    })

        except Exception:
            pass

        # Verificar configurações de segurança
        # Verificar se há secrets em código (excluindo falsos positivos)
        try:
            # Arquivos e padrões a ignorar (hardware defaults, configs de teste, etc)
            ignore_patterns = [
                'hardware.py',           # Senhas default de dispositivos
                'test_',                 # Arquivos de teste
                '.test.',                # Arquivos de teste
                '.spec.',                # Arquivos de spec
                'example',               # Arquivos de exemplo
                '.example',              # Arquivos de exemplo
                'mock',                  # Mocks
                '__pycache__',           # Cache Python
                'node_modules',          # Deps Node
                '.env.example',          # Exemplos de env
                'password or',           # Fallback defaults
                'password:',             # Type hints
                'password=None',         # Defaults None
                'password = None',       # Defaults None
                'TokenData',             # Classes de tipo
                'ProfileToken',          # ONVIF tokens
                'preset_token',          # PTZ presets
            ]

            result = subprocess.run(
                ['grep', '-r', '-i', '-E',
                 '(password|secret|api_key)\\s*=\\s*["\'][a-zA-Z0-9_]{8,}["\']',
                 '/opt/conecta-plus/frontend/src',
                 '/opt/conecta-plus/backend'],
                capture_output=True,
                text=True
            )

            if result.stdout:
                for line in result.stdout.splitlines()[:10]:
                    # Verificar se deve ignorar
                    should_ignore = any(pattern in line for pattern in ignore_patterns)
                    if not should_ignore:
                        gaps.append({
                            'category': 'security',
                            'type': 'hardcoded_secret',
                            'severity': 'critical',
                            'description': 'Possible hardcoded secret detected',
                            'location': line.split(':')[0] if ':' in line else 'unknown',
                            'solution': 'Move secrets to environment variables'
                        })

        except Exception:
            pass

        return {'gaps': gaps}

    def _check_performance_bottlenecks(self) -> Dict[str, Any]:
        """Verifica gargalos de performance"""
        gaps = []

        # Verificar tamanho do bundle
        try:
            next_build_stats = '/opt/conecta-plus/frontend/.next/build-manifest.json'
            if os.path.exists(next_build_stats):
                with open(next_build_stats) as f:
                    build_data = json.load(f)

                # Verificar páginas grandes (>500KB)
                pages = build_data.get('pages', {})
                for page, files in pages.items():
                    total_size = 0
                    for file in files:
                        file_path = os.path.join('/opt/conecta-plus/frontend/.next', file)
                        if os.path.exists(file_path):
                            total_size += os.path.getsize(file_path)

                    if total_size > 500 * 1024:  # 500KB
                        gaps.append({
                            'category': 'performance',
                            'type': 'large_bundle',
                            'severity': 'medium',
                            'description': f'Large bundle size for page: {page}',
                            'size_kb': total_size // 1024,
                            'solution': 'Consider code splitting and lazy loading'
                        })

        except Exception:
            pass

        # Verificar uso de recursos do sistema
        try:
            # CPU usage
            result = subprocess.run(
                ['top', '-bn1'],
                capture_output=True,
                text=True
            )

            cpu_line = [line for line in result.stdout.splitlines() if 'Cpu' in line][0]
            cpu_idle = float(re.search(r'(\d+\.\d+)\s*id', cpu_line).group(1))
            cpu_usage = 100 - cpu_idle

            if cpu_usage > self.config.get('monitoring', {}).get('metrics', {}).get('cpu_threshold', 90):
                gaps.append({
                    'category': 'performance',
                    'type': 'high_cpu',
                    'severity': 'high',
                    'description': f'High CPU usage: {cpu_usage:.1f}%',
                    'solution': 'Investigate CPU-intensive processes'
                })

            # Memory usage
            result = subprocess.run(
                ['free', '-m'],
                capture_output=True,
                text=True
            )

            mem_lines = result.stdout.splitlines()
            mem_info = mem_lines[1].split()
            total_mem = int(mem_info[1])
            used_mem = int(mem_info[2])
            mem_usage = (used_mem / total_mem) * 100

            if mem_usage > self.config.get('monitoring', {}).get('metrics', {}).get('memory_threshold', 85):
                gaps.append({
                    'category': 'performance',
                    'type': 'high_memory',
                    'severity': 'high',
                    'description': f'High memory usage: {mem_usage:.1f}%',
                    'used_mb': used_mem,
                    'total_mb': total_mem,
                    'solution': 'Investigate memory leaks or optimize usage'
                })

        except Exception:
            pass

        return {'gaps': gaps}

    def _check_code_quality(self) -> Dict[str, Any]:
        """Verifica qualidade do código"""
        gaps = []

        # Verificar arquivos TypeScript sem tipos
        try:
            result = subprocess.run(
                ['find', '/opt/conecta-plus/frontend/src', '-name', '*.ts', '-o', '-name', '*.tsx'],
                capture_output=True,
                text=True
            )

            ts_files = result.stdout.splitlines()

            for ts_file in ts_files[:20]:  # Limitar verificação
                try:
                    with open(ts_file, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()

                    # Verificar uso de 'any'
                    any_count = content.count(': any')
                    if any_count > 5:
                        gaps.append({
                            'category': 'code_quality',
                            'type': 'excessive_any',
                            'severity': 'low',
                            'description': f'Excessive use of "any" type in {os.path.basename(ts_file)}',
                            'count': any_count,
                            'file': ts_file,
                            'solution': 'Replace "any" with proper types'
                        })

                    # Verificar console.log não removidos
                    if 'console.log' in content:
                        gaps.append({
                            'category': 'code_quality',
                            'type': 'debug_code',
                            'severity': 'low',
                            'description': f'Debug console.log found in {os.path.basename(ts_file)}',
                            'file': ts_file,
                            'solution': 'Remove or replace with proper logging'
                        })

                except Exception:
                    continue

        except Exception:
            pass

        return {'gaps': gaps}

    def _check_unused_code(self) -> Dict[str, Any]:
        """Detecta código não utilizado"""
        gaps = []

        # Verificar dependências não utilizadas (simplificado)
        try:
            package_json_path = '/opt/conecta-plus/frontend/package.json'
            if os.path.exists(package_json_path):
                with open(package_json_path) as f:
                    package_data = json.load(f)

                dependencies = list(package_data.get('dependencies', {}).keys())

                # Verificar se cada dependência é importada em algum lugar
                for dep in dependencies[:10]:  # Limitar verificação
                    result = subprocess.run(
                        ['grep', '-r', f'from ["\']({dep}|{dep}/)', '/opt/conecta-plus/frontend/src'],
                        capture_output=True,
                        text=True
                    )

                    if not result.stdout:
                        gaps.append({
                            'category': 'unused_code',
                            'type': 'unused_dependency',
                            'severity': 'low',
                            'description': f'Possibly unused dependency: {dep}',
                            'package': dep,
                            'solution': f'Remove if not needed: npm uninstall {dep}'
                        })

        except Exception:
            pass

        return {'gaps': gaps}

    def prioritize_gaps(self, gaps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Prioriza gaps usando sistema P1-P4:

        P1 (Critical): Sistema down, segurança crítica, dados em risco
        P2 (High): Performance degradada, erros frequentes, vulnerabilidades
        P3 (Medium): Pacotes desatualizados com breaking changes, qualidade
        P4 (Low): Melhorias menores, dívida técnica
        """

        def calculate_priority(gap: Dict[str, Any]) -> tuple:
            gap_type = gap.get('type', '')
            severity = gap.get('severity', 'low')
            category = gap.get('category', '')

            # P1 - Critical (prioridade 1)
            if severity == 'critical':
                priority = 1
            elif gap_type in ['hardcoded_secret', 'exposed_endpoint', 'sql_injection']:
                priority = 1
            elif gap_type == 'container_stopped' or 'down' in gap_type.lower():
                priority = 1

            # P2 - High (prioridade 2)
            elif severity == 'high':
                priority = 2
            elif gap_type in ['vulnerability', 'high_cpu', 'high_memory', 'disk_full']:
                priority = 2
            elif gap_type == 'missing_pip_package' or gap_type == 'missing_npm_package':
                priority = 2

            # P3 - Medium (prioridade 3)
            elif severity == 'medium':
                priority = 3
            elif gap_type == 'outdated_npm' and gap.get('current_version', '').split('.')[0] != gap.get('latest_version', '').split('.')[0]:
                priority = 3  # Major version change
            elif gap_type in ['slow_query', 'large_bundle']:
                priority = 3

            # P4 - Low (prioridade 4)
            else:
                priority = 4

            # Adicionar prioridade ao gap
            gap['priority'] = f'P{priority}'
            gap['priority_score'] = priority

            return (priority, severity, gap.get('description', ''))

        # Ordenar por prioridade calculada
        return sorted(gaps, key=calculate_priority)


if __name__ == '__main__':
    # Teste
    import yaml

    with open('/opt/conecta-plus/agents/system-monitor/config.yaml') as f:
        config = yaml.safe_load(f)

    detector = GapDetector(config)
    results = detector.detect_all_gaps()

    print(json.dumps(results, indent=2))
