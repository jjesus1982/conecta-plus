# Memória de Sessão - Conecta Plus
**Data:** 2025-12-23
**Última atualização:** 21:55 UTC

---

## Resumo do Projeto

**Conecta Plus** é uma plataforma de gestão de condomínios com:
- Frontend: Next.js 14 (App Router) + TypeScript + Tailwind CSS
- Backend Node.js: API Gateway (porta 3001)
- Backend Python: FastAPI Q1/Q2 (porta 8000)
- Banco de dados: PostgreSQL (schema "conecta")
- Cache: Redis
- Proxy: Nginx (porta 80)
- Containers: Docker

**Servidor:** 82.25.75.74

---

## O que foi feito nesta sessão

### 1. Frontend Q2 - Inteligência Proativa (COMPLETO)

Criadas 5 páginas para o módulo de Inteligência Proativa:

| Arquivo | Descrição |
|---------|-----------|
| `/frontend/src/app/inteligencia/page.tsx` | Dashboard principal Q2 |
| `/frontend/src/app/inteligencia/previsoes/page.tsx` | RF-05: Previsão de Problemas |
| `/frontend/src/app/inteligencia/sugestoes/page.tsx` | RF-06: Sugestões Automáticas |
| `/frontend/src/app/inteligencia/comunicacao/page.tsx` | RF-07: Comunicação Inteligente |
| `/frontend/src/app/inteligencia/aprendizado/page.tsx` | RF-08: Aprendizado Contínuo |

### 2. Menu Sidebar Atualizado

Adicionado novo grupo "Inteligência" no Sidebar com acesso às páginas Q2.

Arquivo: `/frontend/src/components/layout/Sidebar.tsx`

### 3. Dados de Teste Inseridos

Inseridos no banco PostgreSQL:
- 6 previsões de teste (inadimplência, manutenção, segurança, conflito)
- 7 sugestões de teste (economia, segurança, convivência, manutenção)

### 4. Autenticação Desabilitada para Testes

Arquivos modificados para remover redirects de login:

| Arquivo | Alteração |
|---------|-----------|
| `/frontend/src/services/api.ts` | Interceptor 401 não redireciona mais |
| `/frontend/src/components/layout/Header.tsx` | Logout vai para /dashboard |
| `/frontend/src/components/layout/Sidebar.tsx` | Logout vai para /dashboard |
| `/frontend/src/components/layout/MainLayout.tsx` | Auth check removido |
| `/frontend/src/app/page.tsx` | Redireciona direto para /dashboard |

### 5. Correções de API

- Corrigido path de `/api/inteligencia/` para `/api/v1/inteligencia/` em todas as páginas Q2
- Proxy `/frontend/src/app/api/[[...proxy]]/route.ts` atualizado com rotas Q1

---

## Arquitetura de Rotas API

```
Frontend (Next.js :3000)
    ↓
Nginx (:80)
    ├── /api/v1/tranquilidade → Backend Python Q1 (:8000)
    ├── /api/v1/inteligencia  → Backend Python Q1 (:8000)
    ├── /api/v1/health        → Backend Python Q1 (:8000)
    ├── /api/*                → API Gateway Node.js (:3001)
    └── /*                    → Frontend Next.js (:3000)
```

---

## Containers Docker Ativos

```bash
# Verificar status
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Containers principais:
- conecta-frontend      (porta 3000)
- conecta-nginx         (porta 80, 443)
- conecta-backend-q1    (porta 8000)
- conecta-api-gateway   (porta 3001)
- conecta-postgres      (porta 5432)
- conecta-redis         (porta 6379)
```

---

## Credenciais de Teste

```
Admin: admin@conectaplus.com.br / admin123
Síndico: sindico@conectaplus.com.br / sindico123
```

**Nota:** Autenticação está desabilitada - acesso direto ao dashboard sem login.

---

## Banco de Dados

