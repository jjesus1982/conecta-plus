"""
Skill: API Performance Profiler
Monitora performance de APIs, endpoints lentos, erros frequentes
"""

import time
import requests
import json
from typing import Dict, Any, List
from datetime import datetime
from collections import defaultdict


class APIProfiler:
    """Profila performance de APIs"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.endpoints = [
            ('http://localhost:3001/api/health', 'GET', 'API Health'),
            ('http://localhost:3001/api/dashboard/estatisticas', 'GET', 'Dashboard Stats'),
            ('http://localhost/api/health', 'GET', 'Gateway Health'),
            ('http://localhost:8000/health', 'GET', 'Backend Python API'),
        ]

    def profile_endpoint(self, url: str, method: str = 'GET', name: str = None) -> Dict[str, Any]:
        """Profila um endpoint específico"""
        result = {
            'url': url,
            'method': method,
            'name': name or url,
            'timestamp': datetime.now().isoformat(),
            'success': False,
            'metrics': {},
            'issues': []
        }

        try:
            # Fazer requisição e medir tempo
            start_time = time.time()

            if method == 'GET':
                response = requests.get(url, timeout=10, verify=False)
            elif method == 'POST':
                response = requests.post(url, timeout=10, verify=False)
            elif method == 'PUT':
                response = requests.put(url, timeout=10, verify=False)
            else:
                response = requests.get(url, timeout=10, verify=False)

            total_time = (time.time() - start_time) * 1000  # ms

            # Métricas básicas
            result['metrics']['total_time_ms'] = round(total_time, 2)
            result['metrics']['status_code'] = response.status_code
            result['metrics']['response_size_bytes'] = len(response.content)

            # Breakdown de tempo (se disponível nos headers)
            if 'X-Response-Time' in response.headers:
                result['metrics']['server_time_ms'] = response.headers['X-Response-Time']

            # Classificar performance
            if total_time < 100:
                result['metrics']['performance_grade'] = 'A'  # Excellent
            elif total_time < 300:
                result['metrics']['performance_grade'] = 'B'  # Good
            elif total_time < 500:
                result['metrics']['performance_grade'] = 'C'  # Fair
            elif total_time < 1000:
                result['metrics']['performance_grade'] = 'D'  # Poor
            else:
                result['metrics']['performance_grade'] = 'F'  # Very Poor

            # Verificar status code
            if 200 <= response.status_code < 300:
                result['success'] = True
            elif response.status_code >= 500:
                result['issues'].append({
                    'severity': 'high',
                    'message': f'Erro 5xx: {response.status_code}'
                })
            elif response.status_code >= 400:
                result['issues'].append({
                    'severity': 'warning',
                    'message': f'Erro 4xx: {response.status_code}'
                })

            # Alertar se resposta lenta
            if total_time > 1000:
                result['issues'].append({
                    'severity': 'high',
                    'message': f'Resposta muito lenta: {total_time:.2f}ms'
                })
            elif total_time > 500:
                result['issues'].append({
                    'severity': 'warning',
                    'message': f'Resposta lenta: {total_time:.2f}ms'
                })

            # Verificar tamanho da resposta
            response_size_mb = len(response.content) / (1024 * 1024)
            if response_size_mb > 10:
                result['issues'].append({
                    'severity': 'warning',
                    'message': f'Resposta muito grande: {response_size_mb:.2f}MB'
                })

        except requests.exceptions.Timeout:
            result['issues'].append({
                'severity': 'critical',
                'message': 'Timeout (>10s)'
            })
            result['metrics']['timeout'] = True

        except requests.exceptions.ConnectionError:
            result['issues'].append({
                'severity': 'critical',
                'message': 'Conexão recusada - serviço indisponível'
            })
            result['metrics']['connection_error'] = True

        except Exception as e:
            result['issues'].append({
                'severity': 'high',
                'message': f'Erro: {str(e)}'
            })

        return result

    def profile_all_endpoints(self) -> Dict[str, Any]:
        """Profila todos os endpoints configurados"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'endpoints': [],
            'summary': {
                'total': 0,
                'successful': 0,
                'failed': 0,
                'avg_response_time_ms': 0,
                'slow_endpoints': 0,
                'error_endpoints': 0
            }
        }

        total_time = 0
        successful_count = 0

        for url, method, name in self.endpoints:
            profile = self.profile_endpoint(url, method, name)
            results['endpoints'].append(profile)

            results['summary']['total'] += 1

            if profile['success']:
                results['summary']['successful'] += 1
                successful_count += 1

                if 'total_time_ms' in profile['metrics']:
                    total_time += profile['metrics']['total_time_ms']
            else:
                results['summary']['failed'] += 1
                results['summary']['error_endpoints'] += 1

            # Contar endpoints lentos
            if profile['metrics'].get('total_time_ms', 0) > 500:
                results['summary']['slow_endpoints'] += 1

        # Calcular média
        if successful_count > 0:
            results['summary']['avg_response_time_ms'] = round(total_time / successful_count, 2)

        return results

    def load_test_endpoint(self, url: str, num_requests: int = 50) -> Dict[str, Any]:
        """Faz load test em um endpoint"""
        result = {
            'url': url,
            'num_requests': num_requests,
            'timestamp': datetime.now().isoformat(),
            'results': [],
            'summary': {}
        }

        response_times = []
        status_codes = defaultdict(int)
        errors = 0

        for i in range(num_requests):
            try:
                start = time.time()
                response = requests.get(url, timeout=10, verify=False)
                response_time = (time.time() - start) * 1000

                response_times.append(response_time)
                status_codes[response.status_code] += 1

            except:
                errors += 1

        # Calcular estatísticas
        if response_times:
            result['summary']['min_ms'] = round(min(response_times), 2)
            result['summary']['max_ms'] = round(max(response_times), 2)
            result['summary']['avg_ms'] = round(sum(response_times) / len(response_times), 2)
            result['summary']['median_ms'] = round(sorted(response_times)[len(response_times) // 2], 2)

            # Percentis
            sorted_times = sorted(response_times)
            result['summary']['p50_ms'] = round(sorted_times[int(len(sorted_times) * 0.5)], 2)
            result['summary']['p95_ms'] = round(sorted_times[int(len(sorted_times) * 0.95)], 2)
            result['summary']['p99_ms'] = round(sorted_times[int(len(sorted_times) * 0.99)], 2)

        result['summary']['status_codes'] = dict(status_codes)
        result['summary']['errors'] = errors
        result['summary']['success_rate'] = round(
            (num_requests - errors) / num_requests * 100, 2
        ) if num_requests > 0 else 0

        return result

    def run_full_profile(self) -> Dict[str, Any]:
        """Executa profiling completo"""
        return {
            'timestamp': datetime.now().isoformat(),
            'endpoint_profiles': self.profile_all_endpoints()
        }


if __name__ == '__main__':
    profiler = APIProfiler({})
    results = profiler.run_full_profile()
    print(json.dumps(results, indent=2))
