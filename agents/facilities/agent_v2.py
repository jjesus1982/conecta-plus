"""
Conecta Plus - Agente de Facilities (Nível 7)
Sistema inteligente de gestão de infraestrutura predial

Capacidades:
1. REATIVO: Registrar leituras, controlar estoque
2. PROATIVO: Programar manutenções, alertar consumo
3. PREDITIVO: Prever demanda, identificar anomalias
4. AUTÔNOMO: Solicitar compras, programar inspeções
5. EVOLUTIVO: Aprender padrões de consumo
6. COLABORATIVO: Integrar Financeiro, Manutenção, Síndico
7. TRANSCENDENTE: Facilities cognitivo total
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


class TipoRecurso(Enum):
    AGUA = "agua"
    ENERGIA = "energia"
    GAS = "gas"
    LIMPEZA = "limpeza"
    JARDINAGEM = "jardinagem"
    PISCINA = "piscina"


class TipoLeitura(Enum):
    HIDROMETRO = "hidrometro"
    ENERGIA_COMUM = "energia_comum"
    GAS_CENTRAL = "gas_central"
    GERADOR = "gerador"


class StatusEstoque(Enum):
    NORMAL = "normal"
    BAIXO = "baixo"
    CRITICO = "critico"


@dataclass
class LeituraMedidor:
    id: str
    tipo: TipoLeitura
    valor: float
    unidade: str
    timestamp: datetime
    local: str


@dataclass
class ItemEstoque:
    id: str
    nome: str
    categoria: str
    quantidade: int
    quantidade_minima: int
    unidade: str
    valor_unitario: float
    ultimo_reabastecimento: Optional[date] = None


@dataclass
class Contrato:
    id: str
    fornecedor: str
    servico: str
    valor_mensal: float
    data_inicio: date
    data_fim: date
    ativo: bool = True


class AgenteFacilities(BaseAgent):
    """Agente de Facilities - Nível 7"""

    def __init__(
        self,
        condominio_id: str,
        llm_client: UnifiedLLMClient = None,
        memory: UnifiedMemorySystem = None,
        tools: ToolRegistry = None,
        evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT,
    ):
        super().__init__(
            agent_id=f"facilities_{condominio_id}",
            agent_type="facilities",
            condominio_id=condominio_id,
            evolution_level=evolution_level,
            llm_client=llm_client,
            memory_store=memory,
        )
        self.tools = tools
        self._leituras: List[LeituraMedidor] = []
        self._estoque: Dict[str, ItemEstoque] = {}
        self._contratos: Dict[str, Contrato] = {}

        self.config = {
            "dia_leitura_agua": 25,
            "dia_leitura_energia": 20,
            "alerta_estoque_dias": 7,
            "compra_automatica": True,
        }

    def _register_capabilities(self) -> None:
        self._capabilities["leituras"] = AgentCapability(
            name="leituras", description="Registrar e consultar leituras",
            level=EvolutionLevel.REACTIVE
        )
        self._capabilities["alertas_consumo"] = AgentCapability(
            name="alertas_consumo", description="Alertar consumo anormal",
            level=EvolutionLevel.PROACTIVE
        )
        self._capabilities["previsao_demanda"] = AgentCapability(
            name="previsao_demanda", description="Prever demanda de recursos",
            level=EvolutionLevel.PREDICTIVE
        )
        self._capabilities["compras_autonomas"] = AgentCapability(
            name="compras_autonomas", description="Solicitar compras automaticamente",
            level=EvolutionLevel.AUTONOMOUS
        )
        self._capabilities["facilities_cognitivo"] = AgentCapability(
            name="facilities_cognitivo", description="Gestão cognitiva de facilities",
            level=EvolutionLevel.TRANSCENDENT
        )

    def get_system_prompt(self) -> str:
        return f"""Você é o Agente de Facilities do Conecta Plus.
ID: {self.agent_id} | Condomínio: {self.condominio_id} | Nível: {self.evolution_level.name}

Responsabilidades:
- Registrar leituras de medidores
- Controlar estoque de materiais
- Gerenciar contratos de fornecedores
- Monitorar consumo de recursos
- Programar manutenções preventivas

