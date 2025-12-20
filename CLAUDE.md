# CLAUDE.md - Conecta Plus

## PROXIMA TAREFA PENDENTE

**Arquivo de Sessao**: `/opt/conecta-plus/SESSAO_GUARDIAN_20251220.md`

**Objetivo**: Completar integracao do Guardian (100%)

**Status Atual**:
- Sistema em producao: Backend, Frontend, Nginx, DBs
- Guardian: Codigo existe mas rodando em modo degradado
- Agentes IA: 6 agentes implementados (5.095 linhas)

**Proximos Passos**:
1. Criar modelos de banco para Guardian
2. Atualizar service com persistencia
3. Criar containers Docker (Guardian + AI Orchestrator)
4. Testar todos os 20 endpoints
5. Ativar integracao com cameras

---

## Visao Geral do Projeto

**Conecta Plus** e uma plataforma SaaS integrada de gestao condominial desenvolvida pela **Conecta Mais** (empresa de seguranca eletronica). O sistema oferece 14 modulos, 24 agentes de IA e 80+ submodulos para gestao completa de condominios.

### Modelo de Negocio
- **Sindicos**: Acesso FREE (limitado)
- **Condominios**: Assinatura PAID (completo)
- **Multi-tenant**: Conecta Mais > Sindicos > Condominios > Unidades

### Stack Tecnologico

#### Backend
- **Python 3.11+**: FastAPI, LangChain, Celery
- **Node.js 20+**: TypeScript, Express
- **Bancos**: PostgreSQL 16, Redis 7, MongoDB 7

#### Frontend
- **Next.js 14**: React, TypeScript, TailwindCSS
- **Mobile**: React Native / Flutter

#### IA/ML
- **LLMs**: Claude (Anthropic), GPT-4 (OpenAI)
- **Visao**: YOLO v8, InsightFace, EasyOCR
- **Audio**: Whisper (faster-whisper)
- **Orquestracao**: LangChain, MCPs

#### Infraestrutura
- **Containers**: Docker, Kubernetes
- **Proxy**: Nginx
- **Monitoramento**: Prometheus, Grafana, Loki
- **CI/CD**: GitHub Actions

---

## Estrutura de Diretorios

