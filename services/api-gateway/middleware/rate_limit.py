"""
Conecta Plus - Middleware de Rate Limiting
Proteção contra abuso de API
"""

import os
import time
import asyncio
from typing import Optional, Dict, Callable, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import defaultdict
from functools import wraps

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse


@dataclass
class RateLimitConfig:
    """Configuração de rate limit"""
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    requests_per_day: int = 10000

    # Limites específicos por endpoint
    boleto_create_per_minute: int = 10
    boleto_create_per_hour: int = 100

    cobranca_per_minute: int = 20
    cobranca_per_hour: int = 200

    export_per_minute: int = 5
    export_per_hour: int = 20

    # Burst permitido
    burst_size: int = 10

    # Whitelist de IPs
    whitelist_ips: list = None

    def __post_init__(self):
        self.whitelist_ips = self.whitelist_ips or ['127.0.0.1', '::1']


@dataclass
class RateLimitEntry:
    """Entrada de rate limit para um cliente"""
    minute_count: int = 0
    hour_count: int = 0
    day_count: int = 0
    minute_reset: float = 0
    hour_reset: float = 0
    day_reset: float = 0
    tokens: float = 0
    last_update: float = 0


class RateLimiter:
    """
    Rate Limiter com múltiplas janelas de tempo

    Implementa:
    - Limites por minuto/hora/dia
    - Limites por endpoint
    - Token bucket para burst
    - Whitelist de IPs
    """

    def __init__(self, config: RateLimitConfig = None):
        self.config = config or RateLimitConfig()
        self._entries: Dict[str, RateLimitEntry] = defaultdict(RateLimitEntry)
        self._endpoint_entries: Dict[str, Dict[str, RateLimitEntry]] = defaultdict(lambda: defaultdict(RateLimitEntry))

        # Configura Redis se disponível
        self._redis = None
        self._use_redis = os.getenv('RATE_LIMIT_REDIS', 'false').lower() == 'true'

    def _get_client_id(self, request: Request) -> str:
        """Obtém identificador único do cliente"""
        # Tenta pegar IP real se estiver atrás de proxy
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            ip = forwarded_for.split(',')[0].strip()
        else:
            ip = request.client.host if request.client else 'unknown'

        # Se autenticado, usa user_id
        if hasattr(request.state, 'user') and request.state.user:
            user_id = getattr(request.state.user, 'id', None)
            if user_id:
                return f"user:{user_id}"

        return f"ip:{ip}"

    def _get_endpoint_key(self, request: Request) -> str:
        """Obtém chave do endpoint para limites específicos"""
        path = request.url.path
        method = request.method

        # Agrupa endpoints similares
        if '/boletos' in path and method == 'POST':
            return 'boleto_create'
        elif '/cobranca' in path:
            return 'cobranca'
        elif '/exportar' in path or '/relatorios' in path:
            return 'export'

        return 'default'

    def _get_limits(self, endpoint_key: str) -> Tuple[int, int, int]:
        """Retorna limites para o endpoint"""
        if endpoint_key == 'boleto_create':
            return (
                self.config.boleto_create_per_minute,
                self.config.boleto_create_per_hour,
                self.config.requests_per_day
            )
        elif endpoint_key == 'cobranca':
            return (
                self.config.cobranca_per_minute,
                self.config.cobranca_per_hour,
                self.config.requests_per_day
            )
        elif endpoint_key == 'export':
            return (
                self.config.export_per_minute,
                self.config.export_per_hour,
                self.config.requests_per_day
            )

        return (
            self.config.requests_per_minute,
            self.config.requests_per_hour,
            self.config.requests_per_day
        )

    def _check_and_update(
        self,
        entry: RateLimitEntry,
        limits: Tuple[int, int, int]
    ) -> Tuple[bool, str, int]:
        """
        Verifica e atualiza contadores

        Returns:
            Tupla (permitido, motivo, retry_after_seconds)
        """
        now = time.time()
        minute_limit, hour_limit, day_limit = limits

        # Reset janelas expiradas
        if now >= entry.minute_reset:
            entry.minute_count = 0
            entry.minute_reset = now + 60

        if now >= entry.hour_reset:
            entry.hour_count = 0
            entry.hour_reset = now + 3600

        if now >= entry.day_reset:
            entry.day_count = 0
            entry.day_reset = now + 86400

        # Verifica limites
        if entry.minute_count >= minute_limit:
            retry_after = int(entry.minute_reset - now) + 1
            return False, "rate_limit_minute", retry_after

        if entry.hour_count >= hour_limit:
            retry_after = int(entry.hour_reset - now) + 1
            return False, "rate_limit_hour", retry_after

        if entry.day_count >= day_limit:
            retry_after = int(entry.day_reset - now) + 1
            return False, "rate_limit_day", retry_after

        # Atualiza contadores
        entry.minute_count += 1
        entry.hour_count += 1
        entry.day_count += 1
        entry.last_update = now

        return True, "", 0

    def _check_token_bucket(self, entry: RateLimitEntry) -> Tuple[bool, int]:
        """
        Verifica token bucket para burst

        Returns:
            Tupla (permitido, retry_after_seconds)
        """
        now = time.time()
        burst_size = self.config.burst_size
        refill_rate = 1.0  # 1 token por segundo

        # Calcula tokens acumulados
        elapsed = now - entry.last_update
        entry.tokens = min(burst_size, entry.tokens + elapsed * refill_rate)
        entry.last_update = now

        if entry.tokens < 1:
            retry_after = int((1 - entry.tokens) / refill_rate) + 1
            return False, retry_after

        entry.tokens -= 1
        return True, 0

    async def check(self, request: Request) -> Tuple[bool, Optional[JSONResponse]]:
        """
        Verifica se requisição é permitida

        Returns:
            Tupla (permitido, resposta_de_erro_ou_None)
        """
        client_id = self._get_client_id(request)

        # Verifica whitelist
        ip = client_id.replace('ip:', '').replace('user:', '')
        if ip in self.config.whitelist_ips:
            return True, None

        endpoint_key = self._get_endpoint_key(request)
        limits = self._get_limits(endpoint_key)

        # Obtém ou cria entrada
        entry = self._entries[client_id]

        # Verifica limites
        allowed, reason, retry_after = self._check_and_update(entry, limits)

        if not allowed:
            return False, self._create_error_response(reason, retry_after, client_id)

        return True, None

    def _create_error_response(
        self,
        reason: str,
        retry_after: int,
        client_id: str
    ) -> JSONResponse:
        """Cria resposta de erro de rate limit"""
        messages = {
            'rate_limit_minute': 'Limite de requisições por minuto excedido',
            'rate_limit_hour': 'Limite de requisições por hora excedido',
            'rate_limit_day': 'Limite de requisições diário excedido',
            'rate_limit_burst': 'Muitas requisições simultâneas'
        }

        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                'error': 'rate_limit_exceeded',
                'message': messages.get(reason, 'Limite de requisições excedido'),
                'retry_after': retry_after,
                'detail': {
                    'reason': reason,
                    'client_id': client_id[:20] + '...' if len(client_id) > 20 else client_id
                }
            },
            headers={
                'Retry-After': str(retry_after),
                'X-RateLimit-Reset': str(int(time.time()) + retry_after)
            }
        )

    def get_remaining(self, request: Request) -> Dict[str, int]:
        """Retorna limites restantes para o cliente"""
        client_id = self._get_client_id(request)
        entry = self._entries.get(client_id)

        if not entry:
            return {
                'minute_remaining': self.config.requests_per_minute,
                'hour_remaining': self.config.requests_per_hour,
                'day_remaining': self.config.requests_per_day
            }

        endpoint_key = self._get_endpoint_key(request)
        limits = self._get_limits(endpoint_key)
        minute_limit, hour_limit, day_limit = limits

        return {
            'minute_remaining': max(0, minute_limit - entry.minute_count),
            'hour_remaining': max(0, hour_limit - entry.hour_count),
            'day_remaining': max(0, day_limit - entry.day_count)
        }