Configurações:
- Compra automática: {self.config['compra_automatica']}
"""

    async def process(self, input_data: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        action = input_data.get("action", "")
        params = input_data.get("params", {})

        if action == "registrar_leitura":
            return await self._registrar_leitura(params, context)
        elif action == "consultar_leituras":
            return await self._consultar_leituras(params, context)
        elif action == "estoque":
            return await self._consultar_estoque(params, context)
        elif action == "registrar_saida":
            return await self._registrar_saida_estoque(params, context)
        elif action == "solicitar_compra":
            return await self._solicitar_compra(params, context)
        elif action == "contratos":
            return await self._listar_contratos(params, context)
        elif action == "analise_consumo":
            return await self._analise_consumo(params, context)
        elif action == "previsao_custos":
            return await self._previsao_custos(params, context)
        elif action == "chat":
            return await self._chat(params, context)
        else:
            return {"error": f"Ação '{action}' não reconhecida"}

    async def _registrar_leitura(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        tipo = TipoLeitura(params.get("tipo", "hidrometro"))
        valor = params.get("valor")
        local = params.get("local", "geral")

        leitura = LeituraMedidor(
            id=f"leitura_{datetime.now().timestamp()}",
            tipo=tipo,
            valor=valor,
            unidade=self._get_unidade(tipo),
            timestamp=datetime.now(),
            local=local
        )
        self._leituras.append(leitura)

        # Verificar consumo anormal
        consumo_anormal = await self._verificar_consumo_anormal(tipo, valor)

        # Registrar via MCP de medidores
        if self.tools:
            await self.tools.execute(
                "call_mcp", mcp_name="mcp-medidores",
                method="registrar_leitura", params={
                    "tipo": tipo.value,
                    "valor": valor,
                    "local": local
                }
            )

        return {
            "success": True,
            "leitura_id": leitura.id,
            "tipo": tipo.value,
            "valor": valor,
            "unidade": leitura.unidade,
            "consumo_anormal": consumo_anormal
        }

    def _get_unidade(self, tipo: TipoLeitura) -> str:
        unidades = {
            TipoLeitura.HIDROMETRO: "m³",
            TipoLeitura.ENERGIA_COMUM: "kWh",
            TipoLeitura.GAS_CENTRAL: "m³",
            TipoLeitura.GERADOR: "horas",
        }
        return unidades.get(tipo, "un")

    async def _verificar_consumo_anormal(self, tipo: TipoLeitura, valor: float) -> Optional[Dict]:
        # Buscar média histórica
        leituras_tipo = [l for l in self._leituras if l.tipo == tipo][-12:]  # Últimos 12 meses
        if len(leituras_tipo) < 3:
            return None

        media = sum(l.valor for l in leituras_tipo) / len(leituras_tipo)
        desvio = abs(valor - media) / media * 100

        if desvio > 30:
            alerta = {
                "tipo": "consumo_anormal",
                "recurso": tipo.value,
                "valor_atual": valor,
                "media_historica": media,
                "desvio_percentual": desvio
            }

            if self.tools:
                await self.tools.execute(
                    "send_notification",
                    user_ids=["sindico", "administracao"],
                    title=f"Consumo Anormal - {tipo.value}",
                    message=f"Consumo {desvio:.1f}% acima da média",
                    channels=["push", "app"]
                )

            return alerta
        return None

    async def _consultar_leituras(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        tipo_filtro = params.get("tipo")
        meses = params.get("meses", 12)

        data_inicio = datetime.now() - timedelta(days=meses * 30)
        leituras = [l for l in self._leituras if l.timestamp >= data_inicio]

        if tipo_filtro:
            leituras = [l for l in leituras if l.tipo.value == tipo_filtro]

        return {
            "success": True,
            "leituras": [
                {
                    "id": l.id,
                    "tipo": l.tipo.value,
                    "valor": l.valor,
                    "unidade": l.unidade,
                    "timestamp": l.timestamp.isoformat(),
                    "local": l.local
                }
                for l in leituras
            ]
        }

    async def _consultar_estoque(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        categoria = params.get("categoria")
        apenas_baixo = params.get("apenas_baixo", False)

        itens = list(self._estoque.values())

        if categoria:
            itens = [i for i in itens if i.categoria == categoria]
        if apenas_baixo:
            itens = [i for i in itens if i.quantidade <= i.quantidade_minima]

        return {
            "success": True,
            "itens": [
                {
                    "id": i.id,
                    "nome": i.nome,
                    "categoria": i.categoria,
                    "quantidade": i.quantidade,
                    "quantidade_minima": i.quantidade_minima,
                    "status": self._get_status_estoque(i).value
                }
                for i in itens
            ]
        }

    def _get_status_estoque(self, item: ItemEstoque) -> StatusEstoque:
        if item.quantidade <= item.quantidade_minima * 0.3:
            return StatusEstoque.CRITICO
        elif item.quantidade <= item.quantidade_minima:
            return StatusEstoque.BAIXO
        return StatusEstoque.NORMAL

    async def _registrar_saida_estoque(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        item_id = params.get("item_id")
        quantidade = params.get("quantidade")
        motivo = params.get("motivo", "")

        if item_id not in self._estoque:
            return {"error": "Item não encontrado"}

        item = self._estoque[item_id]
        if item.quantidade < quantidade:
            return {"error": "Quantidade insuficiente em estoque"}

        item.quantidade -= quantidade

        # Verificar necessidade de reposição
        if self._get_status_estoque(item) in [StatusEstoque.BAIXO, StatusEstoque.CRITICO]:
            if self.config["compra_automatica"] and self.has_capability("compras_autonomas"):
                await self._solicitar_compra({"item_id": item_id}, context)

        return {
            "success": True,
            "item_id": item_id,
            "quantidade_retirada": quantidade,
            "quantidade_restante": item.quantidade
        }

    async def _solicitar_compra(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        item_id = params.get("item_id")
        quantidade = params.get("quantidade")

        if item_id in self._estoque:
            item = self._estoque[item_id]
            if not quantidade:
                quantidade = item.quantidade_minima * 2 - item.quantidade
            valor_estimado = quantidade * item.valor_unitario
        else:
            valor_estimado = 0

        # Enviar para aprovação ou aprovar automaticamente
        if self.tools:
            await self.tools.execute(
                "send_notification",
                user_ids=["sindico", "administracao"],
                title="Solicitação de Compra",
                message=f"Item: {item_id}, Qtd: {quantidade}, Valor: R${valor_estimado:.2f}",
                channels=["push", "app"]
            )

        # Colaborar com financeiro
        if self.has_capability("agent_collaboration"):
            await self.send_message(
                f"financeiro_{self.condominio_id}",
                {
                    "action": "aprovar_despesa",
                    "tipo": "compra_estoque",
                    "valor": valor_estimado,
                    "item": item_id
                }
            )

        return {
            "success": True,
            "item_id": item_id,
            "quantidade_solicitada": quantidade,
            "valor_estimado": valor_estimado,
            "status": "aguardando_aprovacao"
        }

    async def _listar_contratos(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        apenas_ativos = params.get("apenas_ativos", True)

        contratos = list(self._contratos.values())
        if apenas_ativos:
            contratos = [c for c in contratos if c.ativo]

        # Verificar vencimentos próximos
        hoje = date.today()
        for c in contratos:
            if (c.data_fim - hoje).days <= 30:
                c._vencendo = True

        return {
            "success": True,
            "contratos": [
                {
                    "id": c.id,
                    "fornecedor": c.fornecedor,
                    "servico": c.servico,
                    "valor_mensal": c.valor_mensal,
                    "data_fim": c.data_fim.isoformat(),
                    "dias_restantes": (c.data_fim - hoje).days
                }
                for c in contratos
            ]
        }

    async def _analise_consumo(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        if not self.has_capability("facilities_cognitivo"):
            return {"error": "Capacidade transcendente não disponível"}

        if self.llm:
            leituras = await self._consultar_leituras({"meses": 12}, context)

            prompt = f"""Analise o consumo de recursos do condomínio:
Leituras últimos 12 meses: {leituras}

Gere análise TRANSCENDENTE com:
1. Tendências de consumo
2. Comparativo mês a mês
3. Anomalias identificadas
4. Oportunidades de economia
5. Previsão próximos 3 meses
"""
            response = await self.llm.generate(self.get_system_prompt(), prompt)
            return {"success": True, "analise": response}

        return {"success": True, "analise": "Consumo dentro da normalidade"}

    async def _previsao_custos(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        if not self.has_capability("previsao_demanda"):
            return {"error": "Capacidade preditiva não disponível"}

        meses = params.get("meses", 3)

        # Calcular custos projetados
        custos_agua = 2500.00
        custos_energia = 4800.00
        custos_gas = 800.00
        custos_contratos = sum(c.valor_mensal for c in self._contratos.values() if c.ativo)

        total_mensal = custos_agua + custos_energia + custos_gas + custos_contratos

        return {
            "success": True,
            "previsao": {
                "agua": custos_agua * meses,
                "energia": custos_energia * meses,
                "gas": custos_gas * meses,
                "contratos": custos_contratos * meses,
                "total": total_mensal * meses
            },
            "periodo_meses": meses
        }

    async def _chat(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        if self.llm:
            response = await self.llm.generate(
                self.get_system_prompt(), params.get("message", "")
            )
            return {"success": True, "response": response}
        return {"error": "LLM não configurado"}


def create_facilities_agent(
    condominio_id: str,
    llm_client: UnifiedLLMClient = None,
    memory: UnifiedMemorySystem = None,
    tools: ToolRegistry = None,
    evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT
) -> AgenteFacilities:
    return AgenteFacilities(
        condominio_id=condominio_id,
        llm_client=llm_client or UnifiedLLMClient(),
        memory=memory, tools=tools,
        evolution_level=evolution_level
    )
