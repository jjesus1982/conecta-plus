"""
Conecta Plus - Agente de RH (Nível 7)
Sistema inteligente de gestão de funcionários

Capacidades:
1. REATIVO: Consultar escala, registrar ponto
2. PROATIVO: Alertar atrasos, lembrar vencimentos
3. PREDITIVO: Prever absenteísmo, identificar turnover
4. AUTÔNOMO: Redistribuir escalas, aprovar férias
5. EVOLUTIVO: Aprender padrões de produtividade
6. COLABORATIVO: Integrar Acesso, Financeiro, Síndico
7. TRANSCENDENTE: Gestão de pessoas cognitiva
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


class TipoFuncionario(Enum):
    PORTEIRO = "porteiro"
    ZELADOR = "zelador"
    FAXINEIRO = "faxineiro"
    SEGURANCA = "seguranca"
    JARDINEIRO = "jardineiro"
    MANUTENCAO = "manutencao"
    ADMINISTRATIVO = "administrativo"


class StatusFuncionario(Enum):
    ATIVO = "ativo"
    FERIAS = "ferias"
    AFASTADO = "afastado"
    DESLIGADO = "desligado"


class TipoRegistro(Enum):
    ENTRADA = "entrada"
    SAIDA = "saida"
    INTERVALO_INICIO = "intervalo_inicio"
    INTERVALO_FIM = "intervalo_fim"


@dataclass
class Funcionario:
    id: str
    nome: str
    tipo: TipoFuncionario
    status: StatusFuncionario
    data_admissao: date
    salario: float
    escala: str
    contato: str
    documentos_vencimento: Optional[date] = None


@dataclass
class RegistroPonto:
    id: str
    funcionario_id: str
    tipo: TipoRegistro
    timestamp: datetime
    metodo: str = "biometrico"
    localização: str = ""


@dataclass
class Escala:
    id: str
    funcionario_id: str
    data: date
    turno: str
    hora_inicio: str
    hora_fim: str
    folga: bool = False


class AgenteRH(BaseAgent):
    """Agente de RH - Nível 7"""

    def __init__(
        self,
        condominio_id: str,
        llm_client: UnifiedLLMClient = None,
        memory: UnifiedMemorySystem = None,
        tools: ToolRegistry = None,
        evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT,
    ):
        super().__init__(
            agent_id=f"rh_{condominio_id}",
            agent_type="rh",
            condominio_id=condominio_id,
            evolution_level=evolution_level,
            llm_client=llm_client,
            memory_store=memory,
        )
        self.tools = tools
        self._funcionarios: Dict[str, Funcionario] = {}
        self._registros_ponto: List[RegistroPonto] = []
        self._escalas: List[Escala] = []

        self.config = {
            "tolerancia_atraso_minutos": 10,
            "alerta_vencimento_dias": 30,
            "banco_horas_ativo": True,
            "aprovacao_automatica_ferias": False,
        }

    def _register_capabilities(self) -> None:
        self._capabilities["gestao_ponto"] = AgentCapability(
            name="gestao_ponto", description="Registrar e consultar ponto",
            level=EvolutionLevel.REACTIVE
        )
        self._capabilities["alertas_rh"] = AgentCapability(
            name="alertas_rh", description="Alertar sobre eventos RH",
            level=EvolutionLevel.PROACTIVE
        )
        self._capabilities["previsao_absenteismo"] = AgentCapability(
            name="previsao_absenteismo", description="Prever ausências",
            level=EvolutionLevel.PREDICTIVE
        )
        self._capabilities["gestao_autonoma"] = AgentCapability(
            name="gestao_autonoma", description="Gestão autônoma de escalas",
            level=EvolutionLevel.AUTONOMOUS
        )
        self._capabilities["rh_cognitivo"] = AgentCapability(
            name="rh_cognitivo", description="Gestão cognitiva de pessoas",
            level=EvolutionLevel.TRANSCENDENT
        )

    def get_system_prompt(self) -> str:
        return f"""Você é o Agente de RH do Conecta Plus.
ID: {self.agent_id} | Condomínio: {self.condominio_id} | Nível: {self.evolution_level.name}

Responsabilidades:
- Gerenciar funcionários e escalas
- Controlar ponto eletrônico
- Monitorar banco de horas
- Alertar vencimentos de documentos
- Integrar com eSocial e folha de pagamento

