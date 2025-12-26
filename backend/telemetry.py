"""
Conecta Plus - OpenTelemetry Configuration
Distributed Tracing com Jaeger
"""

import os
import logging
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

logger = logging.getLogger(__name__)

# Configuracoes
JAEGER_ENDPOINT = os.getenv("JAEGER_ENDPOINT", "http://conecta-jaeger:4317")
OTEL_ENABLED = os.getenv("OTEL_ENABLED", "true").lower() == "true"
SERVICE_NAME_VALUE = os.getenv("OTEL_SERVICE_NAME", "conecta-plus-backend")
SERVICE_VERSION_VALUE = os.getenv("APP_VERSION", "2.0.0")


def setup_telemetry(app=None, engine=None):
    """
    Configura OpenTelemetry com exportador OTLP para Jaeger.

    Args:
        app: FastAPI application instance
        engine: SQLAlchemy engine instance
    """
    if not OTEL_ENABLED:
        logger.info("OpenTelemetry desabilitado via OTEL_ENABLED=false")
        return

    try:
        # Configurar resource com informacoes do servico
        resource = Resource.create({
            SERVICE_NAME: SERVICE_NAME_VALUE,
            SERVICE_VERSION: SERVICE_VERSION_VALUE,
            "deployment.environment": os.getenv("ENVIRONMENT", "production"),
            "host.name": os.getenv("HOSTNAME", "unknown"),
        })

        # Criar TracerProvider
        provider = TracerProvider(resource=resource)

        # Configurar exportador OTLP (para Jaeger)
        otlp_exporter = OTLPSpanExporter(
            endpoint=JAEGER_ENDPOINT,
            insecure=True,  # Usar True para conexoes locais sem TLS
        )

        # Adicionar processor com batch para performance
        span_processor = BatchSpanProcessor(
            otlp_exporter,
            max_queue_size=2048,
            max_export_batch_size=512,
            schedule_delay_millis=5000,
        )
        provider.add_span_processor(span_processor)

        # Registrar provider globalmente
        trace.set_tracer_provider(provider)

        # Instrumentar FastAPI
        if app:
            FastAPIInstrumentor.instrument_app(
                app,
                excluded_urls="health,health/live,health/ready,metrics",
            )
            logger.info("FastAPI instrumentado com OpenTelemetry")

        # Instrumentar SQLAlchemy
        if engine:
            SQLAlchemyInstrumentor().instrument(
                engine=engine,
                enable_commenter=True,
            )
            logger.info("SQLAlchemy instrumentado com OpenTelemetry")

        # Instrumentar Redis
        RedisInstrumentor().instrument()
        logger.info("Redis instrumentado com OpenTelemetry")

        # Instrumentar HTTPX (para chamadas HTTP externas)
        HTTPXClientInstrumentor().instrument()
        logger.info("HTTPX instrumentado com OpenTelemetry")

        logger.info(f"OpenTelemetry configurado - Jaeger endpoint: {JAEGER_ENDPOINT}")

    except Exception as e:
        logger.warning(f"Falha ao configurar OpenTelemetry: {e}")
        logger.warning("Tracing desabilitado - sistema continua funcionando")


def get_tracer(name: str = __name__):
    """
    Retorna um tracer para criacao manual de spans.

    Args:
        name: Nome do modulo/componente

    Returns:
        Tracer instance
    """
    return trace.get_tracer(name)


def add_span_attributes(attributes: dict):
    """
    Adiciona atributos ao span atual.

    Args:
        attributes: Dicionario de atributos
    """
    span = trace.get_current_span()
    if span:
        for key, value in attributes.items():
            span.set_attribute(key, value)


def record_exception(exception: Exception, attributes: dict = None):
    """
    Registra uma excecao no span atual.

    Args:
        exception: Excecao a ser registrada
        attributes: Atributos adicionais
    """
    span = trace.get_current_span()
    if span:
        span.record_exception(exception)
        span.set_status(trace.Status(trace.StatusCode.ERROR, str(exception)))
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)
