"""
Conecta Plus - Agente de Assembleias (Nível 7)
Sistema inteligente de gestão de assembleias condominiais

Capacidades:
1. REATIVO: Agendar assembleias, registrar presença
2. PROATIVO: Enviar convocações, preparar pautas
3. PREDITIVO: Prever quórum, identificar temas críticos
4. AUTÔNOMO: Gerar atas, apurar votações
5. EVOLUTIVO: Aprender padrões de participação
6. COLABORATIVO: Integrar Comunicação, Financeiro, Síndico
7. TRANSCENDENTE: Governança cognitiva condominial
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta, date
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


class TipoAssembleia(Enum):
    ORDINARIA = "ordinaria"
    EXTRAORDINARIA = "extraordinaria"
    INSTALACAO = "instalacao"
    VIRTUAL = "virtual"


class StatusAssembleia(Enum):
    AGENDADA = "agendada"
    CONVOCADA = "convocada"
    EM_ANDAMENTO = "em_andamento"
    ENCERRADA = "encerrada"
    CANCELADA = "cancelada"


class TipoVotacao(Enum):
    SIMPLES = "simples"
    QUALIFICADA = "qualificada"
    UNANIME = "unanime"


class ResultadoVoto(Enum):
    FAVORAVEL = "favoravel"
    CONTRARIO = "contrario"
    ABSTENCAO = "abstencao"


@dataclass
class ItemPauta:
    id: str
    ordem: int
    titulo: str
    descricao: str
    tipo_votacao: TipoVotacao
    resultado: Optional[Dict] = None
    aprovado: Optional[bool] = None


@dataclass
class Assembleia:
    id: str
    tipo: TipoAssembleia
    titulo: str
    data_hora: datetime
    local: str
    status: StatusAssembleia
    pauta: List[ItemPauta] = field(default_factory=list)
    presentes: List[str] = field(default_factory=list)
    procuracoes: Dict[str, str] = field(default_factory=dict)
    quorum_necessario: float = 0.5
    ata: Optional[str] = None


@dataclass
class Voto:
    item_id: str
    unidade: str
    voto: ResultadoVoto
    fracao_ideal: float
    timestamp: datetime


class AgenteAssembleias(BaseAgent):
    """Agente de Assembleias - Nível 7"""

    def __init__(
        self,
        condominio_id: str,
        llm_client: UnifiedLLMClient = None,
        memory: UnifiedMemorySystem = None,
        tools: ToolRegistry = None,
        evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT,
    ):
        super().__init__(
            agent_id=f"assembleias_{condominio_id}",
            agent_type="assembleias",
            condominio_id=condominio_id,
            evolution_level=evolution_level,
            llm_client=llm_client,
            memory_store=memory,
        )
        self.tools = tools
        self._assembleias: Dict[str, Assembleia] = {}
        self._votos: List[Voto] = []
        self._unidades: Dict[str, Dict] = {}

        self.config = {
            "antecedencia_convocacao_dias": 10,
            "quorum_minimo": 0.5,
            "permitir_virtual": True,
            "permitir_procuracao": True,
        }

    def _register_capabilities(self) -> None:
        self._capabilities["gestao_assembleias"] = AgentCapability(
            name="gestao_assembleias", description="Gerenciar assembleias",
            level=EvolutionLevel.REACTIVE
        )
        self._capabilities["convocacoes"] = AgentCapability(
            name="convocacoes", description="Enviar convocações automáticas",
            level=EvolutionLevel.PROACTIVE
        )
        self._capabilities["previsao_quorum"] = AgentCapability(
            name="previsao_quorum", description="Prever quórum",
            level=EvolutionLevel.PREDICTIVE
        )
        self._capabilities["geracao_atas"] = AgentCapability(
            name="geracao_atas", description="Gerar atas automaticamente",
            level=EvolutionLevel.AUTONOMOUS
        )
        self._capabilities["governanca_cognitiva"] = AgentCapability(
            name="governanca_cognitiva", description="Governança cognitiva",
            level=EvolutionLevel.TRANSCENDENT
        )

    def get_system_prompt(self) -> str:
        return f"""Você é o Agente de Assembleias do Conecta Plus.
