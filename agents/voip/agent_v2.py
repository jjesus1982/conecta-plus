"""
Conecta Plus - Agente de VoIP (Nível 7)
Sistema inteligente de telefonia IP e comunicação por voz

Capacidades:
1. REATIVO: Atender chamadas, transferir, registrar
2. PROATIVO: Alertar falhas, monitorar qualidade
3. PREDITIVO: Prever demanda, otimizar rotas
4. AUTÔNOMO: Atendimento automático, URA inteligente
5. EVOLUTIVO: Aprender padrões de chamadas
6. COLABORATIVO: Integrar Portaria, Emergência, Moradores
7. TRANSCENDENTE: Comunicação cognitiva por voz
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


class StatusChamada(Enum):
    TOCANDO = "tocando"
    ATENDIDA = "atendida"
    EM_ESPERA = "em_espera"
    TRANSFERIDA = "transferida"
    ENCERRADA = "encerrada"
    NAO_ATENDIDA = "nao_atendida"


class TipoChamada(Enum):
    INTERNA = "interna"
    EXTERNA_ENTRADA = "externa_entrada"
    EXTERNA_SAIDA = "externa_saida"
    INTERFONE = "interfone"
    EMERGENCIA = "emergencia"


class TipoRamal(Enum):
    PORTARIA = "portaria"
    ADMINISTRACAO = "administracao"
    SINDICO = "sindico"
    ZELADOR = "zelador"
    UNIDADE = "unidade"
    AREA_COMUM = "area_comum"


@dataclass
class Ramal:
    numero: str
    tipo: TipoRamal
    nome: str
    dono_id: str
    ativo: bool = True
    ocupado: bool = False
    encaminhamento: Optional[str] = None


@dataclass
class Chamada:
    id: str
    origem: str
    destino: str
    tipo: TipoChamada
    status: StatusChamada
    timestamp_inicio: datetime
    timestamp_fim: Optional[datetime] = None
    duracao_segundos: int = 0
    gravacao_url: Optional[str] = None
    transcricao: Optional[str] = None


class AgenteVoIP(BaseAgent):
    """Agente de VoIP - Nível 7"""

    def __init__(
        self,
        condominio_id: str,
        llm_client: UnifiedLLMClient = None,
        memory: UnifiedMemorySystem = None,
        tools: ToolRegistry = None,
        evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT,
    ):
        super().__init__(
            agent_id=f"voip_{condominio_id}",
            agent_type="voip",
            condominio_id=condominio_id,
            evolution_level=evolution_level,
            llm_client=llm_client,
            memory_store=memory,
        )
        self.tools = tools
        self._ramais: Dict[str, Ramal] = {}
        self._chamadas: List[Chamada] = []
        self._fila_espera: List[str] = []

        self.config = {
            "gravar_chamadas": True,
            "transcricao_automatica": True,
            "ura_inteligente": True,
            "timeout_toque_segundos": 30,
            "max_fila_espera": 5,
        }

    def _register_capabilities(self) -> None:
        self._capabilities["gestao_chamadas"] = AgentCapability(
            name="gestao_chamadas", description="Gerenciar chamadas telefônicas",
            level=EvolutionLevel.REACTIVE
        )
        self._capabilities["monitoramento_qualidade"] = AgentCapability(
            name="monitoramento_qualidade", description="Monitorar qualidade de áudio",
            level=EvolutionLevel.PROACTIVE
        )
        self._capabilities["previsao_demanda"] = AgentCapability(
            name="previsao_demanda", description="Prever demanda de linhas",
            level=EvolutionLevel.PREDICTIVE
        )
        self._capabilities["ura_autonoma"] = AgentCapability(
            name="ura_autonoma", description="URA inteligente autônoma",
            level=EvolutionLevel.AUTONOMOUS
        )
        self._capabilities["voip_cognitivo"] = AgentCapability(
            name="voip_cognitivo", description="Comunicação cognitiva por voz",
            level=EvolutionLevel.TRANSCENDENT
        )

    def get_system_prompt(self) -> str:
        return f"""Você é o Agente de VoIP do Conecta Plus.
ID: {self.agent_id} | Condomínio: {self.condominio_id} | Nível: {self.evolution_level.name}

Responsabilidades:
- Gerenciar sistema de telefonia IP
- Controlar ramais e chamadas
- Operar URA inteligente
- Integrar interfones e portaria
- Gravar e transcrever chamadas

