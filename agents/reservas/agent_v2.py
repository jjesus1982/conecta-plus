"""
Conecta Plus - Agente de Reservas (Nível 7)
Sistema inteligente de gestão de áreas comuns

Capacidades:
1. REATIVO: Criar e cancelar reservas
2. PROATIVO: Alertar conflitos, sugerir horários
3. PREDITIVO: Prever demanda, otimizar agenda
4. AUTÔNOMO: Aprovar automaticamente, gerenciar lista espera
5. EVOLUTIVO: Aprender preferências dos moradores
6. COLABORATIVO: Integrar Financeiro, Comunicação, Portaria
7. TRANSCENDENTE: Gestão cognitiva de espaços
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta, date, time
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


class TipoEspaco(Enum):
    SALAO_FESTAS = "salao_festas"
    CHURRASQUEIRA = "churrasqueira"
    QUADRA = "quadra"
    PISCINA = "piscina"
    ACADEMIA = "academia"
    SAUNA = "sauna"
    PLAYGROUND = "playground"
    COWORKING = "coworking"


class StatusReserva(Enum):
    PENDENTE = "pendente"
    CONFIRMADA = "confirmada"
    EM_USO = "em_uso"
    CONCLUIDA = "concluida"
    CANCELADA = "cancelada"


@dataclass
class Espaco:
    id: str
    nome: str
    tipo: TipoEspaco
    capacidade: int
    taxa_reserva: float
    taxa_limpeza: float
    horario_abertura: time
    horario_fechamento: time
    antecedencia_minima_horas: int = 24
    antecedencia_maxima_dias: int = 30
    ativo: bool = True


@dataclass
class Reserva:
    id: str
    espaco_id: str
    unidade: str
    data: date
    hora_inicio: time
    hora_fim: time
    status: StatusReserva
    responsavel: str
    telefone: str
    num_convidados: int = 0
    observacoes: str = ""
    valor_total: float = 0.0
    data_criacao: datetime = field(default_factory=datetime.now)


class AgenteReservas(BaseAgent):
    """Agente de Reservas - Nível 7"""

    def __init__(
        self,
        condominio_id: str,
        llm_client: UnifiedLLMClient = None,
        memory: UnifiedMemorySystem = None,
        tools: ToolRegistry = None,
        evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT,
    ):
        super().__init__(
            agent_id=f"reservas_{condominio_id}",
            agent_type="reservas",
            condominio_id=condominio_id,
            evolution_level=evolution_level,
            llm_client=llm_client,
            memory_store=memory,
        )
        self.tools = tools
        self._espacos: Dict[str, Espaco] = {}
        self._reservas: Dict[str, Reserva] = {}
        self._lista_espera: List[Dict] = []

        self.config = {
            "aprovacao_automatica": True,
            "max_reservas_mes_unidade": 4,
            "permite_lista_espera": True,
            "cobranca_automatica": True,
        }

    def _register_capabilities(self) -> None:
        self._capabilities["gestao_reservas"] = AgentCapability(
            name="gestao_reservas", description="Criar e gerenciar reservas",
            level=EvolutionLevel.REACTIVE
        )
        self._capabilities["sugestao_horarios"] = AgentCapability(
            name="sugestao_horarios", description="Sugerir horários alternativos",
            level=EvolutionLevel.PROACTIVE
        )
        self._capabilities["previsao_demanda"] = AgentCapability(
            name="previsao_demanda", description="Prever demanda de espaços",
            level=EvolutionLevel.PREDICTIVE
        )
        self._capabilities["aprovacao_autonoma"] = AgentCapability(
            name="aprovacao_autonoma", description="Aprovar automaticamente",
            level=EvolutionLevel.AUTONOMOUS
        )
        self._capabilities["gestao_cognitiva"] = AgentCapability(
            name="gestao_cognitiva", description="Gestão cognitiva de espaços",
            level=EvolutionLevel.TRANSCENDENT
        )

    def get_system_prompt(self) -> str:
        return f"""Você é o Agente de Reservas do Conecta Plus.
ID: {self.agent_id} | Condomínio: {self.condominio_id} | Nível: {self.evolution_level.name}

Responsabilidades:
- Gerenciar reservas de áreas comuns
- Verificar disponibilidade de espaços
- Processar taxas e cobranças
- Notificar moradores sobre reservas
- Gerenciar lista de espera

