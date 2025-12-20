"""
Conecta Plus - Guardian Access Agent
Agente de Controle de Acesso Inteligente (Nivel 7)

Responsabilidades:
- Validar identidades (face, placa, credencial)
- Tomar decisoes de acesso em tempo real
- Detectar tentativas de fraude
- Aprender padroes de acesso normais
- Integrar com dispositivos de acesso

Tecnologias:
- Face recognition com anti-spoofing
- ANPR/LPR para placas brasileiras
- Anomaly detection para acessos suspeitos
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
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


class AccessDecision(Enum):
    """Decisao de acesso"""
    AUTORIZADO = "autorizado"
    NEGADO = "negado"
    PENDENTE = "pendente"
    MANUAL = "manual"  # Requer verificacao manual


class CredentialType(Enum):
    """Tipo de credencial"""
    FACE = "face"
    PLACA = "placa"
    CARTAO = "cartao"
    QR_CODE = "qr_code"
    BIOMETRIA = "biometria"
    SENHA = "senha"


class PersonType(Enum):
    """Tipo de pessoa"""
    MORADOR = "morador"
    DEPENDENTE = "dependente"
    FUNCIONARIO = "funcionario"
    VISITANTE = "visitante"
    PRESTADOR = "prestador"
    ENTREGADOR = "entregador"
    DESCONHECIDO = "desconhecido"


class FraudIndicator(Enum):
    """Indicadores de fraude"""
    NONE = "none"
    SPOOFING_FACE = "spoofing_face"
    PLACA_CLONADA = "placa_clonada"
    CARTAO_CLONADO = "cartao_clonado"
    HORARIO_ANOMALO = "horario_anomalo"
    FREQUENCIA_ANOMALA = "frequencia_anomala"
    LOCALIZACAO_ANOMALA = "localizacao_anomala"


@dataclass
class AccessRequest:
    """Solicitacao de acesso"""
    id: str
    ponto_acesso: str
    tipo_credencial: CredentialType
    credencial: str
    timestamp: datetime
    imagem_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AccessResult:
    """Resultado da analise de acesso"""
    request_id: str
    decisao: AccessDecision
    pessoa_id: Optional[str] = None
    pessoa_nome: Optional[str] = None
    tipo_pessoa: PersonType = PersonType.DESCONHECIDO
    confianca: float = 0.0
    indicadores_fraude: List[FraudIndicator] = field(default_factory=list)
    motivo: str = ""
    acoes_recomendadas: List[str] = field(default_factory=list)
    tempo_processamento_ms: int = 0


@dataclass
class AccessPattern:
    """Padrao de acesso aprendido"""
    pessoa_id: str
    ponto_acesso: str
    horario_medio: str
    dias_semana: List[int]
    frequencia_semanal: float
    ultima_atualizacao: datetime


class GuardianAccessAgent(BaseAgent):
    """
    Agente de Controle de Acesso Inteligente - Nivel 7

    Capacidades:
    1. REATIVO: Validar credenciais
    2. PROATIVO: Detectar anomalias de acesso
    3. PREDITIVO: Prever acessos legitimos
    4. AUTONOMO: Tomar decisoes automaticas
    5. EVOLUTIVO: Aprender padroes de acesso
    6. COLABORATIVO: Integrar com portaria e CFTV
    7. TRANSCENDENTE: Seguranca adaptativa
    """

    def __init__(
        self,
        condominio_id: str,
        llm_client: Any = None,
        memory: Any = None,
        message_bus: MessageBus = None,
        face_service: Any = None,
        lpr_service: Any = None,
        evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT,
    ):
        super().__init__(
            agent_id=f"guardian_access_{condominio_id}",
            agent_type="guardian_access",
            condominio_id=condominio_id,
            evolution_level=evolution_level,
            llm_client=llm_client,
            memory_store=memory,
        )

        self.message_bus = message_bus
        self.face_service = face_service
        self.lpr_service = lpr_service

        # Banco de dados em memoria
        self._pessoas_autorizadas: Dict[str, Dict] = {}
        self._placas_autorizadas: Dict[str, Dict] = {}
        self._faces_conhecidas: Dict[str, Dict] = {}
        self._padroes_acesso: Dict[str, AccessPattern] = {}

        # Historico
        self._acessos_recentes: List[AccessResult] = []
        self._tentativas_fraude: List[Dict] = []

        # Configuracoes
        self.config = {
            "confianca_minima_face": 0.85,
            "confianca_minima_placa": 0.90,
            "anti_spoofing_ativo": True,
            "verificacao_liveness": True,
            "modo_alta_seguranca": False,
            "permitir_acesso_visitante_auto": False,
            "horario_comercial_inicio": "06:00",
            "horario_comercial_fim": "22:00",
            "max_tentativas_falhas": 3,
            "tempo_bloqueio_minutos": 30,
        }

        # Contadores de tentativas falhas
        self._falhas_por_pessoa: Dict[str, List[datetime]] = defaultdict(list)

        logger.info(f"GuardianAccessAgent inicializado para condominio {condominio_id}")

    def _register_capabilities(self) -> None:
        """Registra capacidades do agente"""
        self._capabilities["validate_credentials"] = AgentCapability(
            name="validate_credentials",
            description="Validar credenciais de acesso",
            level=EvolutionLevel.REACTIVE
        )
        self._capabilities["detect_anomalies"] = AgentCapability(
            name="detect_anomalies",
            description="Detectar anomalias de acesso",
            level=EvolutionLevel.PROACTIVE
        )
        self._capabilities["predict_legitimate"] = AgentCapability(
            name="predict_legitimate",
            description="Prever acessos legitimos",
            level=EvolutionLevel.PREDICTIVE
        )
        self._capabilities["auto_decision"] = AgentCapability(
            name="auto_decision",
            description="Tomar decisoes automaticas",
            level=EvolutionLevel.AUTONOMOUS
        )
        self._capabilities["learn_patterns"] = AgentCapability(
            name="learn_patterns",
            description="Aprender padroes de acesso",
            level=EvolutionLevel.EVOLUTIONARY
        )
        self._capabilities["integrate_systems"] = AgentCapability(
            name="integrate_systems",
            description="Integrar com outros sistemas",
            level=EvolutionLevel.COLLABORATIVE
        )

    def get_system_prompt(self) -> str:
        """Retorna o system prompt do agente"""
        return f"""Voce e o Agente de Controle de Acesso Guardian do Conecta Plus.