Configurações:
- Gravação: {self.config['gravar_chamadas']}
- Transcrição: {self.config['transcricao_automatica']}
- URA inteligente: {self.config['ura_inteligente']}
"""

    async def process(self, input_data: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        action = input_data.get("action", "")
        params = input_data.get("params", {})

        if action == "iniciar_chamada":
            return await self._iniciar_chamada(params, context)
        elif action == "atender_chamada":
            return await self._atender_chamada(params, context)
        elif action == "transferir_chamada":
            return await self._transferir_chamada(params, context)
        elif action == "encerrar_chamada":
            return await self._encerrar_chamada(params, context)
        elif action == "listar_ramais":
            return await self._listar_ramais(params, context)
        elif action == "status_ramal":
            return await self._status_ramal(params, context)
        elif action == "historico_chamadas":
            return await self._historico_chamadas(params, context)
        elif action == "ura_atendimento":
            return await self._ura_atendimento(params, context)
        elif action == "metricas":
            return await self._metricas(params, context)
        elif action == "chat":
            return await self._chat(params, context)
        else:
            return {"error": f"Ação '{action}' não reconhecida"}

    async def _iniciar_chamada(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        origem = params.get("origem")
        destino = params.get("destino")
        tipo = TipoChamada(params.get("tipo", "interna"))

        # Verificar se destino está disponível
        ramal_destino = self._ramais.get(destino)
        if ramal_destino and ramal_destino.ocupado:
            if len(self._fila_espera) < self.config["max_fila_espera"]:
                self._fila_espera.append(origem)
                return {
                    "success": True,
                    "status": "em_fila",
                    "posicao": len(self._fila_espera)
                }
            return {"error": "Ramal ocupado e fila cheia"}

        chamada = Chamada(
            id=f"call_{datetime.now().timestamp()}",
            origem=origem,
            destino=destino,
            tipo=tipo,
            status=StatusChamada.TOCANDO,
            timestamp_inicio=datetime.now()
        )
        self._chamadas.append(chamada)

        # Iniciar chamada via Asterisk
        if self.tools:
            await self.tools.execute(
                "call_mcp", mcp_name="mcp-asterisk",
                method="originate", params={
                    "channel": f"SIP/{origem}",
                    "exten": destino,
                    "context": "condominio"
                }
            )

        return {
            "success": True,
            "chamada_id": chamada.id,
            "status": "tocando"
        }

    async def _atender_chamada(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        chamada_id = params.get("chamada_id")
        ramal = params.get("ramal")

        chamada = next((c for c in self._chamadas if c.id == chamada_id), None)
        if not chamada:
            return {"error": "Chamada não encontrada"}

        chamada.status = StatusChamada.ATENDIDA

        # Marcar ramal como ocupado
        if ramal in self._ramais:
            self._ramais[ramal].ocupado = True

        # Iniciar gravação se configurado
        if self.config["gravar_chamadas"] and self.tools:
            await self.tools.execute(
                "call_mcp", mcp_name="mcp-asterisk",
                method="start_recording", params={"call_id": chamada_id}
            )

        return {
            "success": True,
            "chamada_id": chamada_id,
            "status": "atendida"
        }

    async def _transferir_chamada(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        chamada_id = params.get("chamada_id")
        destino = params.get("destino")
        tipo = params.get("tipo", "cega")  # cega ou assistida

        chamada = next((c for c in self._chamadas if c.id == chamada_id), None)
        if not chamada:
            return {"error": "Chamada não encontrada"}

        chamada.status = StatusChamada.TRANSFERIDA
        chamada.destino = destino

        if self.tools:
            await self.tools.execute(
                "call_mcp", mcp_name="mcp-asterisk",
                method="transfer", params={
                    "call_id": chamada_id,
                    "destination": destino,
                    "type": tipo
                }
            )

        return {
            "success": True,
            "chamada_id": chamada_id,
            "transferida_para": destino
        }

    async def _encerrar_chamada(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        chamada_id = params.get("chamada_id")

        chamada = next((c for c in self._chamadas if c.id == chamada_id), None)
        if not chamada:
            return {"error": "Chamada não encontrada"}

        chamada.status = StatusChamada.ENCERRADA
        chamada.timestamp_fim = datetime.now()
        chamada.duracao_segundos = int((chamada.timestamp_fim - chamada.timestamp_inicio).total_seconds())

        # Liberar ramais
        for ramal in [chamada.origem, chamada.destino]:
            if ramal in self._ramais:
                self._ramais[ramal].ocupado = False

        # Processar gravação e transcrição
        if self.config["gravar_chamadas"] and self.tools:
            gravacao = await self.tools.execute(
                "call_mcp", mcp_name="mcp-asterisk",
                method="stop_recording", params={"call_id": chamada_id}
            )
            chamada.gravacao_url = gravacao.get("url")

            if self.config["transcricao_automatica"]:
                transcricao = await self.tools.execute(
                    "call_mcp", mcp_name="mcp-whisper",
                    method="transcribe", params={"audio_url": chamada.gravacao_url}
                )
                chamada.transcricao = transcricao.get("text")

        return {
            "success": True,
            "chamada_id": chamada_id,
            "duracao_segundos": chamada.duracao_segundos,
            "gravacao_url": chamada.gravacao_url
        }

    async def _listar_ramais(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        tipo_filtro = params.get("tipo")
        apenas_ativos = params.get("apenas_ativos", True)

        ramais = list(self._ramais.values())

        if tipo_filtro:
            ramais = [r for r in ramais if r.tipo.value == tipo_filtro]
        if apenas_ativos:
            ramais = [r for r in ramais if r.ativo]

        return {
            "success": True,
            "ramais": [
                {
                    "numero": r.numero,
                    "tipo": r.tipo.value,
                    "nome": r.nome,
                    "ocupado": r.ocupado
                }
                for r in ramais
            ]
        }

    async def _status_ramal(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        numero = params.get("numero")

        if numero not in self._ramais:
            return {"error": "Ramal não encontrado"}

        r = self._ramais[numero]

        return {
            "success": True,
            "ramal": {
                "numero": r.numero,
                "tipo": r.tipo.value,
                "nome": r.nome,
                "ativo": r.ativo,
                "ocupado": r.ocupado,
                "encaminhamento": r.encaminhamento
            }
        }

    async def _historico_chamadas(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        ramal = params.get("ramal")
        tipo = params.get("tipo")
        limite = params.get("limite", 50)

        chamadas = self._chamadas

        if ramal:
            chamadas = [c for c in chamadas if c.origem == ramal or c.destino == ramal]
        if tipo:
            chamadas = [c for c in chamadas if c.tipo.value == tipo]

        chamadas = sorted(chamadas, key=lambda c: c.timestamp_inicio, reverse=True)[:limite]

        return {
            "success": True,
            "chamadas": [
                {
                    "id": c.id,
                    "origem": c.origem,
                    "destino": c.destino,
                    "tipo": c.tipo.value,
                    "status": c.status.value,
                    "duracao": c.duracao_segundos,
                    "timestamp": c.timestamp_inicio.isoformat()
                }
                for c in chamadas
            ]
        }

    async def _ura_atendimento(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        if not self.config["ura_inteligente"]:
            return {"error": "URA inteligente desativada"}

        chamada_id = params.get("chamada_id")
        entrada_usuario = params.get("entrada")  # DTMF ou voz

        if self.llm and self.has_capability("ura_autonoma"):
            prompt = f"""Você é a URA inteligente do condomínio.
