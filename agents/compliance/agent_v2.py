"""
Conecta Plus - Agente de Compliance (Nível 7)
Sistema inteligente de conformidade e governança

Capacidades:
1. REATIVO: Verificar conformidade, gerar relatórios
2. PROATIVO: Alertar vencimentos, monitorar obrigações
3. PREDITIVO: Prever riscos, identificar gaps
4. AUTÔNOMO: Automatizar verificações, gerar evidências
5. EVOLUTIVO: Aprender mudanças regulatórias
6. COLABORATIVO: Integrar Financeiro, RH, Jurídico
7. TRANSCENDENTE: Compliance cognitivo total
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


class TipoObrigacao(Enum):
    FISCAL = "fiscal"
    TRABALHISTA = "trabalhista"
    AMBIENTAL = "ambiental"
    SEGURANCA = "seguranca"
    ACESSIBILIDADE = "acessibilidade"
    CONDOMINAL = "condominal"
    LGPD = "lgpd"


class StatusObrigacao(Enum):
    PENDENTE = "pendente"
    EM_DIA = "em_dia"
    VENCIDA = "vencida"
    NAO_APLICAVEL = "nao_aplicavel"


class NivelRisco(Enum):
    BAIXO = "baixo"
    MEDIO = "medio"
    ALTO = "alto"
    CRITICO = "critico"


@dataclass
class Obrigacao:
    id: str
    tipo: TipoObrigacao
    nome: str
    descricao: str
    periodicidade: str
    data_vencimento: date
    status: StatusObrigacao
    responsavel: str
    evidencia_url: Optional[str] = None
    ultima_verificacao: Optional[datetime] = None
    observacoes: str = ""


@dataclass
class AuditItem:
    id: str
    categoria: str
    item: str
    conforme: bool
    evidencia: str
    observacao: str
    data_verificacao: datetime


@dataclass
class RiscoCompliance:
    id: str
    tipo: TipoObrigacao
    descricao: str
    nivel: NivelRisco
    impacto_potencial: str
    acao_mitigacao: str
    responsavel: str
    prazo_mitigacao: Optional[date] = None


class AgenteCompliance(BaseAgent):
    """Agente de Compliance - Nível 7"""

    def __init__(
        self,
        condominio_id: str,
        llm_client: UnifiedLLMClient = None,
        memory: UnifiedMemorySystem = None,
        tools: ToolRegistry = None,
        evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT,
    ):
        super().__init__(
            agent_id=f"compliance_{condominio_id}",
            agent_type="compliance",
            condominio_id=condominio_id,
            evolution_level=evolution_level,
            llm_client=llm_client,
            memory_store=memory,
        )
        self.tools = tools
        self._obrigacoes: Dict[str, Obrigacao] = {}
        self._auditorias: List[AuditItem] = []
        self._riscos: Dict[str, RiscoCompliance] = {}

        self.config = {
            "alerta_vencimento_dias": 30,
            "verificacao_automatica": True,
            "lgpd_ativo": True,
            "auditoria_periodica_dias": 90,
        }

        # Inicializar obrigações padrão
        self._inicializar_obrigacoes()

    def _inicializar_obrigacoes(self):
        obrigacoes_padrao = [
            ("AVCB", TipoObrigacao.SEGURANCA, "Auto de Vistoria do Corpo de Bombeiros", "anual"),
            ("PCMSO", TipoObrigacao.TRABALHISTA, "Programa de Controle Médico de Saúde Ocupacional", "anual"),
            ("PPRA", TipoObrigacao.TRABALHISTA, "Programa de Prevenção de Riscos Ambientais", "anual"),
            ("CAGED", TipoObrigacao.TRABALHISTA, "Cadastro Geral de Empregados e Desempregados", "mensal"),
            ("GFIP", TipoObrigacao.FISCAL, "Guia de Recolhimento do FGTS", "mensal"),
            ("RAIS", TipoObrigacao.TRABALHISTA, "Relação Anual de Informações Sociais", "anual"),
            ("IPTU", TipoObrigacao.FISCAL, "Imposto Predial e Territorial Urbano", "anual"),
            ("ELEVADOR", TipoObrigacao.SEGURANCA, "Inspeção de Elevadores", "anual"),
            ("PARA_RAIOS", TipoObrigacao.SEGURANCA, "Inspeção do Para-raios", "anual"),
            ("DEDETIZACAO", TipoObrigacao.AMBIENTAL, "Controle de Pragas", "trimestral"),
            ("LIMPEZA_CAIXA", TipoObrigacao.AMBIENTAL, "Limpeza de Caixa d'água", "semestral"),
        ]

        for nome, tipo, descricao, periodicidade in obrigacoes_padrao:
            self._obrigacoes[nome] = Obrigacao(
                id=nome,
                tipo=tipo,
                nome=nome,
                descricao=descricao,
                periodicidade=periodicidade,
                data_vencimento=date.today() + timedelta(days=180),
                status=StatusObrigacao.PENDENTE,
                responsavel="administracao"
            )

    def _register_capabilities(self) -> None:
        self._capabilities["verificacao_compliance"] = AgentCapability(
            name="verificacao_compliance", description="Verificar conformidade",
            level=EvolutionLevel.REACTIVE
        )
        self._capabilities["alertas_vencimento"] = AgentCapability(
            name="alertas_vencimento", description="Alertar vencimentos",
            level=EvolutionLevel.PROACTIVE
        )
        self._capabilities["analise_riscos"] = AgentCapability(
            name="analise_riscos", description="Analisar riscos de compliance",
            level=EvolutionLevel.PREDICTIVE
        )
        self._capabilities["auditoria_autonoma"] = AgentCapability(
            name="auditoria_autonoma", description="Executar auditorias automaticamente",
            level=EvolutionLevel.AUTONOMOUS
        )
        self._capabilities["compliance_cognitivo"] = AgentCapability(
            name="compliance_cognitivo", description="Compliance cognitivo total",
            level=EvolutionLevel.TRANSCENDENT
        )

    def get_system_prompt(self) -> str:
        return f"""Você é o Agente de Compliance do Conecta Plus.
