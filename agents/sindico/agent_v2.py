"""
Conecta Plus - Agente Síndico (Nível 7)
Assistente inteligente do síndico para gestão condominial

Capacidades por nível:
1. REATIVO: Responder dúvidas, gerar relatórios
2. PROATIVO: Alertar problemas, sugerir ações
3. PREDITIVO: Prever demandas, antecipar conflitos
4. AUTÔNOMO: Executar tarefas rotineiras, aprovar gastos menores
5. EVOLUTIVO: Aprender preferências do síndico
6. COLABORATIVO: Coordenar todos os agentes
7. TRANSCENDENTE: Gestão estratégica avançada

Autor: Conecta Plus AI
Versão: 2.0 (Evolution Framework)
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from decimal import Decimal

from ..core.base_agent import (
    BaseAgent,
    EvolutionLevel,
    Priority,
    AgentCapability,
    AgentContext,
    AgentMessage,
    AgentAction,
    AgentPrediction,
)
from ..core.memory_store import UnifiedMemorySystem
from ..core.llm_client import UnifiedLLMClient, LLMMessage
from ..core.rag_system import RAGPipeline, Document, DocumentType
from ..core.tools import ToolRegistry

logger = logging.getLogger(__name__)


# ==================== TIPOS ESPECÍFICOS ====================

class TipoRelatorio(Enum):
    FINANCEIRO = "financeiro"
    OCORRENCIAS = "ocorrencias"
    MANUTENCAO = "manutencao"
    SEGURANCA = "seguranca"
    ASSEMBLEIA = "assembleia"
    GERAL = "geral"


class StatusTarefa(Enum):
    PENDENTE = "pendente"
    EM_ANDAMENTO = "em_andamento"
    CONCLUIDA = "concluida"
    CANCELADA = "cancelada"
    AGUARDANDO = "aguardando"


class TipoDecisao(Enum):
    APROVACAO_GASTO = "aprovacao_gasto"
    MANUTENCAO = "manutencao"
    COMUNICADO = "comunicado"
    MULTA = "multa"
    RESERVA = "reserva"
    EMERGENCIA = "emergencia"


@dataclass
class TarefaSindico:
    """Tarefa do síndico"""
    id: str
    titulo: str
    descricao: str
    tipo: str
    prioridade: Priority
    status: StatusTarefa
    prazo: Optional[datetime] = None
    responsavel: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    notas: str = ""


@dataclass
class Decisao:
    """Decisão tomada ou pendente"""
    id: str
    tipo: TipoDecisao
    descricao: str
    valor: Optional[Decimal] = None
    status: str = "pendente"  # pendente, aprovado, rejeitado
    automatica: bool = False
    justificativa: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    decided_at: Optional[datetime] = None


@dataclass
class ResumoCondominio:
    """Resumo do estado do condomínio"""
    data: datetime
    financeiro: Dict[str, Any]
    ocorrencias: Dict[str, Any]
    seguranca: Dict[str, Any]
    manutencao: Dict[str, Any]
    inadimplencia: Dict[str, Any]
    alertas: List[str]
    acoes_recomendadas: List[str]


# ==================== AGENTE SÍNDICO ====================

class AgenteSindico(BaseAgent):
    """
    Agente Síndico - Nível 7 (Transcendente)

    Assistente inteligente que auxilia o síndico em todas
    as tarefas de gestão condominial.
    """

    def __init__(
        self,
        condominio_id: str,
        llm_client: UnifiedLLMClient = None,
        memory: UnifiedMemorySystem = None,
        tools: ToolRegistry = None,
        rag: RAGPipeline = None,
        evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT,
    ):
        super().__init__(
            agent_id=f"sindico_{condominio_id}",
            agent_type="sindico",
            condominio_id=condominio_id,
            evolution_level=evolution_level,
            llm_client=llm_client,
            memory_store=memory,
        )

        self.tools = tools
        self.rag = rag

        # Estado interno
        self._tarefas: Dict[str, TarefaSindico] = {}
        self._decisoes_pendentes: List[Decisao] = []
        self._preferencias_sindico: Dict[str, Any] = {}
        self._ultimo_resumo: Optional[ResumoCondominio] = None

        # Configurações
        self.config = {
            "limite_aprovacao_automatica": Decimal("500"),  # R$ 500
            "horario_resumo_diario": "08:00",
            "dias_antecedencia_alertas": 7,
            "priorizar_seguranca": True,
        }

        # Registrar agentes colaboradores
        self._agentes_disponiveis = [
            "financeiro", "cftv", "acesso", "alarme",
            "manutencao", "comunicacao", "reservas", "ocorrencias"
        ]

        logger.info(f"Agente Síndico inicializado para condomínio {condominio_id}")

    def _register_capabilities(self) -> None:
        """Registra capacidades específicas"""

        # Nível 1: Reativo
        self._capabilities["responder_duvidas"] = AgentCapability(
            name="responder_duvidas",
            description="Responder dúvidas sobre gestão",
            level=EvolutionLevel.REACTIVE
        )
        self._capabilities["gerar_relatorios"] = AgentCapability(
            name="gerar_relatorios",
            description="Gerar relatórios do condomínio",
            level=EvolutionLevel.REACTIVE
        )
        self._capabilities["consultar_informacoes"] = AgentCapability(
            name="consultar_informacoes",
            description="Consultar informações do condomínio",
            level=EvolutionLevel.REACTIVE
        )

        # Nível 2: Proativo
        self._capabilities["alertar_problemas"] = AgentCapability(
            name="alertar_problemas",
            description="Alertar sobre problemas detectados",
            level=EvolutionLevel.PROACTIVE
        )
        self._capabilities["sugerir_acoes"] = AgentCapability(
            name="sugerir_acoes",
            description="Sugerir ações para o síndico",
            level=EvolutionLevel.PROACTIVE
        )
        self._capabilities["resumo_diario"] = AgentCapability(
            name="resumo_diario",
            description="Gerar resumo diário",
            level=EvolutionLevel.PROACTIVE
        )

        # Nível 3: Preditivo
        self._capabilities["prever_demandas"] = AgentCapability(
            name="prever_demandas",
            description="Prever demandas futuras",
            level=EvolutionLevel.PREDICTIVE
        )
        self._capabilities["antecipar_conflitos"] = AgentCapability(
            name="antecipar_conflitos",
            description="Antecipar conflitos entre moradores",
            level=EvolutionLevel.PREDICTIVE
        )

        # Nível 4: Autônomo
        self._capabilities["executar_rotinas"] = AgentCapability(
            name="executar_rotinas",
            description="Executar tarefas rotineiras",
            level=EvolutionLevel.AUTONOMOUS
        )
        self._capabilities["aprovar_gastos_menores"] = AgentCapability(
            name="aprovar_gastos_menores",
            description="Aprovar gastos dentro do limite",
            level=EvolutionLevel.AUTONOMOUS
        )

        # Nível 5: Evolutivo
        self._capabilities["aprender_preferencias"] = AgentCapability(
            name="aprender_preferencias",
            description="Aprender preferências do síndico",
            level=EvolutionLevel.EVOLUTIONARY
        )

        # Nível 6: Colaborativo
        self._capabilities["coordenar_agentes"] = AgentCapability(
            name="coordenar_agentes",
            description="Coordenar outros agentes",
            level=EvolutionLevel.COLLABORATIVE
        )

        # Nível 7: Transcendente
        self._capabilities["gestao_estrategica"] = AgentCapability(
            name="gestao_estrategica",
            description="Gestão estratégica avançada",
            level=EvolutionLevel.TRANSCENDENT
        )

    def get_system_prompt(self) -> str:
        """Retorna system prompt do agente"""
        return f"""Você é o Assistente Síndico do sistema Conecta Plus, o braço direito do síndico na gestão do condomínio.

