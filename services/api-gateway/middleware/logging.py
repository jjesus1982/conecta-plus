"""
Middleware de Logging para FastAPI.

Loga automaticamente todas as requisições e respostas.
"""

import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from services.logger import request_logger, audit_logger, create_logger

logger = create_logger("conecta-plus.middleware")


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware que loga todas as requisições HTTP."""

    def __init__(self, app: ASGIApp, exclude_paths: list = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or ["/health", "/metrics", "/favicon.ico"]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Ignora paths excluídos
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)

        # Gera ID único para a requisição
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id

        # Extrai informações da requisição
        method = request.method
        path = request.url.path
        client_ip = self._get_client_ip(request)
        user_id = self._get_user_id(request)

        # Loga início da requisição
        request_logger.log_request(
            request_id=request_id,
            method=method,
            path=path,
            client_ip=client_ip,
            user_id=user_id,
            query_params=str(request.query_params) if request.query_params else None
        )

        # Processa a requisição
        start_time = time.time()
        try:
            response = await call_next(request)
            duration_ms = (time.time() - start_time) * 1000

            # Loga resposta
            request_logger.log_response(
                request_id=request_id,
                method=method,
                path=path,
                status_code=response.status_code,
                duration_ms=duration_ms,
                user_id=user_id
            )

            # Adiciona headers de rastreamento
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"

            return response

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000

            # Loga erro
            request_logger.log_error(
                request_id=request_id,
                method=method,
                path=path,
                error=e,
                user_id=user_id
            )

            raise

    def _get_client_ip(self, request: Request) -> str:
        """Extrai IP do cliente, considerando proxies."""
        # Verifica headers de proxy
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fallback para IP direto
        if request.client:
            return request.client.host

        return "unknown"

    def _get_user_id(self, request: Request) -> str:
        """Extrai user_id do token JWT se disponível."""
        try:
            if hasattr(request.state, 'user'):
                return request.state.user.get('sub', 'anonymous')
        except:
            pass
        return "anonymous"


class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware que audita ações modificadoras (POST, PUT, DELETE)."""

    AUDITABLE_METHODS = ["POST", "PUT", "PATCH", "DELETE"]
    AUDITABLE_PATHS = ["/api/financeiro", "/api/boletos", "/api/pagamentos", "/api/acordos"]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Apenas audita métodos modificadores em paths específicos
        should_audit = (
            request.method in self.AUDITABLE_METHODS and
            any(request.url.path.startswith(path) for path in self.AUDITABLE_PATHS)
        )

        if not should_audit:
            return await call_next(request)

        # Extrai informações
        user_id = self._get_user_id(request)
        user_email = self._get_user_email(request)
        client_ip = self._get_client_ip(request)

        # Processa requisição
        response = await call_next(request)

        # Audita a ação
        action = self._method_to_action(request.method)
        resource = self._path_to_resource(request.url.path)
        resource_id = self._extract_resource_id(request.url.path)

        audit_logger.log_action(
            action=action,
            resource=resource,
            resource_id=resource_id or "new",
            user_id=user_id,
            user_email=user_email,
            success=response.status_code < 400,
            details={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "client_ip": client_ip
            }
        )

        return response

    def _get_client_ip(self, request: Request) -> str:
        """Extrai IP do cliente."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"

    def _get_user_id(self, request: Request) -> str:
        """Extrai user_id do token JWT."""
        try:
            if hasattr(request.state, 'user'):
                return request.state.user.get('sub', 'anonymous')
        except:
            pass
        return "anonymous"

    def _get_user_email(self, request: Request) -> str:
        """Extrai email do usuário do token JWT."""
        try:
            if hasattr(request.state, 'user'):
                return request.state.user.get('email', '')
        except:
            pass
        return ""

    def _method_to_action(self, method: str) -> str:
        """Converte método HTTP para ação."""
        return {
            "POST": "CREATE",
            "PUT": "UPDATE",
            "PATCH": "PARTIAL_UPDATE",
            "DELETE": "DELETE"
        }.get(method, method)

    def _path_to_resource(self, path: str) -> str:
        """Extrai nome do recurso do path."""
        parts = path.strip("/").split("/")
        # /api/financeiro/boletos/123 -> boletos
        if len(parts) >= 3:
            return parts[2]
        return parts[-1] if parts else "unknown"

    def _extract_resource_id(self, path: str) -> str:
        """Extrai ID do recurso do path."""
        parts = path.strip("/").split("/")
        # /api/financeiro/boletos/123 -> 123
        if len(parts) >= 4:
            return parts[3]
        return None


class PerformanceMiddleware(BaseHTTPMiddleware):
    """Middleware que monitora performance e detecta endpoints lentos."""

    SLOW_THRESHOLD_MS = 500  # 500ms

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000

        # Alerta se endpoint for lento
        if duration_ms > self.SLOW_THRESHOLD_MS:
            logger.warning(
                f"Slow endpoint detected: {request.method} {request.url.path}",
                path=request.url.path,
                method=request.method,
                duration_ms=round(duration_ms, 2),
                threshold_ms=self.SLOW_THRESHOLD_MS
            )

        return response


def setup_logging_middleware(app):
    """Configura todos os middlewares de logging na aplicação."""
    # Ordem importa: Performance -> Audit -> Logging (de dentro para fora)
    app.add_middleware(PerformanceMiddleware)
    app.add_middleware(AuditMiddleware)
    app.add_middleware(LoggingMiddleware)

    logger.info("Logging middlewares configurados")