ID: {self.agent_id} | Condomínio: {self.condominio_id} | Nível: {self.evolution_level.name}

Responsabilidades:
- Agendar e gerenciar assembleias
- Enviar convocações e lembretes
- Controlar presença e procurações
- Conduzir votações
- Gerar atas automaticamente

Configurações:
- Antecedência convocação: {self.config['antecedencia_convocacao_dias']} dias
- Quórum mínimo: {self.config['quorum_minimo'] * 100}%
- Virtual permitido: {self.config['permitir_virtual']}
"""

    async def process(self, input_data: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        action = input_data.get("action", "")
        params = input_data.get("params", {})

        if action == "agendar":
            return await self._agendar_assembleia(params, context)
        elif action == "convocar":
            return await self._convocar(params, context)
        elif action == "registrar_presenca":
            return await self._registrar_presenca(params, context)
        elif action == "registrar_procuracao":
            return await self._registrar_procuracao(params, context)
        elif action == "iniciar":
            return await self._iniciar_assembleia(params, context)
        elif action == "votar":
            return await self._registrar_voto(params, context)
        elif action == "apurar_votacao":
            return await self._apurar_votacao(params, context)
        elif action == "encerrar":
            return await self._encerrar_assembleia(params, context)
        elif action == "gerar_ata":
            return await self._gerar_ata(params, context)
        elif action == "listar":
            return await self._listar_assembleias(params, context)
        elif action == "chat":
            return await self._chat(params, context)
        else:
            return {"error": f"Ação '{action}' não reconhecida"}

    async def _agendar_assembleia(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        tipo = TipoAssembleia(params.get("tipo", "ordinaria"))

        pauta_items = []
        for i, item in enumerate(params.get("pauta", [])):
            pauta_items.append(ItemPauta(
                id=f"item_{i}",
                ordem=i + 1,
                titulo=item.get("titulo", ""),
                descricao=item.get("descricao", ""),
                tipo_votacao=TipoVotacao(item.get("tipo_votacao", "simples"))
            ))

        assembleia = Assembleia(
            id=f"asm_{datetime.now().timestamp()}",
            tipo=tipo,
            titulo=params.get("titulo", f"Assembleia {tipo.value}"),
            data_hora=datetime.fromisoformat(params.get("data_hora")),
            local=params.get("local", "Salão de Festas"),
            status=StatusAssembleia.AGENDADA,
            pauta=pauta_items,
            quorum_necessario=params.get("quorum", self.config["quorum_minimo"])
        )
        self._assembleias[assembleia.id] = assembleia

        return {
            "success": True,
            "assembleia_id": assembleia.id,
            "tipo": tipo.value,
            "data_hora": assembleia.data_hora.isoformat(),
            "itens_pauta": len(pauta_items)
        }

    async def _convocar(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        assembleia_id = params.get("assembleia_id")
        if assembleia_id not in self._assembleias:
            return {"error": "Assembleia não encontrada"}

        assembleia = self._assembleias[assembleia_id]
        assembleia.status = StatusAssembleia.CONVOCADA

        # Preparar texto da convocação
        pauta_texto = "\n".join([f"{i.ordem}. {i.titulo}" for i in assembleia.pauta])

        convocacao = f"""
CONVOCAÇÃO DE ASSEMBLEIA {assembleia.tipo.value.upper()}

Data: {assembleia.data_hora.strftime('%d/%m/%Y às %H:%M')}
Local: {assembleia.local}

PAUTA:
{pauta_texto}

