# INVENTARIO GUARDIAN - AUDITORIA COMPLETA
## Projeto Conecta Plus - Modulo de Seguranca

**Data da Auditoria:** 2025-12-20
**Versao do Projeto:** 2.0.0
**Auditor:** Claude Code Guardian

---

## 1. RESUMO EXECUTIVO

### Descoberta Principal
O projeto **Guardian** NAO existe como sistema isolado em `/opt/guardian`. O Guardian e o **modulo de seguranca eletronica** integrado ao **Conecta Plus**, uma plataforma completa de gestao condominial localizada em `/opt/conecta-plus`.

### Escopo Real do Projeto
- **14 modulos** de gestao condominial
- **44 agentes de IA** especializados
- **27 MCPs** (Model Context Protocol)
- **17 routers** de API
- **20 paginas** no frontend

### Stack Tecnologico

| Camada | Tecnologia | Versao |
|--------|------------|--------|
| Backend | Python FastAPI | 3.11+ |
| Frontend | Next.js | 16.0.10 |
| Frontend | React | 19.2.1 |
| Frontend | TypeScript | 5.x |
| Banco Principal | PostgreSQL | 16 |
| Cache | Redis | 7 |
| Documentos | MongoDB | 7 |
| IA Visao | YOLO | v8 |
| NVR | Frigate | Integrado |

---

## 2. ESTRUTURA DO PROJETO

```
/opt/conecta-plus/
├── apps/                    # 14 aplicacoes modulares
├── agents/                  # 44 agentes de IA
├── mcps/                    # 27 MCPs
├── backend/                 # API FastAPI
├── frontend/                # Next.js 16
├── guardian/                # Modulo YOLO/Visao
├── services/                # Microsservicos
├── integrations/            # Integracoes externas
├── config/                  # Configuracoes
├── docker/                  # Docker configs
├── monitoring/              # Prometheus/Grafana
├── scripts/                 # Utilitarios
├── docker-compose.yml       # Orquestracao
└── CLAUDE.md               # Documentacao
```

---

## 3. BACKEND - ANALISE COMPLETA

### 3.1 Routers da API (17 endpoints)

| Router | Arquivo | Tamanho | Status |
|--------|---------|---------|--------|
| auth | auth.py | 19.4 KB | ✅ Completo |
| usuarios | usuarios.py | 4.9 KB | ✅ Completo |
| condominios | condominios.py | 2.4 KB | ✅ Completo |
| unidades | unidades.py | 2.9 KB | ✅ Completo |
| moradores | moradores.py | 3.6 KB | ✅ Completo |
| acesso | acesso.py | 7.3 KB | ✅ Completo |
| ocorrencias | ocorrencias.py | 6.1 KB | ✅ Completo |
| manutencao | manutencao.py | 5.8 KB | ✅ Completo |
| financeiro | financeiro.py | 7.1 KB | ✅ Completo |
| alarmes | alarmes.py | 10.5 KB | ✅ Completo |
| reservas | reservas.py | 7.3 KB | ✅ Completo |
| comunicados | comunicados.py | 4.7 KB | ✅ Completo |
| assembleias | assembleias.py | 9.7 KB | ✅ Completo |
| dashboard | dashboard.py | 5.6 KB | ✅ Completo |
| frigate | frigate.py | 20.1 KB | ✅ Completo |
| dispositivos | dispositivos.py | 8.1 KB | ✅ Completo |

**Total de linhas de codigo nos routers:** ~3.500 linhas

### 3.2 Servicos Backend

| Servico | Arquivo | Linhas | Descricao |
|---------|---------|--------|-----------|
| frigate.py | 481 | Integracao Frigate NVR |
| hardware.py | 1.105 | Comunicacao com dispositivos |
| ldap.py | 348 | Autenticacao LDAP/AD |
| oauth.py | 268 | OAuth 2.0 / SSO |

**Destaque:** `hardware.py` implementa drivers para:
- Control iD (iDAccess, iDFlex, iDBlock)
- Intelbras (DVR, Controladoras)
- Hikvision (ISAPI)
- PPA/Garen/Nice (Portoes)
- JFL/Paradox (Alarmes)

### 3.3 Modelos de Banco de Dados (15 entidades)