```
/opt/conecta-plus/
├── apps/                    # Aplicacoes principais
│   ├── guardian/           # Sistema de monitoramento IA
│   ├── workplace/          # Portal do colaborador
│   ├── portaria/           # Sistema de portaria
│   ├── condomino/          # App do morador
│   ├── financeiro/         # Gestao financeira
│   ├── comunicacao/        # Central de comunicacao
│   ├── facilities/         # Gestao de facilidades
│   ├── assembleias/        # Sistema de assembleias
│   ├── reservas/           # Reserva de areas
│   ├── analytics/          # BI e dashboards
│   ├── encomendas/         # Gestao de encomendas
│   ├── ocorrencias/        # Gestao de ocorrencias
│   ├── manutencao/         # Ordens de servico
│   └── compliance/         # Conformidade
│
├── services/               # Microsservicos
│   ├── api-gateway/        # Gateway central
│   ├── auth-service/       # Autenticacao
│   ├── notification-service/ # Notificacoes
│   ├── media-service/      # Processamento de midia
│   ├── ai-orchestrator/    # Orquestrador de agentes
│   └── integration-hub/    # Hub de integracoes
│
├── agents/                 # 24 Agentes de IA
│   ├── base/              # Classe base
│   ├── cftv/              # Monitoramento de cameras
│   ├── acesso/            # Controle de acesso
│   ├── automacao/         # Portoes e automacao
│   ├── alarme/            # Centrais de alarme
│   ├── rede/              # Infraestrutura de rede
│   ├── portaria-virtual/  # Atendimento remoto
│   ├── rh/                # Recursos humanos
│   ├── facilities/        # Gestao de facilidades
│   ├── manutencao/        # Manutencoes
│   ├── sindico/           # Assistente do sindico
│   ├── financeiro/        # Gestao financeira
│   ├── assembleias/       # Assembleias
│   ├── reservas/          # Reservas
│   ├── morador/           # Assistente do morador
│   ├── comunicacao/       # Comunicacoes
│   ├── encomendas/        # Encomendas
│   ├── ocorrencias/       # Ocorrencias
│   ├── analytics/         # Analytics e BI
│   ├── visao-ia/          # Visao computacional
│   ├── compliance/        # Conformidade
│   ├── voip/              # Telefonia IP
│   ├── infraestrutura/    # Infraestrutura TI
│   ├── suporte/           # Suporte tecnico
│   └── comercial/         # Vendas
│
├── mcps/                   # 24 Model Context Protocols
│   ├── mcp-intelbras-cftv/    # DVR/NVR Intelbras
│   ├── mcp-hikvision-cftv/    # DVR/NVR Hikvision
│   ├── mcp-control-id/        # Controladoras Control iD
│   ├── mcp-intelbras-acesso/  # Controladoras Intelbras
│   ├── mcp-ppa/               # Motores PPA
│   ├── mcp-garen/             # Motores Garen
│   ├── mcp-nice/              # Motores Nice
│   ├── mcp-jfl/               # Alarmes JFL
│   ├── mcp-intelbras-alarme/  # Alarmes Intelbras AMT
│   ├── mcp-ubiquiti/          # UniFi Controller
│   ├── mcp-mikrotik/          # RouterOS
│   ├── mcp-furukawa/          # OLTs GPON
│   ├── mcp-asterisk/          # PBX Asterisk
│   ├── mcp-issabel/           # PBX Issabel
│   ├── mcp-whisper/           # Transcricao de audio
│   ├── mcp-vision-ai/         # Visao computacional
│   ├── mcp-boletos/           # Geracao de boletos
│   ├── mcp-pix/               # API PIX
│   ├── mcp-nfse/              # Emissao de NFS-e
│   ├── mcp-esocial/           # Integracao eSocial
│   ├── mcp-ponto-rep/         # Relogio de ponto
│   ├── mcp-assinatura-digital/ # Assinatura eletronica
│   ├── mcp-mqtt/              # Broker MQTT
│   └── mcp-medidores/         # Leitura de medidores
│
├── integrations/           # Integracoes externas
│   ├── cameras/           # ONVIF, RTSP, HLS
│   ├── network/           # MikroTik, UniFi
│   └── messaging/         # WhatsApp, Telegram, Email
│
├── guardian/              # IA de monitoramento
│   ├── detector/          # YOLO detector
│   └── config/            # Configuracoes
│
├── config/                # Configuracoes
│   ├── nginx/             # Nginx configs
│   ├── redis/             # Redis configs
│   └── postgres/          # PostgreSQL configs
│
├── infrastructure/        # IaC
│   ├── docker/           # Dockerfiles
│   ├── kubernetes/       # K8s manifests
│   ├── terraform/        # Terraform
│   ├── ansible/          # Ansible playbooks
│   └── scripts/          # Scripts utilitarios
│
├── shared/               # Recursos compartilhados
│   ├── logs/            # Logs centralizados
│   ├── backups/         # Backups
│   ├── uploads/         # Uploads
│   ├── models/          # Modelos ML
│   └── templates/       # Templates
│
├── monitoring/           # Monitoramento
│   ├── prometheus/      # Metricas
│   ├── grafana/         # Dashboards
│   ├── loki/            # Logs
│   └── jaeger/          # Tracing
│
├── scripts/              # Scripts utilitarios
│   ├── backup.sh        # Backup automatizado
│   ├── deploy.sh        # Deploy
│   ├── health-check.sh  # Verificacao de saude
│   └── logs.sh          # Visualizador de logs
│
├── docker-compose.yml    # Compose completo
├── docker-compose.base.yml # Compose basico
├── .env                  # Variaveis de ambiente
└── CLAUDE.md            # Este arquivo
```

---

## Comandos Essenciais

### Docker

```bash
# Iniciar todos os servicos
docker compose up -d

# Iniciar apenas infra basica
docker compose -f docker-compose.base.yml up -d

# Ver logs
docker compose logs -f [servico]

# Parar servicos
docker compose down

# Rebuild de servico
docker compose build [servico] --no-cache
```

### Scripts

```bash
# Backup do sistema
./scripts/backup.sh

# Verificar saude
./scripts/health-check.sh

# Ver logs
./scripts/logs.sh [servico]

# Deploy
./scripts/deploy.sh [ambiente]
```

### Banco de Dados

```bash
# Conectar ao PostgreSQL
docker exec -it conecta-postgres psql -U conecta_user -d conecta_db

# Conectar ao Redis
docker exec -it conecta-redis redis-cli -a $REDIS_PASSWORD

# Conectar ao MongoDB
docker exec -it conecta-mongodb mongosh -u conecta -p $MONGO_PASSWORD
```

---

## Arquitetura de Agentes

