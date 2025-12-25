# CONECTA PLUS - ANALISE DE GAPS E ROADMAP Q1
## Documento de Mapeamento: Estado Atual vs. Visao Futura

**Data:** 23 de Dezembro de 2025
**Versao:** 1.0
**Objetivo:** Identificar gaps e definir implementacoes do Q1 (Fundamentos de Tranquilidade)

---

## 1. RESUMO EXECUTIVO

### 1.1 Estado Atual do Projeto

| Componente | Arquivos | Linhas | Status |
|------------|----------|--------|--------|
| **Frontend** | 50+ | ~15k | 23 paginas, 13+ modulos |
| **Backend** | 71 | ~16k | 18 routers, 16 modelos |
| **Agentes IA** | 96 | ~72k | 36 agentes, Guardian Level 7 |
| **MCPs** | 31 | ~8k | 29 funcionais, 2 vazios |

### 1.2 Nota de Avaliacao

```
SITUACAO ATUAL:  8.5/10 - "Funcional, organizado, confiavel"
VISAO FUTURA:    9.5/10 - "Protetor, orientador, tranquilizador"
GAP PRINCIPAL:   Sistema mostra dados, mas NAO orienta decisoes
```

---

## 2. GAPS IDENTIFICADOS POR RF (REQUISITO FUNCIONAL)

### 2.1 RF-01: ALERTAS INTELIGIVEIS

#### O QUE EXISTE (Backend - GuardianAlert)
```python
# /backend/models/guardian.py
- id, alert_code
- type, severity (low/medium/high/critical)
- title, description, location
- camera_id, source
- acknowledged, dismissed
- extra_data (JSONB)
```

#### O QUE FALTA (Conforme Super Prompt)
```yaml
CAMPOS_NECESSARIOS:
  contexto: "Por que isso importa?"
  impacto: "O que acontece se ignorar?"
  responsavel_id: "Quem cuida disso?"
  responsavel_nome: "Nome legivel"
  acao_recomendada: "O que fazer agora?"
  status_detalhado: "Em atendimento - previsao 2h"
  prazo_estimado: datetime
  prazo_tipo: "sla" | "manual" | "ia_sugerido"

EXEMPLO_TRANSFORMACAO:
  antes:
    titulo: "Camera offline"

  depois:
    titulo: "Camera da garagem offline ha 4h"
    contexto: "Esta camera cobre a entrada principal de veiculos"
    impacto: "Seguranca comprometida em area critica"
    responsavel: "Tecnico Conecta Mais acionado"
    acao: "Aguarde atualizacao ou acione suporte"
    status: "Em atendimento - previsao 2h"
```

#### IMPLEMENTACAO NECESSARIA
1. Adicionar campos ao modelo `GuardianAlert`
2. Criar servico `AlertEnricherService` para enriquecer alertas
3. Criar templates de contexto por tipo de alerta
4. Atualizar frontend para exibir novos campos
5. Integrar com SLA por tipo

---

### 2.2 RF-02: OCORRENCIAS COM PRAZO

#### O QUE EXISTE (Backend - Ocorrencia)
```python
# /backend/models/ocorrencia.py
- id, titulo, descricao
- tipo (10 tipos), prioridade, status (6 status)
- reportado_por, responsavel_id
- unidade_id, anexos
- created_at, updated_at, resolvido_at
```

#### O QUE FALTA
```yaml
CAMPOS_NECESSARIOS:
  prazo_estimado: datetime
  prazo_origem: "sla" | "manual" | "ia"
  sla_config_id: FK para configuracao de SLA
  timeline: JSONB  # Historico de mudancas de status
  avaliacao_nota: int (1-5)
  avaliacao_comentario: text
  avaliacao_data: datetime
  notificacoes_enviadas: JSONB  # Registro de notificacoes

SLA_POR_TIPO:
  manutencao_urgente: 4h
  manutencao_normal: 48h
  seguranca: 1h
  barulho: 24h
  vazamento: 2h
  limpeza: 24h
  default: 72h

NOTIFICACOES_AUTOMATICAS:
  - ao_abrir: "Recebemos sua ocorrencia"
  - ao_atribuir: "Responsavel definido: {nome}"
  - ao_atualizar: "Nova atualizacao disponivel"
  - ao_resolver: "Problema resolvido. Avalie em 1 clique"
  - sla_proximo: "Prazo em 2h - priorize!"
  - sla_estourado: "SLA estourado - escalar"
```

