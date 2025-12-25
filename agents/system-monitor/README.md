# 🛡️ Conecta Plus System Monitor Agent

**Agente de IA Autônomo para Monitoramento e Correção Automática do Sistema**

Versão: 1.0.0
Data: 22/12/2025

---

## 📋 Visão Geral

O **System Monitor Agent** é um agente de inteligência artificial completamente autônomo que monitora, detecta problemas, corrige erros e otimiza o sistema Conecta Plus automaticamente.

### Características Principais

✅ **Monitoramento Contínuo**
- Análise de logs em tempo real (Next.js, Backend, Nginx)
- Coleta de métricas do sistema (CPU, memória, disco, rede)
- Detecção de erros e anomalias

✅ **Correção Automática**
- Corrige erros comuns automaticamente (ECONNRESET, timeouts, locks)
- Reinicia serviços quando necessário
- Limpa recursos (disco, memória)
- Gerencia dependências

✅ **Detecção de Gaps**
- Identifica dependências faltando
- Detecta pacotes desatualizados
- Encontra vulnerabilidades de segurança
- Analisa performance e qualidade do código
- Detecta código não utilizado

✅ **Relatórios Detalhados**
- Relatórios em JSON, HTML e Markdown
- Dashboard web em tempo real
- Estatísticas e métricas históricas

---

## 🏗️ Arquitetura

```
/opt/conecta-plus/agents/system-monitor/
├── agent.py                      # Agente principal
├── config.yaml                   # Configuração
├── requirements.txt              # Dependências Python
├── install.sh                    # Script de instalação
├── skills/                       # Skills do agente
│   ├── log_analyzer.py           # Análise de logs
│   ├── error_fixer.py            # Correção automática
│   ├── gap_detector.py           # Detecção de gaps
│   └── reporter.py               # Geração de relatórios
├── mcps/                         # Model Context Protocols
│   ├── logs_mcp/                 # Tools para logs
│   ├── metrics_mcp/              # Tools para métricas
│   └── code_analyzer_mcp/        # Tools para análise de código
├── dashboard/                    # Dashboard web
│   └── app.py                    # Servidor Flask
├── logs/                         # Logs do agente
├── reports/                      # Relatórios gerados
└── state.json                    # Estado atual

Serviços systemd:
├── /etc/systemd/system/system-monitor.service
└── /etc/systemd/system/system-monitor-dashboard.service
```

---

## 📦 Instalação

### Opção 1: Script Automático

```bash
cd /opt/conecta-plus/agents/system-monitor
./install.sh
```

### Opção 2: Manual

```bash
# 1. Instalar dependências
pip3 install --break-system-packages -r requirements.txt

# 2. Criar diretórios
mkdir -p logs reports corrections

# 3. Tornar executável
chmod +x agent.py dashboard/app.py

# 4. Instalar serviços
cp *.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable system-monitor
systemctl enable system-monitor-dashboard
```

---

## 🚀 Uso

### Iniciar Serviços

```bash
# Iniciar agente
systemctl start system-monitor

# Iniciar dashboard
systemctl start system-monitor-dashboard
```

### Parar Serviços

```bash
systemctl stop system-monitor
systemctl stop system-monitor-dashboard
```

### Ver Status

```bash
systemctl status system-monitor
systemctl status system-monitor-dashboard
```

### Executar Uma Vez (Teste)

```bash
python3 /opt/conecta-plus/agents/system-monitor/agent.py --once
```

### Ver Logs

```bash
# Logs do agente (journald)
journalctl -u system-monitor -f

# Logs do dashboard
journalctl -u system-monitor-dashboard -f

# Ou diretamente
tail -f /opt/conecta-plus/agents/system-monitor/logs/agent.log
tail -f /opt/conecta-plus/agents/system-monitor/logs/dashboard.log
```

---

## 🎯 Dashboard Web

**URL:** `http://localhost:8888` ou `http://SEU_IP:8888`

O dashboard fornece:
- **Status do sistema em tempo real**
- **Métricas de CPU, memória e disco**
- **Lista de erros corrigidos**
- **Gaps detectados**
- **Ações tomadas automaticamente**
- **Relatórios gerados**
- **Auto-refresh a cada 30 segundos**

---

## ⚙️ Configuração

Edite `/opt/conecta-plus/agents/system-monitor/config.yaml`:

```yaml
agent:
  interval: 30  # Intervalo entre análises (segundos)
  auto_fix: true  # Habilitar correções automáticas

monitoring:
  logs:
    - path: "/tmp/nextjs-debug.log"
      type: "nextjs"

  metrics:
    cpu_threshold: 90
    memory_threshold: 85
    disk_threshold: 90

auto_fixes:
  enabled: true
  max_attempts: 3
  cooldown: 300

gap_detection:
  enabled: true

reporting:
  enabled: true
  interval: 3600  # Relatório a cada hora
  formats:
    - json
    - html
    - markdown
```

---

## 🔧 Skills Disponíveis

### 1. Log Analyzer
- Analisa logs do Next.js, Backend e Nginx
- Detecta erros e warnings
- Classifica severidade (critical, high, medium, low, ok)
- Gera recomendações automáticas