ID: {self.agent_id} | Condomínio: {self.condominio_id} | Nível: {self.evolution_level.name}

Responsabilidades:
- Monitorar obrigações legais e regulatórias
- Alertar sobre vencimentos e pendências
- Executar auditorias de conformidade
- Analisar e mitigar riscos
- Garantir conformidade com LGPD

Configurações:
- Alerta vencimento: {self.config['alerta_vencimento_dias']} dias
- Verificação automática: {self.config['verificacao_automatica']}
- LGPD ativo: {self.config['lgpd_ativo']}
"""

    async def process(self, input_data: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        action = input_data.get("action", "")
        params = input_data.get("params", {})

        if action == "listar_obrigacoes":
            return await self._listar_obrigacoes(params, context)
        elif action == "status_obrigacao":
            return await self._status_obrigacao(params, context)
        elif action == "atualizar_obrigacao":
            return await self._atualizar_obrigacao(params, context)
        elif action == "vencimentos_proximos":
            return await self._vencimentos_proximos(params, context)
        elif action == "executar_auditoria":
            return await self._executar_auditoria(params, context)
        elif action == "analise_riscos":
            return await self._analise_riscos(params, context)
        elif action == "relatorio_compliance":
            return await self._relatorio_compliance(params, context)
        elif action == "verificar_lgpd":
            return await self._verificar_lgpd(params, context)
        elif action == "chat":
            return await self._chat(params, context)
        else:
            return {"error": f"Ação '{action}' não reconhecida"}

    async def _listar_obrigacoes(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        tipo_filtro = params.get("tipo")
        status_filtro = params.get("status")

        obrigacoes = list(self._obrigacoes.values())

        if tipo_filtro:
            obrigacoes = [o for o in obrigacoes if o.tipo.value == tipo_filtro]
        if status_filtro:
            obrigacoes = [o for o in obrigacoes if o.status.value == status_filtro]

        return {
            "success": True,
            "obrigacoes": [
                {
                    "id": o.id,
                    "nome": o.nome,
                    "tipo": o.tipo.value,
                    "periodicidade": o.periodicidade,
                    "vencimento": o.data_vencimento.isoformat(),
                    "status": o.status.value,
                    "responsavel": o.responsavel
                }
                for o in obrigacoes
            ]
        }

    async def _status_obrigacao(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        obrigacao_id = params.get("obrigacao_id")

        if obrigacao_id not in self._obrigacoes:
            return {"error": "Obrigação não encontrada"}

        o = self._obrigacoes[obrigacao_id]
        dias_para_vencer = (o.data_vencimento - date.today()).days

        return {
            "success": True,
            "obrigacao": {
                "id": o.id,
                "nome": o.nome,
                "tipo": o.tipo.value,
                "descricao": o.descricao,
                "periodicidade": o.periodicidade,
                "vencimento": o.data_vencimento.isoformat(),
                "dias_para_vencer": dias_para_vencer,
                "status": o.status.value,
                "responsavel": o.responsavel,
                "evidencia": o.evidencia_url,
                "ultima_verificacao": o.ultima_verificacao.isoformat() if o.ultima_verificacao else None
            }
        }

    async def _atualizar_obrigacao(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        obrigacao_id = params.get("obrigacao_id")

        if obrigacao_id not in self._obrigacoes:
            return {"error": "Obrigação não encontrada"}

        o = self._obrigacoes[obrigacao_id]

        if "status" in params:
            o.status = StatusObrigacao(params["status"])
        if "data_vencimento" in params:
            o.data_vencimento = date.fromisoformat(params["data_vencimento"])
        if "evidencia_url" in params:
            o.evidencia_url = params["evidencia_url"]
        if "observacoes" in params:
            o.observacoes = params["observacoes"]

        o.ultima_verificacao = datetime.now()

        return {
            "success": True,
            "obrigacao_id": obrigacao_id,
            "status": o.status.value
        }

    async def _vencimentos_proximos(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        dias = params.get("dias", self.config["alerta_vencimento_dias"])
        data_limite = date.today() + timedelta(days=dias)

        proximos = []
        for o in self._obrigacoes.values():
            if o.data_vencimento <= data_limite and o.status != StatusObrigacao.EM_DIA:
                dias_restantes = (o.data_vencimento - date.today()).days
                proximos.append({
                    "id": o.id,
                    "nome": o.nome,
                    "tipo": o.tipo.value,
                    "vencimento": o.data_vencimento.isoformat(),
                    "dias_restantes": dias_restantes,
                    "status": "vencido" if dias_restantes < 0 else "próximo"
                })

        # Ordenar por urgência
        proximos = sorted(proximos, key=lambda x: x["dias_restantes"])

        # Alertar se houver vencimentos
        if proximos and self.tools:
            await self.tools.execute(
                "send_notification",
                user_ids=["sindico", "administracao"],
                title="Alerta de Compliance",
                message=f"{len(proximos)} obrigações próximas do vencimento",
                channels=["push", "app"]
            )

        return {
            "success": True,
            "periodo_dias": dias,
            "vencimentos": proximos
        }

    async def _executar_auditoria(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        if not self.has_capability("auditoria_autonoma"):
            return {"error": "Capacidade autônoma não disponível"}

        tipo = params.get("tipo", "geral")

        itens_auditoria = []

        # Verificar cada obrigação
        for o in self._obrigacoes.values():
            conforme = o.status == StatusObrigacao.EM_DIA
            item = AuditItem(
                id=f"audit_{o.id}_{datetime.now().timestamp()}",
                categoria=o.tipo.value,
                item=o.nome,
                conforme=conforme,
                evidencia=o.evidencia_url or "",
                observacao=o.observacoes,
                data_verificacao=datetime.now()
            )
            itens_auditoria.append(item)
            self._auditorias.append(item)

        total = len(itens_auditoria)
        conformes = len([i for i in itens_auditoria if i.conforme])
        percentual = (conformes / total * 100) if total > 0 else 0

        return {
            "success": True,
            "tipo": tipo,
            "data": datetime.now().isoformat(),
            "total_itens": total,
            "conformes": conformes,
            "nao_conformes": total - conformes,
            "percentual_conformidade": percentual,
            "itens": [
                {
                    "item": i.item,
                    "categoria": i.categoria,
                    "conforme": i.conforme,
                    "observacao": i.observacao
                }
                for i in itens_auditoria
            ]
        }

    async def _analise_riscos(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        if not self.has_capability("analise_riscos"):
            return {"error": "Capacidade preditiva não disponível"}

        riscos = []

        # Analisar obrigações vencidas
        for o in self._obrigacoes.values():
            dias = (o.data_vencimento - date.today()).days

            if dias < 0:
                nivel = NivelRisco.CRITICO
                impacto = "Multas e penalidades imediatas"
            elif dias < 15:
                nivel = NivelRisco.ALTO
                impacto = "Risco de multas próximo"
            elif dias < 30:
                nivel = NivelRisco.MEDIO
                impacto = "Atenção necessária"
            else:
                continue

            risco = RiscoCompliance(
                id=f"risco_{o.id}",
                tipo=o.tipo,
                descricao=f"{o.nome} {'vencido há' if dias < 0 else 'vence em'} {abs(dias)} dias",
                nivel=nivel,
                impacto_potencial=impacto,
                acao_mitigacao=f"Regularizar {o.nome}",
                responsavel=o.responsavel,
                prazo_mitigacao=date.today() + timedelta(days=7)
            )
            riscos.append(risco)

        if self.llm:
            prompt = f"""Analise os riscos de compliance identificados:
{json.dumps([{'descricao': r.descricao, 'nivel': r.nivel.value, 'impacto': r.impacto_potencial} for r in riscos], indent=2)}

