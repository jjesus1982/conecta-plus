"""
Agente de Valorização v2 - Conecta Plus
Gestor de patrimônio - Valor de mercado, melhorias ROI, marketing
Nível 7: Transcendente - Maximiza valor do condomínio proativamente
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import math

from agents.core.base_agent import BaseAgent, AgentCapability, AgentContext
from agents.core.memory_store import UnifiedMemorySystem
from agents.core.llm_client import UnifiedLLMClient
from agents.core.tools import ToolRegistry
from agents.core.rag_system import RAGPipeline


class TipoImovel(Enum):
    """Tipos de imóvel"""
    APARTAMENTO = "apartamento"
    COBERTURA = "cobertura"
    DUPLEX = "duplex"
    TRIPLEX = "triplex"
    GARDEN = "garden"
    STUDIO = "studio"
    LOFT = "loft"
    SALA_COMERCIAL = "sala_comercial"
    LOJA = "loja"
    VAGA_GARAGEM = "vaga_garagem"


class CategoriaCondominio(Enum):
    """Categoria do condomínio"""
    ECONOMICO = "economico"
    PADRAO = "padrao"
    MEDIO = "medio"
    ALTO_PADRAO = "alto_padrao"
    LUXO = "luxo"
    SUPER_LUXO = "super_luxo"


class StatusMelhoria(Enum):
    """Status de melhoria"""
    IDEIA = "ideia"
    EM_ESTUDO = "em_estudo"
    APROVADA = "aprovada"
    EM_EXECUCAO = "em_execucao"
    CONCLUIDA = "concluida"
    CANCELADA = "cancelada"


class TipoMelhoria(Enum):
    """Tipos de melhoria"""
    INFRAESTRUTURA = "infraestrutura"
    SEGURANCA = "seguranca"
    LAZER = "lazer"
    SUSTENTABILIDADE = "sustentabilidade"
    TECNOLOGIA = "tecnologia"
    ESTETICA = "estetica"
    ACESSIBILIDADE = "acessibilidade"
    MANUTENCAO_PREVENTIVA = "manutencao_preventiva"


class TipoBenchmark(Enum):
    """Tipos de benchmark"""
    REGIAO = "regiao"
    CATEGORIA = "categoria"
    IDADE = "idade"
    TAMANHO = "tamanho"


@dataclass
class AvaliacaoMercado:
    """Avaliação de mercado do condomínio"""
    avaliacao_id: str
    data_avaliacao: datetime
    valor_metro_quadrado: float
    valor_medio_unidade: float
    variacao_12_meses: float
    posicao_ranking_regiao: int
    total_condominios_regiao: int
    pontuacao_geral: float  # 0-100
    fatores_positivos: List[str]
    fatores_negativos: List[str]
    comparativo_mercado: Dict[str, Any]
    tendencia: str  # alta, estavel, baixa
    fonte_dados: str
    metodologia: str


@dataclass
class ProjetoMelhoria:
    """Projeto de melhoria para valorização"""
    projeto_id: str
    titulo: str
    descricao: str
    tipo: TipoMelhoria
    status: StatusMelhoria
    investimento_estimado: float
    investimento_real: Optional[float]
    roi_estimado: float  # percentual
    prazo_retorno_meses: int
    impacto_valorizacao: float  # percentual
    areas_beneficiadas: List[str]
    prioridade: int  # 1-5
    votos_assembleia: Optional[Dict[str, int]]
    data_criacao: datetime = field(default_factory=datetime.now)
    data_inicio: Optional[datetime] = None
    data_conclusao: Optional[datetime] = None
    responsavel: Optional[str] = None
    fornecedor: Optional[str] = None
    documentos: List[Dict[str, Any]] = field(default_factory=list)
    fotos_antes: List[str] = field(default_factory=list)
    fotos_depois: List[str] = field(default_factory=list)


@dataclass
class IndicadorValorizacao:
    """Indicador de valorização"""
    indicador_id: str
    nome: str
    categoria: str
    valor_atual: float
    valor_referencia: float  # benchmark
    percentual_atingimento: float
    peso_valorizacao: float
    ultima_atualizacao: datetime
    historico: List[Dict[str, Any]]
    sugestoes_melhoria: List[str]


@dataclass
class PerfilCondominio:
    """Perfil completo do condomínio"""
    condominio_id: str
    nome: str
    endereco: Dict[str, str]
    ano_construcao: int
    categoria: CategoriaCondominio
    total_unidades: int
    total_torres: int
    total_andares: int
    area_total_terreno: float
    area_total_construida: float
    areas_comuns: List[Dict[str, Any]]
    diferenciais: List[str]
    certificacoes: List[str]
    nota_avaliacao: float
    valor_m2_atual: float
    historico_valores: List[Dict[str, Any]]


@dataclass
class CampanhaMarketing:
    """Campanha de marketing do condomínio"""
    campanha_id: str
    titulo: str
    objetivo: str
    publico_alvo: str  # moradores, compradores, investidores
    canais: List[str]
    conteudos: List[Dict[str, Any]]
    data_inicio: datetime
    data_fim: Optional[datetime]
    orcamento: float
    resultados: Dict[str, Any]
    status: str


@dataclass
class ComparativoMercado:
    """Comparativo com mercado"""
    comparativo_id: str
    data_geracao: datetime
    condominios_comparados: List[Dict[str, Any]]
    criterios: List[str]
    ranking_geral: int
    destaques_positivos: List[str]
    pontos_melhorar: List[str]
    gap_lider: float  # diferença para o líder


class PropertyValueAgent(BaseAgent):
    """
    Agente de Valorização - Nível 7 Transcendente

    Capacidades:
    - Avaliação de valor de mercado do condomínio
    - Análise de fatores de valorização/desvalorização
    - Planejamento de melhorias com análise de ROI
    - Benchmark com condomínios da região
    - Marketing e posicionamento do condomínio
    - Certificações e selos de qualidade
    - Relatórios para compradores/investidores
    - Acompanhamento de tendências imobiliárias
    - Gestão de diferenciais competitivos
    """

    def __init__(
        self,
        memory: UnifiedMemorySystem,
        llm_client: UnifiedLLMClient,
        tools: ToolRegistry,
        rag: Optional[RAGPipeline] = None
    ):
        super().__init__(
            agent_id="property-value-agent",
            name="Agente de Valorização",
            capabilities=[
                AgentCapability.MARKET_ANALYSIS,
                AgentCapability.INVESTMENT_PLANNING,
                AgentCapability.REPORTING,
                AgentCapability.MARKETING,
                AgentCapability.BENCHMARKING
            ],
            memory=memory,
            llm_client=llm_client,
            tools=tools
        )

        self.rag = rag

        # Armazenamento
        self.perfil_condominio: Optional[PerfilCondominio] = None
        self.avaliacoes: Dict[str, AvaliacaoMercado] = {}
        self.projetos_melhoria: Dict[str, ProjetoMelhoria] = {}
        self.indicadores: Dict[str, IndicadorValorizacao] = {}
        self.campanhas: Dict[str, CampanhaMarketing] = {}
        self.comparativos: Dict[str, ComparativoMercado] = {}

        # Fatores de valorização (pesos)
        self.fatores_valorizacao = {
            "localizacao": {
                "peso": 0.20,
                "subfatores": ["transporte", "comercio", "escolas", "hospitais", "seguranca_regiao"]
            },
            "infraestrutura": {
                "peso": 0.15,
                "subfatores": ["elevadores", "garagem", "portaria", "areas_comuns", "manutencao"]
            },
            "seguranca": {
                "peso": 0.15,
                "subfatores": ["portaria_24h", "cftv", "controle_acesso", "cercas", "rondas"]
            },
            "lazer": {
                "peso": 0.12,
                "subfatores": ["piscina", "academia", "salao_festas", "playground", "churrasqueira"]
            },
            "sustentabilidade": {
                "peso": 0.10,
                "subfatores": ["energia_solar", "reuso_agua", "coleta_seletiva", "areas_verdes"]
            },
            "tecnologia": {
                "peso": 0.08,
                "subfatores": ["automacao", "wifi_comum", "app_condominio", "carregador_eletrico"]
            },
            "estado_conservacao": {
                "peso": 0.10,
                "subfatores": ["fachada", "areas_comuns", "equipamentos", "pintura"]
            },
            "gestao": {
                "peso": 0.10,
                "subfatores": ["transparencia", "inadimplencia", "reservas", "documentacao"]
            }
        }

        # Benchmarks de mercado (simulado)
        self.benchmarks_mercado = {
            CategoriaCondominio.ECONOMICO: {"m2_min": 3000, "m2_max": 5000, "m2_medio": 4000},
            CategoriaCondominio.PADRAO: {"m2_min": 5000, "m2_max": 8000, "m2_medio": 6500},
            CategoriaCondominio.MEDIO: {"m2_min": 7000, "m2_max": 12000, "m2_medio": 9500},
            CategoriaCondominio.ALTO_PADRAO: {"m2_min": 10000, "m2_max": 20000, "m2_medio": 15000},
            CategoriaCondominio.LUXO: {"m2_min": 18000, "m2_max": 35000, "m2_medio": 25000},
            CategoriaCondominio.SUPER_LUXO: {"m2_min": 30000, "m2_max": 80000, "m2_medio": 50000}
        }

        # Estatísticas
        self.estatisticas = {
            "avaliacoes_realizadas": 0,
            "projetos_melhorias": 0,
            "investimento_total": 0.0,
            "valorizacao_acumulada": 0.0
        }

    async def process(self, context: AgentContext) -> Dict[str, Any]:
        """Processa requisições de valorização"""

        intent = context.metadata.get("intent", "")

        handlers = {
            # Perfil e Avaliação
            "configurar_perfil": self._configurar_perfil,
            "avaliar_mercado": self._avaliar_mercado,
            "calcular_valor_m2": self._calcular_valor_m2,
            "historico_valores": self._historico_valores,

            # Indicadores
            "avaliar_indicadores": self._avaliar_indicadores,
            "atualizar_indicador": self._atualizar_indicador,
            "radar_valorizacao": self._radar_valorizacao,

            # Melhorias
            "propor_melhoria": self._propor_melhoria,
            "calcular_roi": self._calcular_roi,
            "priorizar_melhorias": self._priorizar_melhorias,
            "atualizar_melhoria": self._atualizar_melhoria,
            "listar_melhorias": self._listar_melhorias,

            # Benchmark
            "benchmark_regiao": self._benchmark_regiao,
            "comparar_condominios": self._comparar_condominios,
            "analise_competitiva": self._analise_competitiva,

            # Marketing
            "criar_campanha": self._criar_campanha,
            "gerar_material": self._gerar_material,
            "listar_diferenciais": self._listar_diferenciais,

            # Relatórios
            "relatorio_valor": self._relatorio_valor,
            "relatorio_investidor": self._relatorio_investidor,
            "certificacoes": self._certificacoes,

            # Dashboard e Chat
            "dashboard": self._gerar_dashboard,
            "chat": self._processar_chat,
        }

        handler = handlers.get(intent, self._processar_chat)
        return await handler(context)

    async def _configurar_perfil(self, context: AgentContext) -> Dict[str, Any]:
        """Configura perfil do condomínio"""

        dados = context.metadata.get("dados", {})

        self.perfil_condominio = PerfilCondominio(
            condominio_id=dados.get("condominio_id", "COND-001"),
            nome=dados.get("nome", "Condomínio Conecta Plus"),
            endereco=dados.get("endereco", {}),
            ano_construcao=dados.get("ano_construcao", 2020),
            categoria=CategoriaCondominio(dados.get("categoria", "medio")),
            total_unidades=dados.get("total_unidades", 100),
            total_torres=dados.get("total_torres", 2),
            total_andares=dados.get("total_andares", 15),
            area_total_terreno=dados.get("area_terreno", 5000.0),
            area_total_construida=dados.get("area_construida", 15000.0),
            areas_comuns=dados.get("areas_comuns", []),
            diferenciais=dados.get("diferenciais", []),
            certificacoes=dados.get("certificacoes", []),
            nota_avaliacao=dados.get("nota", 0.0),
            valor_m2_atual=dados.get("valor_m2", 0.0),
            historico_valores=[]
        )

        # Inicializa indicadores padrão
        await self._inicializar_indicadores()

        return {
            "status": "success",
            "message": "Perfil do condomínio configurado",
            "perfil": {
                "id": self.perfil_condominio.condominio_id,
                "nome": self.perfil_condominio.nome,
                "categoria": self.perfil_condominio.categoria.value,
                "unidades": self.perfil_condominio.total_unidades,
                "ano_construcao": self.perfil_condominio.ano_construcao
            }
        }

    async def _inicializar_indicadores(self):
        """Inicializa indicadores de valorização"""

        indicadores_padrao = [
            ("IND-001", "Segurança", "seguranca", 0.8, 1.0),
            ("IND-002", "Infraestrutura", "infraestrutura", 0.75, 1.0),
            ("IND-003", "Lazer", "lazer", 0.7, 1.0),
            ("IND-004", "Sustentabilidade", "sustentabilidade", 0.5, 1.0),
            ("IND-005", "Tecnologia", "tecnologia", 0.6, 1.0),
            ("IND-006", "Estado de Conservação", "estado_conservacao", 0.85, 1.0),
            ("IND-007", "Gestão", "gestao", 0.9, 1.0),
        ]

        for ind_id, nome, categoria, valor, ref in indicadores_padrao:
            self.indicadores[ind_id] = IndicadorValorizacao(
                indicador_id=ind_id,
                nome=nome,
                categoria=categoria,
                valor_atual=valor,
                valor_referencia=ref,
                percentual_atingimento=valor / ref * 100,
                peso_valorizacao=self.fatores_valorizacao.get(categoria, {}).get("peso", 0.1),
                ultima_atualizacao=datetime.now(),
                historico=[{"data": datetime.now().isoformat(), "valor": valor}],
                sugestoes_melhoria=[]
            )

    async def _avaliar_mercado(self, context: AgentContext) -> Dict[str, Any]:
        """Realiza avaliação de mercado do condomínio"""

        if not self.perfil_condominio:
            return {"status": "error", "message": "Perfil do condomínio não configurado"}

        avaliacao_id = f"AVAL-{datetime.now().strftime('%Y%m%d')}-{len(self.avaliacoes) + 1:04d}"

        # Calcula valor m2
        valor_m2 = await self._calcular_valor_m2_interno()

        # Calcula variação
        variacao = 0.0
        if self.perfil_condominio.historico_valores:
            ultimo = self.perfil_condominio.historico_valores[-1]
            if ultimo.get("valor_m2"):
                variacao = (valor_m2 - ultimo["valor_m2"]) / ultimo["valor_m2"] * 100

        # Calcula pontuação geral
        pontuacao = await self._calcular_pontuacao_geral()

        # Identifica fatores
        fatores_pos, fatores_neg = await self._identificar_fatores()

        # Posição no ranking (simulado)
        import random
        posicao_ranking = random.randint(1, 10)
        total_regiao = random.randint(15, 30)

        avaliacao = AvaliacaoMercado(
            avaliacao_id=avaliacao_id,
            data_avaliacao=datetime.now(),
            valor_metro_quadrado=valor_m2,
            valor_medio_unidade=valor_m2 * 70,  # Média 70m2
            variacao_12_meses=variacao,
            posicao_ranking_regiao=posicao_ranking,
            total_condominios_regiao=total_regiao,
            pontuacao_geral=pontuacao,
            fatores_positivos=fatores_pos,
            fatores_negativos=fatores_neg,
            comparativo_mercado=self._comparar_com_benchmark(valor_m2),
            tendencia="alta" if variacao > 2 else "estavel" if variacao > -2 else "baixa",
            fonte_dados="Análise Conecta Plus AI",
            metodologia="Comparativo de mercado com ajustes por características"
        )

        self.avaliacoes[avaliacao_id] = avaliacao
        self.estatisticas["avaliacoes_realizadas"] += 1

        # Atualiza perfil
        self.perfil_condominio.valor_m2_atual = valor_m2
        self.perfil_condominio.nota_avaliacao = pontuacao
        self.perfil_condominio.historico_valores.append({
            "data": datetime.now().isoformat(),
            "valor_m2": valor_m2,
            "pontuacao": pontuacao
        })

        return {
            "status": "success",
            "avaliacao": {
                "id": avaliacao_id,
                "data": avaliacao.data_avaliacao.strftime("%d/%m/%Y"),
                "valor_m2": f"R$ {valor_m2:,.2f}",
                "valor_unidade_media": f"R$ {avaliacao.valor_medio_unidade:,.2f}",
                "variacao_12m": f"{variacao:+.1f}%",
                "pontuacao": f"{pontuacao:.1f}/100",
                "ranking": f"{posicao_ranking}º de {total_regiao} na região",
                "tendencia": avaliacao.tendencia
            },
            "fatores_positivos": fatores_pos[:5],
            "fatores_negativos": fatores_neg[:5],
            "comparativo_mercado": avaliacao.comparativo_mercado
        }

    async def _calcular_valor_m2_interno(self) -> float:
        """Calcula valor do m2 baseado nos indicadores"""

        if not self.perfil_condominio:
            return 0.0

        # Obtém benchmark da categoria
        categoria = self.perfil_condominio.categoria
        benchmark = self.benchmarks_mercado.get(categoria, {"m2_medio": 10000})
        valor_base = benchmark["m2_medio"]

        # Ajusta baseado nos indicadores
        ajuste_total = 0.0

        for ind in self.indicadores.values():
            peso = ind.peso_valorizacao
            performance = ind.valor_atual / ind.valor_referencia
            # Performance acima de 80% adiciona valor, abaixo diminui
            ajuste = (performance - 0.8) * peso * 0.5
            ajuste_total += ajuste

        # Ajusta pela idade do imóvel
        idade = datetime.now().year - self.perfil_condominio.ano_construcao
        ajuste_idade = max(-0.15, -0.01 * idade)  # Máximo -15% por idade
        ajuste_total += ajuste_idade

        # Calcula valor final
        valor_final = valor_base * (1 + ajuste_total)

        return round(valor_final, 2)

    async def _calcular_valor_m2(self, context: AgentContext) -> Dict[str, Any]:
        """Calcula e retorna valor do m2"""

        valor = await self._calcular_valor_m2_interno()

        # Calcula faixa de variação
        margem = valor * 0.1
        valor_min = valor - margem
        valor_max = valor + margem

        return {
            "status": "success",
            "valor_m2": {
                "estimado": f"R$ {valor:,.2f}",
                "minimo": f"R$ {valor_min:,.2f}",
                "maximo": f"R$ {valor_max:,.2f}",
                "confianca": "85%"
            },
            "metodologia": "Análise comparativa com ajustes por características"
        }

    async def _calcular_pontuacao_geral(self) -> float:
        """Calcula pontuação geral do condomínio"""

        if not self.indicadores:
            return 50.0

        pontuacao_total = 0.0
        peso_total = 0.0

        for ind in self.indicadores.values():
            pontuacao_total += ind.valor_atual * ind.peso_valorizacao * 100
            peso_total += ind.peso_valorizacao

        return round(pontuacao_total / peso_total if peso_total > 0 else 50.0, 1)

    async def _identificar_fatores(self) -> Tuple[List[str], List[str]]:
        """Identifica fatores positivos e negativos"""

        positivos = []
        negativos = []

        for ind in self.indicadores.values():
            percentual = ind.percentual_atingimento

            if percentual >= 90:
                positivos.append(f"{ind.nome}: excelente ({percentual:.0f}%)")
            elif percentual >= 75:
                positivos.append(f"{ind.nome}: bom ({percentual:.0f}%)")
            elif percentual < 60:
                negativos.append(f"{ind.nome}: necessita atenção ({percentual:.0f}%)")

        # Adiciona fatores baseados no perfil
        if self.perfil_condominio:
            if self.perfil_condominio.certificacoes:
                positivos.append(f"Certificações: {', '.join(self.perfil_condominio.certificacoes[:3])}")

            if self.perfil_condominio.diferenciais:
                positivos.append(f"Diferenciais: {', '.join(self.perfil_condominio.diferenciais[:3])}")

            idade = datetime.now().year - self.perfil_condominio.ano_construcao
            if idade <= 5:
                positivos.append(f"Construção recente ({idade} anos)")
            elif idade > 20:
                negativos.append(f"Imóvel com {idade} anos")

        return positivos, negativos

    def _comparar_com_benchmark(self, valor_m2: float) -> Dict[str, Any]:
        """Compara valor com benchmark de mercado"""

        if not self.perfil_condominio:
            return {}

        categoria = self.perfil_condominio.categoria
        benchmark = self.benchmarks_mercado.get(categoria, {})

        m2_medio = benchmark.get("m2_medio", valor_m2)
        m2_min = benchmark.get("m2_min", valor_m2 * 0.8)
        m2_max = benchmark.get("m2_max", valor_m2 * 1.2)

        posicao = "acima" if valor_m2 > m2_medio else "abaixo" if valor_m2 < m2_medio else "na média"
        diferenca = (valor_m2 - m2_medio) / m2_medio * 100

        return {
            "categoria": categoria.value,
            "valor_atual": valor_m2,
            "media_mercado": m2_medio,
            "faixa_mercado": f"R$ {m2_min:,.0f} - R$ {m2_max:,.0f}",
            "posicao": posicao,
            "diferenca_percentual": f"{diferenca:+.1f}%"
        }

    async def _historico_valores(self, context: AgentContext) -> Dict[str, Any]:
        """Retorna histórico de valores"""

        if not self.perfil_condominio:
            return {"status": "error", "message": "Perfil não configurado"}

        historico = self.perfil_condominio.historico_valores

        # Calcula variações
        variacoes = []
        for i in range(1, len(historico)):
            anterior = historico[i-1]["valor_m2"]
            atual = historico[i]["valor_m2"]
            variacao = (atual - anterior) / anterior * 100
            variacoes.append({
                "data": historico[i]["data"],
                "valor": atual,
                "variacao": variacao
            })

        return {
            "status": "success",
            "historico": historico,
            "variacoes": variacoes,
            "valor_atual": self.perfil_condominio.valor_m2_atual,
            "total_registros": len(historico)
        }

    async def _avaliar_indicadores(self, context: AgentContext) -> Dict[str, Any]:
        """Avalia todos os indicadores de valorização"""

        resultado = {
            "indicadores": [],
            "pontuacao_geral": await self._calcular_pontuacao_geral(),
            "areas_destaque": [],
            "areas_atencao": []
        }

        for ind in self.indicadores.values():
            resultado["indicadores"].append({
                "id": ind.indicador_id,
                "nome": ind.nome,
                "categoria": ind.categoria,
                "valor_atual": f"{ind.valor_atual:.0%}",
                "meta": f"{ind.valor_referencia:.0%}",
                "atingimento": f"{ind.percentual_atingimento:.0f}%",
                "peso": f"{ind.peso_valorizacao:.0%}",
                "status": "OK" if ind.percentual_atingimento >= 80 else "ATENÇÃO" if ind.percentual_atingimento >= 60 else "CRÍTICO"
            })

            if ind.percentual_atingimento >= 90:
                resultado["areas_destaque"].append(ind.nome)
            elif ind.percentual_atingimento < 70:
                resultado["areas_atencao"].append(ind.nome)

        return {
            "status": "success",
            **resultado
        }

    async def _atualizar_indicador(self, context: AgentContext) -> Dict[str, Any]:
        """Atualiza valor de um indicador"""

        dados = context.metadata.get("dados", {})
        indicador_id = dados.get("indicador_id")
        novo_valor = dados.get("valor")

        if indicador_id not in self.indicadores:
            return {"status": "error", "message": "Indicador não encontrado"}

        ind = self.indicadores[indicador_id]
        valor_anterior = ind.valor_atual

        ind.valor_atual = novo_valor
        ind.percentual_atingimento = (novo_valor / ind.valor_referencia) * 100
        ind.ultima_atualizacao = datetime.now()
        ind.historico.append({
            "data": datetime.now().isoformat(),
            "valor": novo_valor
        })

        variacao = (novo_valor - valor_anterior) / valor_anterior * 100 if valor_anterior > 0 else 0

        return {
            "status": "success",
            "message": f"Indicador {ind.nome} atualizado",
            "indicador": {
                "id": indicador_id,
                "nome": ind.nome,
                "valor_anterior": f"{valor_anterior:.0%}",
                "valor_novo": f"{novo_valor:.0%}",
                "variacao": f"{variacao:+.1f}%"
            }
        }

    async def _radar_valorizacao(self, context: AgentContext) -> Dict[str, Any]:
        """Gera radar de valorização (gráfico radar com indicadores)"""

        dados_radar = []

        for ind in self.indicadores.values():
            dados_radar.append({
                "eixo": ind.nome,
                "valor": ind.percentual_atingimento,
                "meta": 100
            })

        return {
            "status": "success",
            "radar": {
                "titulo": "Radar de Valorização",
                "dados": dados_radar,
                "pontuacao_geral": await self._calcular_pontuacao_geral()
            }
        }

    async def _propor_melhoria(self, context: AgentContext) -> Dict[str, Any]:
        """Propõe projeto de melhoria"""

        dados = context.metadata.get("dados", {})

        projeto_id = f"PROJ-{datetime.now().strftime('%Y%m%d')}-{len(self.projetos_melhoria) + 1:04d}"

        # Calcula ROI estimado
        investimento = dados.get("investimento_estimado", 0)
        impacto = dados.get("impacto_valorizacao", 0.05)

        if self.perfil_condominio:
            valor_total_condominio = (
                self.perfil_condominio.valor_m2_atual *
                self.perfil_condominio.area_total_construida
            )
            ganho_estimado = valor_total_condominio * impacto
            roi = (ganho_estimado / investimento * 100) if investimento > 0 else 0
            prazo_retorno = int(investimento / (ganho_estimado / 60)) if ganho_estimado > 0 else 0  # meses
        else:
            roi = 0
            prazo_retorno = 0

        projeto = ProjetoMelhoria(
            projeto_id=projeto_id,
            titulo=dados.get("titulo", ""),
            descricao=dados.get("descricao", ""),
            tipo=TipoMelhoria(dados.get("tipo", "infraestrutura")),
            status=StatusMelhoria.IDEIA,
            investimento_estimado=investimento,
            roi_estimado=roi,
            prazo_retorno_meses=prazo_retorno,
            impacto_valorizacao=impacto * 100,
            areas_beneficiadas=dados.get("areas", []),
            prioridade=dados.get("prioridade", 3),
            responsavel=dados.get("responsavel")
        )

        self.projetos_melhoria[projeto_id] = projeto
        self.estatisticas["projetos_melhorias"] += 1

        return {
            "status": "success",
            "message": f"Projeto de melhoria {projeto_id} criado",
            "projeto": {
                "id": projeto_id,
                "titulo": projeto.titulo,
                "tipo": projeto.tipo.value,
                "investimento": f"R$ {investimento:,.2f}",
                "roi_estimado": f"{roi:.1f}%",
                "impacto_valorizacao": f"{impacto*100:.1f}%",
                "prazo_retorno": f"{prazo_retorno} meses",
                "prioridade": projeto.prioridade
            }
        }

    async def _calcular_roi(self, context: AgentContext) -> Dict[str, Any]:
        """Calcula ROI de um projeto de melhoria"""

        dados = context.metadata.get("dados", {})
        projeto_id = dados.get("projeto_id")

        if projeto_id and projeto_id in self.projetos_melhoria:
            projeto = self.projetos_melhoria[projeto_id]
            investimento = projeto.investimento_estimado
            impacto = projeto.impacto_valorizacao / 100
        else:
            investimento = dados.get("investimento", 0)
            impacto = dados.get("impacto_percentual", 0) / 100

        if not self.perfil_condominio or investimento <= 0:
            return {"status": "error", "message": "Dados insuficientes para cálculo"}

        valor_total = self.perfil_condominio.valor_m2_atual * self.perfil_condominio.area_total_construida
        valor_por_unidade = valor_total / self.perfil_condominio.total_unidades

        ganho_total = valor_total * impacto
        ganho_por_unidade = ganho_total / self.perfil_condominio.total_unidades
        investimento_por_unidade = investimento / self.perfil_condominio.total_unidades

        roi = (ganho_total / investimento * 100)
        payback_meses = int(investimento / (ganho_total / 60)) if ganho_total > 0 else 0

        return {
            "status": "success",
            "analise_roi": {
                "investimento_total": f"R$ {investimento:,.2f}",
                "investimento_por_unidade": f"R$ {investimento_por_unidade:,.2f}",
                "impacto_valorizacao": f"{impacto*100:.1f}%",
                "ganho_patrimonial_total": f"R$ {ganho_total:,.2f}",
                "ganho_por_unidade": f"R$ {ganho_por_unidade:,.2f}",
                "roi": f"{roi:.1f}%",
                "payback": f"{payback_meses} meses",
                "recomendacao": "FAVORÁVEL" if roi > 100 else "AVALIAR" if roi > 50 else "DESFAVORÁVEL"
            }
        }

    async def _priorizar_melhorias(self, context: AgentContext) -> Dict[str, Any]:
        """Prioriza projetos de melhoria"""

        projetos_priorizados = []

        for proj in self.projetos_melhoria.values():
            if proj.status in [StatusMelhoria.IDEIA, StatusMelhoria.EM_ESTUDO]:
                # Calcula score de priorização
                score = 0

                # ROI alto = mais prioridade
                score += min(proj.roi_estimado / 10, 30)  # Máx 30 pontos

                # Impacto alto = mais prioridade
                score += min(proj.impacto_valorizacao * 2, 20)  # Máx 20 pontos

                # Prioridade definida
                score += (6 - proj.prioridade) * 5  # 5-25 pontos

                # Prazo de retorno curto = mais prioridade
                if proj.prazo_retorno_meses <= 12:
                    score += 15
                elif proj.prazo_retorno_meses <= 24:
                    score += 10
                elif proj.prazo_retorno_meses <= 36:
                    score += 5

                projetos_priorizados.append({
                    "id": proj.projeto_id,
                    "titulo": proj.titulo,
                    "tipo": proj.tipo.value,
                    "investimento": proj.investimento_estimado,
                    "roi": proj.roi_estimado,
                    "impacto": proj.impacto_valorizacao,
                    "prazo_retorno": proj.prazo_retorno_meses,
                    "score_priorizacao": score
                })

        # Ordena por score
        projetos_priorizados.sort(key=lambda x: x["score_priorizacao"], reverse=True)

        return {
            "status": "success",
            "projetos_priorizados": projetos_priorizados,
            "total": len(projetos_priorizados),
            "recomendacao": projetos_priorizados[0] if projetos_priorizados else None
        }

    async def _atualizar_melhoria(self, context: AgentContext) -> Dict[str, Any]:
        """Atualiza status de projeto de melhoria"""

        dados = context.metadata.get("dados", {})
        projeto_id = dados.get("projeto_id")

        if projeto_id not in self.projetos_melhoria:
            return {"status": "error", "message": "Projeto não encontrado"}

        projeto = self.projetos_melhoria[projeto_id]

        novo_status = dados.get("status")
        if novo_status:
            projeto.status = StatusMelhoria(novo_status)

            if novo_status == "em_execucao":
                projeto.data_inicio = datetime.now()
            elif novo_status == "concluida":
                projeto.data_conclusao = datetime.now()
                projeto.investimento_real = dados.get("investimento_real", projeto.investimento_estimado)
                self.estatisticas["investimento_total"] += projeto.investimento_real

                # Atualiza indicadores relacionados
                await self._aplicar_impacto_melhoria(projeto)

        if dados.get("fotos_depois"):
            projeto.fotos_depois.extend(dados["fotos_depois"])

        return {
            "status": "success",
            "message": f"Projeto {projeto_id} atualizado",
            "projeto": {
                "id": projeto_id,
                "status": projeto.status.value
            }
        }

    async def _aplicar_impacto_melhoria(self, projeto: ProjetoMelhoria):
        """Aplica impacto de melhoria nos indicadores"""

        categoria_indicador = {
            TipoMelhoria.INFRAESTRUTURA: "infraestrutura",
            TipoMelhoria.SEGURANCA: "seguranca",
            TipoMelhoria.LAZER: "lazer",
            TipoMelhoria.SUSTENTABILIDADE: "sustentabilidade",
            TipoMelhoria.TECNOLOGIA: "tecnologia",
            TipoMelhoria.ESTETICA: "estado_conservacao",
            TipoMelhoria.ACESSIBILIDADE: "infraestrutura",
            TipoMelhoria.MANUTENCAO_PREVENTIVA: "estado_conservacao"
        }

        categoria = categoria_indicador.get(projeto.tipo)

        for ind in self.indicadores.values():
            if ind.categoria == categoria:
                # Aumenta indicador baseado no impacto
                aumento = projeto.impacto_valorizacao / 100 * 0.3  # 30% do impacto vai pro indicador
                ind.valor_atual = min(1.0, ind.valor_atual + aumento)
                ind.percentual_atingimento = ind.valor_atual / ind.valor_referencia * 100
                ind.historico.append({
                    "data": datetime.now().isoformat(),
                    "valor": ind.valor_atual,
                    "motivo": f"Melhoria: {projeto.titulo}"
                })

    async def _listar_melhorias(self, context: AgentContext) -> Dict[str, Any]:
        """Lista projetos de melhoria"""

        dados = context.metadata.get("dados", {})
        status_filtro = dados.get("status")

        projetos = []

        for proj in self.projetos_melhoria.values():
            if status_filtro and proj.status.value != status_filtro:
                continue

            projetos.append({
                "id": proj.projeto_id,
                "titulo": proj.titulo,
                "tipo": proj.tipo.value,
                "status": proj.status.value,
                "investimento": f"R$ {proj.investimento_estimado:,.2f}",
                "roi": f"{proj.roi_estimado:.1f}%",
                "impacto": f"{proj.impacto_valorizacao:.1f}%",
                "prioridade": proj.prioridade
            })

        # Agrupa por status
        por_status = {}
        for proj in projetos:
            status = proj["status"]
            por_status[status] = por_status.get(status, 0) + 1

        return {
            "status": "success",
            "projetos": projetos,
            "total": len(projetos),
            "por_status": por_status
        }

    async def _benchmark_regiao(self, context: AgentContext) -> Dict[str, Any]:
        """Realiza benchmark com condomínios da região"""

        if not self.perfil_condominio:
            return {"status": "error", "message": "Perfil não configurado"}

        # Simula dados de condomínios da região
        import random

        condominios_regiao = []
        for i in range(10):
            valor_m2 = random.uniform(
                self.benchmarks_mercado[self.perfil_condominio.categoria]["m2_min"],
                self.benchmarks_mercado[self.perfil_condominio.categoria]["m2_max"]
            )
            condominios_regiao.append({
                "nome": f"Condomínio {chr(65 + i)}",
                "valor_m2": valor_m2,
                "pontuacao": random.uniform(60, 95),
                "idade": random.randint(1, 20),
                "unidades": random.randint(50, 200)
            })

        # Adiciona o próprio condomínio
        condominios_regiao.append({
            "nome": self.perfil_condominio.nome,
            "valor_m2": self.perfil_condominio.valor_m2_atual,
            "pontuacao": await self._calcular_pontuacao_geral(),
            "idade": datetime.now().year - self.perfil_condominio.ano_construcao,
            "unidades": self.perfil_condominio.total_unidades,
            "proprio": True
        })

        # Ordena por valor m2
        condominios_regiao.sort(key=lambda x: x["valor_m2"], reverse=True)

        # Encontra posição
        posicao = next(
            (i + 1 for i, c in enumerate(condominios_regiao) if c.get("proprio")),
            len(condominios_regiao)
        )

        # Calcula gap para o líder
        lider = condominios_regiao[0]
        gap = (lider["valor_m2"] - self.perfil_condominio.valor_m2_atual) / self.perfil_condominio.valor_m2_atual * 100

        return {
            "status": "success",
            "benchmark": {
                "posicao": posicao,
                "total": len(condominios_regiao),
                "percentil": f"{(1 - posicao/len(condominios_regiao)) * 100:.0f}%",
                "gap_lider": f"{gap:+.1f}%",
                "lider": {
                    "nome": lider["nome"],
                    "valor_m2": f"R$ {lider['valor_m2']:,.2f}"
                }
            },
            "ranking": [{
                "posicao": i + 1,
                "nome": c["nome"],
                "valor_m2": f"R$ {c['valor_m2']:,.2f}",
                "proprio": c.get("proprio", False)
            } for i, c in enumerate(condominios_regiao)]
        }

    async def _comparar_condominios(self, context: AgentContext) -> Dict[str, Any]:
        """Compara com condomínios específicos"""

        dados = context.metadata.get("dados", {})
        condominios_comparar = dados.get("condominios", [])

        if not self.perfil_condominio:
            return {"status": "error", "message": "Perfil não configurado"}

        comparativo_id = f"COMP-{datetime.now().strftime('%Y%m%d')}-{len(self.comparativos) + 1:04d}"

        # Simula dados dos condomínios a comparar
        comparacao = []

        # Adiciona o próprio
        meu_condo = {
            "nome": self.perfil_condominio.nome,
            "valor_m2": self.perfil_condominio.valor_m2_atual,
            "pontuacao": await self._calcular_pontuacao_geral(),
            "seguranca": self.indicadores.get("IND-001", {}).valor_atual if "IND-001" in self.indicadores else 0.8,
            "lazer": self.indicadores.get("IND-003", {}).valor_atual if "IND-003" in self.indicadores else 0.7,
            "infraestrutura": self.indicadores.get("IND-002", {}).valor_atual if "IND-002" in self.indicadores else 0.75,
            "proprio": True
        }
        comparacao.append(meu_condo)

        # Simula outros
        import random
        for nome in condominios_comparar[:5]:
            comparacao.append({
                "nome": nome,
                "valor_m2": random.uniform(8000, 15000),
                "pontuacao": random.uniform(60, 90),
                "seguranca": random.uniform(0.6, 1.0),
                "lazer": random.uniform(0.5, 1.0),
                "infraestrutura": random.uniform(0.6, 1.0)
            })

        # Identifica destaques
        destaques = []
        melhorar = []

        for criterio in ["valor_m2", "pontuacao", "seguranca", "lazer", "infraestrutura"]:
            valores = [c[criterio] for c in comparacao]
            meu_valor = meu_condo[criterio]

            if meu_valor >= max(valores) * 0.95:
                destaques.append(criterio)
            elif meu_valor <= min(valores) * 1.05:
                melhorar.append(criterio)

        comparativo = ComparativoMercado(
            comparativo_id=comparativo_id,
            data_geracao=datetime.now(),
            condominios_comparados=comparacao,
            criterios=["valor_m2", "pontuacao", "seguranca", "lazer", "infraestrutura"],
            ranking_geral=sorted(comparacao, key=lambda x: x["pontuacao"], reverse=True).index(meu_condo) + 1,
            destaques_positivos=destaques,
            pontos_melhorar=melhorar,
            gap_lider=(max(c["pontuacao"] for c in comparacao) - meu_condo["pontuacao"])
        )

        self.comparativos[comparativo_id] = comparativo

        return {
            "status": "success",
            "comparativo_id": comparativo_id,
            "comparacao": comparacao,
            "ranking": comparativo.ranking_geral,
            "destaques": destaques,
            "melhorar": melhorar,
            "gap_lider": f"{comparativo.gap_lider:.1f} pontos"
        }

    async def _analise_competitiva(self, context: AgentContext) -> Dict[str, Any]:
        """Análise competitiva do condomínio"""

        if not self.perfil_condominio:
            return {"status": "error", "message": "Perfil não configurado"}

        # Gera análise SWOT usando LLM
        prompt = f"""
        Analise competitivamente o condomínio com as seguintes características:

        Nome: {self.perfil_condominio.nome}
        Categoria: {self.perfil_condominio.categoria.value}
        Idade: {datetime.now().year - self.perfil_condominio.ano_construcao} anos
        Unidades: {self.perfil_condominio.total_unidades}
        Valor m2: R$ {self.perfil_condominio.valor_m2_atual:,.2f}
        Diferenciais: {', '.join(self.perfil_condominio.diferenciais[:5])}
        Certificações: {', '.join(self.perfil_condominio.certificacoes)}

        Indicadores:
        {json.dumps({ind.nome: f"{ind.percentual_atingimento:.0f}%" for ind in self.indicadores.values()}, indent=2)}

        Gere uma análise SWOT (Forças, Fraquezas, Oportunidades, Ameaças) em formato JSON:
        {{
            "forcas": ["..."],
            "fraquezas": ["..."],
            "oportunidades": ["..."],
            "ameacas": ["..."],
            "recomendacoes": ["..."]
        }}
        """

        resposta = await self.llm_client.generate(prompt)

        try:
            analise = json.loads(resposta)
        except:
            analise = {
                "forcas": ["Localização privilegiada", "Boa infraestrutura"],
                "fraquezas": ["Necessidade de modernização tecnológica"],
                "oportunidades": ["Investimento em sustentabilidade", "Certificações verdes"],
                "ameacas": ["Novos empreendimentos na região"],
                "recomendacoes": ["Investir em diferenciais tecnológicos"]
            }

        return {
            "status": "success",
            "analise_swot": analise
        }

    async def _criar_campanha(self, context: AgentContext) -> Dict[str, Any]:
        """Cria campanha de marketing"""

        dados = context.metadata.get("dados", {})

        campanha_id = f"CAMP-{datetime.now().strftime('%Y%m%d')}-{len(self.campanhas) + 1:04d}"

        campanha = CampanhaMarketing(
            campanha_id=campanha_id,
            titulo=dados.get("titulo", ""),
            objetivo=dados.get("objetivo", ""),
            publico_alvo=dados.get("publico", "moradores"),
            canais=dados.get("canais", ["app", "email"]),
            conteudos=[],
            data_inicio=datetime.now(),
            data_fim=datetime.now() + timedelta(days=dados.get("duracao_dias", 30)),
            orcamento=dados.get("orcamento", 0),
            resultados={},
            status="ativa"
        )

        self.campanhas[campanha_id] = campanha

        return {
            "status": "success",
            "message": f"Campanha {campanha_id} criada",
            "campanha": {
                "id": campanha_id,
                "titulo": campanha.titulo,
                "publico": campanha.publico_alvo,
                "canais": campanha.canais,
                "duracao": f"{dados.get('duracao_dias', 30)} dias"
            }
        }

    async def _gerar_material(self, context: AgentContext) -> Dict[str, Any]:
        """Gera material de marketing"""

        dados = context.metadata.get("dados", {})
        tipo = dados.get("tipo", "apresentacao")

        if not self.perfil_condominio:
            return {"status": "error", "message": "Perfil não configurado"}

        # Gera conteúdo usando LLM
        prompt = f"""
        Gere um {tipo} de marketing para o condomínio:

        Nome: {self.perfil_condominio.nome}
        Categoria: {self.perfil_condominio.categoria.value}
        Diferenciais: {', '.join(self.perfil_condominio.diferenciais[:5])}
        Áreas comuns: {', '.join([a.get('nome', '') for a in self.perfil_condominio.areas_comuns[:5]])}
        Valor m2: R$ {self.perfil_condominio.valor_m2_atual:,.2f}

        Gere um texto persuasivo destacando os pontos fortes do condomínio.
        """

        conteudo = await self.llm_client.generate(prompt)

        return {
            "status": "success",
            "material": {
                "tipo": tipo,
                "conteudo": conteudo,
                "sugestao_titulo": f"{self.perfil_condominio.nome} - Viva com qualidade",
                "pontos_destaque": self.perfil_condominio.diferenciais[:5]
            }
        }

    async def _listar_diferenciais(self, context: AgentContext) -> Dict[str, Any]:
        """Lista diferenciais do condomínio"""

        if not self.perfil_condominio:
            return {"status": "error", "message": "Perfil não configurado"}

        # Categoriza diferenciais
        categorias = {
            "seguranca": [],
            "lazer": [],
            "sustentabilidade": [],
            "tecnologia": [],
            "comodidade": [],
            "outros": []
        }

        for dif in self.perfil_condominio.diferenciais:
            dif_lower = dif.lower()
            if any(p in dif_lower for p in ["portaria", "cftv", "segurança", "alarme"]):
                categorias["seguranca"].append(dif)
            elif any(p in dif_lower for p in ["piscina", "academia", "salão", "churrasqueira", "playground"]):
                categorias["lazer"].append(dif)
            elif any(p in dif_lower for p in ["solar", "sustent", "água", "reciclagem"]):
                categorias["sustentabilidade"].append(dif)
            elif any(p in dif_lower for p in ["app", "wifi", "automação", "elétrico"]):
                categorias["tecnologia"].append(dif)
            elif any(p in dif_lower for p in ["delivery", "pet", "bicicletário"]):
                categorias["comodidade"].append(dif)
            else:
                categorias["outros"].append(dif)

        return {
            "status": "success",
            "diferenciais": self.perfil_condominio.diferenciais,
            "por_categoria": categorias,
            "total": len(self.perfil_condominio.diferenciais)
        }

    async def _relatorio_valor(self, context: AgentContext) -> Dict[str, Any]:
        """Gera relatório completo de valor"""

        if not self.perfil_condominio:
            return {"status": "error", "message": "Perfil não configurado"}

        # Coleta dados
        avaliacao = await self._avaliar_mercado(context)
        indicadores = await self._avaliar_indicadores(context)
        benchmark = await self._benchmark_regiao(context)

        return {
            "status": "success",
            "relatorio": {
                "titulo": f"Relatório de Valor - {self.perfil_condominio.nome}",
                "data_geracao": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "resumo_executivo": {
                    "valor_m2": f"R$ {self.perfil_condominio.valor_m2_atual:,.2f}",
                    "pontuacao": f"{await self._calcular_pontuacao_geral():.1f}/100",
                    "ranking_regiao": benchmark.get("benchmark", {}).get("posicao", "N/A"),
                    "tendencia": avaliacao.get("avaliacao", {}).get("tendencia", "estável")
                },
                "avaliacao_mercado": avaliacao.get("avaliacao", {}),
                "indicadores": indicadores.get("indicadores", []),
                "benchmark": benchmark.get("benchmark", {}),
                "fatores_positivos": avaliacao.get("fatores_positivos", []),
                "pontos_atencao": avaliacao.get("fatores_negativos", []),
                "projetos_melhoria": len(self.projetos_melhoria)
            }
        }

    async def _relatorio_investidor(self, context: AgentContext) -> Dict[str, Any]:
        """Gera relatório para investidores"""

        if not self.perfil_condominio:
            return {"status": "error", "message": "Perfil não configurado"}

        # Calcula métricas de investimento
        valor_total = self.perfil_condominio.valor_m2_atual * self.perfil_condominio.area_total_construida
        valor_por_unidade = valor_total / self.perfil_condominio.total_unidades

        # Histórico de valorização
        historico = self.perfil_condominio.historico_valores
        valorizacao_acumulada = 0
        if len(historico) >= 2:
            primeiro = historico[0]["valor_m2"]
            ultimo = historico[-1]["valor_m2"]
            valorizacao_acumulada = (ultimo - primeiro) / primeiro * 100

        return {
            "status": "success",
            "relatorio_investidor": {
                "condominio": self.perfil_condominio.nome,
                "categoria": self.perfil_condominio.categoria.value,
                "localizacao": self.perfil_condominio.endereco,
                "metricas_gerais": {
                    "total_unidades": self.perfil_condominio.total_unidades,
                    "area_total": f"{self.perfil_condominio.area_total_construida:,.0f} m²",
                    "valor_m2": f"R$ {self.perfil_condominio.valor_m2_atual:,.2f}",
                    "valor_estimado_total": f"R$ {valor_total:,.2f}",
                    "valor_medio_unidade": f"R$ {valor_por_unidade:,.2f}"
                },
                "performance": {
                    "valorizacao_acumulada": f"{valorizacao_acumulada:+.1f}%",
                    "pontuacao_qualidade": f"{await self._calcular_pontuacao_geral():.1f}/100",
                    "idade_imovel": f"{datetime.now().year - self.perfil_condominio.ano_construcao} anos"
                },
                "diferenciais": self.perfil_condominio.diferenciais[:10],
                "certificacoes": self.perfil_condominio.certificacoes,
                "potencial_valorizacao": {
                    "projetos_planejados": len([p for p in self.projetos_melhoria.values() if p.status == StatusMelhoria.APROVADA]),
                    "investimento_previsto": sum(p.investimento_estimado for p in self.projetos_melhoria.values() if p.status in [StatusMelhoria.APROVADA, StatusMelhoria.EM_EXECUCAO]),
                    "impacto_estimado": f"{sum(p.impacto_valorizacao for p in self.projetos_melhoria.values() if p.status == StatusMelhoria.APROVADA):.1f}%"
                }
            }
        }

    async def _certificacoes(self, context: AgentContext) -> Dict[str, Any]:
        """Gerencia certificações do condomínio"""

        dados = context.metadata.get("dados", {})
        acao = dados.get("acao", "listar")

        if acao == "listar":
            if not self.perfil_condominio:
                return {"status": "error", "message": "Perfil não configurado"}

            # Certificações possíveis
            certificacoes_possiveis = [
                {"nome": "LEED", "categoria": "sustentabilidade", "descricao": "Leadership in Energy and Environmental Design"},
                {"nome": "AQUA-HQE", "categoria": "sustentabilidade", "descricao": "Alta Qualidade Ambiental"},
                {"nome": "ISO 14001", "categoria": "ambiental", "descricao": "Sistema de Gestão Ambiental"},
                {"nome": "Selo Azul CAIXA", "categoria": "sustentabilidade", "descricao": "Construção Sustentável"},
                {"nome": "EDGE", "categoria": "eficiência", "descricao": "Excellence in Design for Greater Efficiencies"},
                {"nome": "WELL", "categoria": "bem-estar", "descricao": "Bem-estar dos ocupantes"},
                {"nome": "Selo Procel", "categoria": "energia", "descricao": "Eficiência Energética"}
            ]

            return {
                "status": "success",
                "certificacoes_atuais": self.perfil_condominio.certificacoes,
                "certificacoes_possiveis": certificacoes_possiveis
            }

        elif acao == "adicionar":
            if not self.perfil_condominio:
                return {"status": "error", "message": "Perfil não configurado"}

            nova_cert = dados.get("certificacao")
            if nova_cert and nova_cert not in self.perfil_condominio.certificacoes:
                self.perfil_condominio.certificacoes.append(nova_cert)

            return {
                "status": "success",
                "message": f"Certificação {nova_cert} adicionada",
                "certificacoes": self.perfil_condominio.certificacoes
            }

        return {"status": "error", "message": "Ação não reconhecida"}

    async def _gerar_dashboard(self, context: AgentContext) -> Dict[str, Any]:
        """Gera dashboard de valorização"""

        if not self.perfil_condominio:
            return {
                "status": "warning",
                "message": "Configure o perfil do condomínio primeiro",
                "dashboard": None
            }

        pontuacao = await self._calcular_pontuacao_geral()

        # Projetos por status
        projetos_status = {}
        for proj in self.projetos_melhoria.values():
            status = proj.status.value
            projetos_status[status] = projetos_status.get(status, 0) + 1

        return {
            "status": "success",
            "dashboard": {
                "valor_mercado": {
                    "valor_m2": f"R$ {self.perfil_condominio.valor_m2_atual:,.2f}",
                    "variacao": "+5.2%",  # Simulado
                    "tendencia": "alta"
                },
                "pontuacao": {
                    "atual": pontuacao,
                    "meta": 85,
                    "evolucao": "+3.5 pts"
                },
                "indicadores_resumo": {
                    "acima_meta": len([i for i in self.indicadores.values() if i.percentual_atingimento >= 80]),
                    "atencao": len([i for i in self.indicadores.values() if 60 <= i.percentual_atingimento < 80]),
                    "critico": len([i for i in self.indicadores.values() if i.percentual_atingimento < 60])
                },
                "projetos_melhoria": {
                    "total": len(self.projetos_melhoria),
                    "por_status": projetos_status,
                    "investimento_planejado": sum(p.investimento_estimado for p in self.projetos_melhoria.values()
                                                  if p.status in [StatusMelhoria.APROVADA, StatusMelhoria.EM_EXECUCAO])
                },
                "estatisticas": self.estatisticas,
                "alertas": {
                    "indicadores_baixos": [i.nome for i in self.indicadores.values() if i.percentual_atingimento < 70],
                    "certificacoes_pendentes": 3 - len(self.perfil_condominio.certificacoes) if len(self.perfil_condominio.certificacoes) < 3 else 0
                }
            }
        }

    async def _processar_chat(self, context: AgentContext) -> Dict[str, Any]:
        """Processa mensagens de chat"""

        mensagem = context.message.lower()

        if any(p in mensagem for p in ["valor", "quanto vale", "m2", "metro"]):
            return await self._calcular_valor_m2(context)

        if any(p in mensagem for p in ["avaliação", "avaliar", "mercado"]):
            return await self._avaliar_mercado(context)

        if any(p in mensagem for p in ["melhoria", "investir", "projeto"]):
            return await self._priorizar_melhorias(context)

        if any(p in mensagem for p in ["benchmark", "comparar", "região"]):
            return await self._benchmark_regiao(context)

        if any(p in mensagem for p in ["indicador", "radar"]):
            return await self._radar_valorizacao(context)

        if any(p in mensagem for p in ["dashboard", "resumo", "status"]):
            return await self._gerar_dashboard(context)

        # Resposta via LLM
        prompt = f"""
        Como agente de valorização imobiliária, responda:

        Pergunta: {context.message}

        Contexto do condomínio:
        - Nome: {self.perfil_condominio.nome if self.perfil_condominio else 'Não configurado'}
        - Valor m2: R$ {self.perfil_condominio.valor_m2_atual if self.perfil_condominio else 0:,.2f}
        - Pontuação: {await self._calcular_pontuacao_geral() if self.perfil_condominio else 0}/100

        Responda de forma objetiva e profissional, focando em valorização imobiliária.
        """

        resposta = await self.llm_client.generate(prompt)

        return {
            "status": "success",
            "response": resposta
        }


def create_property_value_agent(
    memory: UnifiedMemorySystem,
    llm_client: UnifiedLLMClient,
    tools: ToolRegistry,
    rag: Optional[RAGPipeline] = None
) -> PropertyValueAgent:
    """Factory function para criar o agente de valorização"""
    return PropertyValueAgent(memory, llm_client, tools, rag)
