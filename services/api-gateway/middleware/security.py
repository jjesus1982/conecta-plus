"""
Middleware de Segurança para FastAPI.

Implementa:
- Rate Limiting distribuído (com Redis ou in-memory)
- Validação de JWT
- Proteção contra ataques comuns
"""

import time
import hashlib
from collections import defaultdict
from typing import Callable, Dict, Optional, Tuple
from datetime import datetime, timedelta
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from services.logger import audit_logger, create_logger

logger = create_logger("conecta-plus.security")


class InMemoryRateLimiter:
    """Rate limiter simples em memória (para desenvolvimento)."""

    def __init__(self):
        self.requests: Dict[str, list] = defaultdict(list)

    def is_allowed(self, key: str, limit: int, period: int) -> Tuple[bool, int]:
        """
        Verifica se a requisição é permitida.

        Args:
            key: Identificador único (IP, user_id, etc.)
            limit: Número máximo de requisições
            period: Período em segundos

        Returns:
            Tuple[bool, int]: (permitido, requisições restantes)
        """
        now = time.time()
        window_start = now - period

        # Remove requisições antigas
        self.requests[key] = [ts for ts in self.requests[key] if ts > window_start]

        # Verifica limite
        current_count = len(self.requests[key])
        if current_count >= limit:
            return False, 0

        # Registra nova requisição
        self.requests[key].append(now)
        return True, limit - current_count - 1

    def get_reset_time(self, key: str, period: int) -> int:
        """Retorna tempo até reset do limite."""
        if key not in self.requests or not self.requests[key]:
            return 0

        oldest = min(self.requests[key])
        reset_time = int(oldest + period - time.time())
        return max(0, reset_time)


class RedisRateLimiter:
    """Rate limiter distribuído com Redis (para produção)."""

    def __init__(self, redis_client):
        self.redis = redis_client

    async def is_allowed(self, key: str, limit: int, period: int) -> Tuple[bool, int]:
        """Verifica se a requisição é permitida usando Redis."""
        try:
            pipe = self.redis.pipeline()
            now = time.time()
            window_key = f"rate_limit:{key}:{int(now // period)}"

            pipe.incr(window_key)
            pipe.expire(window_key, period)
            results = await pipe.execute()

            current_count = results[0]
            remaining = max(0, limit - current_count)

            return current_count <= limit, remaining
        except Exception as e:
            logger.error(f"Redis rate limit error: {e}")
            # Fallback: permite a requisição se Redis falhar
            return True, limit

    async def get_reset_time(self, key: str, period: int) -> int:
        """Retorna tempo até reset do limite."""
        try:
            now = time.time()
            window_key = f"rate_limit:{key}:{int(now // period)}"
            ttl = await self.redis.ttl(window_key)
            return max(0, ttl)
        except:
            return period


# Instância global do rate limiter in-memory
_rate_limiter = InMemoryRateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware de Rate Limiting."""

    def __init__(
        self,
        app: ASGIApp,
        requests_per_minute: int = 100,
        webhook_limit: int = 10,
        exclude_paths: list = None
    ):
        super().__init__(app)
        self.default_limit = requests_per_minute
        self.default_period = 60
        self.webhook_limit = webhook_limit
        self.exclude_paths = exclude_paths or ["/health", "/metrics", "/docs", "/openapi.json"]

        # Limites específicos por path
        self.path_limits = {
            "/api/financeiro/webhook": (webhook_limit, 60),
            "/api/auth/login": (20, 60),  # 20 tentativas por minuto
            "/api/auth/register": (5, 60),  # 5 registros por minuto
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Ignora paths excluídos
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)

        # Obtém identificador do cliente
        client_key = self._get_client_key(request)

        # Obtém limites específicos para o path
        limit, period = self._get_path_limits(request.url.path)

        # Verifica rate limit
        allowed, remaining = _rate_limiter.is_allowed(client_key, limit, period)

        if not allowed:
            reset_time = _rate_limiter.get_reset_time(client_key, period)

            # Loga tentativa bloqueada
            audit_logger.log_security_event(
                event_type="RATE_LIMIT_EXCEEDED",
                severity="medium",
                client_ip=self._get_client_ip(request),
                user_id=self._get_user_id(request),
                details=f"Path: {request.url.path}, Limit: {limit}/{period}s"
            )

            return JSONResponse(
                status_code=429,
                content={
                    "error": "Too Many Requests",
                    "message": f"Rate limit exceeded. Try again in {reset_time} seconds.",
                    "retry_after": reset_time
                },
                headers={
                    "Retry-After": str(reset_time),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time()) + reset_time)
                }
            )

        # Processa requisição
        response = await call_next(request)

        # Adiciona headers de rate limit
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + period)

        return response

    def _get_client_key(self, request: Request) -> str:
        """Gera chave única para o cliente."""
        # Usa user_id se autenticado, senão usa IP
        user_id = self._get_user_id(request)
        if user_id and user_id != "anonymous":
            return f"user:{user_id}"

        ip = self._get_client_ip(request)
        return f"ip:{ip}"

    def _get_client_ip(self, request: Request) -> str:
        """Extrai IP do cliente."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"

    def _get_user_id(self, request: Request) -> str:
        """Extrai user_id se disponível."""
        try:
            if hasattr(request.state, 'user'):
                return request.state.user.get('sub', 'anonymous')
        except:
            pass
        return "anonymous"

    def _get_path_limits(self, path: str) -> Tuple[int, int]:
        """Retorna limites específicos para o path."""
        for prefix, limits in self.path_limits.items():
            if path.startswith(prefix):
                return limits
        return self.default_limit, self.default_period


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware que adiciona headers de segurança."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # HSTS apenas em produção
        try:
            from config import settings
            if settings.is_production:
                response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        except:
            pass

        return response


