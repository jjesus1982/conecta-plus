# Webhooks Cora Bank - Documentação Técnica

## Visão Geral

O sistema Conecta Plus processa webhooks do Banco Cora em tempo real, permitindo atualizações automáticas de status de cobranças, registro de pagamentos e notificações instantâneas.

---

## Arquitetura

### Componentes

1. **Endpoint Público**: `POST /api/v1/cora/webhook`
   - Sem autenticação (público)
   - Validação HMAC-SHA256
   - Registro imutável

2. **WebhookProcessor**: `services/webhook_processor.py`
   - Processamento de eventos
   - Atualização de status
   - Sistema de retry

3. **NotificationService**: `services/notification_service.py`
   - Notificações multi-canal
   - Email, SMS, Push, WebSocket

4. **Repositórios**:
   - WebhookCoraRepository (armazenamento)
   - CobrancaCoraRepository (atualização)
   - TransacaoCoraRepository (registro)

---

## Fluxo de Processamento

```
1. Cora envia webhook -> POST /api/v1/cora/webhook
                           |
2. Valida assinatura HMAC-SHA256
                           |
3. Registra webhook (IMUTÁVEL) no banco
                           |
4. WebhookProcessor.processar_webhook()
                           |
5. Roteamento por tipo de evento
                           |
6. Atualiza status / Registra transação
                           |
7. Envia notificações
                           |
8. Marca webhook como processado
                           |
9. Retorna 200 OK ao Cora
```

---

## Eventos Suportados

### 1. invoice.paid
**Boleto/PIX Pago**

**Payload Exemplo:**
```json
{
  "type": "invoice.paid",
  "id": "evt_abc123",
  "data": {
    "id": "inv_123",
    "paid_amount": 85000,
    "paid_at": "2025-12-22T10:30:00Z"
  }
}
```

**Ações:**
- Atualiza status da cobrança para `pago`
- Registra valor e data de pagamento
- Envia notificação "Pagamento Recebido"
- TODO: Cria pagamento vinculado ao boleto interno

**Notificações:**
- Email: "Pagamento Recebido - Condomínio"
- WebSocket: Notificação em tempo real

---

### 2. invoice.overdue
**Boleto Vencido**

**Payload Exemplo:**
```json
{
  "type": "invoice.overdue",
  "id": "evt_def456",
  "data": {
    "id": "inv_123",
    "due_date": "2025-12-20",
    "amount": 85000
  }
}
```

**Ações:**
- Atualiza status da cobrança para `vencido`
- Envia notificação "Cobrança Vencida"
- TODO: Ativa fluxo de cobrança automática

**Notificações:**
- Email: "Cobrança Vencida - Condomínio"
- SMS (opcional): Alerta de vencimento

---

### 3. invoice.cancelled
**Boleto Cancelado**

**Payload Exemplo:**
```json
{
  "type": "invoice.cancelled",
  "id": "evt_ghi789",
  "data": {
    "id": "inv_123",
    "cancellation_reason": "Solicitação do cliente"
  }
}
```

**Ações:**
- Atualiza status da cobrança para `cancelado`
- Registra data e motivo do cancelamento
- Envia notificação (se necessário)

---

### 4. pix.received
**PIX Recebido**

**Payload Exemplo:**
```json
{
  "type": "pix.received",
  "id": "evt_jkl012",
  "data": {
    "txid": "txid_abc123",
    "amount": 85000,
    "end_to_end_id": "E123456789",
    "transaction_date": "2025-12-22T10:30:00Z",
    "payer": {
      "name": "João Silva",
      "document": "12345678900"
    }
  }
}
```

**Ações:**
- Se tiver txid, busca cobrança correspondente
- Atualiza cobrança como `paga`
- Se não tiver txid, marca para conciliação manual
- Envia notificação "PIX Recebido"
- TODO: Registra transação

**Notificações:**
- Email: "PIX Recebido - Condomínio"
- WebSocket: Notificação em tempo real

---

### 5. payment.created
**Pagamento Criado**

