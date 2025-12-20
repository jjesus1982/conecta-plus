"""
Conecta Plus - Agente Imobiliário (Nível 7)
Gestor de unidades, locações e transações imobiliárias

Capacidades:
1. REATIVO: Registrar unidades, responder consultas
2. PROATIVO: Alertar vencimento de contratos, avaliar mercado
3. PREDITIVO: Prever vacância, tendências de preço
4. AUTÔNOMO: Gerar contratos, processar mudanças
5. EVOLUTIVO: Aprender padrões do mercado local
6. COLABORATIVO: Integrar Financeiro, Jurídico, Portaria
7. TRANSCENDENTE: Gestão imobiliária completa
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


class TipoUnidade(Enum):
    APARTAMENTO = "apartamento"
    COBERTURA = "cobertura"
    SALA_COMERCIAL = "sala_comercial"
    LOJA = "loja"
    GARAGEM = "garagem"
    DEPOSITO = "deposito"


class StatusUnidade(Enum):
    OCUPADA_PROPRIETARIO = "ocupada_proprietario"
    OCUPADA_LOCATARIO = "ocupada_locatario"
    VAGA = "vaga"
    EM_REFORMA = "em_reforma"
    AIRBNB = "airbnb"
    TEMPORADA = "temporada"


class TipoContrato(Enum):
    LOCACAO_RESIDENCIAL = "locacao_residencial"
    LOCACAO_COMERCIAL = "locacao_comercial"
    TEMPORADA = "temporada"
    AIRBNB = "airbnb"
    COMODATO = "comodato"


class StatusContrato(Enum):
    ATIVO = "ativo"
    VENCIDO = "vencido"
    RENOVADO = "renovado"
    RESCINDIDO = "rescindido"
    EM_NEGOCIACAO = "em_negociacao"


class StatusMudanca(Enum):
    AGENDADA = "agendada"
    EM_ANDAMENTO = "em_andamento"
    CONCLUIDA = "concluida"
    CANCELADA = "cancelada"


@dataclass
class Unidade:
    id: str
    numero: str
    bloco: Optional[str]
    tipo: TipoUnidade
    status: StatusUnidade
    area_m2: float
    quartos: int = 0
    vagas_garagem: int = 0
    proprietario_id: Optional[str] = None
    proprietario_nome: Optional[str] = None
    locatario_id: Optional[str] = None
    locatario_nome: Optional[str] = None
    valor_estimado: float = 0
    valor_aluguel: float = 0
    iptu_anual: float = 0
    fracao_ideal: float = 0


@dataclass
class ContratoLocacao:
    id: str
    unidade_id: str
    tipo: TipoContrato
    status: StatusContrato
    locador_id: str
    locador_nome: str
    locatario_id: str
    locatario_nome: str
    valor_aluguel: float
    dia_vencimento: int
    data_inicio: datetime
    data_fim: datetime
    clausulas_especiais: List[str] = field(default_factory=list)
    fiador: Optional[str] = None
    garantia: Optional[str] = None  # caucao, seguro, fiador
    reajuste: str = "igpm"
    historico_reajustes: List[Dict] = field(default_factory=list)


@dataclass
class Mudanca:
    id: str
    unidade_id: str
    tipo: str  # entrada, saida
    status: StatusMudanca
    data_agendada: datetime
    responsavel: str
    empresa_mudanca: Optional[str] = None
    observacoes: str = ""
    checklist_vistoria: Dict[str, bool] = field(default_factory=dict)
    fotos_antes: List[str] = field(default_factory=list)
    fotos_depois: List[str] = field(default_factory=list)


@dataclass
class AvaliacaoMercado:
    id: str
    unidade_id: str
    data_avaliacao: datetime
    valor_venda_estimado: float
    valor_aluguel_estimado: float
    comparativos: List[Dict] = field(default_factory=list)
    tendencia: str = "estavel"  # alta, estavel, baixa
    observacoes: str = ""


class AgenteImobiliario(BaseAgent):
    """Agente Imobiliário - Gestor de Unidades Nível 7"""

    def __init__(
        self,
        condominio_id: str,
        llm_client: UnifiedLLMClient = None,
        memory: UnifiedMemorySystem = None,
        tools: ToolRegistry = None,
        evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT,
    ):
        super().__init__(
            agent_id=f"imobiliario_{condominio_id}",
            agent_type="imobiliario",
            condominio_id=condominio_id,
            evolution_level=evolution_level,
            llm_client=llm_client,
            memory_store=memory,
        )
        self.tools = tools

        self._unidades: Dict[str, Unidade] = {}
        self._contratos: Dict[str, ContratoLocacao] = {}
        self._mudancas: List[Mudanca] = []
        self._avaliacoes: Dict[str, AvaliacaoMercado] = {}
        self._historico_ocupacao: List[Dict] = []

        self.config = {
            "dias_alerta_vencimento": 60,
            "permitir_airbnb": True,
            "taxa_administracao": 10.0,
            "horario_mudanca_inicio": "08:00",
            "horario_mudanca_fim": "18:00",
        }

    def _register_capabilities(self) -> None:
        self._capabilities["gestao_unidades"] = AgentCapability(
            name="gestao_unidades", description="Gerenciar unidades do condomínio",
            level=EvolutionLevel.REACTIVE
        )
        self._capabilities["gestao_contratos"] = AgentCapability(
            name="gestao_contratos", description="Gerenciar contratos de locação",
            level=EvolutionLevel.PROACTIVE
        )
        self._capabilities["avaliacao_mercado"] = AgentCapability(
            name="avaliacao_mercado", description="Avaliar valor de mercado",
            level=EvolutionLevel.PREDICTIVE
        )
        self._capabilities["gestao_mudancas"] = AgentCapability(
            name="gestao_mudancas", description="Gerenciar mudanças",
            level=EvolutionLevel.AUTONOMOUS
        )
        self._capabilities["gestao_imobiliaria_total"] = AgentCapability(
            name="gestao_imobiliaria_total", description="Gestão imobiliária completa",
            level=EvolutionLevel.TRANSCENDENT
        )

    def get_system_prompt(self) -> str:
        return f"""Você é o Agente Imobiliário do Conecta Plus.
