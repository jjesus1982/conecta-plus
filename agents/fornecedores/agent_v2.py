"""
Agente de Fornecedores v2 - Conecta Plus
Gestor de compras - Cotações, contratos, avaliações, pagamentos
Nível 7: Transcendente - Antecipa necessidades e otimiza relacionamentos
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import hashlib

from agents.core.base_agent import BaseAgent, AgentCapability, AgentContext
from agents.core.memory_store import UnifiedMemorySystem
from agents.core.llm_client import UnifiedLLMClient
from agents.core.tools import ToolRegistry
from agents.core.rag_system import RAGPipeline


class CategoriaFornecedor(Enum):
    """Categorias de fornecedores"""
    MANUTENCAO = "manutencao"
    LIMPEZA = "limpeza"
    SEGURANCA = "seguranca"
    JARDINAGEM = "jardinagem"
    ELEVADORES = "elevadores"
    BOMBAS = "bombas"
    ELETRICA = "eletrica"
    HIDRAULICA = "hidraulica"
    PINTURA = "pintura"
    CONSTRUCAO = "construcao"
    IMPERMEABILIZACAO = "impermeabilizacao"
    DEDETIZACAO = "dedetizacao"
    PISCINA = "piscina"
    GAS = "gas"
    PORTOES = "portoes"
    INTERFONE = "interfone"
    CFTV = "cftv"
    INFORMATICA = "informatica"
    JURIDICO = "juridico"
    CONTABIL = "contabil"
    ADMINISTRACAO = "administracao"
    MATERIAIS = "materiais"
    EQUIPAMENTOS = "equipamentos"
    OUTROS = "outros"


class StatusFornecedor(Enum):
    """Status do fornecedor"""
    ATIVO = "ativo"
    INATIVO = "inativo"
    BLOQUEADO = "bloqueado"
    EM_AVALIACAO = "em_avaliacao"
    HOMOLOGADO = "homologado"
    SUSPENSO = "suspenso"


class StatusCotacao(Enum):
    """Status da cotação"""
    RASCUNHO = "rascunho"
    ENVIADA = "enviada"
    EM_ANALISE = "em_analise"
    APROVADA = "aprovada"
    RECUSADA = "recusada"
    VENCIDA = "vencida"
    CONTRATADA = "contratada"


class StatusContrato(Enum):
    """Status do contrato"""
    RASCUNHO = "rascunho"
    EM_NEGOCIACAO = "em_negociacao"
    AGUARDANDO_ASSINATURA = "aguardando_assinatura"
    ATIVO = "ativo"
    SUSPENSO = "suspenso"
    ENCERRADO = "encerrado"
    RENOVADO = "renovado"
    CANCELADO = "cancelado"


class StatusPedido(Enum):
    """Status do pedido de compra"""
    RASCUNHO = "rascunho"
    AGUARDANDO_APROVACAO = "aguardando_aprovacao"
    APROVADO = "aprovado"
    ENVIADO_FORNECEDOR = "enviado_fornecedor"
    CONFIRMADO = "confirmado"
    EM_PRODUCAO = "em_producao"
    ENVIADO = "enviado"
    ENTREGUE = "entregue"
    CONFERIDO = "conferido"
    FINALIZADO = "finalizado"
    CANCELADO = "cancelado"
    DEVOLVIDO = "devolvido"


class FormaPagamento(Enum):
    """Formas de pagamento"""
    BOLETO = "boleto"
    PIX = "pix"
    TRANSFERENCIA = "transferencia"
    CARTAO = "cartao"
    DEBITO_AUTOMATICO = "debito_automatico"
    CHEQUE = "cheque"


@dataclass
class Fornecedor:
    """Cadastro de fornecedor"""
    fornecedor_id: str
    razao_social: str
    nome_fantasia: str
    cnpj: str
    inscricao_estadual: Optional[str]
    inscricao_municipal: Optional[str]
    categoria: CategoriaFornecedor
    subcategorias: List[str]
    status: StatusFornecedor
    contato_principal: Dict[str, str]  # nome, telefone, email, cargo
    contatos_adicionais: List[Dict[str, str]]
    endereco: Dict[str, str]
    dados_bancarios: Dict[str, str]
    forma_pagamento_preferida: FormaPagamento
    prazo_pagamento_dias: int
    documentos: List[Dict[str, Any]]  # tipo, url, validade
    certificacoes: List[Dict[str, Any]]
    seguros: List[Dict[str, Any]]
    rating: float  # 0-5
    historico_avaliacoes: List[Dict[str, Any]]
    volume_contratado: float
    data_cadastro: datetime = field(default_factory=datetime.now)
    ultima_contratacao: Optional[datetime] = None
    observacoes: Optional[str] = None
    tags: List[str] = field(default_factory=list)


@dataclass
class Cotacao:
    """Cotação de produtos/serviços"""
    cotacao_id: str
    titulo: str
    descricao: str
    categoria: CategoriaFornecedor
    itens: List[Dict[str, Any]]  # descricao, quantidade, unidade, especificacao
    fornecedores_convidados: List[str]
    propostas: List[Dict[str, Any]]  # fornecedor_id, valor, prazo, condicoes
    criterios_avaliacao: Dict[str, float]  # preco, qualidade, prazo, etc. (peso)
    status: StatusCotacao
    solicitante: str
    aprovador: Optional[str]
    data_abertura: datetime = field(default_factory=datetime.now)
    data_limite: Optional[datetime] = None
    data_fechamento: Optional[datetime] = None
    proposta_vencedora: Optional[str] = None
    justificativa_escolha: Optional[str] = None
    valor_estimado: Optional[float] = None
    urgente: bool = False


@dataclass
class Contrato:
    """Contrato com fornecedor"""
    contrato_id: str
    fornecedor_id: str
    numero: str
    tipo: str  # prestacao_servicos, fornecimento, locacao
    objeto: str
    categoria: CategoriaFornecedor
    status: StatusContrato
    valor_mensal: Optional[float]
    valor_total: Optional[float]
    forma_pagamento: FormaPagamento
    dia_vencimento: int
    data_inicio: datetime
    data_fim: datetime
    renovacao_automatica: bool
    prazo_aviso_rescisao_dias: int
    clausulas_especiais: List[str]
    sla: Dict[str, Any]  # indicadores, metas, penalidades
    garantia: Optional[Dict[str, Any]]
    seguro: Optional[Dict[str, Any]]
    anexos: List[Dict[str, Any]]
    aditivos: List[Dict[str, Any]]
    historico_reajustes: List[Dict[str, Any]]
    responsavel_interno: str
    data_criacao: datetime = field(default_factory=datetime.now)
    observacoes: Optional[str] = None


@dataclass
class PedidoCompra:
    """Pedido de compra"""
    pedido_id: str
    fornecedor_id: str
    contrato_id: Optional[str]
    numero: str
    itens: List[Dict[str, Any]]  # descricao, quantidade, unidade, valor_unitario
    valor_total: float
    status: StatusPedido
    solicitante: str
    aprovador: Optional[str]
    centro_custo: str
    data_criacao: datetime = field(default_factory=datetime.now)
    data_aprovacao: Optional[datetime] = None
    data_entrega_prevista: Optional[datetime] = None
    data_entrega_real: Optional[datetime] = None
    endereco_entrega: Dict[str, str] = field(default_factory=dict)
    condicoes_pagamento: str = ""
    observacoes: Optional[str] = None
    nota_fiscal: Optional[Dict[str, Any]] = None
    conferencia: Optional[Dict[str, Any]] = None


@dataclass
class AvaliacaoFornecedor:
    """Avaliação de fornecedor"""
    avaliacao_id: str
    fornecedor_id: str
    contrato_id: Optional[str]
    pedido_id: Optional[str]
    periodo: Tuple[datetime, datetime]
    avaliador: str
    criterios: Dict[str, float]  # criterio: nota (0-5)
    nota_geral: float
    pontos_fortes: List[str]
    pontos_melhorar: List[str]
    recomendacoes: List[str]
    incidentes: List[Dict[str, Any]]
    cumprimento_sla: float  # percentual
    data_avaliacao: datetime = field(default_factory=datetime.now)
    observacoes: Optional[str] = None


@dataclass
class Pagamento:
    """Pagamento a fornecedor"""
    pagamento_id: str
    fornecedor_id: str
    pedido_id: Optional[str]
    contrato_id: Optional[str]
    nota_fiscal: str
    valor: float
    data_vencimento: datetime
    data_pagamento: Optional[datetime]
    status: str  # pendente, agendado, pago, cancelado
    forma_pagamento: FormaPagamento
    comprovante: Optional[str]
    observacoes: Optional[str] = None


class SupplierAgent(BaseAgent):
    """
    Agente de Fornecedores - Nível 7 Transcendente

    Capacidades:
    - Cadastro e homologação de fornecedores
    - Gestão de cotações e comparação de propostas
    - Gestão de contratos e aditivos
    - Pedidos de compra e acompanhamento
    - Avaliação de desempenho de fornecedores
    - Gestão de pagamentos
    - Análise de gastos e otimização
    - Alertas de vencimento de contratos/documentos
    - Ranking e recomendação de fornecedores
    """

    def __init__(
        self,
        memory: UnifiedMemorySystem,
        llm_client: UnifiedLLMClient,
        tools: ToolRegistry,
        rag: Optional[RAGPipeline] = None
    ):
        super().__init__(
            agent_id="supplier-agent",
            name="Agente de Fornecedores",
            capabilities=[
                AgentCapability.PROCUREMENT,
                AgentCapability.CONTRACT_MANAGEMENT,
                AgentCapability.VENDOR_MANAGEMENT,
                AgentCapability.FINANCIAL,
                AgentCapability.REPORTING
            ],
            memory=memory,
            llm_client=llm_client,
            tools=tools
        )

        self.rag = rag

        # Armazenamento em memória
        self.fornecedores: Dict[str, Fornecedor] = {}
        self.cotacoes: Dict[str, Cotacao] = {}
        self.contratos: Dict[str, Contrato] = {}
        self.pedidos: Dict[str, PedidoCompra] = {}
        self.avaliacoes: Dict[str, AvaliacaoFornecedor] = {}
        self.pagamentos: Dict[str, Pagamento] = {}

        # Critérios de avaliação padrão
        self.criterios_avaliacao = {
            "qualidade": 0.25,
            "preco": 0.25,
            "prazo_entrega": 0.15,
            "atendimento": 0.15,
            "documentacao": 0.10,
            "flexibilidade": 0.10
        }

        # Requisitos de homologação
        self.requisitos_homologacao = {
            "documentos_obrigatorios": [
                "contrato_social",
                "cnpj",
                "certidao_negativa_federal",
                "certidao_negativa_estadual",
                "certidao_negativa_municipal",
                "certidao_fgts",
                "certidao_trabalhista"
            ],
            "validade_minima_dias": 30,
            "rating_minimo": 3.0
        }

        # Limites de aprovação
        self.limites_aprovacao = {
            "sindico": 50000.0,
            "subsindico": 20000.0,
            "administradora": 10000.0,
            "zelador": 1000.0,
            "assembleia": float("inf")
        }

        # Estatísticas
        self.estatisticas = {
            "fornecedores_ativos": 0,
            "contratos_ativos": 0,
            "cotacoes_realizadas": 0,
            "economia_gerada": 0.0,
            "volume_contratado_ano": 0.0
        }

    async def process(self, context: AgentContext) -> Dict[str, Any]:
        """Processa requisições de gestão de fornecedores"""

        intent = context.metadata.get("intent", "")

        handlers = {
            # Fornecedores
            "cadastrar_fornecedor": self._cadastrar_fornecedor,
            "atualizar_fornecedor": self._atualizar_fornecedor,
            "homologar_fornecedor": self._homologar_fornecedor,
            "buscar_fornecedor": self._buscar_fornecedor,
            "listar_fornecedores": self._listar_fornecedores,
            "avaliar_fornecedor": self._avaliar_fornecedor,
            "ranking_fornecedores": self._ranking_fornecedores,

            # Cotações
            "criar_cotacao": self._criar_cotacao,
            "registrar_proposta": self._registrar_proposta,
            "analisar_propostas": self._analisar_propostas,
            "aprovar_cotacao": self._aprovar_cotacao,

            # Contratos
            "criar_contrato": self._criar_contrato,
            "renovar_contrato": self._renovar_contrato,
            "criar_aditivo": self._criar_aditivo,
            "encerrar_contrato": self._encerrar_contrato,
            "verificar_vencimentos": self._verificar_vencimentos,

            # Pedidos
            "criar_pedido": self._criar_pedido,
            "aprovar_pedido": self._aprovar_pedido,
            "receber_pedido": self._receber_pedido,
            "conferir_pedido": self._conferir_pedido,

            # Pagamentos
            "registrar_pagamento": self._registrar_pagamento,
            "consultar_pagamentos": self._consultar_pagamentos,
            "gerar_previsao_pagamentos": self._gerar_previsao_pagamentos,

            # Análises
            "analisar_gastos": self._analisar_gastos,
            "recomendar_fornecedor": self._recomendar_fornecedor,
            "monitorar_sla": self._monitorar_sla,

            # Dashboard e Chat
            "dashboard": self._gerar_dashboard,
            "chat": self._processar_chat,
        }

        handler = handlers.get(intent, self._processar_chat)
        return await handler(context)

    async def _cadastrar_fornecedor(self, context: AgentContext) -> Dict[str, Any]:
        """Cadastra novo fornecedor"""

        dados = context.metadata.get("dados", {})

        # Valida CNPJ
        cnpj = dados.get("cnpj", "").replace(".", "").replace("/", "").replace("-", "")
        if not self._validar_cnpj(cnpj):
            return {"status": "error", "message": "CNPJ inválido"}

        # Verifica se já existe
        for f in self.fornecedores.values():
            if f.cnpj == cnpj:
                return {"status": "error", "message": "Fornecedor já cadastrado", "fornecedor_id": f.fornecedor_id}

        fornecedor_id = f"FORN-{datetime.now().strftime('%Y%m%d')}-{len(self.fornecedores) + 1:04d}"

        fornecedor = Fornecedor(
            fornecedor_id=fornecedor_id,
            razao_social=dados.get("razao_social", ""),
            nome_fantasia=dados.get("nome_fantasia", ""),
            cnpj=cnpj,
            inscricao_estadual=dados.get("inscricao_estadual"),
            inscricao_municipal=dados.get("inscricao_municipal"),
            categoria=CategoriaFornecedor(dados.get("categoria", "outros")),
            subcategorias=dados.get("subcategorias", []),
            status=StatusFornecedor.EM_AVALIACAO,
            contato_principal=dados.get("contato_principal", {}),
            contatos_adicionais=dados.get("contatos_adicionais", []),
            endereco=dados.get("endereco", {}),
            dados_bancarios=dados.get("dados_bancarios", {}),
            forma_pagamento_preferida=FormaPagamento(dados.get("forma_pagamento", "boleto")),
            prazo_pagamento_dias=dados.get("prazo_pagamento", 30),
            documentos=dados.get("documentos", []),
            certificacoes=dados.get("certificacoes", []),
            seguros=dados.get("seguros", []),
            rating=0.0,
            historico_avaliacoes=[],
            volume_contratado=0.0,
            observacoes=dados.get("observacoes"),
            tags=dados.get("tags", [])
        )

        self.fornecedores[fornecedor_id] = fornecedor

        # Salva na memória
        await self.memory.store_episodic({
            "event": "fornecedor_cadastrado",
            "fornecedor_id": fornecedor_id,
            "razao_social": fornecedor.razao_social,
            "categoria": fornecedor.categoria.value,
            "timestamp": datetime.now().isoformat()
        })

        return {
            "status": "success",
            "message": f"Fornecedor cadastrado: {fornecedor_id}",
            "fornecedor": {
                "id": fornecedor_id,
                "razao_social": fornecedor.razao_social,
                "nome_fantasia": fornecedor.nome_fantasia,
                "categoria": fornecedor.categoria.value,
                "status": fornecedor.status.value
            },
            "pendencias": await self._verificar_pendencias_homologacao(fornecedor_id)
        }

    def _validar_cnpj(self, cnpj: str) -> bool:
        """Valida CNPJ"""
        if len(cnpj) != 14:
            return False

        # Validação simplificada
        if cnpj == cnpj[0] * 14:
            return False

        return True

    async def _verificar_pendencias_homologacao(self, fornecedor_id: str) -> List[str]:
        """Verifica pendências para homologação"""

        if fornecedor_id not in self.fornecedores:
            return []

        fornecedor = self.fornecedores[fornecedor_id]
        pendencias = []

        # Verifica documentos obrigatórios
        docs_presentes = [d.get("tipo") for d in fornecedor.documentos]
        for doc in self.requisitos_homologacao["documentos_obrigatorios"]:
            if doc not in docs_presentes:
                pendencias.append(f"Documento faltando: {doc}")
            else:
                # Verifica validade
                for d in fornecedor.documentos:
                    if d.get("tipo") == doc:
                        validade = d.get("validade")
                        if validade:
                            val_date = datetime.fromisoformat(validade)
                            if val_date < datetime.now() + timedelta(days=self.requisitos_homologacao["validade_minima_dias"]):
                                pendencias.append(f"Documento vencendo: {doc}")

        # Verifica dados bancários
        if not fornecedor.dados_bancarios:
            pendencias.append("Dados bancários não informados")

        # Verifica contato
        if not fornecedor.contato_principal:
            pendencias.append("Contato principal não informado")

        return pendencias

    async def _homologar_fornecedor(self, context: AgentContext) -> Dict[str, Any]:
        """Homologa fornecedor"""

        dados = context.metadata.get("dados", {})
        fornecedor_id = dados.get("fornecedor_id")

        if fornecedor_id not in self.fornecedores:
            return {"status": "error", "message": "Fornecedor não encontrado"}

        fornecedor = self.fornecedores[fornecedor_id]

        # Verifica pendências
        pendencias = await self._verificar_pendencias_homologacao(fornecedor_id)

        if pendencias and not dados.get("forcar", False):
            return {
                "status": "error",
                "message": "Fornecedor possui pendências",
                "pendencias": pendencias
            }

        # Homologa
        fornecedor.status = StatusFornecedor.HOMOLOGADO
        self.estatisticas["fornecedores_ativos"] += 1

        # Notifica
        await self.send_message(
            "notification-agent",
            {
                "tipo": "fornecedor_homologado",
                "fornecedor_id": fornecedor_id,
                "razao_social": fornecedor.razao_social
            }
        )

        return {
            "status": "success",
            "message": f"Fornecedor {fornecedor_id} homologado",
            "fornecedor": {
                "id": fornecedor_id,
                "razao_social": fornecedor.razao_social,
                "status": fornecedor.status.value
            }
        }

    async def _atualizar_fornecedor(self, context: AgentContext) -> Dict[str, Any]:
        """Atualiza dados do fornecedor"""

        dados = context.metadata.get("dados", {})
        fornecedor_id = dados.get("fornecedor_id")

        if fornecedor_id not in self.fornecedores:
            return {"status": "error", "message": "Fornecedor não encontrado"}

        fornecedor = self.fornecedores[fornecedor_id]

        # Atualiza campos permitidos
        campos_atualizaveis = [
            "nome_fantasia", "contato_principal", "contatos_adicionais",
            "endereco", "dados_bancarios", "forma_pagamento_preferida",
            "prazo_pagamento_dias", "documentos", "certificacoes", "seguros",
            "observacoes", "tags"
        ]

        for campo in campos_atualizaveis:
            if campo in dados:
                setattr(fornecedor, campo, dados[campo])

        return {
            "status": "success",
            "message": f"Fornecedor {fornecedor_id} atualizado"
        }

    async def _buscar_fornecedor(self, context: AgentContext) -> Dict[str, Any]:
        """Busca fornecedor"""

        dados = context.metadata.get("dados", {})
        termo = dados.get("termo", "").lower()

        resultados = []

        for f in self.fornecedores.values():
            if (termo in f.razao_social.lower() or
                termo in f.nome_fantasia.lower() or
                termo in f.cnpj or
                termo in f.categoria.value):

                resultados.append({
                    "id": f.fornecedor_id,
                    "razao_social": f.razao_social,
                    "nome_fantasia": f.nome_fantasia,
                    "categoria": f.categoria.value,
                    "status": f.status.value,
                    "rating": f.rating
                })

        return {
            "status": "success",
            "resultados": resultados,
            "total": len(resultados)
        }

    async def _listar_fornecedores(self, context: AgentContext) -> Dict[str, Any]:
        """Lista fornecedores"""

        dados = context.metadata.get("dados", {})
        categoria = dados.get("categoria")
        status = dados.get("status")
        apenas_homologados = dados.get("apenas_homologados", False)

        fornecedores_filtrados = []

        for f in self.fornecedores.values():
            if categoria and f.categoria.value != categoria:
                continue
            if status and f.status.value != status:
                continue
            if apenas_homologados and f.status != StatusFornecedor.HOMOLOGADO:
                continue

            fornecedores_filtrados.append({
                "id": f.fornecedor_id,
                "razao_social": f.razao_social,
                "nome_fantasia": f.nome_fantasia,
                "categoria": f.categoria.value,
                "status": f.status.value,
                "rating": f.rating,
                "volume_contratado": f.volume_contratado
            })

        # Ordena por rating
        fornecedores_filtrados.sort(key=lambda x: x["rating"], reverse=True)

        return {
            "status": "success",
            "fornecedores": fornecedores_filtrados,
            "total": len(fornecedores_filtrados)
        }

    async def _avaliar_fornecedor(self, context: AgentContext) -> Dict[str, Any]:
        """Avalia desempenho do fornecedor"""

        dados = context.metadata.get("dados", {})
        fornecedor_id = dados.get("fornecedor_id")

        if fornecedor_id not in self.fornecedores:
            return {"status": "error", "message": "Fornecedor não encontrado"}

        fornecedor = self.fornecedores[fornecedor_id]

        avaliacao_id = f"AVAL-{datetime.now().strftime('%Y%m%d')}-{len(self.avaliacoes) + 1:04d}"

        criterios = dados.get("criterios", {})
        notas = []

        for criterio, peso in self.criterios_avaliacao.items():
            nota = criterios.get(criterio, 3.0)  # Nota padrão 3
            notas.append(nota * peso)

        nota_geral = sum(notas)

        avaliacao = AvaliacaoFornecedor(
            avaliacao_id=avaliacao_id,
            fornecedor_id=fornecedor_id,
            contrato_id=dados.get("contrato_id"),
            pedido_id=dados.get("pedido_id"),
            periodo=(
                datetime.fromisoformat(dados.get("periodo_inicio", datetime.now().isoformat())),
                datetime.fromisoformat(dados.get("periodo_fim", datetime.now().isoformat()))
            ),
            avaliador=context.user_id,
            criterios=criterios,
            nota_geral=nota_geral,
            pontos_fortes=dados.get("pontos_fortes", []),
            pontos_melhorar=dados.get("pontos_melhorar", []),
            recomendacoes=dados.get("recomendacoes", []),
            incidentes=dados.get("incidentes", []),
            cumprimento_sla=dados.get("cumprimento_sla", 100.0),
            observacoes=dados.get("observacoes")
        )

        self.avaliacoes[avaliacao_id] = avaliacao

        # Atualiza rating do fornecedor
        fornecedor.historico_avaliacoes.append({
            "avaliacao_id": avaliacao_id,
            "nota": nota_geral,
            "data": datetime.now().isoformat()
        })

        # Recalcula média
        notas_historico = [a["nota"] for a in fornecedor.historico_avaliacoes]
        fornecedor.rating = sum(notas_historico) / len(notas_historico)

        return {
            "status": "success",
            "message": f"Avaliação {avaliacao_id} registrada",
            "avaliacao": {
                "id": avaliacao_id,
                "nota_geral": nota_geral,
                "criterios": criterios
            },
            "fornecedor": {
                "id": fornecedor_id,
                "novo_rating": fornecedor.rating
            }
        }

    async def _ranking_fornecedores(self, context: AgentContext) -> Dict[str, Any]:
        """Gera ranking de fornecedores"""

        dados = context.metadata.get("dados", {})
        categoria = dados.get("categoria")
        top_n = dados.get("top", 10)

        fornecedores_ranking = []

        for f in self.fornecedores.values():
            if f.status != StatusFornecedor.HOMOLOGADO:
                continue
            if categoria and f.categoria.value != categoria:
                continue

            # Calcula score composto
            score = f.rating * 0.5  # 50% rating

            # Adiciona fator de volume
            if f.volume_contratado > 0:
                score += min(f.volume_contratado / 100000, 1.0) * 0.2  # 20% volume

            # Adiciona fator de documentação
            docs_em_dia = len([d for d in f.documentos if self._documento_valido(d)])
            total_docs = len(self.requisitos_homologacao["documentos_obrigatorios"])
            score += (docs_em_dia / max(total_docs, 1)) * 0.15  # 15% documentação

            # Adiciona fator de tempo de relacionamento
            dias_relacionamento = (datetime.now() - f.data_cadastro).days
            score += min(dias_relacionamento / 365, 1.0) * 0.15  # 15% tempo

            fornecedores_ranking.append({
                "id": f.fornecedor_id,
                "razao_social": f.razao_social,
                "nome_fantasia": f.nome_fantasia,
                "categoria": f.categoria.value,
                "rating": f.rating,
                "score_composto": score,
                "volume_contratado": f.volume_contratado,
                "avaliacoes": len(f.historico_avaliacoes)
            })

        # Ordena por score
        fornecedores_ranking.sort(key=lambda x: x["score_composto"], reverse=True)

        return {
            "status": "success",
            "ranking": fornecedores_ranking[:top_n],
            "categoria": categoria,
            "total_avaliados": len(fornecedores_ranking)
        }

    def _documento_valido(self, documento: Dict[str, Any]) -> bool:
        """Verifica se documento está válido"""
        validade = documento.get("validade")
        if not validade:
            return True  # Sem validade = sempre válido
        return datetime.fromisoformat(validade) > datetime.now()

    async def _criar_cotacao(self, context: AgentContext) -> Dict[str, Any]:
        """Cria nova cotação"""

        dados = context.metadata.get("dados", {})

        cotacao_id = f"COT-{datetime.now().strftime('%Y%m%d')}-{len(self.cotacoes) + 1:04d}"

        # Busca fornecedores para convidar se não informados
        fornecedores_convidados = dados.get("fornecedores", [])
        if not fornecedores_convidados:
            categoria = CategoriaFornecedor(dados.get("categoria", "outros"))
            fornecedores_convidados = await self._buscar_fornecedores_categoria(categoria)

        cotacao = Cotacao(
            cotacao_id=cotacao_id,
            titulo=dados.get("titulo", ""),
            descricao=dados.get("descricao", ""),
            categoria=CategoriaFornecedor(dados.get("categoria", "outros")),
            itens=dados.get("itens", []),
            fornecedores_convidados=fornecedores_convidados,
            propostas=[],
            criterios_avaliacao=dados.get("criterios", self.criterios_avaliacao),
            status=StatusCotacao.RASCUNHO,
            solicitante=context.user_id,
            data_limite=datetime.now() + timedelta(days=dados.get("prazo_dias", 7)),
            valor_estimado=dados.get("valor_estimado"),
            urgente=dados.get("urgente", False)
        )

        self.cotacoes[cotacao_id] = cotacao
        self.estatisticas["cotacoes_realizadas"] += 1

        return {
            "status": "success",
            "message": f"Cotação {cotacao_id} criada",
            "cotacao": {
                "id": cotacao_id,
                "titulo": cotacao.titulo,
                "categoria": cotacao.categoria.value,
                "itens": len(cotacao.itens),
                "fornecedores_convidados": len(fornecedores_convidados),
                "data_limite": cotacao.data_limite.strftime("%d/%m/%Y")
            }
        }

    async def _buscar_fornecedores_categoria(self, categoria: CategoriaFornecedor) -> List[str]:
        """Busca fornecedores homologados por categoria"""

        fornecedores = []
        for f in self.fornecedores.values():
            if f.status == StatusFornecedor.HOMOLOGADO and f.categoria == categoria:
                fornecedores.append(f.fornecedor_id)

        return fornecedores[:5]  # Máximo 5 fornecedores

    async def _registrar_proposta(self, context: AgentContext) -> Dict[str, Any]:
        """Registra proposta de fornecedor"""

        dados = context.metadata.get("dados", {})
        cotacao_id = dados.get("cotacao_id")

        if cotacao_id not in self.cotacoes:
            return {"status": "error", "message": "Cotação não encontrada"}

        cotacao = self.cotacoes[cotacao_id]

        if cotacao.status not in [StatusCotacao.RASCUNHO, StatusCotacao.ENVIADA]:
            return {"status": "error", "message": "Cotação não aceita mais propostas"}

        proposta = {
            "fornecedor_id": dados.get("fornecedor_id"),
            "itens": dados.get("itens", []),  # descricao, quantidade, valor_unitario
            "valor_total": dados.get("valor_total"),
            "prazo_entrega_dias": dados.get("prazo_entrega"),
            "validade_proposta_dias": dados.get("validade", 30),
            "condicoes_pagamento": dados.get("condicoes_pagamento"),
            "observacoes": dados.get("observacoes"),
            "data_proposta": datetime.now().isoformat()
        }

        cotacao.propostas.append(proposta)

        if cotacao.status == StatusCotacao.RASCUNHO:
            cotacao.status = StatusCotacao.ENVIADA

        return {
            "status": "success",
            "message": "Proposta registrada",
            "cotacao": {
                "id": cotacao_id,
                "total_propostas": len(cotacao.propostas)
            }
        }

    async def _analisar_propostas(self, context: AgentContext) -> Dict[str, Any]:
        """Analisa propostas de uma cotação"""

        dados = context.metadata.get("dados", {})
        cotacao_id = dados.get("cotacao_id")

        if cotacao_id not in self.cotacoes:
            return {"status": "error", "message": "Cotação não encontrada"}

        cotacao = self.cotacoes[cotacao_id]

        if len(cotacao.propostas) == 0:
            return {"status": "error", "message": "Nenhuma proposta recebida"}

        analise = []
        menor_preco = min(p["valor_total"] for p in cotacao.propostas)

        for proposta in cotacao.propostas:
            fornecedor = self.fornecedores.get(proposta["fornecedor_id"])

            # Calcula score
            score = 0

            # Componente preço (inverso - menor é melhor)
            score_preco = (menor_preco / proposta["valor_total"]) * cotacao.criterios_avaliacao.get("preco", 0.25)
            score += score_preco

            # Componente qualidade (rating do fornecedor)
            if fornecedor:
                score_qualidade = (fornecedor.rating / 5) * cotacao.criterios_avaliacao.get("qualidade", 0.25)
                score += score_qualidade

            # Componente prazo (inverso - menor é melhor)
            prazo_min = min(p.get("prazo_entrega_dias", 30) for p in cotacao.propostas)
            prazo_atual = proposta.get("prazo_entrega_dias", 30)
            score_prazo = (prazo_min / prazo_atual) * cotacao.criterios_avaliacao.get("prazo_entrega", 0.15)
            score += score_prazo

            analise.append({
                "fornecedor_id": proposta["fornecedor_id"],
                "fornecedor_nome": fornecedor.nome_fantasia if fornecedor else "N/A",
                "valor_total": proposta["valor_total"],
                "prazo_entrega": proposta.get("prazo_entrega_dias"),
                "rating_fornecedor": fornecedor.rating if fornecedor else 0,
                "score_final": score,
                "componentes": {
                    "preco": score_preco,
                    "qualidade": score_qualidade if fornecedor else 0,
                    "prazo": score_prazo
                }
            })

        # Ordena por score
        analise.sort(key=lambda x: x["score_final"], reverse=True)

        # Identifica melhor proposta
        melhor = analise[0]
        economia = 0
        if cotacao.valor_estimado:
            economia = cotacao.valor_estimado - melhor["valor_total"]

        return {
            "status": "success",
            "cotacao_id": cotacao_id,
            "total_propostas": len(cotacao.propostas),
            "analise": analise,
            "recomendacao": {
                "fornecedor_id": melhor["fornecedor_id"],
                "fornecedor_nome": melhor["fornecedor_nome"],
                "valor": melhor["valor_total"],
                "score": melhor["score_final"],
                "economia_estimada": economia if economia > 0 else 0
            }
        }

    async def _aprovar_cotacao(self, context: AgentContext) -> Dict[str, Any]:
        """Aprova cotação e seleciona vencedor"""

        dados = context.metadata.get("dados", {})
        cotacao_id = dados.get("cotacao_id")
        fornecedor_vencedor = dados.get("fornecedor_id")

        if cotacao_id not in self.cotacoes:
            return {"status": "error", "message": "Cotação não encontrada"}

        cotacao = self.cotacoes[cotacao_id]

        # Verifica se fornecedor está nas propostas
        proposta_vencedora = None
        for proposta in cotacao.propostas:
            if proposta["fornecedor_id"] == fornecedor_vencedor:
                proposta_vencedora = proposta
                break

        if not proposta_vencedora:
            return {"status": "error", "message": "Fornecedor não participou desta cotação"}

        cotacao.status = StatusCotacao.APROVADA
        cotacao.proposta_vencedora = fornecedor_vencedor
        cotacao.aprovador = context.user_id
        cotacao.data_fechamento = datetime.now()
        cotacao.justificativa_escolha = dados.get("justificativa", "Melhor proposta conforme critérios")

        # Atualiza estatísticas
        if cotacao.valor_estimado and proposta_vencedora["valor_total"] < cotacao.valor_estimado:
            economia = cotacao.valor_estimado - proposta_vencedora["valor_total"]
            self.estatisticas["economia_gerada"] += economia

        return {
            "status": "success",
            "message": f"Cotação {cotacao_id} aprovada",
            "vencedor": {
                "fornecedor_id": fornecedor_vencedor,
                "valor": proposta_vencedora["valor_total"],
                "prazo": proposta_vencedora.get("prazo_entrega_dias")
            },
            "proximo_passo": "Criar contrato ou pedido de compra"
        }

    async def _criar_contrato(self, context: AgentContext) -> Dict[str, Any]:
        """Cria novo contrato"""

        dados = context.metadata.get("dados", {})
        fornecedor_id = dados.get("fornecedor_id")

        if fornecedor_id not in self.fornecedores:
            return {"status": "error", "message": "Fornecedor não encontrado"}

        fornecedor = self.fornecedores[fornecedor_id]

        if fornecedor.status != StatusFornecedor.HOMOLOGADO:
            return {"status": "error", "message": "Fornecedor não está homologado"}

        contrato_id = f"CONT-{datetime.now().strftime('%Y%m%d')}-{len(self.contratos) + 1:04d}"
        numero = f"{datetime.now().year}/{len(self.contratos) + 1:04d}"

        contrato = Contrato(
            contrato_id=contrato_id,
            fornecedor_id=fornecedor_id,
            numero=numero,
            tipo=dados.get("tipo", "prestacao_servicos"),
            objeto=dados.get("objeto", ""),
            categoria=fornecedor.categoria,
            status=StatusContrato.RASCUNHO,
            valor_mensal=dados.get("valor_mensal"),
            valor_total=dados.get("valor_total"),
            forma_pagamento=FormaPagamento(dados.get("forma_pagamento", "boleto")),
            dia_vencimento=dados.get("dia_vencimento", 10),
            data_inicio=datetime.fromisoformat(dados.get("data_inicio", datetime.now().isoformat())),
            data_fim=datetime.fromisoformat(dados.get("data_fim", (datetime.now() + timedelta(days=365)).isoformat())),
            renovacao_automatica=dados.get("renovacao_automatica", False),
            prazo_aviso_rescisao_dias=dados.get("prazo_aviso_rescisao", 30),
            clausulas_especiais=dados.get("clausulas_especiais", []),
            sla=dados.get("sla", {}),
            garantia=dados.get("garantia"),
            seguro=dados.get("seguro"),
            anexos=dados.get("anexos", []),
            aditivos=[],
            historico_reajustes=[],
            responsavel_interno=dados.get("responsavel", context.user_id),
            observacoes=dados.get("observacoes")
        )

        self.contratos[contrato_id] = contrato
        self.estatisticas["contratos_ativos"] += 1

        return {
            "status": "success",
            "message": f"Contrato {contrato_id} criado",
            "contrato": {
                "id": contrato_id,
                "numero": numero,
                "fornecedor": fornecedor.nome_fantasia,
                "objeto": contrato.objeto,
                "valor_mensal": contrato.valor_mensal,
                "vigencia": f"{contrato.data_inicio.strftime('%d/%m/%Y')} a {contrato.data_fim.strftime('%d/%m/%Y')}",
                "status": contrato.status.value
            }
        }

    async def _renovar_contrato(self, context: AgentContext) -> Dict[str, Any]:
        """Renova contrato existente"""

        dados = context.metadata.get("dados", {})
        contrato_id = dados.get("contrato_id")

        if contrato_id not in self.contratos:
            return {"status": "error", "message": "Contrato não encontrado"}

        contrato = self.contratos[contrato_id]

        # Define novo período
        nova_data_inicio = contrato.data_fim + timedelta(days=1)
        nova_data_fim = nova_data_inicio + timedelta(days=dados.get("meses", 12) * 30)

        # Aplica reajuste se informado
        reajuste = dados.get("reajuste_percentual", 0)
        novo_valor = contrato.valor_mensal
        if novo_valor and reajuste:
            novo_valor = novo_valor * (1 + reajuste / 100)

        # Registra no histórico
        contrato.historico_reajustes.append({
            "data": datetime.now().isoformat(),
            "valor_anterior": contrato.valor_mensal,
            "valor_novo": novo_valor,
            "reajuste_percentual": reajuste,
            "indice": dados.get("indice", "IGPM")
        })

        # Atualiza contrato
        contrato.data_inicio = nova_data_inicio
        contrato.data_fim = nova_data_fim
        contrato.valor_mensal = novo_valor
        contrato.status = StatusContrato.RENOVADO

        return {
            "status": "success",
            "message": f"Contrato {contrato_id} renovado",
            "renovacao": {
                "nova_vigencia": f"{nova_data_inicio.strftime('%d/%m/%Y')} a {nova_data_fim.strftime('%d/%m/%Y')}",
                "novo_valor": novo_valor,
                "reajuste_aplicado": f"{reajuste}%"
            }
        }

    async def _criar_aditivo(self, context: AgentContext) -> Dict[str, Any]:
        """Cria aditivo contratual"""

        dados = context.metadata.get("dados", {})
        contrato_id = dados.get("contrato_id")

        if contrato_id not in self.contratos:
            return {"status": "error", "message": "Contrato não encontrado"}

        contrato = self.contratos[contrato_id]

        aditivo = {
            "numero": len(contrato.aditivos) + 1,
            "tipo": dados.get("tipo", "alteracao"),  # alteracao, prorrogacao, reajuste, supressao, acrescimo
            "objeto": dados.get("objeto", ""),
            "valor_anterior": contrato.valor_mensal,
            "valor_novo": dados.get("valor_novo"),
            "data_inicio": dados.get("data_inicio"),
            "data_fim": dados.get("data_fim"),
            "justificativa": dados.get("justificativa", ""),
            "clausulas_alteradas": dados.get("clausulas", []),
            "data_assinatura": datetime.now().isoformat(),
            "responsavel": context.user_id
        }

        contrato.aditivos.append(aditivo)

        # Aplica alterações
        if aditivo["valor_novo"]:
            contrato.valor_mensal = aditivo["valor_novo"]
        if aditivo["data_fim"]:
            contrato.data_fim = datetime.fromisoformat(aditivo["data_fim"])

        return {
            "status": "success",
            "message": f"Aditivo {aditivo['numero']} criado para contrato {contrato_id}",
            "aditivo": aditivo
        }

    async def _encerrar_contrato(self, context: AgentContext) -> Dict[str, Any]:
        """Encerra contrato"""

        dados = context.metadata.get("dados", {})
        contrato_id = dados.get("contrato_id")

        if contrato_id not in self.contratos:
            return {"status": "error", "message": "Contrato não encontrado"}

        contrato = self.contratos[contrato_id]

        motivo = dados.get("motivo", "encerramento_normal")
        data_encerramento = datetime.fromisoformat(dados.get("data_encerramento", datetime.now().isoformat()))

        contrato.status = StatusContrato.ENCERRADO
        contrato.observacoes = f"Encerrado em {data_encerramento.strftime('%d/%m/%Y')}. Motivo: {motivo}"

        self.estatisticas["contratos_ativos"] -= 1

        # Notifica
        await self.send_message(
            "notification-agent",
            {
                "tipo": "contrato_encerrado",
                "contrato_id": contrato_id,
                "fornecedor_id": contrato.fornecedor_id,
                "motivo": motivo
            }
        )

        return {
            "status": "success",
            "message": f"Contrato {contrato_id} encerrado",
            "data_encerramento": data_encerramento.strftime("%d/%m/%Y"),
            "motivo": motivo
        }

    async def _verificar_vencimentos(self, context: AgentContext) -> Dict[str, Any]:
        """Verifica vencimentos de contratos e documentos"""

        dados = context.metadata.get("dados", {})
        dias_antecedencia = dados.get("dias", 30)

        hoje = datetime.now()
        limite = hoje + timedelta(days=dias_antecedencia)

        vencimentos = {
            "contratos": [],
            "documentos": [],
            "certificacoes": [],
            "seguros": []
        }

        # Verifica contratos
        for contrato in self.contratos.values():
            if contrato.status == StatusContrato.ATIVO:
                if contrato.data_fim <= limite:
                    dias_restantes = (contrato.data_fim - hoje).days
                    fornecedor = self.fornecedores.get(contrato.fornecedor_id)

                    vencimentos["contratos"].append({
                        "contrato_id": contrato.contrato_id,
                        "numero": contrato.numero,
                        "fornecedor": fornecedor.nome_fantasia if fornecedor else "N/A",
                        "data_vencimento": contrato.data_fim.strftime("%d/%m/%Y"),
                        "dias_restantes": dias_restantes,
                        "renovacao_automatica": contrato.renovacao_automatica,
                        "valor_mensal": contrato.valor_mensal
                    })

        # Verifica documentos de fornecedores
        for fornecedor in self.fornecedores.values():
            if fornecedor.status != StatusFornecedor.HOMOLOGADO:
                continue

            for doc in fornecedor.documentos:
                if doc.get("validade"):
                    validade = datetime.fromisoformat(doc["validade"])
                    if validade <= limite:
                        dias_restantes = (validade - hoje).days
                        vencimentos["documentos"].append({
                            "fornecedor_id": fornecedor.fornecedor_id,
                            "fornecedor": fornecedor.nome_fantasia,
                            "tipo_documento": doc.get("tipo"),
                            "data_vencimento": validade.strftime("%d/%m/%Y"),
                            "dias_restantes": dias_restantes
                        })

            for cert in fornecedor.certificacoes:
                if cert.get("validade"):
                    validade = datetime.fromisoformat(cert["validade"])
                    if validade <= limite:
                        dias_restantes = (validade - hoje).days
                        vencimentos["certificacoes"].append({
                            "fornecedor_id": fornecedor.fornecedor_id,
                            "fornecedor": fornecedor.nome_fantasia,
                            "certificacao": cert.get("nome"),
                            "data_vencimento": validade.strftime("%d/%m/%Y"),
                            "dias_restantes": dias_restantes
                        })

            for seguro in fornecedor.seguros:
                if seguro.get("validade"):
                    validade = datetime.fromisoformat(seguro["validade"])
                    if validade <= limite:
                        dias_restantes = (validade - hoje).days
                        vencimentos["seguros"].append({
                            "fornecedor_id": fornecedor.fornecedor_id,
                            "fornecedor": fornecedor.nome_fantasia,
                            "seguro": seguro.get("tipo"),
                            "data_vencimento": validade.strftime("%d/%m/%Y"),
                            "dias_restantes": dias_restantes
                        })

        total_vencimentos = sum(len(v) for v in vencimentos.values())

        return {
            "status": "success",
            "periodo_verificado": f"Próximos {dias_antecedencia} dias",
            "vencimentos": vencimentos,
            "resumo": {
                "contratos": len(vencimentos["contratos"]),
                "documentos": len(vencimentos["documentos"]),
                "certificacoes": len(vencimentos["certificacoes"]),
                "seguros": len(vencimentos["seguros"]),
                "total": total_vencimentos
            }
        }

    async def _criar_pedido(self, context: AgentContext) -> Dict[str, Any]:
        """Cria pedido de compra"""

        dados = context.metadata.get("dados", {})
        fornecedor_id = dados.get("fornecedor_id")

        if fornecedor_id not in self.fornecedores:
            return {"status": "error", "message": "Fornecedor não encontrado"}

        pedido_id = f"PED-{datetime.now().strftime('%Y%m%d')}-{len(self.pedidos) + 1:04d}"
        numero = f"PC-{datetime.now().year}-{len(self.pedidos) + 1:04d}"

        itens = dados.get("itens", [])
        valor_total = sum(i.get("valor_unitario", 0) * i.get("quantidade", 1) for i in itens)

        # Determina aprovador necessário
        aprovador_necessario = self._determinar_aprovador(valor_total)

        pedido = PedidoCompra(
            pedido_id=pedido_id,
            fornecedor_id=fornecedor_id,
            contrato_id=dados.get("contrato_id"),
            numero=numero,
            itens=itens,
            valor_total=valor_total,
            status=StatusPedido.AGUARDANDO_APROVACAO,
            solicitante=context.user_id,
            centro_custo=dados.get("centro_custo", "geral"),
            data_entrega_prevista=datetime.fromisoformat(dados.get("data_entrega", (datetime.now() + timedelta(days=7)).isoformat())),
            endereco_entrega=dados.get("endereco_entrega", {}),
            condicoes_pagamento=dados.get("condicoes_pagamento", "30 dias"),
            observacoes=dados.get("observacoes")
        )

        self.pedidos[pedido_id] = pedido

        return {
            "status": "success",
            "message": f"Pedido {pedido_id} criado",
            "pedido": {
                "id": pedido_id,
                "numero": numero,
                "fornecedor_id": fornecedor_id,
                "valor_total": valor_total,
                "itens": len(itens),
                "status": pedido.status.value
            },
            "aprovacao": {
                "requerida": True,
                "aprovador_minimo": aprovador_necessario
            }
        }

    def _determinar_aprovador(self, valor: float) -> str:
        """Determina aprovador necessário baseado no valor"""
        for cargo, limite in sorted(self.limites_aprovacao.items(), key=lambda x: x[1]):
            if valor <= limite:
                return cargo
        return "assembleia"

    async def _aprovar_pedido(self, context: AgentContext) -> Dict[str, Any]:
        """Aprova pedido de compra"""

        dados = context.metadata.get("dados", {})
        pedido_id = dados.get("pedido_id")

        if pedido_id not in self.pedidos:
            return {"status": "error", "message": "Pedido não encontrado"}

        pedido = self.pedidos[pedido_id]

        if pedido.status != StatusPedido.AGUARDANDO_APROVACAO:
            return {"status": "error", "message": f"Pedido não está aguardando aprovação. Status: {pedido.status.value}"}

        pedido.status = StatusPedido.APROVADO
        pedido.aprovador = context.user_id
        pedido.data_aprovacao = datetime.now()

        # Atualiza volume do fornecedor
        fornecedor = self.fornecedores.get(pedido.fornecedor_id)
        if fornecedor:
            fornecedor.volume_contratado += pedido.valor_total
            fornecedor.ultima_contratacao = datetime.now()

        self.estatisticas["volume_contratado_ano"] += pedido.valor_total

        return {
            "status": "success",
            "message": f"Pedido {pedido_id} aprovado",
            "pedido": {
                "id": pedido_id,
                "status": pedido.status.value,
                "aprovador": pedido.aprovador,
                "data_aprovacao": pedido.data_aprovacao.strftime("%d/%m/%Y %H:%M")
            }
        }

    async def _receber_pedido(self, context: AgentContext) -> Dict[str, Any]:
        """Registra recebimento de pedido"""

        dados = context.metadata.get("dados", {})
        pedido_id = dados.get("pedido_id")

        if pedido_id not in self.pedidos:
            return {"status": "error", "message": "Pedido não encontrado"}

        pedido = self.pedidos[pedido_id]

        pedido.status = StatusPedido.ENTREGUE
        pedido.data_entrega_real = datetime.now()

        # Registra nota fiscal
        if dados.get("nota_fiscal"):
            pedido.nota_fiscal = {
                "numero": dados["nota_fiscal"].get("numero"),
                "serie": dados["nota_fiscal"].get("serie"),
                "valor": dados["nota_fiscal"].get("valor"),
                "data_emissao": dados["nota_fiscal"].get("data_emissao"),
                "chave_acesso": dados["nota_fiscal"].get("chave_acesso")
            }

        return {
            "status": "success",
            "message": f"Pedido {pedido_id} recebido",
            "data_recebimento": pedido.data_entrega_real.strftime("%d/%m/%Y %H:%M"),
            "proximo_passo": "Realizar conferência dos itens"
        }

    async def _conferir_pedido(self, context: AgentContext) -> Dict[str, Any]:
        """Confere itens do pedido"""

        dados = context.metadata.get("dados", {})
        pedido_id = dados.get("pedido_id")

        if pedido_id not in self.pedidos:
            return {"status": "error", "message": "Pedido não encontrado"}

        pedido = self.pedidos[pedido_id]

        conferencia = {
            "data": datetime.now().isoformat(),
            "conferente": context.user_id,
            "itens_conferidos": dados.get("itens_conferidos", []),
            "divergencias": dados.get("divergencias", []),
            "aprovado": dados.get("aprovado", True),
            "observacoes": dados.get("observacoes")
        }

        pedido.conferencia = conferencia

        if conferencia["aprovado"]:
            pedido.status = StatusPedido.CONFERIDO
        else:
            pedido.status = StatusPedido.DEVOLVIDO
            # Registra ocorrência com fornecedor
            await self._registrar_incidente_fornecedor(
                pedido.fornecedor_id,
                "divergencia_entrega",
                conferencia["divergencias"]
            )

        return {
            "status": "success",
            "message": f"Conferência do pedido {pedido_id} realizada",
            "resultado": "Aprovado" if conferencia["aprovado"] else "Reprovado",
            "divergencias": conferencia["divergencias"],
            "status_pedido": pedido.status.value
        }

    async def _registrar_incidente_fornecedor(
        self,
        fornecedor_id: str,
        tipo: str,
        detalhes: Any
    ):
        """Registra incidente com fornecedor"""
        if fornecedor_id in self.fornecedores:
            fornecedor = self.fornecedores[fornecedor_id]
            fornecedor.historico_avaliacoes.append({
                "tipo": "incidente",
                "incidente_tipo": tipo,
                "detalhes": detalhes,
                "data": datetime.now().isoformat()
            })

    async def _registrar_pagamento(self, context: AgentContext) -> Dict[str, Any]:
        """Registra pagamento a fornecedor"""

        dados = context.metadata.get("dados", {})

        pagamento_id = f"PAG-{datetime.now().strftime('%Y%m%d')}-{len(self.pagamentos) + 1:04d}"

        pagamento = Pagamento(
            pagamento_id=pagamento_id,
            fornecedor_id=dados.get("fornecedor_id"),
            pedido_id=dados.get("pedido_id"),
            contrato_id=dados.get("contrato_id"),
            nota_fiscal=dados.get("nota_fiscal", ""),
            valor=dados.get("valor", 0.0),
            data_vencimento=datetime.fromisoformat(dados.get("data_vencimento", datetime.now().isoformat())),
            data_pagamento=datetime.fromisoformat(dados.get("data_pagamento")) if dados.get("data_pagamento") else None,
            status=dados.get("status", "pendente"),
            forma_pagamento=FormaPagamento(dados.get("forma_pagamento", "boleto")),
            comprovante=dados.get("comprovante"),
            observacoes=dados.get("observacoes")
        )

        self.pagamentos[pagamento_id] = pagamento

        # Se pedido associado, atualiza status
        if pagamento.pedido_id and pagamento.pedido_id in self.pedidos:
            if pagamento.status == "pago":
                self.pedidos[pagamento.pedido_id].status = StatusPedido.FINALIZADO

        return {
            "status": "success",
            "message": f"Pagamento {pagamento_id} registrado",
            "pagamento": {
                "id": pagamento_id,
                "valor": pagamento.valor,
                "vencimento": pagamento.data_vencimento.strftime("%d/%m/%Y"),
                "status": pagamento.status
            }
        }

    async def _consultar_pagamentos(self, context: AgentContext) -> Dict[str, Any]:
        """Consulta pagamentos"""

        dados = context.metadata.get("dados", {})
        fornecedor_id = dados.get("fornecedor_id")
        status = dados.get("status")
        mes = dados.get("mes")
        ano = dados.get("ano", datetime.now().year)

        pagamentos_filtrados = []

        for pag in self.pagamentos.values():
            if fornecedor_id and pag.fornecedor_id != fornecedor_id:
                continue
            if status and pag.status != status:
                continue
            if mes and pag.data_vencimento.month != mes:
                continue
            if pag.data_vencimento.year != ano:
                continue

            pagamentos_filtrados.append({
                "id": pag.pagamento_id,
                "fornecedor_id": pag.fornecedor_id,
                "valor": pag.valor,
                "vencimento": pag.data_vencimento.strftime("%d/%m/%Y"),
                "pagamento": pag.data_pagamento.strftime("%d/%m/%Y") if pag.data_pagamento else None,
                "status": pag.status,
                "nota_fiscal": pag.nota_fiscal
            })

        # Totaliza
        total = sum(p["valor"] for p in pagamentos_filtrados)
        total_pendente = sum(p["valor"] for p in pagamentos_filtrados if p["status"] == "pendente")
        total_pago = sum(p["valor"] for p in pagamentos_filtrados if p["status"] == "pago")

        return {
            "status": "success",
            "pagamentos": pagamentos_filtrados,
            "resumo": {
                "total": len(pagamentos_filtrados),
                "valor_total": total,
                "valor_pendente": total_pendente,
                "valor_pago": total_pago
            }
        }

    async def _gerar_previsao_pagamentos(self, context: AgentContext) -> Dict[str, Any]:
        """Gera previsão de pagamentos"""

        dados = context.metadata.get("dados", {})
        meses = dados.get("meses", 3)

        hoje = datetime.now()
        previsao = {}

        for i in range(meses):
            mes = hoje + timedelta(days=30 * i)
            chave = mes.strftime("%Y-%m")
            previsao[chave] = {
                "contratos": 0.0,
                "pedidos": 0.0,
                "total": 0.0,
                "detalhes": []
            }

        # Calcula valores de contratos ativos
        for contrato in self.contratos.values():
            if contrato.status == StatusContrato.ATIVO and contrato.valor_mensal:
                for i in range(meses):
                    mes = hoje + timedelta(days=30 * i)
                    if contrato.data_inicio <= mes <= contrato.data_fim:
                        chave = mes.strftime("%Y-%m")
                        previsao[chave]["contratos"] += contrato.valor_mensal
                        previsao[chave]["detalhes"].append({
                            "tipo": "contrato",
                            "id": contrato.contrato_id,
                            "valor": contrato.valor_mensal
                        })

        # Calcula valores de pedidos pendentes
        for pedido in self.pedidos.values():
            if pedido.status in [StatusPedido.APROVADO, StatusPedido.ENVIADO_FORNECEDOR, StatusPedido.ENTREGUE]:
                if pedido.data_entrega_prevista:
                    chave = pedido.data_entrega_prevista.strftime("%Y-%m")
                    if chave in previsao:
                        previsao[chave]["pedidos"] += pedido.valor_total
                        previsao[chave]["detalhes"].append({
                            "tipo": "pedido",
                            "id": pedido.pedido_id,
                            "valor": pedido.valor_total
                        })

        # Calcula totais
        for chave in previsao:
            previsao[chave]["total"] = previsao[chave]["contratos"] + previsao[chave]["pedidos"]

        total_geral = sum(p["total"] for p in previsao.values())

        return {
            "status": "success",
            "previsao": previsao,
            "total_periodo": total_geral,
            "media_mensal": total_geral / meses
        }

    async def _analisar_gastos(self, context: AgentContext) -> Dict[str, Any]:
        """Analisa gastos com fornecedores"""

        dados = context.metadata.get("dados", {})
        periodo_meses = dados.get("meses", 12)

        hoje = datetime.now()
        inicio_periodo = hoje - timedelta(days=30 * periodo_meses)

        # Agrupa gastos por categoria
        gastos_categoria = {}
        gastos_fornecedor = {}

        for pag in self.pagamentos.values():
            if pag.status != "pago":
                continue
            if pag.data_pagamento and pag.data_pagamento < inicio_periodo:
                continue

            fornecedor = self.fornecedores.get(pag.fornecedor_id)
            if not fornecedor:
                continue

            # Por categoria
            cat = fornecedor.categoria.value
            gastos_categoria[cat] = gastos_categoria.get(cat, 0) + pag.valor

            # Por fornecedor
            gastos_fornecedor[pag.fornecedor_id] = gastos_fornecedor.get(pag.fornecedor_id, 0) + pag.valor

        # Calcula participação
        total = sum(gastos_categoria.values())

        analise_categoria = []
        for cat, valor in sorted(gastos_categoria.items(), key=lambda x: x[1], reverse=True):
            analise_categoria.append({
                "categoria": cat,
                "valor": valor,
                "percentual": (valor / total * 100) if total > 0 else 0
            })

        analise_fornecedor = []
        for forn_id, valor in sorted(gastos_fornecedor.items(), key=lambda x: x[1], reverse=True)[:10]:
            fornecedor = self.fornecedores.get(forn_id)
            analise_fornecedor.append({
                "fornecedor_id": forn_id,
                "nome": fornecedor.nome_fantasia if fornecedor else "N/A",
                "valor": valor,
                "percentual": (valor / total * 100) if total > 0 else 0
            })

        # Verifica concentração (risco)
        concentracao_alerta = [f for f in analise_fornecedor if f["percentual"] > 30]

        return {
            "status": "success",
            "periodo": f"Últimos {periodo_meses} meses",
            "total_gasto": total,
            "por_categoria": analise_categoria,
            "top_fornecedores": analise_fornecedor,
            "alertas": {
                "concentracao": concentracao_alerta,
                "mensagem": f"{len(concentracao_alerta)} fornecedor(es) com mais de 30% do volume" if concentracao_alerta else None
            }
        }

    async def _recomendar_fornecedor(self, context: AgentContext) -> Dict[str, Any]:
        """Recomenda fornecedor para uma necessidade"""

        dados = context.metadata.get("dados", {})
        categoria = CategoriaFornecedor(dados.get("categoria", "outros"))
        valor_estimado = dados.get("valor_estimado", 0)
        urgente = dados.get("urgente", False)

        candidatos = []

        for f in self.fornecedores.values():
            if f.status != StatusFornecedor.HOMOLOGADO:
                continue
            if f.categoria != categoria:
                continue

            # Calcula score de recomendação
            score = f.rating * 20  # Base: rating (0-100)

            # Bonus por documentação em dia
            docs_ok = len([d for d in f.documentos if self._documento_valido(d)])
            score += docs_ok * 2

            # Bonus por histórico positivo
            if f.volume_contratado > 0:
                score += 10

            # Penalidade por incidentes recentes
            incidentes = [a for a in f.historico_avaliacoes if a.get("tipo") == "incidente"]
            score -= len(incidentes) * 5

            candidatos.append({
                "fornecedor_id": f.fornecedor_id,
                "nome": f.nome_fantasia,
                "rating": f.rating,
                "volume_historico": f.volume_contratado,
                "score_recomendacao": score,
                "contato": f.contato_principal.get("telefone")
            })

        # Ordena por score
        candidatos.sort(key=lambda x: x["score_recomendacao"], reverse=True)

        if not candidatos:
            return {
                "status": "warning",
                "message": f"Nenhum fornecedor homologado encontrado para categoria {categoria.value}",
                "sugestao": "Cadastrar novos fornecedores ou abrir cotação"
            }

        return {
            "status": "success",
            "categoria": categoria.value,
            "recomendacoes": candidatos[:5],
            "melhor_opcao": candidatos[0] if candidatos else None
        }

    async def _monitorar_sla(self, context: AgentContext) -> Dict[str, Any]:
        """Monitora SLA dos fornecedores"""

        dados = context.metadata.get("dados", {})
        contrato_id = dados.get("contrato_id")

        resultados = []

        contratos_analisar = [self.contratos[contrato_id]] if contrato_id else list(self.contratos.values())

        for contrato in contratos_analisar:
            if contrato.status != StatusContrato.ATIVO:
                continue

            sla = contrato.sla
            if not sla:
                continue

            fornecedor = self.fornecedores.get(contrato.fornecedor_id)

            # Simula métricas de SLA (em produção, consultaria dados reais)
            import random
            metricas_atuais = {}
            cumprimento_geral = 0
            indicadores = sla.get("indicadores", {})

            for indicador, meta in indicadores.items():
                valor_atual = random.uniform(meta * 0.8, meta * 1.1)
                cumprido = valor_atual >= meta
                metricas_atuais[indicador] = {
                    "meta": meta,
                    "atual": valor_atual,
                    "cumprido": cumprido
                }
                if cumprido:
                    cumprimento_geral += 1

            taxa_cumprimento = (cumprimento_geral / len(indicadores) * 100) if indicadores else 100

            resultados.append({
                "contrato_id": contrato.contrato_id,
                "fornecedor": fornecedor.nome_fantasia if fornecedor else "N/A",
                "metricas": metricas_atuais,
                "taxa_cumprimento": taxa_cumprimento,
                "status": "OK" if taxa_cumprimento >= 90 else "ATENÇÃO" if taxa_cumprimento >= 70 else "CRÍTICO"
            })

        return {
            "status": "success",
            "monitoramento": resultados,
            "resumo": {
                "contratos_analisados": len(resultados),
                "ok": len([r for r in resultados if r["status"] == "OK"]),
                "atencao": len([r for r in resultados if r["status"] == "ATENÇÃO"]),
                "critico": len([r for r in resultados if r["status"] == "CRÍTICO"])
            }
        }

    async def _gerar_dashboard(self, context: AgentContext) -> Dict[str, Any]:
        """Gera dashboard de fornecedores"""

        hoje = datetime.now()

        # Contadores
        fornecedores_ativos = len([f for f in self.fornecedores.values() if f.status == StatusFornecedor.HOMOLOGADO])
        contratos_ativos = len([c for c in self.contratos.values() if c.status == StatusContrato.ATIVO])

        # Vencimentos próximos (30 dias)
        vencimentos = await self._verificar_vencimentos(AgentContext(
            user_id="system",
            session_id="dashboard",
            message="",
            metadata={"dados": {"dias": 30}}
        ))

        # Pedidos pendentes
        pedidos_pendentes = len([p for p in self.pedidos.values()
                                if p.status in [StatusPedido.AGUARDANDO_APROVACAO, StatusPedido.APROVADO]])

        # Pagamentos do mês
        pagamentos_mes = [p for p in self.pagamentos.values()
                        if p.data_vencimento.month == hoje.month and p.data_vencimento.year == hoje.year]
        total_pagar_mes = sum(p.valor for p in pagamentos_mes if p.status == "pendente")

        # Top categorias
        gastos = await self._analisar_gastos(AgentContext(
            user_id="system",
            session_id="dashboard",
            message="",
            metadata={"dados": {"meses": 12}}
        ))

        return {
            "status": "success",
            "dashboard": {
                "fornecedores": {
                    "ativos": fornecedores_ativos,
                    "total": len(self.fornecedores),
                    "em_avaliacao": len([f for f in self.fornecedores.values() if f.status == StatusFornecedor.EM_AVALIACAO])
                },
                "contratos": {
                    "ativos": contratos_ativos,
                    "vencendo_30_dias": vencimentos.get("resumo", {}).get("contratos", 0),
                    "valor_mensal_total": sum(c.valor_mensal or 0 for c in self.contratos.values() if c.status == StatusContrato.ATIVO)
                },
                "cotacoes": {
                    "abertas": len([c for c in self.cotacoes.values() if c.status in [StatusCotacao.ENVIADA, StatusCotacao.EM_ANALISE]]),
                    "economia_gerada": self.estatisticas["economia_gerada"]
                },
                "pedidos": {
                    "pendentes_aprovacao": len([p for p in self.pedidos.values() if p.status == StatusPedido.AGUARDANDO_APROVACAO]),
                    "em_andamento": pedidos_pendentes
                },
                "financeiro": {
                    "pagar_este_mes": total_pagar_mes,
                    "volume_ano": self.estatisticas["volume_contratado_ano"]
                },
                "alertas": {
                    "vencimentos": vencimentos.get("resumo", {}).get("total", 0),
                    "documentos_vencendo": vencimentos.get("resumo", {}).get("documentos", 0)
                },
                "top_categorias": gastos.get("por_categoria", [])[:5]
            }
        }

    async def _processar_chat(self, context: AgentContext) -> Dict[str, Any]:
        """Processa mensagens de chat"""

        mensagem = context.message.lower()

        # Análise de intenção
        if any(p in mensagem for p in ["cadastrar", "novo fornecedor", "adicionar fornecedor"]):
            return {
                "status": "info",
                "message": "Para cadastrar um fornecedor, preciso dos seguintes dados:",
                "campos": ["razao_social", "nome_fantasia", "cnpj", "categoria", "contato_principal", "endereco"]
            }

        if any(p in mensagem for p in ["cotação", "cotar", "orçamento"]):
            return {
                "status": "info",
                "message": "Para criar uma cotação, preciso:",
                "campos": ["titulo", "descricao", "categoria", "itens", "prazo_dias"]
            }

        if any(p in mensagem for p in ["vencimento", "vencendo", "vencer"]):
            return await self._verificar_vencimentos(context)

        if any(p in mensagem for p in ["ranking", "melhores", "top"]):
            return await self._ranking_fornecedores(context)

        if any(p in mensagem for p in ["dashboard", "resumo", "status"]):
            return await self._gerar_dashboard(context)

        # Resposta via LLM
        prompt = f"""
        Como agente de gestão de fornecedores, responda:

        Pergunta: {context.message}

        Estatísticas atuais:
        - Fornecedores ativos: {len([f for f in self.fornecedores.values() if f.status == StatusFornecedor.HOMOLOGADO])}
        - Contratos ativos: {len([c for c in self.contratos.values() if c.status == StatusContrato.ATIVO])}
        - Volume contratado no ano: R$ {self.estatisticas['volume_contratado_ano']:,.2f}

        Responda de forma objetiva e profissional.
        """

        resposta = await self.llm_client.generate(prompt)

        return {
            "status": "success",
            "response": resposta
        }


def create_supplier_agent(
    memory: UnifiedMemorySystem,
    llm_client: UnifiedLLMClient,
    tools: ToolRegistry,
    rag: Optional[RAGPipeline] = None
) -> SupplierAgent:
    """Factory function para criar o agente de fornecedores"""
    return SupplierAgent(memory, llm_client, tools, rag)
