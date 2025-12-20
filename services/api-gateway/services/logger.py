"""
Sistema de Logging Estruturado do Conecta Plus.

Fornece logging em formato JSON para produção e formato legível para desenvolvimento.
Integra com stdout para compatibilidade com Docker/Kubernetes.
"""

import logging
import json
import sys
import traceback
from datetime import datetime
from typing import Any, Dict, Optional
from functools import wraps
import time
import uuid


class JSONFormatter(logging.Formatter):
    """Formatter que gera logs em JSON estruturado."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Adiciona campos extras se existirem
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)

        # Adiciona exception info se houver
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info) if record.exc_info[0] else None
            }

        return json.dumps(log_entry, ensure_ascii=False, default=str)


class ColoredFormatter(logging.Formatter):
    """Formatter colorido para desenvolvimento."""

    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET = '\033[0m'

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Formata mensagem base
        msg = f"{color}[{timestamp}] {record.levelname:8}{self.RESET} {record.name}: {record.getMessage()}"

        # Adiciona campos extras se existirem
        if hasattr(record, 'extra_fields') and record.extra_fields:
            extras = " | ".join(f"{k}={v}" for k, v in record.extra_fields.items())
            msg += f" | {extras}"

        # Adiciona exception se houver
        if record.exc_info:
            msg += f"\n{self.formatException(record.exc_info)}"

        return msg


class StructuredLogger:
    """Logger estruturado com suporte a campos extras."""

    def __init__(self, name: str, level: str = "INFO", json_format: bool = False):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))
        self.logger.handlers = []  # Remove handlers existentes

        # Configura handler para stdout
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(getattr(logging, level.upper()))

        # Escolhe formatter baseado no ambiente
        if json_format:
            handler.setFormatter(JSONFormatter())
        else:
            handler.setFormatter(ColoredFormatter())

        self.logger.addHandler(handler)

    def _log(self, level: str, message: str, **kwargs):
        """Log interno com campos extras."""
        record = self.logger.makeRecord(
            self.logger.name,
            getattr(logging, level.upper()),
            fn="",
            lno=0,
            msg=message,
            args=(),
            exc_info=kwargs.pop('exc_info', None)
        )
        record.extra_fields = kwargs
        self.logger.handle(record)

    def debug(self, message: str, **kwargs):
        """Log de debug."""
        self._log("DEBUG", message, **kwargs)

    def info(self, message: str, **kwargs):
        """Log de informação."""
        self._log("INFO", message, **kwargs)

    def warning(self, message: str, **kwargs):
        """Log de aviso."""
        self._log("WARNING", message, **kwargs)

    def error(self, message: str, **kwargs):
        """Log de erro."""
        self._log("ERROR", message, **kwargs)

    def critical(self, message: str, **kwargs):
        """Log crítico."""
        self._log("CRITICAL", message, **kwargs)

    def exception(self, message: str, **kwargs):
        """Log de exceção com traceback."""
        self._log("ERROR", message, exc_info=sys.exc_info(), **kwargs)


class RequestLogger:
    """Logger especializado para requisições HTTP."""

    def __init__(self, logger: StructuredLogger):
        self.logger = logger

    def log_request(
        self,
        request_id: str,
        method: str,
        path: str,
        client_ip: str,
        user_id: Optional[str] = None,
        **extra
    ):
        """Loga início de uma requisição."""
        self.logger.info(
            f"Request started: {method} {path}",
            request_id=request_id,
            method=method,
            path=path,
            client_ip=client_ip,
            user_id=user_id,
            **extra
        )

    def log_response(
        self,
        request_id: str,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        user_id: Optional[str] = None,
        **extra
    ):
        """Loga resposta de uma requisição."""
        level = "INFO" if status_code < 400 else "WARNING" if status_code < 500 else "ERROR"
        log_fn = getattr(self.logger, level.lower())

        log_fn(
            f"Request completed: {method} {path} -> {status_code} ({duration_ms:.2f}ms)",
            request_id=request_id,
            method=method,
            path=path,
            status_code=status_code,
            duration_ms=round(duration_ms, 2),
            user_id=user_id,
            **extra
        )

    def log_error(
        self,
        request_id: str,
        method: str,
        path: str,
        error: Exception,
        user_id: Optional[str] = None,
        **extra
    ):
        """Loga erro em uma requisição."""
        self.logger.exception(
            f"Request failed: {method} {path} - {type(error).__name__}: {str(error)}",
            request_id=request_id,
            method=method,
            path=path,
            error_type=type(error).__name__,
            error_message=str(error),
            user_id=user_id,
            **extra
        )


class AuditLogger:
    """Logger especializado para auditoria de ações."""

    def __init__(self, logger: StructuredLogger):
        self.logger = logger

    def log_action(
        self,
        action: str,
        resource: str,
        resource_id: str,
        user_id: str,
        user_email: str = None,
        details: Dict[str, Any] = None,
        success: bool = True,
        **extra
    ):
        """Loga uma ação de auditoria."""
        self.logger.info(
            f"AUDIT: {action} on {resource}/{resource_id} by {user_id}",
            audit=True,
            action=action,
            resource=resource,
            resource_id=resource_id,
            user_id=user_id,
            user_email=user_email,
            success=success,
            details=details or {},
            **extra
        )

    def log_financial_transaction(
        self,
        transaction_type: str,
        amount: float,
        boleto_id: str = None,
        unidade_id: str = None,
        user_id: str = None,
        status: str = "success",
        **extra
    ):
        """Loga transação financeira para compliance."""
        self.logger.info(
            f"FINANCIAL: {transaction_type} - R$ {amount:.2f}",
            audit=True,
            financial=True,
            transaction_type=transaction_type,
            amount=amount,
            boleto_id=boleto_id,
            unidade_id=unidade_id,
            user_id=user_id,
            status=status,
            **extra
        )

    def log_security_event(
        self,
        event_type: str,
        severity: str,
        client_ip: str,
        user_id: str = None,
        details: str = None,
        **extra
    ):
        """Loga evento de segurança."""
        log_fn = self.logger.warning if severity in ["medium", "low"] else self.logger.error

        log_fn(
            f"SECURITY: {event_type} - {severity}",
            security=True,
            event_type=event_type,
            severity=severity,
            client_ip=client_ip,
            user_id=user_id,
            details=details,
            **extra
        )


class PerformanceLogger:
    """Logger especializado para métricas de performance."""

    def __init__(self, logger: StructuredLogger):
        self.logger = logger

    def log_metric(
        self,
        metric_name: str,
        value: float,
        unit: str = "ms",
        tags: Dict[str, str] = None,
        **extra
    ):
        """Loga uma métrica de performance."""
        self.logger.info(
            f"METRIC: {metric_name}={value}{unit}",
            metric=True,
            metric_name=metric_name,
            value=value,
            unit=unit,
            tags=tags or {},
            **extra
        )

    def log_slow_query(
        self,
        query: str,
        duration_ms: float,
        threshold_ms: float = 100,
        **extra
    ):
        """Loga query lenta."""
        if duration_ms > threshold_ms:
            self.logger.warning(
                f"SLOW QUERY: {duration_ms:.2f}ms",
                slow_query=True,
                duration_ms=duration_ms,
                threshold_ms=threshold_ms,
                query=query[:500],  # Trunca query longa
                **extra
            )


def create_logger(
    name: str,
    level: str = None,
    json_format: bool = None
) -> StructuredLogger:
    """
    Factory function para criar loggers.

    Args:
        name: Nome do logger
        level: Nível de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: Se True, usa formato JSON. Se None, detecta pelo ambiente.
    """
    # Importa settings para pegar configurações
    try:
        from config import settings
        if level is None:
            level = settings.log_level
        if json_format is None:
            json_format = settings.is_production
    except ImportError:
        level = level or "INFO"
        json_format = json_format if json_format is not None else False

    return StructuredLogger(name, level, json_format)


def timed(logger: StructuredLogger = None):
    """Decorator para medir tempo de execução de funções."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            log = logger or create_logger(func.__module__)
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = (time.time() - start) * 1000
                log.debug(
                    f"Function {func.__name__} completed",
                    function=func.__name__,
                    duration_ms=round(duration, 2)
                )
                return result
            except Exception as e:
                duration = (time.time() - start) * 1000
                log.error(
                    f"Function {func.__name__} failed",
                    function=func.__name__,
                    duration_ms=round(duration, 2),
                    error=str(e)
                )
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            log = logger or create_logger(func.__module__)
            start = time.time()
            try:
                result = func(*args, **kwargs)
                duration = (time.time() - start) * 1000
                log.debug(
                    f"Function {func.__name__} completed",
                    function=func.__name__,
                    duration_ms=round(duration, 2)
                )
                return result
            except Exception as e:
                duration = (time.time() - start) * 1000
                log.error(
                    f"Function {func.__name__} failed",
                    function=func.__name__,
                    duration_ms=round(duration, 2),
                    error=str(e)
                )
                raise

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


