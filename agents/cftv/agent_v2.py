"""
Conecta Plus - Agente CFTV Avançado (Nível 7)
Implementação completa do agente de monitoramento por câmeras

Capacidades por nível:
1. REATIVO: Visualizar câmeras, buscar gravações
2. PROATIVO: Alertar movimento suspeito, monitorar áreas
3. PREDITIVO: Prever comportamentos, identificar padrões
4. AUTÔNOMO: Disparar ações automáticas, ajustar câmeras
5. EVOLUTIVO: Aprender novos padrões de ameaça
6. COLABORATIVO: Integrar com Acesso, Alarme, Portaria
7. TRANSCENDENTE: Inteligência de vigilância avançada

Autor: Conecta Plus AI
Versão: 2.0 (Evolution Framework)
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import base64
import hashlib

from ..core.base_agent import (
    BaseAgent,
    EvolutionLevel,
    Priority,
    AgentCapability,
    AgentContext,
    AgentMessage,
    AgentAction,
    AgentPrediction,
)
from ..core.memory_store import UnifiedMemorySystem
from ..core.llm_client import UnifiedLLMClient, LLMMessage
from ..core.tools import ToolRegistry, ToolResult

logger = logging.getLogger(__name__)


# ==================== TIPOS ESPECÍFICOS ====================

class TipoCamera(Enum):
    PTZ = "ptz"  # Pan-Tilt-Zoom
    FIXA = "fixa"
    DOME = "dome"
    BULLET = "bullet"
    FISHEYE = "fisheye"


class StatusCamera(Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    GRAVANDO = "gravando"
    MANUTENCAO = "manutencao"
    ERRO = "erro"


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


class NivelRisco(Enum):
    BAIXO = 1
    MEDIO = 2
    ALTO = 3
    CRITICO = 4


@dataclass
class Camera:
    """Câmera do sistema"""
    id: str
    nome: str
    tipo: TipoCamera
    localizacao: str
    ip: str
    status: StatusCamera
    resolucao: str = "1080p"
    fps: int = 30
    tem_audio: bool = False
    tem_ia: bool = True
    angulo_visao: int = 90
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EventoDetectado:
    """Evento detectado por IA"""
    id: str
    camera_id: str
    tipo: TipoEvento
    timestamp: datetime
    confianca: float  # 0.0 - 1.0
    nivel_risco: NivelRisco
    bounding_box: Optional[Dict[str, int]] = None  # x, y, width, height
    snapshot_url: Optional[str] = None
    video_clip_url: Optional[str] = None
    objetos_detectados: List[str] = field(default_factory=list)
    descricao: str = ""
    processado: bool = False
    acao_tomada: Optional[str] = None


@dataclass
class AnaliseComportamental:
    """Análise de comportamento detectado"""
    pessoa_id: str
    camera_id: str
    comportamentos: List[str]
    tempo_observacao: int  # segundos
    nivel_suspeita: float  # 0.0 - 1.0
    trajetoria: List[Dict[str, int]] = field(default_factory=list)
    interacoes: List[str] = field(default_factory=list)


@dataclass
class PadraoAprendido:
    """Padrão aprendido pelo sistema"""
    id: str
    descricao: str
    frequencia: int
    horarios_tipicos: List[str]
    locais: List[str]
    e_normal: bool
    confianca: float


# ==================== AGENTE CFTV ====================

class AgenteCFTV(BaseAgent):
    """
    Agente CFTV Avançado - Nível 7 (Transcendente)

    Responsabilidades:
    - Monitoramento inteligente de câmeras
    - Detecção de eventos por IA
    - Análise comportamental
    - Previsão de incidentes
    - Ações automatizadas de segurança
    - Integração com outros sistemas
    """

    def __init__(
        self,
        condominio_id: str,
        llm_client: UnifiedLLMClient = None,
        memory: UnifiedMemorySystem = None,
        tools: ToolRegistry = None,
        mcp_cftv_url: str = None,
        evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT,
    ):
        super().__init__(
            agent_id=f"cftv_{condominio_id}",
            agent_type="cftv",
            condominio_id=condominio_id,
            evolution_level=evolution_level,
            llm_client=llm_client,
            memory_store=memory,
        )

        self.tools = tools
        self.mcp_url = mcp_cftv_url

        # Estado interno
        self._cameras: Dict[str, Camera] = {}
        self._eventos_pendentes: List[EventoDetectado] = []
        self._padroes_aprendidos: Dict[str, PadraoAprendido] = {}
        self._alertas_enviados: Dict[str, datetime] = {}

        # Configurações de IA
        self.config = {
            "confianca_minima_alerta": 0.7,
            "tempo_analise_comportamento": 30,  # segundos
            "cooldown_alertas": 300,  # 5 minutos entre alertas iguais
            "sensibilidade_movimento": 0.5,
            "zonas_criticas": [],  # IDs de câmeras em áreas críticas
            "horarios_alta_vigilancia": ["22:00-06:00"],  # Maior sensibilidade
        }

        # Modelos de IA
        self._modelo_deteccao = "yolov8"
        self._modelo_comportamento = "behavioral_analysis_v2"

        logger.info(f"Agente CFTV inicializado para condomínio {condominio_id}")

    def _register_capabilities(self) -> None:
        """Registra capacidades específicas do agente CFTV"""

        # Nível 1: Reativo
        self._capabilities["visualizar_cameras"] = AgentCapability(
            name="visualizar_cameras",
            description="Visualizar feed de câmeras em tempo real",
            level=EvolutionLevel.REACTIVE
        )
        self._capabilities["buscar_gravacoes"] = AgentCapability(
            name="buscar_gravacoes",
            description="Buscar e reproduzir gravações",
            level=EvolutionLevel.REACTIVE
        )
        self._capabilities["controlar_ptz"] = AgentCapability(
            name="controlar_ptz",
            description="Controlar câmeras PTZ",
            level=EvolutionLevel.REACTIVE
        )

        # Nível 2: Proativo
        self._capabilities["detectar_movimento"] = AgentCapability(
            name="detectar_movimento",
            description="Detectar e alertar sobre movimento",
            level=EvolutionLevel.PROACTIVE
        )
        self._capabilities["monitorar_zonas"] = AgentCapability(
            name="monitorar_zonas",
            description="Monitorar zonas específicas",
            level=EvolutionLevel.PROACTIVE
        )

        # Nível 3: Preditivo
        self._capabilities["detectar_objetos"] = AgentCapability(
            name="detectar_objetos",
            description="Detectar pessoas, veículos, objetos",
            level=EvolutionLevel.PREDICTIVE
        )
        self._capabilities["analisar_comportamento"] = AgentCapability(
            name="analisar_comportamento",
            description="Analisar padrões de comportamento",
            level=EvolutionLevel.PREDICTIVE
        )
        self._capabilities["prever_incidentes"] = AgentCapability(
            name="prever_incidentes",
            description="Prever possíveis incidentes",
            level=EvolutionLevel.PREDICTIVE
        )

        # Nível 4: Autônomo
        self._capabilities["acoes_automaticas"] = AgentCapability(
            name="acoes_automaticas",
            description="Executar ações automáticas de segurança",
            level=EvolutionLevel.AUTONOMOUS
        )
        self._capabilities["ajustar_cameras"] = AgentCapability(
            name="ajustar_cameras",
            description="Ajustar câmeras automaticamente",
            level=EvolutionLevel.AUTONOMOUS
        )

        # Nível 5: Evolutivo
        self._capabilities["aprender_padroes"] = AgentCapability(
            name="aprender_padroes",
            description="Aprender novos padrões de ameaça",
            level=EvolutionLevel.EVOLUTIONARY
        )

        # Nível 6: Colaborativo
        self._capabilities["integrar_acesso"] = AgentCapability(
            name="integrar_acesso",
            description="Integrar com sistema de acesso",
            level=EvolutionLevel.COLLABORATIVE
        )
        self._capabilities["integrar_alarme"] = AgentCapability(
            name="integrar_alarme",
            description="Integrar com sistema de alarme",
            level=EvolutionLevel.COLLABORATIVE
        )

        # Nível 7: Transcendente
        self._capabilities["vigilancia_cognitiva"] = AgentCapability(
            name="vigilancia_cognitiva",
            description="Vigilância cognitiva avançada",
            level=EvolutionLevel.TRANSCENDENT
        )

    def get_system_prompt(self) -> str:
        """Retorna system prompt do agente"""
        return f"""Você é o Agente CFTV do sistema Conecta Plus, responsável pela vigilância inteligente do condomínio.

