"""
AI Orchestrator - Orquestrador Central de Agentes
Conecta Plus - Plataforma de Gestão Condominial

Versão 2.0 - Integração com Framework de Evolução
"""

import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional, Callable, Type
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field

# Adicionar path para importar agentes
sys.path.insert(0, '/opt/conecta-plus')

try:
    from langchain_anthropic import ChatAnthropic
    from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
    HAS_LANGCHAIN = True
except ImportError:
    HAS_LANGCHAIN = False

# Importar framework de agentes
try:
    from agents.core import (
        BaseAgent,
        EvolutionLevel,
        AgentContext,
        UnifiedMemorySystem,
        UnifiedLLMClient,
        create_llm_client,
        # Message Bus para comunicação full-duplex
        MessageType,
        MessagePriority,
        BusMessage,
        AgentMessageBus,
        message_bus,
        StandardTopics,
    )
    from agents.core.tools import ToolRegistry, create_standard_tools
    HAS_AGENT_FRAMEWORK = True
except ImportError:
    HAS_AGENT_FRAMEWORK = False


class AgentPriority(Enum):
    """Prioridade de execução do agente"""
    CRITICAL = 1  # Segurança, emergências
    HIGH = 2      # Financeiro, acesso
    NORMAL = 3    # Operacional
    LOW = 4       # Relatórios, analytics


@dataclass
class AgentConfig:
    """Configuração de um agente"""
    name: str
    description: str
    priority: AgentPriority
    mcps: List[str]
    enabled: bool = True
    max_concurrent: int = 5


@dataclass
class TaskRequest:
    """Requisição de tarefa para o orquestrador"""
    id: str
    message: str
    context: Dict[str, Any] = field(default_factory=dict)
    user_id: Optional[str] = None
    condominio_id: Optional[str] = None
    priority: AgentPriority = AgentPriority.NORMAL
    target_agent: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class TaskResponse:
    """Resposta de uma tarefa"""
    request_id: str
    agent: str
    success: bool
    response: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    processing_time_ms: float = 0
    completed_at: datetime = field(default_factory=datetime.now)