| Modelo | Campos Principais | Relacionamentos |
|--------|-------------------|-----------------|
| Usuario | id, nome, email, role, condominio_id | Condominio, Acessos |
| Condominio | id, nome, cnpj, endereco | Unidades, Usuarios |
| Unidade | id, numero, bloco, tipo, condominio_id | Moradores, Veiculos |
| Morador | id, nome, cpf, tipo, unidade_id | Acessos, Veiculos |
| Veiculo | id, placa, modelo, cor, morador_id | Acessos |
| RegistroAcesso | id, tipo, ponto_id, data_hora | Ponto, Usuario |
| PontoAcesso | id, nome, device_id, condominio_id | Acessos |
| Ocorrencia | id, tipo, status, descricao | Usuario, Anexos |
| OrdemServico | id, tipo, status, fornecedor_id | Fornecedor |
| Lancamento | id, tipo, valor, vencimento | Unidade, Boleto |
| Boleto | id, codigo, status, valor | Lancamento |
| ZonaAlarme | id, nome, status, condominio_id | Eventos |
| EventoAlarme | id, tipo, zona_id, timestamp | Zona |
| AreaComum | id, nome, capacidade | Reservas |
| Reserva | id, data, horario, status | Area, Usuario |
| Comunicado | id, titulo, tipo, data | Condominio |
| Assembleia | id, data, pauta, status | Votacoes, Ata |

---

## 4. FRONTEND - ANALISE COMPLETA

### 4.1 Stack Frontend

```json
{
  "next": "16.0.10",
  "react": "19.2.1",
  "typescript": "5.x",
  "tailwindcss": "4.x",
  "zustand": "5.0.9",
  "recharts": "3.6.0",
  "radix-ui": "latest",
  "lucide-react": "0.562.0"
}
```

### 4.2 Paginas Implementadas (20)

| Pagina | Arquivo | Tamanho | Status |
|--------|---------|---------|--------|
| Home | page.tsx | 1.7 KB | ✅ |
| Login | login/page.tsx | - | ✅ |
| Dashboard | dashboard/page.tsx | - | ✅ |
| CFTV | cftv/page.tsx | 18.4 KB | ✅ Destaque |
| Acesso | acesso/page.tsx | - | ✅ |
| Alarmes | alarmes/page.tsx | - | ✅ |
| Alertas | alertas/page.tsx | - | ✅ |
| Assembleias | assembleias/page.tsx | - | ✅ |
| Comunicados | comunicados/page.tsx | - | ✅ |
| Configuracoes | configuracoes/page.tsx | - | ✅ |
| Encomendas | encomendas/page.tsx | - | ✅ |
| Financeiro | financeiro/page.tsx | - | ✅ |
| Manutencao | manutencao/page.tsx | - | ✅ |
| Moradores | moradores/page.tsx | - | ✅ |
| Ocorrencias | ocorrencias/page.tsx | - | ✅ |
| Portaria | portaria/page.tsx | - | ✅ |
| Relatorios | relatorios/page.tsx | - | ✅ |
| Reservas | reservas/page.tsx | - | ✅ |
| Unidades | unidades/page.tsx | - | ✅ |

### 4.3 Componentes UI

```
src/components/
├── ui/                  # Radix UI + Tailwind
│   ├── card.tsx
│   ├── button.tsx
│   ├── dialog.tsx
│   ├── dropdown.tsx
│   ├── select.tsx
│   ├── tabs.tsx
│   └── toast.tsx
├── layout/             # Layout components
├── forms/              # Formularios
├── tables/             # Tabelas de dados
└── charts/             # Graficos Recharts
```

### 4.4 Gerenciamento de Estado

- **Zustand 5.0.9** para estado global
- Stores em `src/stores/`
- Hooks customizados em `src/hooks/`

---

## 5. MODULO GUARDIAN (SEGURANCA)

### 5.1 Componente Python (`/opt/conecta-plus/guardian/`)

```
guardian/
├── detector/
│   └── yolo_detector.py    # 15.6 KB - Detector YOLO v8
├── config/
│   └── default.yaml        # Configuracoes
├── recorder/               # Gravacao
├── streams/                # Streaming
├── snapshots/              # Capturas
└── requirements.txt        # Dependencias
```

