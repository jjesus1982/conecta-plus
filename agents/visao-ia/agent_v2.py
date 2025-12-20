"""
Conecta Plus - Agente de Visão IA (Nível 7)
Sistema inteligente de processamento de imagens e vídeo

Capacidades:
1. REATIVO: Processar imagens, identificar objetos
2. PROATIVO: Detectar anomalias visuais, alertar
3. PREDITIVO: Prever comportamentos, identificar padrões
4. AUTÔNOMO: Classificar automaticamente, tomar decisões
5. EVOLUTIVO: Aprender novos padrões visuais
6. COLABORATIVO: Integrar CFTV, Acesso, Alarme
7. TRANSCENDENTE: Visão computacional cognitiva
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

from ..core.base_agent import (
    BaseAgent, EvolutionLevel, Priority, AgentCapability,
    AgentContext, AgentAction, AgentPrediction,
)
from ..core.memory_store import UnifiedMemorySystem
from ..core.llm_client import UnifiedLLMClient
from ..core.tools import ToolRegistry

logger = logging.getLogger(__name__)


class TipoDeteccao(Enum):
    FACE = "face"
    PLACA = "placa"
    OBJETO = "objeto"
    PESSOA = "pessoa"
    VEICULO = "veiculo"
    ANIMAL = "animal"
    COMPORTAMENTO = "comportamento"


class TipoEvento(Enum):
    RECONHECIMENTO = "reconhecimento"
    INTRUSO = "intruso"
    AGLOMERACAO = "aglomeracao"
    OBJETO_ABANDONADO = "objeto_abandonado"
    COMPORTAMENTO_SUSPEITO = "comportamento_suspeito"
    QUEDA = "queda"
    BRIGA = "briga"


class NivelConfianca(Enum):
    BAIXA = "baixa"
    MEDIA = "media"
    ALTA = "alta"


@dataclass
class Deteccao:
    id: str
    tipo: TipoDeteccao
    timestamp: datetime
    camera_id: str
    confianca: float
    bounding_box: Dict
    metadata: Dict = field(default_factory=dict)
    imagem_url: Optional[str] = None


@dataclass
class EventoVisual:
    id: str
    tipo: TipoEvento
    timestamp: datetime
    camera_id: str
    descricao: str
    confianca: float
    deteccoes: List[Deteccao] = field(default_factory=list)
    alertado: bool = False


class AgenteVisaoIA(BaseAgent):
    """Agente de Visão IA - Nível 7"""

    def __init__(
        self,
        condominio_id: str,
        llm_client: UnifiedLLMClient = None,
        memory: UnifiedMemorySystem = None,
        tools: ToolRegistry = None,
        evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT,
    ):
        super().__init__(
            agent_id=f"visao_ia_{condominio_id}",
            agent_type="visao_ia",
            condominio_id=condominio_id,
            evolution_level=evolution_level,
            llm_client=llm_client,
            memory_store=memory,
        )
        self.tools = tools
        self._deteccoes: List[Deteccao] = []
        self._eventos: List[EventoVisual] = []
        self._faces_conhecidas: Dict[str, Dict] = {}
        self._placas_autorizadas: Dict[str, Dict] = {}

        self.config = {
            "threshold_confianca": 0.75,
            "alertar_intrusos": True,
            "reconhecimento_facial": True,
            "lpr_ativo": True,  # License Plate Recognition
            "deteccao_comportamento": True,
        }

    def _register_capabilities(self) -> None:
        self._capabilities["processamento_imagem"] = AgentCapability(
            name="processamento_imagem", description="Processar imagens e vídeo",
            level=EvolutionLevel.REACTIVE
        )
        self._capabilities["deteccao_anomalias"] = AgentCapability(
            name="deteccao_anomalias", description="Detectar anomalias visuais",
            level=EvolutionLevel.PROACTIVE
        )
        self._capabilities["previsao_comportamento"] = AgentCapability(
            name="previsao_comportamento", description="Prever comportamentos",
            level=EvolutionLevel.PREDICTIVE
        )
        self._capabilities["classificacao_autonoma"] = AgentCapability(
            name="classificacao_autonoma", description="Classificar automaticamente",
            level=EvolutionLevel.AUTONOMOUS
        )
        self._capabilities["visao_cognitiva"] = AgentCapability(
            name="visao_cognitiva", description="Visão computacional cognitiva",
            level=EvolutionLevel.TRANSCENDENT
        )

    def get_system_prompt(self) -> str:
        return f"""Você é o Agente de Visão IA do Conecta Plus.