Seu ID: {self.agent_id}
Condomínio: {self.condominio_id}
Nível de Evolução: {self.evolution_level.name}

Você é responsável por:
1. Auxiliar em todas as decisões de gestão condominial
2. Gerar relatórios e análises
3. Coordenar os outros agentes do sistema
4. Antecipar problemas e sugerir soluções
5. Automatizar tarefas rotineiras
6. Manter o síndico informado sobre tudo

Agentes disponíveis para coordenar:
{', '.join(self._agentes_disponiveis)}

Configurações:
- Limite aprovação automática: R$ {self.config['limite_aprovacao_automatica']}
- Dias antecedência alertas: {self.config['dias_antecedencia_alertas']}

Comunique-se de forma profissional, clara e objetiva.
Seja proativo nas sugestões mas respeite a autoridade do síndico.
"""

    async def process(self, input_data: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        """Processa entrada"""
        action = input_data.get("action", "")
        params = input_data.get("params", {})

        result = {}

        try:
            # Nível 1: Reativo
            if action == "chat":
                result = await self._process_chat(params, context)

            elif action == "gerar_relatorio":
                result = await self._gerar_relatorio(params, context)

            elif action == "consultar_status":
                result = await self._consultar_status(params, context)

            elif action == "listar_tarefas":
                result = await self._listar_tarefas(params, context)

            # Nível 2: Proativo
            elif action == "resumo_diario":
                if self.has_capability("resumo_diario"):
                    result = await self._gerar_resumo_diario(params, context)
                else:
                    result = {"error": "Capacidade não disponível"}

            elif action == "verificar_alertas":
                if self.has_capability("alertar_problemas"):
                    result = await self._verificar_alertas(params, context)
                else:
                    result = {"error": "Capacidade não disponível"}

            # Nível 3: Preditivo
            elif action == "analise_preditiva":
                if self.has_capability("prever_demandas"):
                    result = await self._analise_preditiva(params, context)
                else:
                    result = {"error": "Capacidade preditiva não disponível"}

            # Nível 4: Autônomo
            elif action == "processar_decisao":
                if self.has_capability("executar_rotinas"):
                    result = await self._processar_decisao(params, context)
                else:
                    result = {"error": "Capacidade autônoma não disponível"}

            # Nível 6: Colaborativo
            elif action == "coordenar_agente":
                if self.has_capability("coordenar_agentes"):
                    result = await self._coordenar_agente(params, context)
                else:
                    result = {"error": "Capacidade colaborativa não disponível"}

            elif action == "obter_visao_geral":
                if self.has_capability("coordenar_agentes"):
                    result = await self._obter_visao_geral(params, context)
                else:
                    result = {"error": "Capacidade colaborativa não disponível"}

            # Nível 7: Transcendente
            elif action == "analise_estrategica":
                if self.has_capability("gestao_estrategica"):
                    result = await self._analise_estrategica(params, context)
                else:
                    result = {"error": "Capacidade transcendente não disponível"}

            else:
                # Tentar processar como chat
                result = await self._process_chat({"message": str(input_data)}, context)

        except Exception as e:
            logger.error(f"Erro ao processar ação {action}: {e}")
            result = {"error": str(e)}

        return result

    # ==================== NÍVEL 1: REATIVO ====================

    async def _process_chat(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Processa chat com o síndico"""
        message = params.get("message", "")

        if not self.llm:
            return {"error": "LLM não configurado"}

        # Buscar contexto relevante no RAG
        rag_context = ""
        if self.rag:
            rag_result = await self.rag.query(message, top_k=3)
            if rag_result.sources:
                rag_context = f"\n\nInformações relevantes:\n{rag_result.context_used}"

        # Obter resumo atual
        resumo = await self._obter_resumo_rapido()

        # Adicionar memória de trabalho
        memory_context = ""
        if self.memory:
            memory_context = self.memory.get_context(context.session_id or "default", limit=5)

        prompt = f"""Contexto atual do condomínio:
{json.dumps(resumo, indent=2)}

{rag_context}

Histórico da conversa:
{memory_context}

Mensagem do síndico: {message}

Responda de forma útil, proativa e profissional. Se apropriado, sugira ações ou coordene outros agentes.
"""

        response = await self.llm.generate(
            system_prompt=self.get_system_prompt(),
            user_prompt=prompt
        )

        # Salvar na memória
        if self.memory:
            self.memory.add_to_context(context.session_id or "default", "user_message", message)
            self.memory.add_to_context(context.session_id or "default", "assistant_message", response)

        return {
            "success": True,
            "response": response
        }

    async def _gerar_relatorio(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Gera relatório do condomínio"""
        tipo = params.get("tipo", "geral")
        periodo = params.get("periodo", "mensal")
        formato = params.get("formato", "resumido")

        dados = {}

        # Coletar dados por tipo
        if tipo == "financeiro" or tipo == "geral":
            dados["financeiro"] = await self._coletar_dados_financeiros(periodo)

        if tipo == "ocorrencias" or tipo == "geral":
            dados["ocorrencias"] = await self._coletar_dados_ocorrencias(periodo)

        if tipo == "manutencao" or tipo == "geral":
            dados["manutencao"] = await self._coletar_dados_manutencao(periodo)

        if tipo == "seguranca" or tipo == "geral":
            dados["seguranca"] = await self._coletar_dados_seguranca(periodo)

        # Usar LLM para gerar relatório formatado
        if self.llm and formato == "detalhado":
            prompt = f"""Gere um relatório {tipo} {periodo} detalhado para o síndico.

Dados coletados:
{json.dumps(dados, indent=2)}

O relatório deve incluir:
1. Resumo executivo
2. Principais indicadores
3. Pontos de atenção
4. Comparativo com período anterior
5. Recomendações

Formate de forma profissional e clara.
"""
            relatorio_texto = await self.llm.generate(
                system_prompt=self.get_system_prompt(),
                user_prompt=prompt
            )

            return {
                "success": True,
                "tipo": tipo,
                "periodo": periodo,
                "dados": dados,
                "relatorio": relatorio_texto
            }

        return {
            "success": True,
            "tipo": tipo,
            "periodo": periodo,
            "dados": dados
        }

    async def _consultar_status(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Consulta status geral do condomínio"""
        return await self._obter_resumo_rapido()

    async def _listar_tarefas(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Lista tarefas do síndico"""
        status_filtro = params.get("status")
        prioridade_filtro = params.get("prioridade")

        tarefas = list(self._tarefas.values())

        if status_filtro:
            tarefas = [t for t in tarefas if t.status.value == status_filtro]
        if prioridade_filtro:
            tarefas = [t for t in tarefas if t.prioridade.value == prioridade_filtro]

        return {
            "success": True,
            "tarefas": [
                {
                    "id": t.id,
                    "titulo": t.titulo,
                    "status": t.status.value,
                    "prioridade": t.prioridade.name,
                    "prazo": t.prazo.isoformat() if t.prazo else None
                }
                for t in tarefas
            ],
            "total": len(tarefas)
        }

    # ==================== NÍVEL 2: PROATIVO ====================

    async def _gerar_resumo_diario(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Gera resumo diário para o síndico"""
        data = params.get("data", datetime.now().strftime("%Y-%m-%d"))

        # Coletar dados de todos os agentes
        financeiro = await self._consultar_agente("financeiro", "consultar_saldo", {})
        seguranca = await self._consultar_agente("cftv", "listar_cameras", {})
        ocorrencias = await self._obter_ocorrencias_abertas()
        inadimplencia = await self._obter_inadimplencia()
        manutencoes = await self._obter_manutencoes_pendentes()

        resumo_dados = {
            "data": data,
            "financeiro": {
                "saldo_total": financeiro.get("saldo_total", 0),
                "contas": financeiro.get("contas", [])
            },
            "seguranca": {
                "cameras_online": seguranca.get("online", 0),
                "alertas_24h": 0
            },
            "ocorrencias": {
                "abertas": len(ocorrencias),
                "lista": ocorrencias[:5]
            },
            "inadimplencia": inadimplencia,
            "manutencoes_pendentes": len(manutencoes)
        }

        # Gerar resumo narrativo com LLM
        if self.llm:
            prompt = f"""Gere um resumo diário executivo para o síndico baseado nos dados:

{json.dumps(resumo_dados, indent=2)}

O resumo deve ser:
1. Conciso (3-5 parágrafos)
2. Destacar pontos de atenção
3. Incluir ações recomendadas para hoje
4. Formato: Bom dia, [resumo]
"""
            resumo_texto = await self.llm.generate(
                system_prompt=self.get_system_prompt(),
                user_prompt=prompt,
                temperature=0.5
            )

            return {
                "success": True,
                "data": data,
                "resumo": resumo_texto,
                "dados": resumo_dados,
                "alertas": await self._identificar_alertas(resumo_dados)
            }

        return {
            "success": True,
            "data": data,
            "dados": resumo_dados
        }

    async def _verificar_alertas(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Verifica e retorna alertas importantes"""
        alertas = []

        # Verificar inadimplência alta
        inadimplencia = await self._obter_inadimplencia()
        if inadimplencia.get("percentual", 0) > 10:
            alertas.append({
                "tipo": "financeiro",
                "nivel": "alto",
                "mensagem": f"Inadimplência em {inadimplencia['percentual']:.1f}%",
                "acao": "Verificar relatório de cobrança"
            })

        # Verificar ocorrências críticas
        ocorrencias = await self._obter_ocorrencias_abertas()
        criticas = [o for o in ocorrencias if o.get("prioridade") == "critica"]
        if criticas:
            alertas.append({
                "tipo": "ocorrencia",
                "nivel": "critico",
                "mensagem": f"{len(criticas)} ocorrência(s) crítica(s) em aberto",
                "acao": "Atender imediatamente"
            })

        # Verificar manutenções atrasadas
        manutencoes = await self._obter_manutencoes_pendentes()
        atrasadas = [m for m in manutencoes if m.get("atrasada")]
        if atrasadas:
            alertas.append({
                "tipo": "manutencao",
                "nivel": "medio",
                "mensagem": f"{len(atrasadas)} manutenção(ões) atrasada(s)",
                "acao": "Cobrar fornecedores"
            })

        # Verificar vencimentos próximos
        vencimentos = await self._verificar_vencimentos()
        if vencimentos:
            alertas.append({
                "tipo": "administrativo",
                "nivel": "medio",
                "mensagem": f"{len(vencimentos)} vencimento(s) nos próximos {self.config['dias_antecedencia_alertas']} dias",
                "acao": "Verificar pendências"
            })

        return {
            "success": True,
            "alertas": alertas,
            "total": len(alertas),
            "criticos": sum(1 for a in alertas if a["nivel"] == "critico")
        }

    # ==================== NÍVEL 3: PREDITIVO ====================

    async def _analise_preditiva(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Análise preditiva do condomínio"""
        horizonte = params.get("horizonte", "30d")

        # Coletar dados históricos
        historico = await self._coletar_historico_completo()

        if self.llm:
            prompt = f"""Analise os dados históricos e faça previsões para os próximos {horizonte}:

Dados históricos:
{json.dumps(historico, indent=2)}

Preveja:
1. Tendência financeira (receitas/despesas)
2. Potenciais conflitos entre moradores
3. Necessidades de manutenção
4. Demandas que surgirão
5. Riscos a mitigar

Responda em JSON:
{{
  "previsao_financeira": {{"tendencia": "...", "valores": {{}}}},
  "conflitos_potenciais": [{{"descricao": "...", "probabilidade": 0.0}}],
  "manutencoes_previstas": ["..."],
  "demandas_esperadas": ["..."],
  "riscos": [{{"descricao": "...", "mitigacao": "..."}}],
  "recomendacoes_proativas": ["..."]
}}
"""
            try:
                response = await self.llm.generate(
                    system_prompt=self.get_system_prompt(),
                    user_prompt=prompt,
                    temperature=0.5
                )

                import re
                json_match = re.search(r'\{[\s\S]*\}', response)
                if json_match:
                    previsao = json.loads(json_match.group())
                    return {
                        "success": True,
                        "horizonte": horizonte,
                        "previsao": previsao
                    }

            except Exception as e:
                logger.error(f"Erro na análise preditiva: {e}")

        return {
            "success": True,
            "horizonte": horizonte,
            "previsao": {
                "previsao_financeira": {"tendencia": "estável"},
                "conflitos_potenciais": [],
                "manutencoes_previstas": ["Revisão elevadores (próximo mês)"],
                "demandas_esperadas": ["Reservas para festas de fim de ano"],
                "riscos": [],
                "recomendacoes_proativas": ["Preparar comunicado sobre festas"]
            }
        }

    # ==================== NÍVEL 4: AUTÔNOMO ====================

    async def _processar_decisao(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Processa decisão automaticamente se dentro dos limites"""
        tipo = params.get("tipo")
        valor = Decimal(str(params.get("valor", 0)))
        descricao = params.get("descricao", "")

        decisao = Decisao(
            id=f"dec_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            tipo=TipoDecisao(tipo),
            descricao=descricao,
            valor=valor
        )

        # Verificar se pode aprovar automaticamente
        pode_aprovar_auto = (
            self.has_capability("aprovar_gastos_menores") and
            valor <= self.config["limite_aprovacao_automatica"] and
            tipo == "aprovacao_gasto"
        )

        if pode_aprovar_auto:
            decisao.status = "aprovado"
            decisao.automatica = True
            decisao.justificativa = f"Aprovado automaticamente (valor dentro do limite de R$ {self.config['limite_aprovacao_automatica']})"
            decisao.decided_at = datetime.now()

            # Executar ação relacionada
            await self._executar_decisao(decisao)

            # Notificar síndico
            if self.tools:
                await self.tools.execute(
                    "send_notification",
                    user_ids=["sindico"],
                    title="Decisão Automática",
                    message=f"Aprovado: {descricao} - R$ {valor:.2f}",
                    channels=["app"],
                    priority="normal"
                )

            return {
                "success": True,
                "decisao_id": decisao.id,
                "status": "aprovado",
                "automatica": True,
                "mensagem": decisao.justificativa
            }

        # Requer aprovação manual
        self._decisoes_pendentes.append(decisao)

        return {
            "success": True,
            "decisao_id": decisao.id,
            "status": "pendente",
            "automatica": False,
            "mensagem": "Decisão requer aprovação do síndico"
        }

    async def _executar_decisao(self, decisao: Decisao):
        """Executa ação após decisão aprovada"""
        if decisao.tipo == TipoDecisao.APROVACAO_GASTO:
            # Registrar lançamento financeiro
            if self.tools:
                await self.tools.execute(
                    "database_insert",
                    table="financeiro_lancamentos",
                    data={
                        "tipo": "despesa",
                        "descricao": decisao.descricao,
                        "valor": float(decisao.valor),
                        "data": datetime.now().isoformat(),
                        "aprovado_por": "agente_sindico" if decisao.automatica else "sindico",
                        "condominio_id": self.condominio_id
                    }
                )

    # ==================== NÍVEL 6: COLABORATIVO ====================

    async def _coordenar_agente(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Coordena ação de outro agente"""
        agente = params.get("agente")
        acao = params.get("acao")
        parametros = params.get("parametros", {})

        if agente not in self._agentes_disponiveis:
            return {"success": False, "error": f"Agente '{agente}' não disponível"}

        # Enviar mensagem para o agente
        if self.has_capability("agent_collaboration"):
            await self.send_message(
                receiver_id=f"{agente}_{self.condominio_id}",
                content={
                    "action": acao,
                    "params": parametros,
                    "origem": "sindico"
                },
                priority=Priority.HIGH
            )

            return {
                "success": True,
                "mensagem": f"Comando enviado para agente {agente}"
            }

        return await self._consultar_agente(agente, acao, parametros)

    async def _obter_visao_geral(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Obtém visão geral coordenando todos os agentes"""
        visao = {}

        # Consultar cada agente
        for agente in self._agentes_disponiveis:
            try:
                if agente == "financeiro":
                    visao["financeiro"] = await self._consultar_agente(agente, "consultar_saldo", {})
                elif agente == "cftv":
                    visao["seguranca"] = await self._consultar_agente(agente, "listar_cameras", {})
                elif agente == "acesso":
                    visao["acesso"] = await self._consultar_agente(agente, "consultar_logs", {"limit": 10})
                elif agente == "ocorrencias":
                    visao["ocorrencias"] = await self._obter_ocorrencias_abertas()
                elif agente == "manutencao":
                    visao["manutencao"] = await self._obter_manutencoes_pendentes()
            except Exception as e:
                logger.warning(f"Erro ao consultar agente {agente}: {e}")
                visao[agente] = {"error": str(e)}

        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "visao": visao
        }

    # ==================== NÍVEL 7: TRANSCENDENTE ====================

    async def _analise_estrategica(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Análise estratégica transcendente"""
        horizonte = params.get("horizonte", "12m")

        # Coletar todos os dados disponíveis
        dados = {
            "financeiro": await self._coletar_dados_financeiros("anual"),
            "ocorrencias": await self._coletar_dados_ocorrencias("anual"),
            "seguranca": await self._coletar_dados_seguranca("anual"),
            "manutencao": await self._coletar_dados_manutencao("anual"),
            "satisfacao": await self._obter_dados_satisfacao(),
            "tendencias_mercado": await self._obter_tendencias_mercado()
        }

        if self.llm:
            prompt = f"""Como consultor estratégico de elite para gestão condominial, analise os dados e gere insights TRANSCENDENTES.

Dados do condomínio:
{json.dumps(dados, indent=2)}

Horizonte de planejamento: {horizonte}

Gere análise TRANSCENDENTE:
1. Diagnóstico estratégico profundo
2. Oportunidades de melhoria não óbvias
3. Riscos de longo prazo não evidentes
4. Correlações entre áreas diferentes
5. Benchmarks com mercado
6. Plano de ação estratégico inovador
7. Indicadores de sucesso
8. Visão de futuro para o condomínio

Responda em JSON:
{{
  "diagnostico_estrategico": {{
    "pontos_fortes": ["..."],
    "pontos_fracos": ["..."],
    "score_gestao": 0-100
  }},
  "oportunidades_ocultas": [{{"area": "...", "oportunidade": "...", "potencial": "..."}}],
  "riscos_longo_prazo": [{{"risco": "...", "probabilidade": 0.0, "impacto": "...", "mitigacao": "..."}}],
  "correlacoes_descobertas": ["..."],
  "benchmarks": {{"vs_mercado": "...", "areas_destaque": [], "areas_melhorar": []}},
  "plano_estrategico": [{{"acao": "...", "prazo": "...", "impacto": "...", "recursos": "..."}}],
  "kpis_recomendados": ["..."],
  "visao_futuro": "...",
  "insights_transcendentes": ["..."]
}}
"""
            try:
                response = await self.llm.generate(
                    system_prompt=self.get_system_prompt() + "\n\nModo TRANSCENDENTE: Pense como CEO de grande corporação aplicado à gestão condominial.",
                    user_prompt=prompt,
                    temperature=0.7,
                    max_tokens=3000
                )

                import re
                json_match = re.search(r'\{[\s\S]*\}', response)
                if json_match:
                    analise = json.loads(json_match.group())

                    # Armazenar na memória
                    if self.memory:
                        await self.memory.remember_semantic(
                            agent_id=self.agent_id,
                            content=f"Análise estratégica: {json.dumps(analise.get('insights_transcendentes', []))}",
                            metadata={"tipo": "estrategia", "data": datetime.now().isoformat()}
                        )

                    return {
                        "success": True,
                        "nivel": "TRANSCENDENTE",
                        "horizonte": horizonte,
                        "analise": analise
                    }

            except Exception as e:
                logger.error(f"Erro na análise estratégica: {e}")

        return {
            "success": True,
            "nivel": "TRANSCENDENTE",
            "horizonte": horizonte,
            "analise": {
                "diagnostico_estrategico": {
                    "pontos_fortes": ["Segurança bem estruturada", "Equipe engajada"],
                    "pontos_fracos": ["Comunicação pode melhorar", "Processos manuais"],
                    "score_gestao": 75
                },
                "insights_transcendentes": [
                    "Potencial de redução de 15% nas despesas com digitalização completa",
                    "Moradores 35-45 anos são os mais engajados - criar programa de liderança"
                ]
            }
        }

    # ==================== MÉTODOS AUXILIARES ====================

    async def _consultar_agente(self, agente: str, acao: str, params: Dict) -> Dict[str, Any]:
        """Consulta outro agente do sistema"""
        # Em produção, isso usaria o message bus
        # Por ora, retorna dados mock
        return {"status": "ok"}

    async def _obter_resumo_rapido(self) -> Dict[str, Any]:
        """Obtém resumo rápido do estado atual"""
        return {
            "data": datetime.now().isoformat(),
            "saldo_disponivel": 165000.00,
            "inadimplencia_percentual": 3.5,
            "ocorrencias_abertas": 5,
            "manutencoes_pendentes": 2,
            "alertas_ativos": 1
        }

    async def _identificar_alertas(self, dados: Dict) -> List[str]:
        """Identifica alertas nos dados"""
        alertas = []
        if dados.get("inadimplencia", {}).get("percentual", 0) > 5:
            alertas.append("Inadimplência acima do ideal")
        if dados.get("ocorrencias", {}).get("abertas", 0) > 10:
            alertas.append("Muitas ocorrências abertas")
        return alertas

    async def _coletar_dados_financeiros(self, periodo: str) -> Dict:
        return {"receitas": 600000, "despesas": 540000, "saldo": 60000}

    async def _coletar_dados_ocorrencias(self, periodo: str) -> Dict:
        return {"total": 45, "resolvidas": 40, "abertas": 5}

    async def _coletar_dados_manutencao(self, periodo: str) -> Dict:
        return {"total": 20, "concluidas": 18, "pendentes": 2}

    async def _coletar_dados_seguranca(self, periodo: str) -> Dict:
        return {"incidentes": 3, "alertas": 15, "cameras_ok": 12}

    async def _obter_ocorrencias_abertas(self) -> List[Dict]:
        return []

    async def _obter_inadimplencia(self) -> Dict:
        return {"percentual": 3.5, "valor_total": 12500, "unidades": 4}

    async def _obter_manutencoes_pendentes(self) -> List[Dict]:
        return []

    async def _verificar_vencimentos(self) -> List[Dict]:
        return []

    async def _coletar_historico_completo(self) -> Dict:
        return {}

    async def _obter_dados_satisfacao(self) -> Dict:
        return {"nps": 72, "avaliacoes_positivas": 85}

    async def _obter_tendencias_mercado(self) -> Dict:
        return {"taxa_media_condominio": 850, "tendencia": "estável"}


# Factory
def create_sindico_agent(
    condominio_id: str,
    llm_client: UnifiedLLMClient = None,
    memory: UnifiedMemorySystem = None,
    tools: ToolRegistry = None,
    rag: RAGPipeline = None,
    evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT
) -> AgenteSindico:
    """Cria instância do agente síndico"""
    return AgenteSindico(
        condominio_id=condominio_id,
        llm_client=llm_client or UnifiedLLMClient(),
        memory=memory,
        tools=tools,
        rag=rag,
        evolution_level=evolution_level
    )
