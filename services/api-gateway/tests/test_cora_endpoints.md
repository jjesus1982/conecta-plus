# Testes dos Endpoints Cora Bank API

## Configuração

Base URL: `http://localhost:3001` (ou porta configurada)
Prefix: `/api/v1/cora`

## Autenticação

Todos os endpoints (exceto webhook) requerem autenticação JWT.

## Endpoints Implementados

### 1. Autenticação

#### POST /api/v1/cora/auth
Configura autenticação Cora para o condomínio

**Request:**
```json
{
  "client_id": "seu_client_id",
  "client_secret": "seu_client_secret",
  "webhook_secret": "seu_webhook_secret",
  "ambiente": "production",
  "api_version": "v2"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Autenticação Cora configurada com sucesso",
  "expires_at": "2025-12-22T10:00:00"
}
```

**Rate Limit:** 10 req/min

---

### 2. Saldo

#### GET /api/v1/cora/saldo
Consulta saldo da conta Cora (cache 10min)

**Response:**
```json
{
  "saldo_disponivel": 10000.50,
  "saldo_bloqueado": 500.00,
  "saldo_total": 10500.50,
  "data_referencia": "2025-12-22T04:00:00",
  "from_cache": true
}
```

**Rate Limit:** 30 req/min

---

### 3. Extrato

#### GET /api/v1/cora/extrato
Consulta extrato bancário

**Query Params:**
- `data_inicio` (required): YYYY-MM-DD
- `data_fim` (required): YYYY-MM-DD
- `sincronizar` (optional): boolean (default: false)
- `page` (optional): int >= 1
- `limit` (optional): int 1-100

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "cora_transaction_id": "trans_123",
      "data_transacao": "2025-01-15",
      "tipo": "C",
      "valor": 850.00,
      "descricao": "Pagamento PIX",
      "categoria": "receita",
      "contrapartida_nome": "João Silva",
      "contrapartida_documento": "12345678900",
      "conciliado": false,
      "boleto_id": null
    }
  ],
  "total": 100,
  "page": 1,
  "limit": 50
}
```

**Rate Limit:** 20 req/min

---

### 4. Cobranças

#### POST /api/v1/cora/cobrancas
Cria cobrança no Cora (boleto/PIX/híbrido)

**Request:**
```json
{
  "boleto_id": "uuid-optional",
  "tipo": "hibrido",
  "valor": 850.00,
  "vencimento": "2025-02-15",
  "descricao": "Condomínio 01/2025",
  "pagador_nome": "João Silva",
  "pagador_documento": "12345678900",
  "pagador_email": "joao@example.com",
  "pagador_telefone": "11999999999",
  "numero_parcela": 1,
  "total_parcelas": 1
}
```

**Response:**
```json
{
  "success": true,
  "id": "uuid",
  "cora_invoice_id": "inv_123",
  "tipo": "hibrido",
  "valor": 850.00,
  "codigo_barras": "12345678901234567890123456789012345678901234567",
  "linha_digitavel": "12345.67890 12345.678901 23456.789012 3 45678901234567",
  "pix_qrcode": "base64...",
  "pix_copia_cola": "00020126...998063...",
  "url_pdf": "https://..."
}
```

**Rate Limit:** 30 req/min

---

#### GET /api/v1/cora/cobrancas
Lista cobranças Cora

**Query Params:**
- `status` (optional): pendente|pago|vencido|cancelado
- `page` (optional): int >= 1
- `limit` (optional): int 1-100

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "tipo": "hibrido",
      "status": "pendente",
      "valor": 850.00,
      "valor_pago": null,
      "data_vencimento": "2025-02-15",
      "data_pagamento": null,
      "nosso_numero": "00012345678",
      "linha_digitavel": "12345.67890...",
      "pix_copia_cola": "00020126..."
    }
  ],
  "total": 50,
  "page": 1,
  "limit": 50
}
```

**Rate Limit:** 60 req/min

---

### 5. Conciliação

