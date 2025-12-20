"""
Conecta Plus - Agente de Ocorrências (Nível 7)
Sistema inteligente de registro e gestão de ocorrências

Capacidades:
1. REATIVO: Registrar ocorrências, atribuir responsáveis
2. PROATIVO: Alertar padrões, escalar pendências
3. PREDITIVO: Prever tipos de ocorrências, identificar tendências
4. AUTÔNOMO: Classificar automaticamente, priorizar
5. EVOLUTIVO: Aprender padrões de problemas
6. COLABORATIVO: Integrar Manutenção, Segurança, Síndico
7. TRANSCENDENTE: Gestão cognitiva de conflitos
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


class TipoOcorrencia(Enum):
    BARULHO = "barulho"
    VAZAMENTO = "vazamento"
    VANDALISMO = "vandalismo"
    ESTACIONAMENTO = "estacionamento"
    ANIMAL = "animal"
    LIXO = "lixo"
    SEGURANCA = "seguranca"
    CONVIVENCIA = "convivencia"
    ESTRUTURAL = "estrutural"
    OUTROS = "outros"


class StatusOcorrencia(Enum):
    ABERTA = "aberta"
    EM_ANALISE = "em_analise"
    EM_TRATAMENTO = "em_tratamento"
    AGUARDANDO_RESPOSTA = "aguardando_resposta"
    RESOLVIDA = "resolvida"
    ARQUIVADA = "arquivada"


class PrioridadeOcorrencia(Enum):
    BAIXA = "baixa"
    MEDIA = "media"
    ALTA = "alta"
    CRITICA = "critica"


@dataclass
class Ocorrencia:
    id: str
    tipo: TipoOcorrencia
    titulo: str
    descricao: str
    local: str
    prioridade: PrioridadeOcorrencia
    status: StatusOcorrencia
    registrado_por: str
    unidade_origem: str
    data_registro: datetime
    responsavel: Optional[str] = None
    unidade_envolvida: Optional[str] = None
    data_resolucao: Optional[datetime] = None
    resolucao: str = ""
    anexos: List[str] = field(default_factory=list)
    historico: List[Dict] = field(default_factory=list)


class AgenteOcorrencias(BaseAgent):
    """Agente de Ocorrências - Nível 7"""

    def __init__(
        self,
        condominio_id: str,
        llm_client: UnifiedLLMClient = None,
        memory: UnifiedMemorySystem = None,
        tools: ToolRegistry = None,
        evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT,
    ):
        super().__init__(
            agent_id=f"ocorrencias_{condominio_id}",
            agent_type="ocorrencias",
            condominio_id=condominio_id,
            evolution_level=evolution_level,
            llm_client=llm_client,
            memory_store=memory,
        )
        self.tools = tools
        self._ocorrencias: Dict[str, Ocorrencia] = {}

        self.config = {
            "classificacao_automatica": True,
            "escalar_dias": 7,
            "notificar_sindico_criticas": True,
            "anonimato_permitido": True,
        }

    def _register_capabilities(self) -> None:
        self._capabilities["gestao_ocorrencias"] = AgentCapability(
            name="gestao_ocorrencias", description="Registrar e gerenciar ocorrências",
            level=EvolutionLevel.REACTIVE
        )
        self._capabilities["alertas_padroes"] = AgentCapability(
            name="alertas_padroes", description="Alertar padrões de ocorrências",
            level=EvolutionLevel.PROACTIVE
        )
        self._capabilities["previsao_ocorrencias"] = AgentCapability(
            name="previsao_ocorrencias", description="Prever tipos de ocorrências",
            level=EvolutionLevel.PREDICTIVE
        )
        self._capabilities["classificacao_autonoma"] = AgentCapability(
            name="classificacao_autonoma", description="Classificar automaticamente",
            level=EvolutionLevel.AUTONOMOUS
        )
        self._capabilities["gestao_conflitos"] = AgentCapability(
            name="gestao_conflitos", description="Gestão cognitiva de conflitos",
            level=EvolutionLevel.TRANSCENDENT
        )

    def get_system_prompt(self) -> str:
        return f"""Você é o Agente de Ocorrências do Conecta Plus.