#### IMPLEMENTACAO NECESSARIA
1. Criar modelo `SLAConfig` com regras por tipo
2. Adicionar campos de prazo e timeline na `Ocorrencia`
3. Criar `OcorrenciaTimelineService` para registrar eventos
4. Implementar sistema de notificacoes automaticas
5. Criar endpoint de avaliacao pos-resolucao
6. Atualizar frontend com timeline visual

---

### 2.3 RF-03: REGISTRO AUTOMATICO DE DECISAO

#### O QUE EXISTE
```python
# /backend/models/guardian.py - GuardianActionLog
- action_type, description, location
- executed_by, success, result_message
- alert_id, incident_id

# GuardianIncident.timeline (JSONB)
- timestamp, event, description, user
```

#### O QUE FALTA
```yaml
GAPS:
  1. Registro apenas no Guardian (falta em outros modulos)
  2. Sem mensagem de protecao ao usuario
  3. Sem justificativa obrigatoria em acoes criticas
  4. Sem auditoria em: Acesso, Financeiro, Ocorrencias

MODELO_UNIFICADO_NECESSARIO:
  DecisionLog:
    id: uuid
    modulo: "acesso" | "financeiro" | "ocorrencias" | "guardian" | "portaria"
    tipo_decisao: "acesso_liberado" | "acesso_negado" | "pagamento_aprovado" | etc
    entidade_id: uuid  # ID do registro afetado
    entidade_tipo: string
    decisao: string
    justificativa: text
    regra_aplicada: string  # Qual regra do sistema foi usada
    usuario_id: uuid
    usuario_nome: string
    protecao_exibida: boolean  # Se mostrou msg de protecao
    ip_address: string
    user_agent: string
    created_at: datetime

MENSAGENS_PROTECAO:
  porteiro: "Decisao registrada. Voce esta protegido."
  sindico: "Acao documentada com data e hora."
  operador: "Voce seguiu o procedimento correto."
```

#### IMPLEMENTACAO NECESSARIA
1. Criar modelo unificado `DecisionLog`
2. Criar decorator `@log_decision` para rotas criticas
3. Implementar middleware de auditoria
4. Adicionar mensagem de protecao no frontend
5. Criar dashboard de auditoria para admin

---

### 2.4 RF-04: PAINEL DE TRANQUILIDADE

#### O QUE EXISTE
```python
# Dashboard atual
- KPIs basicos (moradores, visitantes, ocorrencias, cameras)
- Alertas recentes (tipo, tempo, prioridade)
- Acesso rapido a modulos
```

#### O QUE FALTA
```yaml
PAINEL_POR_PERFIL:

  SINDICO:
    situacao_agora: "verde" | "amarelo" | "vermelho"
    precisa_de_voce:
      - items: Lista de 0-3 acoes necessarias
      - cada item com: titulo, urgencia, link
    ja_resolvido_hoje: contador positivo
    recomendacao: "Nenhuma acao necessaria agora" | "Aprovar 2 pagamentos"
    saude_condominio:
      inadimplencia: percentual + tendencia
      ocorrencias: abertas vs resolvidas
      seguranca: score Guardian

  PORTEIRO:
    situacao_agora: estado visual
    proxima_tarefa: destaque unico
    procedimento_sugerido: passo a passo
    botao_duvida: "Estou em duvida" (aciona suporte)
    visitantes_aguardando: lista com tempo de espera
    alertas_ativos: apenas os relevantes

  MORADOR:
    minhas_ocorrencias: status visual com timeline
    comunicados_para_mim: apenas relevantes (segmentados)
    minhas_encomendas: aguardando retirada
    minhas_reservas: proximas agendadas
    financeiro: situacao + proximos vencimentos

ESTADOS_VISUAIS:
  verde:
    criterios:
      - 0 alertas criticos
      - 0 ocorrencias urgentes
      - inadimplencia < 10%
      - todas cameras online
    mensagem: "Tudo sob controle"

  amarelo:
    criterios:
      - 1-3 alertas medios
      - ocorrencias proximas do SLA
      - inadimplencia 10-20%
      - 1-2 cameras offline
    mensagem: "Atencao necessaria"

  vermelho:
    criterios:
      - alertas criticos OU
      - SLA estourado OU
      - inadimplencia > 20% OU
      - >3 cameras offline
    mensagem: "Acao imediata requerida"
```

#### IMPLEMENTACAO NECESSARIA
1. Criar endpoint `/dashboard/tranquilidade/{perfil}`
2. Implementar logica de calculo de estado (verde/amarelo/vermelho)
3. Criar componente `TranquilidadeWidget` no frontend
4. Implementar "Precisa de voce" com priorizacao IA
5. Criar sistema de recomendacoes contextuais

---

## 3. ESTRUTURA TECNICA PROPOSTA

### 3.1 Novos Modelos de Dados

