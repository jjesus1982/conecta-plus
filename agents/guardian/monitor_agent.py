"""
Conecta Plus - Guardian Monitor Agent
Agente de Monitoramento Inteligente de Cameras (Nivel 7)

Responsabilidades:
- Analisar feeds de cameras em tempo real
- Detectar anomalias automaticamente
- Priorizar alertas por criticidade
- Sugerir acoes baseado em padroes
- Integrar com Frigate NVR e YOLO

Tecnologias:
- YOLO v8 para deteccao de objetos
- Frigate NVR para gerenciamento de cameras
- Analise comportamental em tempo real
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import json

from ..core.base_agent import (
    BaseAgent, EvolutionLevel, Priority, AgentCapability,
    AgentContext, AgentAction, AgentPrediction,
)
from ..core.message_bus import MessageBus, BusMessage, MessageType, MessagePriority

logger = logging.getLogger(__name__)


class AlertType(Enum):
    """Tipos de alerta de monitoramento"""
    MOVIMENTO = "movimento"
    PESSOA_DETECTADA = "pessoa_detectada"
    VEICULO_DETECTADO = "veiculo_detectado"
    INTRUSO = "intruso"
    OBJETO_ABANDONADO = "objeto_abandonado"
    AGLOMERACAO = "aglomeracao"
    COMPORTAMENTO_SUSPEITO = "comportamento_suspeito"
    CERCA_VIRTUAL = "cerca_virtual"
    CAMERA_OFFLINE = "camera_offline"
    CAMERA_OBSTRUIDA = "camera_obstruida"


class AlertSeverity(Enum):
    """Severidade do alerta"""
    INFO = 1
    BAIXA = 2
    MEDIA = 3
    ALTA = 4
    CRITICA = 5


@dataclass
class CameraStatus:
    """Status de uma camera"""
    camera_id: str
    nome: str
    status: str  # online, offline, error
    ultimo_evento: Optional[datetime] = None
    deteccao_ativa: bool = True
    gravacao_ativa: bool = True
    fps_atual: int = 0
    objetos_detectados: int = 0


@dataclass
class DetectionEvent:
    """Evento de deteccao"""
    id: str
    camera_id: str
    tipo: AlertType
    timestamp: datetime
    confianca: float
    objetos: List[str]
    bounding_boxes: List[Dict]
    snapshot_url: Optional[str] = None
    clip_url: Optional[str] = None
    processado: bool = False
    alerta_enviado: bool = False


@dataclass
class Alert:
    """Alerta gerado pelo monitoramento"""
    id: str
    tipo: AlertType
    severidade: AlertSeverity
    camera_id: str
    timestamp: datetime
    descricao: str
    eventos: List[str]
    acoes_sugeridas: List[str]
    reconhecido: bool = False
    reconhecido_por: Optional[str] = None
    resolvido: bool = False


class GuardianMonitorAgent(BaseAgent):
    """
    Agente de Monitoramento Inteligente - Nivel 7

    Capacidades por nivel:
    1. REATIVO: Receber eventos de cameras
    2. PROATIVO: Detectar anomalias em tempo real
    3. PREDITIVO: Prever situacoes de risco
    4. AUTONOMO: Tomar acoes automaticas
    5. EVOLUTIVO: Aprender novos padroes
    6. COLABORATIVO: Integrar com outros agentes
    7. TRANSCENDENTE: Visao holistica de seguranca
    """

    def __init__(
        self,
        condominio_id: str,
        llm_client: Any = None,
        memory: Any = None,
        message_bus: MessageBus = None,
        frigate_service: Any = None,
        evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT,
    ):
        super().__init__(
            agent_id=f"guardian_monitor_{condominio_id}",
            agent_type="guardian_monitor",
            condominio_id=condominio_id,
            evolution_level=evolution_level,
            llm_client=llm_client,
            memory_store=memory,
        )

        self.message_bus = message_bus
        self.frigate = frigate_service

        # Estado interno
        self._cameras: Dict[str, CameraStatus] = {}
        self._eventos_pendentes: List[DetectionEvent] = []
        self._alertas_ativos: Dict[str, Alert] = {}
        self._historico_alertas: List[Alert] = []

        # Configuracoes
        self.config = {
            "confianca_minima": 0.7,
            "cooldown_alertas": 60,  # segundos entre alertas similares
            "max_eventos_buffer": 1000,
            "zonas_criticas": [],  # cameras em areas criticas
            "horarios_alta_vigilancia": [
                {"inicio": "22:00", "fim": "06:00"},
            ],
            "objetos_interesse": ["person", "car", "truck", "motorcycle"],
            "alertar_objetos_abandonados": True,
            "tempo_objeto_abandonado": 300,  # 5 minutos
        }

        # Contadores e metricas
        self._metricas = {
            "eventos_processados": 0,
            "alertas_gerados": 0,
            "falsos_positivos": 0,
            "tempo_resposta_medio_ms": 0,
        }

        # Callbacks
        self._on_alert_callbacks: List[Callable] = []

        logger.info(f"GuardianMonitorAgent inicializado para condominio {condominio_id}")

    def _register_capabilities(self) -> None:
        """Registra capacidades do agente"""
        self._capabilities["receive_camera_events"] = AgentCapability(
            name="receive_camera_events",
            description="Receber e processar eventos de cameras",
            level=EvolutionLevel.REACTIVE
        )
        self._capabilities["detect_anomalies"] = AgentCapability(
            name="detect_anomalies",
            description="Detectar anomalias em tempo real",
            level=EvolutionLevel.PROACTIVE
        )
        self._capabilities["predict_risks"] = AgentCapability(
            name="predict_risks",
            description="Prever situacoes de risco",
            level=EvolutionLevel.PREDICTIVE
        )
        self._capabilities["auto_response"] = AgentCapability(
            name="auto_response",
            description="Tomar acoes automaticas",
            level=EvolutionLevel.AUTONOMOUS
        )
        self._capabilities["learn_patterns"] = AgentCapability(
            name="learn_patterns",
            description="Aprender novos padroes de ameaca",
            level=EvolutionLevel.EVOLUTIONARY
        )
        self._capabilities["collaborate_agents"] = AgentCapability(
            name="collaborate_agents",
            description="Colaborar com outros agentes",
            level=EvolutionLevel.COLLABORATIVE
        )
        self._capabilities["holistic_security"] = AgentCapability(
            name="holistic_security",
            description="Visao holistica de seguranca",
            level=EvolutionLevel.TRANSCENDENT
        )

    def get_system_prompt(self) -> str:
        """Retorna o system prompt do agente"""
        return f"""Voce e o Agente de Monitoramento Guardian do Conecta Plus.