class AIOrchestrator:
    """
    Orquestrador Central de Agentes do Conecta Plus

    Responsável por:
    - Roteamento inteligente de requisições para agentes apropriados
    - Coordenação de múltiplos agentes para tarefas complexas
    - Gerenciamento de contexto e sessão
    - Balanceamento de carga entre agentes
    - Monitoramento e logging
    """

    # Mapeamento de agentes e suas capacidades (36 agentes)
    AGENT_CAPABILITIES = {
        # ==================== SEGURANÇA (1-5) ====================
        "cftv": {
            "keywords": ["câmera", "camera", "dvr", "nvr", "gravação", "video", "imagem", "snapshot", "ptz", "monitoramento"],
            "intents": ["monitorar", "gravar", "visualizar", "detectar"],
            "priority": AgentPriority.HIGH,
            "description": "Agente de CFTV e monitoramento de vídeo",
        },
        "acesso": {
            "keywords": ["acesso", "entrada", "saída", "biometria", "digital", "cartão", "facial", "controladora", "catraca"],
            "intents": ["cadastrar", "liberar", "bloquear", "autorizar"],
            "priority": AgentPriority.HIGH,
            "description": "Agente de controle de acesso",
        },
        "automacao": {
            "keywords": ["portão", "gate", "motor", "controle remoto", "abertura", "fechamento", "cancela"],
            "intents": ["abrir", "fechar", "parar", "automatizar"],
            "priority": AgentPriority.HIGH,
            "description": "Agente de automação de portões e cancelas",
        },
        "alarme": {
            "keywords": ["alarme", "sensor", "zona", "partição", "armar", "desarmar", "pânico", "intrusão"],
            "intents": ["armar", "desarmar", "verificar", "disparar"],
            "priority": AgentPriority.CRITICAL,
            "description": "Agente de sistemas de alarme",
        },
        "rede": {
            "keywords": ["rede", "wifi", "internet", "roteador", "switch", "cliente", "conexão", "banda", "firewall"],
            "intents": ["conectar", "bloquear", "verificar", "configurar"],
            "priority": AgentPriority.NORMAL,
            "description": "Agente de infraestrutura de rede",
        },

        # ==================== PORTARIA E ATENDIMENTO (6-8) ====================
        "portaria_virtual": {
            "keywords": ["visitante", "portaria", "interfone", "atendimento", "autorização", "ronda", "qr code", "nc"],
            "intents": ["atender", "liberar", "negar", "comunicar", "registrar", "rondar"],
            "priority": AgentPriority.HIGH,
            "description": "Agente de portaria virtual com rondas e NCs",
        },
        "voip": {
            "keywords": ["telefone", "ramal", "ligação", "voip", "pbx", "chamada", "asterisk"],
            "intents": ["ligar", "transferir", "gravar", "atender"],
            "priority": AgentPriority.NORMAL,
            "description": "Agente de telefonia VoIP",
        },
        "atendimento": {
            "keywords": ["atendimento", "central", "omnichannel", "chat", "bot", "sac", "ouvidoria", "protocolo"],
            "intents": ["atender", "encaminhar", "resolver", "escalar"],
            "priority": AgentPriority.HIGH,
            "description": "Central de atendimento superinteligente omnichannel",
        },

        # ==================== RH E GESTÃO DE PESSOAS (9-10) ====================
        "rh": {
            "keywords": ["funcionário", "ponto", "folha", "férias", "salário", "contrato", "colaborador", "rh"],
            "intents": ["cadastrar", "calcular", "consultar", "aprovar"],
            "priority": AgentPriority.NORMAL,
            "description": "Agente de RH e gestão de funcionários",
        },
        "facilities": {
            "keywords": ["área comum", "limpeza", "manutenção predial", "jardim", "piscina", "zeladoria"],
            "intents": ["agendar", "verificar", "reportar", "limpar"],
            "priority": AgentPriority.LOW,
            "description": "Agente de facilities e zeladoria",
        },

        # ==================== MANUTENÇÃO (11-12) ====================
        "manutencao": {
            "keywords": ["manutenção", "reparo", "conserto", "ordem de serviço", "os", "preventiva", "corretiva"],
            "intents": ["solicitar", "acompanhar", "fechar", "programar"],
            "priority": AgentPriority.NORMAL,
            "description": "Agente de manutenção e ordens de serviço",
        },
        "infraestrutura": {
            "keywords": ["servidor", "banco de dados", "backup", "container", "sistema", "docker", "kubernetes"],
            "intents": ["monitorar", "reiniciar", "escalar", "backup"],
            "priority": AgentPriority.HIGH,
            "description": "Agente de infraestrutura de TI",
        },

        # ==================== GESTÃO CONDOMINIAL (13-16) ====================
        "sindico": {
            "keywords": ["síndico", "decisão", "aprovar", "comunicado", "assembleia", "gestão"],
            "intents": ["aprovar", "decidir", "comunicar", "gerenciar"],
            "priority": AgentPriority.HIGH,
            "description": "Agente assistente do síndico",
        },
        "financeiro": {
            "keywords": ["boleto", "pix", "pagamento", "cobrança", "inadimplência", "taxa", "financeiro", "receita", "despesa"],
            "intents": ["gerar", "cobrar", "consultar", "pagar", "provisionar"],
            "priority": AgentPriority.HIGH,
            "description": "Agente financeiro e de cobrança",
        },
        "assembleias": {
            "keywords": ["assembleia", "votação", "quórum", "ata", "convocação", "pauta", "deliberação"],
            "intents": ["convocar", "votar", "registrar", "apurar"],
            "priority": AgentPriority.NORMAL,
            "description": "Agente de assembleias e votações",
        },
        "reservas": {
            "keywords": ["reserva", "salão", "churrasqueira", "quadra", "disponibilidade", "agendamento"],
            "intents": ["reservar", "cancelar", "verificar", "confirmar"],
            "priority": AgentPriority.LOW,
            "description": "Agente de reservas de áreas comuns",
        },

        # ==================== MORADORES E COMUNICAÇÃO (17-19) ====================
        "morador": {
            "keywords": ["morador", "unidade", "apartamento", "casa", "proprietário", "inquilino", "condômino"],
            "intents": ["solicitar", "consultar", "autorizar", "cadastrar"],
            "priority": AgentPriority.NORMAL,
            "description": "Agente de gestão de moradores",
        },
        "comunicacao": {
            "keywords": ["comunicado", "aviso", "notificação", "mensagem", "whatsapp", "email", "push"],
            "intents": ["enviar", "notificar", "comunicar", "agendar"],
            "priority": AgentPriority.NORMAL,
            "description": "Agente de comunicação multicanal",
        },
        "encomendas": {
            "keywords": ["encomenda", "pacote", "entrega", "correio", "transportadora", "delivery"],
            "intents": ["registrar", "notificar", "retirar", "rastrear"],
            "priority": AgentPriority.LOW,
            "description": "Agente de gestão de encomendas",
        },

        # ==================== OCORRÊNCIAS E COMPLIANCE (20-22) ====================
        "ocorrencias": {
            "keywords": ["ocorrência", "reclamação", "barulho", "incidente", "problema", "denúncia"],
            "intents": ["registrar", "investigar", "resolver", "multar"],
            "priority": AgentPriority.NORMAL,
            "description": "Agente de ocorrências e reclamações",
        },
        "compliance": {
            "keywords": ["compliance", "lgpd", "conformidade", "certificado", "vencimento", "regulamento"],
            "intents": ["verificar", "auditar", "alertar", "renovar"],
            "priority": AgentPriority.NORMAL,
            "description": "Agente de compliance e conformidade",
        },
        "analytics": {
            "keywords": ["relatório", "indicador", "kpi", "dashboard", "estatística", "análise", "bi"],
            "intents": ["analisar", "gerar", "comparar", "prever"],
            "priority": AgentPriority.LOW,
            "description": "Agente de analytics e BI",
        },

        # ==================== IA E VISÃO COMPUTACIONAL (23-24) ====================
        "visao_ia": {
            "keywords": ["detecção", "reconhecimento", "placa", "face", "objeto", "ia", "visão", "lpr"],
            "intents": ["detectar", "reconhecer", "identificar", "classificar"],
            "priority": AgentPriority.NORMAL,
            "description": "Agente de visão computacional e IA",
        },
        "suporte": {
            "keywords": ["suporte", "ajuda", "ticket", "chamado", "problema técnico", "help desk"],
            "intents": ["ajudar", "resolver", "escalonar", "documentar"],
            "priority": AgentPriority.NORMAL,
            "description": "Agente de suporte técnico",
        },

        # ==================== NOVOS AGENTES (25-36) ====================
        "juridico": {
            "keywords": ["jurídico", "advogado", "processo", "notificação", "multa", "convenção", "regimento", "lei"],
            "intents": ["consultar", "notificar", "processar", "orientar"],
            "priority": AgentPriority.HIGH,
            "description": "Agente jurídico especializado em direito condominial",
        },
        "imobiliario": {
            "keywords": ["imóvel", "locação", "aluguel", "mudança", "vaga", "veículo", "contrato imobiliário"],
            "intents": ["cadastrar", "alugar", "transferir", "agendar"],
            "priority": AgentPriority.NORMAL,
            "description": "Agente imobiliário e gestão de unidades",
        },
        "sustentabilidade": {
            "keywords": ["sustentabilidade", "energia", "água", "solar", "reciclagem", "lixo", "esg", "carbono"],
            "intents": ["monitorar", "economizar", "reciclar", "reportar"],
            "priority": AgentPriority.LOW,
            "description": "Agente de sustentabilidade e eficiência energética",
        },
        "social": {
            "keywords": ["evento", "festa", "comunidade", "grupo", "marketplace", "classificados", "networking"],
            "intents": ["criar", "participar", "vender", "conectar"],
            "priority": AgentPriority.LOW,
            "description": "Agente social e de comunidade",
        },
        "pet": {
            "keywords": ["pet", "animal", "cachorro", "gato", "vacina", "passeio", "pet friendly"],
            "intents": ["cadastrar", "vacinar", "agendar", "reportar"],
            "priority": AgentPriority.LOW,
            "description": "Agente de gestão de pets",
        },
        "estacionamento": {
            "keywords": ["estacionamento", "vaga", "garagem", "veículo", "placa", "manobrista", "recarga elétrica"],
            "intents": ["reservar", "liberar", "multar", "recarregar"],
            "priority": AgentPriority.NORMAL,
            "description": "Agente de estacionamento e vagas",
        },
        "emergencia": {
            "keywords": ["emergência", "incêndio", "evacuação", "socorro", "ambulância", "bombeiro", "polícia"],
            "intents": ["alertar", "evacuar", "chamar", "protocolar"],
            "priority": AgentPriority.CRITICAL,
            "description": "Agente de emergências e protocolos de segurança",
        },
        "conhecimento": {
            "keywords": ["faq", "dúvida", "pergunta", "manual", "tutorial", "ajuda", "informação"],
            "intents": ["responder", "buscar", "explicar", "orientar"],
            "priority": AgentPriority.LOW,
            "description": "Agente de base de conhecimento e FAQ",
        },
        "auditoria": {
            "keywords": ["auditoria", "auditora", "fiscalização", "achado", "recomendação", "controle interno"],
            "intents": ["auditar", "fiscalizar", "recomendar", "verificar"],
            "priority": AgentPriority.NORMAL,
            "description": "Agente de auditoria interna",
        },
        "fornecedores": {
            "keywords": ["fornecedor", "compra", "cotação", "contrato", "prestador", "terceirizado"],
            "intents": ["cotar", "contratar", "avaliar", "pagar"],
            "priority": AgentPriority.NORMAL,
            "description": "Agente de gestão de fornecedores",
        },
        "valorizacao": {
            "keywords": ["valorização", "valor", "patrimônio", "melhoria", "investimento", "roi", "benchmark"],
            "intents": ["avaliar", "valorizar", "investir", "comparar"],
            "priority": AgentPriority.LOW,
            "description": "Agente de valorização patrimonial",
        },
        "comercial": {
            "keywords": ["venda", "lead", "proposta", "demo", "cliente", "contrato comercial"],
            "intents": ["prospectar", "negociar", "fechar", "demonstrar"],
            "priority": AgentPriority.LOW,
            "description": "Agente comercial e vendas",
        },
    }

    def __init__(
        self,
        model: str = "claude-3-5-sonnet-20241022",
        max_retries: int = 3,
    ):
        self.model = model
        self.max_retries = max_retries
        self.logger = logging.getLogger("orchestrator")
        self.active_tasks: Dict[str, TaskRequest] = {}
        self.task_history: List[TaskResponse] = []

        # LLM para roteamento inteligente
        self.router_llm = ChatAnthropic(
            model=model,
            temperature=0,
            max_tokens=500,
        )

        # Callbacks para eventos
        self.callbacks: Dict[str, List[Callable]] = {
            "task_started": [],
            "task_completed": [],
            "task_failed": [],
            "agent_selected": [],
        }

    async def route_request(self, request: TaskRequest) -> str:
        """
        Determina qual agente deve processar a requisição
        Usa análise de keywords + LLM para casos ambíguos
        """

        # Se agente específico foi solicitado
        if request.target_agent:
            if request.target_agent in self.AGENT_CAPABILITIES:
                return request.target_agent
            self.logger.warning(f"Agente '{request.target_agent}' não existe")

        # Análise por keywords
        message_lower = request.message.lower()
        scores: Dict[str, int] = {}

        for agent, config in self.AGENT_CAPABILITIES.items():
            score = 0
            for keyword in config["keywords"]:
                if keyword in message_lower:
                    score += 2
            for intent in config["intents"]:
                if intent in message_lower:
                    score += 1
            if score > 0:
                scores[agent] = score

        # Se houver match claro (score > 3), usa diretamente
        if scores:
            best_agent = max(scores, key=scores.get)
            if scores[best_agent] >= 3:
                self.logger.info(f"Roteamento por keyword: {best_agent} (score: {scores[best_agent]})")
                return best_agent

        # Casos ambíguos: usa LLM para decidir
        return await self._llm_route(request, scores)

    async def _llm_route(
        self,
        request: TaskRequest,
        keyword_scores: Dict[str, int],
    ) -> str:
        """Usa LLM para rotear requisições ambíguas"""

        agents_list = "\n".join([
            f"- {name}: {config['keywords'][:5]}"
            for name, config in self.AGENT_CAPABILITIES.items()
        ])

        top_candidates = sorted(
            keyword_scores.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:3] if keyword_scores else []

        prompt = f"""Analise a seguinte mensagem e determine qual agente do sistema deve processá-la.

Mensagem: "{request.message}"

Agentes disponíveis:
{agents_list}

{f"Candidatos prováveis baseado em keywords: {top_candidates}" if top_candidates else ""}

Responda APENAS com o nome do agente mais apropriado (ex: "cftv", "financeiro", "morador").
Se nenhum agente for apropriado, responda "suporte"."""

        try:
            response = await self.router_llm.ainvoke([HumanMessage(content=prompt)])
            agent = response.content.strip().lower().replace('"', '').replace("'", "")

            if agent in self.AGENT_CAPABILITIES:
                self.logger.info(f"Roteamento por LLM: {agent}")
                return agent

        except Exception as e:
            self.logger.error(f"Erro no roteamento LLM: {e}")

        # Fallback para suporte
        return "suporte"

    async def process_request(self, request: TaskRequest) -> TaskResponse:
        """Processa uma requisição através do agente apropriado"""

        start_time = datetime.now()
        self.active_tasks[request.id] = request

        try:
            # 1. Rotear para agente apropriado
            agent_name = await self.route_request(request)
            await self._emit_event("agent_selected", request, agent_name)

            # 2. Carregar e executar agente
            agent = await self._load_agent(agent_name)

            await self._emit_event("task_started", request, agent_name)

            # 3. Processar mensagem
            result = await agent.process_message(
                message=request.message,
                context={
                    **request.context,
                    "user_id": request.user_id,
                    "condominio_id": request.condominio_id,
                },
            )

            # 4. Criar resposta
            processing_time = (datetime.now() - start_time).total_seconds() * 1000

            response = TaskResponse(
                request_id=request.id,
                agent=agent_name,
                success=result.get("success", False),
                response=result.get("response", ""),
                metadata=result,
                processing_time_ms=processing_time,
            )

            await self._emit_event("task_completed", request, response)
            self.task_history.append(response)

            return response

        except Exception as e:
            self.logger.error(f"Erro ao processar requisição {request.id}: {e}")

            response = TaskResponse(
                request_id=request.id,
                agent="orchestrator",
                success=False,
                response=f"Erro ao processar requisição: {str(e)}",
                processing_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
            )

            await self._emit_event("task_failed", request, str(e))
            return response

        finally:
            del self.active_tasks[request.id]

    async def _load_agent(self, agent_name: str):
        """Carrega dinamicamente um agente"""
        # Import dinâmico dos agentes
        module_path = f"agents.{agent_name.replace('_', '-')}.agent"
        try:
            module = __import__(module_path, fromlist=[f"agente_{agent_name}"])
            return getattr(module, f"agente_{agent_name}")
        except (ImportError, AttributeError) as e:
            self.logger.error(f"Erro ao carregar agente {agent_name}: {e}")
            # Retorna agente genérico de suporte
            from agents.suporte.agent import agente_suporte
            return agente_suporte

    async def process_multi_agent(
        self,
        request: TaskRequest,
        agents: List[str],
    ) -> List[TaskResponse]:
        """Processa uma requisição através de múltiplos agentes"""

        tasks = []
        for agent in agents:
            sub_request = TaskRequest(
                id=f"{request.id}_{agent}",
                message=request.message,
                context=request.context,
                user_id=request.user_id,
                condominio_id=request.condominio_id,
                target_agent=agent,
            )
            tasks.append(self.process_request(sub_request))

        return await asyncio.gather(*tasks)

    def on(self, event: str, callback: Callable):
        """Registra callback para evento"""
        if event in self.callbacks:
            self.callbacks[event].append(callback)

    async def _emit_event(self, event: str, *args):
        """Emite evento para callbacks registrados"""
        for callback in self.callbacks.get(event, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(*args)
                else:
                    callback(*args)
            except Exception as e:
                self.logger.error(f"Erro em callback {event}: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Retorna status do orquestrador"""
        return {
            "active_tasks": len(self.active_tasks),
            "total_processed": len(self.task_history),
            "agents_available": list(self.AGENT_CAPABILITIES.keys()),
            "model": self.model,
        }


# ==================== ORCHESTRATOR V2 ====================

class AgentRegistration:
    """Registro de agente no orchestrator V2"""

    def __init__(
        self,
        agent_id: str,
        agent_type: str,
        condominio_id: str,
        evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT,
    ):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.condominio_id = condominio_id
        self.evolution_level = evolution_level
        self.instance: Optional[BaseAgent] = None
        self.status = "stopped"
        self.created_at = datetime.now()
        self.last_activity = None
        self.request_count = 0
        self.error_count = 0


class AIOrchestrator2:
    """
    AI Orchestrator V2 - Integrado com Framework de Evolução

    Nova versão que usa o sistema de agentes avançados com:
    - 7 níveis de evolução
    - Memória persistente
    - Colaboração entre agentes
    - RAG integrado
    - 36 agentes especializados
    """

    # Mapeamento de todos os 36 agentes com suas factories
    AGENT_FACTORIES = {
        # ==================== SEGURANÇA (1-5) ====================
        "cftv": "agents.cftv:create_cftv_agent",
        "acesso": "agents.acesso:create_access_agent",
        "automacao": "agents.automacao:create_automation_agent",
        "alarme": "agents.alarme:create_alarm_agent",
        "rede": "agents.rede:create_network_agent",

        # ==================== PORTARIA E ATENDIMENTO (6-8) ====================
        "portaria_virtual": "agents.portaria-virtual:create_virtual_doorman_agent",
        "voip": "agents.voip:create_voip_agent",
        "atendimento": "agents.atendimento:create_service_center_agent",

        # ==================== RH E GESTÃO DE PESSOAS (9-10) ====================
        "rh": "agents.rh:create_hr_agent",
        "facilities": "agents.facilities:create_facilities_agent",

        # ==================== MANUTENÇÃO (11-12) ====================
        "manutencao": "agents.manutencao:create_maintenance_agent",
        "infraestrutura": "agents.infraestrutura:create_infrastructure_agent",

        # ==================== GESTÃO CONDOMINIAL (13-16) ====================
        "sindico": "agents.sindico:create_sindico_agent",
        "financeiro": "agents.financeiro:create_financial_agent",
        "assembleias": "agents.assembleias:create_assembly_agent",
        "reservas": "agents.reservas:create_reservation_agent",

        # ==================== MORADORES E COMUNICAÇÃO (17-19) ====================
        "morador": "agents.morador:create_resident_agent",
        "comunicacao": "agents.comunicacao:create_communication_agent",
        "encomendas": "agents.encomendas:create_delivery_agent",

        # ==================== OCORRÊNCIAS E COMPLIANCE (20-22) ====================
        "ocorrencias": "agents.ocorrencias:create_incident_agent",
        "compliance": "agents.compliance:create_compliance_agent",
        "analytics": "agents.analytics:create_analytics_agent",

        # ==================== IA E SUPORTE (23-24) ====================
        "visao_ia": "agents.visao-ia:create_vision_agent",
        "suporte": "agents.suporte:create_support_agent",

        # ==================== NOVOS AGENTES (25-36) ====================
        "juridico": "agents.juridico:create_legal_agent",
        "imobiliario": "agents.imobiliario:create_real_estate_agent",
        "sustentabilidade": "agents.sustentabilidade:create_sustainability_agent",
        "social": "agents.social:create_social_agent",
        "pet": "agents.pet:create_pet_agent",
        "estacionamento": "agents.estacionamento:create_parking_agent",
        "emergencia": "agents.emergencia:create_emergency_agent",
        "conhecimento": "agents.conhecimento:create_knowledge_agent",
        "auditoria": "agents.auditoria:create_audit_agent",
        "fornecedores": "agents.fornecedores:create_supplier_agent",
        "valorizacao": "agents.valorizacao:create_property_value_agent",
        "comercial": "agents.comercial:create_commercial_agent",
    }

    # Descrição dos agentes para documentação
    AGENT_DESCRIPTIONS = {
        "cftv": "Monitoramento de vídeo e CFTV",
        "acesso": "Controle de acesso biométrico e facial",
        "automacao": "Automação de portões e cancelas",
        "alarme": "Sistemas de alarme e sensores",
        "rede": "Infraestrutura de rede WiFi",
        "portaria_virtual": "Portaria virtual com rondas e NCs",
        "voip": "Telefonia VoIP e PBX",
        "atendimento": "Central omnichannel superinteligente",
        "rh": "Gestão de RH e funcionários",
        "facilities": "Facilities e zeladoria",
        "manutencao": "Manutenção e ordens de serviço",
        "infraestrutura": "Infraestrutura de TI",
        "sindico": "Assistente do síndico",
        "financeiro": "Gestão financeira e cobrança",
        "assembleias": "Assembleias e votações",
        "reservas": "Reservas de áreas comuns",
        "morador": "Gestão de moradores",
        "comunicacao": "Comunicação multicanal",
        "encomendas": "Gestão de encomendas",
        "ocorrencias": "Ocorrências e reclamações",
        "compliance": "Compliance e LGPD",
        "analytics": "Analytics e BI",
        "visao_ia": "Visão computacional e IA",
        "suporte": "Suporte técnico",
        "juridico": "Consultoria jurídica condominial",
        "imobiliario": "Gestão imobiliária e locações",
        "sustentabilidade": "Sustentabilidade e ESG",
        "social": "Comunidade e eventos",
        "pet": "Gestão de pets",
        "estacionamento": "Estacionamento e vagas",
        "emergencia": "Emergências e protocolos",
        "conhecimento": "Base de conhecimento e FAQ",
        "auditoria": "Auditoria interna",
        "fornecedores": "Gestão de fornecedores",
        "valorizacao": "Valorização patrimonial",
        "comercial": "Comercial e vendas",
    }

    def __init__(
        self,
        redis_url: str = None,
        llm_provider: str = "auto",
        default_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT,
    ):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "")
        self.llm_provider = llm_provider
        self.default_level = default_level
        self.logger = logging.getLogger("orchestrator_v2")

        self._agents: Dict[str, AgentRegistration] = {}
        self._condominios: Dict[str, List[str]] = {}
        self._is_running = False

        # Componentes compartilhados
        self._llm_client: Optional[UnifiedLLMClient] = None
        self._memory: Optional[UnifiedMemorySystem] = None
        self._tools: Optional[ToolRegistry] = None

        # Fallback para V1
        self._v1_orchestrator = AIOrchestrator() if HAS_LANGCHAIN else None

        # Message Bus para comunicação full-duplex entre agentes
        self._message_bus = message_bus if HAS_AGENT_FRAMEWORK else None

        # Métricas
        self._metrics = {
            "total_requests": 0,
            "successful": 0,
            "failed": 0,
            "agents_created": 0,
            "messages_routed": 0,
            "broadcasts_sent": 0,
        }

    async def start(self):
        """Inicia o orchestrator"""
        self.logger.info("Iniciando AI Orchestrator V2...")

        if HAS_AGENT_FRAMEWORK:
            # Inicializar LLM
            self._llm_client = create_llm_client(provider=self.llm_provider)

            # Inicializar Memory
            if self.redis_url:
                self._memory = UnifiedMemorySystem(
                    redis_url=self.redis_url,
                    vector_persist_dir="/opt/conecta-plus/data/vector_db"
                )

            # Inicializar Tools
            self._tools = create_standard_tools(
                notification_url=os.getenv("NOTIFICATION_SERVICE_URL"),
                integration_hub_url=os.getenv("INTEGRATION_HUB_URL")
            )

            # Inicializar Message Bus para comunicação full-duplex
            if self._message_bus:
                await self._message_bus.start()
                # Registrar o próprio orchestrator no bus
                self._orchestrator_queue = self._message_bus.register_agent(
                    agent_id="orchestrator",
                    agent_type="orchestrator",
                    condominio_id="*",  # Global
                    subscriptions=[StandardTopics.SYSTEM_STATUS, StandardTopics.EMERGENCY_ALERT]
                )
                self.logger.info("Message Bus inicializado - comunicação full-duplex ativa")

        self._is_running = True
        self.logger.info("AI Orchestrator V2 iniciado com suporte a 36 agentes")

    async def stop(self):
        """Para o orchestrator"""
        self._is_running = False

        # Parar Message Bus
        if self._message_bus:
            await self._message_bus.stop()

        for agent_id in list(self._agents.keys()):
            await self.destroy_agent(agent_id)
        self.logger.info("AI Orchestrator V2 parado")

    async def get_or_create_agent(
        self,
        agent_type: str,
        condominio_id: str,
        evolution_level: EvolutionLevel = None
    ) -> BaseAgent:
        """Obtém ou cria agente"""
        agent_id = f"{agent_type}_{condominio_id}"

        if agent_id in self._agents and self._agents[agent_id].instance:
            return self._agents[agent_id].instance

        return await self.create_agent(agent_type, condominio_id, evolution_level)

    async def create_agent(
        self,
        agent_type: str,
        condominio_id: str,
        evolution_level: EvolutionLevel = None
    ) -> BaseAgent:
        """Cria novo agente - suporta todos os 36 tipos"""
        if not HAS_AGENT_FRAMEWORK:
            raise RuntimeError("Framework de agentes não disponível")

        agent_id = f"{agent_type}_{condominio_id}"
        level = evolution_level or self.default_level

        # Verificar se o tipo de agente é suportado
        if agent_type not in self.AGENT_FACTORIES:
            raise ValueError(f"Tipo de agente '{agent_type}' não suportado. Tipos disponíveis: {list(self.AGENT_FACTORIES.keys())}")

        # Obter factory do mapeamento
        factory_path = self.AGENT_FACTORIES[agent_type]
        module_path, factory_name = factory_path.rsplit(":", 1)

        # Importar dinamicamente o módulo e factory
        try:
            # Converter path para formato de import (ex: agents.portaria-virtual -> agents.portaria_virtual)
            import_path = module_path.replace("-", "_")
            module = __import__(import_path, fromlist=[factory_name])
            factory_func = getattr(module, factory_name)

            # Criar instância do agente
            instance = factory_func(
                memory=self._memory,
                llm_client=self._llm_client,
                tools=self._tools,
            )

            self.logger.info(f"Agente {agent_type} criado via factory dinâmica")

        except ImportError as e:
            self.logger.warning(f"Não foi possível importar {module_path}: {e}. Tentando import alternativo...")

            # Fallback para imports específicos (agentes já implementados)
            instance = await self._create_agent_fallback(agent_type, condominio_id, level)

            if instance is None:
                raise ValueError(f"Não foi possível criar agente '{agent_type}': {e}")

        # Registrar
        registration = AgentRegistration(
            agent_id=agent_id,
            agent_type=agent_type,
            condominio_id=condominio_id,
            evolution_level=level
        )
        registration.instance = instance
        registration.status = "running"

        self._agents[agent_id] = registration

        if condominio_id not in self._condominios:
            self._condominios[condominio_id] = []
        self._condominios[condominio_id].append(agent_id)

        await instance.start()
        self._metrics["agents_created"] += 1

        self.logger.info(f"Agente {agent_id} criado (nível {level.name})")
        return instance

    async def _create_agent_fallback(
        self,
        agent_type: str,
        condominio_id: str,
        level: EvolutionLevel
    ) -> Optional[BaseAgent]:
        """Fallback para criação de agentes com imports específicos"""

        try:
            # Novos agentes V2 (25-36)
            if agent_type == "juridico":
                from agents.juridico import create_legal_agent
                return create_legal_agent(self._memory, self._llm_client, self._tools)

            elif agent_type == "imobiliario":
                from agents.imobiliario import create_real_estate_agent
                return create_real_estate_agent(self._memory, self._llm_client, self._tools)

            elif agent_type == "sustentabilidade":
                from agents.sustentabilidade import create_sustainability_agent
                return create_sustainability_agent(self._memory, self._llm_client, self._tools)

            elif agent_type == "social":
                from agents.social import create_social_agent
                return create_social_agent(self._memory, self._llm_client, self._tools)

            elif agent_type == "pet":
                from agents.pet import create_pet_agent
                return create_pet_agent(self._memory, self._llm_client, self._tools)

            elif agent_type == "estacionamento":
                from agents.estacionamento import create_parking_agent
                return create_parking_agent(self._memory, self._llm_client, self._tools)

            elif agent_type == "emergencia":
                from agents.emergencia import create_emergency_agent
                return create_emergency_agent(self._memory, self._llm_client, self._tools)

            elif agent_type == "conhecimento":
                from agents.conhecimento import create_knowledge_agent
                return create_knowledge_agent(self._memory, self._llm_client, self._tools)

            elif agent_type == "auditoria":
                from agents.auditoria import create_audit_agent
                return create_audit_agent(self._memory, self._llm_client, self._tools)

            elif agent_type == "fornecedores":
                from agents.fornecedores import create_supplier_agent
                return create_supplier_agent(self._memory, self._llm_client, self._tools)

            elif agent_type == "valorizacao":
                from agents.valorizacao import create_property_value_agent
                return create_property_value_agent(self._memory, self._llm_client, self._tools)

            elif agent_type == "atendimento":
                from agents.atendimento import create_service_center_agent
                return create_service_center_agent(self._memory, self._llm_client, self._tools)

            # Agentes originais (1-24)
            elif agent_type == "portaria_virtual":
                from agents.portaria_virtual import create_virtual_doorman_agent
                return create_virtual_doorman_agent(self._memory, self._llm_client, self._tools)

            elif agent_type == "financeiro":
                from agents.financeiro import create_financial_agent
                return create_financial_agent(self._memory, self._llm_client, self._tools)

            elif agent_type == "cftv":
                from agents.cftv import create_cftv_agent
                return create_cftv_agent(self._memory, self._llm_client, self._tools)

            elif agent_type == "acesso":
                from agents.acesso import create_access_agent
                return create_access_agent(self._memory, self._llm_client, self._tools)

            elif agent_type == "sindico":
                from agents.sindico import create_sindico_agent
                return create_sindico_agent(self._memory, self._llm_client, self._tools)

            elif agent_type == "manutencao":
                from agents.manutencao import create_maintenance_agent
                return create_maintenance_agent(self._memory, self._llm_client, self._tools)

            elif agent_type == "reservas":
                from agents.reservas import create_reservation_agent
                return create_reservation_agent(self._memory, self._llm_client, self._tools)

            elif agent_type == "encomendas":
                from agents.encomendas import create_delivery_agent
                return create_delivery_agent(self._memory, self._llm_client, self._tools)

            elif agent_type == "ocorrencias":
                from agents.ocorrencias import create_incident_agent
                return create_incident_agent(self._memory, self._llm_client, self._tools)

            elif agent_type == "analytics":
                from agents.analytics import create_analytics_agent
                return create_analytics_agent(self._memory, self._llm_client, self._tools)

            elif agent_type == "compliance":
                from agents.compliance import create_compliance_agent
                return create_compliance_agent(self._memory, self._llm_client, self._tools)

            elif agent_type == "comunicacao":
                from agents.comunicacao import create_communication_agent
                return create_communication_agent(self._memory, self._llm_client, self._tools)

            elif agent_type == "assembleias":
                from agents.assembleias import create_assembly_agent
                return create_assembly_agent(self._memory, self._llm_client, self._tools)

            # Restante dos agentes originais
            elif agent_type == "automacao":
                from agents.automacao import create_automation_agent
                return create_automation_agent(self._memory, self._llm_client, self._tools)

            elif agent_type == "alarme":
                from agents.alarme import create_alarm_agent
                return create_alarm_agent(self._memory, self._llm_client, self._tools)

            elif agent_type == "rede":
                from agents.rede import create_network_agent
                return create_network_agent(self._memory, self._llm_client, self._tools)

            elif agent_type == "voip":
                from agents.voip import create_voip_agent
                return create_voip_agent(self._memory, self._llm_client, self._tools)

            elif agent_type == "rh":
                from agents.rh import create_hr_agent
                return create_hr_agent(self._memory, self._llm_client, self._tools)

            elif agent_type == "facilities":
                from agents.facilities import create_facilities_agent
                return create_facilities_agent(self._memory, self._llm_client, self._tools)

            elif agent_type == "infraestrutura":
                from agents.infraestrutura import create_infrastructure_agent
                return create_infrastructure_agent(self._memory, self._llm_client, self._tools)

            elif agent_type == "morador":
                from agents.morador import create_resident_agent
                return create_resident_agent(self._memory, self._llm_client, self._tools)

            elif agent_type == "visao_ia":
                from agents.visao_ia import create_vision_agent
                return create_vision_agent(self._memory, self._llm_client, self._tools)

            elif agent_type == "suporte":
                from agents.suporte import create_support_agent
                return create_support_agent(self._memory, self._llm_client, self._tools)

            elif agent_type == "comercial":
                from agents.comercial import create_commercial_agent
                return create_commercial_agent(self._memory, self._llm_client, self._tools)

        except Exception as e:
            self.logger.error(f"Erro no fallback para {agent_type}: {e}")

        return None

    def get_supported_agents(self) -> Dict[str, str]:
        """Retorna lista de agentes suportados com descrições"""
        return self.AGENT_DESCRIPTIONS.copy()

    def get_agent_count(self) -> int:
        """Retorna número total de tipos de agentes suportados"""
        return len(self.AGENT_FACTORIES)

    async def destroy_agent(self, agent_id: str) -> bool:
        """Destrói agente"""
        if agent_id not in self._agents:
            return False

        reg = self._agents[agent_id]
        if reg.instance:
            await reg.instance.stop()

        del self._agents[agent_id]
        if reg.condominio_id in self._condominios:
            self._condominios[reg.condominio_id].remove(agent_id)

        return True

    async def process_request(
        self,
        condominio_id: str,
        agent_type: str,
        action: str,
        params: Dict[str, Any] = None,
        user_id: str = None,
        session_id: str = None
    ) -> Dict[str, Any]:
        """Processa requisição via agente V2"""
        self._metrics["total_requests"] += 1

        try:
            agent = await self.get_or_create_agent(agent_type, condominio_id)

            context = AgentContext(
                condominio_id=condominio_id,
                user_id=user_id,
                session_id=session_id
            )

            result = await agent.process(
                input_data={"action": action, "params": params or {}},
                context=context
            )

            # Atualizar registro
            if f"{agent_type}_{condominio_id}" in self._agents:
                reg = self._agents[f"{agent_type}_{condominio_id}"]
                reg.last_activity = datetime.now()
                reg.request_count += 1

            self._metrics["successful"] += 1
            return result

        except Exception as e:
            self._metrics["failed"] += 1
            self.logger.error(f"Erro ao processar: {e}")
            return {"error": str(e)}

    async def smart_route(
        self,
        condominio_id: str,
        message: str,
        user_id: str = None
    ) -> Dict[str, Any]:
        """Roteamento inteligente - determina melhor agente entre os 36 disponíveis"""

        # Determinar agente usando V1 (keyword matching + LLM)
        if self._v1_orchestrator:
            request = TaskRequest(
                id=f"route_{datetime.now().timestamp()}",
                message=message,
                condominio_id=condominio_id,
                user_id=user_id
            )
            agent_type = await self._v1_orchestrator.route_request(request)
        else:
            # Fallback: análise simples de keywords
            agent_type = self._simple_route(message)

        self.logger.info(f"Smart route selecionou agente: {agent_type}")

        # Processar com V2 se disponível
        if HAS_AGENT_FRAMEWORK and agent_type in self.AGENT_FACTORIES:
            return await self.process_request(
                condominio_id=condominio_id,
                agent_type=agent_type,
                action="chat",
                params={"message": message},
                user_id=user_id
            )

        # Fallback para V1
        if self._v1_orchestrator:
            response = await self._v1_orchestrator.process_request(request)
            return {
                "success": response.success,
                "response": response.response,
                "agent": response.agent
            }

        return {"error": "Nenhum orchestrator disponível"}

    def _simple_route(self, message: str) -> str:
        """Roteamento simples por keywords quando V1 não está disponível"""
        message_lower = message.lower()

        # Mapeamento de keywords para agentes
        routing_map = {
            "emergencia": ["emergência", "incêndio", "socorro", "urgente", "ambulância"],
            "alarme": ["alarme", "sensor", "disparou", "armar", "desarmar"],
            "portaria_virtual": ["visitante", "portaria", "interfone", "ronda"],
            "financeiro": ["boleto", "pagamento", "cobrança", "inadimplência", "2a via"],
            "manutencao": ["manutenção", "conserto", "reparo", "vazamento", "quebrado"],
            "reservas": ["reserva", "agendar", "salão", "churrasqueira", "quadra"],
            "encomendas": ["encomenda", "pacote", "entrega", "correio"],
            "ocorrencias": ["reclamação", "barulho", "ocorrência", "vizinho"],
            "juridico": ["jurídico", "advogado", "processo", "notificação", "convenção"],
            "estacionamento": ["estacionamento", "vaga", "garagem", "veículo"],
            "pet": ["pet", "cachorro", "gato", "animal"],
            "assembleias": ["assembleia", "votação", "quórum", "ata"],
            "conhecimento": ["dúvida", "faq", "como funciona", "ajuda"],
            "atendimento": ["atendimento", "falar com", "central"],
        }

        for agent, keywords in routing_map.items():
            if any(kw in message_lower for kw in keywords):
                return agent

        # Default: atendimento (central omnichannel)
        return "atendimento"

    def get_status(self) -> Dict[str, Any]:
        """Status do orchestrator com 36 agentes"""
        return {
            "version": "2.0",
            "is_running": self._is_running,
            "has_agent_framework": HAS_AGENT_FRAMEWORK,
            "has_langchain": HAS_LANGCHAIN,
            "total_agent_types": len(self.AGENT_FACTORIES),
            "active_instances": len(self._agents),
            "condominios": len(self._condominios),
            "metrics": self._metrics,
            "supported_agents": {
                "total": len(self.AGENT_FACTORIES),
                "categories": {
                    "seguranca": ["cftv", "acesso", "automacao", "alarme", "rede"],
                    "portaria_atendimento": ["portaria_virtual", "voip", "atendimento"],
                    "rh_pessoas": ["rh", "facilities"],
                    "manutencao": ["manutencao", "infraestrutura"],
                    "gestao_condominial": ["sindico", "financeiro", "assembleias", "reservas"],
                    "moradores_comunicacao": ["morador", "comunicacao", "encomendas"],
                    "ocorrencias_compliance": ["ocorrencias", "compliance", "analytics"],
                    "ia_suporte": ["visao_ia", "suporte"],
                    "novos_agentes": ["juridico", "imobiliario", "sustentabilidade", "social", "pet",
                                     "estacionamento", "emergencia", "conhecimento", "auditoria",
                                     "fornecedores", "valorizacao", "comercial"]
                },
                "descriptions": self.AGENT_DESCRIPTIONS
            },
            "active_agents_list": [
                {
                    "id": reg.agent_id,
                    "type": reg.agent_type,
                    "description": self.AGENT_DESCRIPTIONS.get(reg.agent_type, ""),
                    "level": reg.evolution_level.name if reg.evolution_level else "N/A",
                    "status": reg.status,
                    "requests": reg.request_count,
                    "last_activity": reg.last_activity.isoformat() if reg.last_activity else None
                }
                for reg in self._agents.values()
            ]
        }

    def list_agents(self, condominio_id: str = None) -> List[Dict[str, Any]]:
        """Lista agentes"""
        agents = []
        for reg in self._agents.values():
            if condominio_id and reg.condominio_id != condominio_id:
                continue
            agents.append({
                "agent_id": reg.agent_id,
                "agent_type": reg.agent_type,
                "condominio_id": reg.condominio_id,
                "evolution_level": reg.evolution_level.name if reg.evolution_level else None,
                "status": reg.status,
                "request_count": reg.request_count
            })
        return agents

    # ==================== COMUNICAÇÃO FULL-DUPLEX ====================

    async def send_message_to_agent(
        self,
        sender_id: str,
        receiver_id: str,
        content: Any,
        message_type: str = "direct",
        priority: str = "normal",
        metadata: Dict[str, Any] = None,
    ) -> bool:
        """
        Envia mensagem de um agente para outro via Message Bus.
        Comunicação full-duplex entre qualquer par de agentes.
        """
        if not self._message_bus:
            self.logger.warning("Message Bus não disponível")
            return False

        msg_type = MessageType(message_type) if isinstance(message_type, str) else message_type
        msg_priority = MessagePriority[priority.upper()] if isinstance(priority, str) else priority

        result = await self._message_bus.send(
            sender_id=sender_id,
            receiver_id=receiver_id,
            content=content,
            message_type=msg_type,
            priority=msg_priority,
            metadata=metadata,
        )

        if result:
            self._metrics["messages_routed"] += 1

        return result

    async def broadcast_to_agents(
        self,
        sender_id: str,
        content: Any,
        condominio_id: str = None,
        exclude_sender: bool = True,
        priority: str = "normal",
        metadata: Dict[str, Any] = None,
    ) -> int:
        """
        Envia mensagem broadcast para todos os agentes (ou de um condomínio).
        Retorna número de agentes que receberam.
        """
        if not self._message_bus:
            self.logger.warning("Message Bus não disponível")
            return 0

        msg_priority = MessagePriority[priority.upper()] if isinstance(priority, str) else priority

        delivered = await self._message_bus.broadcast(
            sender_id=sender_id,
            content=content,
            priority=msg_priority,
            exclude_sender=exclude_sender,
            condominio_id=condominio_id,
            metadata=metadata,
        )

        self._metrics["broadcasts_sent"] += 1
        return delivered

    async def request_response(
        self,
        sender_id: str,
        receiver_id: str,
        content: Any,
        timeout: float = 30.0,
        metadata: Dict[str, Any] = None,
    ) -> Optional[Any]:
        """
        Envia requisição e aguarda resposta (padrão request/response).
        Útil para consultas síncronas entre agentes.
        """
        if not self._message_bus:
            return None

        return await self._message_bus.request(
            sender_id=sender_id,
            receiver_id=receiver_id,
            content=content,
            timeout=timeout,
            metadata=metadata,
        )

    async def publish_event(
        self,
        sender_id: str,
        topic: str,
        content: Any,
        priority: str = "normal",
        metadata: Dict[str, Any] = None,
    ) -> int:
        """
        Publica evento em um tópico para todos os inscritos.
        Padrão publish/subscribe para eventos do sistema.
        """
        if not self._message_bus:
            return 0

        msg_priority = MessagePriority[priority.upper()] if isinstance(priority, str) else priority

        return await self._message_bus.publish(
            sender_id=sender_id,
            topic=topic,
            content=content,
            priority=msg_priority,
            metadata=metadata,
        )

    def subscribe_agent_to_topic(self, agent_id: str, topic: str) -> bool:
        """Inscreve agente em um tópico de eventos"""
        if not self._message_bus:
            return False
        return self._message_bus.subscribe(agent_id, topic)

    def unsubscribe_agent_from_topic(self, agent_id: str, topic: str) -> bool:
        """Remove inscrição de agente em um tópico"""
        if not self._message_bus:
            return False
        return self._message_bus.unsubscribe(agent_id, topic)

    def get_message_bus_status(self) -> Dict[str, Any]:
        """Retorna status do Message Bus"""
        if not self._message_bus:
            return {"available": False}
        return {
            "available": True,
            **self._message_bus.get_status()
        }

    def get_agents_by_type(self, agent_type: str) -> List[str]:
        """Retorna IDs de agentes de um tipo específico"""
        if not self._message_bus:
            return []
        return self._message_bus.get_agents_by_type(agent_type)

    def get_agents_in_condominio(self, condominio_id: str) -> List[str]:
        """Retorna IDs de agentes de um condomínio específico"""
        if not self._message_bus:
            return []
        return self._message_bus.get_agents_by_condominio(condominio_id)


# Instância global do orquestrador V1 (compatibilidade)
orchestrator = AIOrchestrator() if HAS_LANGCHAIN else None

# Instância global do orquestrador V2
orchestrator_v2 = AIOrchestrator2()


# API FastAPI para o orquestrador
async def create_api():
    """Cria API FastAPI para o orquestrador"""
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel

    app = FastAPI(
        title="Conecta Plus AI Orchestrator",
        description="API do Orquestrador de Agentes de IA",
        version="1.0.0",
    )

    class RequestInput(BaseModel):
        message: str
        context: Dict[str, Any] = {}
        user_id: Optional[str] = None
        condominio_id: Optional[str] = None
        target_agent: Optional[str] = None

    @app.post("/process")
    async def process(input: RequestInput):
        import uuid
        request = TaskRequest(
            id=str(uuid.uuid4()),
            message=input.message,
            context=input.context,
            user_id=input.user_id,
            condominio_id=input.condominio_id,
            target_agent=input.target_agent,
        )
        response = await orchestrator.process_request(request)
        return response.__dict__

    @app.get("/status")
    async def status():
        return orchestrator.get_status()

    @app.get("/agents")
    async def list_agents():
        return list(orchestrator.AGENT_CAPABILITIES.keys()) if orchestrator else []

    # ==================== ENDPOINTS V2 ====================

    @app.on_event("startup")
    async def startup():
        await orchestrator_v2.start()

    @app.on_event("shutdown")
    async def shutdown():
        await orchestrator_v2.stop()

    class V2RequestInput(BaseModel):
        condominio_id: str
        agent_type: str
        action: str
        params: Dict[str, Any] = {}
        user_id: Optional[str] = None
        session_id: Optional[str] = None

    class SmartRouteInput(BaseModel):
        condominio_id: str
        message: str
        user_id: Optional[str] = None

    @app.post("/v2/process")
    async def process_v2(input: V2RequestInput):
        """Processa requisição via agentes V2"""
        result = await orchestrator_v2.process_request(
            condominio_id=input.condominio_id,
            agent_type=input.agent_type,
            action=input.action,
            params=input.params,
            user_id=input.user_id,
            session_id=input.session_id
        )
        return result

    @app.post("/v2/smart-route")
    async def smart_route(input: SmartRouteInput):
        """Roteamento inteligente - determina melhor agente automaticamente"""
        result = await orchestrator_v2.smart_route(
            condominio_id=input.condominio_id,
            message=input.message,
            user_id=input.user_id
        )
        return result

    @app.get("/v2/status")
    async def status_v2():
        """Status do orchestrator V2"""
        return orchestrator_v2.get_status()

    @app.get("/v2/supported-agents")
    async def supported_agents():
        """Lista todos os 36 tipos de agentes suportados com descrições"""
        return {
            "total": orchestrator_v2.get_agent_count(),
            "agents": orchestrator_v2.get_supported_agents(),
            "categories": {
                "seguranca": {
                    "description": "Segurança eletrônica e monitoramento",
                    "agents": ["cftv", "acesso", "automacao", "alarme", "rede"]
                },
                "portaria_atendimento": {
                    "description": "Portaria e central de atendimento",
                    "agents": ["portaria_virtual", "voip", "atendimento"]
                },
                "rh_pessoas": {
                    "description": "RH e gestão de pessoas",
                    "agents": ["rh", "facilities"]
                },
                "manutencao_infra": {
                    "description": "Manutenção e infraestrutura",
                    "agents": ["manutencao", "infraestrutura"]
                },
                "gestao_condominial": {
                    "description": "Gestão condominial",
                    "agents": ["sindico", "financeiro", "assembleias", "reservas"]
                },
                "moradores_comunicacao": {
                    "description": "Moradores e comunicação",
                    "agents": ["morador", "comunicacao", "encomendas"]
                },
                "ocorrencias_compliance": {
                    "description": "Ocorrências, compliance e analytics",
                    "agents": ["ocorrencias", "compliance", "analytics"]
                },
                "ia_suporte": {
                    "description": "IA, visão computacional e suporte",
                    "agents": ["visao_ia", "suporte"]
                },
                "especializados": {
                    "description": "Agentes especializados",
                    "agents": ["juridico", "imobiliario", "sustentabilidade", "social",
                              "pet", "estacionamento", "emergencia", "conhecimento",
                              "auditoria", "fornecedores", "valorizacao", "comercial"]
                }
            }
        }

    @app.get("/v2/agents")
    async def list_agents_v2(condominio_id: Optional[str] = None):
        """Lista agentes V2"""
        return orchestrator_v2.list_agents(condominio_id)

    @app.post("/v2/agents/{agent_type}/{condominio_id}")
    async def create_agent_v2(agent_type: str, condominio_id: str):
        """Cria agente V2"""
        try:
            agent = await orchestrator_v2.create_agent(agent_type, condominio_id)
            return {"success": True, "agent_id": f"{agent_type}_{condominio_id}"}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.delete("/v2/agents/{agent_id}")
    async def delete_agent_v2(agent_id: str):
        """Remove agente V2"""
        success = await orchestrator_v2.destroy_agent(agent_id)
        if not success:
            raise HTTPException(status_code=404, detail="Agente não encontrado")
        return {"success": True}

    # ==================== ENDPOINTS DE COMUNICAÇÃO FULL-DUPLEX ====================

    class AgentMessageInput(BaseModel):
        sender_id: str
        receiver_id: str
        content: Any
        message_type: str = "direct"
        priority: str = "normal"
        metadata: Dict[str, Any] = {}

    class BroadcastInput(BaseModel):
        sender_id: str
        content: Any
        condominio_id: Optional[str] = None
        exclude_sender: bool = True
        priority: str = "normal"
        metadata: Dict[str, Any] = {}

    class RequestResponseInput(BaseModel):
        sender_id: str
        receiver_id: str
        content: Any
        timeout: float = 30.0
        metadata: Dict[str, Any] = {}

    class PublishEventInput(BaseModel):
        sender_id: str
        topic: str
        content: Any
        priority: str = "normal"
        metadata: Dict[str, Any] = {}

    class SubscriptionInput(BaseModel):
        agent_id: str
        topic: str

    @app.post("/v2/message/send")
    async def send_agent_message(input: AgentMessageInput):
        """Envia mensagem direta entre agentes (full-duplex)"""
        success = await orchestrator_v2.send_message_to_agent(
            sender_id=input.sender_id,
            receiver_id=input.receiver_id,
            content=input.content,
            message_type=input.message_type,
            priority=input.priority,
            metadata=input.metadata,
        )
        return {"success": success}

    @app.post("/v2/message/broadcast")
    async def broadcast_message(input: BroadcastInput):
        """Envia mensagem broadcast para todos os agentes"""
        delivered = await orchestrator_v2.broadcast_to_agents(
            sender_id=input.sender_id,
            content=input.content,
            condominio_id=input.condominio_id,
            exclude_sender=input.exclude_sender,
            priority=input.priority,
            metadata=input.metadata,
        )
        return {"delivered_count": delivered}

    @app.post("/v2/message/request")
    async def request_response(input: RequestResponseInput):
        """Envia requisição e aguarda resposta (padrão request/response)"""
        response = await orchestrator_v2.request_response(
            sender_id=input.sender_id,
            receiver_id=input.receiver_id,
            content=input.content,
            timeout=input.timeout,
            metadata=input.metadata,
        )
        return {"response": response, "success": response is not None}

    @app.post("/v2/message/publish")
    async def publish_event(input: PublishEventInput):
        """Publica evento em um tópico (pub/sub)"""
        delivered = await orchestrator_v2.publish_event(
            sender_id=input.sender_id,
            topic=input.topic,
            content=input.content,
            priority=input.priority,
            metadata=input.metadata,
        )
        return {"delivered_count": delivered}

    @app.post("/v2/message/subscribe")
    async def subscribe_to_topic(input: SubscriptionInput):
        """Inscreve agente em um tópico de eventos"""
        success = orchestrator_v2.subscribe_agent_to_topic(input.agent_id, input.topic)
        return {"success": success}

    @app.post("/v2/message/unsubscribe")
    async def unsubscribe_from_topic(input: SubscriptionInput):
        """Remove inscrição de agente de um tópico"""
        success = orchestrator_v2.unsubscribe_agent_from_topic(input.agent_id, input.topic)
        return {"success": success}

    @app.get("/v2/message/bus-status")
    async def message_bus_status():
        """Retorna status do Message Bus"""
        return orchestrator_v2.get_message_bus_status()

    @app.get("/v2/message/agents-by-type/{agent_type}")
    async def get_agents_by_type(agent_type: str):
        """Retorna IDs de agentes de um tipo específico"""
        agents = orchestrator_v2.get_agents_by_type(agent_type)
        return {"agent_type": agent_type, "agents": agents, "count": len(agents)}

    @app.get("/v2/message/agents-in-condominio/{condominio_id}")
    async def get_agents_in_condominio(condominio_id: str):
        """Retorna IDs de agentes de um condomínio"""
        agents = orchestrator_v2.get_agents_in_condominio(condominio_id)
        return {"condominio_id": condominio_id, "agents": agents, "count": len(agents)}

    return app


if __name__ == "__main__":
    import uvicorn

    async def main():
        app = await create_api()
        config = uvicorn.Config(app, host="0.0.0.0", port=8001, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()

    asyncio.run(main())