```
/backend/models/
├── sla_config.py          # Configuracoes de SLA por tipo
├── decision_log.py        # Registro unificado de decisoes
├── tranquilidade.py       # Cache de estado por perfil
└── notificacao_auto.py    # Templates de notificacao automatica
```

### 3.2 Novos Servicos

```
/backend/services/
├── alert_enricher.py      # Enriquece alertas com contexto
├── sla_manager.py         # Gerencia SLAs e prazos
├── decision_logger.py     # Registra decisoes automaticamente
├── tranquilidade.py       # Calcula estado de tranquilidade
└── notification_engine.py # Motor de notificacoes automaticas
```

### 3.3 Novos Endpoints

```
POST   /alerts/{id}/enrich          # Enriquece alerta com contexto
GET    /ocorrencias/{id}/timeline   # Timeline da ocorrencia
POST   /ocorrencias/{id}/avaliar    # Avaliacao pos-resolucao
GET    /dashboard/tranquilidade/{perfil}  # Painel por perfil
GET    /auditoria/decisoes          # Log de decisoes
GET    /sla/config                  # Configuracoes de SLA
```

### 3.4 Novos Componentes Frontend

```
/frontend/src/components/
├── alerts/
│   └── AlertCard.tsx              # Card de alerta enriquecido
├── ocorrencias/
│   ├── OcorrenciaTimeline.tsx     # Timeline visual
│   └── AvaliacaoModal.tsx         # Modal de avaliacao
├── tranquilidade/
│   ├── TranquilidadeWidget.tsx    # Widget principal
│   ├── PrecisaDeVoce.tsx          # Lista de acoes pendentes
│   └── RecomendacaoCard.tsx       # Card de recomendacao
└── shared/
    └── ProtecaoToast.tsx          # Toast de protecao
```

---

## 4. CRONOGRAMA DE IMPLEMENTACAO Q1

### Semana 1-2: Fundacao
- [ ] Criar modelos: SLAConfig, DecisionLog
- [ ] Migrar banco de dados
- [ ] Implementar SLAManagerService
- [ ] Implementar DecisionLoggerService

### Semana 3-4: RF-01 Alertas Inteligiveis
- [ ] Adicionar campos ao GuardianAlert
- [ ] Criar AlertEnricherService
- [ ] Criar templates de contexto
- [ ] Atualizar AlertCard no frontend

### Semana 5-6: RF-02 Ocorrencias com Prazo
- [ ] Adicionar campos de prazo/timeline
- [ ] Implementar calculo automatico de SLA
- [ ] Criar OcorrenciaTimelineService
- [ ] Implementar sistema de notificacoes
- [ ] Atualizar frontend com timeline

### Semana 7-8: RF-03 Registro de Decisoes
- [ ] Implementar decorator @log_decision
- [ ] Integrar em rotas criticas
- [ ] Criar dashboard de auditoria
- [ ] Implementar mensagem de protecao

### Semana 9-10: RF-04 Painel de Tranquilidade
- [ ] Criar TranquilidadeService
- [ ] Implementar logica verde/amarelo/vermelho
- [ ] Criar endpoints por perfil
- [ ] Desenvolver componentes frontend

### Semana 11-12: Integracao e Testes
- [ ] Testes de integracao
- [ ] Ajustes de UX
- [ ] Documentacao
- [ ] Deploy em staging

---

## 5. METRICAS DE SUCESSO Q1

```yaml
METRICAS_UX:
  reducao_reclamacoes_repetidas: -30%
  reducao_chamados_duvida: -25%
  aumento_uso_diario: +40%
  tempo_primeiro_uau: <5min

METRICAS_OPERACIONAIS:
  sla_cumprido: >90%
  alertas_com_contexto: 100%
  decisoes_registradas: 100%
  avaliacoes_recebidas: >60%

METRICAS_TECNICAS:
  cobertura_testes: >80%
  tempo_resposta_api: <200ms
  uptime: >99.5%
```

---

## 6. CONCLUSAO

O Conecta Plus possui uma **base tecnica solida** (8.5/10), mas precisa evoluir de um sistema que **mostra dados** para um sistema que **orienta decisoes e protege pessoas**.

As implementacoes do Q1 focam nos **Fundamentos de Tranquilidade**:
1. Alertas que explicam o problema E a solucao
2. Ocorrencias com prazo e visibilidade total
3. Registro de decisoes que protege operadores
4. Paineis que reduzem ansiedade por perfil

**Investimento:** 12 semanas
**Resultado:** Sistema que gera dependencia positiva

---

*Documento gerado em 23/12/2025 - Conecta Plus v2.0*
