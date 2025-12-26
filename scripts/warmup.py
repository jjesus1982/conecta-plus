#!/usr/bin/env python3
"""
Conecta Plus - Cache Warmup Script
==================================
Script para pre-carregar dados em cache Redis e aquecer endpoints criticos.

Uso:
    python warmup.py [--verbose] [--endpoints-only] [--cache-only]

Opcoes:
    --verbose       Mostra detalhes de cada requisicao
    --endpoints-only    Apenas faz warmup dos endpoints (sem cache)
    --cache-only        Apenas pre-carrega cache (sem endpoints)
"""

import os
import sys
import json
import time
import logging
import argparse
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

# Configuracao de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/opt/conecta-plus/logs/warmup.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)

# Tentativa de importar dependencias
try:
    import httpx
    import redis.asyncio as redis
except ImportError as e:
    logger.error(f"Dependencia nao encontrada: {e}")
    logger.info("Instalando dependencias...")
    os.system("pip install httpx redis")
    import httpx
    import redis.asyncio as redis


@dataclass
class WarmupConfig:
    """Configuracao do warmup."""
    backend_url: str = os.getenv("BACKEND_URL", "http://localhost:8000")
    redis_url: str = os.getenv("REDIS_URL", "redis://:redis_secret_2024@localhost:6379/0")
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    parallel_requests: int = 5


@dataclass
class WarmupResult:
    """Resultado de uma operacao de warmup."""
    endpoint: str
    success: bool
    response_time: float
    status_code: Optional[int] = None
    error: Optional[str] = None
    cached: bool = False


