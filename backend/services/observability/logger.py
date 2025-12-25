"""
Conecta Plus - Logger Estruturado
Logging JSON com correlation IDs e contexto
"""

import logging
import json
import sys
import os
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from contextvars import ContextVar
from functools import wraps

# Context variables para correlation ID
correlation_id_var: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)
request_context_var: ContextVar[Dict[str, Any]] = ContextVar('request_context', default={})


class LogContext:
    """Gerenciador de contexto para logs."""

    @staticmethod
    def set_correlation_id(correlation_id: str) -> None:
        """Define o correlation ID para a request atual."""
        correlation_id_var.set(correlation_id)

    @staticmethod
    def get_correlation_id() -> Optional[str]:
        """Obtém o correlation ID da request atual."""
        return correlation_id_var.get()

    @staticmethod
    def set_context(key: str, value: Any) -> None:
        """Adiciona contexto extra aos logs."""
        ctx = request_context_var.get().copy()
        ctx[key] = value
        request_context_var.set(ctx)

    @staticmethod
    def get_context() -> Dict[str, Any]:
        """Obtém o contexto atual."""
        return request_context_var.get()

    @staticmethod
    def clear() -> None:
        """Limpa o contexto (chamar no fim da request)."""
        correlation_id_var.set(None)
        request_context_var.set({})


def with_correlation_id(func):
    """Decorator para gerar correlation ID automaticamente."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        if not LogContext.get_correlation_id():
            LogContext.set_correlation_id(str(uuid.uuid4()))
        return await func(*args, **kwargs)
    return wrapper


class JSONFormatter(logging.Formatter):
    """Formatter que produz logs em JSON estruturado."""

    def __init__(self, service_name: str = "conecta-plus"):
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": self.service_name,
        }

        # Adicionar correlation ID se existir
        correlation_id = LogContext.get_correlation_id()
        if correlation_id:
            log_data["correlation_id"] = correlation_id

        # Adicionar contexto extra
        context = LogContext.get_context()
        if context:
            log_data["context"] = context

        # Adicionar informações do arquivo/linha
        log_data["location"] = {
            "file": record.pathname,
            "line": record.lineno,
            "function": record.funcName,
        }

        # Adicionar exception se existir
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info) if record.exc_info else None,
            }

        # Adicionar extras customizados
        if hasattr(record, 'extra_data'):
            log_data["data"] = record.extra_data

        return json.dumps(log_data, ensure_ascii=False, default=str)


class StructuredLogger:
    """Logger estruturado com suporte a contexto e métricas."""

    def __init__(self, name: str, level: int = logging.INFO):
        self._logger = logging.getLogger(name)
        self._logger.setLevel(level)

        # Remover handlers existentes
        self._logger.handlers = []

        # Handler para stdout (JSON)
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setFormatter(JSONFormatter())
        self._logger.addHandler(stdout_handler)

        # Handler para arquivo (se LOG_DIR existir)
        log_dir = os.environ.get('LOG_DIR', '/app/logs')
        if os.path.exists(log_dir):
            file_handler = logging.FileHandler(
                os.path.join(log_dir, 'app.json.log'),
                encoding='utf-8'
            )
            file_handler.setFormatter(JSONFormatter())
            self._logger.addHandler(file_handler)

    def _log(self, level: int, message: str, extra: Optional[Dict[str, Any]] = None, exc_info: bool = False):
        """Log interno com suporte a dados extras."""
        record = self._logger.makeRecord(
            self._logger.name,
            level,
            "(unknown file)",
            0,
            message,
            (),
            None
        )
        if extra:
            record.extra_data = extra
        if exc_info:
            import sys
            record.exc_info = sys.exc_info()
        self._logger.handle(record)

    def debug(self, message: str, **kwargs):
        """Log debug com dados extras."""
        self._log(logging.DEBUG, message, kwargs if kwargs else None)

    def info(self, message: str, **kwargs):
        """Log info com dados extras."""
        self._log(logging.INFO, message, kwargs if kwargs else None)

    def warning(self, message: str, **kwargs):
        """Log warning com dados extras."""
        self._log(logging.WARNING, message, kwargs if kwargs else None)

    def error(self, message: str, exc: Optional[Exception] = None, **kwargs):
        """Log error com exception e dados extras."""
        if exc:
            kwargs['error_type'] = type(exc).__name__
            kwargs['error_message'] = str(exc)
        self._log(logging.ERROR, message, kwargs if kwargs else None, exc_info=exc is not None)

    def critical(self, message: str, exc: Optional[Exception] = None, **kwargs):
        """Log critical com exception e dados extras."""
        if exc:
            kwargs['error_type'] = type(exc).__name__
            kwargs['error_message'] = str(exc)
        self._log(logging.CRITICAL, message, kwargs if kwargs else None, exc_info=exc is not None)

    # === Métodos especializados para eventos de domínio ===

    def audit(self, action: str, entity_type: str, entity_id: str, user_id: Optional[str] = None, **details):
        """Log de auditoria para ações importantes."""
        self.info(
            f"AUDIT: {action}",
            audit=True,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            **details
        )

    def domain_event(self, event_type: str, aggregate_id: str, **data):
        """Log de evento de domínio."""
        self.info(
            f"EVENT: {event_type}",
            event=True,
            event_type=event_type,
            aggregate_id=aggregate_id,
            **data
        )

    def api_request(self, method: str, path: str, status_code: int, duration_ms: float, **kwargs):
        """Log de request HTTP."""
        self.info(
            f"{method} {path} - {status_code}",
            request=True,
            method=method,
            path=path,
            status_code=status_code,
            duration_ms=duration_ms,
            **kwargs
        )

    def external_call(self, service: str, endpoint: str, success: bool, duration_ms: float, **kwargs):
        """Log de chamada a serviço externo."""
        level = logging.INFO if success else logging.WARNING
        self._log(
            level,
            f"EXTERNAL: {service} - {'OK' if success else 'FAILED'}",
            {
                'external_call': True,
                'service': service,
                'endpoint': endpoint,
                'success': success,
                'duration_ms': duration_ms,
                **kwargs
            }
        )


# === Instância global ===
logger = StructuredLogger("conecta-plus")


def get_logger(name: str) -> StructuredLogger:
    """Obtém um logger estruturado com nome específico."""
    return StructuredLogger(name)


# === Middleware para FastAPI ===

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import time


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Middleware para adicionar observabilidade às requests."""

    async def dispatch(self, request: Request, call_next):
        # Gerar ou extrair correlation ID
        correlation_id = request.headers.get('X-Correlation-ID') or str(uuid.uuid4())
        LogContext.set_correlation_id(correlation_id)

        # Adicionar contexto da request
        LogContext.set_context('path', str(request.url.path))
        LogContext.set_context('method', request.method)
        LogContext.set_context('client_ip', request.client.host if request.client else 'unknown')

        start_time = time.time()

        try:
            response = await call_next(request)

            # Log da request
            duration_ms = (time.time() - start_time) * 1000
            logger.api_request(
                method=request.method,
                path=str(request.url.path),
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2)
            )

            # Adicionar correlation ID ao response
            response.headers['X-Correlation-ID'] = correlation_id

            return response

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                f"Request failed: {request.method} {request.url.path}",
                exc=e,
                duration_ms=round(duration_ms, 2)
            )
            raise

        finally:
            LogContext.clear()
