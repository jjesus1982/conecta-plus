#!/usr/bin/env python3
"""
AI Orchestrator V2 - Server Runner
Conecta Plus - Plataforma de Gestão Condominial

Inicia o servidor FastAPI com suporte a 36 agentes e comunicação full-duplex.

Uso:
    python run_server.py

Variáveis de ambiente:
    PORT: Porta do servidor (default: 8001)
    HOST: Host do servidor (default: 0.0.0.0)
    LOG_LEVEL: Nível de log (default: info)
"""

import asyncio
import os
import sys
import logging

# Adicionar paths
sys.path.insert(0, '/app')
sys.path.insert(0, '/app/agents')
sys.path.insert(0, '/opt/conecta-plus')
sys.path.insert(0, '/opt/conecta-plus/services/ai-orchestrator')

import uvicorn
from orchestrator import create_api

# Configurar logging
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO').upper(),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Inicia o servidor do AI Orchestrator"""

    # Configurações do servidor
    port = int(os.getenv('PORT', '8001'))
    host = os.getenv('HOST', '0.0.0.0')
    log_level = os.getenv('LOG_LEVEL', 'info').lower()
    workers = int(os.getenv('WORKERS', '1'))

    logger.info(f"Iniciando AI Orchestrator V2")
    logger.info(f"Host: {host}, Port: {port}")
    logger.info(f"Log Level: {log_level}")

    # Criar aplicação FastAPI
    app = await create_api()

    # Configurar Uvicorn
    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level=log_level,
        access_log=True,
        server_header=False,
        date_header=True,
    )

    server = uvicorn.Server(config)

    logger.info(f"Servidor disponível em http://{host}:{port}")
    logger.info("Endpoints:")
    logger.info(f"  - Documentação: http://{host}:{port}/docs")
    logger.info(f"  - Status V1:    http://{host}:{port}/status")
    logger.info(f"  - Status V2:    http://{host}:{port}/v2/status")
    logger.info(f"  - Message Bus:  http://{host}:{port}/v2/message/bus-status")

    await server.serve()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Servidor interrompido pelo usuário")
    except Exception as e:
        logger.error(f"Erro ao iniciar servidor: {e}")
        sys.exit(1)