class CacheWarmer:
    """Classe responsavel pelo warmup de cache Redis."""

    def __init__(self, config: WarmupConfig):
        self.config = config
        self.redis_client: Optional[redis.Redis] = None

    async def connect(self) -> bool:
        """Conecta ao Redis."""
        try:
            self.redis_client = redis.from_url(
                self.config.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis_client.ping()
            logger.info("Conectado ao Redis com sucesso")
            return True
        except Exception as e:
            logger.error(f"Erro ao conectar ao Redis: {e}")
            return False

    async def disconnect(self):
        """Desconecta do Redis."""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Desconectado do Redis")

    async def warm_cache_key(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Pre-carrega um valor no cache."""
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            await self.redis_client.setex(key, ttl, value)
            logger.debug(f"Cache key '{key}' carregada com TTL {ttl}s")
            return True
        except Exception as e:
            logger.error(f"Erro ao carregar cache key '{key}': {e}")
            return False

    async def warm_common_cache(self) -> Dict[str, bool]:
        """Pre-carrega dados comuns no cache."""
        results = {}

        # Dados comuns para cache
        cache_items = {
            # Configuracoes do sistema
            "config:system": {
                "app_name": "Conecta Plus",
                "version": "1.0.0",
                "maintenance_mode": False,
                "features": {
                    "notifications": True,
                    "ai_assistant": True,
                    "reports": True
                }
            },
            # Cache de permissoes padrao
            "permissions:roles": {
                "admin": ["*"],
                "manager": ["read", "write", "manage_users"],
                "user": ["read", "write"],
                "guest": ["read"]
            },
            # Status do sistema
            "status:last_check": datetime.now().isoformat(),
            "status:healthy": True,
            # Rate limiting config
            "ratelimit:config": {
                "default": {"requests": 100, "window": 60},
                "auth": {"requests": 10, "window": 60},
                "api": {"requests": 1000, "window": 60}
            }
        }

        for key, value in cache_items.items():
            success = await self.warm_cache_key(key, value, ttl=7200)
            results[key] = success

        return results


class EndpointWarmer:
    """Classe responsavel pelo warmup de endpoints HTTP."""

    def __init__(self, config: WarmupConfig):
        self.config = config
        self.client: Optional[httpx.AsyncClient] = None
        self.service_token: Optional[str] = None

    async def connect(self) -> bool:
        """Inicializa o cliente HTTP."""
        try:
            self.client = httpx.AsyncClient(
                base_url=self.config.backend_url,
                timeout=self.config.timeout,
                follow_redirects=True
            )
            logger.info(f"Cliente HTTP inicializado para {self.config.backend_url}")
            return True
        except Exception as e:
            logger.error(f"Erro ao inicializar cliente HTTP: {e}")
            return False

    async def disconnect(self):
        """Fecha o cliente HTTP."""
        if self.client:
            await self.client.aclose()
            logger.info("Cliente HTTP fechado")

    async def get_service_token(self) -> Optional[str]:
        """Obtem token de servico para endpoints autenticados."""
        try:
            # Tenta autenticar com credenciais de servico
            response = await self.client.post(
                "/api/v1/auth/login",
                json={
                    "email": os.getenv("SERVICE_EMAIL", "admin@conectaplus.com.br"),
                    "password": os.getenv("SERVICE_PASSWORD", "admin123")
                }
            )
            if response.status_code == 200:
                data = response.json()
                self.service_token = data.get("access_token")
                logger.info("Token de servico obtido com sucesso")
                return self.service_token
        except Exception as e:
            logger.warning(f"Nao foi possivel obter token de servico: {e}")
        return None

    async def warm_endpoint(self, endpoint: str, method: str = "GET",
                            auth_required: bool = False,
                            data: Optional[Dict] = None) -> WarmupResult:
        """Faz warmup de um endpoint especifico."""
        start_time = time.time()
        headers = {}

        if auth_required and self.service_token:
            headers["Authorization"] = f"Bearer {self.service_token}"

        for attempt in range(self.config.max_retries):
            try:
                if method.upper() == "GET":
                    response = await self.client.get(endpoint, headers=headers)
                elif method.upper() == "POST":
                    response = await self.client.post(endpoint, headers=headers, json=data)
                else:
                    response = await self.client.request(method, endpoint, headers=headers, json=data)

                elapsed = time.time() - start_time

                return WarmupResult(
                    endpoint=endpoint,
                    success=response.status_code < 400,
                    response_time=elapsed,
                    status_code=response.status_code,
                    cached=response.headers.get("X-Cache") == "HIT"
                )

            except Exception as e:
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay)
                else:
                    elapsed = time.time() - start_time
                    return WarmupResult(
                        endpoint=endpoint,
                        success=False,
                        response_time=elapsed,
                        error=str(e)
                    )

        # Fallback (nao deve chegar aqui)
        return WarmupResult(
            endpoint=endpoint,
            success=False,
            response_time=time.time() - start_time,
            error="Max retries exceeded"
        )

    async def warm_all_endpoints(self) -> List[WarmupResult]:
        """Faz warmup de todos os endpoints criticos."""

        # Lista de endpoints para warmup
        endpoints = [
            # Health checks (sem auth)
            {"endpoint": "/health", "auth": False},
            {"endpoint": "/api/v1/health", "auth": False},
            {"endpoint": "/metrics", "auth": False},

            # Endpoints publicos
            {"endpoint": "/api/v1/", "auth": False},

            # Endpoints autenticados
            {"endpoint": "/api/v1/dashboard/resumo", "auth": True},
            {"endpoint": "/api/v1/condominios/", "auth": True},
            {"endpoint": "/api/v1/moradores/", "auth": True},
            {"endpoint": "/api/v1/unidades/", "auth": True},
            {"endpoint": "/api/v1/areas-comuns/", "auth": True},
            {"endpoint": "/api/v1/reservas/", "auth": True},
            {"endpoint": "/api/v1/ocorrencias/", "auth": True},
            {"endpoint": "/api/v1/financeiro/", "auth": True},
            {"endpoint": "/api/v1/assembleias/", "auth": True},
            {"endpoint": "/api/v1/comunicados/", "auth": True},
            {"endpoint": "/api/v1/auth/me", "auth": True},

            # Endpoints de inteligencia (Q2)
            {"endpoint": "/api/v1/inteligencia/insights", "auth": True},
            {"endpoint": "/api/v1/inteligencia/alertas", "auth": True},
            {"endpoint": "/api/v1/guardian/status", "auth": True},
        ]

        results = []

        # Primeiro, tenta obter token para endpoints autenticados
        await self.get_service_token()

        # Processa endpoints em paralelo (com limite)
        semaphore = asyncio.Semaphore(self.config.parallel_requests)

        async def process_with_semaphore(ep_config):
            async with semaphore:
                return await self.warm_endpoint(
                    ep_config["endpoint"],
                    auth_required=ep_config.get("auth", False)
                )

        tasks = [process_with_semaphore(ep) for ep in endpoints]
        results = await asyncio.gather(*tasks)

        return results


class WarmupOrchestrator:
    """Orquestrador principal do warmup."""

    def __init__(self, config: Optional[WarmupConfig] = None):
        self.config = config or WarmupConfig()
        self.cache_warmer = CacheWarmer(self.config)
        self.endpoint_warmer = EndpointWarmer(self.config)

    async def run_full_warmup(self,
                              endpoints: bool = True,
                              cache: bool = True,
                              verbose: bool = False) -> Dict[str, Any]:
        """Executa warmup completo."""

        logger.info("=" * 60)
        logger.info("Iniciando Conecta Plus Cache Warmup")
        logger.info(f"Timestamp: {datetime.now().isoformat()}")
        logger.info("=" * 60)

        start_time = time.time()
        results = {
            "timestamp": datetime.now().isoformat(),
            "cache": {},
            "endpoints": [],
            "summary": {}
        }

        # Warmup de cache
        if cache:
            logger.info("\n[1/2] Iniciando warmup de cache Redis...")
            if await self.cache_warmer.connect():
                cache_results = await self.cache_warmer.warm_common_cache()
                results["cache"] = cache_results

                success_count = sum(1 for v in cache_results.values() if v)
                total_count = len(cache_results)
                logger.info(f"Cache warmup: {success_count}/{total_count} keys carregadas")

                if verbose:
                    for key, success in cache_results.items():
                        status = "OK" if success else "FALHOU"
                        logger.info(f"  - {key}: {status}")

                await self.cache_warmer.disconnect()
            else:
                logger.warning("Skipping cache warmup - Redis nao disponivel")

        # Warmup de endpoints
        if endpoints:
            logger.info("\n[2/2] Iniciando warmup de endpoints...")
            if await self.endpoint_warmer.connect():
                endpoint_results = await self.endpoint_warmer.warm_all_endpoints()
                results["endpoints"] = [
                    {
                        "endpoint": r.endpoint,
                        "success": r.success,
                        "response_time": r.response_time,
                        "status_code": r.status_code,
                        "cached": r.cached,
                        "error": r.error
                    }
                    for r in endpoint_results
                ]

                success_count = sum(1 for r in endpoint_results if r.success)
                total_count = len(endpoint_results)
                avg_time = sum(r.response_time for r in endpoint_results) / total_count if total_count > 0 else 0

                logger.info(f"Endpoint warmup: {success_count}/{total_count} endpoints OK")
                logger.info(f"Tempo medio de resposta: {avg_time:.3f}s")

                if verbose:
                    for r in endpoint_results:
                        status = "OK" if r.success else "FALHOU"
                        cache_status = " (cached)" if r.cached else ""
                        error_msg = f" - {r.error}" if r.error else ""
                        logger.info(f"  - {r.endpoint}: {status} ({r.response_time:.3f}s){cache_status}{error_msg}")

                await self.endpoint_warmer.disconnect()
            else:
                logger.warning("Skipping endpoint warmup - Backend nao disponivel")

        # Resumo final
        total_time = time.time() - start_time
        results["summary"] = {
            "total_time": total_time,
            "cache_success": sum(1 for v in results["cache"].values() if v) if results["cache"] else 0,
            "cache_total": len(results["cache"]) if results["cache"] else 0,
            "endpoints_success": sum(1 for e in results["endpoints"] if e["success"]),
            "endpoints_total": len(results["endpoints"]),
            "avg_response_time": sum(e["response_time"] for e in results["endpoints"]) / len(results["endpoints"]) if results["endpoints"] else 0
        }

        logger.info("\n" + "=" * 60)
        logger.info("Warmup Completo!")
        logger.info(f"Tempo total: {total_time:.2f}s")
        logger.info(f"Cache: {results['summary']['cache_success']}/{results['summary']['cache_total']}")
        logger.info(f"Endpoints: {results['summary']['endpoints_success']}/{results['summary']['endpoints_total']}")
        logger.info("=" * 60)

        return results


async def main():
    """Funcao principal."""
    parser = argparse.ArgumentParser(description="Conecta Plus Cache Warmup")
    parser.add_argument("--verbose", "-v", action="store_true", help="Modo verbose")
    parser.add_argument("--endpoints-only", action="store_true", help="Apenas endpoints")
    parser.add_argument("--cache-only", action="store_true", help="Apenas cache")
    parser.add_argument("--backend-url", default=None, help="URL do backend")
    parser.add_argument("--redis-url", default=None, help="URL do Redis")

    args = parser.parse_args()

    # Configuracao
    config = WarmupConfig()
    if args.backend_url:
        config.backend_url = args.backend_url
    if args.redis_url:
        config.redis_url = args.redis_url

    # Determina o que executar
    run_endpoints = not args.cache_only
    run_cache = not args.endpoints_only

    # Executa warmup
    orchestrator = WarmupOrchestrator(config)
    results = await orchestrator.run_full_warmup(
        endpoints=run_endpoints,
        cache=run_cache,
        verbose=args.verbose
    )

    # Salva resultados
    results_file = "/opt/conecta-plus/logs/warmup_results.json"
    try:
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2, default=str)
        logger.info(f"Resultados salvos em {results_file}")
    except Exception as e:
        logger.warning(f"Nao foi possivel salvar resultados: {e}")

    # Retorna codigo de saida baseado no sucesso
    if results["summary"]["endpoints_success"] < results["summary"]["endpoints_total"] * 0.5:
        logger.warning("Menos de 50% dos endpoints responderam com sucesso")
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
