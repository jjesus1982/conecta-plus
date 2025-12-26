# Rate Limiting - Conecta Plus

## Visao Geral

O sistema Conecta Plus implementa rate limiting em multiplas camadas para proteger a API contra abusos:

1. **Nginx (Camada de Proxy)** - Primeiro nivel de protecao
2. **FastAPI Backend** - Middlewares especificos por tipo de endpoint
3. **API Gateway** - Limites por endpoint e tipo de operacao

---

## 1. Rate Limiting no Nginx

### Zonas Configuradas

| Zona | Rate | Uso |
|------|------|-----|
| `api_limit` | 10 req/s | Endpoints gerais da API |
| `login_limit` | 5 req/min | Endpoint de login |
| `api` | 10 req/s | Zona global |
| `login` | 5 req/min | Zona global login |

### Endpoints com Rate Limit no Nginx

```nginx
# API Gateway - 10 req/s com burst de 20
location /api/ {
    limit_req zone=api_limit burst=20 nodelay;
    ...
}

# Login - 5 req/min com burst de 5
location /api/auth/login {
    limit_req zone=login_limit burst=5 nodelay;
    ...
}

# Inteligencia - 10 req/s com burst de 20
location /api/v1/inteligencia {
    limit_req zone=api_limit burst=20 nodelay;
    ...
}
```

### Arquivos de Configuracao

- `/opt/conecta-plus/config/nginx/nginx.conf` - Definicao das zonas
- `/opt/conecta-plus/config/nginx/conf.d/default.conf` - Aplicacao por location

---

## 2. Rate Limiting no Backend FastAPI

### RateLimitMiddleware (Global)

Middleware que aplica rate limiting a todos os endpoints (exceto whitelist).

**Configuracao padrao:**
- 100 requests por 60 segundos (por IP + User-Agent)
- Configuravel via settings: `RATE_LIMIT_REQUESTS`, `RATE_LIMIT_WINDOW`

**Whitelist (sem rate limit):**
- `/health`
- `/api/v1/docs`
- `/api/v1/openapi.json`

**Headers retornados:**
- `X-RateLimit-Limit` - Limite maximo de requests
- `X-RateLimit-Remaining` - Requests restantes na janela
- `X-RateLimit-Reset` - Segundos ate reset da janela

**Arquivo:** `/opt/conecta-plus/backend/middleware/rate_limit.py`

### LoginRateLimitMiddleware (Autenticacao)

Middleware especifico para endpoints de autenticacao com limites mais restritivos.

#### Endpoints de Login

| Endpoint | Limite/min | Limite/hora |
|----------|------------|-------------|
| `/api/v1/auth/login` | 5 | 20 |
| `/api/v1/auth/login/json` | 5 | 20 |
| `/api/v1/auth/token` | 5 | 20 |

#### Endpoints Criticos

| Endpoint | Limite/min | Limite/hora |
|----------|------------|-------------|
| `/api/v1/auth/change-password` | 3 | 10 |
| `/api/v1/auth/ldap/login` | 3 | 10 |
| `/api/v1/auth/refresh` | 3 | 10 |

**Recursos adicionais:**
- Rastreamento de falhas de login
- Alerta apos 10 falhas consecutivas (possivel ataque de forca bruta)
- Reset do contador apos login bem-sucedido

---

## 3. Rate Limiting no API Gateway

O API Gateway (`/opt/conecta-plus/services/api-gateway/`) implementa limites por tipo de operacao:

### Configuracao por Ambiente

| Ambiente | req/min | req/hora | req/dia |
|----------|---------|----------|---------|
| Production | 60 | 1000 | 10000 |
| Staging | 120 | 2000 | 20000 |
| Development | 1000 | 10000 | 100000 |

### Limites por Tipo de Operacao

| Operacao | req/min | req/hora |
|----------|---------|----------|
| Boleto Create | 10 | 100 |
| Cobranca | 20 | 200 |
| Export/Relatorios | 5 | 20 |

