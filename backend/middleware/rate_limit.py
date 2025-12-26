"""
Conecta Plus - Middleware de Rate Limiting
Protege a API contra abuso e ataques de forca bruta
"""

import time
import hashlib
from typing import Callable, Dict, Optional
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
import logging

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting baseado em IP e usuario.

    Algoritmo: Sliding Window Counter
    - Armazena contagem de requests por janela de tempo
    - Retorna 429 Too Many Requests quando limite excedido
    - Headers informativos: X-RateLimit-*

    Configuracoes:
    - requests_per_window: Numero maximo de requests
    - window_seconds: Tamanho da janela em segundos
    - whitelist_paths: Paths que ignoram rate limit
    """

    def __init__(
        self,
        app,
        requests_per_window: int = 100,
        window_seconds: int = 60,
        whitelist_paths: Optional[list] = None,
    ):
        super().__init__(app)
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
        self.whitelist_paths = whitelist_paths or ["/health", "/api/v1/docs", "/api/v1/openapi.json"]

        # Armazenamento em memoria (usar Redis em producao para multiplas instancias)
        self._requests: Dict[str, list] = defaultdict(list)

    def _get_client_id(self, request: Request) -> str:
        """
        Gera identificador unico do cliente.
        Combina IP + User-Agent para identificacao mais precisa.
        """
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"

        user_agent = request.headers.get("User-Agent", "unknown")

        # Hash para privacidade
        raw_id = f"{ip}:{user_agent}"
        return hashlib.sha256(raw_id.encode()).hexdigest()[:16]

    def _clean_old_requests(self, client_id: str, current_time: float) -> None:
        """Remove requests fora da janela de tempo."""
        cutoff = current_time - self.window_seconds
        self._requests[client_id] = [
            ts for ts in self._requests[client_id] if ts > cutoff
        ]

    def _is_rate_limited(self, client_id: str) -> tuple[bool, int, int]:
        """
        Verifica se cliente excedeu o limite.

        Returns:
            tuple: (is_limited, remaining_requests, reset_time)
        """
        current_time = time.time()
        self._clean_old_requests(client_id, current_time)

        request_count = len(self._requests[client_id])
        remaining = max(0, self.requests_per_window - request_count)

        # Tempo ate reset da janela
        if self._requests[client_id]:
            oldest_request = min(self._requests[client_id])
            reset_time = int(oldest_request + self.window_seconds - current_time)
        else:
            reset_time = self.window_seconds

        is_limited = request_count >= self.requests_per_window

        if not is_limited:
            self._requests[client_id].append(current_time)

        return is_limited, remaining, max(0, reset_time)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Ignorar paths na whitelist
        if any(request.url.path.startswith(path) for path in self.whitelist_paths):
            return await call_next(request)

        client_id = self._get_client_id(request)
        is_limited, remaining, reset_time = self._is_rate_limited(client_id)

        if is_limited:
            logger.warning(
                f"Rate limit excedido para cliente {client_id[:8]}... "
                f"Path: {request.url.path}"
            )
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Muitas requisicoes. Tente novamente mais tarde.",
                    "retry_after": reset_time,
                },
                headers={
                    "Retry-After": str(reset_time),
                    "X-RateLimit-Limit": str(self.requests_per_window),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_time),
                },
            )

        response = await call_next(request)

        # Adiciona headers informativos
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_window)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)

        return response


class LoginRateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting especifico para endpoints de autenticacao e endpoints criticos.
    Mais restritivo para prevenir ataques de forca bruta.

    Limites para Login:
    - 5 tentativas por minuto por IP
    - 20 tentativas por hora por IP
    - Bloqueio progressivo apos falhas consecutivas

    Limites para Endpoints Criticos (password reset, LDAP, OAuth):
    - 3 tentativas por minuto por IP
    - 10 tentativas por hora por IP
    """

    def __init__(self, app, login_paths: Optional[list] = None, critical_paths: Optional[list] = None):
        super().__init__(app)
        # Endpoints de login
        self.login_paths = login_paths or [
            "/api/v1/auth/login",
            "/api/v1/auth/login/json",
            "/api/v1/auth/token",
        ]

        # Endpoints criticos (password reset, SSO, etc)
        self.critical_paths = critical_paths or [
            "/api/v1/auth/change-password",
            "/api/v1/auth/ldap/login",
            "/api/v1/auth/refresh",
        ]

        # Contadores por minuto e hora para login
        self._minute_requests: Dict[str, list] = defaultdict(list)
        self._hour_requests: Dict[str, list] = defaultdict(list)
        self._failed_attempts: Dict[str, int] = defaultdict(int)

        # Contadores separados para endpoints criticos
        self._critical_minute: Dict[str, list] = defaultdict(list)
        self._critical_hour: Dict[str, list] = defaultdict(list)

        # Limites para login
        self.minute_limit = 5
        self.hour_limit = 20

        # Limites para endpoints criticos (mais restritivos)
        self.critical_minute_limit = 3
        self.critical_hour_limit = 10

    def _get_ip(self, request: Request) -> str:
        """Extrai IP do cliente."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _clean_old(self, ip: str, current_time: float) -> None:
        """Remove requests antigos."""
        minute_cutoff = current_time - 60
        hour_cutoff = current_time - 3600

        self._minute_requests[ip] = [
            ts for ts in self._minute_requests[ip] if ts > minute_cutoff
        ]
        self._hour_requests[ip] = [
            ts for ts in self._hour_requests[ip] if ts > hour_cutoff
        ]
        self._critical_minute[ip] = [
            ts for ts in self._critical_minute[ip] if ts > minute_cutoff
        ]
        self._critical_hour[ip] = [
            ts for ts in self._critical_hour[ip] if ts > hour_cutoff
        ]

    def _is_login_path(self, path: str) -> bool:
        """Verifica se path e de login."""
        return any(path.startswith(p) for p in self.login_paths)

    def _is_critical_path(self, path: str) -> bool:
        """Verifica se path e critico."""
        return any(path.startswith(p) for p in self.critical_paths)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        is_login = self._is_login_path(path)
        is_critical = self._is_critical_path(path)

        # Se nao e login nem critico, passa direto
        if not is_login and not is_critical:
            return await call_next(request)

        ip = self._get_ip(request)
        current_time = time.time()
        self._clean_old(ip, current_time)

        # Rate limiting para endpoints de login
        if is_login:
            # Verificar limite por minuto
            if len(self._minute_requests[ip]) >= self.minute_limit:
                logger.warning(f"Login rate limit (minuto) excedido para IP {ip}")
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Muitas tentativas de login. Aguarde 1 minuto.",
                        "retry_after": 60,
                    },
                    headers={
                        "Retry-After": "60",
                        "X-RateLimit-Limit": str(self.minute_limit),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": "60",
                    },
                )

            # Verificar limite por hora
            if len(self._hour_requests[ip]) >= self.hour_limit:
                logger.warning(f"Login rate limit (hora) excedido para IP {ip}")
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Muitas tentativas de login. Aguarde 1 hora.",
                        "retry_after": 3600,
                    },
                    headers={
                        "Retry-After": "3600",
                        "X-RateLimit-Limit": str(self.hour_limit),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": "3600",
                    },
                )

            # Registrar tentativa
            self._minute_requests[ip].append(current_time)
            self._hour_requests[ip].append(current_time)

        # Rate limiting para endpoints criticos
        if is_critical:
            # Verificar limite por minuto
            if len(self._critical_minute[ip]) >= self.critical_minute_limit:
                logger.warning(f"Critical endpoint rate limit (minuto) excedido para IP {ip} - Path: {path}")
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Muitas requisicoes. Aguarde 1 minuto.",
                        "retry_after": 60,
                    },
                    headers={
                        "Retry-After": "60",
                        "X-RateLimit-Limit": str(self.critical_minute_limit),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": "60",
                    },
                )

            # Verificar limite por hora
            if len(self._critical_hour[ip]) >= self.critical_hour_limit:
                logger.warning(f"Critical endpoint rate limit (hora) excedido para IP {ip} - Path: {path}")
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Muitas requisicoes. Aguarde 1 hora.",
                        "retry_after": 3600,
                    },
                    headers={
                        "Retry-After": "3600",
                        "X-RateLimit-Limit": str(self.critical_hour_limit),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": "3600",
                    },
                )

            # Registrar tentativa
            self._critical_minute[ip].append(current_time)
            self._critical_hour[ip].append(current_time)

        response = await call_next(request)

        # Rastrear falhas para bloqueio progressivo (apenas login)
        if is_login:
            if response.status_code == 401:
                self._failed_attempts[ip] += 1
                if self._failed_attempts[ip] >= 10:
                    logger.error(f"Multiplas falhas de login para IP {ip} - possivel ataque")
            elif response.status_code == 200:
                self._failed_attempts[ip] = 0

        # Adicionar headers de rate limit na resposta
        if is_login:
            remaining = max(0, self.minute_limit - len(self._minute_requests[ip]))
            response.headers["X-RateLimit-Limit"] = str(self.minute_limit)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
        elif is_critical:
            remaining = max(0, self.critical_minute_limit - len(self._critical_minute[ip]))
            response.headers["X-RateLimit-Limit"] = str(self.critical_minute_limit)
            response.headers["X-RateLimit-Remaining"] = str(remaining)

        return response