### Orquestrador Central
O **AI Orchestrator** (`services/ai-orchestrator/`) roteia requisicoes para os 24 agentes especializados usando:
1. Analise de keywords
2. Roteamento por LLM quando ambiguo
3. Coordenacao multi-agente para tarefas complexas

### Agentes por Categoria

**Seguranca Eletronica:**
- `cftv` - Cameras e gravacao
- `acesso` - Controle de acesso
- `automacao` - Portoes
- `alarme` - Centrais de alarme

**Infraestrutura:**
- `rede` - Redes e WiFi
- `voip` - Telefonia IP
- `infraestrutura` - TI

**Operacional:**
- `portaria_virtual` - Atendimento
- `facilities` - Areas comuns
- `manutencao` - Ordens de servico
- `encomendas` - Pacotes
- `ocorrencias` - Incidentes
- `reservas` - Espacos

**Administrativo:**
- `sindico` - Assistente do sindico
- `financeiro` - Financas
- `rh` - Recursos humanos
- `assembleias` - Votacoes
- `compliance` - Conformidade

**Usuarios:**
- `morador` - App do morador
- `comunicacao` - Notificacoes

**IA/Analytics:**
- `visao_ia` - Visao computacional
- `analytics` - BI e relatorios

**Comercial:**
- `suporte` - Atendimento
- `comercial` - Vendas

---

## MCPs (Model Context Protocols)

### Seguranca Eletronica (16)
| MCP | Descricao |
|-----|-----------|
| mcp-intelbras-cftv | DVR/NVR Intelbras |
| mcp-hikvision-cftv | DVR/NVR Hikvision (ISAPI) |
| mcp-control-id | Controladoras Control iD |
| mcp-intelbras-acesso | Controladoras SS/CT |
| mcp-ppa | Motores PPA |
| mcp-garen | Motores Garen |
| mcp-nice | Motores Nice |
| mcp-jfl | Alarmes JFL |
| mcp-intelbras-alarme | Alarmes AMT |
| mcp-ubiquiti | UniFi Controller |
| mcp-mikrotik | RouterOS API |
| mcp-furukawa | OLTs GPON |
| mcp-asterisk | PBX AMI |
| mcp-issabel | PBX Issabel |
| mcp-whisper | Transcricao audio |
| mcp-vision-ai | YOLO/InsightFace/OCR |

### Gestao Condominial (8)
| MCP | Descricao |
|-----|-----------|
| mcp-boletos | Geracao CNAB 240/400 |
| mcp-pix | API PIX BACEN |
| mcp-nfse | Emissao NFS-e |
| mcp-esocial | Eventos eSocial |
| mcp-ponto-rep | REP/AFD |
| mcp-assinatura-digital | Assinatura eletronica |
| mcp-mqtt | IoT MQTT |
| mcp-medidores | Agua/Gas/Energia |

---

## Variaveis de Ambiente

```env
# Banco de Dados
POSTGRES_USER=conecta_user
POSTGRES_PASSWORD=<senha_segura>
POSTGRES_DB=conecta_db

# Cache
REDIS_PASSWORD=<senha_segura>

# MongoDB
MONGO_USER=conecta
MONGO_PASSWORD=<senha_segura>

# JWT
JWT_SECRET=<chave_segura>

# APIs de IA
ANTHROPIC_API_KEY=<sua_chave>
OPENAI_API_KEY=<sua_chave>

# Mensageria
WHATSAPP_TOKEN=<token>
TELEGRAM_TOKEN=<token>
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=<email>
SMTP_PASS=<senha>
```

---

## Regras de Desenvolvimento

1. **Sempre use TypeScript/Python tipado**
2. **Documente funcoes e classes**
3. **Testes obrigatorios para features novas**
4. **Code review antes de merge**
5. **Commits semanticos (feat:, fix:, docs:, etc)**
6. **Nao commitar secrets/.env**
7. **LGPD: cuidado com dados pessoais**

---

## Endpoints Principais

| Servico | Porta | Endpoint |
|---------|-------|----------|
| API Gateway | 8000 | /api/v1/* |
| AI Orchestrator | 8001 | /process, /status, /agents |
| PostgreSQL | 5432 | - |
| Redis | 6379 | - |
| MongoDB | 27017 | - |
| Prometheus | 9090 | /metrics |
| Grafana | 3001 | / |
| RabbitMQ | 15672 | / |

---

## Contato

- **Empresa**: Conecta Mais
- **Projeto**: Conecta Plus
- **Repositorio**: /opt/conecta-plus

---

*Documentacao atualizada em 2025-12-18*
*Versao: 2.0.0*
