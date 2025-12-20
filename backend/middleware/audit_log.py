"""
Conecta Plus - Middleware de Audit Log
Registra todas as operacoes para auditoria e compliance
"""

import time
import json
import logging
from datetime import datetime
from typing import Callable, Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("audit")


class AuditLogMiddleware(BaseHTTPMiddleware):
    """
    Registra logs de auditoria para todas as requisicoes.

    Informacoes registradas:
    - Timestamp
    - IP do cliente
    - Usuario (se autenticado)
    - Metodo HTTP
    - Path
    - Status code
    - Tempo de resposta
    - User-Agent
    - Request ID

    Endpoints sensiveis tem logging mais detalhado.
    """

    # Endpoints que requerem logging detalhado
    SENSITIVE_PATHS = [
        "/api/v1/auth/",
        "/api/v1/usuarios/",
        "/api/v1/acesso/",
        "/api/v1/alarmes/",
        "/api/v1/configuracoes/",
    ]

    # Metodos que modificam dados
    MUTATION_METHODS = ["POST", "PUT", "PATCH", "DELETE"]

    def __init__(self, app, log_body: bool = False):
        super().__init__(app)
        self.log_body = log_body

    def _get_client_ip(self, request: Request) -> str:
        """Extrai IP real do cliente."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        return request.client.host if request.client else "unknown"

    def _get_user_id(self, request: Request) -> Optional[str]:
        """Extrai ID do usuario do token JWT (se disponivel)."""
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                import jwt
                token = auth_header[7:]
                # Apenas decodifica sem verificar (para logging)
                payload = jwt.decode(token, options={"verify_signature": False})
                return str(payload.get("sub", "unknown"))
            except Exception:
                pass
        return None

    def _is_sensitive_path(self, path: str) -> bool:
        """Verifica se path e sensivel."""
        return any(path.startswith(p) for p in self.SENSITIVE_PATHS)

    def _sanitize_data(self, data: dict) -> dict:
        """Remove dados sensiveis do log."""
        sensitive_keys = [
            "password", "senha", "secret", "token", "api_key",
            "credit_card", "cpf", "cnpj", "rg"
        ]
        sanitized = {}
        for key, value in data.items():
            key_lower = key.lower()
            if any(sk in key_lower for sk in sensitive_keys):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_data(value)
            else:
                sanitized[key] = value
        return sanitized

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Gerar request ID unico
        request_id = f"{int(time.time() * 1000)}-{id(request)}"

        # Adicionar ao request state
        request.state.request_id = request_id

        # Registrar inicio
        start_time = time.time()

        # Capturar informacoes do request
        client_ip = self._get_client_ip(request)
        user_id = self._get_user_id(request)
        method = request.method
        path = request.url.path
        query_params = dict(request.query_params)
        user_agent = request.headers.get("User-Agent", "unknown")

        # Log de entrada para operacoes de mutacao
        if method in self.MUTATION_METHODS:
            logger.info(
                f"REQUEST | id={request_id} | ip={client_ip} | "
                f"user={user_id or 'anonymous'} | {method} {path}"
            )

        # Processar request
        try:
            response = await call_next(request)
            status_code = response.status_code
            error = None
        except Exception as e:
            status_code = 500
            error = str(e)
            raise
        finally:
            # Calcular tempo de resposta
            process_time = time.time() - start_time

            # Construir log entry
            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": request_id,
                "client_ip": client_ip,
                "user_id": user_id,
                "method": method,
                "path": path,
                "status_code": status_code,
                "process_time_ms": round(process_time * 1000, 2),
                "user_agent": user_agent[:100],  # Limitar tamanho
            }

            # Adicionar detalhes para paths sensiveis
            if self._is_sensitive_path(path) or method in self.MUTATION_METHODS:
                log_entry["query_params"] = self._sanitize_data(query_params)

            # Adicionar erro se houver
            if error:
                log_entry["error"] = error[:500]

            # Determinar nivel do log
            if status_code >= 500:
                logger.error(json.dumps(log_entry))
            elif status_code >= 400:
                logger.warning(json.dumps(log_entry))
            elif self._is_sensitive_path(path) or method in self.MUTATION_METHODS:
                logger.info(json.dumps(log_entry))
            else:
                logger.debug(json.dumps(log_entry))

        # Adicionar request ID no header da resposta
        response.headers["X-Request-ID"] = request_id

        return response