#### GET /api/v1/cora/conciliar/pendentes
Lista transações não conciliadas (apenas créditos)

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "cora_transaction_id": "trans_123",
      "data_transacao": "2025-01-15",
      "valor": 850.00,
      "descricao": "PIX Recebido",
      "contrapartida_nome": "João Silva",
      "contrapartida_documento": "12345678900",
      "end_to_end_id": "E123456789",
      "pix_txid": "txid_123"
    }
  ],
  "total": 10
}
```

**Rate Limit:** 60 req/min

---

#### POST /api/v1/cora/conciliar
Concilia transação manualmente

**Request:**
```json
{
  "transacao_id": "uuid",
  "boleto_id": "uuid",
  "pagamento_id": null,
  "lancamento_id": null,
  "manual": true
}
```

**Response:**
```json
{
  "success": true,
  "message": "Transação conciliada com sucesso",
  "transacao_id": "uuid",
  "conciliado_em": "2025-12-22T04:00:00"
}
```

**Rate Limit:** 30 req/min

---

#### POST /api/v1/cora/conciliar/automatico
Executa conciliação automática (background)

**Response:**
```json
{
  "success": true,
  "message": "Conciliação automática iniciada em background",
  "note": "Implementação pendente"
}
```

**Rate Limit:** 10 req/min

---

### 6. Webhook

#### POST /api/v1/cora/webhook
Recebe webhooks do Cora (PÚBLICO - sem autenticação)

**Headers:**
- `X-Cora-Signature`: HMAC-SHA256 signature

**Request:**
```json
{
  "type": "invoice.paid",
  "id": "evt_123",
  "data": {
    "id": "inv_123",
    "paid_amount": 85000,
    "paid_at": "2025-01-15T10:30:00Z"
  }
}
```

**Response:**
```json
{
  "received": true,
  "event_id": "evt_123"
}
```

**Eventos Suportados:**
- `invoice.paid` - Boleto pago
- `invoice.overdue` - Boleto vencido
- `invoice.cancelled` - Boleto cancelado
- `pix.received` - PIX recebido
- `payment.created` - Pagamento criado
- `payment.failed` - Pagamento falhou
- `transfer.completed` - Transferência concluída
- `transfer.failed` - Transferência falhou

**Rate Limit:** Nenhum (público)

---

### 7. Sincronização

#### POST /api/v1/cora/sincronizar
Sincroniza dados com Cora (background)

**Request:**
```json
{
  "tipo": "extrato",
  "data_inicio": "2025-01-01",
  "data_fim": "2025-01-31"
}
```

**Tipos:**
- `extrato` - Sincroniza transações
- `saldo` - Atualiza saldo
- `cobrancas` - Sincroniza cobranças

**Response:**
```json
{
  "success": true,
  "message": "Sincronização de extrato iniciada",
  "sync_id": "uuid"
}
```

**Rate Limit:** 5 req/min

---

### 8. Logs

#### GET /api/v1/cora/logs/sync
Lista histórico de sincronizações

**Query Params:**
- `limit` (optional): int 1-100 (default: 20)

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "tipo": "extrato",
      "status": "concluido",
      "data_inicio": "2025-01-01",
      "data_fim": "2025-01-31",
      "registros_processados": 150,
      "registros_novos": 120,
      "registros_erro": 0,
      "duracao_segundos": 3.5,
      "iniciado_em": "2025-12-22T04:00:00",
      "finalizado_em": "2025-12-22T04:00:03"
    }
  ],
  "total": 10
}
```

**Rate Limit:** 60 req/min

---

#### GET /api/v1/cora/logs/webhooks
Lista webhooks recebidos

**Query Params:**
- `processado` (optional): boolean
- `limit` (optional): int 1-500 (default: 100)

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "event_type": "invoice.paid",
      "event_id": "evt_123",
      "processado": true,
      "processado_em": "2025-12-22T04:00:00",
      "tentativas_processamento": 1,
      "received_at": "2025-12-22T04:00:00",
      "signature_valid": true
    }
  ],
  "total": 50
}
```

**Rate Limit:** 60 req/min

---

## Códigos de Status HTTP

- `200 OK` - Sucesso
- `201 Created` - Recurso criado
- `400 Bad Request` - Dados inválidos
- `404 Not Found` - Recurso não encontrado
- `429 Too Many Requests` - Rate limit excedido
- `502 Bad Gateway` - Erro na API Cora

---

## Auditoria

Todos os endpoints (exceto webhook e logs) geram registros de auditoria:
- Configuração de autenticação
- Criação de cobranças
- Conciliação de transações

---

## TODOs / Implementações Pendentes

1. **Conciliação Automática**: Algoritmo de matching inteligente
2. **Background Tasks**: Sincronização assíncrona
3. **Webhook Validation**: Validação HMAC-SHA256 real
4. **Extração JWT**: Autenticação real (atualmente mock)
5. **Filtros Avançados**: Mais opções de filtro para listagens
6. **Paginação Cursor-Based**: Para performance em grandes volumes
7. **Cache Redis**: Para saldo e dados frequentes
8. **Retry Webhooks**: Reprocessamento de webhooks com falha
