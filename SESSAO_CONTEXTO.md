# Contexto da Sessão - Conecta Plus
**Data:** 2025-12-18
**Objetivo:** Continuidade do desenvolvimento dos agentes de IA

---

## O Que Foi Discutido

### 1. Usuário quer instalar o GUARDIAN
- Usuário mencionou que estava falando sobre instalar o Guardian
- Quer subir o código fonte para refinar e instalar no Conecta Plus
- **PENDENTE:** Aguardando código fonte do Guardian do usuário

### 2. Verificação de Status dos Agentes de IA
Foi feita uma análise completa de todos os agentes em `/opt/conecta-plus/agents/`

---

## Status Atual dos Agentes

### ✅ TOTALMENTE IMPLEMENTADOS (35 agentes)

#### Tier 1 - Muito Completos (>1500 linhas) - PRODUÇÃO
| Agente | Linhas | Métodos | Arquivo |
|--------|--------|---------|---------|
| portaria-virtual | 2254 | 47 | agent_v2.py |
| auditoria | 1980 | 64 | agent_v2.py |
| fornecedores | 1900 | 37 | agent_v2.py |
| atendimento | 1567 | 34 | agent_v2.py |

#### Tier 2 - Completos (800-1500 linhas)
| Agente | Linhas | Métodos |
|--------|--------|---------|
| valorizacao | 1480 | 32 |
| acesso | 1140 | 28 |
| cftv | 1128 | 29 |
| financeiro | 1108 | 21 |
| juridico | 1077 | 26 |
| sindico | 991 | 31 |
| emergencia | 918 | 24 |
| estacionamento | 882 | 22 |
| social | 860 | 25 |
| pet | 858 | 23 |
| sustentabilidade | 843 | 22 |
| imobiliario | 839 | 21 |
| conhecimento | 810 | 22 |

#### Tier 3 - Moderados (400-799 linhas) - 18 agentes
- comercial (610 linhas, 17 métodos)
- analytics (516 linhas, 16 métodos)
- assembleias (529 linhas, 16 métodos)
- suporte (524 linhas, 16 métodos)
- reservas (523 linhas, 16 métodos)
- compliance (522 linhas, 15 métodos)
- visao-ia (533 linhas, 16 métodos)
- ocorrencias (492 linhas, 15 métodos)
- infraestrutura (491 linhas, 16 métodos)
- voip (493 linhas, 16 métodos)
- facilities (482 linhas, 17 métodos)
- rh (473 linhas, 17 métodos)
- manutencao (462 linhas, 16 métodos)
- comunicacao (457 linhas, 15 métodos)
- morador (448 linhas, 16 métodos)
- encomendas (431 linhas, 15 métodos)
- automacao (424 linhas, 15 métodos)
- rede (453 linhas, 17 métodos)

### ⚠️ IMPLEMENTAÇÃO MÍNIMA (1 agente)
| Agente | Linhas | Métodos | Observação |
|--------|--------|---------|------------|
| alarme | 321 | 15 | Funcional mas precisa expansão |

### ❌ NÃO IMPLEMENTADOS (Diretórios vazios)
- `/opt/conecta-plus/agents/memory/` - vazio
- `/opt/conecta-plus/agents/skills/` - vazio
- `/opt/conecta-plus/agents/tools/` - vazio
- `/opt/conecta-plus/agents/specialized/` - 8 subdiretórios vazios:
  - specialized/acesso/
  - specialized/cftv/
  - specialized/comunicacao/
  - specialized/financeiro/
  - specialized/manutencao/
  - specialized/ocorrencias/
  - specialized/portaria/
  - specialized/sindico/

---

## Core Framework (100% Implementado)

| Módulo | Linhas | Função |
|--------|--------|--------|
| tools.py | 936 | Registry de ferramentas |
| llm_client.py | 825 | Cliente LLM unificado (Claude, GPT, Ollama) |
| message_bus.py | 803 | Comunicação entre agentes |
| rag_system.py | 691 | Sistema RAG |
| memory_store.py | 606 | Memória Redis/Vector/Episódica |
| base_agent.py | 565 | Classe base para todos agentes |
| __init__.py | 125 | Exports |

**Total Core:** 4.551 linhas

---

## Resumo Numérico

| Métrica | Valor |
|---------|-------|
| Agentes prontos para produção | 4 |
| Agentes completos | 13 |
| Agentes funcionais | 18 |
| Agentes básicos | 1 |
| **Total implementado** | **36 agentes** |
| Diretórios vazios | 4 |
| Total linhas de código | ~29.500 |

---

## Arquitetura do Sistema

### Localização
- **Projeto:** `/opt/conecta-plus/`
- **Agentes:** `/opt/conecta-plus/agents/`
- **MCPs:** `/opt/conecta-plus/mcps/` (24+ protocolos)
- **Serviços:** `/opt/conecta-plus/services/`
- **Apps:** `/opt/conecta-plus/apps/`

### Stack Tecnológico
- **Backend:** Python 3.11+, FastAPI, Node.js 20+
- **LLMs:** Claude (primário), GPT-4, Ollama
- **DBs:** PostgreSQL 16, Redis 7, MongoDB 7
- **AI/ML:** YOLO v8, InsightFace, EasyOCR, faster-whisper
- **Infra:** Docker, Kubernetes, Nginx

### Portas dos Serviços
- API Gateway: 8000
- AI Orchestrator: 8001
- PostgreSQL: 5432
- Redis: 6379
- MongoDB: 27017
- Prometheus: 9090
- Grafana: 3001
- RabbitMQ: 5672, 15672

---

## Próximos Passos (PENDENTES)

### Prioridade Alta
1. **[ ] Instalar GUARDIAN** - Aguardando código fonte do usuário
2. **[ ] Expandir agente alarme** - Atualmente com apenas 321 linhas

### Prioridade Média
3. **[ ] Implementar diretórios vazios:**
   - agents/memory/
   - agents/skills/
   - agents/tools/
   - agents/specialized/ (8 subdiretórios)

### Prioridade Baixa
4. **[ ] Testes de integração entre agentes**
5. **[ ] Documentação de APIs dos agentes**

---

## Comandos Úteis

```bash
# Navegar para o projeto
cd /opt/conecta-plus

# Ver estrutura de agentes
ls -la /opt/conecta-plus/agents/

# Ver um agente específico
cat /opt/conecta-plus/agents/cftv/agent_v2.py

# Docker
docker-compose -f docker-compose.yml up -d

# Logs
docker-compose logs -f
```

---

## Arquivos Importantes

| Arquivo | Descrição |
|---------|-----------|
| `/opt/conecta-plus/CLAUDE.md` | Documentação principal do projeto |
| `/opt/conecta-plus/RELATORIO_SETUP.md` | Relatório de setup |
| `/opt/conecta-plus/.env` | Configurações e credenciais |
| `/opt/conecta-plus/docker-compose.yml` | Stack completa |
| `/root/.credentials/conecta-plus.env` | Credenciais (read-only) |

---

## Para Continuar a Sessão

Ao iniciar nova sessão, diga:
> "Leia o arquivo /opt/conecta-plus/SESSAO_CONTEXTO.md para continuar de onde paramos"

Ou:
> "Continue o desenvolvimento do Conecta Plus - veja SESSAO_CONTEXTO.md"

---

*Última atualização: 2025-12-18*