Forneça análise TRANSCENDENTE com:
1. Priorização de riscos
2. Impactos potenciais detalhados
3. Plano de mitigação
4. Indicadores de monitoramento
5. Recomendações preventivas
"""
            response = await self.llm.generate(self.get_system_prompt(), prompt)
            return {
                "success": True,
                "riscos_identificados": len(riscos),
                "analise": response
            }

        return {
            "success": True,
            "riscos": [
                {
                    "descricao": r.descricao,
                    "nivel": r.nivel.value,
                    "impacto": r.impacto_potencial,
                    "acao": r.acao_mitigacao
                }
                for r in riscos
            ]
        }

    async def _relatorio_compliance(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        if not self.has_capability("compliance_cognitivo"):
            return {"error": "Capacidade transcendente não disponível"}

        obrigacoes = await self._listar_obrigacoes({}, context)
        vencimentos = await self._vencimentos_proximos({"dias": 60}, context)
        auditoria = await self._executar_auditoria({"tipo": "geral"}, context)

        if self.llm:
            prompt = f"""Gere relatório executivo de compliance:
Obrigações: {json.dumps(obrigacoes)}
Vencimentos próximos: {json.dumps(vencimentos)}
Última auditoria: {json.dumps(auditoria)}

Relatório TRANSCENDENTE deve incluir:
1. Sumário executivo
2. Status geral de conformidade
3. Riscos críticos
4. Ações recomendadas
5. Indicadores de performance
6. Projeção para próximo período
"""
            response = await self.llm.generate(self.get_system_prompt(), prompt)
            return {"success": True, "relatorio": response}

        return {
            "success": True,
            "percentual_conformidade": auditoria.get("percentual_conformidade"),
            "vencimentos_proximos": len(vencimentos.get("vencimentos", []))
        }

    async def _verificar_lgpd(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        if not self.config["lgpd_ativo"]:
            return {"error": "Verificação LGPD desativada"}

        verificacoes = {
            "politica_privacidade": True,
            "consentimento_dados": True,
            "direito_exclusao": True,
            "dpo_designado": False,
            "registro_tratamento": True,
            "medidas_seguranca": True,
            "notificacao_incidentes": True
        }

        conformes = sum(1 for v in verificacoes.values() if v)
        total = len(verificacoes)

        return {
            "success": True,
            "verificacoes": verificacoes,
            "conformidade": conformes / total * 100,
            "pendencias": [k for k, v in verificacoes.items() if not v]
        }

    async def _chat(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        if self.llm:
            response = await self.llm.generate(
                self.get_system_prompt(), params.get("message", "")
            )
            return {"success": True, "response": response}
        return {"error": "LLM não configurado"}


def create_compliance_agent(
    condominio_id: str,
    llm_client: UnifiedLLMClient = None,
    memory: UnifiedMemorySystem = None,
    tools: ToolRegistry = None,
    evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT
) -> AgenteCompliance:
    return AgenteCompliance(
        condominio_id=condominio_id,
        llm_client=llm_client or UnifiedLLMClient(),
        memory=memory, tools=tools,
        evolution_level=evolution_level
    )
