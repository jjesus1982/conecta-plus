"""
Conecta Plus - Guardian Assistant Agent
Agente Conversacional de Seguranca - Nivel 7 (CFO de Seguranca)

Responsabilidades:
- Interface conversacional para operadores
- Responder perguntas sobre status do sistema
- Fornecer resumos e relatorios
- Auxiliar em tomada de decisoes
- Traduzir dados tecnicos em linguagem natural
"""

import asyncio
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Tuple
from enum import Enum
import re

logger = logging.getLogger(__name__)


class IntentType(Enum):
    """Tipos de intencao do usuario."""
    STATUS_QUERY = "status_query"
    ALERT_QUERY = "alert_query"
    CAMERA_QUERY = "camera_query"
    ACCESS_QUERY = "access_query"
    REPORT_REQUEST = "report_request"
    HELP_REQUEST = "help_request"
    ACTION_REQUEST = "action_request"
    ANALYTICS_QUERY = "analytics_query"
    UNKNOWN = "unknown"


class ResponseType(Enum):
    """Tipos de resposta."""
    TEXT = "text"
    LIST = "list"
    TABLE = "table"
    CHART = "chart"
    ACTION_CONFIRMATION = "action_confirmation"
    ERROR = "error"


@dataclass
class ConversationContext:
    """Contexto de uma conversa."""
    session_id: str
    user_id: str
    user_name: str
    started_at: datetime
    last_activity: datetime
    messages: List[Dict[str, Any]] = field(default_factory=list)
    current_topic: Optional[str] = None
    entities: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UserMessage:
    """Mensagem do usuario."""
    content: str
    timestamp: datetime
    user_id: str
    session_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AssistantResponse:
    """Resposta do assistente."""
    content: str
    response_type: ResponseType
    data: Optional[Dict[str, Any]] = None
    suggestions: List[str] = field(default_factory=list)
    actions: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 1.0


@dataclass
class Intent:
    """Intencao detectada."""
    type: IntentType
    confidence: float
    entities: Dict[str, Any]
    raw_query: str