#### Dependencias Guardian (Python)
```
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
ultralytics>=8.0.0          # YOLO v8
opencv-python-headless>=4.8.0
numpy>=1.24.0
onvif-zeep>=0.2.12         # ONVIF
wsdiscovery>=2.0.0
aiohttp>=3.9.0
```

### 5.2 Detector YOLO (`yolo_detector.py`)

**Funcionalidades implementadas:**
- ✅ Deteccao de objetos (80 classes COCO)
- ✅ Processamento de imagens
- ✅ Processamento de frames de video
- ✅ Streaming em tempo real (RTSP)
- ✅ Suporte GPU (CUDA) e CPU
- ✅ Configuracoes customizaveis
- ✅ Sistema de alertas (`AlertManager`)
- ✅ Regras de deteccao por zona
- ✅ Cooldown entre alertas

**Classes detectadas:**
- person, car, truck, bus, motorcycle
- bicycle, dog, cat, bird
- backpack, handbag, suitcase
- cell phone, laptop, tv
- E mais 65 classes COCO

### 5.3 Integracao Frigate NVR

**Router completo (`frigate.py` - 694 linhas):**
- ✅ Gerenciamento de instancias Frigate
- ✅ Listagem de cameras
- ✅ Snapshots em tempo real
- ✅ Controle de deteccao (ON/OFF)
- ✅ Controle de gravacao (ON/OFF)
- ✅ Streaming (RTSP, HLS, WebRTC, MSE)
- ✅ Busca de eventos por filtros
- ✅ Retencao de eventos
- ✅ Listagem de gravacoes
- ✅ Resumo de gravacoes por hora/dia
- ✅ Controle PTZ completo
- ✅ Gerenciamento de zonas

---

## 6. AGENTES DE IA (44)

### 6.1 Distribuicao por Categoria

| Categoria | Agentes | Total |
|-----------|---------|-------|
| Seguranca | cftv, acesso, automacao, alarme | 4 |
| Infraestrutura | rede, voip, infraestrutura | 3 |
| Operacional | portaria-virtual, facilities, manutencao, encomendas, ocorrencias, reservas, estacionamento | 7 |
| Administrativo | sindico, financeiro, rh, assembleias, compliance, juridico | 6 |
| Usuarios | morador, comunicacao | 2 |
| IA/Analytics | visao-ia, analytics | 2 |
| Comercial | suporte, comercial | 2 |
| Core | base, core, memory, tools, skills, specialized | 6 |
| Outros | atendimento, auditoria, conhecimento, emergencia, fornecedores, imobiliario, pet, social, sustentabilidade, valorizacao | 10 |

### 6.2 Agente CFTV Destaque (`agent_v2.py` - 41 KB)

**Niveis de Evolucao (7 niveis):**
1. REATIVO - Visualizar cameras, buscar gravacoes
2. PROATIVO - Alertar movimento suspeito
3. PREDITIVO - Prever comportamentos
4. AUTONOMO - Disparar acoes automaticas
5. EVOLUTIVO - Aprender novos padroes
6. COLABORATIVO - Integrar com outros sistemas
7. TRANSCENDENTE - Inteligencia de vigilancia avancada

**Tipos de Eventos Detectados:**
- MOVIMENTO, PESSOA, VEICULO
- OBJETO_ABANDONADO, CERCA_VIRTUAL
- AGLOMERACAO, COMPORTAMENTO_SUSPEITO
- INVASAO, QUEDA, BRIGA

**Niveis de Risco:**
- BAIXO (1), MEDIO (2), ALTO (3), CRITICO (4)

---

## 7. MCPs IMPLEMENTADOS (27)

### 7.1 Seguranca Eletronica (16)

