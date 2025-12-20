# AI Orchestrator V2 - Conecta Plus
# Dockerfile para deploy do orquestrador de 36 agentes IA com Message Bus
#
# Build: docker build -t conecta-plus/orchestrator:2.0 -f services/ai-orchestrator/Dockerfile .
# Run:   docker run -p 8001:8001 --env-file .env conecta-plus/orchestrator:2.0

FROM python:3.12-slim

LABEL maintainer="Conecta Plus <dev@conectaplus.com.br>"
LABEL description="AI Orchestrator V2 - Orquestrador de 36 Agentes IA com comunicação full-duplex"
LABEL version="2.0"

# Argumentos de build
ARG DEBIAN_FRONTEND=noninteractive

# Variáveis de ambiente
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app:/app/agents \
    TZ=America/Sao_Paulo \
    PORT=8001 \
    HOST=0.0.0.0

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone

# Criar diretório de trabalho
WORKDIR /app

# Copiar requirements e instalar dependências
COPY services/ai-orchestrator/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar framework de agentes (core e todos os 36 agentes)
COPY agents /app/agents/

# Copiar código do orchestrator
COPY services/ai-orchestrator/orchestrator.py /app/
COPY services/ai-orchestrator/run_server.py /app/

# Criar diretórios necessários
RUN mkdir -p /app/data/vector_db /app/logs

# Criar usuário não-root para segurança
RUN useradd -m -u 1000 -s /bin/bash orchestrator && \
    chown -R orchestrator:orchestrator /app

# Trocar para usuário não-root
USER orchestrator

# Expor porta
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -sf http://localhost:${PORT}/v2/status || exit 1

# Comando de inicialização
CMD ["python", "run_server.py"]