**Payload Exemplo:**
```json
{
  "type": "payment.created",
  "id": "evt_mno345",
  "data": {
    "id": "pay_123",
    "payment_type": "TED",
    "amount": 50000,
    "beneficiary": {
      "name": "Fornecedor XYZ"
    }
  }
}
```

**Ações:**
- Registra log do pagamento criado
- TODO: Atualizar status de pagamento interno

---

### 6. payment.failed
**Pagamento Falhou**

**Payload Exemplo:**
```json
{
  "type": "payment.failed",
  "id": "evt_pqr678",
  "data": {
    "id": "pay_123",
    "failure_reason": "Saldo insuficiente",
    "error_code": "INSUFFICIENT_FUNDS"
  }
}
```

**Ações:**
- Registra falha no log
- Envia alerta para administrador
- TODO: Notificar sistema interno

**Notificações:**
- Email: Alerta de falha de pagamento
- Push: Notificação crítica

---

### 7. transfer.completed
**Transferência Concluída**

**Payload Exemplo:**
```json
{
  "type": "transfer.completed",
  "id": "evt_stu901",
  "data": {
    "id": "trf_123",
    "amount": 100000,
    "beneficiary": {
      "name": "Beneficiário ABC"
    }
  }
}
```

**Ações:**
- Registra transferência bem-sucedida
- TODO: Atualizar saldo
- TODO: Registrar transação

---

### 8. transfer.failed
**Transferência Falhou**

**Payload Exemplo:**
```json
{
  "type": "transfer.failed",
  "id": "evt_vwx234",
  "data": {
    "id": "trf_123",
    "failure_reason": "Dados bancários inválidos"
  }
}
```

**Ações:**
- Registra falha no log
- Envia alerta para administrador

---

## Validação de Assinatura

### Algoritmo HMAC-SHA256

```python
import hmac
import hashlib

# Cora envia no header
signature_received = request.headers.get("X-Cora-Signature")

# Webhook secret configurado na conta
webhook_secret = "seu_webhook_secret"

# Body raw do request
payload = await request.body()

# Calcula assinatura esperada
expected_signature = hmac.new(
    webhook_secret.encode(),
    payload,
    hashlib.sha256
).hexdigest()

# Compara de forma timing-safe
is_valid = hmac.compare_digest(expected_signature, signature_received)
```

### Tratamento de Assinatura Inválida

- **Em produção**: Webhook rejeitado se assinatura inválida
- **Em desenvolvimento**: Aceita webhooks sem secret (para testes)

**Configuração:**
```python
# Configurar webhook_secret ao criar conta Cora
POST /api/v1/cora/auth
{
  "client_id": "...",
  "client_secret": "...",
  "webhook_secret": "seu_secret_aqui"  # ← IMPORTANTE
}
```

---

## Armazenamento Imutável

### Tabela webhooks_cora

**Características:**
- ✅ Apenas INSERT permitido
- ✅ UPDATE apenas de campos de processamento
- ✅ Nunca deletado (auditoria permanente)
- ✅ Body armazenado como JSONB

**Campos:**
```sql
- id: UUID
- event_type: VARCHAR (invoice.paid, etc)
- event_id: VARCHAR (ID único do evento)
- body: JSONB (payload completo)
- signature: VARCHAR
- signature_valid: BOOLEAN
- processado: BOOLEAN
- processado_em: TIMESTAMP
- resultado: JSONB
- erro_mensagem: TEXT
- tentativas_processamento: INTEGER
- ip_origem: INET
- user_agent: TEXT
- received_at: TIMESTAMP
```

---

## Sistema de Retry

### Retry Automático

Webhooks que falham são retentados automaticamente:

```python
# Endpoint de retry manual
POST /api/v1/cora/webhook/{webhook_id}/retry

# Limites
- max_retries: 3
- Incrementa tentativas_processamento
- Exponential backoff (futuro)
```

### Quando Retentar?

✅ **SIM** (erros temporários):
- Timeout de banco de dados
- Conexão perdida
- Serviço temporariamente indisponível

