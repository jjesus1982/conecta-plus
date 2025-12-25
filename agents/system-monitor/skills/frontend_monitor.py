"""
Skill: Frontend Error Tracker
Monitora erros do frontend, performance web, bundle size, build status
"""

import os
import json
import subprocess
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path


class FrontendMonitor:
    """Monitora saúde do frontend"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.frontend_path = '/opt/conecta-plus/frontend'

    def check_build_status(self) -> Dict[str, Any]:
        """Verifica status do build Next.js"""
        result = {
            'timestamp': datetime.now().isoformat(),
            'build_exists': False,
            'build_info': {},
            'issues': []
        }

        # Verificar se .next existe
        next_dir = os.path.join(self.frontend_path, '.next')

        if not os.path.exists(next_dir):
            result['issues'].append({
                'severity': 'critical',
                'message': 'Build Next.js não encontrado - executar npm run build'
            })
            return result

        result['build_exists'] = True

        # Verificar BUILD_ID
        build_id_file = os.path.join(next_dir, 'BUILD_ID')
        if os.path.exists(build_id_file):
            try:
                with open(build_id_file) as f:
                    build_id = f.read().strip()
                result['build_info']['build_id'] = build_id
            except:
                pass

        # Verificar required-server-files.json
        required_files = os.path.join(next_dir, 'required-server-files.json')
        if os.path.exists(required_files):
            try:
                with open(required_files) as f:
                    data = json.load(f)
                result['build_info']['config'] = data.get('config', {})
            except:
                pass

        # Verificar tamanho do build
        try:
            size_cmd = subprocess.run(
                ['du', '-sh', next_dir],
                capture_output=True,
                text=True,
                timeout=10
            )

            if size_cmd.returncode == 0:
                size_str = size_cmd.stdout.split()[0]
                result['build_info']['size'] = size_str

                # Alertar se build > 500MB
                if 'G' in size_str:
                    result['issues'].append({
                        'severity': 'warning',
                        'message': f'Build muito grande: {size_str} (otimizar)'
                    })

        except:
            pass

        # Verificar idade do build
        build_mtime = os.path.getmtime(next_dir)
        build_age_hours = (datetime.now().timestamp() - build_mtime) / 3600
        result['build_info']['age_hours'] = round(build_age_hours, 2)

        if build_age_hours > 168:  # 7 dias
            result['issues'].append({
                'severity': 'warning',
                'message': f'Build antigo ({int(build_age_hours/24)} dias) - considere rebuild'
            })

        return result

    def check_package_json(self) -> Dict[str, Any]:
        """Verifica package.json e dependências"""
        result = {
            'timestamp': datetime.now().isoformat(),
            'dependencies': {},
            'issues': []
        }

        package_json = os.path.join(self.frontend_path, 'package.json')

        if not os.path.exists(package_json):
            result['issues'].append({
                'severity': 'critical',
                'message': 'package.json não encontrado'
            })
            return result

        try:
            with open(package_json) as f:
                package_data = json.load(f)

            result['package_name'] = package_data.get('name', 'unknown')
            result['version'] = package_data.get('version', 'unknown')

            deps = package_data.get('dependencies', {})
            dev_deps = package_data.get('devDependencies', {})

            result['dependencies'] = {
                'production_count': len(deps),
                'development_count': len(dev_deps),
                'total': len(deps) + len(dev_deps)
            }

            # Verificar se Next.js está nas dependências
            if 'next' not in deps:
                result['issues'].append({
                    'severity': 'critical',
                    'message': 'Next.js não encontrado nas dependências'
                })
            else:
                result['dependencies']['next_version'] = deps['next']

            # Verificar React
            if 'react' in deps:
                result['dependencies']['react_version'] = deps['react']

        except json.JSONDecodeError:
            result['issues'].append({
                'severity': 'high',
                'message': 'package.json inválido (JSON malformado)'
            })
        except Exception as e:
            result['issues'].append({
                'severity': 'high',
                'message': f'Erro ao ler package.json: {str(e)}'
            })

        return result

    def check_node_modules(self) -> Dict[str, Any]:
        """Verifica node_modules"""
        result = {
            'timestamp': datetime.now().isoformat(),
            'exists': False,
            'metrics': {},
            'issues': []
        }

        node_modules = os.path.join(self.frontend_path, 'node_modules')

        if not os.path.exists(node_modules):
            result['issues'].append({
                'severity': 'critical',
                'message': 'node_modules não encontrado - executar npm install'
            })
            return result

        result['exists'] = True

        # Contar pacotes instalados
        try:
            package_count = len([
                d for d in os.listdir(node_modules)
                if os.path.isdir(os.path.join(node_modules, d)) and not d.startswith('.')
            ])
            result['metrics']['package_count'] = package_count
        except:
            pass

        # Tamanho do node_modules
        try:
            size_cmd = subprocess.run(
                ['du', '-sh', node_modules],
                capture_output=True,
                text=True,
                timeout=20
            )

            if size_cmd.returncode == 0:
                size_str = size_cmd.stdout.split()[0]
                result['metrics']['size'] = size_str

                # Alertar se > 1GB
                if 'G' in size_str:
                    try:
                        size_gb = float(size_str.replace('G', ''))
                        if size_gb > 1:
                            result['issues'].append({
                                'severity': 'warning',
                                'message': f'node_modules muito grande: {size_str}'
                            })
                    except:
                        pass

        except:
            pass

        return result

    def check_typescript_config(self) -> Dict[str, Any]:
        """Verifica configuração TypeScript"""
        result = {
            'timestamp': datetime.now().isoformat(),
            'configured': False,
            'config': {},
            'issues': []
        }

        tsconfig = os.path.join(self.frontend_path, 'tsconfig.json')

        if not os.path.exists(tsconfig):
            result['issues'].append({
                'severity': 'info',
                'message': 'TypeScript não configurado (tsconfig.json não encontrado)'
            })
            return result

        result['configured'] = True

        try:
            with open(tsconfig) as f:
                ts_config = json.load(f)

            compiler_options = ts_config.get('compilerOptions', {})

            result['config']['strict'] = compiler_options.get('strict', False)
            result['config']['target'] = compiler_options.get('target', 'unknown')
            result['config']['module'] = compiler_options.get('module', 'unknown')

            # Recomendar strict mode
            if not compiler_options.get('strict'):
                result['issues'].append({
                    'severity': 'low',
                    'message': 'TypeScript strict mode não habilitado (recomendado)'
                })

        except Exception as e:
            result['issues'].append({
                'severity': 'warning',
                'message': f'Erro ao ler tsconfig.json: {str(e)}'
            })

        return result

    def check_env_files(self) -> Dict[str, Any]:
        """Verifica arquivos .env do frontend"""
        result = {
            'timestamp': datetime.now().isoformat(),
            'env_files': [],
            'issues': []
        }

        env_files = [
            '.env',
            '.env.local',
            '.env.production',
            '.env.development'
        ]

        for env_file in env_files:
            env_path = os.path.join(self.frontend_path, env_file)

            if os.path.exists(env_path):
                file_info = {
                    'file': env_file,
                    'exists': True,
                    'variable_count': 0
                }

                try:
                    with open(env_path) as f:
                        lines = [
                            line.strip() for line in f
                            if line.strip() and not line.startswith('#') and '=' in line
                        ]
                    file_info['variable_count'] = len(lines)

                    # Verificar variáveis importantes
                    env_content = '\n'.join(lines)

                    important_vars = [
                        'NEXT_PUBLIC_API_URL'
                    ]

                    for var in important_vars:
                        if var not in env_content:
                            if env_file == '.env.local':  # Apenas alertar para .env.local
                                result['issues'].append({
                                    'severity': 'warning',
                                    'message': f'{var} não encontrado em {env_file}'
                                })

                except Exception as e:
                    file_info['error'] = str(e)

                result['env_files'].append(file_info)

        if not any(f['exists'] for f in result['env_files']):
            result['issues'].append({
                'severity': 'warning',
                'message': 'Nenhum arquivo .env encontrado'
            })

        return result

    def run_full_check(self) -> Dict[str, Any]:
        """Executa verificação completa do frontend"""
        return {
            'timestamp': datetime.now().isoformat(),
            'build_status': self.check_build_status(),
            'package_json': self.check_package_json(),
            'node_modules': self.check_node_modules(),
            'typescript': self.check_typescript_config(),
            'environment': self.check_env_files()
        }


if __name__ == '__main__':
    monitor = FrontendMonitor({})
    results = monitor.run_full_check()
    print(json.dumps(results, indent=2))
