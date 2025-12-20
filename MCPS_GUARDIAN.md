# MCPs GUARDIAN - FASE 4
## Model Context Protocols para Sistema de Seguranca

**Data:** 2025-12-20
**Versao:** 2.0.0
**Modulo:** mcps/mcp-guardian-*/

---

## VISAO GERAL

Os MCPs Guardian implementam a interface de comunicacao entre o Claude e o sistema de seguranca, seguindo o padrao Model Context Protocol da Anthropic. Estes MCPs permitem que agentes de IA interajam com todos os subsistemas de seguranca de forma padronizada.

### Arquitetura MCP

```
┌─────────────────────────────────────────────────────────────┐
│                         Claude AI                            │
└─────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │   MCP Protocol    │
                    └─────────┬─────────┘
          ┌───────────────────┼───────────────────┐
          │         │         │         │         │
    ┌─────┴─────┐ ┌─┴───┐ ┌───┴───┐ ┌───┴───┐ ┌───┴────┐
    │  Guardian │ │ Not │ │Access │ │Analyt │ │Frigate │
    │   Core    │ │ifs  │ │       │ │ ics   │ │  NVR   │
    └───────────┘ └─────┘ └───────┘ └───────┘ └────────┘
          │         │         │         │         │
    ┌─────┴─────────┴─────────┴─────────┴─────────┴─────┐
    │              Backend API / Hardware               │
    └───────────────────────────────────────────────────┘
```

---

## MCPs IMPLEMENTADOS

### 1. MCP Guardian Core
**Diretorio:** `mcps/mcp-guardian-core/`
**Funcao:** Sistema central de seguranca

#### Tools Disponiveis (38 tools):

| Categoria | Tool | Descricao |
|-----------|------|-----------|
| **Config** | `guardian_configure` | Configura conexao com API |
| | `guardian_status` | Status geral do sistema |
| **Alertas** | `guardian_list_alerts` | Lista alertas ativos |
| | `guardian_get_alert` | Detalhes de alerta |
| | `guardian_acknowledge_alert` | Reconhece alerta |
| | `guardian_dismiss_alert` | Descarta alerta |
| | `guardian_create_alert` | Cria alerta manual |
| **Incidentes** | `guardian_list_incidents` | Lista incidentes |
| | `guardian_get_incident` | Detalhes de incidente |
| | `guardian_create_incident` | Cria incidente |
| | `guardian_acknowledge_incident` | Reconhece incidente |
| | `guardian_update_incident` | Atualiza status |
| | `guardian_resolve_incident` | Resolve incidente |
| | `guardian_get_incident_timeline` | Timeline de acoes |
| **Risco** | `guardian_get_risk_assessment` | Avaliacao de risco |
| | `guardian_get_anomalies` | Anomalias detectadas |
| | `guardian_get_predictions` | Predicoes de seguranca |
| **Cameras** | `guardian_list_cameras` | Lista cameras |
| | `guardian_get_camera` | Detalhes de camera |
| | `guardian_camera_snapshot` | Captura snapshot |
| | `guardian_toggle_camera_detection` | Liga/desliga deteccao |
| | `guardian_toggle_camera_recording` | Liga/desliga gravacao |
| **Assistente** | `guardian_chat` | Chat com assistente |
| | `guardian_quick_status` | Status rapido em texto |
| **Dashboard** | `guardian_dashboard` | Dados consolidados |
| | `guardian_statistics` | Estatisticas |
| **Acoes** | `guardian_trigger_alarm` | Aciona alarme |
| | `guardian_deactivate_alarm` | Desativa alarme |
| | `guardian_lock_access` | Bloqueia acesso |
| | `guardian_unlock_access` | Desbloqueia acesso |
| | `guardian_dispatch_security` | Despacha seguranca |

---

### 2. MCP Guardian Notifications
**Diretorio:** `mcps/mcp-guardian-notifications/`
**Funcao:** Sistema de notificacoes multi-canal