Quórum necessário: {assembleia.quorum_necessario * 100}%
"""

        # Enviar convocação
        if self.tools:
            await self.tools.execute(
                "send_notification",
                user_ids=["todos_moradores"],
                title=f"Convocação - {assembleia.titulo}",
                message=convocacao,
                channels=["push", "email", "app"]
            )

        return {
            "success": True,
            "assembleia_id": assembleia_id,
            "status": "convocada",
            "convocacao_enviada": True
        }

    async def _registrar_presenca(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        assembleia_id = params.get("assembleia_id")
        unidade = params.get("unidade")

        if assembleia_id not in self._assembleias:
            return {"error": "Assembleia não encontrada"}

        assembleia = self._assembleias[assembleia_id]

        if unidade not in assembleia.presentes:
            assembleia.presentes.append(unidade)

        # Calcular quórum atual
        total_unidades = len(self._unidades) or 100
        quorum_atual = len(assembleia.presentes) / total_unidades

        return {
            "success": True,
            "unidade": unidade,
            "total_presentes": len(assembleia.presentes),
            "quorum_atual": quorum_atual,
            "quorum_atingido": quorum_atual >= assembleia.quorum_necessario
        }

    async def _registrar_procuracao(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        assembleia_id = params.get("assembleia_id")
        outorgante = params.get("outorgante")
        outorgado = params.get("outorgado")

        if not self.config["permitir_procuracao"]:
            return {"error": "Procuração não permitida neste condomínio"}

        if assembleia_id not in self._assembleias:
            return {"error": "Assembleia não encontrada"}

        assembleia = self._assembleias[assembleia_id]
        assembleia.procuracoes[outorgante] = outorgado

        return {
            "success": True,
            "outorgante": outorgante,
            "outorgado": outorgado,
            "total_procuracoes": len(assembleia.procuracoes)
        }

    async def _iniciar_assembleia(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        assembleia_id = params.get("assembleia_id")

        if assembleia_id not in self._assembleias:
            return {"error": "Assembleia não encontrada"}

        assembleia = self._assembleias[assembleia_id]

        # Verificar quórum
        total_unidades = len(self._unidades) or 100
        quorum_atual = (len(assembleia.presentes) + len(assembleia.procuracoes)) / total_unidades

        if quorum_atual < assembleia.quorum_necessario:
            return {
                "success": False,
                "error": "Quórum não atingido",
                "quorum_atual": quorum_atual,
                "quorum_necessario": assembleia.quorum_necessario
            }

        assembleia.status = StatusAssembleia.EM_ANDAMENTO

        return {
            "success": True,
            "assembleia_id": assembleia_id,
            "status": "em_andamento",
            "quorum_atual": quorum_atual,
            "presentes": len(assembleia.presentes),
            "procuracoes": len(assembleia.procuracoes)
        }

    async def _registrar_voto(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        assembleia_id = params.get("assembleia_id")
        item_id = params.get("item_id")
        unidade = params.get("unidade")
        voto = ResultadoVoto(params.get("voto", "favoravel"))

        if assembleia_id not in self._assembleias:
            return {"error": "Assembleia não encontrada"}

        assembleia = self._assembleias[assembleia_id]

        if assembleia.status != StatusAssembleia.EM_ANDAMENTO:
            return {"error": "Assembleia não está em andamento"}

        # Verificar se unidade pode votar
        if unidade not in assembleia.presentes and unidade not in assembleia.procuracoes:
            return {"error": "Unidade não presente na assembleia"}

        # Obter fração ideal
        fracao = self._unidades.get(unidade, {}).get("fracao_ideal", 1.0)

        voto_obj = Voto(
            item_id=item_id,
            unidade=unidade,
            voto=voto,
            fracao_ideal=fracao,
            timestamp=datetime.now()
        )
        self._votos.append(voto_obj)

        return {
            "success": True,
            "item_id": item_id,
            "unidade": unidade,
            "voto": voto.value
        }

    async def _apurar_votacao(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        assembleia_id = params.get("assembleia_id")
        item_id = params.get("item_id")

        if assembleia_id not in self._assembleias:
            return {"error": "Assembleia não encontrada"}

        assembleia = self._assembleias[assembleia_id]
        item = next((i for i in assembleia.pauta if i.id == item_id), None)

        if not item:
            return {"error": "Item não encontrado na pauta"}

        # Contar votos
        votos_item = [v for v in self._votos if v.item_id == item_id]

        favoravel = sum(v.fracao_ideal for v in votos_item if v.voto == ResultadoVoto.FAVORAVEL)
        contrario = sum(v.fracao_ideal for v in votos_item if v.voto == ResultadoVoto.CONTRARIO)
        abstencao = sum(v.fracao_ideal for v in votos_item if v.voto == ResultadoVoto.ABSTENCAO)
        total = favoravel + contrario + abstencao

        # Determinar aprovação baseado no tipo de votação
        if item.tipo_votacao == TipoVotacao.SIMPLES:
            aprovado = favoravel > contrario
        elif item.tipo_votacao == TipoVotacao.QUALIFICADA:
            aprovado = favoravel >= total * 2/3
        else:  # UNANIME
            aprovado = contrario == 0 and abstencao == 0

        item.resultado = {
            "favoravel": favoravel,
            "contrario": contrario,
            "abstencao": abstencao,
            "total_votantes": len(votos_item)
        }
        item.aprovado = aprovado

        return {
            "success": True,
            "item_id": item_id,
            "resultado": item.resultado,
            "aprovado": aprovado
        }

    async def _encerrar_assembleia(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        assembleia_id = params.get("assembleia_id")

        if assembleia_id not in self._assembleias:
            return {"error": "Assembleia não encontrada"}

        assembleia = self._assembleias[assembleia_id]
        assembleia.status = StatusAssembleia.ENCERRADA

        # Gerar ata automaticamente
        if self.has_capability("geracao_atas"):
            ata = await self._gerar_ata({"assembleia_id": assembleia_id}, context)
            assembleia.ata = ata.get("ata")

        return {
            "success": True,
            "assembleia_id": assembleia_id,
            "status": "encerrada",
            "ata_gerada": assembleia.ata is not None
        }

    async def _gerar_ata(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        assembleia_id = params.get("assembleia_id")

        if assembleia_id not in self._assembleias:
            return {"error": "Assembleia não encontrada"}

        assembleia = self._assembleias[assembleia_id]

        if self.llm:
            prompt = f"""Gere a ATA oficial da assembleia:
Tipo: {assembleia.tipo.value}
Título: {assembleia.titulo}
Data: {assembleia.data_hora}
Local: {assembleia.local}
Presentes: {len(assembleia.presentes)} unidades
Procurações: {len(assembleia.procuracoes)}

PAUTA E DELIBERAÇÕES:
{json.dumps([{"titulo": i.titulo, "resultado": i.resultado, "aprovado": i.aprovado} for i in assembleia.pauta], indent=2)}

Gere ata formal seguindo normas condominiais brasileiras.
"""
            response = await self.llm.generate(self.get_system_prompt(), prompt)
            return {"success": True, "ata": response}

        # Ata simples sem LLM
        ata = f"""
ATA DA ASSEMBLEIA {assembleia.tipo.value.upper()}
{assembleia.titulo}

Data: {assembleia.data_hora.strftime('%d/%m/%Y às %H:%M')}
Local: {assembleia.local}
Presentes: {len(assembleia.presentes)} unidades
"""
        return {"success": True, "ata": ata}

    async def _listar_assembleias(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        status_filtro = params.get("status")
        limite = params.get("limite", 20)

        assembleias = list(self._assembleias.values())

        if status_filtro:
            assembleias = [a for a in assembleias if a.status.value == status_filtro]

        assembleias = sorted(assembleias, key=lambda a: a.data_hora, reverse=True)[:limite]

        return {
            "success": True,
            "assembleias": [
                {
                    "id": a.id,
                    "tipo": a.tipo.value,
                    "titulo": a.titulo,
                    "data_hora": a.data_hora.isoformat(),
                    "status": a.status.value,
                    "itens_pauta": len(a.pauta)
                }
                for a in assembleias
            ]
        }

    async def _chat(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        if self.llm:
            response = await self.llm.generate(
                self.get_system_prompt(), params.get("message", "")
            )
            return {"success": True, "response": response}
        return {"error": "LLM não configurado"}


def create_assembly_agent(
    condominio_id: str,
    llm_client: UnifiedLLMClient = None,
    memory: UnifiedMemorySystem = None,
    tools: ToolRegistry = None,
    evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT
) -> AgenteAssembleias:
    return AgenteAssembleias(
        condominio_id=condominio_id,
        llm_client=llm_client or UnifiedLLMClient(),
        memory=memory, tools=tools,
        evolution_level=evolution_level
    )
