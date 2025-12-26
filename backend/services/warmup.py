"""
Conecta Plus - Warmup Service
==============================
Servico de warmup para eliminar cold start.

Funcionalidades:
- Pre-aquece pool de conexoes do banco de dados
- Faz ping no Redis para garantir conectividade
- Carrega cache inicial com dados frequentes
- Faz self-request para endpoints criticos

Uso:
    from .services.warmup import WarmupService

    async def lifespan(app: FastAPI):
        warmup = WarmupService()
        await warmup.run()
        yield
"""

import os
import time
import asyncio
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class WarmupResult:
    """Resultado de uma operacao de warmup."""
    component: str
    success: bool
    duration_ms: float
    details: Optional[str] = None
    error: Optional[str] = None


@dataclass
class WarmupReport:
    """Relatorio completo do warmup."""
    start_time: datetime
    end_time: Optional[datetime] = None
    total_duration_ms: float = 0.0
    results: List[WarmupResult] = field(default_factory=list)
    success: bool = False

    def add_result(self, result: WarmupResult):
        self.results.append(result)

    def finalize(self):
        self.end_time = datetime.utcnow()
        self.total_duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
        # Sucesso se todos os componentes criticos passaram
        critical = ["database", "redis"]
        self.success = all(
            r.success for r in self.results
            if r.component in critical
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "total_duration_ms": round(self.total_duration_ms, 2),
            "success": self.success,
            "results": [
                {
                    "component": r.component,
                    "success": r.success,
                    "duration_ms": round(r.duration_ms, 2),
                    "details": r.details,
                    "error": r.error
                }
                for r in self.results
            ]
        }


