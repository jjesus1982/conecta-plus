# CONECTA PLUS - Q2: INTELIGENCIA PROATIVA
## Documento de Especificacao Tecnica

**Data:** 23 de Dezembro de 2025
**Fase:** Q2 - Inteligencia Proativa
**Dependencias:** Q1 Concluido (Fundamentos de Tranquilidade)

---

## 1. VISAO GERAL Q2

### 1.1 Objetivo
Transformar o sistema de **reativo** para **proativo**, antecipando problemas e sugerindo acoes antes que o usuario precise pensar.

### 1.2 Requisitos Funcionais Q2

| RF | Nome | Descricao |
|----|------|-----------|
| RF-05 | Previsao de Problemas | Analisar tendencias e prever problemas antes que ocorram |
| RF-06 | Sugestoes Automaticas | Recomendar acoes baseadas em padroes e contexto |
| RF-07 | Comunicacao Inteligente | Otimizar timing e canal de notificacoes |
| RF-08 | Aprendizado Continuo | Feedback loops para melhoria do sistema |

---

## 2. RF-05: PREVISAO DE PROBLEMAS

### 2.1 Tipos de Previsao

```yaml
PREVISOES_FINANCEIRAS:
  inadimplencia_risco:
    descricao: "Identificar moradores com risco de inadimplencia"
    sinais:
      - historico_atrasos > 2
      - padrao_pagamento = "ultimo_dia"
      - comunicacao_ignorada = true
    acao: "Oferecer parcelamento proativo"

  fluxo_caixa_alerta:
    descricao: "Prever mes com fluxo negativo"
    sinais:
      - arrecadacao_tendencia = "queda"
      - despesas_programadas > media
      - inadimplencia_crescente = true
    acao: "Alertar sindico com antecedencia"

PREVISOES_MANUTENCAO:
  equipamento_risco:
    descricao: "Prever falha de equipamentos"
    sinais:
      - idade_equipamento > vida_util * 0.8
      - ocorrencias_relacionadas > threshold
      - ultimo_preventiva > intervalo_recomendado
    acao: "Agendar manutencao preventiva"

  area_comum_desgaste:
    descricao: "Identificar areas com uso intenso"
    sinais:
      - reservas_mes > media * 1.5
      - ocorrencias_limpeza > normal
      - tempo_desde_reforma > 5_anos
    acao: "Programar revitalizacao"

PREVISOES_SEGURANCA:
  horario_vulneravel:
    descricao: "Identificar horarios com menor cobertura"
    sinais:
      - turnos_descobertos = true
      - cameras_offline_frequente = horario
      - incidentes_historico > media
    acao: "Reforcar seguranca no horario"

  padrao_anomalo:
    descricao: "Detectar comportamentos fora do padrao"
    sinais:
      - acessos_horario_incomum
      - visitantes_mesma_unidade_frequentes
      - veiculos_nao_cadastrados_recorrentes
    acao: "Investigar e alertar"

PREVISOES_CONVIVENCIA:
  conflito_potencial:
    descricao: "Identificar unidades com historico de conflito"
    sinais:
      - ocorrencias_barulho > 3_ultimos_6_meses
      - reclamacoes_mutuas = true
      - vizinhos_diretos = true
    acao: "Mediar proativamente"
```

### 2.2 Modelo de Dados - Previsao