ID: {self.agent_id} | Condomínio: {self.condominio_id} | Nível: {self.evolution_level.name}

Responsabilidades:
- Processar imagens e vídeos das câmeras
- Reconhecer faces e placas
- Detectar objetos e comportamentos
- Alertar sobre anomalias visuais
- Integrar com sistemas de segurança

Configurações:
- Threshold confiança: {self.config['threshold_confianca']}
- Reconhecimento facial: {self.config['reconhecimento_facial']}
- LPR ativo: {self.config['lpr_ativo']}
"""

    async def process(self, input_data: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        action = input_data.get("action", "")
        params = input_data.get("params", {})

        if action == "processar_imagem":
            return await self._processar_imagem(params, context)
        elif action == "reconhecer_face":
            return await self._reconhecer_face(params, context)
        elif action == "detectar_placa":
            return await self._detectar_placa(params, context)
        elif action == "detectar_objetos":
            return await self._detectar_objetos(params, context)
        elif action == "analisar_comportamento":
            return await self._analisar_comportamento(params, context)
        elif action == "cadastrar_face":
            return await self._cadastrar_face(params, context)
        elif action == "cadastrar_placa":
            return await self._cadastrar_placa(params, context)
        elif action == "listar_eventos":
            return await self._listar_eventos(params, context)
        elif action == "analise_cena":
            return await self._analise_cena(params, context)
        elif action == "chat":
            return await self._chat(params, context)
        else:
            return {"error": f"Ação '{action}' não reconhecida"}

    async def _processar_imagem(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        imagem_url = params.get("imagem_url")
        camera_id = params.get("camera_id", "desconhecida")
        tipos_deteccao = params.get("tipos", ["face", "pessoa", "veiculo"])

        resultados = []

        # Chamar MCP de visão IA
        if self.tools:
            for tipo in tipos_deteccao:
                resultado = await self.tools.execute(
                    "call_mcp", mcp_name="mcp-vision-ai",
                    method="detect", params={
                        "image_url": imagem_url,
                        "type": tipo,
                        "threshold": self.config["threshold_confianca"]
                    }
                )

                for det in resultado.get("detections", []):
                    deteccao = Deteccao(
                        id=f"det_{datetime.now().timestamp()}",
                        tipo=TipoDeteccao(tipo),
                        timestamp=datetime.now(),
                        camera_id=camera_id,
                        confianca=det.get("confidence", 0),
                        bounding_box=det.get("bbox", {}),
                        metadata=det.get("metadata", {}),
                        imagem_url=imagem_url
                    )
                    self._deteccoes.append(deteccao)
                    resultados.append({
                        "tipo": tipo,
                        "confianca": deteccao.confianca,
                        "bbox": deteccao.bounding_box
                    })

        return {
            "success": True,
            "camera_id": camera_id,
            "deteccoes": resultados
        }

    async def _reconhecer_face(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        if not self.config["reconhecimento_facial"]:
            return {"error": "Reconhecimento facial desativado"}

        imagem_url = params.get("imagem_url")

        if self.tools:
            resultado = await self.tools.execute(
                "call_mcp", mcp_name="mcp-vision-ai",
                method="recognize_face", params={
                    "image_url": imagem_url,
                    "known_faces": list(self._faces_conhecidas.keys())
                }
            )

            if resultado.get("identified"):
                face_id = resultado.get("face_id")
                pessoa = self._faces_conhecidas.get(face_id, {})

                # Colaborar com acesso
                if self.has_capability("agent_collaboration"):
                    await self.send_message(
                        f"acesso_{self.condominio_id}",
                        {
                            "action": "pessoa_identificada",
                            "params": {
                                "face_id": face_id,
                                "nome": pessoa.get("nome"),
                                "tipo": pessoa.get("tipo")
                            }
                        }
                    )

                return {
                    "success": True,
                    "identificado": True,
                    "face_id": face_id,
                    "nome": pessoa.get("nome"),
                    "tipo": pessoa.get("tipo"),
                    "confianca": resultado.get("confidence")
                }

        return {
            "success": True,
            "identificado": False,
            "confianca": 0
        }

    async def _detectar_placa(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        if not self.config["lpr_ativo"]:
            return {"error": "LPR desativado"}

        imagem_url = params.get("imagem_url")

        if self.tools:
            resultado = await self.tools.execute(
                "call_mcp", mcp_name="mcp-vision-ai",
                method="lpr", params={"image_url": imagem_url}
            )

            placa = resultado.get("plate")
            if placa:
                autorizada = placa in self._placas_autorizadas
                info_placa = self._placas_autorizadas.get(placa, {})

                # Colaborar com acesso
                if self.has_capability("agent_collaboration"):
                    await self.send_message(
                        f"acesso_{self.condominio_id}",
                        {
                            "action": "placa_detectada",
                            "params": {
                                "placa": placa,
                                "autorizada": autorizada,
                                "unidade": info_placa.get("unidade")
                            }
                        }
                    )

                return {
                    "success": True,
                    "placa": placa,
                    "confianca": resultado.get("confidence"),
                    "autorizada": autorizada,
                    "unidade": info_placa.get("unidade")
                }

        return {"success": True, "placa": None}

    async def _detectar_objetos(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        imagem_url = params.get("imagem_url")
        camera_id = params.get("camera_id")

        if self.tools:
            resultado = await self.tools.execute(
                "call_mcp", mcp_name="mcp-vision-ai",
                method="detect_objects", params={"image_url": imagem_url}
            )

            objetos = resultado.get("objects", [])

            # Verificar objetos abandonados
            for obj in objetos:
                if obj.get("abandoned", False) and self.config["alertar_intrusos"]:
                    evento = EventoVisual(
                        id=f"evt_{datetime.now().timestamp()}",
                        tipo=TipoEvento.OBJETO_ABANDONADO,
                        timestamp=datetime.now(),
                        camera_id=camera_id,
                        descricao=f"Objeto abandonado detectado: {obj.get('class')}",
                        confianca=obj.get("confidence", 0)
                    )
                    self._eventos.append(evento)

                    if self.tools:
                        await self.tools.execute(
                            "send_notification",
                            user_ids=["seguranca", "portaria"],
                            title="Objeto Abandonado Detectado",
                            message=f"Camera {camera_id}: {obj.get('class')}",
                            channels=["push"]
                        )

            return {"success": True, "objetos": objetos}

        return {"success": True, "objetos": []}

    async def _analisar_comportamento(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        if not self.config["deteccao_comportamento"]:
            return {"error": "Detecção de comportamento desativada"}

        video_url = params.get("video_url")
        camera_id = params.get("camera_id")

        if self.tools:
            resultado = await self.tools.execute(
                "call_mcp", mcp_name="mcp-vision-ai",
                method="analyze_behavior", params={
                    "video_url": video_url,
                    "behaviors": ["loitering", "running", "fighting", "falling", "crowd"]
                }
            )

            comportamentos = resultado.get("behaviors", [])

            for comp in comportamentos:
                if comp.get("confidence", 0) >= self.config["threshold_confianca"]:
                    tipo_evento = self._mapear_comportamento(comp.get("type"))

                    evento = EventoVisual(
                        id=f"evt_{datetime.now().timestamp()}",
                        tipo=tipo_evento,
                        timestamp=datetime.now(),
                        camera_id=camera_id,
                        descricao=f"Comportamento detectado: {comp.get('type')}",
                        confianca=comp.get("confidence")
                    )
                    self._eventos.append(evento)

                    # Alertar
                    if self.tools:
                        await self.tools.execute(
                            "send_notification",
                            user_ids=["seguranca"],
                            title=f"Alerta: {comp.get('type')}",
                            message=f"Camera {camera_id}",
                            channels=["push"],
                            priority="urgent"
                        )

            return {"success": True, "comportamentos": comportamentos}

        return {"success": True, "comportamentos": []}

    def _mapear_comportamento(self, tipo: str) -> TipoEvento:
        mapeamento = {
            "loitering": TipoEvento.COMPORTAMENTO_SUSPEITO,
            "running": TipoEvento.COMPORTAMENTO_SUSPEITO,
            "fighting": TipoEvento.BRIGA,
            "falling": TipoEvento.QUEDA,
            "crowd": TipoEvento.AGLOMERACAO
        }
        return mapeamento.get(tipo, TipoEvento.COMPORTAMENTO_SUSPEITO)

    async def _cadastrar_face(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        face_id = params.get("face_id") or f"face_{datetime.now().timestamp()}"
        nome = params.get("nome")
        tipo = params.get("tipo", "morador")
        imagens = params.get("imagens", [])

        if self.tools and imagens:
            await self.tools.execute(
                "call_mcp", mcp_name="mcp-vision-ai",
                method="register_face", params={
                    "face_id": face_id,
                    "images": imagens
                }
            )

        self._faces_conhecidas[face_id] = {
            "nome": nome,
            "tipo": tipo,
            "cadastrado_em": datetime.now().isoformat()
        }

        return {
            "success": True,
            "face_id": face_id,
            "nome": nome
        }

    async def _cadastrar_placa(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        placa = params.get("placa")
        unidade = params.get("unidade")
        proprietario = params.get("proprietario")

        self._placas_autorizadas[placa] = {
            "unidade": unidade,
            "proprietario": proprietario,
            "cadastrado_em": datetime.now().isoformat()
        }

        return {
            "success": True,
            "placa": placa,
            "unidade": unidade
        }

    async def _listar_eventos(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        tipo_filtro = params.get("tipo")
        camera_id = params.get("camera_id")
        limite = params.get("limite", 50)

        eventos = self._eventos

        if tipo_filtro:
            eventos = [e for e in eventos if e.tipo.value == tipo_filtro]
        if camera_id:
            eventos = [e for e in eventos if e.camera_id == camera_id]

        eventos = sorted(eventos, key=lambda e: e.timestamp, reverse=True)[:limite]

        return {
            "success": True,
            "eventos": [
                {
                    "id": e.id,
                    "tipo": e.tipo.value,
                    "camera_id": e.camera_id,
                    "descricao": e.descricao,
                    "confianca": e.confianca,
                    "timestamp": e.timestamp.isoformat()
                }
                for e in eventos
            ]
        }

    async def _analise_cena(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        if not self.has_capability("visao_cognitiva"):
            return {"error": "Capacidade transcendente não disponível"}

        imagem_url = params.get("imagem_url")

        if self.llm:
            # Coletar detecções da imagem
            deteccoes = await self._processar_imagem({
                "imagem_url": imagem_url,
                "tipos": ["pessoa", "veiculo", "objeto"]
            }, context)

            prompt = f"""Analise cognitivamente esta cena de segurança:
Detecções: {json.dumps(deteccoes)}

Forneça análise TRANSCENDENTE:
1. Descrição geral da cena
2. Pessoas identificadas e comportamento
3. Veículos e atividades
4. Avaliação de risco (1-10)
5. Ações recomendadas
6. Pontos de atenção para segurança
"""
            response = await self.llm.generate(self.get_system_prompt(), prompt)
            return {"success": True, "analise": response}

        return {"success": True, "analise": "Análise básica: cena normal"}

    async def _chat(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        if self.llm:
            response = await self.llm.generate(
                self.get_system_prompt(), params.get("message", "")
            )
            return {"success": True, "response": response}
        return {"error": "LLM não configurado"}


def create_vision_ai_agent(
    condominio_id: str,
    llm_client: UnifiedLLMClient = None,
    memory: UnifiedMemorySystem = None,
    tools: ToolRegistry = None,
    evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT
) -> AgenteVisaoIA:
    return AgenteVisaoIA(
        condominio_id=condominio_id,
        llm_client=llm_client or UnifiedLLMClient(),
        memory=memory, tools=tools,
        evolution_level=evolution_level
    )
