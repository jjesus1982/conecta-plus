"""
Testes de Carga para a API do Conecta Plus.

Simula 100+ requisições simultâneas para validar:
- Tempo de resposta sob carga
- Throughput
- Taxa de erros
- Comportamento do rate limiting

Uso:
    python tests/test_load.py
    python tests/test_load.py --requests 200 --concurrent 50
"""

import asyncio
import aiohttp
import time
import argparse
import statistics
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
import json
import sys

sys.path.insert(0, '/opt/conecta-plus/services/api-gateway')


@dataclass
class RequestResult:
    """Resultado de uma requisição."""
    endpoint: str
    method: str
    status_code: int
    duration_ms: float
    success: bool
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class LoadTestReport:
    """Relatório do teste de carga."""
    total_requests: int
    successful_requests: int
    failed_requests: int
    rate_limited_requests: int
    total_duration_seconds: float
    requests_per_second: float
    avg_response_time_ms: float
    min_response_time_ms: float
    max_response_time_ms: float
    p50_response_time_ms: float
    p90_response_time_ms: float
    p99_response_time_ms: float
    error_rate_percent: float
    endpoints_tested: List[str]
    status_code_distribution: Dict[int, int]

    def to_dict(self) -> Dict:
        """Converte para dicionário."""
        return {
            'total_requests': self.total_requests,
            'successful_requests': self.successful_requests,
            'failed_requests': self.failed_requests,
            'rate_limited_requests': self.rate_limited_requests,
            'total_duration_seconds': round(self.total_duration_seconds, 2),
            'requests_per_second': round(self.requests_per_second, 2),
            'response_times': {
                'avg_ms': round(self.avg_response_time_ms, 2),
                'min_ms': round(self.min_response_time_ms, 2),
                'max_ms': round(self.max_response_time_ms, 2),
                'p50_ms': round(self.p50_response_time_ms, 2),
                'p90_ms': round(self.p90_response_time_ms, 2),
                'p99_ms': round(self.p99_response_time_ms, 2)
            },
            'error_rate_percent': round(self.error_rate_percent, 2),
            'status_codes': self.status_code_distribution
        }

    def print_report(self):
        """Imprime relatório formatado."""
        print("\n" + "=" * 60)
        print("RELATÓRIO DE TESTE DE CARGA")
        print("=" * 60)

        print(f"\n📊 RESUMO")
        print(f"   Total de requisições: {self.total_requests}")
        print(f"   Requisições com sucesso: {self.successful_requests}")
        print(f"   Requisições com falha: {self.failed_requests}")
        print(f"   Rate limited: {self.rate_limited_requests}")
        print(f"   Taxa de erro: {self.error_rate_percent:.2f}%")

        print(f"\n⏱️  PERFORMANCE")
        print(f"   Duração total: {self.total_duration_seconds:.2f}s")
        print(f"   Throughput: {self.requests_per_second:.2f} req/s")

        print(f"\n📈 TEMPOS DE RESPOSTA")
        print(f"   Média: {self.avg_response_time_ms:.2f}ms")
        print(f"   Mínimo: {self.min_response_time_ms:.2f}ms")
        print(f"   Máximo: {self.max_response_time_ms:.2f}ms")
        print(f"   P50: {self.p50_response_time_ms:.2f}ms")
        print(f"   P90: {self.p90_response_time_ms:.2f}ms")
        print(f"   P99: {self.p99_response_time_ms:.2f}ms")

        print(f"\n📋 STATUS CODES")
        for code, count in sorted(self.status_code_distribution.items()):
            print(f"   {code}: {count} ({count/self.total_requests*100:.1f}%)")

        print("\n" + "=" * 60)

        # Avaliação
        print("\n✅ AVALIAÇÃO")
        passed = True

        if self.p99_response_time_ms > 500:
            print(f"   ❌ P99 > 500ms ({self.p99_response_time_ms:.2f}ms)")
            passed = False
        else:
            print(f"   ✅ P99 < 500ms ({self.p99_response_time_ms:.2f}ms)")

        if self.error_rate_percent > 1:
            print(f"   ❌ Taxa de erro > 1% ({self.error_rate_percent:.2f}%)")
            passed = False
        else:
            print(f"   ✅ Taxa de erro < 1% ({self.error_rate_percent:.2f}%)")

        if self.requests_per_second < 50:
            print(f"   ⚠️  Throughput baixo ({self.requests_per_second:.2f} req/s)")
        else:
            print(f"   ✅ Throughput adequado ({self.requests_per_second:.2f} req/s)")

        print("\n" + "=" * 60)
        if passed:
            print("🎉 TESTE DE CARGA: APROVADO")
        else:
            print("❌ TESTE DE CARGA: REPROVADO")
        print("=" * 60 + "\n")


