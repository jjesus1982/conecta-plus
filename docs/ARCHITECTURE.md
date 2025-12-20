# Conecta Plus - Arquitetura do Sistema

## Visão Geral

O Conecta Plus é uma plataforma SaaS de gestão condominial inteligente que integra:
- 24 Agentes de IA com evolução em 7 níveis
- 24 MCPs para integração com hardware
- Sistema de vigilância cognitiva
- Automação inteligente

## Diagrama de Arquitetura

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND (Next.js 14)                          │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐            │
│  │Dashboard│ │  CFTV   │ │Financ.  │ │ Acesso  │ │  ...    │            │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘            │
└───────┼──────────┼─────────┼─────────┼─────────┼────────────────────────┘
        │          │         │         │         │
        └──────────┴─────────┴─────────┴─────────┘
                            │
                     ┌──────▼──────┐
                     │    NGINX    │ (Proxy Reverso)
                     │  Port 80/443│
                     └──────┬──────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
┌───────▼───────┐   ┌───────▼───────┐   ┌───────▼───────┐
│  API Gateway  │   │AI Orchestrator│   │  WebSocket    │
│  (FastAPI)    │   │  (Python)     │   │   Server      │
│  Port 3001    │   │  Port 8001    │   │               │
└───────┬───────┘   └───────┬───────┘   └───────────────┘
        │                   │
        │           ┌───────▼───────┐
        │           │   AGENTES IA  │
        │           │  (24 agentes) │
        │           │  Nível 1-7    │
        │           └───────┬───────┘
        │                   │
        └─────────┬─────────┴─────────┐
                  │                   │
        ┌─────────▼─────────┐ ┌───────▼───────┐
        │    PostgreSQL     │ │    Redis      │
        │   (Dados Core)    │ │ (Cache/Filas) │
        │    Port 5432      │ │  Port 6379    │
        └───────────────────┘ └───────────────┘
                  │
        ┌─────────▼─────────┐
        │     MongoDB       │
        │  (Logs/Eventos)   │
        │   Port 27017      │
        └───────────────────┘
