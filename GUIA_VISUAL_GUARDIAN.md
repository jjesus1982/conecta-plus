# 🎯 GUIA VISUAL - ONDE VER O GUARDIAN NO CONECTA PLUS

## 📍 PASSO A PASSO PARA VER AS MUDANÇAS

### PASSO 1: Acesse o Conecta Plus

**URL:** `http://localhost:3000` ou `http://SEU_IP:3000`

Faça login normalmente no sistema.

---

### PASSO 2: Menu Lateral - Novo Item "Guardian AI"

Após o login, **OLHE PARA O MENU LATERAL ESQUERDO**:

```
┌─────────────────────────────────────┐
│  Conecta+                           │
├─────────────────────────────────────┤
│  Principal                          │
│  • Dashboard                        │
│  • Alertas                          │
│                                     │
│  🔒 Segurança                       │
│  • Guardian AI  [🔴 5]  ← AQUI!    │
│  • CFTV                             │
│  • Controle de Acesso               │
│  • Alarmes                          │
│  • Portaria Virtual                 │
│                                     │
│  Gestão                             │
│  • Financeiro                       │
│  • Ocorrências                      │
└─────────────────────────────────────┘
```

**O que você verá:**
- ✅ Ícone de escudo com check (ShieldCheck)
- ✅ Texto "Guardian AI"
- ✅ **Badge vermelho com número** de alertas ativos (exemplo: 5)
- ✅ Badge atualiza automaticamente a cada 30 segundos

---

### PASSO 3: Dashboard Principal - Widget Guardian

**URL:** `http://localhost:3000/dashboard`

Role a página para baixo. **VOCÊ VERÁ UM NOVO BLOCO** com:

```
┌──────────────────────────────────────────────────────────────┐
│  🛡️ Guardian Security                                        │
│  Status: Operacional                                         │
│                                                              │
│  Risco: Alto (Score: 65/100) 📈                             │
│  • Fator 1: Horário Noturno (+15.0)                        │
│  • Fator 2: Alertas Pendentes (+20.0)                      │
│                                                              │
│  📊 Estatísticas:                                           │
│  • Alertas Ativos: 5                                        │
│  • Incidentes: 2                                            │
│  • Câmeras Online: 23/24                                    │
│  • Acessos 24h: 1250                                        │
│                                                              │
│  💡 Recomendações:                                          │
│  • Revisar alertas pendentes                               │
│  • Verificar câmeras do Bloco B                            │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  Acesso Rápido - Segurança                                   │
│  [Guardian AI] [Câmeras] [Alertas] [Analytics]              │
└──────────────────────────────────────────────────────────────┘
```

---

### PASSO 4: Página Guardian Completa

**URL:** `http://localhost:3000/guardian`

Clique em "Guardian AI" no menu lateral ou acesse direto. **VOCÊ VERÁ:**

```
═══════════════════════════════════════════════════════════════
  🛡️ Guardian Security
  Sistema Inteligente de Segurança
                                        [🔄 Atualizar] [🔗 Abrir em Nova Aba]
───────────────────────────────────────────────────────────────

CARDS DE ACESSO RÁPIDO:

┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ 🟠 Alertas   │ │ 🔴 Incidentes│ │ 📹 Câmeras   │ │ 📊 Analytics │
│ 5 ativos     │ │ 2 ativos     │ │ 23 online    │ │              │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘

───────────────────────────────────────────────────────────────

WIDGET GUARDIAN (1/3 da tela)    ALERTAS RECENTES (2/3 da tela)
┌─────────────────────────────┐  ┌────────────────────────────┐
│ 🛡️ Guardian Security        │  │ Alertas Recentes           │
│ Status: Operacional          │  │                            │
│                              │  │ [🟠] Intrusão detectada    │
│ Risco: Alto (65/100)         │  │ Bloco B - 5min atrás       │
│ ████████░░░░░░░░░░           │  │ [✓ Reconhecer] [X]         │
│                              │  │                            │
│ Alertas: 5                   │  │ [🟡] Movimento suspeito    │
│ Incidentes: 2                │  │ Garagem - 12min atrás      │
│ Câmeras: 23/24               │  │ [✓ Reconhecer] [X]         │
└─────────────────────────────┘  └────────────────────────────┘

───────────────────────────────────────────────────────────────

INTERFACE COMPLETA GUARDIAN (IFRAME)
┌──────────────────────────────────────────────────────────────┐
│ 🛡️ Interface Completa Guardian            [⛶ Tela Cheia]   │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│    [IFRAME: https://91.108.124.140.nip.io/dashboard]        │
│                                                              │
│    • Dashboard                                               │
│    • Atendimentos                                            │
│    • Câmeras                                                 │
│    • Gravações                                               │
│    • Detecções IA                                            │
│    • Equipamentos                                            │
│    • Frigate NVR                                             │
│    • Edge Computing                                          │
│    • Alarmes                                                 │
│    • Ativos                                                  │
│    • Organizações                                            │
│    • Usuários                                                │
│    • Configurações                                           │
│                                                              │
│    (800px de altura - scroll disponível)                    │
│                                                              │
└──────────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════
```