```python
class Previsao(Base):
    __tablename__ = "previsoes"

    id = Column(UUID, primary_key=True)
    tipo = Column(String(50))  # financeiro, manutencao, seguranca, convivencia
    subtipo = Column(String(50))  # inadimplencia_risco, equipamento_risco, etc

    # Entidade relacionada
    entidade_tipo = Column(String(50))  # morador, unidade, equipamento, area
    entidade_id = Column(UUID)

    # Analise
    probabilidade = Column(Float)  # 0.0 a 1.0
    confianca = Column(Float)  # Nivel de confianca da previsao
    horizonte_dias = Column(Integer)  # Em quantos dias pode ocorrer

    # Sinais detectados
    sinais = Column(JSONB)  # Lista de sinais que levaram a previsao
    dados_entrada = Column(JSONB)  # Dados usados na analise

    # Acao
    acao_recomendada = Column(String(500))
    acao_tomada = Column(Boolean, default=False)
    acao_resultado = Column(String(255))

    # Status
    status = Column(String(20))  # pendente, confirmada, evitada, falso_positivo
    validada_em = Column(DateTime)
    validada_por = Column(UUID, ForeignKey("usuarios.id"))

    # Condominio
    condominio_id = Column(UUID, ForeignKey("condominios.id"))

    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
```

---

## 3. RF-06: SUGESTOES AUTOMATICAS

### 3.1 Tipos de Sugestao

```yaml
SUGESTOES_OPERACIONAIS:
  otimizar_ronda:
    contexto: "Rondas concentradas em horarios errados"
    sugestao: "Redistribuir rondas para horarios de maior risco"
    dados: historico_incidentes_por_horario

  reagendar_manutencao:
    contexto: "Manutencao programada em data com reservas"
    sugestao: "Mover para {data_alternativa} sem conflitos"
    dados: agenda_reservas + agenda_manutencao

  consolidar_comunicados:
    contexto: "Muitos comunicados em pouco tempo"
    sugestao: "Agrupar em boletim semanal"
    dados: historico_comunicados + taxa_leitura

SUGESTOES_FINANCEIRAS:
  renegociar_contrato:
    contexto: "Contrato com fornecedor acima do mercado"
    sugestao: "Renegociar ou buscar alternativas"
    dados: benchmark_mercado + historico_reajustes

  antecipar_cobranca:
    contexto: "Moradores com padrao de atraso"
    sugestao: "Enviar lembrete 5 dias antes"
    dados: historico_pagamentos

  reserva_emergencia:
    contexto: "Fundo de reserva abaixo do recomendado"
    sugestao: "Aumentar contribuicao em {valor}"
    dados: despesas_emergenciais + saldo_atual

SUGESTOES_CONVIVENCIA:
  mediar_conflito:
    contexto: "Ocorrencias entre mesmas unidades"
    sugestao: "Agendar mediacao com {partes}"
    dados: historico_ocorrencias_unidades

  reconhecer_colaborador:
    contexto: "Morador participa ativamente"
    sugestao: "Enviar agradecimento publico"
    dados: participacao_assembleias + colaboracoes
```

### 3.2 Modelo de Dados - Sugestao

```python
class Sugestao(Base):
    __tablename__ = "sugestoes"

    id = Column(UUID, primary_key=True)
    tipo = Column(String(50))  # operacional, financeira, convivencia
    codigo = Column(String(50))  # otimizar_ronda, renegociar_contrato, etc

    # Conteudo
    titulo = Column(String(255))
    descricao = Column(Text)
    contexto = Column(Text)  # Por que esta sugerindo
    beneficio_estimado = Column(String(255))  # "Economia de R$ 500/mes"

    # Dados que geraram a sugestao
    dados_entrada = Column(JSONB)
    regra_aplicada = Column(String(100))

    # Destinatario
    perfil_destino = Column(String(50))  # sindico, admin, porteiro
    usuario_destino_id = Column(UUID, ForeignKey("usuarios.id"))

    # Acao
    acao_url = Column(String(255))  # Link para executar acao
    acao_params = Column(JSONB)  # Parametros pre-preenchidos

    # Status
    status = Column(String(20))  # pendente, aceita, rejeitada, expirada
    respondida_em = Column(DateTime)
    respondida_por = Column(UUID)
    motivo_rejeicao = Column(String(255))

    # Feedback
    foi_util = Column(Boolean)
    feedback = Column(Text)

    # Metadata
    prioridade = Column(Integer, default=50)  # 1-100
    condominio_id = Column(UUID, ForeignKey("condominios.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
```

---