```

## Componentes Principais

### 1. Frontend (Next.js 14)

```
frontend/
├── src/
│   ├── app/                    # App Router
│   │   ├── (auth)/            # Rotas autenticadas
│   │   │   ├── dashboard/
│   │   │   ├── cftv/
│   │   │   ├── financeiro/
│   │   │   └── ...
│   │   ├── login/
│   │   └── layout.tsx
│   ├── components/
│   │   ├── ui/                # Componentes base (shadcn)
│   │   └── layout/            # Layout components
│   ├── lib/
│   │   ├── api.ts            # Cliente API
│   │   └── utils.ts
│   ├── stores/               # Zustand stores
│   └── hooks/                # Custom hooks
```

### 2. API Gateway (FastAPI)

```python
# Endpoints principais
/api/auth/login          # Autenticação JWT
/api/auth/refresh        # Refresh token
/api/users/*             # CRUD usuários
/api/condominios/*       # CRUD condomínios
/api/unidades/*          # CRUD unidades
/api/financeiro/*        # Módulo financeiro
/api/cftv/*              # Módulo CFTV
/api/acesso/*            # Controle de acesso
/api/ocorrencias/*       # Ocorrências
/api/reservas/*          # Reservas
/api/comunicados/*       # Comunicados

# WebSocket
/ws/{client_id}          # Conexão WebSocket
```

### 3. AI Orchestrator

```
services/ai-orchestrator/
├── main.py               # FastAPI app
├── orchestrator.py       # Orquestrador de agentes
├── agent_manager.py      # Gerenciador de agentes
└── routes/
    ├── agents.py         # Rotas de agentes
    └── tasks.py          # Rotas de tarefas
```

### 4. Framework de Agentes

```
agents/
├── core/
│   ├── __init__.py
│   ├── base_agent.py      # Classe base (7 níveis)
│   ├── memory_store.py    # Sistema de memória
│   ├── llm_client.py      # Cliente LLM unificado
│   ├── rag_system.py      # Sistema RAG
│   └── tools.py           # Ferramentas de agentes
├── financeiro/
│   ├── agent.py           # Agente v1
│   └── agent_v2.py        # Agente v2 (Nível 7)
├── cftv/
│   ├── agent.py
│   └── agent_v2.py        # Agente v2 (Nível 7)
├── acesso/
├── alarme/
├── sindico/
└── ... (24 agentes total)
```

## Níveis de Evolução dos Agentes

### Nível 1: REATIVO
- Responde a comandos diretos
- Executa operações CRUD
- Sem proatividade

### Nível 2: PROATIVO
- Antecipa necessidades
- Envia alertas automaticamente
- Monitora condições

### Nível 3: PREDITIVO
- Usa ML para previsões
- Analisa padrões
- Projeta cenários futuros

### Nível 4: AUTÔNOMO
- Toma decisões independentes
- Executa ações sem aprovação (dentro de limites)
- Ajusta parâmetros automaticamente

### Nível 5: EVOLUTIVO
- Aprende com cada interação
- Melhora continuamente
- Identifica e corrige falhas

### Nível 6: COLABORATIVO
- Trabalha com outros agentes
- Compartilha conhecimento
- Coordena ações complexas

### Nível 7: TRANSCENDENTE
- Gera insights além do óbvio
- Correlações não esperadas
- Soluções inovadoras

## Sistema de Memória

```
┌─────────────────────────────────────────────────────────────┐
│                    UnifiedMemorySystem                       │
│                                                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │ RedisMemory     │  │ VectorMemory    │  │ WorkingMem   │ │
│  │ (Key-Value)     │  │ (ChromaDB)      │  │ (In-Memory)  │ │
│  │                 │  │                 │  │              │ │
│  │ - Cache rápido  │  │ - Embeddings    │  │ - Contexto   │ │
│  │ - Sessões       │  │ - Busca semânt. │  │ - Conversas  │ │
│  │ - Temporário    │  │ - RAG           │  │ - Sliding    │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                    EpisodicMemory                        │ │
│  │                                                          │ │
│  │  - Sequências de eventos                                 │ │
│  │  - Lições aprendidas                                     │ │
│  │  - Histórico de decisões                                 │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Sistema RAG

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Documento   │────▶│  Processor   │────▶│   Chunks     │
│              │     │  - Chunk     │     │              │
│              │     │  - Embed     │     │              │
└──────────────┘     └──────────────┘     └──────┬───────┘
                                                  │
                                                  ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Resposta   │◀────│     LLM      │◀────│  Retriever   │
│   + Fontes   │     │   + Context  │     │  (Top-K)     │
└──────────────┘     └──────────────┘     └──────────────┘
```

## MCPs (Model Context Protocols)

```
mcps/
├── mcp-intelbras-cftv/      # Câmeras Intelbras
├── mcp-hikvision-cftv/      # Câmeras Hikvision
├── mcp-control-id/          # Controle de acesso
├── mcp-intelbras-acesso/    # Acesso Intelbras
├── mcp-ppa/                 # Portões PPA
├── mcp-garen/               # Portões Garen
├── mcp-jfl/                 # Alarmes JFL
├── mcp-intelbras-alarme/    # Alarmes Intelbras
├── mcp-ubiquiti/            # Rede UniFi
├── mcp-mikrotik/            # Rede MikroTik
├── mcp-asterisk/            # VoIP
├── mcp-whisper/             # Transcrição áudio
├── mcp-vision-ai/           # Visão computacional
├── mcp-llm-agents/          # Agentes LLM
├── mcp-boletos/             # Geração boletos
├── mcp-pix/                 # Pagamentos PIX
├── mcp-nfse/                # Notas fiscais
├── mcp-esocial/             # eSocial
├── mcp-ponto-rep/           # Ponto eletrônico
├── mcp-assinatura-digital/  # Assinatura digital
├── mcp-mqtt/                # IoT MQTT
└── mcp-medidores/           # Medição água/gás
```

## Fluxo de Dados

### 1. Requisição do Usuário

```
Frontend → Nginx → API Gateway → [Validação JWT]
                                       ↓
                               [Rota apropriada]
                                       ↓
                               [Lógica de negócio]
                                       ↓
                               [Banco de dados]
                                       ↓
                               [Resposta JSON]
```

### 2. Evento de IA (CFTV)

```
Câmera → Guardian (YOLO) → [Detecção]
                               ↓
                        AI Orchestrator
                               ↓
                        Agente CFTV
                               ↓
                   [Análise/Decisão/Ação]
                               ↓
              ┌────────────────┼────────────────┐
              ↓                ↓                ↓
        Notificação      Gravação         Alarme
```

### 3. Colaboração entre Agentes

```
Agente CFTV ──[invasão detectada]──▶ Agente Acesso
                                          ↓
                                   [bloquear acessos]
                                          ↓
Agente Alarme ◀──[ativar sirene]────────────
       ↓
[notificar emergência]
       ↓
Agente Comunicação ──▶ [enviar SMS/WhatsApp]
```

## Docker Compose Services

| Serviço | Porta | Descrição |
|---------|-------|-----------|
| postgres | 5432 | Banco de dados principal |
| redis | 6379 | Cache e filas |
| mongodb | 27017 | Logs e documentos |
| api-gateway | 3001 | Backend FastAPI |
| frontend | 3000 | Next.js |
| ai-orchestrator | 8001 | Orquestrador de IA |
| guardian | - | Sistema de visão IA |
| nginx | 80/443 | Proxy reverso |
| prometheus | 9090 | Métricas |
| grafana | 3002 | Dashboards |
| loki | 3100 | Logs |
| rabbitmq | 5672/15672 | Message broker |

## Segurança

### Autenticação
- JWT com refresh tokens
- Tempo de expiração: 24h
- Blacklist de tokens revogados

### Autorização
- RBAC (Role-Based Access Control)
- Roles: admin, sindico, porteiro, morador, visitante

### Proteções
- Rate limiting (10 req/s API, 5 req/min login)
- CORS configurado
- Headers de segurança (X-Frame-Options, CSP, etc.)
- Validação de entrada
- Sanitização de dados

## Monitoramento

### Métricas (Prometheus)
- Requests por endpoint
- Latência de resposta
- Erros por tipo
- Uso de recursos (CPU, memória)

### Logs (Loki)
- Logs estruturados JSON
- Níveis: DEBUG, INFO, WARNING, ERROR
- Retenção: 30 dias

### Alertas (Grafana)
- CPU > 80%
- Memória > 85%
- Latência > 2s
- Taxa de erro > 1%

## Escalabilidade

### Horizontal
- Frontend: múltiplas réplicas atrás do Nginx
- API Gateway: múltiplas instâncias
- Agentes: por demanda

### Vertical
- PostgreSQL: otimização de queries, índices
- Redis: cluster mode
- MongoDB: sharding se necessário

## Deployment

### Desenvolvimento
```bash
docker-compose up -d
```

### Produção
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### CI/CD
- GitHub Actions para testes
- Build automático de imagens
- Deploy via SSH/Docker

## Variáveis de Ambiente

```env
# Banco de dados
POSTGRES_USER=conecta_user
POSTGRES_PASSWORD=<secret>
POSTGRES_DB=conecta_db

# Redis
REDIS_PASSWORD=<secret>

# MongoDB
MONGO_USER=conecta
MONGO_PASSWORD=<secret>

# JWT
JWT_SECRET=<secret>

# APIs de IA
ANTHROPIC_API_KEY=<secret>
OPENAI_API_KEY=<secret>

# Notificações
WHATSAPP_TOKEN=<secret>
TELEGRAM_TOKEN=<secret>
SMTP_HOST=<host>
SMTP_USER=<user>
SMTP_PASS=<secret>
```

## Contribuição

1. Fork o repositório
2. Crie branch de feature
3. Implemente com testes
4. Abra Pull Request

## Licença

Proprietário - Conecta Plus
