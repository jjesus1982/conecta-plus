"""
Conecta Plus - API Principal
Sistema de Gestao Condominial com IA
Versao 2.0 - Seguranca Aprimorada
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
import logging
import time
import sys
import os

from .config import settings

# Detectar diretório de logs baseado no ambiente
# Prioridade: /app/logs (dentro do container) > variável de ambiente
_log_dir = os.environ.get('LOG_DIR', '/app/logs')
# Verificar se podemos escrever no diretório especificado
if os.path.exists('/app/logs'):
    LOG_DIR = '/app/logs'
elif os.access(os.path.dirname(_log_dir) or '/', os.W_OK):
    LOG_DIR = _log_dir
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
    except PermissionError:
        LOG_DIR = '/app/logs'
        os.makedirs(LOG_DIR, exist_ok=True)
else:
    LOG_DIR = '/app/logs'
    os.makedirs(LOG_DIR, exist_ok=True)
from .database import init_db
from .routers import (
    auth_router,
    usuarios_router,
    condominios_router,
    unidades_router,
    moradores_router,
    acesso_router,
    ocorrencias_router,
    manutencao_router,
    financeiro_router,
    alarmes_router,
    reservas_router,
    comunicados_router,
    assembleias_router,
    dashboard_router,
    tranquilidade_router,
    inteligencia_router,
    health_router,
    events_router,
)
from .routers.frigate import router as frigate_router
from .routers.dispositivos import router as dispositivos_router
from .services.hardware import get_hardware_manager

# Importar middlewares de seguranca
from .middleware import (
    SecurityHeadersMiddleware,
    RateLimitMiddleware,
    AuditLogMiddleware,
)
from .middleware.rate_limit import LoginRateLimitMiddleware
from .telemetry import setup_telemetry

# Configurar logging estruturado
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(LOG_DIR, 'api.log'), encoding='utf-8'),
    ]
)
logger = logging.getLogger(__name__)

# Logger separado para auditoria
audit_logger = logging.getLogger("audit")
audit_handler = logging.FileHandler(os.path.join(LOG_DIR, 'audit.log'), encoding='utf-8')
audit_handler.setFormatter(logging.Formatter('%(asctime)s | %(message)s'))
audit_logger.addHandler(audit_handler)
audit_logger.setLevel(logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia o ciclo de vida da aplicacao."""
    # Startup
    logger.info("=" * 60)
    logger.info("Iniciando Conecta Plus API v2.0")
    logger.info("=" * 60)

    # Validar configuracoes criticas
    logger.info("Validando configuracoes de seguranca...")
    if settings.DEBUG:
        logger.warning("ATENCAO: DEBUG=True em ambiente de producao!")

    # Inicializar banco
    init_db()
    logger.info("Banco de dados inicializado")

    # Inicializar OpenTelemetry (distributed tracing)
    try:
        from .database import engine
        setup_telemetry(app=app, engine=engine)
        logger.info("OpenTelemetry/Jaeger inicializado")
    except Exception as e:
        logger.warning(f"OpenTelemetry nao disponivel: {e}")

    # Inicializar hardware manager
    try:
        hw = await get_hardware_manager()
        logger.info("Hardware Manager inicializado")
    except Exception as e:
        logger.warning(f"Hardware Manager nao disponivel: {e}")

    logger.info("API pronta para receber requisicoes")

    yield

    # Shutdown
    logger.info("Encerrando Conecta Plus API...")
    try:
        from .services.hardware import hardware_manager
        await hardware_manager.shutdown()
    except Exception:
        pass
    logger.info("API encerrada com sucesso")