class WarmupService:
    """
    Servico de warmup para eliminar cold start.

    Executa durante o startup da aplicacao para:
    1. Pre-aquecer conexoes do pool do banco
    2. Verificar conectividade com Redis
    3. Carregar cache inicial
    4. Aquecer endpoints criticos
    """

    def __init__(
        self,
        db_pool_warmup_connections: int = 3,
        enable_self_request: bool = True,
        enable_cache_preload: bool = True,
        timeout_seconds: float = 30.0
    ):
        """
        Inicializa o servico de warmup.

        Args:
            db_pool_warmup_connections: Numero de conexoes para aquecer no pool
            enable_self_request: Se deve fazer self-request para /health
            enable_cache_preload: Se deve pre-carregar cache inicial
            timeout_seconds: Timeout total para o warmup
        """
        self.db_pool_warmup_connections = db_pool_warmup_connections
        self.enable_self_request = enable_self_request
        self.enable_cache_preload = enable_cache_preload
        self.timeout_seconds = timeout_seconds
        self._report: Optional[WarmupReport] = None

    @property
    def report(self) -> Optional[WarmupReport]:
        """Retorna o relatorio do ultimo warmup."""
        return self._report

    async def run(self) -> WarmupReport:
        """
        Executa o warmup completo.

        Returns:
            WarmupReport com resultados de cada componente
        """
        self._report = WarmupReport(start_time=datetime.utcnow())

        logger.info("=" * 50)
        logger.info("Iniciando warmup do sistema...")
        logger.info("=" * 50)

        try:
            # Executa warmup com timeout
            await asyncio.wait_for(
                self._run_warmup(),
                timeout=self.timeout_seconds
            )
        except asyncio.TimeoutError:
            logger.warning(f"Warmup timeout apos {self.timeout_seconds}s")
            self._report.add_result(WarmupResult(
                component="timeout",
                success=False,
                duration_ms=self.timeout_seconds * 1000,
                error=f"Warmup timeout apos {self.timeout_seconds}s"
            ))
        except Exception as e:
            logger.error(f"Erro durante warmup: {e}")
            self._report.add_result(WarmupResult(
                component="general",
                success=False,
                duration_ms=0,
                error=str(e)
            ))

        self._report.finalize()

        # Log do resultado
        status = "SUCCESS" if self._report.success else "PARTIAL"
        logger.info("=" * 50)
        logger.info(f"Warmup {status} em {self._report.total_duration_ms:.2f}ms")
        for r in self._report.results:
            status_icon = "[OK]" if r.success else "[FAIL]"
            logger.info(f"  {status_icon} {r.component}: {r.duration_ms:.2f}ms")
            if r.error:
                logger.warning(f"       Erro: {r.error}")
        logger.info("=" * 50)

        return self._report

    async def _run_warmup(self):
        """Executa as etapas do warmup."""
        # 1. Aquecer pool de conexoes do banco
        result = await self._warmup_database()
        self._report.add_result(result)

        # 2. Verificar e aquecer Redis
        result = await self._warmup_redis()
        self._report.add_result(result)

        # 3. Pre-carregar cache (se habilitado)
        if self.enable_cache_preload:
            result = await self._warmup_cache()
            self._report.add_result(result)

        # 4. Self-request para /health (se habilitado)
        if self.enable_self_request:
            result = await self._warmup_self_request()
            self._report.add_result(result)

    async def _warmup_database(self) -> WarmupResult:
        """Aquece o pool de conexoes do banco de dados."""
        start = time.time()
        connections_warmed = 0

        try:
            from ..database import SessionLocal, engine
            from sqlalchemy import text

            # Criar multiplas conexoes para aquecer o pool
            sessions = []
            for i in range(self.db_pool_warmup_connections):
                try:
                    session = SessionLocal()
                    # Executa query simples para garantir conexao ativa
                    session.execute(text("SELECT 1"))
                    sessions.append(session)
                    connections_warmed += 1
                except Exception as e:
                    logger.warning(f"Falha ao aquecer conexao {i+1}: {e}")

            # Fecha as sessoes (retorna ao pool)
            for session in sessions:
                try:
                    session.close()
                except Exception:
                    pass

            duration_ms = (time.time() - start) * 1000

            # Verifica estatisticas do pool
            pool_status = engine.pool.status()

            return WarmupResult(
                component="database",
                success=connections_warmed > 0,
                duration_ms=duration_ms,
                details=f"{connections_warmed}/{self.db_pool_warmup_connections} conexoes aquecidas. Pool: {pool_status}"
            )

        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            logger.error(f"Erro no warmup do banco: {e}")
            return WarmupResult(
                component="database",
                success=False,
                duration_ms=duration_ms,
                error=str(e)
            )

    async def _warmup_redis(self) -> WarmupResult:
        """Verifica e aquece conexao com Redis."""
        start = time.time()

        try:
            import redis

            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
            client = redis.from_url(redis_url, socket_timeout=5)

            # Ping para verificar conexao
            client.ping()

            # Executar algumas operacoes para aquecer
            test_key = "warmup:test"
            client.setex(test_key, 60, "warmup_value")
            client.get(test_key)
            client.delete(test_key)

            # Obter info do servidor
            info = client.info("server")
            redis_version = info.get("redis_version", "unknown")

            duration_ms = (time.time() - start) * 1000

            return WarmupResult(
                component="redis",
                success=True,
                duration_ms=duration_ms,
                details=f"Redis v{redis_version} conectado"
            )

        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            logger.warning(f"Erro no warmup do Redis: {e}")
            return WarmupResult(
                component="redis",
                success=False,
                duration_ms=duration_ms,
                error=str(e)
            )

    async def _warmup_cache(self) -> WarmupResult:
        """Pre-carrega dados frequentes no cache."""
        start = time.time()
        items_cached = 0

        try:
            import redis
            import json

            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
            client = redis.from_url(redis_url, socket_timeout=5)

            # Dados frequentes para pre-carregar
            cache_items = {
                "warmup:status": json.dumps({
                    "last_warmup": datetime.utcnow().isoformat(),
                    "version": "2.0.0"
                }),
                "config:app": json.dumps({
                    "name": "Conecta Plus",
                    "maintenance_mode": False
                }),
                "cache:roles": json.dumps({
                    "admin": ["*"],
                    "sindico": ["read", "write", "manage"],
                    "morador": ["read", "limited_write"]
                })
            }

            for key, value in cache_items.items():
                try:
                    client.setex(key, 7200, value)  # 2 horas TTL
                    items_cached += 1
                except Exception as e:
                    logger.warning(f"Falha ao cachear {key}: {e}")

            duration_ms = (time.time() - start) * 1000

            return WarmupResult(
                component="cache",
                success=items_cached > 0,
                duration_ms=duration_ms,
                details=f"{items_cached}/{len(cache_items)} itens cacheados"
            )

        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            logger.warning(f"Erro no warmup do cache: {e}")
            return WarmupResult(
                component="cache",
                success=False,
                duration_ms=duration_ms,
                error=str(e)
            )

    async def _warmup_self_request(self) -> WarmupResult:
        """Faz self-request para aquecer rotas."""
        start = time.time()

        try:
            import httpx

            port = int(os.getenv('PORT', '8000'))
            base_url = f"http://127.0.0.1:{port}"

            async with httpx.AsyncClient(timeout=10.0) as client:
                # Tenta fazer request para /health
                # Nota: Isso so funciona se o servidor ja estiver rodando
                # Em lifespan, pode falhar na primeira vez
                try:
                    response = await client.get(f"{base_url}/health")
                    status = response.status_code

                    duration_ms = (time.time() - start) * 1000

                    if status == 200:
                        return WarmupResult(
                            component="self_request",
                            success=True,
                            duration_ms=duration_ms,
                            details=f"/health retornou {status}"
                        )
                    else:
                        return WarmupResult(
                            component="self_request",
                            success=False,
                            duration_ms=duration_ms,
                            details=f"/health retornou {status}"
                        )

                except httpx.ConnectError:
                    # Servidor ainda nao esta pronto - isso e esperado no lifespan
                    duration_ms = (time.time() - start) * 1000
                    return WarmupResult(
                        component="self_request",
                        success=True,  # Nao e erro critico
                        duration_ms=duration_ms,
                        details="Servidor ainda nao disponivel (esperado no startup)"
                    )

        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            logger.warning(f"Erro no self-request: {e}")
            return WarmupResult(
                component="self_request",
                success=True,  # Nao e erro critico
                duration_ms=duration_ms,
                error=str(e)
            )