# Instância global
rate_limiter = RateLimiter()


# ==================== MIDDLEWARE FASTAPI ====================

async def rate_limit_middleware(request: Request, call_next):
    """
    Middleware de rate limiting para FastAPI

    Uso no main.py:
        app.middleware("http")(rate_limit_middleware)
    """
    # Ignora health check
    if request.url.path in ['/health', '/health/', '/api/health']:
        return await call_next(request)

    # Verifica rate limit
    allowed, error_response = await rate_limiter.check(request)

    if not allowed:
        return error_response

    # Processa requisição
    response = await call_next(request)

    # Adiciona headers de rate limit
    remaining = rate_limiter.get_remaining(request)
    response.headers['X-RateLimit-Remaining-Minute'] = str(remaining['minute_remaining'])
    response.headers['X-RateLimit-Remaining-Hour'] = str(remaining['hour_remaining'])

    return response


# ==================== DECORATOR PARA RATE LIMIT ====================

def rate_limit(
    requests_per_minute: int = 60,
    requests_per_hour: int = 1000
):
    """
    Decorator para aplicar rate limit a endpoints específicos

    Uso:
        @app.get('/api/dados')
        @rate_limit(requests_per_minute=10)
        async def get_dados():
            ...
    """
    def decorator(func):
        # Cria limiter específico para este endpoint
        config = RateLimitConfig(
            requests_per_minute=requests_per_minute,
            requests_per_hour=requests_per_hour
        )
        limiter = RateLimiter(config)

        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Tenta extrair request dos argumentos
            request = kwargs.get('request')
            if not request:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            if request:
                allowed, error_response = await limiter.check(request)
                if not allowed:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Rate limit exceeded"
                    )

            return await func(*args, **kwargs)

        return wrapper
    return decorator


# ==================== CONFIGURAÇÃO POR AMBIENTE ====================

def get_rate_limit_config() -> RateLimitConfig:
    """Retorna configuração de rate limit baseada no ambiente"""
    env = os.getenv('ENVIRONMENT', 'development')

    if env == 'production':
        return RateLimitConfig(
            requests_per_minute=60,
            requests_per_hour=1000,
            requests_per_day=10000,
            boleto_create_per_minute=10,
            boleto_create_per_hour=100,
            cobranca_per_minute=20,
            cobranca_per_hour=200,
            export_per_minute=5,
            export_per_hour=20,
            burst_size=10
        )
    elif env == 'staging':
        return RateLimitConfig(
            requests_per_minute=120,
            requests_per_hour=2000,
            requests_per_day=20000,
            boleto_create_per_minute=20,
            boleto_create_per_hour=200,
            cobranca_per_minute=40,
            cobranca_per_hour=400,
            export_per_minute=10,
            export_per_hour=40,
            burst_size=20
        )
    else:
        # Development - limites mais altos
        return RateLimitConfig(
            requests_per_minute=1000,
            requests_per_hour=10000,
            requests_per_day=100000,
            boleto_create_per_minute=100,
            boleto_create_per_hour=1000,
            cobranca_per_minute=200,
            cobranca_per_hour=2000,
            export_per_minute=50,
            export_per_hour=200,
            burst_size=50
        )


# Reconfigura limiter global com config do ambiente
rate_limiter = RateLimiter(get_rate_limit_config())
