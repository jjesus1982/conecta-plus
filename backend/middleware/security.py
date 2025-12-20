"""
Conecta Plus - Middleware de Headers de Seguranca
Implementa headers de seguranca recomendados pela OWASP
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from typing import Callable


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adiciona headers de seguranca em todas as respostas.

    Headers implementados:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - X-XSS-Protection: 1; mode=block
    - Strict-Transport-Security: max-age=31536000
    - Content-Security-Policy: default-src 'self'
    - Referrer-Policy: strict-origin-when-cross-origin
    - Permissions-Policy: geolocation=(), microphone=(), camera=()
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Previne MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Previne clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Ativa protecao XSS do browser (legado, mas ainda util)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Forca HTTPS (HSTS)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Content Security Policy
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' ws: wss:; "
            "frame-ancestors 'none';"
        )

        # Controla informacoes de referrer
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Restringe APIs do browser
        response.headers["Permissions-Policy"] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=()"
        )

        # Remove headers que expoe informacoes do servidor
        if "Server" in response.headers:
            del response.headers["Server"]
        if "X-Powered-By" in response.headers:
            del response.headers["X-Powered-By"]

        return response