| MCP | Descricao | Status |
|-----|-----------|--------|
| mcp-intelbras-cftv | DVR/NVR Intelbras | ✅ |
| mcp-hikvision-cftv | DVR/NVR Hikvision (ISAPI) | ✅ |
| mcp-frigate-nvr | Frigate NVR | ✅ |
| mcp-vision-ai | YOLO/InsightFace/OCR | ✅ |
| mcp-control-id | Controladoras Control iD | ✅ |
| mcp-intelbras-acesso | Controladoras SS/CT | ✅ |
| mcp-ppa | Motores PPA | ✅ |
| mcp-garen | Motores Garen | ✅ |
| mcp-nice | Motores Nice | ✅ |
| mcp-jfl | Alarmes JFL | ✅ |
| mcp-intelbras-alarme | Alarmes AMT | ✅ |
| mcp-ubiquiti | UniFi Controller | ✅ |
| mcp-mikrotik | RouterOS API | ✅ |
| mcp-furukawa | OLTs GPON | ✅ |
| mcp-asterisk | PBX AMI | ✅ |
| mcp-issabel | PBX Issabel | ✅ |

### 7.2 Gestao Condominial (8)

| MCP | Descricao | Status |
|-----|-----------|--------|
| mcp-boletos | Geracao CNAB 240/400 | ✅ |
| mcp-pix | API PIX BACEN | ✅ |
| mcp-nfse | Emissao NFS-e | ✅ |
| mcp-esocial | Eventos eSocial | ✅ |
| mcp-ponto-rep | REP/AFD | ✅ |
| mcp-assinatura-digital | Assinatura eletronica | ✅ |
| mcp-mqtt | IoT MQTT | ✅ |
| mcp-medidores | Agua/Gas/Energia | ✅ |

### 7.3 IA e Outros (3)

| MCP | Descricao | Status |
|-----|-----------|--------|
| mcp-whisper | Transcricao audio | ✅ |
| mcp-llm-agents | Orquestracao LLM | ✅ |
| mcp-infraestrutura | Infra TI | ✅ |

### 7.4 MCP Vision AI - Ferramentas

```typescript
// Ferramentas disponiveis:
vision_detect_objects    // YOLO detection
vision_detect_faces      // Face detection
vision_compare_faces     // Face comparison
vision_search_face       // Face search in DB
vision_detect_plates     // LPR/ALPR
vision_read_text         // OCR
vision_analyze_stream    // Real-time analysis
vision_detect_motion     // Motion detection
vision_count_people      // People counting
vision_detect_ppe        // EPIs detection
vision_line_crossing     // Line crossing
vision_intrusion_detection // Intrusion detection
```

---

## 8. INFRAESTRUTURA

### 8.1 Docker Compose

**Servicos configurados:**
- postgres (16-alpine)
- redis (7-alpine)
- mongodb (7)
- api-gateway (FastAPI)
- frontend (Next.js)
- auth-service
- notification-service
- ai-orchestrator
- frigate (NVR)

### 8.2 Redes e Volumes

```yaml
networks:
  conecta-network:
    driver: bridge

volumes:
  postgres_data:
  redis_data:
  mongodb_data:
  frigate_media:
```

### 8.3 Health Checks
Todos os servicos tem health checks configurados com:
- Interval: 10-30s
- Timeout: 5-10s
- Retries: 3-5

---

## 9. AVALIACAO DE QUALIDADE

### 9.1 Pontos Fortes

| Aspecto | Score | Observacao |
|---------|-------|------------|
| Arquitetura | 85/100 | Bem estruturado, modular |
| Backend | 80/100 | FastAPI bem implementado |
| Frontend | 75/100 | Next.js 16 moderno |
| Integracao Frigate | 90/100 | Muito completo |
| Agentes IA | 85/100 | Framework robusto |
| MCPs | 70/100 | Estrutura pronta, alguns stubs |
| Documentacao | 60/100 | CLAUDE.md bom, falta mais |
| Testes | 30/100 | Poucos testes encontrados |
| Seguranca | 65/100 | Autenticacao OK, melhorar validacao |

### 9.2 Pontos de Melhoria Identificados

1. **Testes** - Baixa cobertura de testes
2. **Validacao** - Nem todos os inputs sao validados
3. **Rate Limiting** - Nao encontrado em todos endpoints
4. **Documentacao** - Swagger incompleto
5. **Logs** - Logging basico, precisa estruturacao
6. **Multi-tenancy** - Presente mas precisa auditoria
7. **MCPs** - Alguns retornam stubs vazios
8. **TypeScript** - Strict mode nao habilitado

### 9.3 Score Geral de Qualidade