#### Canais Suportados:
- SMS (Twilio, Zenvia)
- Email (SMTP, SendGrid)
- Push (Firebase, OneSignal)
- WhatsApp (Evolution, Z-API)
- Chamada Telefonica (Asterisk, Twilio)
- Intercomunicador (SIP)
- Dashboard (WebSocket)

#### Tools Disponiveis (22 tools):

| Categoria | Tool | Descricao |
|-----------|------|-----------|
| **Canais** | `notification_configure_channel` | Configura canal |
| | `notification_list_channels` | Lista canais |
| | `notification_test_channel` | Testa canal |
| **Envio** | `notification_send` | Envia notificacao |
| | `notification_send_template` | Envia via template |
| | `notification_broadcast` | Broadcast multi-destinatario |
| | `notification_send_to_group` | Envia para grupo |
| **Templates** | `notification_list_templates` | Lista templates |
| | `notification_get_template` | Obtem template |
| | `notification_create_template` | Cria template |
| | `notification_update_template` | Atualiza template |
| **Contatos** | `notification_add_contact` | Adiciona contato |
| | `notification_list_contacts` | Lista contatos |
| | `notification_remove_contact` | Remove contato |
| **Grupos** | `notification_create_group` | Cria grupo |
| | `notification_list_groups` | Lista grupos |
| | `notification_add_to_group` | Adiciona ao grupo |
| **Historico** | `notification_history` | Historico envios |
| | `notification_get_status` | Status de notificacao |
| **Emergencia** | `notification_emergency_broadcast` | Broadcast emergencia |
| | `notification_intercom_announce` | Anuncio intercomunicador |

#### Templates Pre-configurados:
- `alert_security` - Alertas de seguranca
- `incident_created` - Novo incidente
- `incident_escalated` - Escalonamento
- `emergency` - Emergencias
- `access_denied` - Acesso negado

---

### 3. MCP Guardian Access
**Diretorio:** `mcps/mcp-guardian-access/`
**Funcao:** Controle de acesso unificado

#### Fabricantes Suportados:
- Control iD (iDAccess, iDBox, iDFlex, iDFace)
- Intelbras (SS 3530, SS 5530)
- Hikvision (DS-K series)
- Garen, Nice, PPA, JFL

#### Credenciais Suportadas:
- Face (reconhecimento facial)
- Fingerprint (biometria digital)
- Card (RFID/Mifare)
- QR Code
- Plate (ANPR/LPR)
- PIN
- Bluetooth

#### Tools Disponiveis (35 tools):

| Categoria | Tool | Descricao |
|-----------|------|-----------|
| **Controladoras** | `access_add_controller` | Adiciona controladora |
| | `access_list_controllers` | Lista controladoras |
| | `access_controller_status` | Status controladora |
| | `access_sync_controller` | Sincroniza dados |
| **Pontos** | `access_add_point` | Adiciona ponto acesso |
| | `access_list_points` | Lista pontos |
| | `access_lock_point` | Bloqueia ponto |
| | `access_unlock_point` | Desbloqueia ponto |
| | `access_open_point` | Abre remotamente |
| **Pessoas** | `access_add_person` | Cadastra pessoa |
| | `access_get_person` | Obtem dados pessoa |
| | `access_list_persons` | Lista pessoas |
| | `access_block_person` | Bloqueia pessoa |
| | `access_unblock_person` | Desbloqueia pessoa |
| **Credenciais** | `access_add_credential` | Adiciona credencial |
| | `access_remove_credential` | Remove credencial |
| | `access_enroll_face` | Cadastra face |
| | `access_enroll_fingerprint` | Cadastra digital |
| **Veiculos** | `access_add_vehicle` | Cadastra veiculo |
| | `access_list_vehicles` | Lista veiculos |
| | `access_authorize_vehicle` | Autoriza/desautoriza |
| **Validacao** | `access_validate` | Valida acesso |
| | `access_validate_plate` | Valida por placa |
| **Logs** | `access_get_logs` | Obtem logs acesso |
| | `access_statistics` | Estatisticas |
| **Visitantes** | `access_create_visitor` | Cria visitante |
| | `access_list_visitors` | Lista visitantes |
| | `access_checkout_visitor` | Registra saida |
| **Emergencia** | `access_emergency_unlock_all` | Desbloqueia todos |
| | `access_emergency_lock_all` | Lockdown |

