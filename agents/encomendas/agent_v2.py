"""
Conecta Plus - Agente de Encomendas (Nível 7)
Sistema inteligente de gestão de encomendas e correspondências

Capacidades:
1. REATIVO: Registrar, notificar, entregar
2. PROATIVO: Alertar pendentes, lembrar retirada
3. PREDITIVO: Prever horários de entrega
4. AUTÔNOMO: Organizar logística, otimizar espaço
5. EVOLUTIVO: Aprender padrões de recebimento
6. COLABORATIVO: Integrar Portaria, Comunicação, Morador
7. TRANSCENDENTE: Logística cognitiva de correspondências
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


class TipoEncomenda(Enum):
    CORREIOS = "correios"
    TRANSPORTADORA = "transportadora"
    DELIVERY = "delivery"
    DOCUMENTO = "documento"
    CARGA = "carga"


class StatusEncomenda(Enum):
    RECEBIDA = "recebida"
    ARMAZENADA = "armazenada"
    NOTIFICADA = "notificada"
    ENTREGUE = "entregue"
    DEVOLVIDA = "devolvida"


class TamanhoEncomenda(Enum):
    PEQUENO = "pequeno"
    MEDIO = "medio"
    GRANDE = "grande"
    VOLUMOSO = "volumoso"


@dataclass
class Encomenda:
    id: str
    tipo: TipoEncomenda
    unidade_destino: str
    remetente: str
    transportadora: str
    codigo_rastreio: Optional[str]
    tamanho: TamanhoEncomenda
    status: StatusEncomenda
    local_armazenamento: str
    recebido_por: str
    data_recebimento: datetime
    data_entrega: Optional[datetime] = None
    retirado_por: Optional[str] = None
    observacoes: str = ""
    foto_url: Optional[str] = None
    notificacoes_enviadas: int = 0


class AgenteEncomendas(BaseAgent):
    """Agente de Encomendas - Nível 7"""

    def __init__(
        self,
        condominio_id: str,
        llm_client: UnifiedLLMClient = None,
        memory: UnifiedMemorySystem = None,
        tools: ToolRegistry = None,
        evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT,
    ):
        super().__init__(
            agent_id=f"encomendas_{condominio_id}",
            agent_type="encomendas",
            condominio_id=condominio_id,
            evolution_level=evolution_level,
            llm_client=llm_client,
            memory_store=memory,
        )
        self.tools = tools
        self._encomendas: Dict[str, Encomenda] = {}
        self._locais_armazenamento: Dict[str, int] = {
            "prateleira_1": 20,
            "prateleira_2": 20,
            "area_volumes": 10,
            "armario_documentos": 50
        }

        self.config = {
            "notificar_automatico": True,
            "lembrete_pendentes_dias": 3,
            "max_dias_armazenamento": 30,
            "foto_obrigatoria": True,
        }

    def _register_capabilities(self) -> None:
        self._capabilities["gestao_encomendas"] = AgentCapability(
            name="gestao_encomendas", description="Registrar e entregar encomendas",
            level=EvolutionLevel.REACTIVE
        )
        self._capabilities["alertas_pendentes"] = AgentCapability(
            name="alertas_pendentes", description="Alertar encomendas pendentes",
            level=EvolutionLevel.PROACTIVE
        )
        self._capabilities["previsao_entregas"] = AgentCapability(
            name="previsao_entregas", description="Prever horários de entrega",
            level=EvolutionLevel.PREDICTIVE
        )
        self._capabilities["logistica_autonoma"] = AgentCapability(
            name="logistica_autonoma", description="Organizar logística automaticamente",
            level=EvolutionLevel.AUTONOMOUS
        )
        self._capabilities["logistica_cognitiva"] = AgentCapability(
            name="logistica_cognitiva", description="Logística cognitiva de correspondências",
            level=EvolutionLevel.TRANSCENDENT
        )

    def get_system_prompt(self) -> str:
        return f"""Você é o Agente de Encomendas do Conecta Plus.
ID: {self.agent_id} | Condomínio: {self.condominio_id} | Nível: {self.evolution_level.name}

Responsabilidades:
- Registrar chegada de encomendas
- Notificar moradores
- Controlar entregas e retiradas
- Gerenciar espaço de armazenamento
- Rastrear correspondências