---

### PASSO 5: Subpáginas Guardian

Clique nos cards de acesso rápido para acessar:

#### 📱 `/guardian/alertas`
```
┌──────────────────────────────────────────────────────────────┐
│ 🟠 Alertas Guardian                                          │
│ 5 alertas ativos                                             │
├──────────────────────────────────────────────────────────────┤
│ FILTROS:                                                     │
│ Severidade: [Todos] [Baixo] [Médio] [Alto] [Crítico]       │
│ Status: [Todos] [Não Reconhecidos] [Reconhecidos]          │
├──────────────────────────────────────────────────────────────┤
│ ALERTAS:                                                     │
│                                                              │
│ [🔴] CRÍTICO - Intrusão detectada                           │
│ Bloco B - Estacionamento | 5min atrás                       │
│ [✓ Reconhecer] [X Dispensar]                                │
│                                                              │
│ [🟠] ALTO - Pessoa não autorizada                           │
│ Entrada Principal | 10min atrás                             │
│ [✓ Reconhecer] [X Dispensar]                                │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

#### 📹 `/guardian/cameras`
```
┌──────────────────────────────────────────────────────────────┐
│ 📹 Câmeras Guardian                                          │
│ Monitoramento e detecções IA                                 │
├──────────────────────────────────────────────────────────────┤
│ [IFRAME: https://91.108.124.140.nip.io/cameras]             │
│                                                              │
│ Sistema completo de câmeras com:                             │
│ • Live view de todas as câmeras                             │
│ • Detecções em tempo real                                   │
│ • PTZ control                                                │
│ • Gravações                                                  │
└──────────────────────────────────────────────────────────────┘
```

#### 📊 `/guardian/analytics`
```
┌──────────────────────────────────────────────────────────────┐
│ 📊 Analytics Guardian                                        │
│ Análises preditivas e insights                               │
├──────────────────────────────────────────────────────────────┤
│ [IFRAME: https://91.108.124.140.nip.io/analytics]           │
│                                                              │
│ Dashboard analytics com:                                     │
│ • Gráficos de tendências                                    │
│ • Predições de segurança                                    │
│ • Anomalias detectadas                                      │
│ • Insights inteligentes                                     │
└──────────────────────────────────────────────────────────────┘
```

---

### PASSO 6: Notificações em Tempo Real

**Localização:** Canto superior direito da tela

Quando um novo alerta ou incidente ocorrer, **VOCÊ VERÁ UMA NOTIFICAÇÃO POPUP**:

```
                                    ┌────────────────────────────┐
                                    │ 🔴 ALERTA CRÍTICO          │
                                    │ Intrusão detectada         │
                                    │ Pessoa detectada em área   │
                                    │ restrita do Bloco B        │
                                    │ 14:35:22              [X]  │
                                    │ ▓▓▓▓▓▓▓▓▓▓░░░░░░          │
                                    └────────────────────────────┘
                                    ┌────────────────────────────┐
                                    │ 🟢 WebSocket: Conectado    │
                                    │ Guardian conectado         │
                                    └────────────────────────────┘
```

**Características:**
- ✅ Aparece automaticamente em tempo real
- ✅ Som para alertas críticos/altos
- ✅ Desaparece sozinha após 10 segundos
- ✅ Barra de progresso animada
- ✅ Máximo 5 notificações simultâneas
- ✅ Botão [X] para fechar manualmente

---

## 🔧 SE NÃO ESTIVER VENDO AS MUDANÇAS

### Solução 1: Limpar Cache do Navegador
```
1. Chrome/Edge: Ctrl+Shift+Del
2. Marque "Imagens e arquivos em cache"
3. Clique em "Limpar dados"
4. Recarregue a página: Ctrl+F5
```

### Solução 2: Forçar Hard Refresh
```
- Chrome/Firefox/Edge: Ctrl+Shift+R ou Ctrl+F5
- Mac: Cmd+Shift+R
```

### Solução 3: Modo Anônimo
```
1. Abra uma janela anônima
2. Acesse http://localhost:3000
3. Faça login
4. Verifique se o Guardian aparece
```

### Solução 4: Reiniciar Next.js (JÁ FOI FEITO)
```bash
✅ Next.js já foi reiniciado automaticamente
✅ Rodando em: http://localhost:3000
✅ Build successful
```

---

## ✅ CHECKLIST - O QUE VOCÊ DEVE VER

### Menu Lateral
- [ ] Item "Guardian AI" na seção Segurança
- [ ] Ícone de escudo com check (ShieldCheck)
- [ ] Badge vermelho com número de alertas

### Dashboard Principal (`/dashboard`)
- [ ] Widget Guardian com status e risco
- [ ] Card "Acesso Rápido - Segurança" com 4 botões
- [ ] Estatísticas: alertas, incidentes, câmeras

### Página Guardian (`/guardian`)
- [ ] 4 cards de acesso rápido no topo
- [ ] Widget Guardian (1/3 da tela)
- [ ] Lista de alertas recentes (2/3 da tela)
- [ ] Iframe do Guardian completo (800px)
- [ ] Botões: Atualizar, Abrir em nova aba

### Subpáginas
- [ ] `/guardian/alertas` - Lista com filtros
- [ ] `/guardian/cameras` - Iframe câmeras
- [ ] `/guardian/analytics` - Iframe analytics

### Notificações
- [ ] Notificações popup no canto superior direito
- [ ] Indicador de conexão WebSocket

---

## 🎨 CORES E ESTILOS

### Severidades
- 🔵 **Baixo:** Azul (`bg-blue-100 text-blue-800`)
- 🟡 **Médio:** Amarelo (`bg-yellow-100 text-yellow-800`)
- 🟠 **Alto:** Laranja (`bg-orange-100 text-orange-800`)
- 🔴 **Crítico:** Vermelho (`bg-red-100 text-red-800`)

### Níveis de Risco
- 🟢 **Baixo:** Verde (`bg-green-100 text-green-600`)
- 🟡 **Moderado:** Amarelo (`bg-yellow-100 text-yellow-600`)
- 🟠 **Alto:** Laranja (`bg-orange-100 text-orange-600`)
- 🔴 **Crítico:** Vermelho (`bg-red-100 text-red-600`)

---

## 📱 RESPONSIVIDADE

O Guardian funciona em:
- ✅ **Desktop:** Layout completo
- ✅ **Tablet:** Cards empilhados
- ✅ **Mobile:** Single column

---

## 🔗 URLs IMPORTANTES

```
Dashboard Principal:    http://localhost:3000/dashboard
Guardian Principal:     http://localhost:3000/guardian
Alertas Guardian:       http://localhost:3000/guardian/alertas
Câmeras Guardian:       http://localhost:3000/guardian/cameras
Analytics Guardian:     http://localhost:3000/guardian/analytics

Guardian Externo:       https://91.108.124.140.nip.io/dashboard
API Guardian:           https://91.108.124.140.nip.io/api/v1/guardian/status
```

---

## 🎯 TESTE RÁPIDO

**Para testar se está tudo funcionando:**

1. ✅ Acesse: `http://localhost:3000/dashboard`
2. ✅ Faça login
3. ✅ Olhe no menu lateral esquerdo
4. ✅ Procure por "Guardian AI" na seção Segurança
5. ✅ Clique em "Guardian AI"
6. ✅ Você deve ver a página completa do Guardian

**Se você VER "Guardian AI" no menu → SUCESSO! ✅**
**Se você NÃO ver → Limpe o cache e force refresh (Ctrl+Shift+R)**

---

**Criado em:** 22/12/2025
**Versão:** 1.0.0