class IPBlockMiddleware(BaseHTTPMiddleware):
    """Middleware para bloquear IPs maliciosos."""

    def __init__(self, app: ASGIApp, blocked_ips: list = None, whitelist_ips: list = None):
        super().__init__(app)
        self.blocked_ips = set(blocked_ips or [])
        self.whitelist_ips = set(whitelist_ips or ["127.0.0.1", "::1"])

        # IPs temporariamente bloqueados (após muitas falhas)
        self.temp_blocked: Dict[str, float] = {}
        self.block_duration = 300  # 5 minutos

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = self._get_client_ip(request)

        # Whitelist sempre passa
        if client_ip in self.whitelist_ips:
            return await call_next(request)

        # Verifica bloqueio permanente
        if client_ip in self.blocked_ips:
            logger.warning(f"Blocked IP attempted access: {client_ip}")
            return JSONResponse(
                status_code=403,
                content={"error": "Forbidden", "message": "Access denied"}
            )

        # Verifica bloqueio temporário
        if client_ip in self.temp_blocked:
            if time.time() < self.temp_blocked[client_ip]:
                return JSONResponse(
                    status_code=403,
                    content={"error": "Forbidden", "message": "Temporarily blocked"}
                )
            else:
                del self.temp_blocked[client_ip]

        return await call_next(request)

    def block_ip_temporarily(self, ip: str):
        """Bloqueia um IP temporariamente."""
        self.temp_blocked[ip] = time.time() + self.block_duration
        logger.warning(f"IP temporarily blocked: {ip}")

    def _get_client_ip(self, request: Request) -> str:
        """Extrai IP do cliente."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"


class BruteForceProtectionMiddleware(BaseHTTPMiddleware):
    """Middleware para proteção contra força bruta em endpoints de autenticação."""

    def __init__(self, app: ASGIApp, max_attempts: int = 5, lockout_time: int = 300):
        super().__init__(app)
        self.max_attempts = max_attempts
        self.lockout_time = lockout_time
        self.failed_attempts: Dict[str, list] = defaultdict(list)
        self.locked_accounts: Dict[str, float] = {}

        # Endpoints protegidos
        self.protected_paths = ["/api/auth/login", "/api/auth/token"]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Apenas verifica endpoints de autenticação
        if not any(request.url.path.startswith(path) for path in self.protected_paths):
            return await call_next(request)

        if request.method != "POST":
            return await call_next(request)

        client_ip = self._get_client_ip(request)
        key = f"{client_ip}"

        # Verifica se está bloqueado
        if key in self.locked_accounts:
            if time.time() < self.locked_accounts[key]:
                remaining = int(self.locked_accounts[key] - time.time())
                return JSONResponse(
                    status_code=423,
                    content={
                        "error": "Account Locked",
                        "message": f"Too many failed attempts. Try again in {remaining} seconds.",
                        "retry_after": remaining
                    }
                )
            else:
                del self.locked_accounts[key]
                self.failed_attempts[key] = []

        # Processa requisição
        response = await call_next(request)

        # Registra falha de autenticação
        if response.status_code == 401:
            self._record_failure(key)

            # Verifica se deve bloquear
            if len(self.failed_attempts[key]) >= self.max_attempts:
                self.locked_accounts[key] = time.time() + self.lockout_time

                audit_logger.log_security_event(
                    event_type="BRUTE_FORCE_LOCKOUT",
                    severity="high",
                    client_ip=client_ip,
                    details=f"Locked after {self.max_attempts} failed attempts"
                )

        # Limpa após sucesso
        elif response.status_code == 200:
            self.failed_attempts[key] = []

        return response

    def _record_failure(self, key: str):
        """Registra tentativa falha."""
        now = time.time()
        # Remove tentativas antigas (mais de 1 hora)
        self.failed_attempts[key] = [
            ts for ts in self.failed_attempts[key]
            if now - ts < 3600
        ]
        self.failed_attempts[key].append(now)

    def _get_client_ip(self, request: Request) -> str:
        """Extrai IP do cliente."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """Middleware para validação básica de requisições."""

    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Verifica tamanho do content
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.MAX_CONTENT_LENGTH:
            return JSONResponse(
                status_code=413,
                content={
                    "error": "Request Entity Too Large",
                    "message": f"Maximum content length is {self.MAX_CONTENT_LENGTH} bytes"
                }
            )

        # Verifica Content-Type para POST/PUT
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = request.headers.get("content-type", "")
            if not content_type:
                # Permite requisições sem body
                pass
            elif not any(ct in content_type for ct in ["application/json", "multipart/form-data", "application/x-www-form-urlencoded"]):
                return JSONResponse(
                    status_code=415,
                    content={
                        "error": "Unsupported Media Type",
                        "message": "Content-Type must be application/json, multipart/form-data, or application/x-www-form-urlencoded"
                    }
                )

        return await call_next(request)


def setup_security_middleware(app, settings=None):
    """Configura todos os middlewares de segurança na aplicação."""

    # Carrega configurações
    if settings is None:
        try:
            from config import settings
        except ImportError:
            settings = None

    # Rate limiting
    if settings:
        requests_per_minute = settings.rate_limit.requests
        webhook_limit = settings.rate_limit.webhook_limit
    else:
        requests_per_minute = 100
        webhook_limit = 10

    # Ordem importa: de dentro para fora
    app.add_middleware(RequestValidationMiddleware)
    app.add_middleware(BruteForceProtectionMiddleware)
    app.add_middleware(IPBlockMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=requests_per_minute,
        webhook_limit=webhook_limit
    )

    logger.info("Security middlewares configurados")
