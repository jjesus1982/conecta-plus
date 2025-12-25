# Conciliação Bancária Automática - Banco Cora

## Visão Geral

O sistema de **Conciliação Automática** é um componente inteligente que identifica e associa automaticamente transações bancárias (extrato Cora) com boletos/pagamentos do sistema interno.

**Objetivo**: Eliminar trabalho manual de conciliação financeira usando algoritmos de matching inteligente.

---

## Arquitetura

### Componentes

```
┌─────────────────────────────────────────────────────┐
│                   Conciliação Flow                  │
└─────────────────────────────────────────────────────┘

1. Transação Cora recebida (extrato ou webhook)
                    ↓
2. ConciliacaoService.executar_conciliacao_automatica()
                    ↓
3. Para cada transação não conciliada:
    ├── Estratégia 1: Match por end_to_end_id (PIX) → 100% confiança
    ├── Estratégia 2: Match por pix_txid → 100% confiança
    ├── Estratégia 3: Match por valor+data+documento → 95% confiança
    ├── Estratégia 4: Match por valor+data → 70% confiança
    └── Estratégia 5: Match por valor aproximado → 60% confiança
                    ↓
4. Se confiança ≥ 95%: Concilia automaticamente
   Se confiança < 95%: Marca para revisão manual
                    ↓
5. Atualiza banco de dados e registra auditoria
```

---

## Algoritmos de Matching

### 1. Match por end_to_end_id (PIX)
**Confiança**: 100%

Quando um PIX é pago, o Banco Cora envia o `end_to_end_id` único da transação. Este ID é armazenado na cobrança Cora vinculada ao boleto.

**Critério**:
- `transacao.end_to_end_id == cobranca_cora.end_to_end_id`

**Exemplo**:
```python
Transação: end_to_end_id = "E12345678920250115..."
Cobrança: end_to_end_id = "E12345678920250115..."

Match: ✅ 100% confiança
Ação: Concilia automaticamente
```

---

### 2. Match por pix_txid
**Confiança**: 100%

Similar ao end_to_end_id, mas usa o `txid` do QR Code PIX gerado.

**Critério**:
- `transacao.pix_txid == cobranca_cora.pix_txid`

**Exemplo**:
```python
Transação: pix_txid = "txid_abc123..."
Cobrança: pix_txid = "txid_abc123..."

Match: ✅ 100% confiança
Ação: Concilia automaticamente
```

---

### 3. Match por Valor + Data + Documento
**Confiança**: 95%

Busca boleto com:
- Valor exato
- Vencimento dentro de ±3 dias da data da transação
- Documento do pagador = documento da unidade/morador

**Critério**:
```python
boleto.valor == transacao.valor
AND boleto.vencimento BETWEEN (transacao.data - 3 dias) AND (transacao.data + 3 dias)
AND boleto.unidade.morador_documento == transacao.contrapartida_documento
```

**Cenários**:

| Matches Encontrados | Confiança | Ação |
|---------------------|-----------|------|
| 1 boleto | 95% | Concilia automaticamente |
| 2+ boletos | 70% | Marca para revisão manual |
| 0 boletos | 0% | Tenta próxima estratégia |

**Exemplo**:
```python
Transação:
  - Valor: R$ 850,00
  - Data: 2025-01-15
  - Documento: 123.456.789-00

Boleto encontrado:
  - Valor: R$ 850,00
  - Vencimento: 2025-01-13 (dentro de ±3 dias)
  - Morador CPF: 12345678900 (match sem pontuação)

Match: ✅ 95% confiança
Ação: Concilia automaticamente
```

---

### 4. Match por Valor + Data
**Confiança**: 70%

Similar ao anterior, mas **sem validação de documento**. Usa janela maior de ±7 dias.

**Critério**:
```python
boleto.valor == transacao.valor
AND boleto.vencimento BETWEEN (transacao.data - 7 dias) AND (transacao.data + 7 dias)
```

**Cenários**:

