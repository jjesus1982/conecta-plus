# ============================================
# Conecta Plus - Backend Dockerfile
# Produção
# ============================================

FROM python:3.11-slim

# Definir variáveis de ambiente
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Definir diretório de trabalho
WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar código da aplicação
COPY . ./backend/

# Criar usuário não-root para segurança
RUN useradd -m -u 1000 conecta && \
    chown -R conecta:conecta /app

# Criar diretórios necessários
RUN mkdir -p /app/data/uploads /app/logs && \
    chown -R conecta:conecta /app/data /app/logs

# Mudar para usuário não-root
USER conecta

# Expor porta
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Comando para iniciar a aplicação
# SEGURANÇA: --no-server-header para não expor versão do servidor
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--no-server-header"]
