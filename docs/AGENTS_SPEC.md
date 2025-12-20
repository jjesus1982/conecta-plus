# Conecta Plus - Especificação dos Agentes IA

## Framework de Evolução

### Classe Base: `BaseAgent`

```python
from agents.core import BaseAgent, EvolutionLevel

class MeuAgente(BaseAgent):
    def __init__(self, condominio_id: str, **kwargs):
        super().__init__(
            agent_id=f"meu_agente_{condominio_id}",
            agent_type="meu_agente",
            condominio_id=condominio_id,
            evolution_level=EvolutionLevel.TRANSCENDENT,
            **kwargs
        )

    def _register_capabilities(self) -> None:
        # Registrar capacidades específicas
        pass

    def get_system_prompt(self) -> str:
        # Retornar prompt do sistema
        pass

    async def process(self, input_data: Dict, context: AgentContext) -> Dict:
        # Processar entrada
        pass
```

### Níveis de Evolução

| Nível | Nome | Capacidades |
|-------|------|-------------|
| 1 | REACTIVE | Responde a comandos |
| 2 | PROACTIVE | Antecipa necessidades |
| 3 | PREDICTIVE | Faz previsões |
| 4 | AUTONOMOUS | Age sozinho |
| 5 | EVOLUTIONARY | Aprende continuamente |
| 6 | COLLABORATIVE | Trabalha com outros |
| 7 | TRANSCENDENT | Insights além do óbvio |

---

## Agente Financeiro

### Identificação
- **ID Pattern**: `financeiro_{condominio_id}`
- **Tipo**: `financeiro`
- **Nível Máximo**: TRANSCENDENT (7)

### Capacidades por Nível

#### Nível 1: REATIVO
- `consultar_saldo`: Consultar saldo de contas
- `gerar_boleto`: Gerar boletos de cobrança
- `registrar_pagamento`: Registrar pagamentos

#### Nível 2: PROATIVO
- `alertar_inadimplencia`: Alertar sobre inadimplência
- `lembrar_vencimento`: Enviar lembretes

#### Nível 3: PREDITIVO
- `prever_inadimplencia`: Prever risco de inadimplência
- `projetar_fluxo_caixa`: Projetar fluxo de caixa

#### Nível 4: AUTÔNOMO
- `renegociar_dividas`: Renegociar automaticamente
- `aplicar_multas`: Aplicar multas/juros

#### Nível 5: EVOLUTIVO
- `aprender_padroes_pagamento`: Aprender padrões

#### Nível 6: COLABORATIVO
- `integrar_sindico`: Integrar com Síndico

#### Nível 7: TRANSCENDENTE
- `otimizar_financas`: Otimização avançada

### Configurações

```python
config = {
    "taxa_juros_atraso": 0.01,      # 1% ao mês
    "taxa_multa_atraso": 0.02,       # 2% fixo
    "dias_tolerancia": 3,
    "dias_alerta_vencimento": 5,
    "limite_renegociacao_automatica": 5000,
    "parcelas_max_renegociacao": 12,
}
```

### API de Ações

```json
// Consultar saldo
{
  "action": "consultar_saldo",
  "params": {
    "conta_id": "opcional"
  }
}

// Gerar boleto
{
  "action": "gerar_boleto",
  "params": {
    "unidade_id": "101",
    "valor": 850.00,
    "vencimento": "2025-01-10",
    "competencia": "2025-01"
  }
}

// Prever inadimplência
{
  "action": "prever_inadimplencia",
  "params": {
    "unidade_id": "101"
  }
}

// Otimização transcendente
{
  "action": "otimizar",
  "params": {}
}
```

### Resposta de Otimização

```json
{
  "success": true,
  "nivel": "TRANSCENDENTE",
  "otimizacoes": {
    "otimizacoes": [
      {
        "tipo": "fluxo_caixa",
        "descricao": "Ajustar vencimento para dia 10",
        "economia_potencial": 2500.00,
        "implementacao": "...",
        "risco": "baixo",
        "confianca": 0.85
      }
    ],
    "correlacoes_descobertas": ["..."],
    "previsoes_longo_prazo": ["..."]
  }
}
```