## 4. RF-07: COMUNICACAO INTELIGENTE

### 4.1 Otimizacao de Timing

```yaml
ANALISE_COMPORTAMENTO:
  horario_leitura:
    descricao: "Quando cada usuario le notificacoes"
    dados:
      - horario_abertura_app
      - horario_clique_notificacao
      - tempo_entre_envio_e_leitura
    resultado: "Melhor horario para notificar {usuario}"

  canal_preferido:
    descricao: "Qual canal tem melhor engajamento"
    canais:
      - push: taxa_abertura, tempo_resposta
      - email: taxa_abertura, taxa_clique
      - whatsapp: taxa_leitura, taxa_resposta
      - sms: taxa_leitura (emergencias)
    resultado: "Canal primario para {tipo_mensagem}"

  frequencia_ideal:
    descricao: "Quantas notificacoes por periodo"
    regras:
      - max_diario: 3 (exceto emergencias)
      - agrupamento: comunicados similares
      - descanso: nao notificar entre 22h-7h
    resultado: "Evitar fadiga de notificacao"

PERSONALIZACAO_MENSAGEM:
  por_perfil:
    sindico:
      tom: "Profissional, direto"
      detalhes: "Completos, com metricas"
      frequencia: "Alta tolerancia"
    porteiro:
      tom: "Claro, passo a passo"
      detalhes: "Essenciais para acao"
      frequencia: "Apenas urgentes"
    morador:
      tom: "Amigavel, tranquilizador"
      detalhes: "Resumido, com link para mais"
      frequencia: "Minimo necessario"

  por_urgencia:
    critica:
      canais: [push, whatsapp, sms]
      retry: true
      confirmacao: obrigatoria
    alta:
      canais: [push, whatsapp]
      retry: true
      confirmacao: opcional
    media:
      canais: [push, email]
      retry: false
      confirmacao: nao
    baixa:
      canais: [email]
      agrupamento: boletim_semanal
```

### 4.2 Modelo de Dados - Comunicacao

```python
class PreferenciaComunicacao(Base):
    __tablename__ = "preferencias_comunicacao"

    id = Column(UUID, primary_key=True)
    usuario_id = Column(UUID, ForeignKey("usuarios.id"), unique=True)

    # Horarios preferidos (aprendido automaticamente)
    horario_preferido_inicio = Column(Time)
    horario_preferido_fim = Column(Time)
    dias_preferidos = Column(ARRAY(Integer))  # 0=Dom, 6=Sab

    # Canais
    canal_primario = Column(String(20))  # push, email, whatsapp
    canal_secundario = Column(String(20))
    canal_emergencia = Column(String(20))

    # Frequencia
    max_notificacoes_dia = Column(Integer, default=5)
    agrupar_similares = Column(Boolean, default=True)

    # Categorias (opt-in/opt-out)
    receber_financeiro = Column(Boolean, default=True)
    receber_manutencao = Column(Boolean, default=True)
    receber_seguranca = Column(Boolean, default=True)
    receber_comunicados = Column(Boolean, default=True)
    receber_marketing = Column(Boolean, default=False)

    # Metricas aprendidas
    taxa_abertura_push = Column(Float)
    taxa_abertura_email = Column(Float)
    tempo_medio_resposta = Column(Integer)  # segundos

    updated_at = Column(DateTime, default=datetime.utcnow)


class HistoricoComunicacao(Base):
    __tablename__ = "historico_comunicacao"

    id = Column(UUID, primary_key=True)
    usuario_id = Column(UUID, ForeignKey("usuarios.id"))

    # Mensagem
    tipo = Column(String(50))  # alerta, comunicado, lembrete, sugestao
    titulo = Column(String(255))
    conteudo_resumo = Column(String(500))

    # Envio
    canal = Column(String(20))
    enviado_em = Column(DateTime)
    horario_otimizado = Column(Boolean)  # Se usou ML para horario

    # Engajamento
    entregue = Column(Boolean)
    aberto = Column(Boolean)
    aberto_em = Column(DateTime)
    clicou = Column(Boolean)
    clicou_em = Column(DateTime)
    respondeu = Column(Boolean)

    # Feedback
    foi_util = Column(Boolean)
    marcou_spam = Column(Boolean)

    condominio_id = Column(UUID, ForeignKey("condominios.id"))
```