# Instancia global para acesso ao ultimo relatorio
_warmup_service: Optional[WarmupService] = None


def get_warmup_service() -> WarmupService:
    """Retorna a instancia do servico de warmup."""
    global _warmup_service
    if _warmup_service is None:
        _warmup_service = WarmupService()
    return _warmup_service


async def run_warmup(
    db_connections: int = 3,
    enable_self_request: bool = False,  # Desabilitado por default no lifespan
    enable_cache: bool = True,
    timeout: float = 30.0
) -> WarmupReport:
    """
    Funcao helper para executar warmup.

    Args:
        db_connections: Numero de conexoes do banco para aquecer
        enable_self_request: Se deve fazer self-request
        enable_cache: Se deve pre-carregar cache
        timeout: Timeout em segundos

    Returns:
        WarmupReport com resultados
    """
    global _warmup_service
    _warmup_service = WarmupService(
        db_pool_warmup_connections=db_connections,
        enable_self_request=enable_self_request,
        enable_cache_preload=enable_cache,
        timeout_seconds=timeout
    )
    return await _warmup_service.run()


def get_last_warmup_report() -> Optional[Dict[str, Any]]:
    """Retorna o relatorio do ultimo warmup em formato dict."""
    if _warmup_service and _warmup_service.report:
        return _warmup_service.report.to_dict()
    return None