| Matches Encontrados | Confiança | Ação |
|---------------------|-----------|------|
| 1 boleto | 70% | Marca para revisão manual |
| 2+ boletos | 50% | Marca para revisão manual |

**Exemplo**:
```python
Transação:
  - Valor: R$ 1.200,00
  - Data: 2025-01-20

Boleto encontrado:
  - Valor: R$ 1.200,00
  - Vencimento: 2025-01-15 (5 dias antes)

Match: ⚠️ 70% confiança
Ação: Marca para revisão manual
```

---

### 5. Match por Valor Aproximado
**Confiança**: 60%

Útil para pagamentos com **juros/multa pequenos** (±1%).

**Critério**:
```python
boleto.valor BETWEEN (transacao.valor * 0.99) AND (transacao.valor * 1.01)
AND boleto.vencimento BETWEEN (transacao.data - 3 dias) AND (transacao.data + 3 dias)
```

**Exemplo**:
```python
Transação:
  - Valor: R$ 858,50 (boleto de R$ 850 + 1% de juros)
  - Data: 2025-01-17

Boleto encontrado:
  - Valor: R$ 850,00
  - Vencimento: 2025-01-15

Diferença: R$ 8,50 (1% do valor original)

Match: ⚠️ 60% confiança
Ação: Marca para revisão manual
```

---

## Uso da API

### 1. Executar Conciliação Automática

```bash
POST /api/v1/cora/conciliar/automatico
Authorization: Bearer {TOKEN}
```

**Response**:
```json
{
  "success": true,
  "message": "Conciliação automática iniciada em background",
  "note": "Verifique os logs de sincronização para acompanhar o progresso"
}
```

**O que acontece**:
1. Background task é iniciada
2. Busca todas as transações não conciliadas (créditos)
3. Aplica algoritmos de matching
4. Auto-concilia quando confiança ≥ 95%
5. Marca para revisão quando confiança < 95%
6. Registra auditoria completa

---

### 2. Obter Sugestões de Match (para UI)

```bash
GET /api/v1/cora/conciliar/sugestoes/{transacao_id}
Authorization: Bearer {TOKEN}
```

**Response**:
```json
{
  "transacao_id": "uuid-123",
  "total_sugestoes": 2,
  "sugestoes": [
    {
      "boleto_id": "uuid-boleto-1",
      "confianca": 0.95,
      "metodo": "valor_data_documento",
      "motivo": "Match único por valor exato, data ±3 dias e documento",
      "boleto": {
        "valor": 850.00,
        "vencimento": "2025-01-13",
        "unidade": "101",
        "morador": "João Silva"
      }
    },
    {
      "boleto_id": "uuid-boleto-2",
      "confianca": 0.70,
      "metodo": "valor_data",
      "motivo": "Match único por valor exato e data ±7 dias",
      "boleto": {
        "valor": 850.00,
        "vencimento": "2025-01-10",
        "unidade": "102",
        "morador": "Maria Santos"
      }
    }
  ]
}
```

**Uso na UI**:
- Exibe lista de boletos candidatos
- Usuário seleciona o correto
- Chama `POST /conciliar` com `boleto_id` selecionado

---

### 3. Conciliar Manualmente

```bash
POST /api/v1/cora/conciliar
Authorization: Bearer {TOKEN}
Content-Type: application/json

{
  "transacao_id": "uuid-transacao",
  "boleto_id": "uuid-boleto",
  "manual": true
}
```

**Response**:
```json
{
  "success": true,
  "message": "Transação conciliada com sucesso",
  "transacao_id": "uuid-transacao",
  "conciliado_em": "2025-01-20T10:30:00"
}
```

---

## Configuração

### Níveis de Confiança

Você pode ajustar os níveis de confiança em `services/conciliacao_service.py`:

```python
class ConfiancaMatch:
    """Níveis de confiança para matching"""
    MUITO_ALTA = 0.95  # Auto-concilia
    ALTA = 0.85
    MEDIA = 0.70
    BAIXA = 0.50
    MUITO_BAIXA = 0.30
```

### Auto-Conciliação

