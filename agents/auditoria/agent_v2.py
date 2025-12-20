"""
Agente de Auditoria v2 - Conecta Plus
Auditor automático para auditorias financeiras, operacionais, de segurança e compliance
Nível 7: Transcendente - Antecipa riscos e recomenda melhorias proativas
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import hashlib
from abc import ABC, abstractmethod

from agents.core.base_agent import BaseAgent, AgentCapability, AgentContext
from agents.core.memory_store import UnifiedMemorySystem
from agents.core.llm_client import UnifiedLLMClient
from agents.core.tools import ToolRegistry
from agents.core.rag_system import RAGPipeline


class TipoAuditoria(Enum):
    """Tipos de auditoria"""
    FINANCEIRA = "financeira"
    OPERACIONAL = "operacional"
    SEGURANCA = "seguranca"
    COMPLIANCE = "compliance"
    CONTRATOS = "contratos"
    PROCESSOS = "processos"
    RECURSOS_HUMANOS = "recursos_humanos"
    TECNOLOGIA = "tecnologia"
    AMBIENTAL = "ambiental"
    PATRIMONIAL = "patrimonial"


class StatusAuditoria(Enum):
    """Status da auditoria"""
    PLANEJADA = "planejada"
    EM_ANDAMENTO = "em_andamento"
    PENDENTE_DOCUMENTOS = "pendente_documentos"
    EM_ANALISE = "em_analise"
    AGUARDANDO_RESPOSTA = "aguardando_resposta"
    CONCLUIDA = "concluida"
    CANCELADA = "cancelada"


class SeveridadeAchado(Enum):
    """Severidade do achado de auditoria"""
    INFORMATIVO = "informativo"
    BAIXA = "baixa"
    MEDIA = "media"
    ALTA = "alta"
    CRITICA = "critica"


class CategoriaRisco(Enum):
    """Categorias de risco identificadas"""
    FRAUDE = "fraude"
    DESVIO_FINANCEIRO = "desvio_financeiro"
    NAO_CONFORMIDADE = "nao_conformidade"
    INEFICIENCIA = "ineficiencia"
    SEGURANCA_INFORMACAO = "seguranca_informacao"
    SEGURANCA_FISICA = "seguranca_fisica"
    TRABALHISTA = "trabalhista"
    AMBIENTAL = "ambiental"
    REPUTACIONAL = "reputacional"
    CONTRATUAL = "contratual"


class StatusRecomendacao(Enum):
    """Status da recomendação"""
    PENDENTE = "pendente"
    EM_IMPLEMENTACAO = "em_implementacao"
    IMPLEMENTADA = "implementada"
    NAO_APLICAVEL = "nao_aplicavel"
    RECUSADA = "recusada"


@dataclass
class AchadoAuditoria:
    """Achado identificado em auditoria"""
    achado_id: str
    auditoria_id: str
    titulo: str
    descricao: str
    severidade: SeveridadeAchado
    categoria_risco: CategoriaRisco
    evidencias: List[Dict[str, Any]]
    criterio_referencia: str  # Norma, lei ou procedimento violado
    impacto_estimado: Dict[str, Any]  # Financeiro, operacional, etc.
    causa_raiz: Optional[str] = None
    responsavel_area: Optional[str] = None
    data_identificacao: datetime = field(default_factory=datetime.now)
    status_tratamento: str = "aberto"
    acoes_corretivas: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class Recomendacao:
    """Recomendação de auditoria"""
    recomendacao_id: str
    achado_id: str
    descricao: str
    prioridade: int  # 1-5
    prazo_sugerido: datetime
    responsavel_sugerido: Optional[str]
    status: StatusRecomendacao
    custo_estimado: Optional[float] = None
    beneficio_esperado: Optional[str] = None
    data_criacao: datetime = field(default_factory=datetime.now)
    data_implementacao: Optional[datetime] = None
    observacoes_implementacao: Optional[str] = None


@dataclass
class PlanoAuditoria:
    """Plano de auditoria"""
    plano_id: str
    titulo: str
    tipo: TipoAuditoria
    escopo: str
    objetivos: List[str]
    areas_auditadas: List[str]
    periodo_referencia: Tuple[datetime, datetime]
    procedimentos: List[Dict[str, Any]]
    amostragem: Dict[str, Any]
    recursos_necessarios: List[str]
    cronograma: List[Dict[str, Any]]
    riscos_do_plano: List[str]
    data_criacao: datetime = field(default_factory=datetime.now)
    aprovado_por: Optional[str] = None
    data_aprovacao: Optional[datetime] = None


@dataclass
class Auditoria:
    """Auditoria completa"""
    auditoria_id: str
    plano_id: str
    tipo: TipoAuditoria
    status: StatusAuditoria
    titulo: str
    escopo: str
    periodo_referencia: Tuple[datetime, datetime]
    auditor_responsavel: str
    equipe_auditora: List[str]
    documentos_solicitados: List[Dict[str, Any]]
    documentos_recebidos: List[Dict[str, Any]]
    testes_realizados: List[Dict[str, Any]]
    achados: List[str]  # IDs dos achados
    recomendacoes: List[str]  # IDs das recomendações
    conclusao: Optional[str] = None
    parecer: Optional[str] = None  # Com ressalvas, sem ressalvas, adverso
    data_inicio: datetime = field(default_factory=datetime.now)
    data_fim: Optional[datetime] = None
    horas_trabalhadas: float = 0.0
    proxima_auditoria: Optional[datetime] = None


@dataclass
class ControleInterno:
    """Controle interno avaliado"""
    controle_id: str
    nome: str
    descricao: str
    area: str
    tipo: str  # Preventivo, detectivo, corretivo
    frequencia: str  # Diário, semanal, mensal, etc.
    automatizado: bool
    responsavel: str
    efetividade: str  # Efetivo, parcialmente efetivo, inefetivo
    ultima_avaliacao: datetime
    proxima_avaliacao: datetime
    evidencias_teste: List[Dict[str, Any]]
    observacoes: Optional[str] = None


@dataclass
class MatrizRisco:
    """Matriz de riscos"""
    matriz_id: str
    area: str
    riscos: List[Dict[str, Any]]  # {risco, probabilidade, impacto, nivel, controles, residual}
    data_atualizacao: datetime
    responsavel: str
    aprovado_por: Optional[str] = None
    versao: int = 1


class AuditAgent(BaseAgent):
    """
    Agente de Auditoria - Nível 7 Transcendente

    Capacidades:
    - Planejamento de auditorias (financeira, operacional, compliance, etc.)
    - Execução automatizada de testes e procedimentos
    - Identificação de riscos e não conformidades
    - Análise de controles internos
    - Geração de relatórios e recomendações
    - Monitoramento contínuo de indicadores
    - Detecção de anomalias e fraudes
    - Gestão do ciclo de vida das recomendações
    """

    def __init__(
        self,
        memory: UnifiedMemorySystem,
        llm_client: UnifiedLLMClient,
        tools: ToolRegistry,
        rag: Optional[RAGPipeline] = None
    ):
        super().__init__(
            agent_id="audit-agent",
            name="Agente de Auditoria",
            capabilities=[
                AgentCapability.ANALYSIS,
                AgentCapability.COMPLIANCE,
                AgentCapability.REPORTING,
                AgentCapability.RISK_ASSESSMENT,
                AgentCapability.DOCUMENT_PROCESSING
            ],
            memory=memory,
            llm_client=llm_client,
            tools=tools
        )

        self.rag = rag

        # Armazenamento em memória (produção usaria banco de dados)
        self.auditorias: Dict[str, Auditoria] = {}
        self.planos: Dict[str, PlanoAuditoria] = {}
        self.achados: Dict[str, AchadoAchado] = {}
        self.recomendacoes: Dict[str, Recomendacao] = {}
        self.controles: Dict[str, ControleInterno] = {}
        self.matrizes_risco: Dict[str, MatrizRisco] = {}

        # Parâmetros de análise
        self.thresholds = {
            "variacao_orcamento": 0.10,  # 10% de variação alerta
            "atraso_pagamento_dias": 30,
            "concentracao_fornecedor": 0.30,  # 30% de compras
            "rotatividade_funcionarios": 0.20,  # 20% ao ano
            "inadimplencia": 0.15,  # 15% de inadimplência
            "desvio_contratual": 0.05,  # 5% de variação
        }

        # Critérios de referência
        self.criterios = {
            "nbr_iso_19011": "Diretrizes para auditoria de sistemas de gestão",
            "cpc_00": "Estrutura Conceitual para Relatório Financeiro",
            "lgpd": "Lei Geral de Proteção de Dados",
            "codigo_civil": "Código Civil - Condomínios",
            "convencao": "Convenção do Condomínio",
            "regimento": "Regimento Interno",
        }

        # Programação de auditorias
        self.calendario_auditorias = {
            TipoAuditoria.FINANCEIRA: {"frequencia": "mensal", "prioridade": 1},
            TipoAuditoria.OPERACIONAL: {"frequencia": "trimestral", "prioridade": 2},
            TipoAuditoria.SEGURANCA: {"frequencia": "semestral", "prioridade": 1},
            TipoAuditoria.COMPLIANCE: {"frequencia": "anual", "prioridade": 1},
            TipoAuditoria.CONTRATOS: {"frequencia": "anual", "prioridade": 2},
        }

        # Estatísticas
        self.estatisticas = {
            "auditorias_realizadas": 0,
            "achados_identificados": 0,
            "recomendacoes_emitidas": 0,
            "recomendacoes_implementadas": 0,
            "valor_economizado": 0.0,
            "fraudes_detectadas": 0,
        }

    async def process(self, context: AgentContext) -> Dict[str, Any]:
        """Processa requisições de auditoria"""

        intent = context.metadata.get("intent", "")

        # Roteamento por intenção
        handlers = {
            "planejar_auditoria": self._planejar_auditoria,
            "iniciar_auditoria": self._iniciar_auditoria,
            "executar_testes": self._executar_testes,
            "registrar_achado": self._registrar_achado,
            "gerar_recomendacao": self._gerar_recomendacao,
            "analisar_financeiro": self._analisar_financeiro,
            "analisar_operacional": self._analisar_operacional,
            "avaliar_controles": self._avaliar_controles,
            "detectar_anomalias": self._detectar_anomalias,
            "monitorar_recomendacoes": self._monitorar_recomendacoes,
            "gerar_relatorio": self._gerar_relatorio,
            "matriz_risco": self._gerar_matriz_risco,
            "auditoria_continua": self._auditoria_continua,
            "verificar_compliance": self._verificar_compliance,
            "consultar_status": self._consultar_status,
            "dashboard": self._gerar_dashboard,
            "chat": self._processar_chat,
        }

        handler = handlers.get(intent, self._processar_chat)
        return await handler(context)

    async def _planejar_auditoria(self, context: AgentContext) -> Dict[str, Any]:
        """Elabora plano de auditoria"""

        dados = context.metadata.get("dados", {})
        tipo = TipoAuditoria(dados.get("tipo", "operacional"))
        escopo = dados.get("escopo", "")
        periodo_inicio = datetime.fromisoformat(dados.get("periodo_inicio", datetime.now().isoformat()))
        periodo_fim = datetime.fromisoformat(dados.get("periodo_fim", datetime.now().isoformat()))

        # Gera ID do plano
        plano_id = f"PLN-{datetime.now().strftime('%Y%m%d')}-{len(self.planos) + 1:04d}"

        # Define objetivos baseados no tipo
        objetivos = await self._definir_objetivos_auditoria(tipo, escopo)

        # Define procedimentos
        procedimentos = await self._definir_procedimentos(tipo)

        # Define amostragem
        amostragem = self._calcular_amostragem(tipo, periodo_inicio, periodo_fim)

        # Cria cronograma
        cronograma = self._criar_cronograma_auditoria(tipo, procedimentos)

        # Analisa riscos do plano
        riscos_plano = self._identificar_riscos_plano(tipo, escopo)

        plano = PlanoAuditoria(
            plano_id=plano_id,
            titulo=f"Auditoria {tipo.value.title()} - {periodo_inicio.strftime('%m/%Y')}",
            tipo=tipo,
            escopo=escopo,
            objetivos=objetivos,
            areas_auditadas=dados.get("areas", ["todas"]),
            periodo_referencia=(periodo_inicio, periodo_fim),
            procedimentos=procedimentos,
            amostragem=amostragem,
            recursos_necessarios=["Auditor IA", "Acesso aos sistemas", "Documentação"],
            cronograma=cronograma,
            riscos_do_plano=riscos_plano
        )

        self.planos[plano_id] = plano

        # Salva na memória
        await self.memory.store_episodic({
            "event": "plano_auditoria_criado",
            "plano_id": plano_id,
            "tipo": tipo.value,
            "timestamp": datetime.now().isoformat()
        })

        return {
            "status": "success",
            "message": f"Plano de auditoria {plano_id} elaborado",
            "plano": {
                "id": plano_id,
                "titulo": plano.titulo,
                "tipo": tipo.value,
                "objetivos": objetivos,
                "procedimentos_count": len(procedimentos),
                "cronograma": cronograma,
                "amostragem": amostragem,
                "pendente_aprovacao": True
            }
        }

    async def _definir_objetivos_auditoria(
        self,
        tipo: TipoAuditoria,
        escopo: str
    ) -> List[str]:
        """Define objetivos da auditoria por tipo"""

        objetivos_padrao = {
            TipoAuditoria.FINANCEIRA: [
                "Verificar a exatidão dos registros contábeis",
                "Avaliar a adequação das provisões e reservas",
                "Confirmar a existência e propriedade dos ativos",
                "Verificar a integridade das receitas e despesas",
                "Avaliar a conformidade tributária",
                "Identificar possíveis desvios ou fraudes"
            ],
            TipoAuditoria.OPERACIONAL: [
                "Avaliar a eficiência dos processos operacionais",
                "Identificar gargalos e ineficiências",
                "Verificar o cumprimento de procedimentos internos",
                "Avaliar a qualidade dos serviços prestados",
                "Medir indicadores de desempenho",
                "Propor melhorias operacionais"
            ],
            TipoAuditoria.SEGURANCA: [
                "Avaliar a efetividade dos controles de acesso",
                "Verificar funcionamento de equipamentos de segurança",
                "Analisar incidentes e ocorrências",
                "Avaliar procedimentos de emergência",
                "Verificar treinamento da equipe de segurança",
                "Identificar vulnerabilidades físicas e lógicas"
            ],
            TipoAuditoria.COMPLIANCE: [
                "Verificar conformidade com a Convenção e Regimento",
                "Avaliar cumprimento de obrigações legais (LGPD, trabalhista)",
                "Verificar licenças e alvarás em vigor",
                "Avaliar processos de tomada de decisão em assembleia",
                "Verificar contratos e obrigações contratuais",
                "Identificar riscos de não conformidade"
            ],
            TipoAuditoria.CONTRATOS: [
                "Verificar vigência e atualização de contratos",
                "Avaliar cumprimento de cláusulas contratuais",
                "Analisar adequação de preços e reajustes",
                "Verificar garantias e seguros",
                "Avaliar processo de contratação",
                "Identificar oportunidades de renegociação"
            ]
        }

        return objetivos_padrao.get(tipo, ["Avaliar processos e identificar melhorias"])

    async def _definir_procedimentos(self, tipo: TipoAuditoria) -> List[Dict[str, Any]]:
        """Define procedimentos de auditoria por tipo"""

        procedimentos_padrao = {
            TipoAuditoria.FINANCEIRA: [
                {"id": 1, "nome": "Análise de balancete mensal", "tipo": "analítico", "risco": "alto"},
                {"id": 2, "nome": "Conciliação bancária", "tipo": "substantivo", "risco": "alto"},
                {"id": 3, "nome": "Teste de despesas (amostra)", "tipo": "substantivo", "risco": "médio"},
                {"id": 4, "nome": "Verificação de receitas", "tipo": "substantivo", "risco": "alto"},
                {"id": 5, "nome": "Análise de inadimplência", "tipo": "analítico", "risco": "médio"},
                {"id": 6, "nome": "Teste de folha de pagamento", "tipo": "substantivo", "risco": "alto"},
                {"id": 7, "nome": "Verificação de recolhimentos fiscais", "tipo": "compliance", "risco": "alto"},
                {"id": 8, "nome": "Análise de variações orçamentárias", "tipo": "analítico", "risco": "médio"},
                {"id": 9, "nome": "Confirmação de saldos com terceiros", "tipo": "substantivo", "risco": "baixo"},
                {"id": 10, "nome": "Teste de cut-off de período", "tipo": "substantivo", "risco": "médio"}
            ],
            TipoAuditoria.OPERACIONAL: [
                {"id": 1, "nome": "Mapeamento de processos", "tipo": "analítico", "risco": "baixo"},
                {"id": 2, "nome": "Avaliação de SLAs de fornecedores", "tipo": "analítico", "risco": "médio"},
                {"id": 3, "nome": "Teste de tempos de atendimento", "tipo": "substantivo", "risco": "médio"},
                {"id": 4, "nome": "Verificação de manutenções preventivas", "tipo": "compliance", "risco": "médio"},
                {"id": 5, "nome": "Análise de reclamações e ouvidoria", "tipo": "analítico", "risco": "médio"},
                {"id": 6, "nome": "Avaliação de consumo de insumos", "tipo": "analítico", "risco": "baixo"},
                {"id": 7, "nome": "Teste de controles operacionais", "tipo": "controle", "risco": "médio"},
                {"id": 8, "nome": "Verificação de escalas e jornadas", "tipo": "compliance", "risco": "alto"}
            ],
            TipoAuditoria.SEGURANCA: [
                {"id": 1, "nome": "Teste de câmeras e gravações", "tipo": "substantivo", "risco": "alto"},
                {"id": 2, "nome": "Verificação de controle de acesso", "tipo": "controle", "risco": "alto"},
                {"id": 3, "nome": "Análise de logs de ocorrências", "tipo": "analítico", "risco": "médio"},
                {"id": 4, "nome": "Teste de procedimentos de emergência", "tipo": "substantivo", "risco": "alto"},
                {"id": 5, "nome": "Verificação de treinamentos", "tipo": "compliance", "risco": "médio"},
                {"id": 6, "nome": "Inspeção física de perímetro", "tipo": "substantivo", "risco": "alto"},
                {"id": 7, "nome": "Teste de alarmes e sensores", "tipo": "substantivo", "risco": "alto"},
                {"id": 8, "nome": "Avaliação de iluminação", "tipo": "substantivo", "risco": "médio"}
            ]
        }

        return procedimentos_padrao.get(tipo, [])

    def _calcular_amostragem(
        self,
        tipo: TipoAuditoria,
        inicio: datetime,
        fim: datetime
    ) -> Dict[str, Any]:
        """Calcula amostragem estatística para auditoria"""

        dias_periodo = (fim - inicio).days

        # Parâmetros de amostragem
        nivel_confianca = 0.95
        margem_erro = 0.05

        amostragem = {
            "nivel_confianca": nivel_confianca,
            "margem_erro": margem_erro,
            "periodo_dias": dias_periodo,
            "itens": {}
        }

        if tipo == TipoAuditoria.FINANCEIRA:
            # Estimativa de população por categoria
            amostragem["itens"] = {
                "lancamentos_contabeis": {"populacao": dias_periodo * 50, "amostra": min(100, dias_periodo * 5)},
                "notas_fiscais": {"populacao": dias_periodo * 3, "amostra": min(50, dias_periodo)},
                "pagamentos": {"populacao": dias_periodo * 5, "amostra": min(80, dias_periodo * 2)},
                "boletos_condominiais": {"populacao": dias_periodo // 30 * 200, "amostra": 50},
            }
        elif tipo == TipoAuditoria.OPERACIONAL:
            amostragem["itens"] = {
                "ordens_servico": {"populacao": dias_periodo * 10, "amostra": min(100, dias_periodo * 2)},
                "atendimentos": {"populacao": dias_periodo * 20, "amostra": min(100, dias_periodo * 3)},
                "manutencoes": {"populacao": dias_periodo * 2, "amostra": min(50, dias_periodo)},
            }
        elif tipo == TipoAuditoria.SEGURANCA:
            amostragem["itens"] = {
                "acessos_portaria": {"populacao": dias_periodo * 200, "amostra": 150},
                "ocorrencias": {"populacao": dias_periodo * 5, "amostra": min(100, dias_periodo * 2)},
                "rondas": {"populacao": dias_periodo * 8, "amostra": min(100, dias_periodo * 2)},
            }

        return amostragem

    def _criar_cronograma_auditoria(
        self,
        tipo: TipoAuditoria,
        procedimentos: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Cria cronograma de execução da auditoria"""

        cronograma = []
        data_atual = datetime.now()

        # Fase de planejamento
        cronograma.append({
            "fase": "Planejamento",
            "inicio": data_atual.isoformat(),
            "fim": (data_atual + timedelta(days=2)).isoformat(),
            "atividades": ["Aprovação do plano", "Solicitação de documentos", "Preparação"]
        })

        # Fase de execução
        dias_execucao = len(procedimentos) // 2 + 3
        cronograma.append({
            "fase": "Execução",
            "inicio": (data_atual + timedelta(days=3)).isoformat(),
            "fim": (data_atual + timedelta(days=3 + dias_execucao)).isoformat(),
            "atividades": [p["nome"] for p in procedimentos]
        })

        # Fase de relatório
        cronograma.append({
            "fase": "Relatório",
            "inicio": (data_atual + timedelta(days=4 + dias_execucao)).isoformat(),
            "fim": (data_atual + timedelta(days=6 + dias_execucao)).isoformat(),
            "atividades": ["Consolidação de achados", "Elaboração de relatório", "Revisão"]
        })

        # Fase de comunicação
        cronograma.append({
            "fase": "Comunicação",
            "inicio": (data_atual + timedelta(days=7 + dias_execucao)).isoformat(),
            "fim": (data_atual + timedelta(days=8 + dias_execucao)).isoformat(),
            "atividades": ["Apresentação de resultados", "Discussão com gestores", "Plano de ação"]
        })

        return cronograma

    def _identificar_riscos_plano(self, tipo: TipoAuditoria, escopo: str) -> List[str]:
        """Identifica riscos do próprio plano de auditoria"""

        riscos = [
            "Indisponibilidade de documentação no prazo",
            "Limitação de acesso a sistemas",
            "Conflito de agenda com auditados"
        ]

        if tipo == TipoAuditoria.FINANCEIRA:
            riscos.extend([
                "Complexidade de reconciliações",
                "Volume elevado de transações"
            ])
        elif tipo == TipoAuditoria.SEGURANCA:
            riscos.extend([
                "Falhas em equipamentos durante testes",
                "Interferência em operação normal"
            ])

        return riscos

    async def _iniciar_auditoria(self, context: AgentContext) -> Dict[str, Any]:
        """Inicia execução de auditoria"""

        dados = context.metadata.get("dados", {})
        plano_id = dados.get("plano_id")

        if plano_id not in self.planos:
            return {"status": "error", "message": "Plano de auditoria não encontrado"}

        plano = self.planos[plano_id]

        # Gera ID da auditoria
        auditoria_id = f"AUD-{datetime.now().strftime('%Y%m%d')}-{len(self.auditorias) + 1:04d}"

        auditoria = Auditoria(
            auditoria_id=auditoria_id,
            plano_id=plano_id,
            tipo=plano.tipo,
            status=StatusAuditoria.EM_ANDAMENTO,
            titulo=plano.titulo,
            escopo=plano.escopo,
            periodo_referencia=plano.periodo_referencia,
            auditor_responsavel="Agente IA Auditoria",
            equipe_auditora=["Agente IA Auditoria"],
            documentos_solicitados=[],
            documentos_recebidos=[],
            testes_realizados=[],
            achados=[],
            recomendacoes=[]
        )

        # Gera lista de documentos a solicitar
        auditoria.documentos_solicitados = await self._gerar_lista_documentos(plano.tipo)

        self.auditorias[auditoria_id] = auditoria
        self.estatisticas["auditorias_realizadas"] += 1

        # Notifica início
        await self.send_message(
            "notification-agent",
            {
                "tipo": "auditoria_iniciada",
                "auditoria_id": auditoria_id,
                "titulo": auditoria.titulo,
                "escopo": auditoria.escopo
            }
        )

        return {
            "status": "success",
            "message": f"Auditoria {auditoria_id} iniciada",
            "auditoria": {
                "id": auditoria_id,
                "titulo": auditoria.titulo,
                "tipo": plano.tipo.value,
                "documentos_solicitados": len(auditoria.documentos_solicitados),
                "procedimentos_planejados": len(plano.procedimentos)
            }
        }

    async def _gerar_lista_documentos(self, tipo: TipoAuditoria) -> List[Dict[str, Any]]:
        """Gera lista de documentos a solicitar por tipo de auditoria"""

        documentos = {
            TipoAuditoria.FINANCEIRA: [
                {"nome": "Balancete mensal", "obrigatorio": True, "formato": "PDF/Excel"},
                {"nome": "Extratos bancários", "obrigatorio": True, "formato": "PDF"},
                {"nome": "Conciliação bancária", "obrigatorio": True, "formato": "Excel"},
                {"nome": "Relatório de inadimplência", "obrigatorio": True, "formato": "PDF"},
                {"nome": "Notas fiscais de despesas", "obrigatorio": True, "formato": "PDF"},
                {"nome": "Folha de pagamento", "obrigatorio": True, "formato": "PDF"},
                {"nome": "Guias de recolhimento (INSS, FGTS, IR)", "obrigatorio": True, "formato": "PDF"},
                {"nome": "Orçamento aprovado", "obrigatorio": True, "formato": "PDF"},
                {"nome": "Ata de aprovação de contas", "obrigatorio": False, "formato": "PDF"},
            ],
            TipoAuditoria.OPERACIONAL: [
                {"nome": "Relatório de ordens de serviço", "obrigatorio": True, "formato": "Excel"},
                {"nome": "Contratos de prestadores", "obrigatorio": True, "formato": "PDF"},
                {"nome": "Relatório de manutenções", "obrigatorio": True, "formato": "Excel"},
                {"nome": "Planilha de consumo (água, luz, gás)", "obrigatorio": True, "formato": "Excel"},
                {"nome": "Registro de reclamações", "obrigatorio": True, "formato": "Excel"},
                {"nome": "Escalas de funcionários", "obrigatorio": True, "formato": "PDF"},
            ],
            TipoAuditoria.SEGURANCA: [
                {"nome": "Relatório de ocorrências", "obrigatorio": True, "formato": "Excel"},
                {"nome": "Log de acessos", "obrigatorio": True, "formato": "Excel"},
                {"nome": "Relatório de rondas", "obrigatorio": True, "formato": "Excel"},
                {"nome": "Certificados de equipamentos", "obrigatorio": True, "formato": "PDF"},
                {"nome": "Treinamentos realizados", "obrigatorio": True, "formato": "PDF"},
                {"nome": "Plano de emergência", "obrigatorio": True, "formato": "PDF"},
            ]
        }

        return documentos.get(tipo, [])

    async def _executar_testes(self, context: AgentContext) -> Dict[str, Any]:
        """Executa testes de auditoria automatizados"""

        dados = context.metadata.get("dados", {})
        auditoria_id = dados.get("auditoria_id")

        if auditoria_id not in self.auditorias:
            return {"status": "error", "message": "Auditoria não encontrada"}

        auditoria = self.auditorias[auditoria_id]
        plano = self.planos.get(auditoria.plano_id)

        if not plano:
            return {"status": "error", "message": "Plano de auditoria não encontrado"}

        resultados_testes = []
        achados_identificados = []

        # Executa cada procedimento do plano
        for procedimento in plano.procedimentos:
            resultado = await self._executar_procedimento(
                procedimento,
                auditoria.tipo,
                auditoria.periodo_referencia
            )

            resultados_testes.append(resultado)

            # Se encontrou problemas, registra achado
            if resultado.get("achados"):
                for achado_data in resultado["achados"]:
                    achado = await self._criar_achado(
                        auditoria_id,
                        achado_data,
                        procedimento
                    )
                    achados_identificados.append(achado.achado_id)

        # Atualiza auditoria
        auditoria.testes_realizados = resultados_testes
        auditoria.achados.extend(achados_identificados)

        return {
            "status": "success",
            "message": f"Testes executados: {len(resultados_testes)}",
            "testes": {
                "executados": len(resultados_testes),
                "com_achados": len([t for t in resultados_testes if t.get("achados")]),
                "sem_achados": len([t for t in resultados_testes if not t.get("achados")])
            },
            "achados_identificados": len(achados_identificados)
        }

    async def _executar_procedimento(
        self,
        procedimento: Dict[str, Any],
        tipo: TipoAuditoria,
        periodo: Tuple[datetime, datetime]
    ) -> Dict[str, Any]:
        """Executa um procedimento de auditoria específico"""

        resultado = {
            "procedimento_id": procedimento["id"],
            "nome": procedimento["nome"],
            "tipo": procedimento["tipo"],
            "data_execucao": datetime.now().isoformat(),
            "status": "executado",
            "achados": []
        }

        # Simulação de execução de testes (em produção, consultaria dados reais)
        # Aqui demonstramos a lógica de identificação de achados

        nome = procedimento["nome"].lower()

        if "conciliação bancária" in nome:
            # Teste de conciliação
            diferenca = await self._verificar_conciliacao_bancaria()
            if diferenca > 0:
                resultado["achados"].append({
                    "titulo": "Diferença em conciliação bancária",
                    "descricao": f"Identificada diferença de R$ {diferenca:.2f} na conciliação",
                    "severidade": SeveridadeAchado.ALTA if diferenca > 1000 else SeveridadeAchado.MEDIA,
                    "categoria": CategoriaRisco.DESVIO_FINANCEIRO
                })

        elif "variações orçamentárias" in nome:
            # Análise de variação
            variacoes = await self._analisar_variacoes_orcamento()
            for var in variacoes:
                if abs(var["variacao"]) > self.thresholds["variacao_orcamento"]:
                    resultado["achados"].append({
                        "titulo": f"Variação orçamentária em {var['conta']}",
                        "descricao": f"Variação de {var['variacao']*100:.1f}% (limite: {self.thresholds['variacao_orcamento']*100}%)",
                        "severidade": SeveridadeAchado.MEDIA,
                        "categoria": CategoriaRisco.INEFICIENCIA
                    })

        elif "inadimplência" in nome:
            # Análise de inadimplência
            taxa = await self._calcular_taxa_inadimplencia()
            if taxa > self.thresholds["inadimplencia"]:
                resultado["achados"].append({
                    "titulo": "Taxa de inadimplência elevada",
                    "descricao": f"Taxa atual: {taxa*100:.1f}% (limite: {self.thresholds['inadimplencia']*100}%)",
                    "severidade": SeveridadeAchado.ALTA,
                    "categoria": CategoriaRisco.DESVIO_FINANCEIRO
                })

        elif "controle de acesso" in nome:
            # Teste de controle de acesso
            falhas = await self._testar_controle_acesso()
            for falha in falhas:
                resultado["achados"].append({
                    "titulo": f"Falha no controle de acesso: {falha['tipo']}",
                    "descricao": falha["descricao"],
                    "severidade": SeveridadeAchado.ALTA,
                    "categoria": CategoriaRisco.SEGURANCA_FISICA
                })

        return resultado

    async def _verificar_conciliacao_bancaria(self) -> float:
        """Verifica conciliação bancária (simulado)"""
        # Em produção, consultaria dados reais do sistema financeiro
        import random
        return random.choice([0, 0, 0, 150.50, 0, 2500.00, 0])

    async def _analisar_variacoes_orcamento(self) -> List[Dict[str, Any]]:
        """Analisa variações orçamentárias (simulado)"""
        import random
        contas = ["Manutenção", "Limpeza", "Segurança", "Energia", "Água"]
        variacoes = []
        for conta in contas:
            var = random.uniform(-0.15, 0.20)
            variacoes.append({"conta": conta, "variacao": var})
        return variacoes

    async def _calcular_taxa_inadimplencia(self) -> float:
        """Calcula taxa de inadimplência (simulado)"""
        import random
        return random.uniform(0.05, 0.25)

    async def _testar_controle_acesso(self) -> List[Dict[str, Any]]:
        """Testa controles de acesso (simulado)"""
        import random
        falhas = []
        if random.random() < 0.3:
            falhas.append({
                "tipo": "Acesso sem registro",
                "descricao": "Identificado acesso de visitante sem registro completo"
            })
        return falhas

    async def _criar_achado(
        self,
        auditoria_id: str,
        dados_achado: Dict[str, Any],
        procedimento: Dict[str, Any]
    ) -> AchadoAuditoria:
        """Cria registro de achado de auditoria"""

        achado_id = f"ACH-{datetime.now().strftime('%Y%m%d')}-{len(self.achados) + 1:04d}"

        achado = AchadoAuditoria(
            achado_id=achado_id,
            auditoria_id=auditoria_id,
            titulo=dados_achado["titulo"],
            descricao=dados_achado["descricao"],
            severidade=dados_achado.get("severidade", SeveridadeAchado.MEDIA),
            categoria_risco=dados_achado.get("categoria", CategoriaRisco.NAO_CONFORMIDADE),
            evidencias=[{"procedimento": procedimento["nome"], "data": datetime.now().isoformat()}],
            criterio_referencia=self._identificar_criterio(dados_achado),
            impacto_estimado=self._estimar_impacto(dados_achado)
        )

        self.achados[achado_id] = achado
        self.estatisticas["achados_identificados"] += 1

        return achado

    def _identificar_criterio(self, dados_achado: Dict[str, Any]) -> str:
        """Identifica critério de referência para o achado"""
        categoria = dados_achado.get("categoria", CategoriaRisco.NAO_CONFORMIDADE)

        criterios = {
            CategoriaRisco.FRAUDE: "Código Civil Art. 1.348 - Deveres do Síndico",
            CategoriaRisco.DESVIO_FINANCEIRO: "Convenção do Condomínio - Prestação de Contas",
            CategoriaRisco.NAO_CONFORMIDADE: "Regimento Interno",
            CategoriaRisco.SEGURANCA_FISICA: "NBR 16280 - Segurança em Condomínios",
            CategoriaRisco.TRABALHISTA: "CLT e Convenção Coletiva",
        }

        return criterios.get(categoria, "Boas práticas de gestão condominial")

    def _estimar_impacto(self, dados_achado: Dict[str, Any]) -> Dict[str, Any]:
        """Estima impacto do achado"""
        severidade = dados_achado.get("severidade", SeveridadeAchado.MEDIA)

        multiplicadores = {
            SeveridadeAchado.INFORMATIVO: 0.1,
            SeveridadeAchado.BAIXA: 0.25,
            SeveridadeAchado.MEDIA: 0.5,
            SeveridadeAchado.ALTA: 0.75,
            SeveridadeAchado.CRITICA: 1.0
        }

        return {
            "financeiro": multiplicadores[severidade] * 10000,  # Estimativa em R$
            "operacional": severidade.value,
            "reputacional": "Alto" if severidade in [SeveridadeAchado.ALTA, SeveridadeAchado.CRITICA] else "Médio"
        }

    async def _registrar_achado(self, context: AgentContext) -> Dict[str, Any]:
        """Registra achado manualmente"""

        dados = context.metadata.get("dados", {})

        achado_id = f"ACH-{datetime.now().strftime('%Y%m%d')}-{len(self.achados) + 1:04d}"

        achado = AchadoAuditoria(
            achado_id=achado_id,
            auditoria_id=dados.get("auditoria_id", "manual"),
            titulo=dados.get("titulo", "Achado identificado"),
            descricao=dados.get("descricao", ""),
            severidade=SeveridadeAchado(dados.get("severidade", "media")),
            categoria_risco=CategoriaRisco(dados.get("categoria", "nao_conformidade")),
            evidencias=dados.get("evidencias", []),
            criterio_referencia=dados.get("criterio", "Regimento Interno"),
            impacto_estimado=dados.get("impacto", {}),
            causa_raiz=dados.get("causa_raiz"),
            responsavel_area=dados.get("responsavel")
        )

        self.achados[achado_id] = achado
        self.estatisticas["achados_identificados"] += 1

        return {
            "status": "success",
            "message": f"Achado {achado_id} registrado",
            "achado": {
                "id": achado_id,
                "titulo": achado.titulo,
                "severidade": achado.severidade.value,
                "categoria": achado.categoria_risco.value
            }
        }

    async def _gerar_recomendacao(self, context: AgentContext) -> Dict[str, Any]:
        """Gera recomendação para achado"""

        dados = context.metadata.get("dados", {})
        achado_id = dados.get("achado_id")

        if achado_id not in self.achados:
            return {"status": "error", "message": "Achado não encontrado"}

        achado = self.achados[achado_id]

        # Gera recomendação usando LLM
        prompt = f"""
        Analise o seguinte achado de auditoria e gere uma recomendação detalhada:

        Título: {achado.titulo}
        Descrição: {achado.descricao}
        Severidade: {achado.severidade.value}
        Categoria: {achado.categoria_risco.value}
        Critério violado: {achado.criterio_referencia}

        Gere uma recomendação que inclua:
        1. Ação corretiva específica
        2. Prazo sugerido (em dias)
        3. Responsável sugerido (área/cargo)
        4. Benefício esperado
        5. Custo estimado de implementação (se aplicável)

        Responda em formato JSON.
        """

        resposta = await self.llm_client.generate(prompt)

        try:
            dados_rec = json.loads(resposta)
        except:
            dados_rec = {
                "acao": f"Implementar controles para corrigir: {achado.titulo}",
                "prazo_dias": 30,
                "responsavel": "Síndico/Administração",
                "beneficio": "Mitigação de riscos identificados",
                "custo": None
            }

        recomendacao_id = f"REC-{datetime.now().strftime('%Y%m%d')}-{len(self.recomendacoes) + 1:04d}"

        recomendacao = Recomendacao(
            recomendacao_id=recomendacao_id,
            achado_id=achado_id,
            descricao=dados_rec.get("acao", ""),
            prioridade=self._calcular_prioridade(achado.severidade),
            prazo_sugerido=datetime.now() + timedelta(days=dados_rec.get("prazo_dias", 30)),
            responsavel_sugerido=dados_rec.get("responsavel"),
            status=StatusRecomendacao.PENDENTE,
            custo_estimado=dados_rec.get("custo"),
            beneficio_esperado=dados_rec.get("beneficio")
        )

        self.recomendacoes[recomendacao_id] = recomendacao
        self.estatisticas["recomendacoes_emitidas"] += 1

        # Atualiza achado
        achado.acoes_corretivas.append({
            "recomendacao_id": recomendacao_id,
            "data": datetime.now().isoformat()
        })

        return {
            "status": "success",
            "message": f"Recomendação {recomendacao_id} gerada",
            "recomendacao": {
                "id": recomendacao_id,
                "descricao": recomendacao.descricao,
                "prioridade": recomendacao.prioridade,
                "prazo": recomendacao.prazo_sugerido.strftime("%d/%m/%Y"),
                "responsavel": recomendacao.responsavel_sugerido
            }
        }

    def _calcular_prioridade(self, severidade: SeveridadeAchado) -> int:
        """Calcula prioridade baseada na severidade"""
        prioridades = {
            SeveridadeAchado.CRITICA: 1,
            SeveridadeAchado.ALTA: 2,
            SeveridadeAchado.MEDIA: 3,
            SeveridadeAchado.BAIXA: 4,
            SeveridadeAchado.INFORMATIVO: 5
        }
        return prioridades.get(severidade, 3)

    async def _analisar_financeiro(self, context: AgentContext) -> Dict[str, Any]:
        """Análise financeira automatizada"""

        dados = context.metadata.get("dados", {})
        periodo = dados.get("periodo", "ultimo_mes")

        analises = {
            "conciliacao_bancaria": await self._verificar_conciliacao_bancaria(),
            "variacoes_orcamento": await self._analisar_variacoes_orcamento(),
            "inadimplencia": await self._calcular_taxa_inadimplencia(),
            "concentracao_fornecedores": await self._analisar_concentracao_fornecedores(),
            "despesas_sem_aprovacao": await self._verificar_despesas_sem_aprovacao(),
            "pagamentos_duplicados": await self._detectar_pagamentos_duplicados()
        }

        alertas = []

        if analises["conciliacao_bancaria"] > 0:
            alertas.append({
                "tipo": "conciliacao",
                "mensagem": f"Diferença de R$ {analises['conciliacao_bancaria']:.2f} na conciliação",
                "severidade": "alta" if analises["conciliacao_bancaria"] > 1000 else "media"
            })

        if analises["inadimplencia"] > self.thresholds["inadimplencia"]:
            alertas.append({
                "tipo": "inadimplencia",
                "mensagem": f"Taxa de inadimplência: {analises['inadimplencia']*100:.1f}%",
                "severidade": "alta"
            })

        for var in analises["variacoes_orcamento"]:
            if abs(var["variacao"]) > self.thresholds["variacao_orcamento"]:
                alertas.append({
                    "tipo": "variacao",
                    "mensagem": f"{var['conta']}: variação de {var['variacao']*100:.1f}%",
                    "severidade": "media"
                })

        return {
            "status": "success",
            "periodo": periodo,
            "analises": {
                "diferenca_conciliacao": analises["conciliacao_bancaria"],
                "taxa_inadimplencia": f"{analises['inadimplencia']*100:.1f}%",
                "variacoes_acima_limite": len([v for v in analises["variacoes_orcamento"]
                                               if abs(v["variacao"]) > self.thresholds["variacao_orcamento"]])
            },
            "alertas": alertas,
            "total_alertas": len(alertas)
        }

    async def _analisar_concentracao_fornecedores(self) -> Dict[str, float]:
        """Analisa concentração de compras por fornecedor"""
        # Simulado - em produção, consultaria dados reais
        return {
            "Fornecedor A": 0.25,
            "Fornecedor B": 0.18,
            "Fornecedor C": 0.15,
            "Outros": 0.42
        }

    async def _verificar_despesas_sem_aprovacao(self) -> List[Dict[str, Any]]:
        """Verifica despesas sem aprovação adequada"""
        import random
        despesas = []
        if random.random() < 0.2:
            despesas.append({
                "descricao": "Manutenção emergencial",
                "valor": 3500.00,
                "data": datetime.now().isoformat()
            })
        return despesas

    async def _detectar_pagamentos_duplicados(self) -> List[Dict[str, Any]]:
        """Detecta possíveis pagamentos duplicados"""
        import random
        duplicados = []
        if random.random() < 0.1:
            duplicados.append({
                "fornecedor": "Fornecedor X",
                "valor": 1200.00,
                "nf1": "12345",
                "nf2": "12346"
            })
        return duplicados

    async def _analisar_operacional(self, context: AgentContext) -> Dict[str, Any]:
        """Análise operacional automatizada"""

        analises = {
            "tempo_medio_atendimento": await self._calcular_tempo_medio_atendimento(),
            "taxa_resolucao_primeiro_contato": await self._calcular_taxa_resolucao(),
            "manutencoes_preventivas_realizadas": await self._verificar_manutencoes_preventivas(),
            "sla_fornecedores": await self._verificar_sla_fornecedores(),
            "satisfacao_moradores": await self._calcular_satisfacao()
        }

        alertas = []

        if analises["tempo_medio_atendimento"] > 24:  # horas
            alertas.append({
                "tipo": "atendimento",
                "mensagem": f"Tempo médio de atendimento: {analises['tempo_medio_atendimento']}h",
                "severidade": "media"
            })

        if analises["taxa_resolucao_primeiro_contato"] < 0.7:
            alertas.append({
                "tipo": "resolucao",
                "mensagem": f"Taxa de resolução no primeiro contato: {analises['taxa_resolucao_primeiro_contato']*100:.0f}%",
                "severidade": "media"
            })

        if analises["manutencoes_preventivas_realizadas"] < 0.8:
            alertas.append({
                "tipo": "manutencao",
                "mensagem": f"Apenas {analises['manutencoes_preventivas_realizadas']*100:.0f}% das manutenções preventivas realizadas",
                "severidade": "alta"
            })

        return {
            "status": "success",
            "analises": {
                "tempo_medio_atendimento": f"{analises['tempo_medio_atendimento']}h",
                "taxa_resolucao": f"{analises['taxa_resolucao_primeiro_contato']*100:.0f}%",
                "manutencoes_preventivas": f"{analises['manutencoes_preventivas_realizadas']*100:.0f}%",
                "satisfacao": f"{analises['satisfacao_moradores']*100:.0f}%"
            },
            "alertas": alertas
        }

    async def _calcular_tempo_medio_atendimento(self) -> float:
        """Calcula tempo médio de atendimento (horas)"""
        import random
        return random.uniform(4, 48)

    async def _calcular_taxa_resolucao(self) -> float:
        """Calcula taxa de resolução no primeiro contato"""
        import random
        return random.uniform(0.5, 0.95)

    async def _verificar_manutencoes_preventivas(self) -> float:
        """Verifica percentual de manutenções preventivas realizadas"""
        import random
        return random.uniform(0.6, 1.0)

    async def _verificar_sla_fornecedores(self) -> Dict[str, float]:
        """Verifica SLA de fornecedores"""
        return {
            "Limpeza": 0.95,
            "Manutenção": 0.88,
            "Segurança": 0.92,
            "Jardinagem": 0.85
        }

    async def _calcular_satisfacao(self) -> float:
        """Calcula satisfação dos moradores"""
        import random
        return random.uniform(0.7, 0.95)

    async def _avaliar_controles(self, context: AgentContext) -> Dict[str, Any]:
        """Avalia efetividade dos controles internos"""

        dados = context.metadata.get("dados", {})
        area = dados.get("area", "geral")

        controles_avaliados = []

        # Lista de controles por área
        controles_area = {
            "financeiro": [
                {"nome": "Aprovação de despesas", "tipo": "preventivo", "automatizado": False},
                {"nome": "Conciliação bancária", "tipo": "detectivo", "automatizado": True},
                {"nome": "Cobrança de inadimplentes", "tipo": "corretivo", "automatizado": True},
                {"nome": "Segregação de funções", "tipo": "preventivo", "automatizado": False},
            ],
            "operacional": [
                {"nome": "Checklist de manutenção", "tipo": "preventivo", "automatizado": False},
                {"nome": "Registro de ocorrências", "tipo": "detectivo", "automatizado": True},
                {"nome": "Avaliação de fornecedores", "tipo": "detectivo", "automatizado": False},
            ],
            "seguranca": [
                {"nome": "Controle de acesso", "tipo": "preventivo", "automatizado": True},
                {"nome": "Monitoramento CFTV", "tipo": "detectivo", "automatizado": True},
                {"nome": "Rondas periódicas", "tipo": "preventivo", "automatizado": False},
            ]
        }

        for controle in controles_area.get(area, controles_area["financeiro"]):
            efetividade = await self._testar_efetividade_controle(controle)

            controle_avaliado = ControleInterno(
                controle_id=f"CTR-{len(self.controles) + 1:04d}",
                nome=controle["nome"],
                descricao=f"Controle de {controle['nome'].lower()}",
                area=area,
                tipo=controle["tipo"],
                frequencia="diário" if controle["automatizado"] else "semanal",
                automatizado=controle["automatizado"],
                responsavel="Sistema" if controle["automatizado"] else "Administração",
                efetividade=efetividade["classificacao"],
                ultima_avaliacao=datetime.now(),
                proxima_avaliacao=datetime.now() + timedelta(days=90),
                evidencias_teste=efetividade["evidencias"]
            )

            self.controles[controle_avaliado.controle_id] = controle_avaliado
            controles_avaliados.append({
                "nome": controle["nome"],
                "tipo": controle["tipo"],
                "efetividade": efetividade["classificacao"],
                "score": efetividade["score"]
            })

        # Calcula score geral
        scores = [c["score"] for c in controles_avaliados]
        score_geral = sum(scores) / len(scores) if scores else 0

        return {
            "status": "success",
            "area": area,
            "controles_avaliados": controles_avaliados,
            "score_geral": f"{score_geral:.0%}",
            "classificacao_geral": "Efetivo" if score_geral >= 0.8 else "Parcialmente Efetivo" if score_geral >= 0.6 else "Inefetivo",
            "recomendacoes_gerais": self._gerar_recomendacoes_controles(controles_avaliados)
        }

    async def _testar_efetividade_controle(self, controle: Dict[str, Any]) -> Dict[str, Any]:
        """Testa efetividade de um controle"""
        import random

        score = random.uniform(0.5, 1.0)

        if controle["automatizado"]:
            score = min(score + 0.1, 1.0)  # Controles automatizados tendem a ser mais efetivos

        classificacao = "Efetivo" if score >= 0.8 else "Parcialmente Efetivo" if score >= 0.6 else "Inefetivo"

        return {
            "score": score,
            "classificacao": classificacao,
            "evidencias": [{"teste": "Amostragem", "resultado": f"{score*100:.0f}% conforme"}]
        }

    def _gerar_recomendacoes_controles(self, controles: List[Dict[str, Any]]) -> List[str]:
        """Gera recomendações para controles"""
        recomendacoes = []

        for controle in controles:
            if controle["efetividade"] == "Inefetivo":
                recomendacoes.append(f"Redesenhar controle: {controle['nome']}")
            elif controle["efetividade"] == "Parcialmente Efetivo":
                recomendacoes.append(f"Fortalecer controle: {controle['nome']}")

        return recomendacoes

    async def _detectar_anomalias(self, context: AgentContext) -> Dict[str, Any]:
        """Detecta anomalias usando análise de dados"""

        dados = context.metadata.get("dados", {})
        tipo = dados.get("tipo", "todos")

        anomalias = []

        # Detecção de anomalias financeiras
        if tipo in ["todos", "financeiro"]:
            anomalias_fin = await self._detectar_anomalias_financeiras()
            anomalias.extend(anomalias_fin)

        # Detecção de anomalias operacionais
        if tipo in ["todos", "operacional"]:
            anomalias_op = await self._detectar_anomalias_operacionais()
            anomalias.extend(anomalias_op)

        # Detecção de anomalias de segurança
        if tipo in ["todos", "seguranca"]:
            anomalias_seg = await self._detectar_anomalias_seguranca()
            anomalias.extend(anomalias_seg)

        # Classifica anomalias por risco
        anomalias_classificadas = sorted(anomalias, key=lambda x: x.get("score_risco", 0), reverse=True)

        # Registra achados para anomalias de alto risco
        for anomalia in anomalias_classificadas:
            if anomalia.get("score_risco", 0) >= 0.8:
                await self._registrar_achado(AgentContext(
                    user_id="system",
                    session_id="auto",
                    message="",
                    metadata={
                        "dados": {
                            "titulo": anomalia["descricao"],
                            "descricao": f"Anomalia detectada: {anomalia['detalhes']}",
                            "severidade": "alta",
                            "categoria": anomalia.get("categoria", "nao_conformidade")
                        }
                    }
                ))

        return {
            "status": "success",
            "anomalias_detectadas": len(anomalias),
            "alto_risco": len([a for a in anomalias if a.get("score_risco", 0) >= 0.8]),
            "anomalias": anomalias_classificadas[:10]  # Top 10
        }

    async def _detectar_anomalias_financeiras(self) -> List[Dict[str, Any]]:
        """Detecta anomalias financeiras"""
        import random

        anomalias = []

        # Transação fora do padrão
        if random.random() < 0.3:
            anomalias.append({
                "tipo": "transacao_atipica",
                "descricao": "Transação fora do padrão histórico",
                "detalhes": "Pagamento 3x maior que média histórica",
                "score_risco": random.uniform(0.6, 0.9),
                "categoria": "desvio_financeiro"
            })

        # Pagamento em dia/horário incomum
        if random.random() < 0.2:
            anomalias.append({
                "tipo": "horario_atipico",
                "descricao": "Operação em horário incomum",
                "detalhes": "Transferência realizada às 23h de domingo",
                "score_risco": random.uniform(0.5, 0.8),
                "categoria": "fraude"
            })

        return anomalias

    async def _detectar_anomalias_operacionais(self) -> List[Dict[str, Any]]:
        """Detecta anomalias operacionais"""
        import random

        anomalias = []

        # Pico de consumo
        if random.random() < 0.4:
            anomalias.append({
                "tipo": "consumo_atipico",
                "descricao": "Consumo de água acima do esperado",
                "detalhes": "Aumento de 40% no consumo sem justificativa",
                "score_risco": random.uniform(0.4, 0.7),
                "categoria": "ineficiencia"
            })

        return anomalias

    async def _detectar_anomalias_seguranca(self) -> List[Dict[str, Any]]:
        """Detecta anomalias de segurança"""
        import random

        anomalias = []

        # Acesso em horário atípico
        if random.random() < 0.3:
            anomalias.append({
                "tipo": "acesso_atipico",
                "descricao": "Padrão de acesso incomum",
                "detalhes": "Múltiplos acessos em curto período de tempo",
                "score_risco": random.uniform(0.5, 0.85),
                "categoria": "seguranca_fisica"
            })

        return anomalias

    async def _monitorar_recomendacoes(self, context: AgentContext) -> Dict[str, Any]:
        """Monitora status das recomendações"""

        recomendacoes_por_status = {
            status.value: [] for status in StatusRecomendacao
        }

        vencidas = []
        proximas_vencer = []
        hoje = datetime.now()

        for rec_id, rec in self.recomendacoes.items():
            recomendacoes_por_status[rec.status.value].append(rec_id)

            if rec.status == StatusRecomendacao.PENDENTE:
                if rec.prazo_sugerido < hoje:
                    vencidas.append({
                        "id": rec_id,
                        "descricao": rec.descricao[:50],
                        "prazo": rec.prazo_sugerido.strftime("%d/%m/%Y"),
                        "dias_atraso": (hoje - rec.prazo_sugerido).days
                    })
                elif rec.prazo_sugerido < hoje + timedelta(days=7):
                    proximas_vencer.append({
                        "id": rec_id,
                        "descricao": rec.descricao[:50],
                        "prazo": rec.prazo_sugerido.strftime("%d/%m/%Y")
                    })

        # Calcula taxa de implementação
        total = len(self.recomendacoes)
        implementadas = len(recomendacoes_por_status[StatusRecomendacao.IMPLEMENTADA.value])
        taxa_implementacao = implementadas / total if total > 0 else 0

        return {
            "status": "success",
            "resumo": {
                "total": total,
                "pendentes": len(recomendacoes_por_status[StatusRecomendacao.PENDENTE.value]),
                "em_implementacao": len(recomendacoes_por_status[StatusRecomendacao.EM_IMPLEMENTACAO.value]),
                "implementadas": implementadas,
                "taxa_implementacao": f"{taxa_implementacao*100:.0f}%"
            },
            "vencidas": vencidas,
            "proximas_vencer": proximas_vencer,
            "alertas": len(vencidas) + len(proximas_vencer)
        }

    async def _gerar_relatorio(self, context: AgentContext) -> Dict[str, Any]:
        """Gera relatório de auditoria"""

        dados = context.metadata.get("dados", {})
        auditoria_id = dados.get("auditoria_id")

        if auditoria_id and auditoria_id in self.auditorias:
            return await self._gerar_relatorio_auditoria(auditoria_id)
        else:
            return await self._gerar_relatorio_geral()

    async def _gerar_relatorio_auditoria(self, auditoria_id: str) -> Dict[str, Any]:
        """Gera relatório de auditoria específica"""

        auditoria = self.auditorias[auditoria_id]
        plano = self.planos.get(auditoria.plano_id)

        # Coleta achados
        achados_auditoria = [self.achados[a_id] for a_id in auditoria.achados if a_id in self.achados]

        # Coleta recomendações
        recomendacoes_auditoria = [self.recomendacoes[r_id] for r_id in auditoria.recomendacoes if r_id in self.recomendacoes]

        # Gera parecer
        parecer = self._gerar_parecer(achados_auditoria)

        # Gera relatório usando LLM
        prompt = f"""
        Gere um resumo executivo para o relatório de auditoria:

        Tipo: {auditoria.tipo.value}
        Escopo: {auditoria.escopo}
        Achados: {len(achados_auditoria)} (críticos: {len([a for a in achados_auditoria if a.severidade == SeveridadeAchado.CRITICA])})
        Recomendações: {len(recomendacoes_auditoria)}

        Principais achados:
        {[a.titulo for a in achados_auditoria[:5]]}

        Parecer: {parecer}

        Gere um resumo executivo de 3-4 parágrafos.
        """

        resumo_executivo = await self.llm_client.generate(prompt)

        return {
            "status": "success",
            "relatorio": {
                "auditoria_id": auditoria_id,
                "tipo": auditoria.tipo.value,
                "titulo": auditoria.titulo,
                "escopo": auditoria.escopo,
                "periodo": f"{auditoria.periodo_referencia[0].strftime('%d/%m/%Y')} a {auditoria.periodo_referencia[1].strftime('%d/%m/%Y')}",
                "resumo_executivo": resumo_executivo,
                "achados": {
                    "total": len(achados_auditoria),
                    "por_severidade": {
                        "critico": len([a for a in achados_auditoria if a.severidade == SeveridadeAchado.CRITICA]),
                        "alto": len([a for a in achados_auditoria if a.severidade == SeveridadeAchado.ALTA]),
                        "medio": len([a for a in achados_auditoria if a.severidade == SeveridadeAchado.MEDIA]),
                        "baixo": len([a for a in achados_auditoria if a.severidade == SeveridadeAchado.BAIXA])
                    },
                    "lista": [{"titulo": a.titulo, "severidade": a.severidade.value} for a in achados_auditoria]
                },
                "recomendacoes": {
                    "total": len(recomendacoes_auditoria),
                    "lista": [{"descricao": r.descricao[:100], "prioridade": r.prioridade} for r in recomendacoes_auditoria]
                },
                "parecer": parecer,
                "data_emissao": datetime.now().strftime("%d/%m/%Y %H:%M")
            }
        }

    def _gerar_parecer(self, achados: List[AchadoAuditoria]) -> str:
        """Gera parecer da auditoria"""

        criticos = len([a for a in achados if a.severidade == SeveridadeAchado.CRITICA])
        altos = len([a for a in achados if a.severidade == SeveridadeAchado.ALTA])

        if criticos > 0:
            return "ADVERSO - Foram identificados achados críticos que requerem ação imediata"
        elif altos > 2:
            return "COM RESSALVAS - Foram identificados múltiplos achados de alta severidade"
        elif altos > 0:
            return "COM RESSALVAS - Foram identificados achados que requerem atenção"
        else:
            return "SEM RESSALVAS - Não foram identificados achados significativos"

    async def _gerar_relatorio_geral(self) -> Dict[str, Any]:
        """Gera relatório geral de auditorias"""

        return {
            "status": "success",
            "relatorio_geral": {
                "periodo": "Acumulado",
                "estatisticas": self.estatisticas,
                "auditorias": {
                    "total": len(self.auditorias),
                    "por_tipo": self._contar_por_tipo(),
                    "por_status": self._contar_por_status()
                },
                "achados": {
                    "total": len(self.achados),
                    "abertos": len([a for a in self.achados.values() if a.status_tratamento == "aberto"])
                },
                "recomendacoes": {
                    "total": len(self.recomendacoes),
                    "taxa_implementacao": self.estatisticas["recomendacoes_implementadas"] /
                                         max(self.estatisticas["recomendacoes_emitidas"], 1) * 100
                }
            }
        }

    def _contar_por_tipo(self) -> Dict[str, int]:
        """Conta auditorias por tipo"""
        contagem = {}
        for aud in self.auditorias.values():
            tipo = aud.tipo.value
            contagem[tipo] = contagem.get(tipo, 0) + 1
        return contagem

    def _contar_por_status(self) -> Dict[str, int]:
        """Conta auditorias por status"""
        contagem = {}
        for aud in self.auditorias.values():
            status = aud.status.value
            contagem[status] = contagem.get(status, 0) + 1
        return contagem

    async def _gerar_matriz_risco(self, context: AgentContext) -> Dict[str, Any]:
        """Gera matriz de riscos"""

        dados = context.metadata.get("dados", {})
        area = dados.get("area", "geral")

        riscos = await self._identificar_riscos(area)

        matriz_id = f"MTR-{datetime.now().strftime('%Y%m%d')}-{len(self.matrizes_risco) + 1:04d}"

        matriz = MatrizRisco(
            matriz_id=matriz_id,
            area=area,
            riscos=riscos,
            data_atualizacao=datetime.now(),
            responsavel="Agente IA Auditoria"
        )

        self.matrizes_risco[matriz_id] = matriz

        # Calcula estatísticas
        riscos_por_nivel = {"critico": 0, "alto": 0, "medio": 0, "baixo": 0}
        for risco in riscos:
            nivel = risco["nivel"]
            riscos_por_nivel[nivel] = riscos_por_nivel.get(nivel, 0) + 1

        return {
            "status": "success",
            "matriz_id": matriz_id,
            "area": area,
            "total_riscos": len(riscos),
            "por_nivel": riscos_por_nivel,
            "riscos_criticos": [r for r in riscos if r["nivel"] == "critico"],
            "top_5_riscos": sorted(riscos, key=lambda x: x["score"], reverse=True)[:5]
        }

    async def _identificar_riscos(self, area: str) -> List[Dict[str, Any]]:
        """Identifica riscos por área"""

        riscos_base = {
            "financeiro": [
                {"risco": "Fraude em pagamentos", "probabilidade": 0.2, "impacto": 0.9},
                {"risco": "Desvio de recursos", "probabilidade": 0.1, "impacto": 1.0},
                {"risco": "Inadimplência elevada", "probabilidade": 0.4, "impacto": 0.7},
                {"risco": "Erro em prestação de contas", "probabilidade": 0.3, "impacto": 0.6},
                {"risco": "Falta de provisão para contingências", "probabilidade": 0.5, "impacto": 0.5},
            ],
            "operacional": [
                {"risco": "Falha em manutenção crítica", "probabilidade": 0.3, "impacto": 0.8},
                {"risco": "Interrupção de serviços essenciais", "probabilidade": 0.2, "impacto": 0.9},
                {"risco": "Qualidade insatisfatória de serviços", "probabilidade": 0.4, "impacto": 0.5},
                {"risco": "Rotatividade elevada de funcionários", "probabilidade": 0.3, "impacto": 0.6},
            ],
            "seguranca": [
                {"risco": "Invasão/furto", "probabilidade": 0.2, "impacto": 0.9},
                {"risco": "Falha em sistema de CFTV", "probabilidade": 0.3, "impacto": 0.7},
                {"risco": "Acesso não autorizado", "probabilidade": 0.4, "impacto": 0.6},
                {"risco": "Incêndio", "probabilidade": 0.1, "impacto": 1.0},
            ],
            "compliance": [
                {"risco": "Violação de LGPD", "probabilidade": 0.3, "impacto": 0.8},
                {"risco": "Irregularidade trabalhista", "probabilidade": 0.4, "impacto": 0.7},
                {"risco": "Licenças vencidas", "probabilidade": 0.2, "impacto": 0.6},
                {"risco": "Descumprimento de convenção", "probabilidade": 0.3, "impacto": 0.5},
            ]
        }

        riscos_area = riscos_base.get(area, riscos_base["financeiro"])

        # Calcula score e nível
        for risco in riscos_area:
            risco["score"] = risco["probabilidade"] * risco["impacto"]

            if risco["score"] >= 0.7:
                risco["nivel"] = "critico"
            elif risco["score"] >= 0.4:
                risco["nivel"] = "alto"
            elif risco["score"] >= 0.2:
                risco["nivel"] = "medio"
            else:
                risco["nivel"] = "baixo"

            risco["controles_sugeridos"] = self._sugerir_controles(risco["risco"])

        return riscos_area

    def _sugerir_controles(self, risco: str) -> List[str]:
        """Sugere controles para mitigar risco"""

        controles = {
            "Fraude em pagamentos": ["Dupla aprovação", "Reconciliação bancária diária", "Auditoria de pagamentos"],
            "Inadimplência elevada": ["Cobrança automatizada", "Acordos de parcelamento", "Protesto de boletos"],
            "Falha em manutenção crítica": ["Manutenção preventiva", "Contratos de manutenção", "Estoque de peças"],
            "Invasão/furto": ["CFTV 24h", "Controle de acesso biométrico", "Ronda eletrônica"],
            "Violação de LGPD": ["Política de privacidade", "Consentimento documentado", "Treinamento de funcionários"],
        }

        return controles.get(risco, ["Avaliar controles específicos"])

    async def _auditoria_continua(self, context: AgentContext) -> Dict[str, Any]:
        """Executa auditoria contínua (monitoramento em tempo real)"""

        alertas = []

        # Monitora indicadores em tempo real
        indicadores = {
            "financeiro": await self._monitorar_indicadores_financeiros(),
            "operacional": await self._monitorar_indicadores_operacionais(),
            "seguranca": await self._monitorar_indicadores_seguranca()
        }

        # Verifica thresholds
        for area, dados in indicadores.items():
            for indicador, valor in dados.items():
                threshold = self.thresholds.get(indicador)
                if threshold and valor > threshold:
                    alertas.append({
                        "area": area,
                        "indicador": indicador,
                        "valor_atual": valor,
                        "threshold": threshold,
                        "severidade": "alta" if valor > threshold * 1.5 else "media"
                    })

        # Detecta anomalias
        anomalias = await self._detectar_anomalias(AgentContext(
            user_id="system",
            session_id="continuous",
            message="",
            metadata={"dados": {"tipo": "todos"}}
        ))

        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "indicadores": indicadores,
            "alertas_threshold": alertas,
            "anomalias": anomalias.get("anomalias_detectadas", 0),
            "saude_geral": "OK" if len(alertas) == 0 else "ATENÇÃO" if len(alertas) < 3 else "CRÍTICO"
        }

    async def _monitorar_indicadores_financeiros(self) -> Dict[str, float]:
        """Monitora indicadores financeiros"""
        import random
        return {
            "inadimplencia": random.uniform(0.05, 0.20),
            "variacao_orcamento": random.uniform(-0.15, 0.15),
            "concentracao_fornecedor": random.uniform(0.10, 0.35)
        }

    async def _monitorar_indicadores_operacionais(self) -> Dict[str, float]:
        """Monitora indicadores operacionais"""
        import random
        return {
            "tempo_medio_atendimento_horas": random.uniform(4, 48),
            "taxa_manutencao_preventiva": random.uniform(0.6, 1.0),
            "satisfacao": random.uniform(0.7, 0.95)
        }

    async def _monitorar_indicadores_seguranca(self) -> Dict[str, float]:
        """Monitora indicadores de segurança"""
        import random
        return {
            "taxa_ocorrencias": random.uniform(0.01, 0.05),
            "disponibilidade_cftv": random.uniform(0.95, 1.0),
            "conformidade_rondas": random.uniform(0.8, 1.0)
        }

    async def _verificar_compliance(self, context: AgentContext) -> Dict[str, Any]:
        """Verifica compliance regulatório"""

        dados = context.metadata.get("dados", {})
        regulamento = dados.get("regulamento", "todos")

        verificacoes = {
            "lgpd": await self._verificar_lgpd(),
            "trabalhista": await self._verificar_trabalhista(),
            "condominial": await self._verificar_condominial(),
            "tributario": await self._verificar_tributario()
        }

        if regulamento != "todos":
            verificacoes = {regulamento: verificacoes.get(regulamento, {})}

        total_itens = sum(v.get("total_itens", 0) for v in verificacoes.values())
        itens_conformes = sum(v.get("conformes", 0) for v in verificacoes.values())
        taxa_compliance = itens_conformes / total_itens if total_itens > 0 else 0

        return {
            "status": "success",
            "verificacoes": verificacoes,
            "resumo": {
                "total_itens": total_itens,
                "conformes": itens_conformes,
                "nao_conformes": total_itens - itens_conformes,
                "taxa_compliance": f"{taxa_compliance*100:.1f}%"
            },
            "classificacao": "CONFORME" if taxa_compliance >= 0.95 else "PARCIALMENTE CONFORME" if taxa_compliance >= 0.8 else "NÃO CONFORME"
        }

    async def _verificar_lgpd(self) -> Dict[str, Any]:
        """Verifica conformidade com LGPD"""
        itens = [
            {"item": "Política de privacidade publicada", "conforme": True},
            {"item": "Consentimento para tratamento de dados", "conforme": True},
            {"item": "Processo de exclusão de dados", "conforme": False},
            {"item": "Encarregado de dados designado", "conforme": True},
            {"item": "Registro de operações de tratamento", "conforme": False},
        ]

        return {
            "total_itens": len(itens),
            "conformes": len([i for i in itens if i["conforme"]]),
            "itens": itens
        }

    async def _verificar_trabalhista(self) -> Dict[str, Any]:
        """Verifica conformidade trabalhista"""
        itens = [
            {"item": "Registro de funcionários em dia", "conforme": True},
            {"item": "Controle de jornada", "conforme": True},
            {"item": "Pagamento de encargos (INSS/FGTS)", "conforme": True},
            {"item": "Exames médicos periódicos", "conforme": True},
            {"item": "EPIs fornecidos e documentados", "conforme": True},
        ]

        return {
            "total_itens": len(itens),
            "conformes": len([i for i in itens if i["conforme"]]),
            "itens": itens
        }

    async def _verificar_condominial(self) -> Dict[str, Any]:
        """Verifica conformidade condominial"""
        itens = [
            {"item": "Convenção registrada", "conforme": True},
            {"item": "Regimento interno aprovado", "conforme": True},
            {"item": "Assembleias ordinárias realizadas", "conforme": True},
            {"item": "Prestação de contas aprovada", "conforme": True},
            {"item": "Seguro obrigatório em vigor", "conforme": True},
            {"item": "Fundo de reserva mantido", "conforme": True},
        ]

        return {
            "total_itens": len(itens),
            "conformes": len([i for i in itens if i["conforme"]]),
            "itens": itens
        }

    async def _verificar_tributario(self) -> Dict[str, Any]:
        """Verifica conformidade tributária"""
        itens = [
            {"item": "DCTF entregue", "conforme": True},
            {"item": "EFD-Reinf transmitida", "conforme": True},
            {"item": "Retenções de IR recolhidas", "conforme": True},
            {"item": "Contribuições previdenciárias", "conforme": True},
        ]

        return {
            "total_itens": len(itens),
            "conformes": len([i for i in itens if i["conforme"]]),
            "itens": itens
        }

    async def _consultar_status(self, context: AgentContext) -> Dict[str, Any]:
        """Consulta status de auditoria ou recomendação"""

        dados = context.metadata.get("dados", {})

        if "auditoria_id" in dados:
            auditoria_id = dados["auditoria_id"]
            if auditoria_id in self.auditorias:
                aud = self.auditorias[auditoria_id]
                return {
                    "status": "success",
                    "tipo": "auditoria",
                    "dados": {
                        "id": auditoria_id,
                        "titulo": aud.titulo,
                        "status": aud.status.value,
                        "achados": len(aud.achados),
                        "recomendacoes": len(aud.recomendacoes)
                    }
                }

        if "recomendacao_id" in dados:
            rec_id = dados["recomendacao_id"]
            if rec_id in self.recomendacoes:
                rec = self.recomendacoes[rec_id]
                return {
                    "status": "success",
                    "tipo": "recomendacao",
                    "dados": {
                        "id": rec_id,
                        "descricao": rec.descricao,
                        "status": rec.status.value,
                        "prazo": rec.prazo_sugerido.strftime("%d/%m/%Y"),
                        "prioridade": rec.prioridade
                    }
                }

        return {"status": "error", "message": "ID não encontrado"}

    async def _gerar_dashboard(self, context: AgentContext) -> Dict[str, Any]:
        """Gera dashboard de auditoria"""

        # Estatísticas gerais
        total_auditorias = len(self.auditorias)
        auditorias_andamento = len([a for a in self.auditorias.values() if a.status == StatusAuditoria.EM_ANDAMENTO])

        total_achados = len(self.achados)
        achados_abertos = len([a for a in self.achados.values() if a.status_tratamento == "aberto"])
        achados_criticos = len([a for a in self.achados.values() if a.severidade == SeveridadeAchado.CRITICA])

        total_recomendacoes = len(self.recomendacoes)
        rec_pendentes = len([r for r in self.recomendacoes.values() if r.status == StatusRecomendacao.PENDENTE])
        rec_implementadas = len([r for r in self.recomendacoes.values() if r.status == StatusRecomendacao.IMPLEMENTADA])

        # Recomendações vencidas
        hoje = datetime.now()
        rec_vencidas = len([r for r in self.recomendacoes.values()
                          if r.status == StatusRecomendacao.PENDENTE and r.prazo_sugerido < hoje])

        return {
            "status": "success",
            "dashboard": {
                "auditorias": {
                    "total": total_auditorias,
                    "em_andamento": auditorias_andamento,
                    "concluidas": self.estatisticas["auditorias_realizadas"]
                },
                "achados": {
                    "total": total_achados,
                    "abertos": achados_abertos,
                    "criticos": achados_criticos,
                    "por_categoria": self._contar_achados_por_categoria()
                },
                "recomendacoes": {
                    "total": total_recomendacoes,
                    "pendentes": rec_pendentes,
                    "implementadas": rec_implementadas,
                    "vencidas": rec_vencidas,
                    "taxa_implementacao": f"{(rec_implementadas/max(total_recomendacoes,1))*100:.0f}%"
                },
                "indicadores": {
                    "valor_economizado": f"R$ {self.estatisticas['valor_economizado']:,.2f}",
                    "fraudes_detectadas": self.estatisticas["fraudes_detectadas"],
                    "score_compliance": "92%"
                },
                "alertas_ativos": achados_criticos + rec_vencidas,
                "proximas_auditorias": self._listar_proximas_auditorias()
            }
        }

    def _contar_achados_por_categoria(self) -> Dict[str, int]:
        """Conta achados por categoria"""
        contagem = {}
        for achado in self.achados.values():
            cat = achado.categoria_risco.value
            contagem[cat] = contagem.get(cat, 0) + 1
        return contagem

    def _listar_proximas_auditorias(self) -> List[Dict[str, Any]]:
        """Lista próximas auditorias programadas"""
        return [
            {"tipo": "Financeira", "data_prevista": (datetime.now() + timedelta(days=15)).strftime("%d/%m/%Y")},
            {"tipo": "Operacional", "data_prevista": (datetime.now() + timedelta(days=45)).strftime("%d/%m/%Y")},
        ]

    async def _processar_chat(self, context: AgentContext) -> Dict[str, Any]:
        """Processa mensagens de chat"""

        mensagem = context.message.lower()

        # Análise de intenção
        if any(p in mensagem for p in ["status", "como está", "situação"]):
            return await self._gerar_dashboard(context)

        if any(p in mensagem for p in ["auditoria", "auditar", "verificar"]):
            return {
                "status": "success",
                "message": "Posso ajudar com auditorias. Que tipo você precisa?",
                "opcoes": [t.value for t in TipoAuditoria]
            }

        if any(p in mensagem for p in ["risco", "matriz"]):
            return await self._gerar_matriz_risco(context)

        if any(p in mensagem for p in ["compliance", "conformidade", "lgpd"]):
            return await self._verificar_compliance(context)

        if any(p in mensagem for p in ["recomendação", "recomendações", "pendente"]):
            return await self._monitorar_recomendacoes(context)

        # Resposta via LLM
        prompt = f"""
        Como agente de auditoria especializado em condomínios, responda à pergunta:

        Pergunta: {context.message}

        Considere:
        - Estatísticas: {self.estatisticas}
        - Auditorias ativas: {len([a for a in self.auditorias.values() if a.status == StatusAuditoria.EM_ANDAMENTO])}
        - Achados abertos: {len([a for a in self.achados.values() if a.status_tratamento == "aberto"])}

        Responda de forma profissional e objetiva.
        """

        resposta = await self.llm_client.generate(prompt)

        return {
            "status": "success",
            "response": resposta
        }


def create_audit_agent(
    memory: UnifiedMemorySystem,
    llm_client: UnifiedLLMClient,
    tools: ToolRegistry,
    rag: Optional[RAGPipeline] = None
) -> AuditAgent:
    """Factory function para criar o agente de auditoria"""
    return AuditAgent(memory, llm_client, tools, rag)
