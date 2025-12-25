"""
Skill: Container Health Monitor
Monitora saúde, performance e logs de todos os containers Docker
"""

import subprocess
import json
from typing import Dict, Any, List
from datetime import datetime


class ContainerMonitor:
    """Monitora containers Docker"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def list_all_containers(self) -> List[Dict[str, Any]]:
        """Lista todos os containers"""
        containers = []

        try:
            result = subprocess.run(
                ['docker', 'ps', '-a', '--format', '{{json .}}'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line:
                        try:
                            container = json.loads(line)
                            containers.append(container)
                        except json.JSONDecodeError:
                            pass

        except Exception as e:
            print(f"Error listing containers: {e}")

        return containers

    def check_container_health(self, container_name: str) -> Dict[str, Any]:
        """Verifica saúde de um container específico"""
        result = {
            'name': container_name,
            'timestamp': datetime.now().isoformat(),
            'status': 'unknown',
            'health': 'unknown',
            'metrics': {},
            'issues': []
        }

        try:
            # Inspect container
            inspect_cmd = subprocess.run(
                ['docker', 'inspect', container_name],
                capture_output=True,
                text=True,
                timeout=5
            )

            if inspect_cmd.returncode == 0:
                inspect_data = json.loads(inspect_cmd.stdout)[0]

                # Status
                state = inspect_data.get('State', {})
                result['status'] = state.get('Status', 'unknown')
                result['running'] = state.get('Running', False)
                result['restart_count'] = state.get('RestartCount', 0)

                # Health check
                if 'Health' in state:
                    health_status = state['Health'].get('Status', 'none')
                    result['health'] = health_status

                    if health_status == 'unhealthy':
                        result['issues'].append({
                            'severity': 'critical',
                            'message': f'Container {container_name} está unhealthy'
                        })

                # Restart count alto
                if result['restart_count'] > 5:
                    result['issues'].append({
                        'severity': 'high',
                        'message': f'Container reiniciou {result["restart_count"]} vezes'
                    })

                # Stats (CPU, Memory)
                stats_cmd = subprocess.run(
                    ['docker', 'stats', container_name, '--no-stream', '--format', '{{json .}}'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                if stats_cmd.returncode == 0:
                    try:
                        stats_data = json.loads(stats_cmd.stdout)
                        result['metrics']['cpu_percent'] = stats_data.get('CPUPerc', '0%').replace('%', '')
                        result['metrics']['memory_usage'] = stats_data.get('MemUsage', 'N/A')
                        result['metrics']['memory_percent'] = stats_data.get('MemPerc', '0%').replace('%', '')
                        result['metrics']['network_io'] = stats_data.get('NetIO', 'N/A')
                        result['metrics']['block_io'] = stats_data.get('BlockIO', 'N/A')

                        # Alertar se CPU > 80%
                        try:
                            cpu_percent = float(result['metrics']['cpu_percent'])
                            if cpu_percent > 80:
                                result['issues'].append({
                                    'severity': 'warning',
                                    'message': f'CPU usage alto: {cpu_percent}%'
                                })
                        except ValueError:
                            pass

                        # Alertar se Memory > 80%
                        try:
                            mem_percent = float(result['metrics']['memory_percent'])
                            if mem_percent > 80:
                                result['issues'].append({
                                    'severity': 'warning',
                                    'message': f'Memory usage alto: {mem_percent}%'
                                })
                        except ValueError:
                            pass

                    except json.JSONDecodeError:
                        pass

                # Verificar logs recentes para erros
                logs_cmd = subprocess.run(
                    ['docker', 'logs', '--tail', '100', container_name],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                if logs_cmd.returncode == 0:
                    error_keywords = ['error', 'exception', 'fatal', 'panic', 'crash']
                    error_count = sum(
                        logs_cmd.stderr.lower().count(keyword) + logs_cmd.stdout.lower().count(keyword)
                        for keyword in error_keywords
                    )

                    result['metrics']['recent_errors'] = error_count

                    if error_count > 10:
                        result['issues'].append({
                            'severity': 'high',
                            'message': f'{error_count} erros encontrados nos últimos 100 logs'
                        })

        except subprocess.TimeoutExpired:
            result['issues'].append({
                'severity': 'high',
                'message': 'Timeout ao inspecionar container'
            })
        except Exception as e:
            result['issues'].append({
                'severity': 'high',
                'message': f'Erro: {str(e)}'
            })

        return result

    def check_all_containers(self) -> Dict[str, Any]:
        """Verifica todos os containers"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'containers': [],
            'summary': {
                'total': 0,
                'running': 0,
                'stopped': 0,
                'unhealthy': 0,
                'total_issues': 0
            }
        }

        containers = self.list_all_containers()
        results['summary']['total'] = len(containers)

        for container in containers:
            container_name = container.get('Names', 'unknown')
            health_check = self.check_container_health(container_name)
            results['containers'].append(health_check)

            # Atualizar summary
            if health_check.get('running'):
                results['summary']['running'] += 1
            else:
                results['summary']['stopped'] += 1

            if health_check.get('health') == 'unhealthy':
                results['summary']['unhealthy'] += 1

            results['summary']['total_issues'] += len(health_check.get('issues', []))

        return results

    def check_docker_disk_usage(self) -> Dict[str, Any]:
        """Verifica uso de disco do Docker"""
        result = {
            'timestamp': datetime.now().isoformat(),
            'disk_usage': {},
            'issues': []
        }

        try:
            df_cmd = subprocess.run(
                ['docker', 'system', 'df', '--format', '{{json .}}'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if df_cmd.returncode == 0:
                for line in df_cmd.stdout.strip().split('\n'):
                    if line:
                        try:
                            item = json.loads(line)
                            item_type = item.get('Type', 'unknown')
                            result['disk_usage'][item_type] = {
                                'total': item.get('TotalCount', 0),
                                'active': item.get('Active', 0),
                                'size': item.get('Size', '0B'),
                                'reclaimable': item.get('Reclaimable', '0B')
                            }

                            # Alertar se reclaimable > 10GB
                            reclaimable_str = item.get('Reclaimable', '0B')
                            if 'GB' in reclaimable_str:
                                try:
                                    reclaimable_gb = float(reclaimable_str.split('GB')[0])
                                    if reclaimable_gb > 10:
                                        result['issues'].append({
                                            'severity': 'warning',
                                            'message': f'{item_type}: {reclaimable_gb}GB podem ser recuperados'
                                        })
                                except ValueError:
                                    pass

                        except json.JSONDecodeError:
                            pass

        except Exception as e:
            result['issues'].append({
                'severity': 'warning',
                'message': f'Erro ao verificar disk usage: {str(e)}'
            })

        return result

    def run_full_check(self) -> Dict[str, Any]:
        """Executa verificação completa de containers"""
        return {
            'timestamp': datetime.now().isoformat(),
            'container_health': self.check_all_containers(),
            'disk_usage': self.check_docker_disk_usage()
        }


if __name__ == '__main__':
    monitor = ContainerMonitor({})
    results = monitor.run_full_check()
    print(json.dumps(results, indent=2))