---

## 5. RF-08: APRENDIZADO CONTINUO

### 5.1 Loops de Feedback

```yaml
FEEDBACK_EXPLICITO:
  avaliacoes:
    - "Esta sugestao foi util?" (sim/nao)
    - "Avalie a resolucao" (1-5 estrelas)
    - "O que podemos melhorar?" (texto)

  acoes:
    - Sugestao aceita vs rejeitada
    - Previsao confirmada vs falso positivo
    - Notificacao util vs ignorada

FEEDBACK_IMPLICITO:
  comportamento:
    - Tempo de resposta a notificacao
    - Taxa de abertura por tipo
    - Abandono de fluxo (onde para)
    - Recorrencia de problema apos sugestao

  resultados:
    - Inadimplencia pos-lembrete
    - Ocorrencias pos-manutencao-preventiva
    - Incidentes pos-alerta-seguranca

METRICAS_MODELO:
  previsoes:
    - precision: acertos / total_previsto
    - recall: acertos / total_ocorrido
    - f1_score: media harmonica

  sugestoes:
    - taxa_aceitacao: aceitas / total
    - taxa_utilidade: uteis / aceitas
    - nps_sugestoes: promotores - detratores

  comunicacao:
    - taxa_entrega: entregues / enviados
    - taxa_engajamento: interacoes / entregues
    - tempo_resposta: media em minutos
```

### 5.2 Modelo de Dados - Aprendizado

```python
class FeedbackModelo(Base):
    __tablename__ = "feedback_modelo"

    id = Column(UUID, primary_key=True)

    # Origem
    tipo_origem = Column(String(50))  # previsao, sugestao, comunicacao
    origem_id = Column(UUID)

    # Feedback
    tipo_feedback = Column(String(20))  # explicito, implicito
    valor = Column(String(50))  # util, nao_util, aceito, rejeitado, etc
    comentario = Column(Text)

    # Contexto
    usuario_id = Column(UUID, ForeignKey("usuarios.id"))
    perfil_usuario = Column(String(50))

    # Uso no treinamento
    usado_treinamento = Column(Boolean, default=False)
    versao_modelo = Column(String(20))

    created_at = Column(DateTime, default=datetime.utcnow)


class MetricaModelo(Base):
    __tablename__ = "metricas_modelo"

    id = Column(UUID, primary_key=True)

    # Modelo
    modelo = Column(String(50))  # previsao_inadimplencia, sugestao_manutencao, etc
    versao = Column(String(20))

    # Periodo
    periodo_inicio = Column(DateTime)
    periodo_fim = Column(DateTime)

    # Metricas
    total_predicoes = Column(Integer)
    verdadeiros_positivos = Column(Integer)
    falsos_positivos = Column(Integer)
    verdadeiros_negativos = Column(Integer)
    falsos_negativos = Column(Integer)

    precision = Column(Float)
    recall = Column(Float)
    f1_score = Column(Float)

    # Metricas de negocio
    taxa_aceitacao = Column(Float)
    taxa_utilidade = Column(Float)

    created_at = Column(DateTime, default=datetime.utcnow)
```

---

## 6. SERVICOS A IMPLEMENTAR

### 6.1 Arquitetura de Servicos Q2

```
/backend/services/q2/
├── prediction_engine.py      # Motor de previsoes
├── suggestion_engine.py      # Motor de sugestoes
├── communication_optimizer.py # Otimizador de comunicacao
├── learning_engine.py        # Motor de aprendizado
└── analytics_collector.py    # Coletor de metricas
```

### 6.2 Endpoints Q2

