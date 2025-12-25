"""
Skill: Edge Case Tester
Testa edge cases e dados inválidos
"""

import requests
from typing import Dict, Any, List
from datetime import datetime


class EdgeCaseTester:
    """Testa edge cases e validações"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def test_null_and_empty_values(self) -> Dict[str, Any]:
        """Testa valores nulos e vazios"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'test_type': 'null_empty_validation',
            'tests': []
        }

        base_url = 'http://localhost:3001/api'

        # Test cases
        test_cases = [
            {
                'name': 'Null JSON body',
                'endpoint': f'{base_url}/condominios',
                'method': 'POST',
                'data': None,
                'expected_status': [400, 422, 403]
            },
            {
                'name': 'Empty JSON',
                'endpoint': f'{base_url}/condominios',
                'method': 'POST',
                'data': {},
                'expected_status': [400, 422, 403]
            },
            {
                'name': 'Null values in fields',
                'endpoint': f'{base_url}/condominios',
                'method': 'POST',
                'data': {'name': None, 'cnpj': None},
                'expected_status': [400, 422, 403]
            },
            {
                'name': 'Empty strings',
                'endpoint': f'{base_url}/condominios',
                'method': 'POST',
                'data': {'name': '', 'cnpj': ''},
                'expected_status': [400, 422, 403]
            },
        ]

        for test in test_cases:
            result = self._run_test_case(test)
            results['tests'].append(result)

        results['summary'] = self._summarize(results['tests'])
        return results

    def test_invalid_data_types(self) -> Dict[str, Any]:
        """Testa tipos de dados inválidos"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'test_type': 'invalid_data_types',
            'tests': []
        }

        base_url = 'http://localhost:3001/api'

        test_cases = [
            {
                'name': 'String where number expected',
                'endpoint': f'{base_url}/condominios',
                'method': 'POST',
                'data': {'id': 'abc', 'name': 'Test'},
                'expected_status': [400, 422, 403]
            },
            {
                'name': 'Number where string expected',
                'endpoint': f'{base_url}/condominios',
                'method': 'POST',
                'data': {'name': 12345},
                'expected_status': [400, 422, 403]
            },
            {
                'name': 'Array where object expected',
                'endpoint': f'{base_url}/condominios',
                'method': 'POST',
                'data': [],
                'expected_status': [400, 422, 403]
            },
        ]

        for test in test_cases:
            result = self._run_test_case(test)
            results['tests'].append(result)

        results['summary'] = self._summarize(results['tests'])
        return results

    def test_boundary_values(self) -> Dict[str, Any]:
        """Testa valores limites"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'test_type': 'boundary_values',
            'tests': []
        }

        base_url = 'http://localhost:3001/api'

        test_cases = [
            {
                'name': 'Very long string (10000 chars)',
                'endpoint': f'{base_url}/condominios',
                'method': 'POST',
                'data': {'name': 'A' * 10000, 'cnpj': '12345678901234'},
                'expected_status': [400, 422, 413, 403]  # 413 = Payload too large
            },
            {
                'name': 'Negative numbers where positive expected',
                'endpoint': f'{base_url}/unidades',
                'method': 'POST',
                'data': {'numero': -1, 'nome': 'Test'},
                'expected_status': [400, 422, 403]
            },
            {
                'name': 'SQL Injection attempt',
                'endpoint': f'{base_url}/condominios',
                'method': 'POST',
                'data': {'name': "'; DROP TABLE users; --", 'cnpj': '12345'},
                'expected_status': [400, 422, 403]
            },
            {
                'name': 'XSS attempt',
                'endpoint': f'{base_url}/condominios',
                'method': 'POST',
                'data': {'name': '<script>alert("xss")</script>', 'cnpj': '12345'},
                'expected_status': [400, 422, 403, 201]  # API pode aceitar e sanitizar
            },
        ]

        for test in test_cases:
            result = self._run_test_case(test)
            results['tests'].append(result)

        results['summary'] = self._summarize(results['tests'])
        return results

    def test_concurrent_operations(self) -> Dict[str, Any]:
        """Testa operações concorrentes (race conditions)"""
        import asyncio
        import aiohttp

        results = {
            'timestamp': datetime.now().isoformat(),
            'test_type': 'concurrent_operations',
            'tests': []
        }

        # Criar mesmo recurso simultaneamente
        test_result = {
            'name': 'Create same resource 10 times simultaneously',
            'success': False,
            'created_count': 0
        }

        try:
            async def create_resource():
                async with aiohttp.ClientSession() as session:
                    tasks = []
                    for i in range(10):
                        task = session.post(
                            'http://localhost:3001/api/condominios',
                            json={'name': f'Concurrent Test {i}', 'cnpj': f'1234567890123{i}'},
                            timeout=5
                        )
                        tasks.append(task)

                    responses = await asyncio.gather(*tasks, return_exceptions=True)

                    successful = sum(1 for r in responses if not isinstance(r, Exception) and r.status in [200, 201])
                    return successful

            created = asyncio.run(create_resource())
            test_result['created_count'] = created
            test_result['success'] = True
            test_result['message'] = f'{created} resources created simultaneously'

        except Exception as e:
            test_result['error'] = str(e)

        results['tests'].append(test_result)
        results['summary'] = self._summarize(results['tests'])

        return results

    def _run_test_case(self, test: Dict[str, Any]) -> Dict[str, Any]:
        """Executa um test case"""
        result = {
            'name': test['name'],
            'endpoint': test['endpoint'],
            'success': False
        }

        try:
            method = test.get('method', 'GET').lower()
            kwargs = {
                'timeout': 5,
                'json': test.get('data')
            }

            if method == 'get':
                response = requests.get(test['endpoint'], **kwargs)
            elif method == 'post':
                response = requests.post(test['endpoint'], **kwargs)
            elif method == 'put':
                response = requests.put(test['endpoint'], **kwargs)
            elif method == 'delete':
                response = requests.delete(test['endpoint'], **kwargs)
            else:
                response = requests.get(test['endpoint'], **kwargs)

            result['status_code'] = response.status_code
            result['success'] = response.status_code in test.get('expected_status', [200])
            result['response_time'] = response.elapsed.total_seconds()

            if not result['success']:
                result['message'] = f"Expected {test.get('expected_status')}, got {response.status_code}"

        except requests.exceptions.Timeout:
            result['error'] = 'Timeout'
        except Exception as e:
            result['error'] = str(e)

        return result

    def _summarize(self, tests: List[Dict]) -> Dict[str, Any]:
        """Gera resumo dos testes"""
        return {
            'total': len(tests),
            'passed': sum(1 for t in tests if t.get('success')),
            'failed': sum(1 for t in tests if not t.get('success')),
            'pass_rate': (sum(1 for t in tests if t.get('success')) / len(tests) * 100) if tests else 0
        }

    def run_all_tests(self) -> Dict[str, Any]:
        """Executa todos os testes de edge cases"""
        return {
            'timestamp': datetime.now().isoformat(),
            'null_empty_tests': self.test_null_and_empty_values(),
            'invalid_types_tests': self.test_invalid_data_types(),
            'boundary_tests': self.test_boundary_values(),
            'concurrent_tests': self.test_concurrent_operations()
        }


if __name__ == '__main__':
    import json
    tester = EdgeCaseTester({})
    results = tester.run_all_tests()
    print(json.dumps(results, indent=2))