### 2. Error Fixer
- **Erros de Rede:** Reinicia proxies, retry logic
- **Timeouts:** Identifica processos lentos
- **Lock Files:** Remove locks do Next.js
- **Dependências:** Executa npm/pip install
- **Disco Cheio:** Limpa logs antigos
- **Conflitos de Porta:** Mata processos

### 3. Gap Detector
- Dependências faltando (npm, pip)
- Pacotes desatualizados
- Vulnerabilidades (npm audit)
- Secrets hardcoded no código
- Bundles grandes (>500KB)
- Alto uso de recursos
- Código de baixa qualidade
- TODO/FIXME não resolvidos

### 4. Reporter
- Gera relatórios em JSON, HTML e Markdown
- Resumo executivo
- Estatísticas detalhadas
- Recomendações priorizadas

---

## 🔌 MCPs (Model Context Protocols)

### Logs MCP
- `tail_log`: Últimas N linhas de um log
- `grep_log`: Buscar padrão em log
- `watch_log`: Monitorar log em tempo real
- `count_pattern`: Contar ocorrências
- `rotate_log`: Rotacionar logs grandes

### Metrics MCP
- `get_cpu_usage`: Uso de CPU
- `get_memory_usage`: Uso de memória
- `get_disk_usage`: Uso de disco
- `get_network_stats`: Estatísticas de rede
- `get_process_info`: Info sobre processos
- `check_port`: Verificar porta em uso

### Code Analyzer MCP
- `find_files`: Encontrar arquivos
- `search_code`: Buscar no código
- `count_lines`: Contar linhas (código/comentários)
- `analyze_imports`: Analisar imports
- `detect_todos`: Encontrar TODOs
- `find_large_files`: Arquivos grandes
- `analyze_complexity`: Complexidade ciclomática

---

## 📊 Exemplos de Uso

### Exemplo 1: Erro ECONNRESET Detectado

```
2025-12-22 18:00:00 - SystemMonitor - INFO - Error detected: ECONNRESET
2025-12-22 18:00:01 - SystemMonitor - INFO - ✓ Fixed: network - restart_nextjs
```

O agente automaticamente:
1. Detectou erro de rede
2. Reiniciou Next.js
3. Removeu lock file
4. Verificou funcionamento

### Exemplo 2: Disco Cheio

```
2025-12-22 19:00:00 - SystemMonitor - WARNING - High disk usage: 92%
2025-12-22 19:00:05 - SystemMonitor - INFO - ✓ Fixed: disk - cleaned_old_logs
```

O agente automaticamente:
1. Detectou disco quase cheio
2. Limpou logs com mais de 7 dias
3. Liberou espaço
4. Verificou se resolveu

### Exemplo 3: Dependência Faltando

```
2025-12-22 20:00:00 - SystemMonitor - INFO - Gap detected: missing_npm_package - redis
2025-12-22 20:00:00 - SystemMonitor - INFO - Recommendation: Run npm install
```

O agente:
1. Detectou dependência faltando
2. Gerou recomendação
3. Incluiu no relatório

---

## 📈 Estatísticas

O agente mantém estatísticas de:
- **Total de iterações** executadas
- **Total de erros corrigidos**
- **Total de gaps detectados**
- **Taxa de sucesso** das correções
- **Histórico de ações**

Acesse via Dashboard ou em `/opt/conecta-plus/agents/system-monitor/state.json`

---

## 🔒 Segurança

- ✅ Executa como root (necessário para operações de sistema)
- ✅ Logs detalhados de todas as ações
- ✅ Cooldown para evitar loops infinitos
- ✅ Máximo de tentativas configurável
- ✅ Não executa comandos arbitrários
- ✅ Valida todas as operações

---

## 🐛 Troubleshooting

### Agente não inicia

```bash
# Verificar status
systemctl status system-monitor

# Ver logs de erro
journalctl -u system-monitor -n 50

# Testar manualmente
python3 /opt/conecta-plus/agents/system-monitor/agent.py --once
```

### Dashboard não carrega

```bash
# Verificar porta
lsof -i :8888

# Reiniciar
systemctl restart system-monitor-dashboard

# Ver logs
tail -f /opt/conecta-plus/agents/system-monitor/logs/dashboard-error.log
```

### Dependências faltando

```bash
pip3 install --break-system-packages -r requirements.txt
```

---

## 📝 Desenvolvimento

### Adicionar Nova Skill

1. Criar arquivo em `skills/nova_skill.py`
2. Implementar classe com métodos
3. Importar em `agent.py`
4. Chamar no ciclo de monitoramento

### Adicionar Novo MCP

1. Criar diretório em `mcps/novo_mcp/`
2. Implementar `__init__.py` com `get_tools()`
3. Importar em `agent.py`
4. Usar tools no agente

---

## 📞 Suporte

- **Logs:** `/opt/conecta-plus/agents/system-monitor/logs/`
- **Estado:** `/opt/conecta-plus/agents/system-monitor/state.json`
- **Relatórios:** `/opt/conecta-plus/agents/system-monitor/reports/`
- **Dashboard:** `http://localhost:8888`

---

## 📜 Licença

Sistema Conecta Plus
© 2025 - Todos os direitos reservados

---

**Criado em:** 22/12/2025
**Versão:** 1.0.0
**Autor:** Claude Sonnet 4.5 + System Monitor AI