ID: {self.agent_id} | Condomínio: {self.condominio_id} | Nível: {self.evolution_level.name}

Responsabilidades:
- Registrar ocorrências e reclamações
- Classificar e priorizar automaticamente
- Atribuir responsáveis
- Acompanhar resolução
- Identificar padrões e tendências

Configurações:
- Classificação automática: {self.config['classificacao_automatica']}
- Escalar após: {self.config['escalar_dias']} dias
"""

    async def process(self, input_data: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        action = input_data.get("action", "")
        params = input_data.get("params", {})

        if action == "registrar":
            return await self._registrar_ocorrencia(params, context)
        elif action == "atualizar":
            return await self._atualizar_ocorrencia(params, context)
        elif action == "listar":
            return await self._listar_ocorrencias(params, context)
        elif action == "detalhes":
            return await self._detalhes_ocorrencia(params, context)
        elif action == "atribuir":
            return await self._atribuir_responsavel(params, context)
        elif action == "resolver":
            return await self._resolver_ocorrencia(params, context)
        elif action == "adicionar_comentario":
            return await self._adicionar_comentario(params, context)
        elif action == "estatisticas":
            return await self._estatisticas(params, context)
        elif action == "chat":
            return await self._chat(params, context)
        else:
            return {"error": f"Ação '{action}' não reconhecida"}

    async def _registrar_ocorrencia(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        descricao = params.get("descricao", "")

        # Classificação automática com LLM
        tipo = TipoOcorrencia(params.get("tipo", "outros"))
        prioridade = PrioridadeOcorrencia(params.get("prioridade", "media"))

        if self.config["classificacao_automatica"] and self.llm and not params.get("tipo"):
            classificacao = await self._classificar_automaticamente(descricao)
            tipo = TipoOcorrencia(classificacao.get("tipo", "outros"))
            prioridade = PrioridadeOcorrencia(classificacao.get("prioridade", "media"))

        ocorrencia = Ocorrencia(
            id=f"oco_{datetime.now().timestamp()}",
            tipo=tipo,
            titulo=params.get("titulo", descricao[:50]),
            descricao=descricao,
            local=params.get("local", ""),
            prioridade=prioridade,
            status=StatusOcorrencia.ABERTA,
            registrado_por=params.get("registrado_por", "anonimo"),
            unidade_origem=params.get("unidade_origem", ""),
            unidade_envolvida=params.get("unidade_envolvida"),
            data_registro=datetime.now(),
            anexos=params.get("anexos", [])
        )
        self._ocorrencias[ocorrencia.id] = ocorrencia

        # Notificar responsáveis
        if self.tools:
            destinatarios = ["administracao"]
            if prioridade == PrioridadeOcorrencia.CRITICA and self.config["notificar_sindico_criticas"]:
                destinatarios.append("sindico")

            await self.tools.execute(
                "send_notification",
                user_ids=destinatarios,
                title=f"Nova Ocorrência - {prioridade.value.upper()}",
                message=f"{tipo.value}: {ocorrencia.titulo}",
                channels=["push", "app"]
            )

        # Direcionar para manutenção se necessário
        if tipo in [TipoOcorrencia.VAZAMENTO, TipoOcorrencia.ESTRUTURAL] and self.has_capability("agent_collaboration"):
            await self.send_message(
                f"manutencao_{self.condominio_id}",
                {
                    "action": "abrir_chamado",
                    "params": {
                        "titulo": ocorrencia.titulo,
                        "descricao": ocorrencia.descricao,
                        "local": ocorrencia.local,
                        "prioridade": "alta" if prioridade in [PrioridadeOcorrencia.ALTA, PrioridadeOcorrencia.CRITICA] else "media",
                        "area": "hidraulica" if tipo == TipoOcorrencia.VAZAMENTO else "civil"
                    }
                }
            )

        return {
            "success": True,
            "ocorrencia_id": ocorrencia.id,
            "tipo": tipo.value,
            "prioridade": prioridade.value,
            "status": "aberta"
        }

    async def _classificar_automaticamente(self, descricao: str) -> Dict:
        if not self.llm:
            return {"tipo": "outros", "prioridade": "media"}

        prompt = f"""Classifique esta ocorrência condominial:
"{descricao}"

Retorne JSON com:
- tipo: barulho, vazamento, vandalismo, estacionamento, animal, lixo, seguranca, convivencia, estrutural, outros
- prioridade: baixa, media, alta, critica

Critérios:
- critica: risco à vida/segurança
- alta: dano patrimonial ou urgência
- media: incômodo significativo
- baixa: questões menores
"""
        response = await self.llm.generate(self.get_system_prompt(), prompt)
        try:
            return json.loads(response)
        except:
            return {"tipo": "outros", "prioridade": "media"}

    async def _atualizar_ocorrencia(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        ocorrencia_id = params.get("ocorrencia_id")
        if ocorrencia_id not in self._ocorrencias:
            return {"error": "Ocorrência não encontrada"}

        ocorrencia = self._ocorrencias[ocorrencia_id]

        if "status" in params:
            ocorrencia.status = StatusOcorrencia(params["status"])
            ocorrencia.historico.append({
                "data": datetime.now().isoformat(),
                "acao": f"Status alterado para {params['status']}",
                "usuario": params.get("usuario", "sistema")
            })

        if "prioridade" in params:
            ocorrencia.prioridade = PrioridadeOcorrencia(params["prioridade"])

        return {
            "success": True,
            "ocorrencia_id": ocorrencia_id,
            "status": ocorrencia.status.value
        }

    async def _listar_ocorrencias(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        tipo_filtro = params.get("tipo")
        status_filtro = params.get("status")
        prioridade_filtro = params.get("prioridade")
        unidade = params.get("unidade")
        limite = params.get("limite", 50)

        ocorrencias = list(self._ocorrencias.values())

        if tipo_filtro:
            ocorrencias = [o for o in ocorrencias if o.tipo.value == tipo_filtro]
        if status_filtro:
            ocorrencias = [o for o in ocorrencias if o.status.value == status_filtro]
        if prioridade_filtro:
            ocorrencias = [o for o in ocorrencias if o.prioridade.value == prioridade_filtro]
        if unidade:
            ocorrencias = [o for o in ocorrencias if o.unidade_origem == unidade or o.unidade_envolvida == unidade]

        # Ordenar por prioridade e data
        prioridade_ordem = {"critica": 0, "alta": 1, "media": 2, "baixa": 3}
        ocorrencias = sorted(ocorrencias, key=lambda o: (prioridade_ordem.get(o.prioridade.value, 4), -o.data_registro.timestamp()))
        ocorrencias = ocorrencias[:limite]

        return {
            "success": True,
            "ocorrencias": [
                {
                    "id": o.id,
                    "tipo": o.tipo.value,
                    "titulo": o.titulo,
                    "local": o.local,
                    "prioridade": o.prioridade.value,
                    "status": o.status.value,
                    "data_registro": o.data_registro.isoformat()
                }
                for o in ocorrencias
            ]
        }

    async def _detalhes_ocorrencia(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        ocorrencia_id = params.get("ocorrencia_id")
        if ocorrencia_id not in self._ocorrencias:
            return {"error": "Ocorrência não encontrada"}

        o = self._ocorrencias[ocorrencia_id]

        return {
            "success": True,
            "ocorrencia": {
                "id": o.id,
                "tipo": o.tipo.value,
                "titulo": o.titulo,
                "descricao": o.descricao,
                "local": o.local,
                "prioridade": o.prioridade.value,
                "status": o.status.value,
                "unidade_origem": o.unidade_origem,
                "unidade_envolvida": o.unidade_envolvida,
                "responsavel": o.responsavel,
                "data_registro": o.data_registro.isoformat(),
                "data_resolucao": o.data_resolucao.isoformat() if o.data_resolucao else None,
                "resolucao": o.resolucao,
                "anexos": o.anexos,
                "historico": o.historico
            }
        }

    async def _atribuir_responsavel(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        ocorrencia_id = params.get("ocorrencia_id")
        responsavel = params.get("responsavel")

        if ocorrencia_id not in self._ocorrencias:
            return {"error": "Ocorrência não encontrada"}

        ocorrencia = self._ocorrencias[ocorrencia_id]
        ocorrencia.responsavel = responsavel
        ocorrencia.status = StatusOcorrencia.EM_ANALISE
        ocorrencia.historico.append({
            "data": datetime.now().isoformat(),
            "acao": f"Atribuída a {responsavel}",
            "usuario": params.get("atribuido_por", "sistema")
        })

        return {
            "success": True,
            "ocorrencia_id": ocorrencia_id,
            "responsavel": responsavel
        }

    async def _resolver_ocorrencia(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        ocorrencia_id = params.get("ocorrencia_id")
        resolucao = params.get("resolucao", "")

        if ocorrencia_id not in self._ocorrencias:
            return {"error": "Ocorrência não encontrada"}

        ocorrencia = self._ocorrencias[ocorrencia_id]
        ocorrencia.status = StatusOcorrencia.RESOLVIDA
        ocorrencia.resolucao = resolucao
        ocorrencia.data_resolucao = datetime.now()
        ocorrencia.historico.append({
            "data": datetime.now().isoformat(),
            "acao": "Ocorrência resolvida",
            "resolucao": resolucao
        })

        # Notificar autor
        if self.tools and ocorrencia.registrado_por != "anonimo":
            await self.tools.execute(
                "send_notification",
                user_ids=[ocorrencia.registrado_por],
                title="Ocorrência Resolvida",
                message=f"Sua ocorrência '{ocorrencia.titulo}' foi resolvida.",
                channels=["push", "app"]
            )

        return {
            "success": True,
            "ocorrencia_id": ocorrencia_id,
            "status": "resolvida",
            "tempo_resolucao": str(ocorrencia.data_resolucao - ocorrencia.data_registro)
        }

    async def _adicionar_comentario(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        ocorrencia_id = params.get("ocorrencia_id")
        comentario = params.get("comentario")
        autor = params.get("autor", "sistema")

        if ocorrencia_id not in self._ocorrencias:
            return {"error": "Ocorrência não encontrada"}

        ocorrencia = self._ocorrencias[ocorrencia_id]
        ocorrencia.historico.append({
            "data": datetime.now().isoformat(),
            "acao": "comentario",
            "texto": comentario,
            "autor": autor
        })

        return {
            "success": True,
            "ocorrencia_id": ocorrencia_id,
            "comentario_adicionado": True
        }

    async def _estatisticas(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        if not self.has_capability("gestao_conflitos"):
            return {"error": "Capacidade transcendente não disponível"}

        periodo = params.get("periodo", "mes")

        todas = list(self._ocorrencias.values())
        por_tipo = {}
        por_status = {}

        for o in todas:
            por_tipo[o.tipo.value] = por_tipo.get(o.tipo.value, 0) + 1
            por_status[o.status.value] = por_status.get(o.status.value, 0) + 1

        if self.llm:
            prompt = f"""Analise as estatísticas de ocorrências:
Total: {len(todas)}
Por tipo: {por_tipo}
Por status: {por_status}
Período: {periodo}

Gere análise TRANSCENDENTE com:
1. Tipos mais frequentes
2. Áreas/unidades com mais ocorrências
3. Tempo médio de resolução
4. Tendências identificadas
5. Recomendações preventivas
"""
            response = await self.llm.generate(self.get_system_prompt(), prompt)
            return {"success": True, "estatisticas": response}

        return {
            "success": True,
            "total": len(todas),
            "por_tipo": por_tipo,
            "por_status": por_status
        }

    async def _chat(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        if self.llm:
            response = await self.llm.generate(
                self.get_system_prompt(), params.get("message", "")
            )
            return {"success": True, "response": response}
        return {"error": "LLM não configurado"}


def create_incidents_agent(
    condominio_id: str,
    llm_client: UnifiedLLMClient = None,
    memory: UnifiedMemorySystem = None,
    tools: ToolRegistry = None,
    evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT
) -> AgenteOcorrencias:
    return AgenteOcorrencias(
        condominio_id=condominio_id,
        llm_client=llm_client or UnifiedLLMClient(),
        memory=memory, tools=tools,
        evolution_level=evolution_level
    )