❌ **NÃO** (erros permanentes):
- Cobrança não encontrada
- Dados inválidos
- Violação de constraint

### Monitoramento de Falhas

```sql
-- Webhooks com falha recorrente
SELECT * FROM financeiro.webhooks_cora
WHERE processado = false
  AND tentativas_processamento >= 2
ORDER BY received_at DESC;

-- Taxa de sucesso por tipo de evento
SELECT
  event_type,
  COUNT(*) AS total,
  SUM(CASE WHEN processado THEN 1 ELSE 0 END) AS processados,
  ROUND(100.0 * SUM(CASE WHEN processado THEN 1 ELSE 0 END) / COUNT(*), 2) AS taxa_sucesso
FROM financeiro.webhooks_cora
WHERE received_at > NOW() - INTERVAL '7 days'
GROUP BY event_type;
```

---

## Notificações

### Canais Suportados

1. **Email** ✅
   - Templates HTML
   - Assunto personalizado
   - Habilitado por padrão

2. **SMS** ⏳
   - Mensagens curtas
   - Apenas eventos críticos
   - Requer configuração (Twilio, etc)

3. **Push Notifications** ⏳
   - Mobile app
   - Requer FCM/APNs

4. **WebSocket** ✅
   - Tempo real
   - Broadcast para usuários conectados
   - Habilitado por padrão

5. **WhatsApp** ⏳
   - Business API
   - Requer aprovação de templates

### Configuração

```python
# services/notification_service.py
notification_service.enabled_channels = {
    CanalNotificacao.EMAIL: True,
    CanalNotificacao.SMS: False,  # Configurar Twilio
    CanalNotificacao.PUSH: False,  # Configurar FCM
    CanalNotificacao.WEBSOCKET: True,
    CanalNotificacao.WHATSAPP: False,  # Configurar Meta API
}
```

### Templates de Email

**Pagamento Recebido:**
```html
<h2>Pagamento Recebido</h2>
<p>Informamos que recebemos o pagamento:</p>
<ul>
    <li>Valor: R$ 850,00</li>
    <li>Data: 22/12/2025 10:30</li>
    <li>Forma: Boleto/PIX</li>
</ul>
```

**Cobrança Vencida:**
```html
<h2>Cobrança Vencida</h2>
<p>A cobrança a seguir está vencida:</p>
<ul>
    <li>Valor: R$ 850,00</li>
    <li>Vencimento: 20/12/2025</li>
    <li>Nosso Número: 00012345678</li>
</ul>
<p>Por favor, regularize sua situação.</p>
```

---

## Configuração no Cora

### 1. Registrar Webhook URL

**Via API:**
```bash
curl -X POST https://api.cora.com.br/v2/webhooks \
  -H "Authorization: Bearer ${CORA_ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://seudominio.com.br/api/v1/cora/webhook",
    "events": [
      "invoice.paid",
      "invoice.overdue",
      "invoice.cancelled",
      "pix.received",
      "payment.created",
      "payment.failed",
      "transfer.completed",
      "transfer.failed"
    ],
    "secret": "seu_webhook_secret_aqui"
  }'
```

**Via Dashboard Cora:**
1. Acesse painel Cora
2. Configurações → Webhooks
3. Adicione URL pública
4. Selecione eventos
5. Configure secret (OBRIGATÓRIO para produção)

### 2. Testar Webhook

**Via Dashboard:**
- Use ferramenta "Test Webhook" do Cora

**Manualmente:**
```bash
# Simular webhook local
curl -X POST http://localhost:3001/api/v1/cora/webhook \
  -H "Content-Type: application/json" \
  -H "X-Cora-Signature: fake_signature" \
  -d '{
    "type": "invoice.paid",
    "id": "evt_test_123",
    "data": {
      "id": "inv_123",
      "paid_amount": 85000,
      "paid_at": "2025-12-22T10:30:00Z"
    }
  }'
```

---

## Troubleshooting

### Webhook Não Está Sendo Recebido