ID: {self.agent_id}
Condominio: {self.condominio_id}
Nivel de Evolucao: {self.evolution_level.name}

Responsabilidades:
1. Validar identidades (face, placa, cartao)
2. Tomar decisoes de acesso em tempo real
3. Detectar tentativas de fraude
4. Aprender padroes de acesso normais
5. Integrar com portaria e cameras

Configuracoes:
- Confianca minima face: {self.config['confianca_minima_face']}
- Confianca minima placa: {self.config['confianca_minima_placa']}
- Anti-spoofing: {self.config['anti_spoofing_ativo']}
- Modo alta seguranca: {self.config['modo_alta_seguranca']}

Pessoas autorizadas: {len(self._pessoas_autorizadas)}
Placas autorizadas: {len(self._placas_autorizadas)}
"""

    async def process(self, input_data: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        """Processa entrada e retorna resultado"""
        action = input_data.get("action", "status")

        if action == "status":
            return await self._get_status()
        elif action == "validate_access":
            return await self._validate_access(input_data)
        elif action == "register_person":
            return await self._register_person(input_data)
        elif action == "register_plate":
            return await self._register_plate(input_data)
        elif action == "get_access_history":
            return await self._get_access_history(input_data.get("filters", {}))
        elif action == "analyze_patterns":
            return await self._analyze_access_patterns()
        elif action == "get_fraud_alerts":
            return await self._get_fraud_alerts()
        else:
            return {"error": f"Acao desconhecida: {action}"}

    async def _get_status(self) -> Dict[str, Any]:
        """Retorna status do agente"""
        return {
            "agent_id": self.agent_id,
            "status": "active",
            "pessoas_autorizadas": len(self._pessoas_autorizadas),
            "placas_autorizadas": len(self._placas_autorizadas),
            "faces_cadastradas": len(self._faces_conhecidas),
            "acessos_hoje": self._count_today_accesses(),
            "tentativas_fraude": len(self._tentativas_fraude),
            "config": self.config,
        }

    async def _validate_access(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Valida solicitacao de acesso"""
        start_time = datetime.now()

        request = AccessRequest(
            id=data.get("id", f"req_{datetime.now().timestamp()}"),
            ponto_acesso=data.get("ponto_acesso", ""),
            tipo_credencial=CredentialType(data.get("tipo_credencial", "cartao")),
            credencial=data.get("credencial", ""),
            timestamp=datetime.now(),
            imagem_url=data.get("imagem_url"),
            metadata=data.get("metadata", {}),
        )

        # Processar baseado no tipo de credencial
        if request.tipo_credencial == CredentialType.FACE:
            result = await self._validate_face_access(request)
        elif request.tipo_credencial == CredentialType.PLACA:
            result = await self._validate_plate_access(request)
        elif request.tipo_credencial == CredentialType.CARTAO:
            result = await self._validate_card_access(request)
        else:
            result = AccessResult(
                request_id=request.id,
                decisao=AccessDecision.NEGADO,
                motivo="Tipo de credencial nao suportado",
            )

        # Calcular tempo de processamento
        result.tempo_processamento_ms = int(
            (datetime.now() - start_time).total_seconds() * 1000
        )

        # Registrar acesso
        self._acessos_recentes.append(result)

        # Aprender padrao se autorizado
        if result.decisao == AccessDecision.AUTORIZADO and result.pessoa_id:
            await self._learn_access_pattern(result, request)

        # Notificar outros agentes se fraude detectada
        if result.indicadores_fraude:
            await self._notify_fraud_detected(result, request)

        return {
            "request_id": result.request_id,
            "decisao": result.decisao.value,
            "pessoa": {
                "id": result.pessoa_id,
                "nome": result.pessoa_nome,
                "tipo": result.tipo_pessoa.value,
            } if result.pessoa_id else None,
            "confianca": result.confianca,
            "motivo": result.motivo,
            "fraude_detectada": len(result.indicadores_fraude) > 0,
            "indicadores_fraude": [i.value for i in result.indicadores_fraude],
            "acoes_recomendadas": result.acoes_recomendadas,
            "tempo_processamento_ms": result.tempo_processamento_ms,
        }

    async def _validate_face_access(self, request: AccessRequest) -> AccessResult:
        """Valida acesso por reconhecimento facial"""
        indicadores_fraude = []

        # Verificar anti-spoofing
        if self.config["anti_spoofing_ativo"]:
            is_real, spoofing_score = await self._check_anti_spoofing(request.imagem_url)
            if not is_real:
                indicadores_fraude.append(FraudIndicator.SPOOFING_FACE)
                self._tentativas_fraude.append({
                    "tipo": "spoofing_face",
                    "ponto_acesso": request.ponto_acesso,
                    "timestamp": datetime.now().isoformat(),
                    "score": spoofing_score,
                })
                return AccessResult(
                    request_id=request.id,
                    decisao=AccessDecision.NEGADO,
                    indicadores_fraude=indicadores_fraude,
                    motivo="Tentativa de spoofing facial detectada",
                    acoes_recomendadas=[
                        "Verificar camera",
                        "Alertar seguranca",
                        "Registrar tentativa de fraude",
                    ],
                )

        # Buscar face no banco
        match_result = await self._match_face(request.credencial)

        if not match_result:
            return AccessResult(
                request_id=request.id,
                decisao=AccessDecision.MANUAL,
                tipo_pessoa=PersonType.DESCONHECIDO,
                motivo="Face nao reconhecida",
                acoes_recomendadas=["Solicitar identificacao manual"],
            )

        pessoa_id = match_result["pessoa_id"]
        confianca = match_result["confianca"]

        # Verificar confianca minima
        if confianca < self.config["confianca_minima_face"]:
            return AccessResult(
                request_id=request.id,
                decisao=AccessDecision.MANUAL,
                pessoa_id=pessoa_id,
                pessoa_nome=match_result.get("nome"),
                tipo_pessoa=PersonType(match_result.get("tipo", "morador")),
                confianca=confianca,
                motivo=f"Confianca baixa ({confianca:.2%})",
                acoes_recomendadas=["Solicitar confirmacao adicional"],
            )

        # Verificar anomalias de acesso
        anomalias = await self._check_access_anomalies(pessoa_id, request)
        indicadores_fraude.extend(anomalias)

        # Verificar se esta bloqueado
        if self._is_blocked(pessoa_id):
            return AccessResult(
                request_id=request.id,
                decisao=AccessDecision.NEGADO,
                pessoa_id=pessoa_id,
                pessoa_nome=match_result.get("nome"),
                confianca=confianca,
                motivo="Acesso temporariamente bloqueado",
            )

        return AccessResult(
            request_id=request.id,
            decisao=AccessDecision.AUTORIZADO,
            pessoa_id=pessoa_id,
            pessoa_nome=match_result.get("nome"),
            tipo_pessoa=PersonType(match_result.get("tipo", "morador")),
            confianca=confianca,
            indicadores_fraude=indicadores_fraude,
            motivo="Acesso autorizado por reconhecimento facial",
        )

    async def _validate_plate_access(self, request: AccessRequest) -> AccessResult:
        """Valida acesso por placa de veiculo"""
        placa = request.credencial.upper().replace("-", "").replace(" ", "")

        # Buscar placa no banco
        if placa not in self._placas_autorizadas:
            return AccessResult(
                request_id=request.id,
                decisao=AccessDecision.MANUAL,
                motivo=f"Placa {placa} nao cadastrada",
                acoes_recomendadas=["Verificar com portaria"],
            )

        placa_info = self._placas_autorizadas[placa]
        pessoa_id = placa_info.get("pessoa_id")

        # Verificar anomalias
        indicadores_fraude = []
        anomalias = await self._check_access_anomalies(pessoa_id, request)
        indicadores_fraude.extend(anomalias)

        # Verificar se placa pode estar clonada
        if await self._check_cloned_plate(placa, request):
            indicadores_fraude.append(FraudIndicator.PLACA_CLONADA)
            return AccessResult(
                request_id=request.id,
                decisao=AccessDecision.MANUAL,
                pessoa_id=pessoa_id,
                indicadores_fraude=indicadores_fraude,
                motivo="Possivel placa clonada - verificacao necessaria",
                acoes_recomendadas=[
                    "Verificar veiculo visualmente",
                    "Confirmar com proprietario",
                ],
            )

        return AccessResult(
            request_id=request.id,
            decisao=AccessDecision.AUTORIZADO,
            pessoa_id=pessoa_id,
            pessoa_nome=placa_info.get("proprietario"),
            tipo_pessoa=PersonType(placa_info.get("tipo_pessoa", "morador")),
            confianca=0.95,
            indicadores_fraude=indicadores_fraude,
            motivo=f"Placa {placa} autorizada",
        )

    async def _validate_card_access(self, request: AccessRequest) -> AccessResult:
        """Valida acesso por cartao"""
        cartao_id = request.credencial

        # Buscar cartao no banco
        for pessoa_id, pessoa in self._pessoas_autorizadas.items():
            if pessoa.get("cartao_id") == cartao_id:
                # Verificar anomalias
                anomalias = await self._check_access_anomalies(pessoa_id, request)

                return AccessResult(
                    request_id=request.id,
                    decisao=AccessDecision.AUTORIZADO,
                    pessoa_id=pessoa_id,
                    pessoa_nome=pessoa.get("nome"),
                    tipo_pessoa=PersonType(pessoa.get("tipo", "morador")),
                    confianca=1.0,
                    indicadores_fraude=anomalias,
                    motivo="Cartao autorizado",
                )

        return AccessResult(
            request_id=request.id,
            decisao=AccessDecision.NEGADO,
            motivo="Cartao nao reconhecido",
        )

    async def _check_anti_spoofing(self, imagem_url: str) -> Tuple[bool, float]:
        """Verifica se imagem e real (anti-spoofing)"""
        # Simulacao - em producao usar servico de liveness detection
        # Verificaria: movimento, textura, profundidade, reflexos
        return True, 0.95

    async def _match_face(self, face_embedding: str) -> Optional[Dict]:
        """Busca correspondencia de face no banco"""
        # Simulacao - em producao usar servico de face matching
        # Compararia embedding com banco de faces conhecidas
        if face_embedding in self._faces_conhecidas:
            return self._faces_conhecidas[face_embedding]
        return None

    async def _check_access_anomalies(
        self, pessoa_id: str, request: AccessRequest
    ) -> List[FraudIndicator]:
        """Verifica anomalias no padrao de acesso"""
        anomalias = []

        if pessoa_id not in self._padroes_acesso:
            return anomalias

        padrao = self._padroes_acesso[pessoa_id]
        hora_atual = datetime.now().hour
        dia_atual = datetime.now().weekday()

        # Verificar horario anomalo
        horario_padrao = int(padrao.horario_medio.split(":")[0])
        if abs(hora_atual - horario_padrao) > 6:  # Mais de 6 horas de diferenca
            if not self._is_business_hours():
                anomalias.append(FraudIndicator.HORARIO_ANOMALO)

        # Verificar frequencia anomala
        acessos_hoje = sum(
            1 for a in self._acessos_recentes
            if a.pessoa_id == pessoa_id and
            a.decisao == AccessDecision.AUTORIZADO and
            datetime.now().date() == datetime.now().date()
        )
        if acessos_hoje > padrao.frequencia_semanal * 2:
            anomalias.append(FraudIndicator.FREQUENCIA_ANOMALA)

        return anomalias

    async def _check_cloned_plate(self, placa: str, request: AccessRequest) -> bool:
        """Verifica se placa pode estar clonada"""
        # Verificar se placa foi vista em local diferente recentemente
        acessos_placa = [
            a for a in self._acessos_recentes
            if a.pessoa_id and
            self._placas_autorizadas.get(placa, {}).get("pessoa_id") == a.pessoa_id
        ]

        if not acessos_placa:
            return False

        ultimo_acesso = acessos_placa[-1]
        tempo_desde_ultimo = (datetime.now() - datetime.now()).total_seconds()

        # Se acesso muito rapido de pontos distantes, pode ser clone
        # Logica simplificada - em producao verificaria geolocalizacao
        return False

    def _is_blocked(self, pessoa_id: str) -> bool:
        """Verifica se pessoa esta bloqueada por muitas falhas"""
        falhas = self._falhas_por_pessoa.get(pessoa_id, [])

        # Limpar falhas antigas
        tempo_bloqueio = timedelta(minutes=self.config["tempo_bloqueio_minutos"])
        falhas_recentes = [f for f in falhas if datetime.now() - f < tempo_bloqueio]
        self._falhas_por_pessoa[pessoa_id] = falhas_recentes

        return len(falhas_recentes) >= self.config["max_tentativas_falhas"]

    def _is_business_hours(self) -> bool:
        """Verifica se esta em horario comercial"""
        hora_atual = datetime.now().strftime("%H:%M")
        return (
            self.config["horario_comercial_inicio"] <=
            hora_atual <=
            self.config["horario_comercial_fim"]
        )

    async def _learn_access_pattern(
        self, result: AccessResult, request: AccessRequest
    ) -> None:
        """Aprende padrao de acesso"""
        pessoa_id = result.pessoa_id
        if not pessoa_id:
            return

        hora_atual = datetime.now().strftime("%H:%M")
        dia_atual = datetime.now().weekday()

        if pessoa_id in self._padroes_acesso:
            padrao = self._padroes_acesso[pessoa_id]
            # Atualizar padrao existente
            if dia_atual not in padrao.dias_semana:
                padrao.dias_semana.append(dia_atual)
            padrao.ultima_atualizacao = datetime.now()
        else:
            # Criar novo padrao
            self._padroes_acesso[pessoa_id] = AccessPattern(
                pessoa_id=pessoa_id,
                ponto_acesso=request.ponto_acesso,
                horario_medio=hora_atual,
                dias_semana=[dia_atual],
                frequencia_semanal=1.0,
                ultima_atualizacao=datetime.now(),
            )

    async def _notify_fraud_detected(
        self, result: AccessResult, request: AccessRequest
    ) -> None:
        """Notifica fraude detectada para outros agentes"""
        if not self.message_bus:
            return

        message = BusMessage(
            message_id=f"fraud_{datetime.now().timestamp()}",
            sender_id=self.agent_id,
            sender_type=self.agent_type,
            receiver_id="*",
            content={
                "tipo": "fraude_detectada",
                "request_id": result.request_id,
                "ponto_acesso": request.ponto_acesso,
                "indicadores": [i.value for i in result.indicadores_fraude],
                "acoes_recomendadas": result.acoes_recomendadas,
            },
            message_type=MessageType.EVENT,
            priority=MessagePriority.URGENT,
        )

        await self.message_bus.publish(message)

    async def _register_person(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Registra nova pessoa autorizada"""
        pessoa_id = data.get("id", f"pessoa_{datetime.now().timestamp()}")

        self._pessoas_autorizadas[pessoa_id] = {
            "nome": data.get("nome"),
            "tipo": data.get("tipo", "morador"),
            "unidade": data.get("unidade"),
            "cartao_id": data.get("cartao_id"),
            "ativo": True,
            "criado_em": datetime.now().isoformat(),
        }

        # Registrar face se fornecida
        if data.get("face_embedding"):
            self._faces_conhecidas[data["face_embedding"]] = {
                "pessoa_id": pessoa_id,
                "nome": data.get("nome"),
                "tipo": data.get("tipo", "morador"),
            }

        return {"success": True, "pessoa_id": pessoa_id}

    async def _register_plate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Registra nova placa autorizada"""
        placa = data.get("placa", "").upper().replace("-", "")

        self._placas_autorizadas[placa] = {
            "pessoa_id": data.get("pessoa_id"),
            "proprietario": data.get("proprietario"),
            "tipo_pessoa": data.get("tipo_pessoa", "morador"),
            "modelo_veiculo": data.get("modelo"),
            "cor_veiculo": data.get("cor"),
            "ativo": True,
            "criado_em": datetime.now().isoformat(),
        }

        return {"success": True, "placa": placa}

    async def _get_access_history(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Retorna historico de acessos"""
        acessos = self._acessos_recentes

        # Aplicar filtros
        if "pessoa_id" in filters:
            acessos = [a for a in acessos if a.pessoa_id == filters["pessoa_id"]]

        if "decisao" in filters:
            acessos = [a for a in acessos if a.decisao.value == filters["decisao"]]

        return {
            "total": len(acessos),
            "acessos": [
                {
                    "request_id": a.request_id,
                    "pessoa_id": a.pessoa_id,
                    "pessoa_nome": a.pessoa_nome,
                    "decisao": a.decisao.value,
                    "confianca": a.confianca,
                    "motivo": a.motivo,
                }
                for a in acessos[-100:]  # Ultimos 100
            ]
        }

    async def _analyze_access_patterns(self) -> Dict[str, Any]:
        """Analisa padroes de acesso"""
        return {
            "total_padroes": len(self._padroes_acesso),
            "padroes": [
                {
                    "pessoa_id": p.pessoa_id,
                    "horario_medio": p.horario_medio,
                    "dias_semana": p.dias_semana,
                    "frequencia_semanal": p.frequencia_semanal,
                }
                for p in list(self._padroes_acesso.values())[:20]
            ]
        }

    async def _get_fraud_alerts(self) -> Dict[str, Any]:
        """Retorna alertas de fraude"""
        return {
            "total": len(self._tentativas_fraude),
            "alertas": self._tentativas_fraude[-50:],
        }

    def _count_today_accesses(self) -> int:
        """Conta acessos de hoje"""
        hoje = datetime.now().date()
        return sum(
            1 for a in self._acessos_recentes
            if a.decisao == AccessDecision.AUTORIZADO
        )