Por padrão, apenas matches com **confiança ≥ 95%** são conciliados automaticamente.

Para alterar:

```python
# No endpoint
resultado = conciliacao_service.executar_conciliacao_automatica(
    condominio_id=condominio_id,
    auto_conciliar=True,
    min_confianca=0.90  # Reduz threshold para 90%
)
```

**⚠️ Atenção**: Reduzir muito o threshold pode causar conciliações incorretas.

---

## Casos de Uso

### Caso 1: PIX Pago (Ideal)

**Entrada**:
- Webhook `pix.received` do Cora
- Transação com `end_to_end_id` e `pix_txid`

**Processo**:
1. Webhook cria transação no banco
2. Conciliação automática é executada (ou manualmente)
3. Match por `end_to_end_id` (100% confiança)
4. Auto-concilia

**Resultado**: Conciliação instantânea e automática ✅

---

### Caso 2: Boleto Pago com Atraso

**Entrada**:
- Webhook `invoice.paid` do Cora
- Transação com valor, data, documento do pagador

**Processo**:
1. Match por `valor + data ±3 dias + documento`
2. Encontra 1 boleto
3. Confiança: 95%
4. Auto-concilia

**Resultado**: Conciliação automática ✅

---

### Caso 3: Múltiplos Boletos com Mesmo Valor

**Entrada**:
- Transação: R$ 850,00 (valor comum de condomínio)
- Data: 2025-01-15

**Processo**:
1. Busca boletos com R$ 850,00 e vencimento ±3 dias
2. Encontra 3 boletos (unidades 101, 102, 103)
3. Confiança: 70% (múltiplos matches)

**Resultado**: Marcado para **revisão manual** ⚠️

**Ação do usuário**:
1. Acessa painel de conciliação
2. Visualiza 3 sugestões
3. Verifica documento do pagador
4. Concilia manualmente

---

### Caso 4: Pagamento com Juros/Multa

**Entrada**:
- Transação: R$ 875,00 (boleto de R$ 850 + juros)
- Data: 2025-01-20 (5 dias após vencimento)

**Processo**:
1. Match exato falha (R$ 875 ≠ R$ 850)
2. Match por valor aproximado ±1%
3. Encontra boleto de R$ 850,00
4. Diferença: 2.94% (dentro da tolerância)
5. Confiança: 60%

**Resultado**: Marcado para **revisão manual** ⚠️

**Ação do usuário**:
1. Verifica sugestão com R$ 850,00
2. Confirma que diferença é juros/multa
3. Concilia manualmente

---

## Monitoramento e Logs

### Logs de Execução

Toda execução de conciliação automática gera logs detalhados:

```
[2025-01-20 10:30:00] INFO: Iniciando conciliação automática para condomínio cond_123
[2025-01-20 10:30:01] INFO: Encontradas 15 transações pendentes
[2025-01-20 10:30:02] INFO: Match EXATO por end_to_end_id: transação uuid-1 → boleto uuid-b1
[2025-01-20 10:30:02] INFO: Conciliando automaticamente: transação uuid-1 → boleto uuid-b1 (confiança: 100%)
[2025-01-20 10:30:03] WARNING: Múltiplos matches para transação uuid-2: 3 boletos candidatos
[2025-01-20 10:30:05] INFO: Conciliação concluída: 8 conciliadas, 5 para revisão, 2 sem match
```

### Auditoria

Toda conciliação (automática ou manual) é auditada:

```json
{
  "tipo": "EXECUTE",
  "descricao": "Conciliação automática executada: 8 transações conciliadas",
  "user_id": "uuid-admin",
  "entidade_tipo": "conciliacao_automatica",
  "entidade_id": "cond_123",
  "detalhes": {
    "total_analisadas": 15,
    "conciliadas_automaticamente": 8,
    "marcadas_para_revisao": 5,
    "sem_match": 2
  }
}
```

### Métricas Importantes