ID: {self.agent_id}
Condominio: {self.condominio_id}
Nivel de Evolucao: {self.evolution_level.name}

Responsabilidades:
1. Monitorar todas as cameras do condominio em tempo real
2. Detectar pessoas, veiculos e objetos suspeitos
3. Identificar comportamentos anomalos
4. Gerar alertas priorizados por severidade
5. Sugerir acoes de resposta apropriadas
6. Aprender padroes normais vs anomalos

Diretrizes:
- Priorize a seguranca dos moradores
- Minimize falsos positivos
- Seja claro e objetivo nos alertas
- Sugira acoes concretas e executaveis
- Colabore com outros agentes quando necessario

Cameras monitoradas: {len(self._cameras)}
Alertas ativos: {len(self._alertas_ativos)}
"""

    async def process(self, input_data: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        """Processa entrada e retorna resultado"""
        action = input_data.get("action", "status")

        if action == "status":
            return await self._get_status()
        elif action == "process_event":
            return await self._process_detection_event(input_data.get("event", {}))
        elif action == "list_alerts":
            return await self._list_alerts(input_data.get("filters", {}))
        elif action == "acknowledge_alert":
            return await self._acknowledge_alert(
                input_data.get("alert_id"),
                context.user_id
            )
        elif action == "analyze_camera":
            return await self._analyze_camera(input_data.get("camera_id"))
        elif action == "get_recommendations":
            return await self._get_security_recommendations()
        else:
            return {"error": f"Acao desconhecida: {action}"}

    async def _get_status(self) -> Dict[str, Any]:
        """Retorna status atual do monitoramento"""
        cameras_online = sum(1 for c in self._cameras.values() if c.status == "online")
        cameras_total = len(self._cameras)

        return {
            "agent_id": self.agent_id,
            "status": "active",
            "cameras": {
                "total": cameras_total,
                "online": cameras_online,
                "offline": cameras_total - cameras_online,
            },
            "alertas_ativos": len(self._alertas_ativos),
            "eventos_pendentes": len(self._eventos_pendentes),
            "metricas": self._metricas,
            "config": self.config,
        }

    async def _process_detection_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Processa evento de deteccao do Frigate/YOLO"""
        try:
            event = DetectionEvent(
                id=event_data.get("id", f"evt_{datetime.now().timestamp()}"),
                camera_id=event_data.get("camera"),
                tipo=self._classify_event_type(event_data),
                timestamp=datetime.now(),
                confianca=event_data.get("score", 0.0),
                objetos=event_data.get("labels", []),
                bounding_boxes=event_data.get("boxes", []),
                snapshot_url=event_data.get("snapshot_url"),
                clip_url=event_data.get("clip_url"),
            )

            self._eventos_pendentes.append(event)
            self._metricas["eventos_processados"] += 1

            # Analisar se deve gerar alerta
            should_alert, severity, descricao = await self._analyze_event(event)

            if should_alert:
                alert = await self._create_alert(event, severity, descricao)
                return {
                    "processed": True,
                    "alert_generated": True,
                    "alert": {
                        "id": alert.id,
                        "tipo": alert.tipo.value,
                        "severidade": alert.severidade.value,
                        "descricao": alert.descricao,
                    }
                }

            return {"processed": True, "alert_generated": False}

        except Exception as e:
            logger.error(f"Erro ao processar evento: {e}")
            return {"processed": False, "error": str(e)}

    def _classify_event_type(self, event_data: Dict[str, Any]) -> AlertType:
        """Classifica o tipo de evento baseado nos dados"""
        label = event_data.get("label", "").lower()
        zone = event_data.get("zone", "")

        if label == "person":
            if "entrada" in zone or "portaria" in zone:
                return AlertType.PESSOA_DETECTADA
            return AlertType.INTRUSO
        elif label in ["car", "truck", "motorcycle"]:
            return AlertType.VEICULO_DETECTADO
        elif "abandoned" in event_data.get("type", ""):
            return AlertType.OBJETO_ABANDONADO
        elif event_data.get("type") == "line_crossing":
            return AlertType.CERCA_VIRTUAL

        return AlertType.MOVIMENTO

    async def _analyze_event(
        self, event: DetectionEvent
    ) -> tuple[bool, AlertSeverity, str]:
        """Analisa evento e decide se deve gerar alerta"""

        # Filtrar por confianca minima
        if event.confianca < self.config["confianca_minima"]:
            return False, AlertSeverity.INFO, ""

        # Verificar cooldown
        if self._is_in_cooldown(event):
            return False, AlertSeverity.INFO, ""

        # Verificar horario de alta vigilancia
        is_high_alert = self._is_high_alert_time()

        # Determinar severidade
        severity = AlertSeverity.MEDIA
        descricao = ""

        if event.tipo == AlertType.INTRUSO:
            severity = AlertSeverity.CRITICA if is_high_alert else AlertSeverity.ALTA
            descricao = f"Pessoa detectada em area restrita - Camera {event.camera_id}"

        elif event.tipo == AlertType.OBJETO_ABANDONADO:
            severity = AlertSeverity.ALTA
            descricao = f"Objeto abandonado detectado - Camera {event.camera_id}"

        elif event.tipo == AlertType.CERCA_VIRTUAL:
            severity = AlertSeverity.ALTA
            descricao = f"Cruzamento de cerca virtual - Camera {event.camera_id}"

        elif event.tipo == AlertType.AGLOMERACAO:
            severity = AlertSeverity.MEDIA
            descricao = f"Aglomeracao detectada - Camera {event.camera_id}"

        elif event.tipo == AlertType.PESSOA_DETECTADA:
            # Pessoa em area normal - apenas logar
            return False, AlertSeverity.INFO, ""

        elif event.tipo == AlertType.VEICULO_DETECTADO:
            # Veiculo em area normal - apenas logar
            return False, AlertSeverity.INFO, ""

        else:
            severity = AlertSeverity.BAIXA
            descricao = f"Movimento detectado - Camera {event.camera_id}"

        # Elevar severidade para cameras em zonas criticas
        if event.camera_id in self.config["zonas_criticas"]:
            if severity.value < AlertSeverity.ALTA.value:
                severity = AlertSeverity.ALTA

        return True, severity, descricao

    def _is_in_cooldown(self, event: DetectionEvent) -> bool:
        """Verifica se evento similar esta em cooldown"""
        cooldown = self.config["cooldown_alertas"]

        for alert_id, alert in self._alertas_ativos.items():
            if alert.camera_id == event.camera_id and alert.tipo == event.tipo:
                elapsed = (datetime.now() - alert.timestamp).total_seconds()
                if elapsed < cooldown:
                    return True

        return False

    def _is_high_alert_time(self) -> bool:
        """Verifica se esta em horario de alta vigilancia"""
        now = datetime.now()
        current_time = now.strftime("%H:%M")

        for periodo in self.config["horarios_alta_vigilancia"]:
            inicio = periodo["inicio"]
            fim = periodo["fim"]

            # Periodo que cruza meia-noite
            if inicio > fim:
                if current_time >= inicio or current_time < fim:
                    return True
            else:
                if inicio <= current_time < fim:
                    return True

        return False

    async def _create_alert(
        self,
        event: DetectionEvent,
        severity: AlertSeverity,
        descricao: str
    ) -> Alert:
        """Cria e registra um novo alerta"""
        alert_id = f"alert_{datetime.now().timestamp()}"

        # Gerar sugestoes de acao
        acoes = await self._generate_action_suggestions(event, severity)

        alert = Alert(
            id=alert_id,
            tipo=event.tipo,
            severidade=severity,
            camera_id=event.camera_id,
            timestamp=datetime.now(),
            descricao=descricao,
            eventos=[event.id],
            acoes_sugeridas=acoes,
        )

        self._alertas_ativos[alert_id] = alert
        self._metricas["alertas_gerados"] += 1

        # Notificar callbacks
        for callback in self._on_alert_callbacks:
            try:
                await callback(alert)
            except Exception as e:
                logger.error(f"Erro em callback de alerta: {e}")

        # Enviar para message bus
        if self.message_bus:
            await self._broadcast_alert(alert)

        logger.info(f"Alerta gerado: {alert_id} - {severity.name} - {descricao}")

        return alert

    async def _generate_action_suggestions(
        self,
        event: DetectionEvent,
        severity: AlertSeverity
    ) -> List[str]:
        """Gera sugestoes de acao baseado no evento"""
        acoes = []

        if severity == AlertSeverity.CRITICA:
            acoes.extend([
                "Acionar seguranca imediatamente",
                "Verificar cameras adjacentes",
                "Preparar para acionamento de autoridades",
                "Bloquear acessos automaticos",
            ])
        elif severity == AlertSeverity.ALTA:
            acoes.extend([
                "Notificar equipe de seguranca",
                "Verificar camera em tempo real",
                "Revisar ultimos minutos de gravacao",
            ])
        elif severity == AlertSeverity.MEDIA:
            acoes.extend([
                "Monitorar situacao",
                "Verificar se ha padrao recorrente",
            ])
        else:
            acoes.append("Apenas registrar para analise posterior")

        # Acoes especificas por tipo
        if event.tipo == AlertType.OBJETO_ABANDONADO:
            acoes.insert(0, "Verificar objeto abandonado - possivel ameaca")

        if event.tipo == AlertType.CERCA_VIRTUAL:
            acoes.insert(0, "Verificar invasao de perimetro")

        return acoes

    async def _broadcast_alert(self, alert: Alert) -> None:
        """Envia alerta para outros agentes via message bus"""
        if not self.message_bus:
            return

        message = BusMessage(
            message_id=f"msg_{alert.id}",
            sender_id=self.agent_id,
            sender_type=self.agent_type,
            receiver_id="*",  # Broadcast
            content={
                "alert_id": alert.id,
                "tipo": alert.tipo.value,
                "severidade": alert.severidade.value,
                "camera_id": alert.camera_id,
                "descricao": alert.descricao,
                "acoes_sugeridas": alert.acoes_sugeridas,
            },
            message_type=MessageType.EVENT,
            priority=MessagePriority(alert.severidade.value),
        )

        await self.message_bus.publish(message)

    async def _list_alerts(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Lista alertas com filtros"""
        alerts = list(self._alertas_ativos.values())

        # Aplicar filtros
        if "severidade_minima" in filters:
            min_sev = filters["severidade_minima"]
            alerts = [a for a in alerts if a.severidade.value >= min_sev]

        if "camera_id" in filters:
            alerts = [a for a in alerts if a.camera_id == filters["camera_id"]]

        if "tipo" in filters:
            alerts = [a for a in alerts if a.tipo.value == filters["tipo"]]

        if "nao_reconhecidos" in filters and filters["nao_reconhecidos"]:
            alerts = [a for a in alerts if not a.reconhecido]

        return {
            "total": len(alerts),
            "alertas": [
                {
                    "id": a.id,
                    "tipo": a.tipo.value,
                    "severidade": a.severidade.value,
                    "camera_id": a.camera_id,
                    "descricao": a.descricao,
                    "timestamp": a.timestamp.isoformat(),
                    "reconhecido": a.reconhecido,
                    "acoes_sugeridas": a.acoes_sugeridas,
                }
                for a in alerts
            ]
        }

    async def _acknowledge_alert(
        self, alert_id: str, user_id: str
    ) -> Dict[str, Any]:
        """Reconhece um alerta"""
        if alert_id not in self._alertas_ativos:
            return {"success": False, "error": "Alerta nao encontrado"}

        alert = self._alertas_ativos[alert_id]
        alert.reconhecido = True
        alert.reconhecido_por = user_id

        logger.info(f"Alerta {alert_id} reconhecido por {user_id}")

        return {
            "success": True,
            "alert_id": alert_id,
            "reconhecido_por": user_id,
        }

    async def _analyze_camera(self, camera_id: str) -> Dict[str, Any]:
        """Analisa status e eventos de uma camera"""
        if camera_id not in self._cameras:
            return {"error": "Camera nao encontrada"}

        camera = self._cameras[camera_id]

        # Buscar eventos recentes
        eventos_recentes = [
            e for e in self._eventos_pendentes
            if e.camera_id == camera_id
        ][-10:]

        # Buscar alertas da camera
        alertas_camera = [
            a for a in self._alertas_ativos.values()
            if a.camera_id == camera_id
        ]

        return {
            "camera": {
                "id": camera.camera_id,
                "nome": camera.nome,
                "status": camera.status,
                "deteccao_ativa": camera.deteccao_ativa,
                "gravacao_ativa": camera.gravacao_ativa,
            },
            "eventos_recentes": len(eventos_recentes),
            "alertas_ativos": len(alertas_camera),
            "ultimo_evento": camera.ultimo_evento.isoformat() if camera.ultimo_evento else None,
        }

    async def _get_security_recommendations(self) -> Dict[str, Any]:
        """Gera recomendacoes de seguranca baseado na analise"""
        recommendations = []

        # Analisar cameras offline
        cameras_offline = [c for c in self._cameras.values() if c.status != "online"]
        if cameras_offline:
            recommendations.append({
                "tipo": "manutencao",
                "prioridade": "alta",
                "descricao": f"{len(cameras_offline)} camera(s) offline - verificar conexao",
                "cameras": [c.camera_id for c in cameras_offline],
            })

        # Analisar alertas nao reconhecidos
        alertas_pendentes = [
            a for a in self._alertas_ativos.values()
            if not a.reconhecido
        ]
        if len(alertas_pendentes) > 5:
            recommendations.append({
                "tipo": "operacional",
                "prioridade": "media",
                "descricao": f"{len(alertas_pendentes)} alertas aguardando reconhecimento",
            })

        # Analisar padroes de eventos
        if self._metricas["eventos_processados"] > 0:
            taxa_alertas = (
                self._metricas["alertas_gerados"] /
                self._metricas["eventos_processados"]
            )
            if taxa_alertas > 0.3:
                recommendations.append({
                    "tipo": "configuracao",
                    "prioridade": "baixa",
                    "descricao": "Alta taxa de alertas - considere ajustar sensibilidade",
                })

        return {
            "total": len(recommendations),
            "recomendacoes": recommendations,
            "timestamp": datetime.now().isoformat(),
        }

    def on_alert(self, callback: Callable) -> None:
        """Registra callback para novos alertas"""
        self._on_alert_callbacks.append(callback)

    async def start_monitoring(self) -> None:
        """Inicia loop de monitoramento"""
        self._is_running = True
        logger.info(f"Monitoramento iniciado para {self.agent_id}")

        while self._is_running:
            try:
                # Processar eventos pendentes
                await self._process_pending_events()

                # Verificar cameras
                await self._check_cameras_health()

                # Limpar eventos antigos
                await self._cleanup_old_events()

                await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Erro no loop de monitoramento: {e}")
                await asyncio.sleep(5)

    async def stop_monitoring(self) -> None:
        """Para o monitoramento"""
        self._is_running = False
        logger.info(f"Monitoramento parado para {self.agent_id}")

    async def _process_pending_events(self) -> None:
        """Processa eventos pendentes no buffer"""
        eventos_para_processar = [
            e for e in self._eventos_pendentes if not e.processado
        ]

        for evento in eventos_para_processar[:10]:  # Processar em lotes
            await self._process_detection_event({
                "id": evento.id,
                "camera": evento.camera_id,
                "score": evento.confianca,
                "labels": evento.objetos,
            })
            evento.processado = True

    async def _check_cameras_health(self) -> None:
        """Verifica saude das cameras"""
        for camera_id, camera in self._cameras.items():
            if camera.ultimo_evento:
                tempo_sem_evento = datetime.now() - camera.ultimo_evento
                if tempo_sem_evento > timedelta(minutes=5):
                    # Camera pode estar com problema
                    if camera.status == "online":
                        camera.status = "warning"
                        logger.warning(f"Camera {camera_id} sem eventos ha 5 minutos")

    async def _cleanup_old_events(self) -> None:
        """Remove eventos antigos do buffer"""
        max_eventos = self.config["max_eventos_buffer"]
        if len(self._eventos_pendentes) > max_eventos:
            self._eventos_pendentes = self._eventos_pendentes[-max_eventos:]