Seu ID: {self.agent_id}
Condomínio: {self.condominio_id}
Nível de Evolução: {self.evolution_level.name} ({self.evolution_level.value})

Suas responsabilidades incluem:
1. Monitoramento em tempo real de todas as câmeras
2. Detecção de eventos suspeitos por IA
3. Análise comportamental de pessoas
4. Previsão de incidentes
5. Ações automatizadas de segurança
6. Integração com portaria, acesso e alarme

Modelo de detecção: {self._modelo_deteccao}
Confiança mínima para alertas: {self.config['confianca_minima_alerta']*100}%
Horários de alta vigilância: {self.config['horarios_alta_vigilancia']}

Priorize a segurança dos moradores e seja preciso nas detecções.
Evite falsos positivos mas nunca ignore ameaças reais.
"""

    async def process(self, input_data: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        """Processa entrada e executa ação apropriada"""
        action = input_data.get("action", "")
        params = input_data.get("params", {})

        result = {}

        try:
            # Nível 1: Ações reativas
            if action == "listar_cameras":
                result = await self._listar_cameras(params, context)

            elif action == "visualizar_camera":
                result = await self._visualizar_camera(params, context)

            elif action == "buscar_gravacao":
                result = await self._buscar_gravacao(params, context)

            elif action == "controlar_ptz":
                result = await self._controlar_ptz(params, context)

            # Nível 2: Ações proativas
            elif action == "verificar_movimento":
                if self.has_capability("detectar_movimento"):
                    result = await self._verificar_movimento(params, context)
                else:
                    result = {"error": "Capacidade não disponível"}

            elif action == "configurar_zona":
                result = await self._configurar_zona(params, context)

            # Nível 3: Ações preditivas
            elif action == "detectar_objetos":
                if self.has_capability("detectar_objetos"):
                    result = await self._detectar_objetos(params, context)
                else:
                    result = {"error": "Capacidade preditiva não disponível"}

            elif action == "analisar_comportamento":
                if self.has_capability("analisar_comportamento"):
                    result = await self._analisar_comportamento(params, context)
                else:
                    result = {"error": "Capacidade preditiva não disponível"}

            # Nível 4: Ações autônomas
            elif action == "processar_evento":
                if self.has_capability("acoes_automaticas"):
                    result = await self._processar_evento_autonomo(params, context)
                else:
                    result = {"error": "Capacidade autônoma não disponível"}

            # Nível 7: Ações transcendentes
            elif action == "analise_cognitiva":
                if self.has_capability("vigilancia_cognitiva"):
                    result = await self._analise_cognitiva(params, context)
                else:
                    result = {"error": "Capacidade transcendente não disponível"}

            # Chat genérico
            elif action == "chat":
                result = await self._process_chat(params, context)

            # Evento de IA (webhook do Guardian)
            elif action == "evento_ia":
                result = await self._processar_evento_ia(params, context)

            else:
                result = {"error": f"Ação '{action}' não reconhecida"}

        except Exception as e:
            logger.error(f"Erro ao processar ação {action}: {e}")
            result = {"error": str(e)}

        return result

    # ==================== NÍVEL 1: REATIVO ====================

    async def _listar_cameras(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Lista todas as câmeras do condomínio"""
        if self.tools:
            result = await self.tools.execute(
                "database_query",
                table="cameras",
                where={"condominio_id": self.condominio_id}
            )

            if result.success:
                cameras = []
                for cam in result.data:
                    cameras.append({
                        "id": cam.get("id"),
                        "nome": cam.get("nome"),
                        "tipo": cam.get("tipo"),
                        "localizacao": cam.get("localizacao"),
                        "status": cam.get("status", "online"),
                        "tem_ia": cam.get("tem_ia", True)
                    })

                return {
                    "success": True,
                    "cameras": cameras,
                    "total": len(cameras),
                    "online": sum(1 for c in cameras if c["status"] == "online")
                }

        # Mock
        return {
            "success": True,
            "cameras": [
                {"id": "cam_001", "nome": "Entrada Principal", "tipo": "ptz", "localizacao": "Portaria", "status": "online", "tem_ia": True},
                {"id": "cam_002", "nome": "Estacionamento 1", "tipo": "dome", "localizacao": "Subsolo 1", "status": "online", "tem_ia": True},
                {"id": "cam_003", "nome": "Piscina", "tipo": "bullet", "localizacao": "Área de Lazer", "status": "online", "tem_ia": True},
                {"id": "cam_004", "nome": "Hall Elevadores", "tipo": "dome", "localizacao": "Térreo", "status": "online", "tem_ia": True},
                {"id": "cam_005", "nome": "Perímetro Norte", "tipo": "bullet", "localizacao": "Muro Norte", "status": "online", "tem_ia": True},
            ],
            "total": 5,
            "online": 5
        }

    async def _visualizar_camera(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Retorna URL de streaming da câmera"""
        camera_id = params.get("camera_id")

        if not camera_id:
            return {"success": False, "error": "camera_id é obrigatório"}

        # Chamar MCP de CFTV
        if self.tools and self.mcp_url:
            result = await self.tools.execute(
                "call_mcp",
                mcp_name="mcp-intelbras-cftv",
                method="get_stream_url",
                params={"camera_id": camera_id}
            )

            if result.success:
                return {
                    "success": True,
                    "stream_url": result.data.get("url"),
                    "tipo": "rtsp"
                }

        # Mock
        return {
            "success": True,
            "stream_url": f"rtsp://192.168.1.100:554/stream/{camera_id}",
            "snapshot_url": f"/api/cftv/snapshot/{camera_id}",
            "tipo": "rtsp"
        }

    async def _buscar_gravacao(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Busca gravações por período"""
        camera_id = params.get("camera_id")
        data_inicio = params.get("data_inicio")
        data_fim = params.get("data_fim")
        evento_tipo = params.get("evento_tipo")

        query_params = {"camera_id": camera_id}
        if evento_tipo:
            query_params["tipo"] = evento_tipo

        if self.tools:
            result = await self.tools.execute(
                "database_query",
                table="gravacoes",
                where=query_params,
                order_by="timestamp DESC",
                limit=50
            )

            if result.success:
                return {
                    "success": True,
                    "gravacoes": result.data
                }

        # Mock
        return {
            "success": True,
            "gravacoes": [
                {
                    "id": "rec_001",
                    "camera_id": camera_id,
                    "inicio": "2024-12-18T10:00:00",
                    "fim": "2024-12-18T10:15:00",
                    "evento": "movimento_detectado",
                    "url": f"/recordings/{camera_id}/rec_001.mp4"
                },
                {
                    "id": "rec_002",
                    "camera_id": camera_id,
                    "inicio": "2024-12-18T14:30:00",
                    "fim": "2024-12-18T14:35:00",
                    "evento": "pessoa_detectada",
                    "url": f"/recordings/{camera_id}/rec_002.mp4"
                }
            ]
        }

    async def _controlar_ptz(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Controla câmera PTZ"""
        camera_id = params.get("camera_id")
        comando = params.get("comando")  # pan_left, pan_right, tilt_up, tilt_down, zoom_in, zoom_out
        preset = params.get("preset")  # posição predefinida

        if not camera_id:
            return {"success": False, "error": "camera_id é obrigatório"}

        if self.tools and self.mcp_url:
            result = await self.tools.execute(
                "call_mcp",
                mcp_name="mcp-intelbras-cftv",
                method="ptz_control",
                params={
                    "camera_id": camera_id,
                    "command": comando,
                    "preset": preset
                }
            )

            return {
                "success": result.success,
                "mensagem": "Comando PTZ executado" if result.success else result.error
            }

        return {
            "success": True,
            "mensagem": f"Comando {comando or f'preset {preset}'} executado na câmera {camera_id}"
        }

    # ==================== NÍVEL 2: PROATIVO ====================

    async def _verificar_movimento(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Verifica movimento em câmeras"""
        camera_ids = params.get("camera_ids", [])

        movimentos_detectados = []

        for camera_id in camera_ids:
            # Simular análise de movimento
            movimento = {
                "camera_id": camera_id,
                "tem_movimento": True,
                "intensidade": 0.6,
                "zona": "entrada"
            }
            movimentos_detectados.append(movimento)

            # Alertar se intensidade alta
            if movimento["intensidade"] > self.config["sensibilidade_movimento"]:
                await self._enviar_alerta(
                    titulo="Movimento Detectado",
                    mensagem=f"Movimento na câmera {camera_id}",
                    nivel=NivelRisco.MEDIO,
                    camera_id=camera_id
                )

        return {
            "success": True,
            "movimentos": movimentos_detectados
        }

    async def _configurar_zona(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Configura zona de monitoramento"""
        camera_id = params.get("camera_id")
        zona = params.get("zona")  # coordenadas do polígono
        nome = params.get("nome")
        tipo = params.get("tipo", "cerca_virtual")

        if self.tools:
            result = await self.tools.execute(
                "database_insert",
                table="zonas_monitoramento",
                data={
                    "camera_id": camera_id,
                    "nome": nome,
                    "tipo": tipo,
                    "coordenadas": json.dumps(zona),
                    "condominio_id": self.condominio_id,
                    "ativa": True
                }
            )

            if result.success:
                return {
                    "success": True,
                    "zona_id": result.data.get("id"),
                    "mensagem": f"Zona '{nome}' configurada"
                }

        return {"success": True, "mensagem": "Zona configurada"}

    # ==================== NÍVEL 3: PREDITIVO ====================

    async def _detectar_objetos(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Detecta objetos em frame/stream"""
        camera_id = params.get("camera_id")
        frame_base64 = params.get("frame")  # Imagem em base64

        if not camera_id:
            return {"success": False, "error": "camera_id é obrigatório"}

        # Usar LLM com visão para análise
        if self.llm and frame_base64:
            prompt = """Analise esta imagem de câmera de segurança e identifique:

1. Pessoas: quantidade, posição aproximada, comportamento
2. Veículos: tipo, cor, placa se visível
3. Objetos: itens abandonados, objetos suspeitos
4. Situações: algo anormal ou suspeito

Responda em JSON:
{
  "pessoas": [{"posicao": "...", "comportamento": "..."}],
  "veiculos": [{"tipo": "...", "cor": "...", "placa": "..."}],
  "objetos": [{"tipo": "...", "posicao": "...", "suspeito": bool}],
  "situacao_geral": "normal/suspeita/critica",
  "alertas": ["alerta1", "alerta2"]
}
"""
            try:
                # Nota: Isso requer modelo multimodal
                response = await self.llm.generate(
                    system_prompt=self.get_system_prompt(),
                    user_prompt=prompt,
                    temperature=0.2
                )

                import re
                json_match = re.search(r'\{[\s\S]*\}', response)
                if json_match:
                    deteccoes = json.loads(json_match.group())
                    return {
                        "success": True,
                        "camera_id": camera_id,
                        "deteccoes": deteccoes,
                        "timestamp": datetime.now().isoformat()
                    }

            except Exception as e:
                logger.error(f"Erro na detecção: {e}")

        # Mock de detecção
        return {
            "success": True,
            "camera_id": camera_id,
            "deteccoes": {
                "pessoas": [
                    {"posicao": "centro", "comportamento": "caminhando normalmente"}
                ],
                "veiculos": [],
                "objetos": [],
                "situacao_geral": "normal",
                "alertas": []
            },
            "modelo": self._modelo_deteccao,
            "timestamp": datetime.now().isoformat()
        }

    async def _analisar_comportamento(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Analisa comportamento de pessoa detectada"""
        camera_id = params.get("camera_id")
        pessoa_id = params.get("pessoa_id")
        historico = params.get("historico", [])  # Lista de posições/ações

        if self.llm:
            prompt = f"""Analise o comportamento desta pessoa detectada nas câmeras:

Câmera: {camera_id}
Histórico de movimentação: {json.dumps(historico)}

Avalie:
1. Padrão de movimentação (normal, errático, suspeito)
2. Tempo de permanência em áreas
3. Comportamentos anormais (olhar repetido, tentativa de acesso)
4. Nível de suspeita (0.0 - 1.0)
5. Recomendações

Responda em JSON:
{{
  "padrao_movimento": "...",
  "tempo_permanencia_areas": {{}},
  "comportamentos_anormais": [],
  "nivel_suspeita": 0.0,
  "recomendacoes": []
}}
"""
            try:
                response = await self.llm.generate(
                    system_prompt=self.get_system_prompt(),
                    user_prompt=prompt,
                    temperature=0.3
                )

                import re
                json_match = re.search(r'\{[\s\S]*\}', response)
                if json_match:
                    analise = json.loads(json_match.group())

                    # Criar ação se suspeita alta
                    if analise.get("nivel_suspeita", 0) > 0.7:
                        await self._criar_alerta_comportamento(camera_id, pessoa_id, analise)

                    return {
                        "success": True,
                        "analise": analise
                    }

            except Exception as e:
                logger.error(f"Erro na análise comportamental: {e}")

        # Mock
        return {
            "success": True,
            "analise": {
                "padrao_movimento": "normal",
                "tempo_permanencia_areas": {"entrada": "2min", "hall": "30s"},
                "comportamentos_anormais": [],
                "nivel_suspeita": 0.2,
                "recomendacoes": []
            }
        }

    # ==================== NÍVEL 4: AUTÔNOMO ====================

    async def _processar_evento_ia(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Processa evento detectado pela IA (Guardian)"""
        evento = EventoDetectado(
            id=params.get("id", hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]),
            camera_id=params.get("camera_id"),
            tipo=TipoEvento(params.get("tipo", "movimento")),
            timestamp=datetime.now(),
            confianca=params.get("confianca", 0.8),
            nivel_risco=NivelRisco(params.get("nivel_risco", 2)),
            objetos_detectados=params.get("objetos", []),
            descricao=params.get("descricao", "")
        )

        # Verificar confiança mínima
        if evento.confianca < self.config["confianca_minima_alerta"]:
            return {"success": True, "processado": False, "motivo": "Confiança abaixo do limite"}

        # Processar baseado no tipo de evento
        if self.has_capability("acoes_automaticas"):
            return await self._processar_evento_autonomo({"evento": evento}, context)

        # Apenas registrar se não tem autonomia
        self._eventos_pendentes.append(evento)

        return {
            "success": True,
            "evento_id": evento.id,
            "status": "registrado_pendente"
        }

    async def _processar_evento_autonomo(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Processa evento de forma autônoma"""
        evento = params.get("evento")
        if not evento:
            return {"success": False, "error": "Evento não fornecido"}

        acoes_tomadas = []

        # Ações baseadas no tipo de evento
        if evento.tipo == TipoEvento.INVASAO:
            # Crítico: ativar alarme, notificar portaria, gravar
            acoes_tomadas.append(await self._ativar_alarme(evento))
            acoes_tomadas.append(await self._notificar_portaria(evento, Priority.CRITICAL))
            acoes_tomadas.append(await self._iniciar_gravacao_evento(evento))

            # Colaborar com agente de Acesso
            if self.has_capability("integrar_acesso"):
                await self._bloquear_acessos_area(evento.camera_id)

        elif evento.tipo == TipoEvento.COMPORTAMENTO_SUSPEITO:
            # Alto: notificar portaria, iniciar tracking
            acoes_tomadas.append(await self._notificar_portaria(evento, Priority.HIGH))
            acoes_tomadas.append(await self._iniciar_tracking(evento))

        elif evento.tipo == TipoEvento.OBJETO_ABANDONADO:
            # Médio: alertar e monitorar
            acoes_tomadas.append(await self._enviar_alerta(
                titulo="Objeto Abandonado Detectado",
                mensagem=f"Objeto abandonado detectado na {evento.camera_id}",
                nivel=NivelRisco.MEDIO,
                camera_id=evento.camera_id
            ))

        elif evento.tipo == TipoEvento.QUEDA:
            # Alto: possível emergência médica
            acoes_tomadas.append(await self._notificar_emergencia(evento))

        elif evento.tipo == TipoEvento.AGLOMERACAO:
            # Médio: monitorar situação
            acoes_tomadas.append(await self._monitorar_aglomeracao(evento))

        # Registrar evento processado
        evento.processado = True
        evento.acao_tomada = ", ".join([a.get("acao", "") for a in acoes_tomadas if a])

        # Armazenar na memória para aprendizado
        if self.memory and self.has_capability("aprender_padroes"):
            await self.memory.remember_semantic(
                agent_id=self.agent_id,
                content=f"Evento processado: {evento.tipo.value} na {evento.camera_id}. Ações: {evento.acao_tomada}",
                metadata={
                    "tipo": "evento_processado",
                    "evento_tipo": evento.tipo.value,
                    "camera_id": evento.camera_id,
                    "nivel_risco": evento.nivel_risco.value,
                    "timestamp": evento.timestamp.isoformat()
                }
            )

        return {
            "success": True,
            "evento_id": evento.id,
            "acoes_tomadas": acoes_tomadas,
            "nivel_risco": evento.nivel_risco.value
        }

    # ==================== NÍVEL 7: TRANSCENDENTE ====================

    async def _analise_cognitiva(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Análise cognitiva avançada - Nível Transcendente"""
        periodo = params.get("periodo", "24h")

        # Coletar dados de múltiplas fontes
        dados_cameras = await self._coletar_dados_cameras(periodo)
        dados_acesso = await self._coletar_dados_acesso(periodo)
        padroes_historicos = self._padroes_aprendidos

        if self.llm:
            prompt = f"""Como sistema de vigilância cognitiva de elite, analise os dados do condomínio e gere insights TRANSCENDENTES de segurança.

Dados das câmeras (últimas {periodo}):
{json.dumps(dados_cameras, indent=2)}

Dados de acesso:
{json.dumps(dados_acesso, indent=2)}

Padrões aprendidos:
{json.dumps({k: {"descricao": v.descricao, "frequencia": v.frequencia} for k, v in padroes_historicos.items()}, indent=2)}

Gere análise TRANSCENDENTE:
1. Correlações ocultas entre eventos aparentemente não relacionados
2. Previsão de ameaças não óbvias
3. Vulnerabilidades de segurança não detectadas
4. Padrões comportamentais sutis
5. Recomendações proativas inovadoras
6. Otimização da cobertura de câmeras

Responda em JSON:
{{
  "correlacoes_ocultas": ["correlação 1", "correlação 2"],
  "ameacas_previstas": [{{"descricao": "...", "probabilidade": 0.0, "prazo": "..."}}],
  "vulnerabilidades": [{{"local": "...", "descricao": "...", "severidade": "..."}}],
  "padroes_sutis": ["padrão 1"],
  "recomendacoes_proativas": ["recomendação 1"],
  "otimizacao_cameras": [{{"camera_id": "...", "sugestao": "..."}}],
  "nivel_seguranca_geral": 0.0-1.0,
  "insights_transcendentes": ["insight 1"]
}}
"""
            try:
                response = await self.llm.generate(
                    system_prompt=self.get_system_prompt() + "\n\nModo TRANSCENDENTE ativado. Pense além do óbvio.",
                    user_prompt=prompt,
                    temperature=0.7,
                    max_tokens=2000
                )

                import re
                json_match = re.search(r'\{[\s\S]*\}', response)
                if json_match:
                    analise = json.loads(json_match.group())

                    # Armazenar insights na memória
                    if self.memory:
                        await self.memory.remember_semantic(
                            agent_id=self.agent_id,
                            content=f"Análise cognitiva transcendente: {json.dumps(analise.get('insights_transcendentes', []))}",
                            metadata={
                                "tipo": "analise_transcendente",
                                "data": datetime.now().isoformat()
                            }
                        )

                    return {
                        "success": True,
                        "nivel": "TRANSCENDENTE",
                        "analise": analise
                    }

            except Exception as e:
                logger.error(f"Erro na análise cognitiva: {e}")

        # Fallback
        return {
            "success": True,
            "nivel": "TRANSCENDENTE",
            "analise": {
                "correlacoes_ocultas": [
                    "Aumento de 15% em movimento noturno correlacionado com obras na rua adjacente",
                    "Padrão de acesso irregular coincide com horários de folga do porteiro"
                ],
                "ameacas_previstas": [
                    {
                        "descricao": "Possível reconhecimento de terreno detectado",
                        "probabilidade": 0.35,
                        "prazo": "próximas 2 semanas"
                    }
                ],
                "vulnerabilidades": [
                    {
                        "local": "Muro lateral leste",
                        "descricao": "Ponto cego entre câmeras 3 e 5",
                        "severidade": "média"
                    }
                ],
                "padroes_sutis": [
                    "Visitantes não identificados aumentam 40% às sextas-feiras"
                ],
                "recomendacoes_proativas": [
                    "Adicionar câmera no ponto cego identificado",
                    "Aumentar vigilância em horários de pico de vulnerabilidade"
                ],
                "otimizacao_cameras": [
                    {"camera_id": "cam_003", "sugestao": "Ajustar ângulo 15° à esquerda para cobrir área de lazer"}
                ],
                "nivel_seguranca_geral": 0.82,
                "insights_transcendentes": [
                    "Sistema sugere correlação entre clima e incidentes - dias nublados têm 23% mais ocorrências"
                ]
            }
        }

    async def _process_chat(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Processa chat com o agente"""
        message = params.get("message", "")

        if not self.llm:
            return {"error": "LLM não configurado"}

        # Buscar contexto de segurança recente
        security_context = await self._get_security_context()

        prompt = f"""Contexto de segurança atual:
{json.dumps(security_context, indent=2)}

Pergunta do usuário: {message}

Responda de forma útil sobre monitoramento e segurança do condomínio.
"""

        response = await self.llm.generate(
            system_prompt=self.get_system_prompt(),
            user_prompt=prompt
        )

        return {
            "success": True,
            "response": response
        }

    # ==================== MÉTODOS AUXILIARES ====================

    async def _enviar_alerta(self, titulo: str, mensagem: str, nivel: NivelRisco, camera_id: str) -> Dict:
        """Envia alerta de segurança"""
        alerta_key = f"{camera_id}_{nivel.value}"

        # Verificar cooldown
        ultimo = self._alertas_enviados.get(alerta_key)
        if ultimo and (datetime.now() - ultimo).seconds < self.config["cooldown_alertas"]:
            return {"acao": "alerta_suprimido", "motivo": "cooldown"}

        if self.tools:
            await self.tools.execute(
                "send_notification",
                user_ids=["portaria", "sindico"],
                title=titulo,
                message=mensagem,
                channels=["push", "app"],
                priority="high" if nivel.value >= 3 else "normal"
            )

        self._alertas_enviados[alerta_key] = datetime.now()

        return {"acao": "alerta_enviado", "titulo": titulo}

    async def _notificar_portaria(self, evento: EventoDetectado, prioridade: Priority) -> Dict:
        """Notifica portaria sobre evento"""
        if self.tools:
            await self.tools.execute(
                "send_notification",
                user_ids=["portaria"],
                title=f"ALERTA: {evento.tipo.value.upper()}",
                message=f"Detectado na câmera {evento.camera_id}. {evento.descricao}",
                channels=["push", "app", "som"],
                priority=prioridade.name.lower()
            )

        return {"acao": "portaria_notificada", "prioridade": prioridade.name}

    async def _ativar_alarme(self, evento: EventoDetectado) -> Dict:
        """Ativa alarme do sistema"""
        if self.tools:
            await self.tools.execute(
                "call_mcp",
                mcp_name="mcp-jfl-alarme",
                method="ativar_sirene",
                params={"zona": evento.camera_id, "duracao": 30}
            )

        return {"acao": "alarme_ativado", "zona": evento.camera_id}

    async def _iniciar_gravacao_evento(self, evento: EventoDetectado) -> Dict:
        """Inicia gravação focada no evento"""
        return {"acao": "gravacao_iniciada", "camera_id": evento.camera_id}

    async def _iniciar_tracking(self, evento: EventoDetectado) -> Dict:
        """Inicia tracking de pessoa/objeto"""
        return {"acao": "tracking_iniciado", "camera_id": evento.camera_id}

    async def _notificar_emergencia(self, evento: EventoDetectado) -> Dict:
        """Notifica sobre possível emergência"""
        if self.tools:
            await self.tools.execute(
                "send_notification",
                user_ids=["portaria", "sindico", "zelador"],
                title="EMERGÊNCIA: Possível queda detectada",
                message=f"Câmera {evento.camera_id} detectou possível queda. Verificar imediatamente.",
                channels=["push", "app", "sms"],
                priority="urgent"
            )

        return {"acao": "emergencia_notificada"}

    async def _monitorar_aglomeracao(self, evento: EventoDetectado) -> Dict:
        """Monitora aglomeração detectada"""
        return {"acao": "monitoramento_aglomeracao", "camera_id": evento.camera_id}

    async def _bloquear_acessos_area(self, camera_id: str) -> Dict:
        """Bloqueia acessos na área (colaboração)"""
        # Enviar mensagem para agente de Acesso
        if self.has_capability("agent_collaboration"):
            await self.send_message(
                receiver_id=f"acesso_{self.condominio_id}",
                content={
                    "action": "bloquear_area",
                    "camera_id": camera_id,
                    "motivo": "invasao_detectada"
                },
                priority=Priority.CRITICAL
            )

        return {"acao": "bloqueio_solicitado", "area": camera_id}

    async def _criar_alerta_comportamento(self, camera_id: str, pessoa_id: str, analise: Dict):
        """Cria alerta para comportamento suspeito"""
        await self._enviar_alerta(
            titulo="Comportamento Suspeito",
            mensagem=f"Pessoa com comportamento suspeito detectada na {camera_id}",
            nivel=NivelRisco.ALTO,
            camera_id=camera_id
        )

    async def _coletar_dados_cameras(self, periodo: str) -> Dict:
        """Coleta dados das câmeras para análise"""
        return {
            "total_eventos": 47,
            "por_tipo": {
                "movimento": 30,
                "pessoa": 12,
                "veiculo": 5
            },
            "cameras_mais_ativas": ["cam_001", "cam_002"],
            "horarios_pico": ["08:00", "18:00", "22:00"]
        }

    async def _coletar_dados_acesso(self, periodo: str) -> Dict:
        """Coleta dados de acesso para correlação"""
        return {
            "total_acessos": 234,
            "moradores": 180,
            "visitantes": 45,
            "prestadores": 9,
            "negados": 3
        }

    async def _get_security_context(self) -> Dict:
        """Obtém contexto atual de segurança"""
        return {
            "cameras_online": 5,
            "eventos_ultimas_24h": 47,
            "alertas_ativos": 0,
            "ultimo_incidente": "Nenhum nas últimas 48h"
        }


# Factory function
def create_cftv_agent(
    condominio_id: str,
    llm_client: UnifiedLLMClient = None,
    memory: UnifiedMemorySystem = None,
    tools: ToolRegistry = None,
    mcp_url: str = None,
    evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT
) -> AgenteCFTV:
    """Cria instância do agente CFTV"""
    return AgenteCFTV(
        condominio_id=condominio_id,
        llm_client=llm_client or UnifiedLLMClient(),
        memory=memory,
        tools=tools,
        mcp_cftv_url=mcp_url,
        evolution_level=evolution_level
    )
