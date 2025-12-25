"""
Skill: Load Tester
Testa carga do sistema com múltiplas requisições simultâneas
"""

import asyncio
import aiohttp
import time
from typing import Dict, Any, List
from datetime import datetime
import statistics


class LoadTester:
    """Executa testes de carga no sistema"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.test_results = []

    async def _make_request(
        self,
        session: aiohttp.ClientSession,
        url: str,
        method: str = 'GET',
        headers: Dict = None,
        json_data: Dict = None
    ) -> Dict[str, Any]:
        """Faz uma requisição HTTP"""
        start_time = time.time()

        try:
            async with session.request(
                method,
                url,
                headers=headers,
                json=json_data,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                duration = time.time() - start_time

                return {
                    'success': True,
                    'status_code': response.status,
                    'duration': duration,
                    'url': url,
                    'method': method
                }
        except asyncio.TimeoutError:
            return {
                'success': False,
                'error': 'timeout',
                'duration': time.time() - start_time,
                'url': url,
                'method': method
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'duration': time.time() - start_time,
                'url': url,
                'method': method
            }

    async def run_concurrent_requests(
        self,
        url: str,
        num_requests: int = 100,
        method: str = 'GET',
        headers: Dict = None,
        json_data: Dict = None
    ) -> Dict[str, Any]:
        """
        Executa N requisições concorrentes

        Args:
            url: URL para testar
            num_requests: Número de requisições simultâneas
            method: Método HTTP
            headers: Headers da requisição
            json_data: Dados JSON para POST/PUT

        Returns:
            Estatísticas do teste
        """
        start_time = time.time()

        async with aiohttp.ClientSession() as session:
            tasks = [
                self._make_request(session, url, method, headers, json_data)
                for _ in range(num_requests)
            ]

            results = await asyncio.gather(*tasks)

        total_time = time.time() - start_time

        # Análise dos resultados
        successful = [r for r in results if r.get('success')]
        failed = [r for r in results if not r.get('success')]

        durations = [r['duration'] for r in successful]
        status_codes = {}

        for r in results:
            code = r.get('status_code', 'error')
            status_codes[code] = status_codes.get(code, 0) + 1

        return {
            'timestamp': datetime.now().isoformat(),
            'url': url,
            'method': method,
            'total_requests': num_requests,
            'successful': len(successful),
            'failed': len(failed),
            'success_rate': (len(successful) / num_requests * 100) if num_requests > 0 else 0,
            'total_time': total_time,
            'requests_per_second': num_requests / total_time if total_time > 0 else 0,
            'avg_response_time': statistics.mean(durations) if durations else 0,
            'min_response_time': min(durations) if durations else 0,
            'max_response_time': max(durations) if durations else 0,
            'median_response_time': statistics.median(durations) if durations else 0,
            'status_codes': status_codes,
            'errors': [r.get('error') for r in failed if r.get('error')],
            'performance_grade': self._grade_performance(durations, len(failed), num_requests)
        }

    def _grade_performance(
        self,
        durations: List[float],
        failed_count: int,
        total: int
    ) -> str:
        """Avalia performance do teste"""
        if not durations:
            return 'F - Sistema não respondeu'

        avg = statistics.mean(durations)
        failure_rate = (failed_count / total * 100) if total > 0 else 100

        if failure_rate > 10:
            return 'F - Alta taxa de falha'
        elif avg < 0.1:  # < 100ms
            return 'A - Excelente'
        elif avg < 0.5:  # < 500ms
            return 'B - Bom'
        elif avg < 1.0:  # < 1s
            return 'C - Aceitável'
        elif avg < 3.0:  # < 3s
            return 'D - Lento'
        else:
            return 'F - Muito lento'

    def test_endpoints(self) -> Dict[str, Any]:
        """Testa todos os endpoints principais"""
        endpoints = [
            ('http://localhost:3000/', 'GET', 'Frontend Home'),
            ('http://localhost:3000/dashboard', 'GET', 'Dashboard'),
            ('http://localhost:3000/cftv', 'GET', 'CFTV Page'),
            ('http://localhost:3001/health', 'GET', 'API Health'),
            ('http://localhost:8888/', 'GET', 'Monitor Dashboard'),
        ]

        results = {}

        for url, method, name in endpoints:
            try:
                result = asyncio.run(
                    self.run_concurrent_requests(url, num_requests=100, method=method)
                )
                results[name] = result
            except Exception as e:
                results[name] = {
                    'error': str(e),
                    'url': url,
                    'failed': True
                }

        return {
            'timestamp': datetime.now().isoformat(),
            'test_type': 'load_test',
            'results': results,
            'summary': self._summarize_results(results)
        }

    def _summarize_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Gera resumo dos resultados"""
        total_endpoints = len(results)
        passing = sum(1 for r in results.values() if r.get('performance_grade', 'F')[0] in ['A', 'B'])
        failing = sum(1 for r in results.values() if r.get('performance_grade', 'F')[0] in ['D', 'F'])

        avg_rps = statistics.mean([
            r.get('requests_per_second', 0)
            for r in results.values()
            if not r.get('failed')
        ]) if results else 0

        return {
            'total_endpoints_tested': total_endpoints,
            'passing': passing,
            'warning': total_endpoints - passing - failing,
            'failing': failing,
            'avg_requests_per_second': avg_rps,
            'overall_health': 'healthy' if failing == 0 else 'degraded' if failing < total_endpoints / 2 else 'critical'
        }

    def stress_test(self, url: str, duration_seconds: int = 60) -> Dict[str, Any]:
        """
        Teste de stress - aumenta carga gradualmente

        Args:
            url: URL para testar
            duration_seconds: Duração do teste

        Returns:
            Resultados do stress test
        """
        results = []
        start_time = time.time()

        concurrent_requests = 10

        while time.time() - start_time < duration_seconds:
            result = asyncio.run(
                self.run_concurrent_requests(url, concurrent_requests)
            )

            results.append({
                'concurrent_requests': concurrent_requests,
                'result': result
            })

            # Aumentar carga gradualmente
            if result['success_rate'] > 95:
                concurrent_requests = int(concurrent_requests * 1.5)

            time.sleep(5)  # Aguardar entre rodadas

        return {
            'timestamp': datetime.now().isoformat(),
            'test_type': 'stress_test',
            'duration': duration_seconds,
            'url': url,
            'max_concurrent': max([r['concurrent_requests'] for r in results]),
            'results': results,
            'breaking_point': self._find_breaking_point(results)
        }

    def _find_breaking_point(self, results: List[Dict]) -> Dict[str, Any]:
        """Identifica o ponto onde o sistema começa a falhar"""
        for i, r in enumerate(results):
            if r['result']['success_rate'] < 90:
                return {
                    'concurrent_requests': r['concurrent_requests'],
                    'success_rate': r['result']['success_rate'],
                    'avg_response_time': r['result']['avg_response_time']
                }

        return {
            'message': 'Sistema aguentou toda a carga',
            'max_tested': results[-1]['concurrent_requests'] if results else 0
        }


if __name__ == '__main__':
    # Teste
    import json

    tester = LoadTester({})
    results = tester.test_endpoints()

    print(json.dumps(results, indent=2))