# Loggers pré-configurados
app_logger = create_logger("conecta-plus")
request_logger = RequestLogger(create_logger("conecta-plus.requests"))
audit_logger = AuditLogger(create_logger("conecta-plus.audit"))
performance_logger = PerformanceLogger(create_logger("conecta-plus.performance"))


# Funções de conveniência
def log_info(message: str, **kwargs):
    """Log de informação rápido."""
    app_logger.info(message, **kwargs)


def log_error(message: str, **kwargs):
    """Log de erro rápido."""
    app_logger.error(message, **kwargs)


def log_warning(message: str, **kwargs):
    """Log de aviso rápido."""
    app_logger.warning(message, **kwargs)


def log_debug(message: str, **kwargs):
    """Log de debug rápido."""
    app_logger.debug(message, **kwargs)


def log_exception(message: str, **kwargs):
    """Log de exceção com traceback."""
    app_logger.exception(message, **kwargs)


if __name__ == "__main__":
    # Teste do sistema de logging
    print("=== Teste de Logging ===\n")

    # Logger padrão
    logger = create_logger("test", level="DEBUG", json_format=False)
    logger.debug("Mensagem de debug", user_id="123")
    logger.info("Mensagem de informação", endpoint="/api/test")
    logger.warning("Mensagem de aviso", timeout=30)
    logger.error("Mensagem de erro", error_code=500)

    print("\n--- Request Logger ---")
    req_logger = RequestLogger(logger)
    req_id = str(uuid.uuid4())[:8]
    req_logger.log_request(req_id, "GET", "/api/boletos", "192.168.1.1", user_id="user_123")
    req_logger.log_response(req_id, "GET", "/api/boletos", 200, 45.3, user_id="user_123")

    print("\n--- Audit Logger ---")
    aud_logger = AuditLogger(logger)
    aud_logger.log_action("CREATE", "boleto", "BOL-001", "user_123", details={"valor": 150.00})
    aud_logger.log_financial_transaction("PAGAMENTO", 150.00, boleto_id="BOL-001", user_id="user_123")

    print("\n--- JSON Format ---")
    json_logger = create_logger("test-json", level="INFO", json_format=True)
    json_logger.info("Teste em JSON", endpoint="/api/test", user_id="123")