ID: {self.agent_id} | Condomínio: {self.condominio_id} | Nível: {self.evolution_level.name}

RESPONSABILIDADES:
- Cadastro e gestão de unidades
- Contratos de locação e temporada
- Controle de Airbnb/temporada
- Agendamento de mudanças
- Avaliação de mercado
- Vistoria de entrada/saída

COMPORTAMENTO:
- Mantenha dados atualizados
- Alerte sobre vencimentos
- Sugira valores de mercado
- Coordene com outros agentes
"""

    async def process(self, input_data: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        action = input_data.get("action", "")
        params = input_data.get("params", {})

        if action == "cadastrar_unidade":
            return await self._cadastrar_unidade(params, context)
        elif action == "atualizar_unidade":
            return await self._atualizar_unidade(params, context)
        elif action == "listar_unidades":
            return await self._listar_unidades(params, context)
        elif action == "cadastrar_contrato":
            return await self._cadastrar_contrato(params, context)
        elif action == "renovar_contrato":
            return await self._renovar_contrato(params, context)
        elif action == "rescindir_contrato":
            return await self._rescindir_contrato(params, context)
        elif action == "listar_contratos":
            return await self._listar_contratos(params, context)
        elif action == "agendar_mudanca":
            return await self._agendar_mudanca(params, context)
        elif action == "registrar_vistoria":
            return await self._registrar_vistoria(params, context)
        elif action == "avaliar_mercado":
            return await self._avaliar_mercado(params, context)
        elif action == "unidades_disponiveis":
            return await self._unidades_disponiveis(params, context)
        elif action == "contratos_vencendo":
            return await self._contratos_vencendo(params, context)
        elif action == "registrar_airbnb":
            return await self._registrar_airbnb(params, context)
        elif action == "ocupacao_historico":
            return await self._ocupacao_historico(params, context)
        elif action == "dashboard":
            return await self._dashboard(params, context)
        elif action == "chat":
            return await self._chat(params, context)
        else:
            return {"error": f"Ação '{action}' não reconhecida"}

    async def _cadastrar_unidade(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Cadastrar unidade"""
        numero = params.get("numero")
        bloco = params.get("bloco")
        tipo = params.get("tipo", "apartamento")
        area = params.get("area_m2", 0)
        quartos = params.get("quartos", 0)
        vagas = params.get("vagas_garagem", 0)
        proprietario_id = params.get("proprietario_id")
        proprietario_nome = params.get("proprietario_nome")
        fracao = params.get("fracao_ideal", 0)

        unidade_id = f"{bloco}_{numero}" if bloco else numero

        unidade = Unidade(
            id=unidade_id,
            numero=numero,
            bloco=bloco,
            tipo=TipoUnidade[tipo.upper()],
            status=StatusUnidade.OCUPADA_PROPRIETARIO if proprietario_id else StatusUnidade.VAGA,
            area_m2=area,
            quartos=quartos,
            vagas_garagem=vagas,
            proprietario_id=proprietario_id,
            proprietario_nome=proprietario_nome,
            fracao_ideal=fracao
        )
        self._unidades[unidade_id] = unidade

        return {
            "success": True,
            "unidade_id": unidade_id,
            "numero": numero,
            "status": unidade.status.value
        }

    async def _atualizar_unidade(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Atualizar unidade"""
        unidade_id = params.get("unidade_id")

        if unidade_id not in self._unidades:
            return {"error": "Unidade não encontrada"}

        unidade = self._unidades[unidade_id]

        if "status" in params:
            unidade.status = StatusUnidade[params["status"].upper()]
        if "proprietario_id" in params:
            unidade.proprietario_id = params["proprietario_id"]
        if "proprietario_nome" in params:
            unidade.proprietario_nome = params["proprietario_nome"]
        if "locatario_id" in params:
            unidade.locatario_id = params["locatario_id"]
        if "locatario_nome" in params:
            unidade.locatario_nome = params["locatario_nome"]
        if "valor_estimado" in params:
            unidade.valor_estimado = params["valor_estimado"]
        if "valor_aluguel" in params:
            unidade.valor_aluguel = params["valor_aluguel"]

        return {
            "success": True,
            "unidade_id": unidade_id,
            "status": unidade.status.value
        }

    async def _listar_unidades(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Listar unidades"""
        status = params.get("status")
        tipo = params.get("tipo")
        bloco = params.get("bloco")

        unidades = list(self._unidades.values())

        if status:
            unidades = [u for u in unidades if u.status.value == status]
        if tipo:
            unidades = [u for u in unidades if u.tipo.value == tipo]
        if bloco:
            unidades = [u for u in unidades if u.bloco == bloco]

        return {
            "success": True,
            "total": len(unidades),
            "unidades": [
                {
                    "id": u.id,
                    "numero": u.numero,
                    "bloco": u.bloco,
                    "tipo": u.tipo.value,
                    "status": u.status.value,
                    "area_m2": u.area_m2,
                    "proprietario": u.proprietario_nome,
                    "locatario": u.locatario_nome,
                    "valor_aluguel": u.valor_aluguel
                }
                for u in unidades
            ]
        }

    async def _cadastrar_contrato(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Cadastrar contrato de locação"""
        unidade_id = params.get("unidade_id")
        tipo = params.get("tipo", "locacao_residencial")
        locador_id = params.get("locador_id")
        locador_nome = params.get("locador_nome")
        locatario_id = params.get("locatario_id")
        locatario_nome = params.get("locatario_nome")
        valor = params.get("valor_aluguel")
        dia_vencimento = params.get("dia_vencimento", 10)
        data_inicio = params.get("data_inicio")
        duracao_meses = params.get("duracao_meses", 30)
        garantia = params.get("garantia")
        fiador = params.get("fiador")

        if unidade_id not in self._unidades:
            return {"error": "Unidade não encontrada"}

        data_inicio_dt = datetime.fromisoformat(data_inicio) if data_inicio else datetime.now()
        data_fim = data_inicio_dt + timedelta(days=duracao_meses * 30)

        contrato = ContratoLocacao(
            id=f"contrato_{datetime.now().timestamp()}",
            unidade_id=unidade_id,
            tipo=TipoContrato[tipo.upper()],
            status=StatusContrato.ATIVO,
            locador_id=locador_id,
            locador_nome=locador_nome,
            locatario_id=locatario_id,
            locatario_nome=locatario_nome,
            valor_aluguel=valor,
            dia_vencimento=dia_vencimento,
            data_inicio=data_inicio_dt,
            data_fim=data_fim,
            garantia=garantia,
            fiador=fiador
        )
        self._contratos[contrato.id] = contrato

        # Atualizar unidade
        unidade = self._unidades[unidade_id]
        unidade.status = StatusUnidade.OCUPADA_LOCATARIO
        unidade.locatario_id = locatario_id
        unidade.locatario_nome = locatario_nome
        unidade.valor_aluguel = valor

        # Notificar financeiro
        if self.has_capability("agent_collaboration"):
            await self.send_message(
                f"financeiro_{self.condominio_id}",
                {
                    "action": "registrar_locacao",
                    "unidade_id": unidade_id,
                    "locatario_id": locatario_id,
                    "valor": valor,
                    "dia_vencimento": dia_vencimento
                }
            )

        return {
            "success": True,
            "contrato_id": contrato.id,
            "unidade": unidade_id,
            "locatario": locatario_nome,
            "valor": valor,
            "vigencia": f"{data_inicio_dt.date()} a {data_fim.date()}"
        }

    async def _renovar_contrato(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Renovar contrato"""
        contrato_id = params.get("contrato_id")
        novo_valor = params.get("novo_valor")
        duracao_meses = params.get("duracao_meses", 12)

        if contrato_id not in self._contratos:
            return {"error": "Contrato não encontrado"}

        contrato = self._contratos[contrato_id]

        # Registrar reajuste
        if novo_valor and novo_valor != contrato.valor_aluguel:
            contrato.historico_reajustes.append({
                "data": datetime.now().isoformat(),
                "valor_anterior": contrato.valor_aluguel,
                "valor_novo": novo_valor,
                "percentual": ((novo_valor - contrato.valor_aluguel) / contrato.valor_aluguel) * 100
            })
            contrato.valor_aluguel = novo_valor

        # Atualizar datas
        contrato.data_inicio = datetime.now()
        contrato.data_fim = datetime.now() + timedelta(days=duracao_meses * 30)
        contrato.status = StatusContrato.RENOVADO

        return {
            "success": True,
            "contrato_id": contrato_id,
            "novo_valor": novo_valor,
            "nova_vigencia": f"{contrato.data_inicio.date()} a {contrato.data_fim.date()}"
        }

    async def _rescindir_contrato(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Rescindir contrato"""
        contrato_id = params.get("contrato_id")
        motivo = params.get("motivo")
        data_saida = params.get("data_saida")

        if contrato_id not in self._contratos:
            return {"error": "Contrato não encontrado"}

        contrato = self._contratos[contrato_id]
        contrato.status = StatusContrato.RESCINDIDO

        # Atualizar unidade
        if contrato.unidade_id in self._unidades:
            unidade = self._unidades[contrato.unidade_id]
            unidade.status = StatusUnidade.VAGA
            unidade.locatario_id = None
            unidade.locatario_nome = None

        # Agendar vistoria de saída
        await self._agendar_mudanca({
            "unidade_id": contrato.unidade_id,
            "tipo": "saida",
            "data": data_saida,
            "responsavel": contrato.locatario_nome
        }, context)

        return {
            "success": True,
            "contrato_id": contrato_id,
            "status": "rescindido",
            "motivo": motivo,
            "data_saida": data_saida
        }

    async def _listar_contratos(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Listar contratos"""
        status = params.get("status")
        unidade_id = params.get("unidade_id")

        contratos = list(self._contratos.values())

        if status:
            contratos = [c for c in contratos if c.status.value == status]
        if unidade_id:
            contratos = [c for c in contratos if c.unidade_id == unidade_id]

        return {
            "success": True,
            "total": len(contratos),
            "contratos": [
                {
                    "id": c.id,
                    "unidade": c.unidade_id,
                    "tipo": c.tipo.value,
                    "status": c.status.value,
                    "locatario": c.locatario_nome,
                    "valor": c.valor_aluguel,
                    "inicio": c.data_inicio.isoformat(),
                    "fim": c.data_fim.isoformat()
                }
                for c in contratos
            ]
        }

    async def _agendar_mudanca(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Agendar mudança"""
        unidade_id = params.get("unidade_id")
        tipo = params.get("tipo", "entrada")
        data = params.get("data")
        responsavel = params.get("responsavel")
        empresa = params.get("empresa_mudanca")

        data_mudanca = datetime.fromisoformat(data) if data else datetime.now() + timedelta(days=7)

        mudanca = Mudanca(
            id=f"mudanca_{datetime.now().timestamp()}",
            unidade_id=unidade_id,
            tipo=tipo,
            status=StatusMudanca.AGENDADA,
            data_agendada=data_mudanca,
            responsavel=responsavel,
            empresa_mudanca=empresa,
            checklist_vistoria={
                "pintura": False,
                "piso": False,
                "eletrica": False,
                "hidraulica": False,
                "vidros": False,
                "fechaduras": False,
                "limpeza": False
            }
        )
        self._mudancas.append(mudanca)

        # Notificar portaria
        if self.has_capability("agent_collaboration"):
            await self.send_message(
                f"portaria_virtual_{self.condominio_id}",
                {
                    "action": "agendar_mudanca",
                    "unidade_id": unidade_id,
                    "data": data_mudanca.isoformat(),
                    "tipo": tipo,
                    "responsavel": responsavel
                }
            )

        return {
            "success": True,
            "mudanca_id": mudanca.id,
            "unidade": unidade_id,
            "tipo": tipo,
            "data": data_mudanca.isoformat(),
            "checklist_pendente": True
        }

    async def _registrar_vistoria(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Registrar vistoria de mudança"""
        mudanca_id = params.get("mudanca_id")
        checklist = params.get("checklist", {})
        fotos = params.get("fotos", [])
        observacoes = params.get("observacoes")

        mudanca = next((m for m in self._mudancas if m.id == mudanca_id), None)
        if not mudanca:
            return {"error": "Mudança não encontrada"}

        mudanca.checklist_vistoria.update(checklist)

        if mudanca.tipo == "entrada":
            mudanca.fotos_antes = fotos
        else:
            mudanca.fotos_depois = fotos

        if observacoes:
            mudanca.observacoes = observacoes

        # Verificar se vistoria está completa
        vistoria_completa = all(mudanca.checklist_vistoria.values())

        if vistoria_completa:
            mudanca.status = StatusMudanca.CONCLUIDA

        return {
            "success": True,
            "mudanca_id": mudanca_id,
            "checklist": mudanca.checklist_vistoria,
            "vistoria_completa": vistoria_completa,
            "fotos_registradas": len(fotos)
        }

    async def _avaliar_mercado(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Avaliar valor de mercado da unidade"""
        unidade_id = params.get("unidade_id")

        if unidade_id not in self._unidades:
            return {"error": "Unidade não encontrada"}

        unidade = self._unidades[unidade_id]

        # Valores estimados (em produção, usar API de mercado)
        preco_m2_venda = 8500  # Valor médio fictício
        preco_m2_aluguel = 45

        valor_venda = unidade.area_m2 * preco_m2_venda
        valor_aluguel = unidade.area_m2 * preco_m2_aluguel

        # Ajustes por características
        if unidade.tipo == TipoUnidade.COBERTURA:
            valor_venda *= 1.3
            valor_aluguel *= 1.25
        if unidade.vagas_garagem > 1:
            valor_venda += 50000 * (unidade.vagas_garagem - 1)
            valor_aluguel += 300 * (unidade.vagas_garagem - 1)

        avaliacao = AvaliacaoMercado(
            id=f"aval_{datetime.now().timestamp()}",
            unidade_id=unidade_id,
            data_avaliacao=datetime.now(),
            valor_venda_estimado=valor_venda,
            valor_aluguel_estimado=valor_aluguel,
            tendencia="estavel",
            observacoes=f"Avaliação baseada em {unidade.area_m2}m² e {unidade.quartos} quartos"
        )
        self._avaliacoes[avaliacao.id] = avaliacao

        return {
            "success": True,
            "unidade_id": unidade_id,
            "valor_venda_estimado": valor_venda,
            "valor_aluguel_estimado": valor_aluguel,
            "preco_m2_venda": preco_m2_venda,
            "preco_m2_aluguel": preco_m2_aluguel,
            "tendencia": "estavel",
            "data_avaliacao": avaliacao.data_avaliacao.isoformat()
        }

    async def _unidades_disponiveis(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Listar unidades disponíveis para locação/venda"""
        finalidade = params.get("finalidade", "locacao")  # locacao, venda

        disponiveis = [u for u in self._unidades.values() if u.status == StatusUnidade.VAGA]

        return {
            "success": True,
            "finalidade": finalidade,
            "total": len(disponiveis),
            "unidades": [
                {
                    "id": u.id,
                    "numero": u.numero,
                    "bloco": u.bloco,
                    "tipo": u.tipo.value,
                    "area_m2": u.area_m2,
                    "quartos": u.quartos,
                    "vagas": u.vagas_garagem,
                    "valor_estimado": u.valor_estimado,
                    "valor_aluguel": u.valor_aluguel
                }
                for u in disponiveis
            ]
        }

    async def _contratos_vencendo(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Listar contratos próximos do vencimento"""
        dias = params.get("dias", self.config["dias_alerta_vencimento"])

        limite = datetime.now() + timedelta(days=dias)

        vencendo = [
            c for c in self._contratos.values()
            if c.status == StatusContrato.ATIVO and c.data_fim <= limite
        ]

        return {
            "success": True,
            "dias_antecedencia": dias,
            "total": len(vencendo),
            "contratos": [
                {
                    "id": c.id,
                    "unidade": c.unidade_id,
                    "locatario": c.locatario_nome,
                    "valor": c.valor_aluguel,
                    "vencimento": c.data_fim.isoformat(),
                    "dias_restantes": (c.data_fim - datetime.now()).days
                }
                for c in sorted(vencendo, key=lambda x: x.data_fim)
            ]
        }

    async def _registrar_airbnb(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Registrar unidade como Airbnb/temporada"""
        unidade_id = params.get("unidade_id")
        responsavel = params.get("responsavel")
        regras = params.get("regras_especiais", [])

        if not self.config["permitir_airbnb"]:
            return {"error": "Airbnb não permitido neste condomínio"}

        if unidade_id not in self._unidades:
            return {"error": "Unidade não encontrada"}

        unidade = self._unidades[unidade_id]
        unidade.status = StatusUnidade.AIRBNB

        # Notificar portaria
        if self.has_capability("agent_collaboration"):
            await self.send_message(
                f"portaria_virtual_{self.condominio_id}",
                {
                    "action": "registrar_airbnb",
                    "unidade_id": unidade_id,
                    "responsavel": responsavel,
                    "regras": regras
                }
            )

        return {
            "success": True,
            "unidade_id": unidade_id,
            "status": "airbnb",
            "responsavel": responsavel
        }

    async def _ocupacao_historico(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Histórico de ocupação"""
        unidades = list(self._unidades.values())

        ocupadas = len([u for u in unidades if u.status in [
            StatusUnidade.OCUPADA_PROPRIETARIO,
            StatusUnidade.OCUPADA_LOCATARIO,
            StatusUnidade.AIRBNB,
            StatusUnidade.TEMPORADA
        ]])

        vagas = len([u for u in unidades if u.status == StatusUnidade.VAGA])
        em_reforma = len([u for u in unidades if u.status == StatusUnidade.EM_REFORMA])

        taxa_ocupacao = (ocupadas / len(unidades) * 100) if unidades else 0

        return {
            "success": True,
            "total_unidades": len(unidades),
            "ocupadas": ocupadas,
            "vagas": vagas,
            "em_reforma": em_reforma,
            "taxa_ocupacao": round(taxa_ocupacao, 1),
            "por_tipo_ocupacao": {
                status.value: len([u for u in unidades if u.status == status])
                for status in StatusUnidade
            }
        }

    async def _dashboard(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Dashboard imobiliário"""
        unidades = list(self._unidades.values())
        contratos = list(self._contratos.values())

        # Contratos vencendo em 60 dias
        limite = datetime.now() + timedelta(days=60)
        vencendo = [c for c in contratos if c.status == StatusContrato.ATIVO and c.data_fim <= limite]

        # Mudanças agendadas
        mudancas_pendentes = [m for m in self._mudancas if m.status == StatusMudanca.AGENDADA]

        # Valor total em aluguéis
        receita_aluguel = sum(c.valor_aluguel for c in contratos if c.status == StatusContrato.ATIVO)

        return {
            "success": True,
            "resumo": {
                "total_unidades": len(unidades),
                "ocupadas": len([u for u in unidades if u.status != StatusUnidade.VAGA]),
                "vagas": len([u for u in unidades if u.status == StatusUnidade.VAGA]),
                "contratos_ativos": len([c for c in contratos if c.status == StatusContrato.ATIVO]),
                "contratos_vencendo": len(vencendo),
                "mudancas_agendadas": len(mudancas_pendentes),
                "receita_aluguel_mensal": receita_aluguel
            },
            "unidades_por_tipo": {
                tipo.value: len([u for u in unidades if u.tipo == tipo])
                for tipo in TipoUnidade
            },
            "alertas": {
                "contratos_vencendo": [
                    {"unidade": c.unidade_id, "locatario": c.locatario_nome, "vencimento": c.data_fim.isoformat()}
                    for c in vencendo[:5]
                ],
                "mudancas_proximas": [
                    {"unidade": m.unidade_id, "tipo": m.tipo, "data": m.data_agendada.isoformat()}
                    for m in mudancas_pendentes[:5]
                ]
            }
        }

    async def _chat(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        if self.llm:
            response = await self.llm.generate(
                self.get_system_prompt(), params.get("message", "")
            )
            return {"success": True, "response": response}
        return {"error": "LLM não configurado"}


def create_real_estate_agent(
    condominio_id: str,
    llm_client: UnifiedLLMClient = None,
    memory: UnifiedMemorySystem = None,
    tools: ToolRegistry = None,
    evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT
) -> AgenteImobiliario:
    """Factory function para criar agente imobiliário"""
    return AgenteImobiliario(
        condominio_id=condominio_id,
        llm_client=llm_client or UnifiedLLMClient(),
        memory=memory,
        tools=tools,
        evolution_level=evolution_level
    )