```sql
-- Taxa de conciliação automática (objetivo: > 80%)
SELECT
  COUNT(*) FILTER (WHERE conciliado = true AND manual = false) AS auto_conciliadas,
  COUNT(*) FILTER (WHERE conciliado = true AND manual = true) AS manual_conciliadas,
  COUNT(*) AS total,
  ROUND(
    100.0 * COUNT(*) FILTER (WHERE conciliado = true AND manual = false) / COUNT(*),
    2
  ) AS taxa_auto_conciliacao
FROM financeiro.transacoes_cora
WHERE tipo = 'C'  -- Apenas créditos
  AND created_at > NOW() - INTERVAL '30 days';
```

---

## Troubleshooting

### Transação Não Está Sendo Conciliada

**Checklist**:
1. ✅ Transação é do tipo CRÉDITO?
2. ✅ Transação já não está conciliada?
3. ✅ Existe boleto correspondente?
4. ✅ Valores são exatos ou aproximados?
5. ✅ Datas estão dentro da janela de tolerância?

**Debug**:
```bash
# Buscar sugestões manualmente
GET /api/v1/cora/conciliar/sugestoes/{transacao_id}

# Ver logs de execução
SELECT * FROM financeiro.cora_sync_logs
WHERE tipo = 'conciliacao_automatica'
ORDER BY created_at DESC
LIMIT 1;
```

---

### Múltiplos Matches (Falso Positivo)

**Causa**: Vários boletos com mesmo valor e vencimento próximo.

**Solução**:
- Usar conciliação manual
- Verificar documento do pagador
- Se possível, usar PIX (garante match exato)

---

### Match Não Encontrado (Falso Negativo)

**Causas Comuns**:
- Valor com diferença > 1% (juros/multa altos)
- Data fora da janela de ±7 dias
- Documento do pagador diferente do cadastrado
- Boleto já foi pago/cancelado

**Solução**:
- Conciliar manualmente
- Ajustar tolerância de valor (não recomendado)
- Corrigir cadastro de morador

---

## Performance

### Otimizações Implementadas

1. **Índices no Banco**:
```sql
CREATE INDEX idx_transacoes_cora_conciliado ON transacoes_cora(conciliado);
CREATE INDEX idx_transacoes_cora_tipo_valor ON transacoes_cora(tipo, valor);
CREATE INDEX idx_boletos_valor_vencimento ON boletos(valor, vencimento);
```

2. **Queries Otimizadas**:
- Usa `BETWEEN` para ranges de data/valor
- Filtra por status ANTES de joins
- Limita resultados (LIMIT 1 quando possível)

3. **Early Return**:
- Se encontra match com 100% confiança, não tenta outras estratégias

### Benchmarks

| Cenário | Tempo Esperado |
|---------|----------------|
| 10 transações | < 2 segundos |
| 100 transações | < 10 segundos |
| 1000 transações | < 30 segundos |

---

## Roadmap / Melhorias Futuras

1. **Machine Learning**:
   - Treinar modelo para sugerir matches
   - Aprender com conciliações manuais

2. **OCR de Comprovantes**:
   - Upload de comprovante de pagamento
   - Extrair dados automaticamente
   - Conciliar baseado em dados extraídos

3. **Fuzzy Matching de Nomes**:
   - Usar similaridade de strings para nomes
   - Útil quando documento não disponível

4. **Conciliação Proativa**:
   - Notificar síndico quando há pendências
   - Sugerir ações (ex: "3 transações podem ser conciliadas automaticamente")

5. **Dashboard de Conciliação**:
   - Visualização gráfica de taxa de conciliação
   - Identificação de padrões de pagamento
   - Alertas para divergências recorrentes

---

## Referências

- **Código**: `/opt/conecta-plus/services/api-gateway/services/conciliacao_service.py`
- **Testes**: `/opt/conecta-plus/services/api-gateway/tests/test_conciliacao_automatica.py`
- **Endpoints**: `/opt/conecta-plus/services/api-gateway/routers/cora.py`
- **Modelos**: `/opt/conecta-plus/services/api-gateway/models/cora.py`

---

**Última atualização**: 2025-01-20
**Versão**: 1.0