class LoadTester:
    """Executor de testes de carga."""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        token: str = None
    ):
        self.base_url = base_url
        self.token = token or "test-token"
        self.results: List[RequestResult] = []

        # Endpoints a testar (method, path, payload)
        # Para POST com query params, incluir na URL
        self.endpoints = [
            ("GET", "/health"),
            ("GET", "/api/financeiro/boletos"),
            ("GET", "/api/financeiro/resumo"),
            ("GET", "/api/financeiro/categorias"),
            ("GET", "/api/financeiro/ia/alertas-proativos"),
            ("POST", "/api/financeiro/ia/analisar-sentimento?mensagem=Vou%20pagar%20amanha"),
        ]

    async def make_request(
        self,
        session: aiohttp.ClientSession,
        method: str,
        endpoint: str,
        payload: Dict = None
    ) -> RequestResult:
        """Faz uma requisição e mede o tempo."""
        url = f"{self.base_url}{endpoint}"
        headers = {"Authorization": f"Bearer {self.token}"}

        start_time = time.time()
        error = None
        status_code = 0

        try:
            if method == "GET":
                async with session.get(url, headers=headers, timeout=30) as response:
                    status_code = response.status
                    await response.text()
            elif method == "POST":
                async with session.post(url, headers=headers, json=payload, timeout=30) as response:
                    status_code = response.status
                    await response.text()
        except asyncio.TimeoutError:
            error = "Timeout"
            status_code = 408
        except aiohttp.ClientError as e:
            error = str(e)
            status_code = 0
        except Exception as e:
            error = str(e)
            status_code = 0

        duration_ms = (time.time() - start_time) * 1000
        success = 200 <= status_code < 400

        return RequestResult(
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            duration_ms=duration_ms,
            success=success,
            error=error
        )

    async def run_batch(
        self,
        session: aiohttp.ClientSession,
        num_requests: int
    ) -> List[RequestResult]:
        """Executa um lote de requisições."""
        tasks = []

        for i in range(num_requests):
            # Escolhe endpoint aleatório (round-robin)
            idx = i % len(self.endpoints)
            endpoint_config = self.endpoints[idx]

            if len(endpoint_config) == 2:
                method, endpoint = endpoint_config
                payload = None
            else:
                method, endpoint, payload = endpoint_config

            task = self.make_request(session, method, endpoint, payload)
            tasks.append(task)

        return await asyncio.gather(*tasks)

    async def run_load_test(
        self,
        total_requests: int = 100,
        concurrent_requests: int = 10,
        ramp_up_seconds: int = 0
    ) -> LoadTestReport:
        """
        Executa o teste de carga.

        Args:
            total_requests: Número total de requisições
            concurrent_requests: Requisições simultâneas
            ramp_up_seconds: Tempo para aumentar carga gradualmente
        """
        print(f"\n🚀 Iniciando teste de carga...")
        print(f"   Requisições totais: {total_requests}")
        print(f"   Requisições simultâneas: {concurrent_requests}")
        print(f"   URL base: {self.base_url}")

        start_time = time.time()

        connector = aiohttp.TCPConnector(limit=concurrent_requests)
        async with aiohttp.ClientSession(connector=connector) as session:

            # Executa em batches
            remaining = total_requests
            batch_num = 0

            while remaining > 0:
                batch_size = min(concurrent_requests, remaining)
                batch_num += 1

                print(f"\r   Executando batch {batch_num}... ({total_requests - remaining}/{total_requests})", end="")

                results = await self.run_batch(session, batch_size)
                self.results.extend(results)

                remaining -= batch_size

                # Pequena pausa entre batches
                await asyncio.sleep(0.1)

        total_duration = time.time() - start_time
        print(f"\r   Concluído! {total_requests} requisições em {total_duration:.2f}s")

        return self._generate_report(total_duration)

    def _generate_report(self, total_duration: float) -> LoadTestReport:
        """Gera relatório do teste."""
        if not self.results:
            return None

        durations = [r.duration_ms for r in self.results]
        successful = [r for r in self.results if r.success]
        failed = [r for r in self.results if not r.success]
        rate_limited = [r for r in self.results if r.status_code == 429]

        # Status code distribution
        status_codes = {}
        for r in self.results:
            status_codes[r.status_code] = status_codes.get(r.status_code, 0) + 1

        # Endpoints testados
        endpoints = list(set(r.endpoint for r in self.results))

        # Calcula percentis
        sorted_durations = sorted(durations)
        p50_idx = int(len(sorted_durations) * 0.50)
        p90_idx = int(len(sorted_durations) * 0.90)
        p99_idx = int(len(sorted_durations) * 0.99)

        return LoadTestReport(
            total_requests=len(self.results),
            successful_requests=len(successful),
            failed_requests=len(failed),
            rate_limited_requests=len(rate_limited),
            total_duration_seconds=total_duration,
            requests_per_second=len(self.results) / total_duration,
            avg_response_time_ms=statistics.mean(durations),
            min_response_time_ms=min(durations),
            max_response_time_ms=max(durations),
            p50_response_time_ms=sorted_durations[p50_idx] if p50_idx < len(sorted_durations) else 0,
            p90_response_time_ms=sorted_durations[p90_idx] if p90_idx < len(sorted_durations) else 0,
            p99_response_time_ms=sorted_durations[p99_idx] if p99_idx < len(sorted_durations) else 0,
            error_rate_percent=(len(failed) / len(self.results)) * 100,
            endpoints_tested=endpoints,
            status_code_distribution=status_codes
        )


