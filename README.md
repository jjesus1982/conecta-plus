# Conecta Plus

**Plataforma SaaS Integrada de Gestão Condominial com Inteligência Artificial**

[![Version](https://img.shields.io/badge/version-2.0.1-blue.svg)](https://github.com/conecta-plus)
[![License](https://img.shields.io/badge/license-Proprietary-red.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-green.svg)](https://python.org)
[![Next.js](https://img.shields.io/badge/Next.js-16-black.svg)](https://nextjs.org)

---

## Visão Geral

O **Conecta Plus** é uma plataforma completa de gestão condominial desenvolvida pela Conecta Mais, empresa especializada em segurança eletrônica. O sistema integra 14 módulos principais, 42 agentes de IA e mais de 80 submódulos para oferecer uma solução completa de gestão.

### Modelo de Negócio

- **Síndicos**: Acesso FREE (funcionalidades limitadas)
- **Condomínios**: Assinatura PAID (acesso completo)
- **Multi-tenant**: Conecta Mais → Síndicos → Condomínios → Unidades

---

## Stack Tecnológica

### Backend
- **Python 3.11+** - FastAPI, SQLAlchemy, Alembic
- **Node.js 20+** - TypeScript, Express

### Frontend
- **Next.js 16** - React 19, TypeScript
- **Tailwind CSS** - Estilização
- **Radix UI** - Componentes acessíveis

### Databases
- **PostgreSQL 16** - Banco principal
- **Redis 7** - Cache e filas
- **MongoDB 7** - Logs e eventos

### IA/ML
- **LLMs**: Claude (Anthropic), GPT-4 (OpenAI)
- **Visão**: YOLO v8, InsightFace, EasyOCR
- **Áudio**: Whisper (faster-whisper)

### Infraestrutura
- **Docker** + **Docker Compose**
- **Nginx** - Proxy reverso
- **Prometheus** + **Grafana** - Monitoramento

---

## Instalação

### Pré-requisitos

- Docker 24+
- Docker Compose 2.20+
- Git

### Quick Start

```bash
# Clone o repositório
git clone https://github.com/conecta-mais/conecta-plus.git
cd conecta-plus

# Copie o arquivo de ambiente
cp .env.example .env

# Configure as variáveis de ambiente
nano .env

# Inicie os containers
docker compose up -d

# Verifique o status
docker compose ps
```

### Variáveis de Ambiente

```env
# Banco de Dados
POSTGRES_USER=conecta
POSTGRES_PASSWORD=sua_senha_segura
POSTGRES_DB=conecta_plus

# Redis
REDIS_PASSWORD=sua_senha_redis

# JWT
JWT_SECRET=sua_chave_secreta_muito_longa

# IA (opcional)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
```

---

## Estrutura do Projeto

```
/opt/conecta-plus/
├── frontend/           # Next.js 16 (React 19)
├── backend/            # FastAPI Python
│   ├── routers/        # 21 endpoints API
│   ├── models/         # 22 modelos SQLAlchemy
│   └── services/       # Lógica de negócio
├── agents/             # 42 Agentes de IA
│   ├── core/           # Base agent, message bus
│   ├── specialized/    # 8 categorias
│   └── system-monitor/ # Monitoramento autônomo
├── services/           # Microserviços
│   ├── api-gateway/    # Gateway central
│   ├── auth-service/   # Autenticação
│   └── ai-orchestrator/# Orquestrador IA
├── mcps/               # 27 integrações hardware
├── config/             # Nginx, SSL
└── docker-compose.yml
```

---

## Módulos Principais

| Módulo | Descrição |
|--------|-----------|
| **Guardian** | Monitoramento IA de câmeras (CFTV) |
| **Portaria Virtual** | Atendimento remoto 24/7 |
| **Financeiro** | Gestão de boletos, cobranças, DRE |
| **Acesso** | Controle de pedestres, veículos, visitantes |
| **Manutenção** | Ordens de serviço, preventiva/corretiva |
| **Comunicação** | Comunicados, notificações multi-canal |
| **Assembleias** | Votação digital, atas automáticas |
| **Reservas** | Áreas comuns, aprovação automática |
| **Ocorrências** | Registro, tratamento, escalonamento |
| **Encomendas** | Rastreamento, notificação |

---

## API Endpoints

A API está disponível em `http://localhost:8000/docs` (Swagger UI).

### Principais Endpoints

```
GET  /health              # Status do sistema
POST /api/v1/auth/login   # Autenticação
GET  /api/v1/dashboard    # Dashboard principal
GET  /api/v1/condominios  # Listar condomínios
GET  /api/v1/unidades     # Listar unidades
GET  /api/v1/moradores    # Listar moradores
GET  /api/v1/financeiro   # Dados financeiros
GET  /api/v1/acesso       # Controle de acesso
GET  /api/v1/cftv         # Câmeras
GET  /api/v1/manutencao   # Manutenções
```

---

## Agentes de IA

O sistema conta com 42 agentes especializados organizados em 8 categorias:

### Categorias

1. **CFTV** - Monitoramento, análise de vídeo, gravação
2. **Acesso** - Pedestres, veículos, visitantes
3. **Portaria** - Porteiro virtual, encomendas, controle
4. **Financeiro** - Cobrança, contas, relatórios
5. **Manutenção** - Preventiva, corretiva, fornecedores
6. **Comunicação** - Atendimento, comunicados, notificações
7. **Ocorrências** - Registro, tratamento, escalonamento
8. **Síndico** - Gestão, assembleias, documentos

### Inteligência Proativa (Q2)

- **Previsões**: Análise preditiva de eventos
- **Sugestões**: Recomendações automáticas
- **Alertas Enriquecidos**: Contexto e ações sugeridas
- **Tranquilidade**: Status em tempo real para porteiros/moradores

---

## Integrações (MCPs)

27 integrações com hardware de segurança:

| Fabricante | Tipo |
|------------|------|
| **Intelbras** | CFTV, Acesso, Alarme |
| **Hikvision** | CFTV |
| **Control iD** | Acesso |
| **Garen** | Portões |
| **JFL** | Alarme |
| **MikroTik** | Rede |
| **Furukawa** | Infraestrutura |
| **Asterisk/Issabel** | VoIP |

---

## Desenvolvimento

### Executar Localmente

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

### Testes

```bash
# Backend
cd backend
pytest -v

# Frontend
cd frontend
npm run test
```

### Lint e Formatação

```bash
# Python
black backend/
flake8 backend/

# TypeScript
npm run lint
npm run format
```

---

## Deploy em Produção

### Docker Compose

```bash
# Build e deploy
docker compose -f docker/docker-compose.prod.yml up -d --build

# Verificar logs
docker compose logs -f

# Verificar saúde
curl http://localhost:8000/health
```

### Verificação de Saúde

```json
{
  "status": "healthy",
  "components": {
    "api": {"status": "healthy"},
    "database": {"status": "healthy"},
    "redis": {"status": "healthy"},
    "event_stream": {"status": "healthy"}
  }
}
```

---

## Monitoramento

### Prometheus

Métricas disponíveis em `http://localhost:9090`

### Grafana

Dashboards em `http://localhost:3000/grafana`

### System Monitor Agent

Agente autônomo que monitora todo o sistema:

```bash
# Ver relatórios
ls agents/system-monitor/reports/

# Status do agente
systemctl status system-monitor
```

---

## Segurança

- Autenticação JWT com refresh tokens
- Rate limiting configurável
- CORS configurado
- HTTPS via Nginx
- Secrets em variáveis de ambiente
- Validação de entrada (Pydantic)

---

## Licença

Proprietário - Conecta Mais Soluções em Segurança Eletrônica

---

## Suporte

- **Email**: suporte@conectaplus.com.br
- **Documentação**: `/docs` na API
- **Issues**: GitHub Issues

---

## Changelog

Veja [CHANGELOG.md](CHANGELOG.md) para histórico de versões.

---

**Desenvolvido por Conecta Mais** | Gestão Condominial Inteligente
