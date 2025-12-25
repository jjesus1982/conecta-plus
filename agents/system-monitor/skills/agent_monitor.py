"""
Skill: Agent Health Monitor
Monitora saúde de TODOS os agentes do Conecta Plus
"""

import os
import json
import subprocess
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path


class AgentMonitor:
    """Monitora saúde de todos os agentes"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.agents_dir = '/opt/conecta-plus/agents'

    def discover_all_agents(self) -> List[str]:
        """Descobre todos os agentes no sistema"""
        agents = []

        try:
            for item in os.listdir(self.agents_dir):
                agent_path = os.path.join(self.agents_dir, item)
                if os.path.isdir(agent_path):
                    # Verificar se tem agent.py ou main.py
                    if (os.path.exists(os.path.join(agent_path, 'agent.py')) or
                        os.path.exists(os.path.join(agent_path, 'main.py')) or
                        os.path.exists(os.path.join(agent_path, 'index.ts'))):
                        agents.append(item)
        except Exception as e:
            print(f"Error discovering agents: {e}")

        return sorted(agents)

    def check_agent_health(self, agent_name: str) -> Dict[str, Any]:
        """Verifica saúde de um agente específico"""
        result = {
            'agent_name': agent_name,
            'timestamp': datetime.now().isoformat(),
            'status': 'unknown',
            'metrics': {},
            'issues': []
        }

        agent_path = os.path.join(self.agents_dir, agent_name)

        # Verificar se diretório existe
        if not os.path.exists(agent_path):
            result['status'] = 'not_found'
            result['issues'].append({
                'severity': 'critical',
                'message': f'Diretório do agente não encontrado: {agent_path}'
            })
            return result

        # Verificar arquivo principal
        main_files = ['agent.py', 'main.py', 'index.ts', 'index.js']
        main_file_found = None

        for main_file in main_files:
            if os.path.exists(os.path.join(agent_path, main_file)):
                main_file_found = main_file
                break

        if not main_file_found:
            result['status'] = 'incomplete'
            result['issues'].append({
                'severity': 'high',
                'message': 'Arquivo principal não encontrado (agent.py, main.py, index.ts)'
            })
            return result

        result['metrics']['main_file'] = main_file_found

        # Verificar se tem state.json (se agente salva estado)
        state_file = os.path.join(agent_path, 'state.json')
        if os.path.exists(state_file):
            try:
                with open(state_file) as f:
                    state_data = json.load(f)

                result['metrics']['has_state'] = True
                result['metrics']['last_update'] = state_data.get('last_update', 'unknown')
                result['metrics']['iteration'] = state_data.get('iteration', 0)

                # Verificar se está atualizando (último update < 5 minutos)
                if 'last_update' in state_data:
                    try:
                        from datetime import datetime as dt, timedelta
                        last_update = dt.fromisoformat(state_data['last_update'])
                        now = dt.now()
                        diff = (now - last_update).total_seconds()

                        if diff > 300:  # 5 minutos
                            result['issues'].append({
                                'severity': 'warning',
                                'message': f'Agente não atualiza há {int(diff/60)} minutos'
                            })
                    except:
                        pass

            except Exception as e:
                result['issues'].append({
                    'severity': 'warning',
                    'message': f'Erro ao ler state.json: {str(e)}'
                })

        # Verificar logs
        logs_dir = os.path.join(agent_path, 'logs')
        if os.path.exists(logs_dir):
            result['metrics']['has_logs'] = True

            # Procurar arquivo de log mais recente
            log_files = list(Path(logs_dir).glob('*.log'))
            if log_files:
                latest_log = max(log_files, key=lambda p: p.stat().st_mtime)
                result['metrics']['latest_log'] = str(latest_log.name)

                # Verificar tamanho do log
                log_size_mb = latest_log.stat().st_size / (1024 * 1024)
                result['metrics']['log_size_mb'] = round(log_size_mb, 2)

                if log_size_mb > 100:
                    result['issues'].append({
                        'severity': 'warning',
                        'message': f'Log muito grande: {log_size_mb:.2f}MB (considere rotação)'
                    })

                # Ler últimas linhas para erros
                try:
                    with open(latest_log) as f:
                        lines = f.readlines()[-100:]  # Últimas 100 linhas

                    error_count = sum(
                        1 for line in lines
                        if any(keyword in line.lower() for keyword in ['error', 'exception', 'critical', 'fatal'])
                    )

                    result['metrics']['recent_errors'] = error_count

                    if error_count > 10:
                        result['issues'].append({
                            'severity': 'high',
                            'message': f'{error_count} erros nos últimos 100 logs'
                        })

                except Exception as e:
                    result['issues'].append({
                        'severity': 'info',
                        'message': f'Erro ao ler log: {str(e)}'
                    })

        # Verificar se tem package.json ou requirements.txt
        if os.path.exists(os.path.join(agent_path, 'package.json')):
            result['metrics']['type'] = 'Node.js/TypeScript'
        elif os.path.exists(os.path.join(agent_path, 'requirements.txt')):
            result['metrics']['type'] = 'Python'
        else:
            result['metrics']['type'] = 'unknown'

        # Verificar se tem README
        if os.path.exists(os.path.join(agent_path, 'README.md')):
            result['metrics']['has_documentation'] = True
        else:
            result['issues'].append({
                'severity': 'low',
                'message': 'README.md não encontrado'
            })

        # Verificar se está rodando como serviço
        service_name = agent_name.replace('_', '-')
        try:
            service_check = subprocess.run(
                ['systemctl', 'is-active', service_name],
                capture_output=True,
                text=True,
                timeout=2
            )

            if service_check.stdout.strip() == 'active':
                result['status'] = 'running'
                result['metrics']['service_status'] = 'active'
            elif service_check.stdout.strip() == 'inactive':
                result['status'] = 'stopped'
                result['metrics']['service_status'] = 'inactive'
                result['issues'].append({
                    'severity': 'high',
                    'message': f'Serviço {service_name} não está rodando'
                })
            else:
                result['status'] = 'no_service'
                result['metrics']['service_status'] = 'not_configured'
                result['issues'].append({
                    'severity': 'info',
                    'message': 'Agente não configurado como serviço systemd'
                })

        except Exception:
            result['status'] = 'no_service'
            result['metrics']['service_status'] = 'unknown'

        # Se não tem issues críticos e está rodando, marcar como healthy
        if result['status'] == 'running' and not any(
            issue['severity'] in ['critical', 'high'] for issue in result['issues']
        ):
            result['status'] = 'healthy'

        return result

    def check_all_agents(self) -> Dict[str, Any]:
        """Verifica todos os agentes do sistema"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'agents': [],
            'summary': {
                'total_agents': 0,
                'healthy': 0,
                'running': 0,
                'stopped': 0,
                'errors': 0,
                'total_issues': 0
            }
        }

        agents = self.discover_all_agents()
        results['summary']['total_agents'] = len(agents)

        for agent_name in agents:
            agent_health = self.check_agent_health(agent_name)
            results['agents'].append(agent_health)

            # Atualizar summary
            status = agent_health['status']

            if status == 'healthy':
                results['summary']['healthy'] += 1
                results['summary']['running'] += 1
            elif status == 'running':
                results['summary']['running'] += 1
            elif status == 'stopped':
                results['summary']['stopped'] += 1

            # Contar issues críticos
            critical_issues = [
                issue for issue in agent_health.get('issues', [])
                if issue['severity'] in ['critical', 'high']
            ]

            if critical_issues:
                results['summary']['errors'] += 1

            results['summary']['total_issues'] += len(agent_health.get('issues', []))

        return results

    def get_agent_dependencies(self, agent_name: str) -> Dict[str, Any]:
        """Verifica dependências de um agente"""
        result = {
            'agent_name': agent_name,
            'dependencies': [],
            'issues': []
        }

        agent_path = os.path.join(self.agents_dir, agent_name)

        # Verificar package.json
        package_json = os.path.join(agent_path, 'package.json')
        if os.path.exists(package_json):
            try:
                with open(package_json) as f:
                    package_data = json.load(f)

                deps = package_data.get('dependencies', {})
                dev_deps = package_data.get('devDependencies', {})

                result['dependencies'] = {
                    'production': list(deps.keys()),
                    'development': list(dev_deps.keys()),
                    'total': len(deps) + len(dev_deps)
                }

            except Exception as e:
                result['issues'].append({
                    'severity': 'warning',
                    'message': f'Erro ao ler package.json: {str(e)}'
                })

        # Verificar requirements.txt
        requirements_txt = os.path.join(agent_path, 'requirements.txt')
        if os.path.exists(requirements_txt):
            try:
                with open(requirements_txt) as f:
                    deps = [line.strip() for line in f if line.strip() and not line.startswith('#')]

                result['dependencies'] = {
                    'python_packages': deps,
                    'total': len(deps)
                }

            except Exception as e:
                result['issues'].append({
                    'severity': 'warning',
                    'message': f'Erro ao ler requirements.txt: {str(e)}'
                })

        return result

    def run_full_check(self) -> Dict[str, Any]:
        """Executa verificação completa de todos os agentes"""
        return {
            'timestamp': datetime.now().isoformat(),
            'agent_health': self.check_all_agents()
        }


if __name__ == '__main__':
    monitor = AgentMonitor({})
    results = monitor.run_full_check()
    print(json.dumps(results, indent=2))