---

## Agente CFTV

### Identificação
- **ID Pattern**: `cftv_{condominio_id}`
- **Tipo**: `cftv`
- **Nível Máximo**: TRANSCENDENT (7)

### Capacidades por Nível

#### Nível 1: REATIVO
- `visualizar_cameras`: Ver feeds em tempo real
- `buscar_gravacoes`: Buscar gravações
- `controlar_ptz`: Controlar PTZ

#### Nível 2: PROATIVO
- `detectar_movimento`: Detectar movimento
- `monitorar_zonas`: Monitorar zonas

#### Nível 3: PREDITIVO
- `detectar_objetos`: Detectar pessoas/veículos
- `analisar_comportamento`: Análise comportamental
- `prever_incidentes`: Prever incidentes

#### Nível 4: AUTÔNOMO
- `acoes_automaticas`: Ações de segurança
- `ajustar_cameras`: Ajuste automático

#### Nível 5: EVOLUTIVO
- `aprender_padroes`: Aprender padrões de ameaça

#### Nível 6: COLABORATIVO
- `integrar_acesso`: Integrar com Acesso
- `integrar_alarme`: Integrar com Alarme

#### Nível 7: TRANSCENDENTE
- `vigilancia_cognitiva`: Vigilância cognitiva

### Tipos de Evento

```python
class TipoEvento(Enum):
    MOVIMENTO = "movimento"
    PESSOA = "pessoa"
    VEICULO = "veiculo"
    OBJETO_ABANDONADO = "objeto_abandonado"
    CERCA_VIRTUAL = "cerca_virtual"
    AGLOMERACAO = "aglomeracao"
    COMPORTAMENTO_SUSPEITO = "comportamento_suspeito"
    INVASAO = "invasao"
    QUEDA = "queda"
    BRIGA = "briga"
```

### Níveis de Risco

```python
class NivelRisco(Enum):
    BAIXO = 1
    MEDIO = 2
    ALTO = 3
    CRITICO = 4
```

### Configurações

```python
config = {
    "confianca_minima_alerta": 0.7,
    "tempo_analise_comportamento": 30,
    "cooldown_alertas": 300,
    "sensibilidade_movimento": 0.5,
    "horarios_alta_vigilancia": ["22:00-06:00"],
}
```

### API de Ações

```json
// Listar câmeras
{
  "action": "listar_cameras",
  "params": {}
}

// Visualizar câmera
{
  "action": "visualizar_camera",
  "params": {
    "camera_id": "cam_001"
  }
}

// Buscar gravação
{
  "action": "buscar_gravacao",
  "params": {
    "camera_id": "cam_001",
    "data_inicio": "2025-01-01T00:00:00",
    "data_fim": "2025-01-01T23:59:59"
  }
}

// Análise cognitiva (Nível 7)
{
  "action": "analise_cognitiva",
  "params": {
    "periodo": "24h"
  }
}
```

### Resposta de Análise Cognitiva

```json
{
  "success": true,
  "nivel": "TRANSCENDENTE",
  "analise": {
    "correlacoes_ocultas": [
      "Aumento movimento noturno correlacionado com obras"
    ],
    "ameacas_previstas": [
      {
        "descricao": "Possível reconhecimento de terreno",
        "probabilidade": 0.35,
        "prazo": "próximas 2 semanas"
      }
    ],
    "vulnerabilidades": [
      {
        "local": "Muro lateral leste",
        "descricao": "Ponto cego entre câmeras",
        "severidade": "média"
      }
    ],
    "nivel_seguranca_geral": 0.82,
    "insights_transcendentes": [
      "Correlação clima-incidentes: dias nublados +23%"
    ]
  }
}
```

---

## Sistema de Memória

### UnifiedMemorySystem