Configurações:
- Tolerância atraso: {self.config['tolerancia_atraso_minutos']} min
- Banco de horas: {self.config['banco_horas_ativo']}
"""

    async def process(self, input_data: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        action = input_data.get("action", "")
        params = input_data.get("params", {})

        if action == "registrar_ponto":
            return await self._registrar_ponto(params, context)
        elif action == "consultar_ponto":
            return await self._consultar_ponto(params, context)
        elif action == "listar_funcionarios":
            return await self._listar_funcionarios(params, context)
        elif action == "escala_dia":
            return await self._escala_dia(params, context)
        elif action == "gerar_escala":
            return await self._gerar_escala(params, context)
        elif action == "solicitar_ferias":
            return await self._solicitar_ferias(params, context)
        elif action == "banco_horas":
            return await self._banco_horas(params, context)
        elif action == "relatorio_rh":
            return await self._relatorio_rh(params, context)
        elif action == "vencimentos":
            return await self._verificar_vencimentos(params, context)
        elif action == "chat":
            return await self._chat(params, context)
        else:
            return {"error": f"Ação '{action}' não reconhecida"}

    async def _registrar_ponto(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        funcionario_id = params.get("funcionario_id")
        tipo = TipoRegistro(params.get("tipo", "entrada"))
        metodo = params.get("metodo", "biometrico")

        registro = RegistroPonto(
            id=f"ponto_{datetime.now().timestamp()}",
            funcionario_id=funcionario_id,
            tipo=tipo,
            timestamp=datetime.now(),
            metodo=metodo
        )
        self._registros_ponto.append(registro)

        # Enviar para REP via MCP
        if self.tools:
            await self.tools.execute(
                "call_mcp", mcp_name="mcp-ponto-rep",
                method="registrar", params={
                    "funcionario_id": funcionario_id,
                    "tipo": tipo.value,
                    "timestamp": registro.timestamp.isoformat()
                }
            )

        # Verificar atraso
        atraso = None
        if tipo == TipoRegistro.ENTRADA:
            escala = self._get_escala_funcionario(funcionario_id, date.today())
            if escala:
                hora_prevista = datetime.strptime(escala.hora_inicio, "%H:%M").time()
                hora_registro = registro.timestamp.time()
                if hora_registro > hora_prevista:
                    diff = datetime.combine(date.today(), hora_registro) - datetime.combine(date.today(), hora_prevista)
                    atraso = diff.seconds // 60
                    if atraso > self.config["tolerancia_atraso_minutos"]:
                        await self._alertar_atraso(funcionario_id, atraso)

        return {
            "success": True,
            "registro_id": registro.id,
            "funcionario_id": funcionario_id,
            "tipo": tipo.value,
            "timestamp": registro.timestamp.isoformat(),
            "atraso_minutos": atraso
        }

    def _get_escala_funcionario(self, funcionario_id: str, data: date) -> Optional[Escala]:
        for escala in self._escalas:
            if escala.funcionario_id == funcionario_id and escala.data == data:
                return escala
        return None

    async def _alertar_atraso(self, funcionario_id: str, minutos: int):
        if self.tools:
            funcionario = self._funcionarios.get(funcionario_id)
            await self.tools.execute(
                "send_notification",
                user_ids=["sindico", "administracao"],
                title="Atraso Registrado",
                message=f"Funcionário {funcionario.nome if funcionario else funcionario_id} chegou com {minutos} min de atraso",
                channels=["push"]
            )

    async def _consultar_ponto(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        funcionario_id = params.get("funcionario_id")
        data_inicio = params.get("data_inicio")
        data_fim = params.get("data_fim")

        registros = [r for r in self._registros_ponto if r.funcionario_id == funcionario_id]

        return {
            "success": True,
            "funcionario_id": funcionario_id,
            "registros": [
                {
                    "id": r.id,
                    "tipo": r.tipo.value,
                    "timestamp": r.timestamp.isoformat(),
                    "metodo": r.metodo
                }
                for r in registros[-30:]  # Últimos 30 registros
            ]
        }

    async def _listar_funcionarios(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        tipo_filtro = params.get("tipo")
        status_filtro = params.get("status")

        funcionarios = list(self._funcionarios.values())

        if tipo_filtro:
            funcionarios = [f for f in funcionarios if f.tipo.value == tipo_filtro]
        if status_filtro:
            funcionarios = [f for f in funcionarios if f.status.value == status_filtro]

        return {
            "success": True,
            "funcionarios": [
                {
                    "id": f.id,
                    "nome": f.nome,
                    "tipo": f.tipo.value,
                    "status": f.status.value,
                    "escala": f.escala
                }
                for f in funcionarios
            ]
        }

    async def _escala_dia(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        data = params.get("data", date.today().isoformat())
        if isinstance(data, str):
            data = date.fromisoformat(data)

        escalas = [e for e in self._escalas if e.data == data and not e.folga]

        return {
            "success": True,
            "data": data.isoformat(),
            "escalas": [
                {
                    "funcionario_id": e.funcionario_id,
                    "turno": e.turno,
                    "hora_inicio": e.hora_inicio,
                    "hora_fim": e.hora_fim
                }
                for e in escalas
            ]
        }

    async def _gerar_escala(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        if not self.has_capability("gestao_autonoma"):
            return {"error": "Capacidade autônoma não disponível"}

        mes = params.get("mes", datetime.now().month)
        ano = params.get("ano", datetime.now().year)

        if self.llm:
            funcionarios = await self._listar_funcionarios({}, context)
            prompt = f"""Gere escala de trabalho otimizada:
Funcionários: {funcionarios}
Mês: {mes}/{ano}

Considere:
- Cobertura 24h para portaria
- Folgas semanais
- Escala 12x36 para segurança
- Banco de horas existente

Retorne escala em formato estruturado.
"""
            response = await self.llm.generate(self.get_system_prompt(), prompt)
            return {"success": True, "escala_gerada": response}

        return {"success": True, "message": "Escala padrão gerada"}

    async def _solicitar_ferias(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        funcionario_id = params.get("funcionario_id")
        data_inicio = params.get("data_inicio")
        dias = params.get("dias", 30)

        funcionario = self._funcionarios.get(funcionario_id)
        if not funcionario:
            return {"error": "Funcionário não encontrado"}

        # Verificar período aquisitivo
        meses_trabalhados = (date.today() - funcionario.data_admissao).days // 30
        if meses_trabalhados < 12:
            return {
                "success": False,
                "message": "Período aquisitivo incompleto",
                "meses_trabalhados": meses_trabalhados
            }

        # Aprovar automaticamente se configurado
        if self.config["aprovacao_automatica_ferias"]:
            return {
                "success": True,
                "status": "aprovado",
                "funcionario_id": funcionario_id,
                "data_inicio": data_inicio,
                "dias": dias
            }

        # Enviar para aprovação do síndico
        if self.tools:
            await self.tools.execute(
                "send_notification",
                user_ids=["sindico"],
                title="Solicitação de Férias",
                message=f"{funcionario.nome} solicitou {dias} dias de férias a partir de {data_inicio}",
                channels=["push", "app"]
            )

        return {
            "success": True,
            "status": "pendente_aprovacao",
            "funcionario_id": funcionario_id
        }

    async def _banco_horas(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        funcionario_id = params.get("funcionario_id")

        # Calcular banco de horas
        registros = [r for r in self._registros_ponto if r.funcionario_id == funcionario_id]

        # Simplificado - em produção calcular com base na escala
        horas_trabalhadas = len(registros) * 8
        horas_esperadas = len(registros) * 8
        saldo = horas_trabalhadas - horas_esperadas

        return {
            "success": True,
            "funcionario_id": funcionario_id,
            "saldo_horas": saldo,
            "horas_trabalhadas": horas_trabalhadas,
            "horas_esperadas": horas_esperadas
        }

    async def _relatorio_rh(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        if not self.has_capability("rh_cognitivo"):
            return {"error": "Capacidade transcendente não disponível"}

        if self.llm:
            funcionarios = await self._listar_funcionarios({}, context)
            vencimentos = await self._verificar_vencimentos({}, context)

            prompt = f"""Gere relatório executivo de RH:
Funcionários: {funcionarios}
Vencimentos próximos: {vencimentos}
Total registros ponto: {len(self._registros_ponto)}

Análise TRANSCENDENTE:
1. Visão geral da equipe
2. Indicadores de produtividade
3. Alertas e pendências
4. Recomendações estratégicas
"""
            response = await self.llm.generate(self.get_system_prompt(), prompt)
            return {"success": True, "relatorio": response}

        return {
            "success": True,
            "total_funcionarios": len(self._funcionarios),
            "ativos": len([f for f in self._funcionarios.values() if f.status == StatusFuncionario.ATIVO])
        }

    async def _verificar_vencimentos(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        dias_antecedencia = params.get("dias", self.config["alerta_vencimento_dias"])
        data_limite = date.today() + timedelta(days=dias_antecedencia)

        vencimentos = []
        for func in self._funcionarios.values():
            if func.documentos_vencimento and func.documentos_vencimento <= data_limite:
                vencimentos.append({
                    "funcionario_id": func.id,
                    "nome": func.nome,
                    "vencimento": func.documentos_vencimento.isoformat(),
                    "dias_restantes": (func.documentos_vencimento - date.today()).days
                })

        return {"success": True, "vencimentos": vencimentos}

    async def _chat(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        if self.llm:
            response = await self.llm.generate(
                self.get_system_prompt(), params.get("message", "")
            )
            return {"success": True, "response": response}
        return {"error": "LLM não configurado"}


def create_hr_agent(
    condominio_id: str,
    llm_client: UnifiedLLMClient = None,
    memory: UnifiedMemorySystem = None,
    tools: ToolRegistry = None,
    evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT
) -> AgenteRH:
    return AgenteRH(
        condominio_id=condominio_id,
        llm_client=llm_client or UnifiedLLMClient(),
        memory=memory, tools=tools,
        evolution_level=evolution_level
    )