class GuardianAssistantAgent:
    """
    Agente Assistente Guardian - Nivel 7 TRANSCENDENT (CFO de Seguranca)

    Capacidades:
    - Processamento de linguagem natural
    - Respostas contextualizadas
    - Integracao com todos os subsistemas
    - Geracao de relatorios sob demanda
    - Recomendacoes inteligentes
    """

    def __init__(
        self,
        agent_id: str = "guardian_assistant",
        config: Optional[Dict[str, Any]] = None,
        message_bus: Optional[Any] = None,
        monitor_agent: Optional[Any] = None,
        access_agent: Optional[Any] = None,
        analytics_agent: Optional[Any] = None
    ):
        self.agent_id = agent_id
        self.config = config or {}
        self.message_bus = message_bus

        # Referencias para outros agentes
        self.monitor_agent = monitor_agent
        self.access_agent = access_agent
        self.analytics_agent = analytics_agent

        # Configuracoes
        self.max_context_messages = self.config.get("max_context_messages", 20)
        self.session_timeout_minutes = self.config.get("session_timeout_minutes", 30)

        # Sessoes ativas
        self.active_sessions: Dict[str, ConversationContext] = {}

        # Padroes de reconhecimento de intencao
        self._intent_patterns = self._build_intent_patterns()

        # Templates de resposta
        self._response_templates = self._build_response_templates()

        # Estado
        self.is_running = False

        logger.info(f"GuardianAssistantAgent {agent_id} inicializado")

    def _build_intent_patterns(self) -> Dict[IntentType, List[str]]:
        """Constroi padroes para deteccao de intencao."""
        return {
            IntentType.STATUS_QUERY: [
                r"status",
                r"como est[aá]",
                r"situa[çc][aã]o",
                r"tudo bem",
                r"tudo ok",
                r"funcionando",
                r"opera[çc]ional",
                r"resumo geral"
            ],
            IntentType.ALERT_QUERY: [
                r"alert",
                r"ocorr[eê]ncia",
                r"incidente",
                r"problema",
                r"alarme",
                r"aten[çc][aã]o",
                r"urgente",
                r"emergen[çc]ia"
            ],
            IntentType.CAMERA_QUERY: [
                r"c[aâ]mera",
                r"cftv",
                r"grava[çc][aã]o",
                r"v[ií]deo",
                r"imagem",
                r"monitoramento",
                r"frigate"
            ],
            IntentType.ACCESS_QUERY: [
                r"acesso",
                r"entrada",
                r"sa[ií]da",
                r"portaria",
                r"visitante",
                r"morador",
                r"placa",
                r"veiculo",
                r"ve[ií]culo"
            ],
            IntentType.REPORT_REQUEST: [
                r"relat[oó]rio",
                r"report",
                r"exportar",
                r"gerar",
                r"lista",
                r"hist[oó]rico"
            ],
            IntentType.HELP_REQUEST: [
                r"ajuda",
                r"help",
                r"como fa[çc]o",
                r"o que",
                r"explica",
                r"tutorial"
            ],
            IntentType.ACTION_REQUEST: [
                r"abrir",
                r"fechar",
                r"liberar",
                r"bloquear",
                r"ativar",
                r"desativar",
                r"acionar"
            ],
            IntentType.ANALYTICS_QUERY: [
                r"an[aá]lise",
                r"estat[ií]stica",
                r"tend[eê]ncia",
                r"predi[çc][aã]o",
                r"previs[aã]o",
                r"risco",
                r"anomalia"
            ]
        }

    def _build_response_templates(self) -> Dict[str, str]:
        """Constroi templates de resposta."""
        return {
            "greeting": "Ola, {user_name}! Sou o Assistente Guardian. Como posso ajudar?",
            "status_ok": "Sistema operando normalmente. Todas as {camera_count} cameras ativas, "
                        "{access_points} pontos de acesso funcionando. Nivel de risco: {risk_level}.",
            "status_alert": "Atencao! {alert_count} alertas ativos. Nivel de risco: {risk_level}. "
                           "Recomendo verificar: {recommendations}",
            "no_alerts": "Nenhum alerta ativo no momento. Sistema funcionando normalmente.",
            "alerts_found": "Encontrei {count} alertas:\n{alert_list}",
            "camera_status": "Status das cameras:\n- Ativas: {active}\n- Offline: {offline}\n"
                            "- Em manutencao: {maintenance}",
            "access_summary": "Resumo de acessos das ultimas {hours}h:\n"
                             "- Entradas: {entries}\n- Saidas: {exits}\n"
                             "- Negados: {denied}\n- Visitantes: {visitors}",
            "help_general": "Posso ajudar com:\n"
                           "- Status do sistema\n"
                           "- Consulta de alertas\n"
                           "- Status de cameras\n"
                           "- Historico de acessos\n"
                           "- Relatorios\n"
                           "- Analises e previsoes\n\n"
                           "Basta perguntar!",
            "action_confirm": "Acao '{action}' solicitada. Confirma a execucao?",
            "action_executed": "Acao '{action}' executada com sucesso.",
            "action_denied": "Desculpe, voce nao tem permissao para executar '{action}'.",
            "not_understood": "Desculpe, nao entendi sua solicitacao. Pode reformular? "
                             "Diga 'ajuda' para ver o que posso fazer.",
            "analytics_risk": "Analise de Risco:\n"
                             "- Score atual: {score}/100 ({level})\n"
                             "- Tendencia: {trend}\n"
                             "- Anomalias (24h): {anomalies}\n"
                             "- Recomendacoes: {recommendations}",
            "error": "Ocorreu um erro ao processar sua solicitacao: {error}"
        }

    async def start(self) -> None:
        """Inicia o agente assistente."""
        if self.is_running:
            return

        self.is_running = True

        if self.message_bus:
            await self.message_bus.subscribe("assistant.message", self._handle_incoming_message)
            await self.message_bus.subscribe("assistant.query", self._handle_query)

        logger.info(f"GuardianAssistantAgent {self.agent_id} iniciado")

    async def stop(self) -> None:
        """Para o agente assistente."""
        self.is_running = False
        logger.info(f"GuardianAssistantAgent {self.agent_id} parado")

    async def _handle_incoming_message(self, message: Dict[str, Any]) -> None:
        """Processa mensagem recebida via message bus."""
        try:
            user_message = UserMessage(
                content=message.get("content", ""),
                timestamp=datetime.fromisoformat(message.get("timestamp", datetime.now().isoformat())),
                user_id=message.get("user_id", "unknown"),
                session_id=message.get("session_id", ""),
                metadata=message.get("metadata", {})
            )

            response = await self.process_message(user_message)

            if self.message_bus:
                await self.message_bus.publish("assistant.response", {
                    "session_id": user_message.session_id,
                    "user_id": user_message.user_id,
                    "response": response.content,
                    "type": response.response_type.value,
                    "data": response.data,
                    "suggestions": response.suggestions,
                    "timestamp": datetime.now().isoformat()
                })

        except Exception as e:
            logger.error(f"Erro ao processar mensagem: {e}")

    async def _handle_query(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Processa query direta e retorna resposta."""
        try:
            user_message = UserMessage(
                content=query.get("query", ""),
                timestamp=datetime.now(),
                user_id=query.get("user_id", "system"),
                session_id=query.get("session_id", "direct")
            )

            response = await self.process_message(user_message)

            return {
                "success": True,
                "response": response.content,
                "type": response.response_type.value,
                "data": response.data,
                "suggestions": response.suggestions
            }

        except Exception as e:
            logger.error(f"Erro ao processar query: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def process_message(self, message: UserMessage) -> AssistantResponse:
        """Processa mensagem do usuario e gera resposta."""
        # Obter ou criar contexto de sessao
        context = self._get_or_create_context(message)

        # Detectar intencao
        intent = self._detect_intent(message.content)

        # Adicionar mensagem ao contexto
        context.messages.append({
            "role": "user",
            "content": message.content,
            "timestamp": message.timestamp.isoformat(),
            "intent": intent.type.value
        })

        # Processar baseado na intencao
        response = await self._generate_response(intent, context)

        # Adicionar resposta ao contexto
        context.messages.append({
            "role": "assistant",
            "content": response.content,
            "timestamp": datetime.now().isoformat()
        })

        # Manter tamanho do contexto
        if len(context.messages) > self.max_context_messages:
            context.messages = context.messages[-self.max_context_messages:]

        context.last_activity = datetime.now()

        return response

    def _get_or_create_context(self, message: UserMessage) -> ConversationContext:
        """Obtem ou cria contexto de conversa."""
        session_id = message.session_id or f"session_{message.user_id}"

        if session_id in self.active_sessions:
            context = self.active_sessions[session_id]
            # Verificar timeout
            if datetime.now() - context.last_activity > timedelta(minutes=self.session_timeout_minutes):
                # Sessao expirou, criar nova
                del self.active_sessions[session_id]
            else:
                return context

        # Criar novo contexto
        context = ConversationContext(
            session_id=session_id,
            user_id=message.user_id,
            user_name=message.metadata.get("user_name", "Usuario"),
            started_at=datetime.now(),
            last_activity=datetime.now()
        )
        self.active_sessions[session_id] = context
        return context

    def _detect_intent(self, text: str) -> Intent:
        """Detecta a intencao do usuario."""
        text_lower = text.lower()
        entities = {}

        # Verificar cada tipo de intencao
        best_match: Tuple[IntentType, float] = (IntentType.UNKNOWN, 0.0)

        for intent_type, patterns in self._intent_patterns.items():
            match_count = 0
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    match_count += 1

            if match_count > 0:
                confidence = min(match_count * 0.3 + 0.4, 1.0)
                if confidence > best_match[1]:
                    best_match = (intent_type, confidence)

        # Extrair entidades
        entities = self._extract_entities(text)

        return Intent(
            type=best_match[0],
            confidence=best_match[1],
            entities=entities,
            raw_query=text
        )

    def _extract_entities(self, text: str) -> Dict[str, Any]:
        """Extrai entidades do texto."""
        entities = {}

        # Extrair numeros
        numbers = re.findall(r'\d+', text)
        if numbers:
            entities["numbers"] = [int(n) for n in numbers]

        # Extrair periodos de tempo
        time_patterns = {
            "hoje": "today",
            "ontem": "yesterday",
            "semana": "week",
            "mes": "month",
            "hora": "hour",
            "minuto": "minute"
        }
        for pt, en in time_patterns.items():
            if pt in text.lower():
                entities["time_reference"] = en

        # Extrair horas
        hours_match = re.search(r'(\d{1,2})\s*h', text.lower())
        if hours_match:
            entities["hours"] = int(hours_match.group(1))

        # Extrair locais
        location_keywords = ["entrada", "saida", "portaria", "bloco", "torre", "garagem"]
        for loc in location_keywords:
            if loc in text.lower():
                entities["location"] = loc
                break

        # Extrair nomes de camera
        camera_match = re.search(r'camera\s+(\d+|[a-zA-Z]+)', text.lower())
        if camera_match:
            entities["camera_id"] = camera_match.group(1)

        return entities

    async def _generate_response(
        self,
        intent: Intent,
        context: ConversationContext
    ) -> AssistantResponse:
        """Gera resposta baseada na intencao."""
        try:
            handlers = {
                IntentType.STATUS_QUERY: self._handle_status_query,
                IntentType.ALERT_QUERY: self._handle_alert_query,
                IntentType.CAMERA_QUERY: self._handle_camera_query,
                IntentType.ACCESS_QUERY: self._handle_access_query,
                IntentType.REPORT_REQUEST: self._handle_report_request,
                IntentType.HELP_REQUEST: self._handle_help_request,
                IntentType.ACTION_REQUEST: self._handle_action_request,
                IntentType.ANALYTICS_QUERY: self._handle_analytics_query,
                IntentType.UNKNOWN: self._handle_unknown
            }

            handler = handlers.get(intent.type, self._handle_unknown)
            return await handler(intent, context)

        except Exception as e:
            logger.error(f"Erro ao gerar resposta: {e}")
            return AssistantResponse(
                content=self._response_templates["error"].format(error=str(e)),
                response_type=ResponseType.ERROR,
                confidence=1.0
            )

    async def _handle_status_query(
        self,
        intent: Intent,
        context: ConversationContext
    ) -> AssistantResponse:
        """Processa consulta de status."""
        # Coletar dados de status
        status_data = await self._collect_system_status()

        if status_data.get("alert_count", 0) > 0:
            template = self._response_templates["status_alert"]
        else:
            template = self._response_templates["status_ok"]

        response_text = template.format(**status_data)

        return AssistantResponse(
            content=response_text,
            response_type=ResponseType.TEXT,
            data=status_data,
            suggestions=[
                "Ver alertas ativos",
                "Ver status das cameras",
                "Ver acessos de hoje"
            ],
            confidence=0.9
        )

    async def _handle_alert_query(
        self,
        intent: Intent,
        context: ConversationContext
    ) -> AssistantResponse:
        """Processa consulta de alertas."""
        # Buscar alertas
        alerts = await self._get_active_alerts()

        if not alerts:
            return AssistantResponse(
                content=self._response_templates["no_alerts"],
                response_type=ResponseType.TEXT,
                suggestions=["Ver status geral", "Ver historico de alertas"]
            )

        # Formatar lista de alertas
        alert_list = "\n".join([
            f"- [{a['severity'].upper()}] {a['description']} ({a['time']})"
            for a in alerts[:5]
        ])

        response_text = self._response_templates["alerts_found"].format(
            count=len(alerts),
            alert_list=alert_list
        )

        if len(alerts) > 5:
            response_text += f"\n\n... e mais {len(alerts) - 5} alertas."

        return AssistantResponse(
            content=response_text,
            response_type=ResponseType.LIST,
            data={"alerts": alerts},
            suggestions=[
                "Ver detalhes do alerta",
                "Marcar como resolvido",
                "Gerar relatorio de alertas"
            ],
            confidence=0.9
        )

    async def _handle_camera_query(
        self,
        intent: Intent,
        context: ConversationContext
    ) -> AssistantResponse:
        """Processa consulta de cameras."""
        camera_data = await self._get_camera_status()

        response_text = self._response_templates["camera_status"].format(**camera_data)

        # Se perguntou sobre camera especifica
        if "camera_id" in intent.entities:
            camera_id = intent.entities["camera_id"]
            specific_info = await self._get_specific_camera_info(camera_id)
            if specific_info:
                response_text += f"\n\nCamera {camera_id}:\n"
                response_text += f"- Status: {specific_info.get('status', 'desconhecido')}\n"
                response_text += f"- Local: {specific_info.get('location', 'nao informado')}\n"
                response_text += f"- Ultima deteccao: {specific_info.get('last_detection', 'nenhuma')}"

        return AssistantResponse(
            content=response_text,
            response_type=ResponseType.TEXT,
            data=camera_data,
            suggestions=[
                "Ver gravacoes recentes",
                "Verificar camera offline",
                "Status de todas as cameras"
            ],
            confidence=0.85
        )

    async def _handle_access_query(
        self,
        intent: Intent,
        context: ConversationContext
    ) -> AssistantResponse:
        """Processa consulta de acessos."""
        hours = intent.entities.get("hours", 24)
        access_data = await self._get_access_summary(hours)

        response_text = self._response_templates["access_summary"].format(
            hours=hours,
            **access_data
        )

        return AssistantResponse(
            content=response_text,
            response_type=ResponseType.TEXT,
            data=access_data,
            suggestions=[
                "Ver acessos negados",
                "Ver visitantes do dia",
                "Gerar relatorio de acessos"
            ],
            confidence=0.85
        )

    async def _handle_report_request(
        self,
        intent: Intent,
        context: ConversationContext
    ) -> AssistantResponse:
        """Processa solicitacao de relatorio."""
        report_types = []

        # Identificar tipo de relatorio
        query_lower = intent.raw_query.lower()
        if any(word in query_lower for word in ["acesso", "entrada", "saida"]):
            report_types.append("acessos")
        if any(word in query_lower for word in ["alerta", "incidente", "ocorrencia"]):
            report_types.append("alertas")
        if any(word in query_lower for word in ["camera", "video", "gravacao"]):
            report_types.append("cameras")

        if not report_types:
            report_types = ["geral"]

        # Simular geracao de relatorio
        response_text = f"Gerando relatorio de {', '.join(report_types)}...\n\n"
        response_text += "O relatorio sera enviado para seu email em alguns minutos.\n"
        response_text += "Voce tambem pode acessa-lo em: Sistema > Relatorios > Recentes"

        return AssistantResponse(
            content=response_text,
            response_type=ResponseType.TEXT,
            data={"report_types": report_types, "status": "generating"},
            actions=[{"action": "generate_report", "types": report_types}],
            suggestions=[
                "Ver relatorios anteriores",
                "Agendar relatorio periodico"
            ],
            confidence=0.8
        )

    async def _handle_help_request(
        self,
        intent: Intent,
        context: ConversationContext
    ) -> AssistantResponse:
        """Processa pedido de ajuda."""
        # Verificar se e ajuda especifica
        query_lower = intent.raw_query.lower()

        if "camera" in query_lower:
            help_text = ("Para consultar cameras, voce pode perguntar:\n"
                        "- 'Status das cameras'\n"
                        "- 'Camera 1 esta funcionando?'\n"
                        "- 'Cameras offline'\n"
                        "- 'Ver gravacao da camera X'")
        elif "acesso" in query_lower:
            help_text = ("Para consultar acessos, voce pode perguntar:\n"
                        "- 'Acessos de hoje'\n"
                        "- 'Ultimas entradas'\n"
                        "- 'Acessos negados'\n"
                        "- 'Visitantes do dia'")
        elif "alerta" in query_lower:
            help_text = ("Para consultar alertas, voce pode perguntar:\n"
                        "- 'Alertas ativos'\n"
                        "- 'Ultimos incidentes'\n"
                        "- 'Alertas criticos'\n"
                        "- 'Historico de alertas'")
        else:
            help_text = self._response_templates["help_general"]

        return AssistantResponse(
            content=help_text,
            response_type=ResponseType.TEXT,
            suggestions=[
                "Status do sistema",
                "Alertas ativos",
                "Cameras offline"
            ],
            confidence=1.0
        )

    async def _handle_action_request(
        self,
        intent: Intent,
        context: ConversationContext
    ) -> AssistantResponse:
        """Processa solicitacao de acao."""
        query_lower = intent.raw_query.lower()

        # Identificar acao solicitada
        action = None
        if "abrir" in query_lower or "liberar" in query_lower:
            action = "abrir_acesso"
        elif "fechar" in query_lower or "bloquear" in query_lower:
            action = "bloquear_acesso"
        elif "ativar" in query_lower:
            action = "ativar_alarme"
        elif "desativar" in query_lower:
            action = "desativar_alarme"

        if not action:
            return AssistantResponse(
                content="Nao consegui identificar a acao solicitada. "
                       "Pode especificar o que deseja fazer?",
                response_type=ResponseType.TEXT,
                suggestions=[
                    "Abrir portaria",
                    "Bloquear acesso",
                    "Ativar alarme"
                ],
                confidence=0.5
            )

        # Solicitar confirmacao
        return AssistantResponse(
            content=self._response_templates["action_confirm"].format(action=action),
            response_type=ResponseType.ACTION_CONFIRMATION,
            data={"action": action, "requires_confirmation": True},
            actions=[{"action": action, "status": "pending_confirmation"}],
            suggestions=["Sim, confirmar", "Nao, cancelar"],
            confidence=0.7
        )

    async def _handle_analytics_query(
        self,
        intent: Intent,
        context: ConversationContext
    ) -> AssistantResponse:
        """Processa consulta de analytics."""
        if self.analytics_agent:
            try:
                dashboard_data = await self.analytics_agent.get_dashboard_data()

                response_text = self._response_templates["analytics_risk"].format(
                    score=int(dashboard_data.get("risk_score", 0)),
                    level=dashboard_data.get("risk_level", "desconhecido"),
                    trend=self._translate_trend(dashboard_data.get("risk_trend", "stable")),
                    anomalies=dashboard_data.get("anomalies_24h", 0),
                    recommendations="\n  - ".join(dashboard_data.get("recommendations", ["Nenhuma"]))
                )

                return AssistantResponse(
                    content=response_text,
                    response_type=ResponseType.TEXT,
                    data=dashboard_data,
                    suggestions=[
                        "Ver anomalias detectadas",
                        "Ver previsoes",
                        "Relatorio de risco"
                    ],
                    confidence=0.9
                )

            except Exception as e:
                logger.error(f"Erro ao obter analytics: {e}")

        # Fallback se nao tem analytics agent
        return AssistantResponse(
            content="Sistema de analytics indisponivel no momento. "
                   "Tente novamente em alguns instantes.",
            response_type=ResponseType.TEXT,
            confidence=0.5
        )

    async def _handle_unknown(
        self,
        intent: Intent,
        context: ConversationContext
    ) -> AssistantResponse:
        """Processa intencao nao reconhecida."""
        # Verificar se e saudacao
        greetings = ["oi", "ola", "bom dia", "boa tarde", "boa noite", "hey", "hi"]
        if any(g in intent.raw_query.lower() for g in greetings):
            return AssistantResponse(
                content=self._response_templates["greeting"].format(
                    user_name=context.user_name
                ),
                response_type=ResponseType.TEXT,
                suggestions=[
                    "Status do sistema",
                    "Alertas ativos",
                    "Ajuda"
                ],
                confidence=1.0
            )

        return AssistantResponse(
            content=self._response_templates["not_understood"],
            response_type=ResponseType.TEXT,
            suggestions=[
                "Status do sistema",
                "Ver alertas",
                "Ajuda"
            ],
            confidence=0.3
        )

    def _translate_trend(self, trend: str) -> str:
        """Traduz tendencia para portugues."""
        translations = {
            "increasing": "em alta",
            "decreasing": "em queda",
            "stable": "estavel",
            "spike": "pico detectado"
        }
        return translations.get(trend, trend)

    # Metodos auxiliares para coleta de dados
    async def _collect_system_status(self) -> Dict[str, Any]:
        """Coleta status geral do sistema."""
        # Simulacao - em producao buscaria dos agentes reais
        camera_count = 24
        access_points = 8
        alert_count = 0
        risk_level = "baixo"

        if self.monitor_agent:
            try:
                # Buscar dados reais do monitor agent
                pass
            except Exception:
                pass

        if self.analytics_agent:
            try:
                dashboard = await self.analytics_agent.get_dashboard_data()
                risk_level = dashboard.get("risk_level", "baixo")
                alert_count = dashboard.get("anomalies_24h", 0)
            except Exception:
                pass

        return {
            "camera_count": camera_count,
            "access_points": access_points,
            "alert_count": alert_count,
            "risk_level": risk_level,
            "recommendations": "Verificar cameras do bloco B" if alert_count > 0 else ""
        }

    async def _get_active_alerts(self) -> List[Dict[str, Any]]:
        """Obtem alertas ativos."""
        # Simulacao - em producao buscaria do sistema real
        if self.monitor_agent:
            try:
                alerts = await self.monitor_agent.get_active_alerts()
                return [
                    {
                        "id": a.id,
                        "severity": a.severity.value,
                        "description": a.description,
                        "time": a.timestamp.strftime("%H:%M")
                    }
                    for a in alerts
                ]
            except Exception:
                pass

        return []

    async def _get_camera_status(self) -> Dict[str, Any]:
        """Obtem status das cameras."""
        # Simulacao
        return {
            "active": 22,
            "offline": 1,
            "maintenance": 1
        }

    async def _get_specific_camera_info(self, camera_id: str) -> Optional[Dict[str, Any]]:
        """Obtem info de camera especifica."""
        # Simulacao
        return {
            "status": "ativo",
            "location": "Entrada Principal",
            "last_detection": "ha 5 minutos"
        }

    async def _get_access_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Obtem resumo de acessos."""
        # Simulacao
        return {
            "entries": 145,
            "exits": 132,
            "denied": 3,
            "visitors": 12
        }

    # API publica
    async def chat(
        self,
        message: str,
        user_id: str,
        session_id: Optional[str] = None,
        user_name: str = "Usuario"
    ) -> Dict[str, Any]:
        """Interface principal de chat."""
        user_message = UserMessage(
            content=message,
            timestamp=datetime.now(),
            user_id=user_id,
            session_id=session_id or f"session_{user_id}",
            metadata={"user_name": user_name}
        )

        response = await self.process_message(user_message)

        return {
            "response": response.content,
            "type": response.response_type.value,
            "data": response.data,
            "suggestions": response.suggestions,
            "confidence": response.confidence
        }

    async def get_quick_status(self) -> str:
        """Retorna status rapido em texto."""
        status = await self._collect_system_status()

        if status["alert_count"] > 0:
            return f"⚠️ {status['alert_count']} alertas ativos | Risco: {status['risk_level']}"
        else:
            return f"✅ Sistema OK | {status['camera_count']} cameras | Risco: {status['risk_level']}"