```python
from agents.core import UnifiedMemorySystem

memory = UnifiedMemorySystem(
    redis_url="redis://:password@localhost:6379",
    vector_persist_dir="./data/vector_db"
)

# Key-Value
await memory.store(agent_id, key, value, metadata)
await memory.retrieve(agent_id, key)

# Semântica
await memory.remember_semantic(agent_id, content, metadata)
await memory.search_semantic(agent_id, query, limit=10)

# Episódica
episode = memory.start_episode(agent_id, context)
memory.add_episode_event(episode_id, event_type, data)
await memory.end_episode(episode_id, outcome, summary, lessons)

# Working (contexto)
memory.add_to_context(session_id, item_type, content)
memory.get_context(session_id, limit=10)
```

---

## Sistema RAG

### Criar Sistema RAG

```python
from agents.core import create_rag_system, Document, DocumentType

rag = create_rag_system(conversational=True)

# Indexar documento
doc = Document(
    doc_id="reg_001",
    content="Regulamento do condomínio...",
    doc_type=DocumentType.TEXT,
    title="Regulamento Interno"
)
await rag.index_documents([doc])

# Query
response = await rag.query(
    question="Qual o horário de silêncio?",
    top_k=5
)

print(response.answer)
print(response.sources)
print(response.confidence)
```

---

## LLM Client

### Cliente Unificado

```python
from agents.core import UnifiedLLMClient, LLMMessage

llm = UnifiedLLMClient()

# Geração simples
response = await llm.generate(
    system_prompt="Você é um assistente...",
    user_prompt="Qual o saldo?"
)

# Chat com histórico
messages = [
    LLMMessage(role="system", content="..."),
    LLMMessage(role="user", content="..."),
]
response = await llm.chat(messages)

# Com tools
response = await llm.generate_with_tools(messages, tools)
```

### Provedores Suportados

| Provider | Modelo Padrão | Fallback |
|----------|---------------|----------|
| Claude | claude-sonnet-4-20250514 | Sim |
| OpenAI | gpt-4o | Sim |
| Ollama | llama3.2 | Local |

---

## Tools (Ferramentas)

### Registro de Ferramentas

```python
from agents.core.tools import ToolRegistry, create_standard_tools

tools = create_standard_tools(
    db_pool=db_pool,
    notification_url="http://notification:8000",
    integration_hub_url="http://hub:8000"
)

# Usar ferramenta
result = await tools.execute(
    "database_query",
    table="financeiro_boletos",
    where={"status": "pendente"},
    limit=100
)
```

### Ferramentas Disponíveis

| Tool | Categoria | Descrição |
|------|-----------|-----------|
| database_query | DATABASE | SELECT seguro |
| database_insert | DATABASE | INSERT com validação |
| database_update | DATABASE | UPDATE com validação |
| send_notification | NOTIFICATION | Multi-canal |
| send_whatsapp | NOTIFICATION | WhatsApp API |
| analyze_data | ANALYSIS | Estatísticas |
| predict_values | ANALYSIS | Previsões |
| call_mcp | INTEGRATION | Chamar MCPs |

---

## Colaboração entre Agentes

### Registro de Colaborador

```python
# Agente CFTV registra Agente Acesso
agente_cftv.register_collaborator(agente_acesso)
```

### Envio de Mensagem

```python
await agente_cftv.send_message(
    receiver_id="acesso_condo_001",
    content={"action": "bloquear_area", "zona": "entrada"},
    priority=Priority.CRITICAL
)
```

### Processamento de Mensagens

```python
# No agente receptor
async def _handle_message(self, message: AgentMessage):
    if message.content.get("action") == "bloquear_area":
        await self._bloquear_zona(message.content.get("zona"))
```

---

## Ciclo de Vida do Agente

```python
# Criar
agente = create_financial_agent(
    condominio_id="condo_001",
    evolution_level=EvolutionLevel.TRANSCENDENT
)

# Iniciar
await agente.start()

# Processar
context = AgentContext(
    condominio_id="condo_001",
    user_id="user_001",
    session_id="session_001"
)

result = await agente.process(
    input_data={"action": "consultar_saldo"},
    context=context
)

# Métricas
metrics = agente.get_metrics()
state = agente.get_state()

# Parar
await agente.stop()
```

---

## Lista de Todos os Agentes