**Conexão:**
```
Host: localhost (ou conecta-postgres)
Port: 5432
Database: conecta_plus
Schema: conecta
User: conecta_user
Password: conecta_pass_2024
```

**Tabelas Q2:**
- `conecta.previsoes` - Previsões de problemas
- `conecta.sugestoes` - Sugestões automáticas
- `conecta.comunicacoes` - Comunicações inteligentes
- `conecta.feedback_ia` - Feedback para aprendizado

---

## Próximos Passos Sugeridos

### Prioridade Alta
1. [ ] Testar todas as páginas Q2 no navegador
2. [ ] Verificar se os dados de teste aparecem corretamente
3. [ ] Implementar ações nos botões (aprovar/rejeitar sugestões, etc.)

### Prioridade Média
4. [ ] Implementar endpoints de comunicação inteligente (RF-07)
5. [ ] Implementar endpoints de aprendizado contínuo (RF-08)
6. [ ] Adicionar gráficos reais nos dashboards

### Prioridade Baixa
7. [ ] Reativar autenticação após testes
8. [ ] Implementar testes E2E
9. [ ] Documentação da API Q2

---

## Comandos Úteis

```bash
# Acessar o sistema
http://82.25.75.74/

# Reconstruir frontend
docker compose build frontend --no-cache
docker stop conecta-frontend && docker rm conecta-frontend
docker run -d --name conecta-frontend --network conecta-network -p 3000:3000 -e HOSTNAME=0.0.0.0 conecta-plus-frontend:latest

# Logs do frontend
docker logs -f conecta-frontend

# Logs do backend Q1
docker logs -f conecta-backend-q1

# Acessar banco de dados
docker exec -it conecta-postgres psql -U conecta_user -d conecta_plus

# Testar API Q1
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJiMmMzZDRlNS1mNmE3LTg5MDEtYmNkZS1mMTIzNDU2Nzg5MDEiLCJlbWFpbCI6ImFkbWluQGNvbmVjdGFwbHVzLmNvbS5iciIsInJvbGUiOiJhZG1pbiIsImV4cCI6MTc2ODk2ODQ1NH0.oZJSdoxBk5bHj2HKOUAuyfJNueA0wFp_I9Ak5Jd3sAM"
curl -s "http://localhost:8000/api/v1/inteligencia/previsoes?condominio_id=a1b2c3d4-e5f6-7890-abcd-ef1234567890" -H "Authorization: Bearer $TOKEN"
```

---

## Arquivos Importantes

```
/opt/conecta-plus/
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── inteligencia/          # Páginas Q2
│   │   │   ├── dashboard/
│   │   │   ├── login/
│   │   │   └── api/[[...proxy]]/      # Proxy para backends
│   │   ├── components/
│   │   │   └── layout/
│   │   │       ├── Sidebar.tsx        # Menu lateral
│   │   │       ├── Header.tsx
│   │   │       └── MainLayout.tsx
│   │   ├── services/
│   │   │   └── api.ts                 # Cliente API Axios
│   │   └── stores/
│   │       └── authStore.ts           # Estado de autenticação
│   └── Dockerfile
├── services/
│   └── backend-q1/                    # FastAPI Python
│       ├── api/
│       │   └── v1/
│       │       └── endpoints/
│       │           └── inteligencia.py
│       └── services/
│           └── inteligencia_service.py
├── config/
│   └── nginx/
│       └── conf.d/
│           └── default.conf           # Configuração Nginx
└── docker-compose.yml
```

---

## Observações

1. **Guardian** está em outro servidor - não mexer nesta sessão
2. **Autenticação** está desabilitada - lembrar de reativar para produção
3. **Condomínio de teste:** `a1b2c3d4-e5f6-7890-abcd-ef1234567890`
4. **Usuário admin de teste:** `b2c3d4e5-f6a7-8901-bcde-f12345678901`

---

*Arquivo gerado automaticamente para continuidade de sessão.*