Entrada do usuário: {entrada_usuario}

Responda de forma natural e direcione para:
1 - Portaria
2 - Administração
3 - Síndico
4 - Manutenção
0 - Falar com atendente

Se entrada for por voz, interprete a intenção.
"""
            response = await self.llm.generate(self.get_system_prompt(), prompt)

            # Determinar destino baseado na resposta
            destino = self._mapear_opcao_ura(entrada_usuario)

            return {
                "success": True,
                "resposta_ura": response,
                "destino_sugerido": destino
            }

        return {"success": True, "destino": self._mapear_opcao_ura(entrada_usuario)}

    def _mapear_opcao_ura(self, entrada: str) -> str:
        mapeamento = {
            "1": "portaria",
            "2": "administracao",
            "3": "sindico",
            "4": "manutencao",
            "0": "atendente"
        }
        return mapeamento.get(entrada, "atendente")

    async def _metricas(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        if not self.has_capability("voip_cognitivo"):
            return {"error": "Capacidade transcendente não disponível"}

        periodo = params.get("periodo", "dia")

        total_chamadas = len(self._chamadas)
        atendidas = len([c for c in self._chamadas if c.status == StatusChamada.ENCERRADA])
        nao_atendidas = len([c for c in self._chamadas if c.status == StatusChamada.NAO_ATENDIDA])
        duracao_media = sum(c.duracao_segundos for c in self._chamadas) / max(total_chamadas, 1)

        if self.llm:
            prompt = f"""Analise as métricas do sistema VoIP:
Total chamadas: {total_chamadas}
Atendidas: {atendidas}
Não atendidas: {nao_atendidas}
Duração média: {duracao_media}s

Gere análise TRANSCENDENTE:
1. Taxa de atendimento
2. Horários de pico
3. Qualidade do serviço
4. Otimizações sugeridas
"""
            response = await self.llm.generate(self.get_system_prompt(), prompt)
            return {"success": True, "metricas": response}

        return {
            "success": True,
            "total_chamadas": total_chamadas,
            "atendidas": atendidas,
            "nao_atendidas": nao_atendidas,
            "duracao_media_segundos": duracao_media
        }

    async def _chat(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        if self.llm:
            response = await self.llm.generate(
                self.get_system_prompt(), params.get("message", "")
            )
            return {"success": True, "response": response}
        return {"error": "LLM não configurado"}


def create_voip_agent(
    condominio_id: str,
    llm_client: UnifiedLLMClient = None,
    memory: UnifiedMemorySystem = None,
    tools: ToolRegistry = None,
    evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT
) -> AgenteVoIP:
    return AgenteVoIP(
        condominio_id=condominio_id,
        llm_client=llm_client or UnifiedLLMClient(),
        memory=memory, tools=tools,
        evolution_level=evolution_level
    )