| # | Agente | Domínio | Principais Ações |
|---|--------|---------|------------------|
| 1 | financeiro | Finanças | Boletos, cobrança, previsões |
| 2 | cftv | Segurança | Câmeras, detecção, vigilância |
| 3 | acesso | Segurança | Portões, biometria, visitantes |
| 4 | automacao | IoT | Iluminação, climatização |
| 5 | alarme | Segurança | Sensores, sirenes |
| 6 | rede | Infra | WiFi, conectividade |
| 7 | portaria-virtual | Portaria | Atendimento automatizado |
| 8 | rh | RH | Funcionários, ponto |
| 9 | facilities | Manutenção | Facilities management |
| 10 | manutencao | Manutenção | Ordens de serviço |
| 11 | sindico | Gestão | Assistente do síndico |
| 12 | assembleias | Gestão | Assembleias, votações |
| 13 | reservas | Áreas comuns | Reserva de espaços |
| 14 | morador | Moradores | Assistente do morador |
| 15 | comunicacao | Comunicação | Avisos, circulares |
| 16 | encomendas | Portaria | Gestão de entregas |
| 17 | ocorrencias | Operacional | Registro de ocorrências |
| 18 | analytics | BI | Dashboards, relatórios |
| 19 | visao-ia | IA | Processamento de imagem |
| 20 | compliance | Jurídico | LGPD, regulamentos |
| 21 | voip | Telecom | Telefonia, interfones |
| 22 | infraestrutura | TI | Servidores, rede |
| 23 | suporte | Suporte | Help desk |
| 24 | comercial | Comercial | Vendas, marketing |

---

## Métricas e Monitoramento

### Métricas do Agente

```python
metrics = agente.get_metrics()
# {
#   "actions_executed": 150,
#   "predictions_made": 45,
#   "successful_actions": 148,
#   "failed_actions": 2,
#   "messages_sent": 30,
#   "messages_received": 25,
#   "learning_iterations": 100,
#   "success_rate": 0.987,
#   "capabilities_active": 12,
#   "collaborators_count": 3
# }
```

### Estado do Agente

```python
state = agente.get_state()
# AgentState(
#   agent_id="financeiro_condo_001",
#   agent_type="financeiro",
#   evolution_level=7,
#   is_active=True,
#   current_task=None,
#   pending_tasks=0,
#   performance_score=98.67,
#   error_count=2
# )
```

---

## Exemplo Completo

```python
import asyncio
from agents.core import (
    UnifiedLLMClient,
    UnifiedMemorySystem,
    create_rag_system,
)
from agents.core.tools import create_standard_tools
from agents.financeiro.agent_v2 import create_financial_agent
from agents.cftv.agent_v2 import create_cftv_agent

async def main():
    # Inicializar componentes
    llm = UnifiedLLMClient()
    memory = UnifiedMemorySystem(redis_url="redis://:pass@localhost:6379")
    tools = create_standard_tools(notification_url="http://notif:8000")

    # Criar agentes
    agente_fin = create_financial_agent(
        condominio_id="condo_001",
        llm_client=llm,
        memory=memory,
        tools=tools
    )

    agente_cftv = create_cftv_agent(
        condominio_id="condo_001",
        llm_client=llm,
        memory=memory,
        tools=tools
    )

    # Registrar colaboração
    agente_fin.register_collaborator(agente_cftv)
    agente_cftv.register_collaborator(agente_fin)

    # Iniciar agentes
    await agente_fin.start()
    await agente_cftv.start()

    # Processar requisição
    context = AgentContext(condominio_id="condo_001")

    # Consulta financeira
    result = await agente_fin.process(
        {"action": "consultar_saldo"},
        context
    )
    print(f"Saldo: {result}")

    # Análise de segurança
    result = await agente_cftv.process(
        {"action": "analise_cognitiva", "params": {"periodo": "24h"}},
        context
    )
    print(f"Análise: {result}")

    # Parar
    await agente_fin.stop()
    await agente_cftv.stop()

if __name__ == "__main__":
    asyncio.run(main())
```