**Checklist:**
- [ ] URL pública acessível (não localhost)
- [ ] HTTPS configurado (Cora requer SSL)
- [ ] Porta 443 aberta
- [ ] Firewall permite IPs do Cora
- [ ] Nginx/proxy reverso configurado

**IPs do Cora** (whitelist se necessário):
```
# Production
200.100.50.x/24
200.100.51.x/24

# Sandbox
200.100.60.x/24
```

### Webhook Recebido Mas Não Processado

**Verificar:**
```sql
-- Webhooks com erro
SELECT * FROM financeiro.webhooks_cora
WHERE processado = false
  AND erro_mensagem IS NOT NULL
ORDER BY received_at DESC
LIMIT 10;
```

**Logs:**
```bash
# Ver logs do webhook processor
tail -f /var/log/conecta-plus/webhook_processor.log

# Filtrar por erro
grep "ERROR" /var/log/conecta-plus/webhook_processor.log
```

**Retry Manual:**
```bash
# Reprocessar webhook específico
curl -X POST http://localhost:3001/api/v1/cora/webhook/{webhook_id}/retry \
  -H "Authorization: Bearer TOKEN"
```

### Assinatura Inválida

**Causas Comuns:**
- Secret incorreto no sistema
- Secret alterado no Cora (reconfigurar)
- Body modificado (middleware, proxy)
- Encoding incorreto (UTF-8 esperado)

**Debug:**
```python
# Adicionar log temporário
logger.info(f"Body recebido: {body}")
logger.info(f"Signature recebida: {signature}")
logger.info(f"Signature esperada: {expected}")
logger.info(f"Secret usado: {webhook_secret[:10]}...")
```

---

## Segurança

### Boas Práticas

✅ **SEMPRE:**
- Validar assinatura HMAC-SHA256
- Usar HTTPS em produção
- Armazenar secret criptografado
- Registrar webhooks imutavelmente
- Rate limiting (se necessário)
- Validar estrutura do payload

❌ **NUNCA:**
- Expor webhook_secret em logs
- Processar webhook sem validação
- Confiar cegamente no payload
- Deletar registros de webhook

### Rate Limiting (Opcional)

Se necessário limitar frequência de webhooks:

```python
# Em routers/cora.py
@router.post("/webhook")
@rate_limit(requests_per_minute=100)  # Limite por IP
async def receber_webhook_cora(...):
    ...
```

---

## Métricas e Monitoramento

### KPIs Importantes

1. **Taxa de Sucesso**: % webhooks processados com sucesso
2. **Tempo de Processamento**: Média e p95
3. **Taxa de Retry**: % webhooks que precisaram retry
4. **Latência**: Tempo desde recebimento até conclusão

### Dashboard Sugerido

```sql
-- KPIs últimas 24h
SELECT
  COUNT(*) AS total_webhooks,
  SUM(CASE WHEN processado THEN 1 ELSE 0 END) AS processados,
  SUM(CASE WHEN tentativas_processamento > 1 THEN 1 ELSE 0 END) AS retries,
  ROUND(AVG(EXTRACT(EPOCH FROM (processado_em - received_at))), 2) AS latencia_media_seg
FROM financeiro.webhooks_cora
WHERE received_at > NOW() - INTERVAL '24 hours';
```

---

## TODOs / Melhorias Futuras

1. **Exponential Backoff**: Retry com delays crescentes
2. **Dead Letter Queue**: Webhooks permanentemente falhos
3. **Idempotência**: Prevenir processamento duplicado
4. **Webhook Replay**: Reprocessar eventos antigos
5. **Métricas Prometheus**: Exposição de métricas
6. **Alertas Automáticos**: Notificar devs se taxa de erro > 10%
7. **Webhooks Síncronos**: Para eventos críticos (opcional)
8. **Compressão**: Suporte a gzip em payloads grandes

---

## Referências

- **Documentação Cora**: https://docs.cora.com.br/webhooks
- **HMAC-SHA256**: RFC 2104
- **Webhook Best Practices**: https://webhooks.fyi/best-practices/