```
# Previsoes
GET    /api/v1/previsoes                    # Lista previsoes ativas
GET    /api/v1/previsoes/{id}               # Detalhe da previsao
POST   /api/v1/previsoes/{id}/validar       # Valida previsao (confirma/nega)
GET    /api/v1/previsoes/dashboard          # Dashboard de previsoes

# Sugestoes
GET    /api/v1/sugestoes                    # Lista sugestoes pendentes
GET    /api/v1/sugestoes/{id}               # Detalhe da sugestao
POST   /api/v1/sugestoes/{id}/aceitar       # Aceita sugestao
POST   /api/v1/sugestoes/{id}/rejeitar      # Rejeita sugestao
POST   /api/v1/sugestoes/{id}/feedback      # Feedback pos-acao

# Comunicacao
GET    /api/v1/comunicacao/preferencias     # Preferencias do usuario
PUT    /api/v1/comunicacao/preferencias     # Atualiza preferencias
GET    /api/v1/comunicacao/historico        # Historico de comunicacoes
GET    /api/v1/comunicacao/metricas         # Metricas de engajamento

# Aprendizado
POST   /api/v1/feedback                     # Envia feedback
GET    /api/v1/metricas/modelo/{modelo}     # Metricas do modelo
```

---

## 7. COMPONENTES FRONTEND Q2

```
/frontend/src/components/q2/
├── previsoes/
│   ├── PrevisaoCard.tsx          # Card de previsao
│   ├── PrevisaoTimeline.tsx      # Timeline de previsoes
│   └── PrevisaoDashboard.tsx     # Dashboard de previsoes
├── sugestoes/
│   ├── SugestaoCard.tsx          # Card de sugestao
│   ├── SugestaoModal.tsx         # Modal de detalhes
│   └── SugestaoFeedback.tsx      # Feedback pos-acao
├── comunicacao/
│   ├── PreferenciasComunicacao.tsx  # Config preferencias
│   └── HistoricoComunicacao.tsx     # Historico de mensagens
└── feedback/
    ├── FeedbackWidget.tsx        # Widget de feedback rapido
    └── AvaliacaoModal.tsx        # Modal de avaliacao detalhada
```

---

## 8. CRONOGRAMA Q2

### Fase 1: Fundacao (Semanas 1-3)
- [ ] Criar modelos de dados Q2
- [ ] Migrar banco de dados
- [ ] Estruturar servicos base

### Fase 2: Previsoes RF-05 (Semanas 4-6)
- [ ] Implementar PredictionEngine
- [ ] Criar algoritmos de previsao
- [ ] Integrar com dados existentes
- [ ] Criar dashboard de previsoes

### Fase 3: Sugestoes RF-06 (Semanas 7-9)
- [ ] Implementar SuggestionEngine
- [ ] Criar regras de sugestao
- [ ] Integrar com fluxos existentes
- [ ] Criar componentes frontend

### Fase 4: Comunicacao RF-07 (Semanas 10-11)
- [ ] Implementar CommunicationOptimizer
- [ ] Criar sistema de preferencias
- [ ] Integrar com canais existentes
- [ ] Otimizar timing de envio

### Fase 5: Aprendizado RF-08 (Semana 12)
- [ ] Implementar LearningEngine
- [ ] Criar loops de feedback
- [ ] Configurar metricas
- [ ] Dashboard de performance

---

## 9. METRICAS DE SUCESSO Q2

```yaml
PREVISOES:
  precision: >75%
  recall: >60%
  acoes_preventivas: +50%
  problemas_evitados: >30%

SUGESTOES:
  taxa_aceitacao: >40%
  taxa_utilidade: >70%
  economia_gerada: mensuravel

COMUNICACAO:
  taxa_engajamento: +25%
  tempo_resposta: -30%
  opt_out_rate: <5%

APRENDIZADO:
  melhoria_modelos: +10% por trimestre
  feedback_coletado: >60% das interacoes
```

---

*Documento Q2 - Conecta Plus - Inteligencia Proativa*