---

### 4. MCP Guardian Analytics
**Diretorio:** `mcps/mcp-guardian-analytics/`
**Funcao:** Analises e relatorios de seguranca

#### Tools Disponiveis (27 tools):

| Categoria | Tool | Descricao |
|-----------|------|-----------|
| **Metricas** | `analytics_get_metrics` | Metricas principais |
| | `analytics_get_kpis` | KPIs de seguranca |
| | `analytics_compare_periods` | Compara periodos |
| **Series Temp** | `analytics_get_timeseries` | Dados serie temporal |
| | `analytics_get_heatmap` | Heatmap atividade |
| **Tendencias** | `analytics_get_trends` | Analise tendencias |
| | `analytics_get_predictions` | Predicoes |
| | `analytics_get_anomalies` | Anomalias detectadas |
| **Relatorios** | `analytics_generate_report` | Gera relatorio |
| | `analytics_get_daily_summary` | Resumo diario |
| | `analytics_create_report_config` | Config relatorio recorrente |
| | `analytics_list_scheduled_reports` | Lista agendados |
| **Acessos** | `analytics_access_summary` | Resumo acessos |
| | `analytics_access_patterns` | Padroes acesso |
| | `analytics_peak_hours` | Horarios pico |
| **Incidentes** | `analytics_incident_summary` | Resumo incidentes |
| | `analytics_response_times` | Tempos resposta |
| | `analytics_incident_hotspots` | Hotspots |
| **Risco** | `analytics_risk_evolution` | Evolucao risco |
| | `analytics_risk_factors` | Fatores de risco |
| | `analytics_vulnerability_windows` | Janelas vulnerabilidade |
| **Export** | `analytics_export_data` | Exporta dados |
| **Dashboard** | `analytics_dashboard_data` | Dados dashboard |

---

## INTEGRACAO COM CLAUDE

### Configuracao do Claude Desktop

Adicionar ao `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "guardian-core": {
      "command": "npx",
      "args": ["tsx", "/opt/conecta-plus/mcps/mcp-guardian-core/index.ts"],
      "env": {
        "GUARDIAN_API_URL": "http://localhost:8000",
        "GUARDIAN_API_KEY": "sua-api-key"
      }
    },
    "guardian-notifications": {
      "command": "npx",
      "args": ["tsx", "/opt/conecta-plus/mcps/mcp-guardian-notifications/index.ts"]
    },
    "guardian-access": {
      "command": "npx",
      "args": ["tsx", "/opt/conecta-plus/mcps/mcp-guardian-access/index.ts"]
    },
    "guardian-analytics": {
      "command": "npx",
      "args": ["tsx", "/opt/conecta-plus/mcps/mcp-guardian-analytics/index.ts"]
    }
  }
}
```

---

## EXEMPLOS DE USO

### 1. Verificar Status do Sistema

```
Usuario: Qual o status atual do sistema de seguranca?

Claude: [Usa guardian_status e guardian_quick_status]

Resposta: Sistema operando normalmente.
- 23/24 cameras online
- 2 alertas ativos (medium)
- 1 incidente em andamento
- Score de risco: 35/100 (baixo)
```

### 2. Liberar Acesso para Visitante

```
Usuario: Preciso liberar acesso para Joao da Silva, visitante da unidade 101

Claude: [Usa access_create_visitor]

Resposta: Visitante cadastrado com sucesso:
- Nome: Joao da Silva
- Visitando: Unidade 101
- Valido ate: 20/12/2025 23:59
- Pode acessar: Entrada Principal, Portaria Social
```