```
╔════════════════════════════════════════╗
║     SCORE GERAL: 72/100               ║
║     Classificacao: BOM                 ║
╚════════════════════════════════════════╝
```

---

## 10. MODULOS - STATUS DETALHADO

### CFTV (Cameras)
| Funcionalidade | Status |
|----------------|--------|
| Gerenciamento de cameras | ✅ Completo |
| Visualizacao ao vivo | ✅ Completo |
| Gravacao continua | ✅ Frigate |
| Gravacao por movimento | ✅ Frigate |
| Playback e timeline | ✅ Frigate |
| PTZ control | ✅ Completo |
| Protocolos RTSP/HLS | ✅ Completo |
| ONVIF | ✅ Detector |
| Grid de cameras | ✅ Frontend |

### Inteligencia Artificial
| Funcionalidade | Status |
|----------------|--------|
| Deteccao de pessoas | ✅ YOLO |
| Deteccao de veiculos | ✅ YOLO |
| Reconhecimento facial | 🔄 MCP stub |
| Reconhecimento de placas | 🔄 MCP stub |
| Analise comportamental | ✅ Agente CFTV |
| Busca inteligente | ✅ Frigate events |

### Controle de Acesso
| Funcionalidade | Status |
|----------------|--------|
| Cadastro de pessoas | ✅ Completo |
| Credenciais (cartao) | ✅ Hardware |
| Credenciais (face) | 🔄 Parcial |
| Visitantes | ✅ Completo |
| Logs de acesso | ✅ Completo |
| Integracao Control iD | ✅ Driver |

### Automacao
| Funcionalidade | Status |
|----------------|--------|
| Portoes e cancelas | ✅ MCPs |
| Iluminacao | ❌ Nao encontrado |
| Interfones IP | ✅ Asterisk MCP |

### Alarmes
| Funcionalidade | Status |
|----------------|--------|
| Central de alarme | ✅ Router |
| Sensores | ✅ Zonas |
| Cerca eletrica | 🔄 Parcial |
| Resposta a eventos | ✅ Agente |

### Alertas e Notificacoes
| Funcionalidade | Status |
|----------------|--------|
| Sistema de alertas | ✅ AlertManager |
| WhatsApp | 🔄 MCP pendente |
| Telegram | 🔄 MCP pendente |
| Email | ✅ Config |
| Push | 🔄 Parcial |

### Relatorios
| Funcionalidade | Status |
|----------------|--------|
| Dashboards | ✅ Pagina |
| Relatorios operacionais | ✅ Pagina |
| Analytics | ✅ Agente |
| Exportacao | 🔄 Parcial |

---

## 11. RECOMENDACOES

### 11.1 Prioridade Alta

1. **Implementar testes automatizados**
   - Jest para frontend
   - Pytest para backend
   - Cobertura minima 80%

2. **Completar MCPs com stubs**
   - Implementar logica real nos MCPs
   - Conectar com APIs dos fabricantes

3. **Adicionar validacao robusta**
   - Pydantic validators no backend
   - Zod no frontend

4. **Rate limiting global**
   - Redis-based rate limiting
   - Por endpoint e por usuario

### 11.2 Prioridade Media

5. **Melhorar logging**
   - Winston/Pino estruturado
   - Correlacao de requests

6. **Documentar APIs**
   - Swagger completo
   - Exemplos de uso

7. **TypeScript strict mode**
   - Habilitar strict: true
   - Corrigir erros de tipo

### 11.3 Prioridade Baixa

8. **Adicionar metricas**
   - Prometheus exporters
   - Dashboards Grafana

9. **Implementar caching**
   - Redis caching layer
   - Cache invalidation

10. **CI/CD**
    - GitHub Actions
    - Deploy automatizado

---

## 12. PROXIMOS PASSOS

1. ✅ **FASE 1 CONCLUIDA** - Auditoria completa
2. ⏳ **FASE 2** - Elevacao de qualidade
3. ⏳ **FASE 3** - Implementacao de agentes de IA
4. ⏳ **FASE 4** - Implementacao de MCPs
5. ⏳ **FASE 5** - Preparacao para integracao

---

*Documento gerado automaticamente pela auditoria do Claude Code Guardian*
*Data: 2025-12-20 | Versao: 1.0*