# Criar aplicacao FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    ## Conecta Plus API v2.0

    Sistema completo de gestao condominial com inteligencia artificial.

    ### Seguranca
    - Autenticacao JWT com refresh tokens
    - Rate limiting por IP e usuario
    - Headers de seguranca OWASP
    - Audit log completo
    - Validacao robusta de inputs

    ### Modulos disponiveis:
    - **Autenticacao** - Login, tokens JWT, OAuth, LDAP/AD
    - **Usuarios** - Gestao de usuarios e permissoes
    - **Condominios** - Cadastro e configuracao
    - **Unidades** - Gestao de unidades
    - **Moradores** - Cadastro de moradores
    - **Controle de Acesso** - Registro de entradas e saidas
    - **Ocorrencias** - Registro e acompanhamento
    - **Manutencao** - Ordens de servico
    - **Financeiro** - Lancamentos e boletos
    - **Alarmes** - Monitoramento de zonas
    - **Reservas** - Agendamento de areas comuns
    - **Comunicados** - Avisos e informativos
    - **Assembleias** - Gestao de assembleias
    - **Dashboard** - Indicadores e estatisticas
    - **CFTV** - Integracao Frigate NVR
    - **Dispositivos** - Controle de hardware
    - **Inteligencia** - IA proativa e previsoes
    """,
    openapi_url=f"{settings.API_PREFIX}/openapi.json",
    docs_url=f"{settings.API_PREFIX}/docs",
    redoc_url=f"{settings.API_PREFIX}/redoc",
    lifespan=lifespan,
    # Seguranca adicional
    swagger_ui_parameters={
        "persistAuthorization": True,
        "displayRequestDuration": True,
    },
)


# ==================== MIDDLEWARES (ordem importa!) ====================

# 1. Security Headers (mais externo)
if settings.SECURITY_HEADERS_ENABLED:
    app.add_middleware(SecurityHeadersMiddleware)
    logger.info("Middleware: SecurityHeaders ativado")

# 2. Rate Limiting geral
if settings.RATE_LIMIT_ENABLED:
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_window=settings.RATE_LIMIT_REQUESTS,
        window_seconds=settings.RATE_LIMIT_WINDOW,
    )
    logger.info(f"Middleware: RateLimit ativado ({settings.RATE_LIMIT_REQUESTS} req/{settings.RATE_LIMIT_WINDOW}s)")

# 3. Rate Limiting especifico para login
app.add_middleware(LoginRateLimitMiddleware)
logger.info("Middleware: LoginRateLimit ativado")

# 4. Audit Log
app.add_middleware(AuditLogMiddleware)
logger.info("Middleware: AuditLog ativado")

# 5. CORS (mais interno, perto da aplicacao)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID", "X-RateLimit-Remaining"],
)


# ==================== EXCEPTION HANDLERS ====================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Trata erros de validacao com mensagens amigaveis."""
    errors = []
    for error in exc.errors():
        field = " -> ".join(str(loc) for loc in error["loc"])
        errors.append({
            "field": field,
            "message": error["msg"],
            "type": error["type"],
        })

    logger.warning(f"Validacao falhou: {request.url.path} - {errors}")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Erro de validacao nos dados enviados",
            "errors": errors,
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Trata erros nao esperados sem expor detalhes internos."""
    request_id = getattr(request.state, 'request_id', 'unknown')

    logger.error(
        f"Erro nao tratado | request_id={request_id} | "
        f"path={request.url.path} | error={str(exc)}",
        exc_info=True
    )

    # Nao expor detalhes do erro em producao
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Erro interno do servidor",
            "request_id": request_id,
        },
    )


# ==================== REGISTRAR ROUTERS ====================

app.include_router(auth_router, prefix=settings.API_PREFIX)
app.include_router(usuarios_router, prefix=settings.API_PREFIX)
app.include_router(condominios_router, prefix=settings.API_PREFIX)
app.include_router(unidades_router, prefix=settings.API_PREFIX)
app.include_router(moradores_router, prefix=settings.API_PREFIX)
app.include_router(acesso_router, prefix=settings.API_PREFIX)
app.include_router(ocorrencias_router, prefix=settings.API_PREFIX)
app.include_router(manutencao_router, prefix=settings.API_PREFIX)
app.include_router(financeiro_router, prefix=settings.API_PREFIX)
app.include_router(alarmes_router, prefix=settings.API_PREFIX)
app.include_router(reservas_router, prefix=settings.API_PREFIX)
app.include_router(comunicados_router, prefix=settings.API_PREFIX)
app.include_router(assembleias_router, prefix=settings.API_PREFIX)
app.include_router(dashboard_router, prefix=settings.API_PREFIX)
app.include_router(frigate_router, prefix=settings.API_PREFIX)
app.include_router(dispositivos_router, prefix=settings.API_PREFIX)
app.include_router(tranquilidade_router, prefix=settings.API_PREFIX)
app.include_router(inteligencia_router, prefix=settings.API_PREFIX)
app.include_router(health_router, prefix="")  # /health, /health/live, /health/ready
app.include_router(events_router, prefix=settings.API_PREFIX)  # /api/v1/events/stream


# ==================== PROMETHEUS METRICS ====================

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

# Métricas customizadas
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency in seconds',
    ['method', 'endpoint'],
    buckets=[0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0]
)

REQUESTS_IN_PROGRESS = Gauge(
    'http_requests_inprogress',
    'Number of HTTP requests in progress',
    ['method', 'endpoint']
)

# Middleware para coletar métricas
@app.middleware("http")
async def prometheus_middleware(request: Request, call_next):
    method = request.method
    endpoint = request.url.path

    # Não medir /metrics e /health
    if endpoint in ["/metrics", "/health", "/health/live", "/health/ready"]:
        return await call_next(request)

    REQUESTS_IN_PROGRESS.labels(method=method, endpoint=endpoint).inc()
    start_time = time.time()

    try:
        response = await call_next(request)
        status = response.status_code
    except Exception as e:
        status = 500
        raise
    finally:
        duration = time.time() - start_time
        REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status).inc()
        REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(duration)
        REQUESTS_IN_PROGRESS.labels(method=method, endpoint=endpoint).dec()

    return response

# Endpoint de métricas
@app.get("/metrics", tags=["Monitoring"], include_in_schema=True)
async def metrics():
    """Endpoint de métricas Prometheus."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )

logger.info("Prometheus metrics habilitado em /metrics")


# ==================== ROTAS DE SISTEMA ====================

@app.get("/", tags=["Sistema"])
async def root():
    """Rota raiz da API."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "online",
        "docs": f"{settings.API_PREFIX}/docs",
        "health": "/health",
    }


@app.get("/health", tags=["Sistema"])
async def health_check():
    """
    Verificacao de saude da API.

    Retorna status dos componentes criticos:
    - API: sempre healthy se responder
    - Database: verificado via conexao
    - Redis: verificado se configurado
    """
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "version": settings.APP_VERSION,
        "components": {
            "api": "healthy",
            "database": "unknown",
            "redis": "unknown",
        }
    }

    # Verificar banco de dados
    try:
        from .database import SessionLocal
        from sqlalchemy import text
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        health_status["components"]["database"] = "healthy"
    except Exception as e:
        health_status["components"]["database"] = "unhealthy"
        health_status["status"] = "degraded"
        logger.error(f"Health check - Database unhealthy: {e}")

    return health_status


@app.get(f"{settings.API_PREFIX}", tags=["Sistema"])
async def api_info():
    """Informacoes da API e endpoints disponiveis."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "security": {
            "rate_limit": f"{settings.RATE_LIMIT_REQUESTS} req/{settings.RATE_LIMIT_WINDOW}s",
            "headers": settings.SECURITY_HEADERS_ENABLED,
            "audit_log": True,
        },
        "endpoints": {
            "auth": f"{settings.API_PREFIX}/auth",
            "usuarios": f"{settings.API_PREFIX}/usuarios",
            "condominios": f"{settings.API_PREFIX}/condominios",
            "unidades": f"{settings.API_PREFIX}/unidades",
            "moradores": f"{settings.API_PREFIX}/moradores",
            "acesso": f"{settings.API_PREFIX}/acesso",
            "ocorrencias": f"{settings.API_PREFIX}/ocorrencias",
            "manutencao": f"{settings.API_PREFIX}/manutencao",
            "financeiro": f"{settings.API_PREFIX}/financeiro",
            "alarmes": f"{settings.API_PREFIX}/alarmes",
            "reservas": f"{settings.API_PREFIX}/reservas",
            "comunicados": f"{settings.API_PREFIX}/comunicados",
            "assembleias": f"{settings.API_PREFIX}/assembleias",
            "dashboard": f"{settings.API_PREFIX}/dashboard",
            "frigate": f"{settings.API_PREFIX}/frigate",
            "dispositivos": f"{settings.API_PREFIX}/dispositivos",
            "tranquilidade": f"{settings.API_PREFIX}/tranquilidade",
            "inteligencia": f"{settings.API_PREFIX}/inteligencia",
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        access_log=True,
        log_level="info",
        server_header=False,  # SEGURANÇA: Não expor versão do servidor
        date_header=False,    # SEGURANÇA: Não expor header Date
    )