### 3. Gerar Relatorio Semanal

```
Usuario: Gere um relatorio semanal de seguranca

Claude: [Usa analytics_generate_report]

Resposta: Relatorio gerado:

RESUMO SEMANAL DE SEGURANCA
Periodo: 13/12 a 20/12/2025

Acessos: 3.405 (97.6% autorizados)
Incidentes: 8 (100% resolvidos)
Alertas: 45 (0 criticos)
Score medio de risco: 38/100

Recomendacoes:
1. Verificar camera CAM-B04 (2 eventos offline)
2. Revisar regras de acesso noturno
```

### 4. Responder a Emergencia

```
Usuario: Ativar protocolo de emergencia - incendio no Bloco B

Claude: [Usa notification_emergency_broadcast, access_emergency_unlock_all]

Resposta: Protocolo de emergencia ativado:
1. Alarmes acionados em todas as areas
2. Saidas de emergencia desbloqueadas
3. Notificacao enviada:
   - Intercomunicador: todas as zonas
   - SMS: equipe de seguranca
   - Push: todos os moradores
4. Bombeiros acionados (193)

Status: Em andamento
```

---

## INTEGRACAO COM OUTROS MCPs

Os MCPs Guardian podem trabalhar em conjunto com os MCPs existentes:

| MCP Existente | Integracao |
|---------------|------------|
| `mcp-frigate-nvr` | Cameras e deteccoes |
| `mcp-control-id` | Controladoras Control iD |
| `mcp-intelbras-acesso` | Controladoras Intelbras |
| `mcp-mqtt` | Comunicacao IoT |
| `mcp-asterisk` | Chamadas telefonicas |
| `mcp-vision-ai` | Reconhecimento facial |
| `mcp-whisper` | Transcrição de audio |

---

## ARQUIVOS CRIADOS

| Arquivo | Linhas | Descricao |
|---------|--------|-----------|
| `mcp-guardian-core/index.ts` | ~750 | Core do sistema |
| `mcp-guardian-core/package.json` | 20 | Config npm |
| `mcp-guardian-notifications/index.ts` | ~700 | Notificacoes |
| `mcp-guardian-notifications/package.json` | 20 | Config npm |
| `mcp-guardian-access/index.ts` | ~900 | Controle acesso |
| `mcp-guardian-access/package.json` | 20 | Config npm |
| `mcp-guardian-analytics/index.ts` | ~650 | Analytics |
| `mcp-guardian-analytics/package.json` | 20 | Config npm |

**Total:** ~3.080 linhas de codigo TypeScript

---

## INSTALACAO

```bash
# Entrar no diretorio de cada MCP
cd /opt/conecta-plus/mcps/mcp-guardian-core
npm install

cd /opt/conecta-plus/mcps/mcp-guardian-notifications
npm install

cd /opt/conecta-plus/mcps/mcp-guardian-access
npm install

cd /opt/conecta-plus/mcps/mcp-guardian-analytics
npm install
```

---

## PROXIMOS PASSOS - FASE 5

### Integracao Final
1. [ ] Conectar MCPs aos routers do backend FastAPI
2. [ ] Implementar autenticacao entre MCPs e API
3. [ ] Configurar WebSockets para tempo real
4. [ ] Integrar com frontend React
5. [ ] Testes de integracao E2E
6. [ ] Deploy em producao

---

## CONCLUSAO

A Fase 4 implementou 4 MCPs completos com:

- **122 tools** para interacao com Claude
- **Suporte multi-fabricante** para controladoras
- **Notificacoes multi-canal** (SMS, Email, Push, WhatsApp)
- **Analytics avancado** com predicoes e tendencias
- **Integracao pronta** com MCPs existentes

O sistema esta preparado para a **Fase 5: Integracao Final**.

---

*Documento gerado automaticamente pelo Claude Code Guardian*
*Data: 2025-12-20 | Versao: 2.0*