Configurações:
- Aprovação automática: {self.config['aprovacao_automatica']}
- Máx reservas/mês: {self.config['max_reservas_mes_unidade']}
"""

    async def process(self, input_data: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        action = input_data.get("action", "")
        params = input_data.get("params", {})

        if action == "criar_reserva":
            return await self._criar_reserva(params, context)
        elif action == "cancelar_reserva":
            return await self._cancelar_reserva(params, context)
        elif action == "consultar_disponibilidade":
            return await self._consultar_disponibilidade(params, context)
        elif action == "listar_reservas":
            return await self._listar_reservas(params, context)
        elif action == "listar_espacos":
            return await self._listar_espacos(params, context)
        elif action == "sugerir_horarios":
            return await self._sugerir_horarios(params, context)
        elif action == "lista_espera":
            return await self._adicionar_lista_espera(params, context)
        elif action == "relatorio_ocupacao":
            return await self._relatorio_ocupacao(params, context)
        elif action == "chat":
            return await self._chat(params, context)
        else:
            return {"error": f"Ação '{action}' não reconhecida"}

    async def _criar_reserva(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        espaco_id = params.get("espaco_id")
        unidade = params.get("unidade")
        data_str = params.get("data")
        hora_inicio_str = params.get("hora_inicio")
        hora_fim_str = params.get("hora_fim")

        # Validar espaço
        if espaco_id not in self._espacos:
            return {"error": "Espaço não encontrado"}

        espaco = self._espacos[espaco_id]

        # Parse dates
        data = date.fromisoformat(data_str)
        hora_inicio = time.fromisoformat(hora_inicio_str)
        hora_fim = time.fromisoformat(hora_fim_str)

        # Verificar disponibilidade
        disponivel = await self._verificar_disponibilidade(espaco_id, data, hora_inicio, hora_fim)
        if not disponivel:
            # Sugerir horários alternativos
            if self.has_capability("sugestao_horarios"):
                alternativas = await self._sugerir_horarios({"espaco_id": espaco_id, "data": data_str}, context)
                return {
                    "success": False,
                    "error": "Horário não disponível",
                    "alternativas": alternativas.get("sugestoes", [])
                }
            return {"error": "Horário não disponível"}

        # Verificar limite de reservas do mês
        reservas_mes = len([r for r in self._reservas.values()
                          if r.unidade == unidade and r.data.month == data.month])
        if reservas_mes >= self.config["max_reservas_mes_unidade"]:
            return {"error": f"Limite de {self.config['max_reservas_mes_unidade']} reservas/mês atingido"}

        # Calcular valor
        valor_total = espaco.taxa_reserva + espaco.taxa_limpeza

        reserva = Reserva(
            id=f"reserva_{datetime.now().timestamp()}",
            espaco_id=espaco_id,
            unidade=unidade,
            data=data,
            hora_inicio=hora_inicio,
            hora_fim=hora_fim,
            status=StatusReserva.CONFIRMADA if self.config["aprovacao_automatica"] else StatusReserva.PENDENTE,
            responsavel=params.get("responsavel", ""),
            telefone=params.get("telefone", ""),
            num_convidados=params.get("num_convidados", 0),
            observacoes=params.get("observacoes", ""),
            valor_total=valor_total
        )
        self._reservas[reserva.id] = reserva

        # Processar cobrança
        if self.config["cobranca_automatica"] and self.has_capability("agent_collaboration"):
            await self.send_message(
                f"financeiro_{self.condominio_id}",
                {
                    "action": "gerar_cobranca",
                    "tipo": "taxa_reserva",
                    "unidade": unidade,
                    "valor": valor_total,
                    "descricao": f"Reserva {espaco.nome} - {data_str}"
                }
            )

        # Notificar
        if self.tools:
            await self.tools.execute(
                "send_notification",
                user_ids=[f"morador_{unidade}"],
                title="Reserva Confirmada",
                message=f"{espaco.nome} reservado para {data_str} das {hora_inicio_str} às {hora_fim_str}",
                channels=["push", "app"]
            )

        return {
            "success": True,
            "reserva_id": reserva.id,
            "espaco": espaco.nome,
            "data": data_str,
            "horario": f"{hora_inicio_str} - {hora_fim_str}",
            "valor": valor_total,
            "status": reserva.status.value
        }

    async def _verificar_disponibilidade(self, espaco_id: str, data: date, hora_inicio: time, hora_fim: time) -> bool:
        for reserva in self._reservas.values():
            if reserva.espaco_id != espaco_id:
                continue
            if reserva.data != data:
                continue
            if reserva.status in [StatusReserva.CANCELADA, StatusReserva.CONCLUIDA]:
                continue
            # Verificar sobreposição de horário
            if not (hora_fim <= reserva.hora_inicio or hora_inicio >= reserva.hora_fim):
                return False
        return True

    async def _cancelar_reserva(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        reserva_id = params.get("reserva_id")
        motivo = params.get("motivo", "")

        if reserva_id not in self._reservas:
            return {"error": "Reserva não encontrada"}

        reserva = self._reservas[reserva_id]
        reserva.status = StatusReserva.CANCELADA

        # Verificar lista de espera
        if self.config["permite_lista_espera"]:
            await self._processar_lista_espera(reserva.espaco_id, reserva.data)

        # Notificar
        if self.tools:
            await self.tools.execute(
                "send_notification",
                user_ids=[f"morador_{reserva.unidade}"],
                title="Reserva Cancelada",
                message=f"Sua reserva foi cancelada. Motivo: {motivo}",
                channels=["push", "app"]
            )

        return {
            "success": True,
            "reserva_id": reserva_id,
            "status": "cancelada"
        }

    async def _processar_lista_espera(self, espaco_id: str, data: date):
        for i, item in enumerate(self._lista_espera):
            if item["espaco_id"] == espaco_id and item["data"] == data.isoformat():
                # Notificar primeiro da lista
                if self.tools:
                    await self.tools.execute(
                        "send_notification",
                        user_ids=[f"morador_{item['unidade']}"],
                        title="Vaga Disponível!",
                        message=f"O espaço que você aguardava está disponível para {data.isoformat()}",
                        channels=["push", "app"]
                    )
                self._lista_espera.pop(i)
                break

    async def _consultar_disponibilidade(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        espaco_id = params.get("espaco_id")
        data_str = params.get("data")

        if espaco_id not in self._espacos:
            return {"error": "Espaço não encontrado"}

        espaco = self._espacos[espaco_id]
        data = date.fromisoformat(data_str)

        # Buscar reservas do dia
        reservas_dia = [r for r in self._reservas.values()
                       if r.espaco_id == espaco_id and r.data == data
                       and r.status not in [StatusReserva.CANCELADA, StatusReserva.CONCLUIDA]]

        horarios_ocupados = [(r.hora_inicio.isoformat(), r.hora_fim.isoformat()) for r in reservas_dia]

        return {
            "success": True,
            "espaco": espaco.nome,
            "data": data_str,
            "horario_funcionamento": f"{espaco.horario_abertura} - {espaco.horario_fechamento}",
            "horarios_ocupados": horarios_ocupados
        }

    async def _listar_reservas(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        unidade = params.get("unidade")
        espaco_id = params.get("espaco_id")
        status_filtro = params.get("status")
        data_inicio = params.get("data_inicio")
        data_fim = params.get("data_fim")

        reservas = list(self._reservas.values())

        if unidade:
            reservas = [r for r in reservas if r.unidade == unidade]
        if espaco_id:
            reservas = [r for r in reservas if r.espaco_id == espaco_id]
        if status_filtro:
            reservas = [r for r in reservas if r.status.value == status_filtro]
        if data_inicio:
            reservas = [r for r in reservas if r.data >= date.fromisoformat(data_inicio)]
        if data_fim:
            reservas = [r for r in reservas if r.data <= date.fromisoformat(data_fim)]

        reservas = sorted(reservas, key=lambda r: (r.data, r.hora_inicio))

        return {
            "success": True,
            "reservas": [
                {
                    "id": r.id,
                    "espaco_id": r.espaco_id,
                    "unidade": r.unidade,
                    "data": r.data.isoformat(),
                    "horario": f"{r.hora_inicio.isoformat()} - {r.hora_fim.isoformat()}",
                    "status": r.status.value,
                    "valor": r.valor_total
                }
                for r in reservas
            ]
        }

    async def _listar_espacos(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        tipo_filtro = params.get("tipo")
        apenas_ativos = params.get("apenas_ativos", True)

        espacos = list(self._espacos.values())

        if tipo_filtro:
            espacos = [e for e in espacos if e.tipo.value == tipo_filtro]
        if apenas_ativos:
            espacos = [e for e in espacos if e.ativo]

        return {
            "success": True,
            "espacos": [
                {
                    "id": e.id,
                    "nome": e.nome,
                    "tipo": e.tipo.value,
                    "capacidade": e.capacidade,
                    "taxa_reserva": e.taxa_reserva,
                    "taxa_limpeza": e.taxa_limpeza,
                    "horario": f"{e.horario_abertura} - {e.horario_fechamento}"
                }
                for e in espacos
            ]
        }

    async def _sugerir_horarios(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        espaco_id = params.get("espaco_id")
        data_str = params.get("data")

        if espaco_id not in self._espacos:
            return {"error": "Espaço não encontrado"}

        espaco = self._espacos[espaco_id]
        data = date.fromisoformat(data_str)

        # Buscar horários livres
        disponibilidade = await self._consultar_disponibilidade({"espaco_id": espaco_id, "data": data_str}, context)
        ocupados = disponibilidade.get("horarios_ocupados", [])

        # Gerar sugestões (simplificado)
        sugestoes = []
        hora_atual = espaco.horario_abertura
        while hora_atual < espaco.horario_fechamento:
            hora_fim = time(hora_atual.hour + 4, 0) if hora_atual.hour + 4 <= espaco.horario_fechamento.hour else espaco.horario_fechamento
            livre = True
            for inicio, fim in ocupados:
                if not (hora_fim.isoformat() <= inicio or hora_atual.isoformat() >= fim):
                    livre = False
                    break
            if livre:
                sugestoes.append({
                    "hora_inicio": hora_atual.isoformat(),
                    "hora_fim": hora_fim.isoformat()
                })
            hora_atual = time(hora_atual.hour + 1, 0)
            if hora_atual.hour >= espaco.horario_fechamento.hour:
                break

        return {"success": True, "sugestoes": sugestoes[:5]}

    async def _adicionar_lista_espera(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        if not self.config["permite_lista_espera"]:
            return {"error": "Lista de espera não habilitada"}

        self._lista_espera.append({
            "espaco_id": params.get("espaco_id"),
            "unidade": params.get("unidade"),
            "data": params.get("data"),
            "timestamp": datetime.now().isoformat()
        })

        return {
            "success": True,
            "posicao": len(self._lista_espera),
            "message": "Adicionado à lista de espera"
        }

    async def _relatorio_ocupacao(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        if not self.has_capability("gestao_cognitiva"):
            return {"error": "Capacidade transcendente não disponível"}

        periodo = params.get("periodo", "mes")

        # Calcular estatísticas
        total_reservas = len(self._reservas)
        por_espaco = {}
        for r in self._reservas.values():
            por_espaco[r.espaco_id] = por_espaco.get(r.espaco_id, 0) + 1

        if self.llm:
            prompt = f"""Analise a ocupação dos espaços comuns:
Total reservas: {total_reservas}
Por espaço: {por_espaco}
Período: {periodo}

Gere análise TRANSCENDENTE com:
1. Taxa de ocupação por espaço
2. Horários mais procurados
3. Padrões de uso
4. Sugestões de otimização
5. Previsão de demanda
"""
            response = await self.llm.generate(self.get_system_prompt(), prompt)
            return {"success": True, "relatorio": response}

        return {
            "success": True,
            "total_reservas": total_reservas,
            "por_espaco": por_espaco
        }

    async def _chat(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        if self.llm:
            response = await self.llm.generate(
                self.get_system_prompt(), params.get("message", "")
            )
            return {"success": True, "response": response}
        return {"error": "LLM não configurado"}


def create_reservations_agent(
    condominio_id: str,
    llm_client: UnifiedLLMClient = None,
    memory: UnifiedMemorySystem = None,
    tools: ToolRegistry = None,
    evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT
) -> AgenteReservas:
    return AgenteReservas(
        condominio_id=condominio_id,
        llm_client=llm_client or UnifiedLLMClient(),
        memory=memory, tools=tools,
        evolution_level=evolution_level
    )