async def run_stress_test(base_url: str, token: str):
    """Teste de stress: aumenta carga até falhar."""
    print("\n🔥 TESTE DE STRESS")
    print("   Aumentando carga até atingir limite...")

    concurrent_levels = [10, 25, 50, 100, 150, 200]

    for concurrent in concurrent_levels:
        tester = LoadTester(base_url, token)
        report = await tester.run_load_test(
            total_requests=concurrent * 2,
            concurrent_requests=concurrent
        )

        print(f"   Concurrent {concurrent}: {report.requests_per_second:.1f} req/s, P99: {report.p99_response_time_ms:.1f}ms, Erros: {report.error_rate_percent:.1f}%")

        if report.error_rate_percent > 10 or report.p99_response_time_ms > 2000:
            print(f"\n   ⚠️  Limite atingido em {concurrent} requisições simultâneas")
            break


async def run_endpoint_benchmark(base_url: str, token: str):
    """Benchmark individual por endpoint."""
    print("\n📊 BENCHMARK POR ENDPOINT")

    endpoints = [
        ("GET", "/health"),
        ("GET", "/api/financeiro/boletos"),
        ("GET", "/api/financeiro/resumo"),
        ("GET", "/api/financeiro/ia/alertas-proativos"),
        ("POST", "/api/financeiro/ia/analisar-sentimento?mensagem=Teste"),
    ]

    results = []

    for endpoint_config in endpoints:
        if len(endpoint_config) == 2:
            method, endpoint = endpoint_config
            payload = None
        else:
            method, endpoint, payload = endpoint_config

        tester = LoadTester(base_url, token)
        tester.endpoints = [(method, endpoint) if payload is None else (method, endpoint, payload)]

        report = await tester.run_load_test(
            total_requests=50,
            concurrent_requests=10
        )

        results.append({
            'endpoint': endpoint,
            'method': method,
            'avg_ms': report.avg_response_time_ms,
            'p99_ms': report.p99_response_time_ms
        })

        print(f"   {method} {endpoint}")
        print(f"      Avg: {report.avg_response_time_ms:.2f}ms | P99: {report.p99_response_time_ms:.2f}ms")

    # Ordena por tempo médio
    print("\n   📈 Ranking (mais lento primeiro):")
    for i, r in enumerate(sorted(results, key=lambda x: x['avg_ms'], reverse=True)):
        print(f"      {i+1}. {r['method']} {r['endpoint']}: {r['avg_ms']:.2f}ms")


async def main():
    """Função principal."""
    parser = argparse.ArgumentParser(description='Teste de Carga da API Conecta Plus')
    parser.add_argument('--url', default='http://localhost:8000', help='URL base da API')
    parser.add_argument('--token', default='test-token', help='Token de autenticação')
    parser.add_argument('--requests', type=int, default=100, help='Número total de requisições')
    parser.add_argument('--concurrent', type=int, default=10, help='Requisições simultâneas')
    parser.add_argument('--stress', action='store_true', help='Executa teste de stress')
    parser.add_argument('--benchmark', action='store_true', help='Benchmark por endpoint')
    parser.add_argument('--output', help='Salva resultado em arquivo JSON')

    args = parser.parse_args()

    if args.stress:
        await run_stress_test(args.url, args.token)
        return

    if args.benchmark:
        await run_endpoint_benchmark(args.url, args.token)
        return

    # Teste de carga padrão
    tester = LoadTester(args.url, args.token)
    report = await tester.run_load_test(
        total_requests=args.requests,
        concurrent_requests=args.concurrent
    )

    report.print_report()

    if args.output:
        with open(args.output, 'w') as f:
            json.dump(report.to_dict(), f, indent=2)
        print(f"\n📁 Resultado salvo em: {args.output}")


if __name__ == '__main__':
    asyncio.run(main())
