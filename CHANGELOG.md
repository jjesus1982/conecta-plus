# Changelog

Todas as mudanças notáveis neste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere ao [Versionamento Semântico](https://semver.org/lang/pt-BR/).

---

## [2.0.1] - 2025-12-25

### Corrigido
- Autenticação Redis no backend-q1 (health check 100% healthy)
- Remoção de código Guardian legado não utilizado
- Configuração de rede Docker para comunicação entre containers

### Adicionado
- README.md completo com documentação do projeto
- CHANGELOG.md para histórico de versões
- CI/CD workflow GitHub Actions

---

## [2.0.0] - 2025-12-22

### Adicionado

#### Backend
- 21 routers FastAPI implementados
- 22 modelos SQLAlchemy com PostgreSQL
- Sistema de Health Check unificado com circuit breakers
- API Gateway com autenticação JWT
- Integração com Banco Cora para boletos
- NLP Engine com análise de sentimento
- Sistema de eventos em tempo real (SSE)
- Observabilidade com logging estruturado
- Circuit breakers para resiliência

#### Frontend
- 27 páginas Next.js implementadas
- 63 componentes React/TypeScript
- Dashboard com gráficos Recharts
- Sistema de autenticação completo
- UI com Tailwind CSS + Radix UI
- React Query para gerenciamento de estado
- Zustand para estado global

#### Agentes IA
- 42 agentes implementados
- 8 categorias especializadas
- Message Bus para comunicação inter-agentes
- Base agent com padrão consistente
- Integração com LLMs (Claude/GPT)

#### Inteligência Proativa (Q2)
- Sistema de Previsões
- Engine de Sugestões
- Alertas Enriquecidos
- Tranquilidade do Porteiro/Morador
- Learning Engine para melhoria contínua

#### Integrações (MCPs)
- 27 MCPs implementados
- Intelbras (CFTV, Acesso, Alarme)
- Hikvision (CFTV)
- Control iD (Acesso)
- MikroTik (Rede)
- Asterisk/Issabel (VoIP)
- E mais...

#### Infraestrutura
- Docker Compose configurado
- 8 containers em produção
- Nginx como proxy reverso
- SSL/HTTPS configurado
- Prometheus para métricas
- System Monitor Agent autônomo

### Modificado
- Migração de endpoints MOCK para PostgreSQL
- Atualização de dependências frontend (Next.js 16, React 19)
- Refatoração de agentes especializados

---

## [1.0.0] - 2025-12-18

### Adicionado
- Estrutura inicial do projeto
- Setup de Docker e Docker Compose
- Configuração de bancos de dados (PostgreSQL, Redis, MongoDB)
- Frontend básico Next.js
- Backend básico FastAPI
- Primeiros agentes IA
- Documentação inicial

---

## Versões Futuras

### [2.1.0] - Planejado
- [ ] Testes E2E com Playwright
- [ ] Cobertura de testes 80%+
- [ ] Dashboards Grafana
- [ ] Mobile app (React Native)
- [ ] Integração WhatsApp Business

### [3.0.0] - Planejado
- [ ] Kubernetes deployment
- [ ] Multi-region support
- [ ] Real-time video analytics
- [ ] Voice assistant integration