Configurações:
- Notificação automática: {self.config['notificar_automatico']}
- Lembrete após: {self.config['lembrete_pendentes_dias']} dias
- Máx armazenamento: {self.config['max_dias_armazenamento']} dias
"""

    async def process(self, input_data: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        action = input_data.get("action", "")
        params = input_data.get("params", {})

        if action == "registrar":
            return await self._registrar_encomenda(params, context)
        elif action == "entregar":
            return await self._entregar_encomenda(params, context)
        elif action == "listar_encomendas":
            return await self._listar_encomendas(params, context)
        elif action == "pendentes_unidade":
            return await self._pendentes_unidade(params, context)
        elif action == "buscar_rastreio":
            return await self._buscar_rastreio(params, context)
        elif action == "reenviar_notificacao":
            return await self._reenviar_notificacao(params, context)
        elif action == "relatorio":
            return await self._relatorio(params, context)
        elif action == "espaco_disponivel":
            return await self._espaco_disponivel(params, context)
        elif action == "chat":
            return await self._chat(params, context)
        else:
            return {"error": f"Ação '{action}' não reconhecida"}

    async def _registrar_encomenda(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        tipo = TipoEncomenda(params.get("tipo", "correios"))
        tamanho = TamanhoEncomenda(params.get("tamanho", "medio"))

        # Determinar local de armazenamento
        local = self._selecionar_local(tamanho)
        if not local:
            return {"error": "Sem espaço disponível para armazenamento"}

        encomenda = Encomenda(
            id=f"enc_{datetime.now().timestamp()}",
            tipo=tipo,
            unidade_destino=params.get("unidade"),
            remetente=params.get("remetente", ""),
            transportadora=params.get("transportadora", ""),
            codigo_rastreio=params.get("codigo_rastreio"),
            tamanho=tamanho,
            status=StatusEncomenda.RECEBIDA,
            local_armazenamento=local,
            recebido_por=params.get("recebido_por", "portaria"),
            data_recebimento=datetime.now(),
            foto_url=params.get("foto_url"),
            observacoes=params.get("observacoes", "")
        )
        self._encomendas[encomenda.id] = encomenda

        # Atualizar espaço
        self._locais_armazenamento[local] -= 1

        # Notificar morador
        if self.config["notificar_automatico"] and self.tools:
            await self.tools.execute(
                "send_notification",
                user_ids=[f"morador_{encomenda.unidade_destino}"],
                title="Encomenda Recebida!",
                message=f"Uma encomenda de {encomenda.remetente or encomenda.transportadora} chegou para você.",
                channels=["push", "app"]
            )
            encomenda.notificacoes_enviadas += 1
            encomenda.status = StatusEncomenda.NOTIFICADA

        return {
            "success": True,
            "encomenda_id": encomenda.id,
            "local_armazenamento": local,
            "status": encomenda.status.value
        }

    def _selecionar_local(self, tamanho: TamanhoEncomenda) -> Optional[str]:
        if tamanho == TamanhoEncomenda.VOLUMOSO:
            if self._locais_armazenamento["area_volumes"] > 0:
                return "area_volumes"
        elif tamanho == TamanhoEncomenda.PEQUENO:
            if self._locais_armazenamento["armario_documentos"] > 0:
                return "armario_documentos"

        # Prateleiras para médio/grande
        if self._locais_armazenamento["prateleira_1"] > 0:
            return "prateleira_1"
        if self._locais_armazenamento["prateleira_2"] > 0:
            return "prateleira_2"

        return None

    async def _entregar_encomenda(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        encomenda_id = params.get("encomenda_id")
        retirado_por = params.get("retirado_por")
        documento = params.get("documento")

        if encomenda_id not in self._encomendas:
            return {"error": "Encomenda não encontrada"}

        encomenda = self._encomendas[encomenda_id]

        if encomenda.status == StatusEncomenda.ENTREGUE:
            return {"error": "Encomenda já foi entregue"}

        # Liberar espaço
        self._locais_armazenamento[encomenda.local_armazenamento] += 1

        encomenda.status = StatusEncomenda.ENTREGUE
        encomenda.data_entrega = datetime.now()
        encomenda.retirado_por = retirado_por

        return {
            "success": True,
            "encomenda_id": encomenda_id,
            "status": "entregue",
            "retirado_por": retirado_por,
            "tempo_armazenamento": str(encomenda.data_entrega - encomenda.data_recebimento)
        }

    async def _listar_encomendas(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        status_filtro = params.get("status")
        unidade = params.get("unidade")
        data_inicio = params.get("data_inicio")
        limite = params.get("limite", 50)

        encomendas = list(self._encomendas.values())

        if status_filtro:
            encomendas = [e for e in encomendas if e.status.value == status_filtro]
        if unidade:
            encomendas = [e for e in encomendas if e.unidade_destino == unidade]
        if data_inicio:
            dt = datetime.fromisoformat(data_inicio)
            encomendas = [e for e in encomendas if e.data_recebimento >= dt]

        encomendas = sorted(encomendas, key=lambda e: e.data_recebimento, reverse=True)[:limite]

        return {
            "success": True,
            "encomendas": [
                {
                    "id": e.id,
                    "tipo": e.tipo.value,
                    "unidade": e.unidade_destino,
                    "remetente": e.remetente,
                    "transportadora": e.transportadora,
                    "status": e.status.value,
                    "local": e.local_armazenamento,
                    "data_recebimento": e.data_recebimento.isoformat()
                }
                for e in encomendas
            ]
        }

    async def _pendentes_unidade(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        unidade = params.get("unidade")

        pendentes = [e for e in self._encomendas.values()
                    if e.unidade_destino == unidade
                    and e.status in [StatusEncomenda.RECEBIDA, StatusEncomenda.NOTIFICADA, StatusEncomenda.ARMAZENADA]]

        return {
            "success": True,
            "unidade": unidade,
            "total_pendentes": len(pendentes),
            "encomendas": [
                {
                    "id": e.id,
                    "tipo": e.tipo.value,
                    "remetente": e.remetente or e.transportadora,
                    "local": e.local_armazenamento,
                    "dias_aguardando": (datetime.now() - e.data_recebimento).days
                }
                for e in pendentes
            ]
        }

    async def _buscar_rastreio(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        codigo = params.get("codigo_rastreio")

        encomendas = [e for e in self._encomendas.values() if e.codigo_rastreio == codigo]

        if not encomendas:
            return {"error": "Encomenda não encontrada com este código de rastreio"}

        encomenda = encomendas[0]

        return {
            "success": True,
            "encomenda_id": encomenda.id,
            "codigo_rastreio": codigo,
            "status": encomenda.status.value,
            "unidade": encomenda.unidade_destino
        }

    async def _reenviar_notificacao(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        encomenda_id = params.get("encomenda_id")

        if encomenda_id not in self._encomendas:
            return {"error": "Encomenda não encontrada"}

        encomenda = self._encomendas[encomenda_id]

        if self.tools:
            await self.tools.execute(
                "send_notification",
                user_ids=[f"morador_{encomenda.unidade_destino}"],
                title="Lembrete: Encomenda Aguardando",
                message=f"Você tem uma encomenda aguardando retirada há {(datetime.now() - encomenda.data_recebimento).days} dias.",
                channels=["push", "app", "sms"]
            )
            encomenda.notificacoes_enviadas += 1

        return {
            "success": True,
            "encomenda_id": encomenda_id,
            "notificacoes_enviadas": encomenda.notificacoes_enviadas
        }

    async def _relatorio(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        if not self.has_capability("logistica_cognitiva"):
            return {"error": "Capacidade transcendente não disponível"}

        periodo = params.get("periodo", "mes")

        # Estatísticas
        todas = list(self._encomendas.values())
        pendentes = [e for e in todas if e.status not in [StatusEncomenda.ENTREGUE, StatusEncomenda.DEVOLVIDA]]
        entregues = [e for e in todas if e.status == StatusEncomenda.ENTREGUE]

        if self.llm:
            prompt = f"""Analise a logística de encomendas:
Total registradas: {len(todas)}
Pendentes: {len(pendentes)}
Entregues: {len(entregues)}
Período: {periodo}

Gere análise TRANSCENDENTE com:
1. Volume por tipo de encomenda
2. Tempo médio de retirada
3. Unidades com mais pendências
4. Previsão de demanda
5. Otimizações de espaço sugeridas
"""
            response = await self.llm.generate(self.get_system_prompt(), prompt)
            return {"success": True, "relatorio": response}

        return {
            "success": True,
            "total": len(todas),
            "pendentes": len(pendentes),
            "entregues": len(entregues)
        }

    async def _espaco_disponivel(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        return {
            "success": True,
            "locais": self._locais_armazenamento,
            "total_disponivel": sum(self._locais_armazenamento.values())
        }

    async def _chat(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        if self.llm:
            response = await self.llm.generate(
                self.get_system_prompt(), params.get("message", "")
            )
            return {"success": True, "response": response}
        return {"error": "LLM não configurado"}


def create_packages_agent(
    condominio_id: str,
    llm_client: UnifiedLLMClient = None,
    memory: UnifiedMemorySystem = None,
    tools: ToolRegistry = None,
    evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT
) -> AgenteEncomendas:
    return AgenteEncomendas(
        condominio_id=condominio_id,
        llm_client=llm_client or UnifiedLLMClient(),
        memory=memory, tools=tools,
        evolution_level=evolution_level
    )