**Arquivo:** `/opt/conecta-plus/services/api-gateway/middleware/rate_limit.py`

---

## 4. Headers de Rate Limit

Todas as respostas da API incluem headers informativos:

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 45
Retry-After: 60  # Apenas em respostas 429
```

### Resposta 429 (Too Many Requests)

```json
{
    "detail": "Muitas requisicoes. Tente novamente mais tarde.",
    "retry_after": 60
}
```

---

## 5. Armazenamento

### Backend (Memoria)

Atualmente o rate limiting usa armazenamento em memoria (defaultdict).

**Limitacoes:**
- Nao persiste entre restarts
- Nao compartilha entre multiplas instancias

### Suporte a Redis (Futuro)

O codigo ja esta preparado para usar Redis:

```python
# API Gateway
self._use_redis = os.getenv('RATE_LIMIT_REDIS', 'false').lower() == 'true'
```

Para habilitar Redis, configurar a variavel de ambiente:
```bash
RATE_LIMIT_REDIS=true
REDIS_URL=redis://localhost:6379/0
```

---

## 6. Configuracao via Variaveis de Ambiente

| Variavel | Padrao | Descricao |
|----------|--------|-----------|
| `RATE_LIMIT_ENABLED` | `true` | Habilita/desabilita rate limiting |
| `RATE_LIMIT_REQUESTS` | `100` | Requests por janela |
| `RATE_LIMIT_WINDOW` | `60` | Segundos por janela |
| `RATE_LIMIT_REDIS` | `false` | Usar Redis para storage |
| `REDIS_URL` | `redis://localhost:6379/0` | URL do Redis |

---

## 7. Monitoramento e Logs

### Logs de Rate Limit

```log
# Warning - limite excedido
2024-12-26 10:15:23 | WARNING | rate_limit | Rate limit excedido para cliente abc12345... Path: /api/v1/usuarios

# Error - possivel ataque
2024-12-26 10:15:30 | ERROR | rate_limit | Multiplas falhas de login para IP 192.168.1.100 - possivel ataque
```

### Metricas Prometheus

O endpoint `/metrics` expoe metricas relacionadas a rate limiting:

```
http_requests_total{status="429"} 15
```

---

## 8. Boas Praticas

1. **Nunca desabilitar em producao** - Rate limiting e essencial para seguranca
2. **Ajustar limites com base no uso** - Monitorar e ajustar conforme necessario
3. **Usar Redis em producao** - Para ambientes com multiplas instancias
4. **Informar usuarios** - Retornar headers informativos para clientes
5. **Logar tentativas bloqueadas** - Para analise de seguranca

---

## 9. Endpoints Criticos Protegidos

| Endpoint | Protecao | Limite |
|----------|----------|--------|
| `POST /api/v1/auth/login` | Login + Nginx | 5/min, 20/hora |
| `POST /api/v1/auth/login/json` | Login | 5/min, 20/hora |
| `POST /api/v1/auth/ldap/login` | Critico | 3/min, 10/hora |
| `POST /api/v1/auth/change-password` | Critico | 3/min, 10/hora |
| `POST /api/v1/auth/refresh` | Critico | 3/min, 10/hora |
| `POST /api/v1/usuarios` | Global + Admin | 100/min (requer autenticacao) |
| `POST /api/v1/boletos` | API Gateway | 10/min (production) |

---

## 10. Testes

### Testar Rate Limit Manual

```bash
# Testar limite de login (deve falhar apos 5 tentativas)
for i in {1..10}; do
    curl -X POST https://localhost/api/v1/auth/login \
        -H "Content-Type: application/json" \
        -d '{"email":"test@test.com","password":"wrong"}' \
        -w "\nHTTP %{http_code}\n"
done
```

### Verificar Headers

```bash
curl -v https://localhost/api/v1/health 2>&1 | grep -i x-ratelimit
```

---

**Ultima atualizacao:** 2024-12-26
