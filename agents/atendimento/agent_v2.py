"""
Agente de Atendimento v2 - Conecta Plus
Central superinteligente - Omnichannel expandido, hub de todos os agentes
Nível 7: Transcendente - Orquestra toda a experiência do morador
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
import uuid
import re

from agents.core.base_agent import BaseAgent, AgentCapability, AgentContext
from agents.core.memory_store import UnifiedMemorySystem
from agents.core.llm_client import UnifiedLLMClient
from agents.core.tools import ToolRegistry
from agents.core.rag_system import RAGPipeline


class CanalAtendimento(Enum):
    """Canais de atendimento disponíveis"""
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"
    APP = "app"
    EMAIL = "email"
    TELEFONE = "telefone"
    INTERFONE = "interfone"
    PRESENCIAL = "presencial"
    CHAT_WEB = "chat_web"
    SMS = "sms"
    ALEXA = "alexa"
    GOOGLE_HOME = "google_home"
    TOTEM = "totem"


class CategoriaAtendimento(Enum):
    """Categorias de atendimento"""
    FINANCEIRO = "financeiro"
    MANUTENCAO = "manutencao"
    SEGURANCA = "seguranca"
    RESERVAS = "reservas"
    ENCOMENDAS = "encomendas"
    OCORRENCIAS = "ocorrencias"
    DOCUMENTOS = "documentos"
    ASSEMBLEIA = "assembleia"
    COMUNICACAO = "comunicacao"
    ACESSO = "acesso"
    DUVIDAS = "duvidas"
    RECLAMACAO = "reclamacao"
    SUGESTAO = "sugestao"
    ELOGIO = "elogio"
    EMERGENCIA = "emergencia"
    OUTROS = "outros"


class PrioridadeAtendimento(Enum):
    """Prioridade do atendimento"""
    CRITICA = "critica"
    ALTA = "alta"
    MEDIA = "media"
    BAIXA = "baixa"


class StatusAtendimento(Enum):
    """Status do atendimento"""
    AGUARDANDO = "aguardando"
    EM_ATENDIMENTO = "em_atendimento"
    AGUARDANDO_USUARIO = "aguardando_usuario"
    AGUARDANDO_AGENTE = "aguardando_agente"
    TRANSFERIDO = "transferido"
    RESOLVIDO = "resolvido"
    FECHADO = "fechado"
    CANCELADO = "cancelado"
    REABERTO = "reaberto"


class SentimentoUsuario(Enum):
    """Sentimento detectado do usuário"""
    MUITO_POSITIVO = "muito_positivo"
    POSITIVO = "positivo"
    NEUTRO = "neutro"
    NEGATIVO = "negativo"
    MUITO_NEGATIVO = "muito_negativo"
    URGENTE = "urgente"


class TipoResposta(Enum):
    """Tipo de resposta"""
    TEXTO = "texto"
    IMAGEM = "imagem"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENTO = "documento"
    BOTOES = "botoes"
    LISTA = "lista"
    CARROSSEL = "carrossel"
    LOCALIZACAO = "localizacao"
    LINK = "link"


@dataclass
class Mensagem:
    """Mensagem do atendimento"""
    mensagem_id: str
    atendimento_id: str
    remetente: str  # usuario, sistema, agente
    conteudo: str
    tipo: TipoResposta
    anexos: List[Dict[str, Any]]
    timestamp: datetime = field(default_factory=datetime.now)
    lida: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Atendimento:
    """Atendimento completo"""
    atendimento_id: str
    protocolo: str
    usuario_id: str
    usuario_nome: str
    unidade: str
    canal: CanalAtendimento
    categoria: CategoriaAtendimento
    subcategoria: Optional[str]
    prioridade: PrioridadeAtendimento
    status: StatusAtendimento
    assunto: str
    mensagens: List[Mensagem]
    agentes_envolvidos: List[str]
    tags: List[str]
    sentimento: SentimentoUsuario
    satisfacao: Optional[int]  # 1-5
    tempo_primeira_resposta: Optional[float]  # segundos
    tempo_resolucao: Optional[float]  # segundos
    data_abertura: datetime = field(default_factory=datetime.now)
    data_primeira_resposta: Optional[datetime] = None
    data_resolucao: Optional[datetime] = None
    data_fechamento: Optional[datetime] = None
    transferencias: List[Dict[str, Any]] = field(default_factory=list)
    intencoes_detectadas: List[str] = field(default_factory=list)
    entidades_extraidas: Dict[str, Any] = field(default_factory=dict)
    contexto_conversa: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FilaAtendimento:
    """Fila de atendimento por categoria"""
    fila_id: str
    categoria: CategoriaAtendimento
    atendimentos: List[str]  # IDs
    agente_responsavel: Optional[str]
    tempo_espera_medio: float
    atendimentos_dia: int
    sla_minutos: int


@dataclass
class PerfilUsuario:
    """Perfil do usuário para personalização"""
    usuario_id: str
    nome: str
    unidade: str
    telefone: str
    email: str
    preferencia_canal: CanalAtendimento
    idioma: str
    historico_atendimentos: List[str]
    satisfacao_media: float
    perfil_comunicacao: str  # formal, informal, tecnico
    horario_preferido: Optional[str]
    tags_interesse: List[str]
    ultima_interacao: datetime


@dataclass
class RespostaRapida:
    """Resposta rápida pré-configurada"""
    resposta_id: str
    titulo: str
    conteudo: str
    categoria: CategoriaAtendimento
    gatilhos: List[str]  # palavras-chave
    variaveis: List[str]  # {nome}, {unidade}, etc.
    uso_count: int
    efetividade: float  # taxa de resolução


@dataclass
class FluxoAtendimento:
    """Fluxo de atendimento automatizado"""
    fluxo_id: str
    nome: str
    categoria: CategoriaAtendimento
    etapas: List[Dict[str, Any]]
    condicoes: Dict[str, Any]
    ativo: bool
    uso_count: int


class ServiceCenterAgent(BaseAgent):
    """
    Agente de Atendimento - Nível 7 Transcendente

    Central Superinteligente que:
    - Recebe todos os contatos de moradores (omnichannel)
    - Classifica e roteia para os agentes especializados
    - Mantém contexto de conversa através de canais
    - Detecta sentimento e urgência
    - Personaliza interações baseado no perfil
    - Orquestra colaboração entre agentes
    - Aprende com cada interação
    - Fornece experiência unificada
    """

    def __init__(
        self,
        memory: UnifiedMemorySystem,
        llm_client: UnifiedLLMClient,
        tools: ToolRegistry,
        rag: Optional[RAGPipeline] = None
    ):
        super().__init__(
            agent_id="service-center-agent",
            name="Central de Atendimento",
            capabilities=[
                AgentCapability.CONVERSATION,
                AgentCapability.ROUTING,
                AgentCapability.SENTIMENT_ANALYSIS,
                AgentCapability.PERSONALIZATION,
                AgentCapability.ORCHESTRATION,
                AgentCapability.OMNICHANNEL
            ],
            memory=memory,
            llm_client=llm_client,
            tools=tools
        )

        self.rag = rag

        # Armazenamento
        self.atendimentos: Dict[str, Atendimento] = {}
        self.filas: Dict[str, FilaAtendimento] = {}
        self.perfis_usuarios: Dict[str, PerfilUsuario] = {}
        self.respostas_rapidas: Dict[str, RespostaRapida] = {}
        self.fluxos: Dict[str, FluxoAtendimento] = {}
        self.sessoes_ativas: Dict[str, Dict[str, Any]] = {}  # usuario_id -> sessao

        # Mapeamento de agentes especializados
        self.agentes_especializados = {
            CategoriaAtendimento.FINANCEIRO: "finance-agent",
            CategoriaAtendimento.MANUTENCAO: "maintenance-agent",
            CategoriaAtendimento.SEGURANCA: "security-agent",
            CategoriaAtendimento.RESERVAS: "reservation-agent",
            CategoriaAtendimento.ENCOMENDAS: "delivery-agent",
            CategoriaAtendimento.OCORRENCIAS: "incident-agent",
            CategoriaAtendimento.ASSEMBLEIA: "assembly-agent",
            CategoriaAtendimento.COMUNICACAO: "communication-agent",
            CategoriaAtendimento.ACESSO: "access-agent",
            CategoriaAtendimento.EMERGENCIA: "emergency-agent",
            CategoriaAtendimento.DUVIDAS: "knowledge-agent",
        }

        # Padrões de detecção de intenção
        self.padroes_intencao = {
            "boleto": CategoriaAtendimento.FINANCEIRO,
            "2a via": CategoriaAtendimento.FINANCEIRO,
            "pagamento": CategoriaAtendimento.FINANCEIRO,
            "inadimplência": CategoriaAtendimento.FINANCEIRO,
            "manutenção": CategoriaAtendimento.MANUTENCAO,
            "conserto": CategoriaAtendimento.MANUTENCAO,
            "vazamento": CategoriaAtendimento.MANUTENCAO,
            "quebrado": CategoriaAtendimento.MANUTENCAO,
            "reserva": CategoriaAtendimento.RESERVAS,
            "salão": CategoriaAtendimento.RESERVAS,
            "churrasqueira": CategoriaAtendimento.RESERVAS,
            "encomenda": CategoriaAtendimento.ENCOMENDAS,
            "entrega": CategoriaAtendimento.ENCOMENDAS,
            "pacote": CategoriaAtendimento.ENCOMENDAS,
            "barulho": CategoriaAtendimento.OCORRENCIAS,
            "reclamação": CategoriaAtendimento.OCORRENCIAS,
            "vizinho": CategoriaAtendimento.OCORRENCIAS,
            "assembleia": CategoriaAtendimento.ASSEMBLEIA,
            "votação": CategoriaAtendimento.ASSEMBLEIA,
            "segurança": CategoriaAtendimento.SEGURANCA,
            "portaria": CategoriaAtendimento.SEGURANCA,
            "visitante": CategoriaAtendimento.ACESSO,
            "liberação": CategoriaAtendimento.ACESSO,
            "emergência": CategoriaAtendimento.EMERGENCIA,
            "urgente": CategoriaAtendimento.EMERGENCIA,
            "incêndio": CategoriaAtendimento.EMERGENCIA,
        }

        # SLAs por categoria (minutos)
        self.slas = {
            CategoriaAtendimento.EMERGENCIA: 1,
            CategoriaAtendimento.SEGURANCA: 5,
            CategoriaAtendimento.FINANCEIRO: 30,
            CategoriaAtendimento.MANUTENCAO: 60,
            CategoriaAtendimento.RESERVAS: 30,
            CategoriaAtendimento.ENCOMENDAS: 15,
            CategoriaAtendimento.OCORRENCIAS: 60,
            CategoriaAtendimento.ASSEMBLEIA: 120,
            CategoriaAtendimento.COMUNICACAO: 60,
            CategoriaAtendimento.ACESSO: 5,
            CategoriaAtendimento.DUVIDAS: 30,
            CategoriaAtendimento.OUTROS: 120,
        }

        # Estatísticas
        self.estatisticas = {
            "atendimentos_total": 0,
            "atendimentos_hoje": 0,
            "tempo_medio_resposta": 0.0,
            "tempo_medio_resolucao": 0.0,
            "satisfacao_media": 0.0,
            "resolucao_primeiro_contato": 0.0,
            "por_canal": {},
            "por_categoria": {}
        }

        # Inicializa filas
        self._inicializar_filas()

    def _inicializar_filas(self):
        """Inicializa filas de atendimento"""
        for categoria in CategoriaAtendimento:
            fila_id = f"FILA-{categoria.value.upper()}"
            self.filas[fila_id] = FilaAtendimento(
                fila_id=fila_id,
                categoria=categoria,
                atendimentos=[],
                agente_responsavel=self.agentes_especializados.get(categoria),
                tempo_espera_medio=0.0,
                atendimentos_dia=0,
                sla_minutos=self.slas.get(categoria, 60)
            )

    async def process(self, context: AgentContext) -> Dict[str, Any]:
        """Processa requisições de atendimento"""

        intent = context.metadata.get("intent", "")

        handlers = {
            # Atendimento principal
            "iniciar_atendimento": self._iniciar_atendimento,
            "processar_mensagem": self._processar_mensagem,
            "encerrar_atendimento": self._encerrar_atendimento,
            "transferir_atendimento": self._transferir_atendimento,

            # Gestão
            "consultar_atendimento": self._consultar_atendimento,
            "historico_usuario": self._historico_usuario,
            "listar_atendimentos": self._listar_atendimentos,
            "avaliar_atendimento": self._avaliar_atendimento,

            # Filas
            "status_filas": self._status_filas,
            "priorizar_atendimento": self._priorizar_atendimento,

            # Configuração
            "criar_resposta_rapida": self._criar_resposta_rapida,
            "criar_fluxo": self._criar_fluxo,

            # Relatórios
            "metricas_atendimento": self._metricas_atendimento,
            "relatorio_satisfacao": self._relatorio_satisfacao,
            "analise_sentimento": self._analise_sentimento_geral,

            # Dashboard
            "dashboard": self._gerar_dashboard,
            "chat": self._processar_chat_principal,
        }

        handler = handlers.get(intent, self._processar_chat_principal)
        return await handler(context)

    async def _iniciar_atendimento(self, context: AgentContext) -> Dict[str, Any]:
        """Inicia novo atendimento"""

        dados = context.metadata.get("dados", {})
        usuario_id = dados.get("usuario_id", context.user_id)
        canal = CanalAtendimento(dados.get("canal", "app"))
        mensagem_inicial = dados.get("mensagem", context.message)

        # Busca ou cria perfil do usuário
        perfil = await self._obter_perfil_usuario(usuario_id)

        # Gera IDs
        atendimento_id = f"ATD-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"
        protocolo = f"{datetime.now().year}{datetime.now().month:02d}{len(self.atendimentos) + 1:06d}"

        # Analisa mensagem inicial
        categoria = await self._classificar_categoria(mensagem_inicial)
        prioridade = await self._definir_prioridade(mensagem_inicial, categoria)
        sentimento = await self._analisar_sentimento(mensagem_inicial)
        intencoes = await self._extrair_intencoes(mensagem_inicial)
        entidades = await self._extrair_entidades(mensagem_inicial)

        # Cria mensagem inicial
        msg = Mensagem(
            mensagem_id=f"MSG-{uuid.uuid4().hex[:8]}",
            atendimento_id=atendimento_id,
            remetente="usuario",
            conteudo=mensagem_inicial,
            tipo=TipoResposta.TEXTO,
            anexos=dados.get("anexos", [])
        )

        # Cria atendimento
        atendimento = Atendimento(
            atendimento_id=atendimento_id,
            protocolo=protocolo,
            usuario_id=usuario_id,
            usuario_nome=perfil.nome if perfil else "Morador",
            unidade=perfil.unidade if perfil else dados.get("unidade", ""),
            canal=canal,
            categoria=categoria,
            subcategoria=dados.get("subcategoria"),
            prioridade=prioridade,
            status=StatusAtendimento.AGUARDANDO,
            assunto=self._extrair_assunto(mensagem_inicial),
            mensagens=[msg],
            agentes_envolvidos=[self.agent_id],
            tags=dados.get("tags", []),
            sentimento=sentimento,
            intencoes_detectadas=intencoes,
            entidades_extraidas=entidades,
            contexto_conversa={"mensagem_inicial": mensagem_inicial}
        )

        self.atendimentos[atendimento_id] = atendimento
        self.estatisticas["atendimentos_total"] += 1
        self.estatisticas["atendimentos_hoje"] += 1

        # Adiciona à fila apropriada
        fila_id = f"FILA-{categoria.value.upper()}"
        if fila_id in self.filas:
            self.filas[fila_id].atendimentos.append(atendimento_id)

        # Atualiza estatísticas por canal e categoria
        canal_key = canal.value
        cat_key = categoria.value
        self.estatisticas["por_canal"][canal_key] = self.estatisticas["por_canal"].get(canal_key, 0) + 1
        self.estatisticas["por_categoria"][cat_key] = self.estatisticas["por_categoria"].get(cat_key, 0) + 1

        # Cria sessão ativa
        self.sessoes_ativas[usuario_id] = {
            "atendimento_id": atendimento_id,
            "canal": canal.value,
            "inicio": datetime.now().isoformat(),
            "contexto": {}
        }

        # Gera resposta de boas-vindas
        resposta = await self._gerar_resposta_inicial(atendimento, perfil)

        # Registra resposta
        msg_resposta = Mensagem(
            mensagem_id=f"MSG-{uuid.uuid4().hex[:8]}",
            atendimento_id=atendimento_id,
            remetente="sistema",
            conteudo=resposta["texto"],
            tipo=TipoResposta(resposta.get("tipo", "texto")),
            anexos=[]
        )
        atendimento.mensagens.append(msg_resposta)
        atendimento.status = StatusAtendimento.EM_ATENDIMENTO
        atendimento.data_primeira_resposta = datetime.now()
        atendimento.tempo_primeira_resposta = (datetime.now() - atendimento.data_abertura).total_seconds()

        # Salva na memória
        await self.memory.store_episodic({
            "event": "atendimento_iniciado",
            "atendimento_id": atendimento_id,
            "protocolo": protocolo,
            "usuario_id": usuario_id,
            "categoria": categoria.value,
            "canal": canal.value,
            "timestamp": datetime.now().isoformat()
        })

        return {
            "status": "success",
            "atendimento": {
                "id": atendimento_id,
                "protocolo": protocolo,
                "categoria": categoria.value,
                "prioridade": prioridade.value,
                "status": atendimento.status.value
            },
            "resposta": resposta,
            "analise": {
                "sentimento": sentimento.value,
                "intencoes": intencoes,
                "entidades": entidades
            }
        }

    async def _obter_perfil_usuario(self, usuario_id: str) -> Optional[PerfilUsuario]:
        """Obtém ou cria perfil do usuário"""

        if usuario_id in self.perfis_usuarios:
            perfil = self.perfis_usuarios[usuario_id]
            perfil.ultima_interacao = datetime.now()
            return perfil

        # Busca dados do usuário em outros agentes
        # Em produção, consultaria banco de dados
        return None

    async def _classificar_categoria(self, mensagem: str) -> CategoriaAtendimento:
        """Classifica categoria da mensagem"""

        mensagem_lower = mensagem.lower()

        # Verifica padrões
        for padrao, categoria in self.padroes_intencao.items():
            if padrao in mensagem_lower:
                return categoria

        # Usa LLM para classificação mais precisa
        prompt = f"""
        Classifique a mensagem do morador na categoria mais apropriada.

        Mensagem: {mensagem}

        Categorias disponíveis:
        - financeiro: boletos, pagamentos, inadimplência
        - manutencao: reparos, consertos, problemas estruturais
        - seguranca: portaria, CFTV, ocorrências de segurança
        - reservas: reserva de áreas comuns
        - encomendas: entregas, pacotes
        - ocorrencias: reclamações, barulho, conflitos
        - assembleia: votações, reuniões
        - acesso: visitantes, liberações
        - emergencia: situações urgentes
        - duvidas: informações gerais

        Responda apenas com o nome da categoria (uma palavra).
        """

        resposta = await self.llm_client.generate(prompt)
        categoria_str = resposta.strip().lower()

        try:
            return CategoriaAtendimento(categoria_str)
        except:
            return CategoriaAtendimento.OUTROS

    async def _definir_prioridade(
        self,
        mensagem: str,
        categoria: CategoriaAtendimento
    ) -> PrioridadeAtendimento:
        """Define prioridade do atendimento"""

        mensagem_lower = mensagem.lower()

        # Prioridade crítica
        if any(p in mensagem_lower for p in ["emergência", "urgente", "incêndio", "vazamento grave", "acidente"]):
            return PrioridadeAtendimento.CRITICA

        # Prioridade por categoria
        if categoria == CategoriaAtendimento.EMERGENCIA:
            return PrioridadeAtendimento.CRITICA

        if categoria in [CategoriaAtendimento.SEGURANCA, CategoriaAtendimento.ACESSO]:
            return PrioridadeAtendimento.ALTA

        # Análise de sentimento urgente
        if any(p in mensagem_lower for p in ["por favor", "preciso", "necessário", "rápido"]):
            return PrioridadeAtendimento.ALTA

        return PrioridadeAtendimento.MEDIA

    async def _analisar_sentimento(self, mensagem: str) -> SentimentoUsuario:
        """Analisa sentimento da mensagem"""

        mensagem_lower = mensagem.lower()

        # Indicadores de urgência
        if any(p in mensagem_lower for p in ["socorro", "emergência", "urgente", "ajuda"]):
            return SentimentoUsuario.URGENTE

        # Indicadores negativos
        indicadores_negativos = ["absurdo", "péssimo", "horrível", "inaceitável", "vergonha", "raiva"]
        if sum(1 for p in indicadores_negativos if p in mensagem_lower) >= 2:
            return SentimentoUsuario.MUITO_NEGATIVO

        if any(p in mensagem_lower for p in ["ruim", "problema", "reclamação", "insatisfeito"]):
            return SentimentoUsuario.NEGATIVO

        # Indicadores positivos
        if any(p in mensagem_lower for p in ["ótimo", "excelente", "parabéns", "maravilhoso"]):
            return SentimentoUsuario.MUITO_POSITIVO

        if any(p in mensagem_lower for p in ["bom", "obrigado", "agradeço"]):
            return SentimentoUsuario.POSITIVO

        return SentimentoUsuario.NEUTRO

    async def _extrair_intencoes(self, mensagem: str) -> List[str]:
        """Extrai intenções da mensagem"""

        intencoes = []
        mensagem_lower = mensagem.lower()

        mapeamento = {
            "consultar": ["quanto", "qual", "quando", "onde", "como está"],
            "solicitar": ["preciso", "quero", "gostaria", "poderia"],
            "reclamar": ["reclamação", "problema", "não funciona", "ruim"],
            "reservar": ["reservar", "agendar", "marcar"],
            "pagar": ["pagar", "boleto", "2a via", "quitação"],
            "informar": ["informo", "aviso", "comunico"],
            "cancelar": ["cancelar", "desistir", "não quero mais"]
        }

        for intencao, gatilhos in mapeamento.items():
            if any(g in mensagem_lower for g in gatilhos):
                intencoes.append(intencao)

        return intencoes if intencoes else ["consultar"]

    async def _extrair_entidades(self, mensagem: str) -> Dict[str, Any]:
        """Extrai entidades da mensagem"""

        entidades = {}

        # Extrai datas
        datas = re.findall(r'\d{1,2}/\d{1,2}(?:/\d{2,4})?', mensagem)
        if datas:
            entidades["datas"] = datas

        # Extrai valores monetários
        valores = re.findall(r'R\$\s*[\d.,]+|[\d.,]+\s*reais', mensagem)
        if valores:
            entidades["valores"] = valores

        # Extrai números de unidade/apto
        unidades = re.findall(r'(?:apt[oa]?|unidade|bloco)\s*\d+', mensagem, re.IGNORECASE)
        if unidades:
            entidades["unidades"] = unidades

        # Extrai horários
        horarios = re.findall(r'\d{1,2}:\d{2}|\d{1,2}\s*(?:h|horas?)', mensagem)
        if horarios:
            entidades["horarios"] = horarios

        # Extrai telefones
        telefones = re.findall(r'\(?[0-9]{2}\)?\s*[0-9]{4,5}-?[0-9]{4}', mensagem)
        if telefones:
            entidades["telefones"] = telefones

        return entidades

    def _extrair_assunto(self, mensagem: str) -> str:
        """Extrai assunto resumido da mensagem"""
        # Pega as primeiras palavras significativas
        palavras = mensagem.split()[:10]
        assunto = " ".join(palavras)
        if len(assunto) > 50:
            assunto = assunto[:47] + "..."
        return assunto

    async def _gerar_resposta_inicial(
        self,
        atendimento: Atendimento,
        perfil: Optional[PerfilUsuario]
    ) -> Dict[str, Any]:
        """Gera resposta inicial personalizada"""

        nome = perfil.nome.split()[0] if perfil else "Morador"

        # Saudação baseada no horário
        hora = datetime.now().hour
        if hora < 12:
            saudacao = "Bom dia"
        elif hora < 18:
            saudacao = "Boa tarde"
        else:
            saudacao = "Boa noite"

        # Mensagem baseada na categoria
        mensagens_categoria = {
            CategoriaAtendimento.FINANCEIRO: "Entendi que você tem uma questão financeira.",
            CategoriaAtendimento.MANUTENCAO: "Entendi que você precisa de manutenção.",
            CategoriaAtendimento.RESERVAS: "Entendi que você deseja fazer uma reserva.",
            CategoriaAtendimento.ENCOMENDAS: "Entendi que você tem uma questão sobre encomendas.",
            CategoriaAtendimento.EMERGENCIA: "Entendi que é uma situação de emergência. Estou priorizando seu atendimento!",
            CategoriaAtendimento.OCORRENCIAS: "Entendi que você deseja registrar uma ocorrência.",
            CategoriaAtendimento.ACESSO: "Entendi que você precisa de uma liberação de acesso.",
        }

        mensagem_especifica = mensagens_categoria.get(
            atendimento.categoria,
            "Entendi sua solicitação."
        )

        # Monta resposta
        resposta = f"""{saudacao}, {nome}! 👋

{mensagem_especifica}

📋 Seu protocolo é: **{atendimento.protocolo}**

Como posso ajudar especificamente?"""

        # Adiciona opções se aplicável
        opcoes = await self._gerar_opcoes_rapidas(atendimento.categoria)

        return {
            "texto": resposta,
            "tipo": "botoes" if opcoes else "texto",
            "opcoes": opcoes
        }

    async def _gerar_opcoes_rapidas(self, categoria: CategoriaAtendimento) -> List[Dict[str, str]]:
        """Gera opções rápidas baseadas na categoria"""

        opcoes = {
            CategoriaAtendimento.FINANCEIRO: [
                {"label": "💳 2ª via boleto", "value": "2via_boleto"},
                {"label": "📊 Extrato", "value": "extrato"},
                {"label": "💬 Falar com atendente", "value": "atendente"}
            ],
            CategoriaAtendimento.MANUTENCAO: [
                {"label": "🔧 Abrir chamado", "value": "abrir_chamado"},
                {"label": "📋 Consultar chamado", "value": "consultar_chamado"},
                {"label": "💬 Falar com atendente", "value": "atendente"}
            ],
            CategoriaAtendimento.RESERVAS: [
                {"label": "📅 Nova reserva", "value": "nova_reserva"},
                {"label": "📋 Minhas reservas", "value": "minhas_reservas"},
                {"label": "❌ Cancelar reserva", "value": "cancelar_reserva"}
            ],
            CategoriaAtendimento.ENCOMENDAS: [
                {"label": "📦 Minhas encomendas", "value": "minhas_encomendas"},
                {"label": "🔔 Alertas de entrega", "value": "alertas_entrega"},
                {"label": "💬 Falar com portaria", "value": "portaria"}
            ]
        }

        return opcoes.get(categoria, [{"label": "💬 Falar com atendente", "value": "atendente"}])

    async def _processar_mensagem(self, context: AgentContext) -> Dict[str, Any]:
        """Processa mensagem em atendimento existente"""

        dados = context.metadata.get("dados", {})
        atendimento_id = dados.get("atendimento_id")
        mensagem = dados.get("mensagem", context.message)
        usuario_id = dados.get("usuario_id", context.user_id)

        # Se não informou ID, busca atendimento ativo do usuário
        if not atendimento_id:
            sessao = self.sessoes_ativas.get(usuario_id)
            if sessao:
                atendimento_id = sessao.get("atendimento_id")

        if not atendimento_id or atendimento_id not in self.atendimentos:
            # Inicia novo atendimento
            return await self._iniciar_atendimento(context)

        atendimento = self.atendimentos[atendimento_id]

        # Registra mensagem do usuário
        msg = Mensagem(
            mensagem_id=f"MSG-{uuid.uuid4().hex[:8]}",
            atendimento_id=atendimento_id,
            remetente="usuario",
            conteudo=mensagem,
            tipo=TipoResposta.TEXTO,
            anexos=dados.get("anexos", [])
        )
        atendimento.mensagens.append(msg)

        # Atualiza análises
        sentimento = await self._analisar_sentimento(mensagem)
        atendimento.sentimento = sentimento

        novas_intencoes = await self._extrair_intencoes(mensagem)
        atendimento.intencoes_detectadas.extend(novas_intencoes)

        novas_entidades = await self._extrair_entidades(mensagem)
        atendimento.entidades_extraidas.update(novas_entidades)

        # Verifica se precisa reclassificar categoria
        nova_categoria = await self._classificar_categoria(mensagem)
        if nova_categoria != atendimento.categoria and nova_categoria != CategoriaAtendimento.OUTROS:
            # Transfere para nova categoria
            atendimento.categoria = nova_categoria

        # Verifica opções rápidas
        if mensagem.lower() in ["2via_boleto", "extrato", "abrir_chamado", "nova_reserva"]:
            return await self._processar_opcao_rapida(atendimento, mensagem.lower())

        # Verifica se deve rotear para agente especializado
        agente_especializado = self.agentes_especializados.get(atendimento.categoria)

        if agente_especializado and self._deve_rotear(atendimento, mensagem):
            # Roteia para agente especializado
            resposta_agente = await self.send_message(
                agente_especializado,
                {
                    "tipo": "atendimento",
                    "atendimento_id": atendimento_id,
                    "usuario_id": usuario_id,
                    "mensagem": mensagem,
                    "contexto": atendimento.contexto_conversa,
                    "entidades": atendimento.entidades_extraidas
                }
            )

            resposta_texto = resposta_agente.get("response", "Estou processando sua solicitação...")
        else:
            # Gera resposta diretamente
            resposta_texto = await self._gerar_resposta_contextual(atendimento, mensagem)

        # Registra resposta do sistema
        msg_resposta = Mensagem(
            mensagem_id=f"MSG-{uuid.uuid4().hex[:8]}",
            atendimento_id=atendimento_id,
            remetente="sistema",
            conteudo=resposta_texto,
            tipo=TipoResposta.TEXTO,
            anexos=[]
        )
        atendimento.mensagens.append(msg_resposta)

        # Atualiza status
        atendimento.status = StatusAtendimento.EM_ATENDIMENTO

        return {
            "status": "success",
            "atendimento_id": atendimento_id,
            "resposta": {
                "texto": resposta_texto,
                "tipo": "texto"
            },
            "analise": {
                "sentimento": sentimento.value,
                "categoria": atendimento.categoria.value
            }
        }

    def _deve_rotear(self, atendimento: Atendimento, mensagem: str) -> bool:
        """Verifica se deve rotear para agente especializado"""

        # Sempre roteia categorias críticas
        if atendimento.categoria in [CategoriaAtendimento.EMERGENCIA, CategoriaAtendimento.SEGURANCA]:
            return True

        # Roteia se detectou intenções específicas
        intencoes_acao = ["solicitar", "reservar", "pagar", "cancelar"]
        if any(i in atendimento.intencoes_detectadas for i in intencoes_acao):
            return True

        # Roteia após 2 mensagens
        if len(atendimento.mensagens) >= 4:  # 2 do usuário, 2 do sistema
            return True

        return False

    async def _processar_opcao_rapida(
        self,
        atendimento: Atendimento,
        opcao: str
    ) -> Dict[str, Any]:
        """Processa opção rápida selecionada"""

        respostas = {
            "2via_boleto": "Vou gerar sua 2ª via do boleto. Um momento...",
            "extrato": "Gerando seu extrato financeiro...",
            "abrir_chamado": "Vamos abrir um chamado de manutenção. Descreva o problema:",
            "nova_reserva": "Vou ajudar você a fazer uma reserva. Qual área você deseja reservar?",
            "minhas_reservas": "Consultando suas reservas...",
            "minhas_encomendas": "Consultando suas encomendas..."
        }

        resposta = respostas.get(opcao, "Processando sua solicitação...")

        # Aciona agente especializado
        agente = self.agentes_especializados.get(atendimento.categoria)
        if agente:
            await self.send_message(
                agente,
                {
                    "acao": opcao,
                    "usuario_id": atendimento.usuario_id,
                    "atendimento_id": atendimento.atendimento_id
                }
            )

        return {
            "status": "success",
            "resposta": {"texto": resposta, "tipo": "texto"}
        }

    async def _gerar_resposta_contextual(
        self,
        atendimento: Atendimento,
        mensagem: str
    ) -> str:
        """Gera resposta contextual usando LLM"""

        # Monta contexto da conversa
        historico = "\n".join([
            f"{'Morador' if m.remetente == 'usuario' else 'Atendimento'}: {m.conteudo}"
            for m in atendimento.mensagens[-6:]  # Últimas 6 mensagens
        ])

        prompt = f"""
        Você é o assistente virtual de um condomínio. Responda de forma educada, objetiva e prestativa.

        Informações do morador:
        - Nome: {atendimento.usuario_nome}
        - Unidade: {atendimento.unidade}
        - Categoria do atendimento: {atendimento.categoria.value}
        - Sentimento detectado: {atendimento.sentimento.value}

        Histórico da conversa:
        {historico}

        Nova mensagem do morador: {mensagem}

        Instruções:
        - Seja educado e empático
        - Se o sentimento for negativo, demonstre compreensão
        - Forneça informações úteis
        - Se não souber responder, direcione para o canal apropriado
        - Mantenha respostas concisas (máximo 3 parágrafos)
        """

        resposta = await self.llm_client.generate(prompt)

        return resposta.strip()

    async def _encerrar_atendimento(self, context: AgentContext) -> Dict[str, Any]:
        """Encerra atendimento"""

        dados = context.metadata.get("dados", {})
        atendimento_id = dados.get("atendimento_id")

        if atendimento_id not in self.atendimentos:
            return {"status": "error", "message": "Atendimento não encontrado"}

        atendimento = self.atendimentos[atendimento_id]

        atendimento.status = StatusAtendimento.RESOLVIDO
        atendimento.data_resolucao = datetime.now()
        atendimento.tempo_resolucao = (datetime.now() - atendimento.data_abertura).total_seconds()

        # Remove da fila
        fila_id = f"FILA-{atendimento.categoria.value.upper()}"
        if fila_id in self.filas:
            if atendimento_id in self.filas[fila_id].atendimentos:
                self.filas[fila_id].atendimentos.remove(atendimento_id)

        # Remove sessão ativa
        if atendimento.usuario_id in self.sessoes_ativas:
            del self.sessoes_ativas[atendimento.usuario_id]

        # Atualiza estatísticas
        self._atualizar_estatisticas(atendimento)

        # Solicita avaliação
        mensagem_encerramento = f"""
Seu atendimento foi concluído! ✅

📋 Protocolo: {atendimento.protocolo}
⏱️ Tempo total: {int(atendimento.tempo_resolucao / 60)} minutos

Como você avalia este atendimento?
        """

        return {
            "status": "success",
            "message": "Atendimento encerrado",
            "atendimento": {
                "id": atendimento_id,
                "protocolo": atendimento.protocolo,
                "tempo_resolucao": f"{int(atendimento.tempo_resolucao / 60)} min"
            },
            "resposta": {
                "texto": mensagem_encerramento,
                "tipo": "botoes",
                "opcoes": [
                    {"label": "⭐⭐⭐⭐⭐ Excelente", "value": "5"},
                    {"label": "⭐⭐⭐⭐ Bom", "value": "4"},
                    {"label": "⭐⭐⭐ Regular", "value": "3"},
                    {"label": "⭐⭐ Ruim", "value": "2"},
                    {"label": "⭐ Péssimo", "value": "1"}
                ]
            }
        }

    def _atualizar_estatisticas(self, atendimento: Atendimento):
        """Atualiza estatísticas com base no atendimento"""

        # Tempo médio de resposta
        if atendimento.tempo_primeira_resposta:
            total = self.estatisticas["atendimentos_total"]
            media_atual = self.estatisticas["tempo_medio_resposta"]
            nova_media = ((media_atual * (total - 1)) + atendimento.tempo_primeira_resposta) / total
            self.estatisticas["tempo_medio_resposta"] = nova_media

        # Tempo médio de resolução
        if atendimento.tempo_resolucao:
            total = self.estatisticas["atendimentos_total"]
            media_atual = self.estatisticas["tempo_medio_resolucao"]
            nova_media = ((media_atual * (total - 1)) + atendimento.tempo_resolucao) / total
            self.estatisticas["tempo_medio_resolucao"] = nova_media

    async def _transferir_atendimento(self, context: AgentContext) -> Dict[str, Any]:
        """Transfere atendimento para outro agente/setor"""

        dados = context.metadata.get("dados", {})
        atendimento_id = dados.get("atendimento_id")
        destino = dados.get("destino")
        motivo = dados.get("motivo", "Transferido pelo sistema")

        if atendimento_id not in self.atendimentos:
            return {"status": "error", "message": "Atendimento não encontrado"}

        atendimento = self.atendimentos[atendimento_id]

        # Registra transferência
        atendimento.transferencias.append({
            "origem": atendimento.categoria.value,
            "destino": destino,
            "motivo": motivo,
            "timestamp": datetime.now().isoformat()
        })

        # Atualiza categoria se for outro setor
        try:
            nova_categoria = CategoriaAtendimento(destino)
            atendimento.categoria = nova_categoria
        except:
            pass

        atendimento.status = StatusAtendimento.TRANSFERIDO

        # Notifica agente de destino
        agente_destino = self.agentes_especializados.get(
            CategoriaAtendimento(destino) if destino in [c.value for c in CategoriaAtendimento] else None
        )

        if agente_destino:
            await self.send_message(
                agente_destino,
                {
                    "tipo": "transferencia",
                    "atendimento_id": atendimento_id,
                    "usuario_id": atendimento.usuario_id,
                    "contexto": atendimento.contexto_conversa,
                    "mensagens": [{"remetente": m.remetente, "conteudo": m.conteudo} for m in atendimento.mensagens]
                }
            )

        return {
            "status": "success",
            "message": f"Atendimento transferido para {destino}",
            "resposta": {
                "texto": f"Seu atendimento foi transferido para o setor de {destino}. Um especialista continuará em breve."
            }
        }

    async def _consultar_atendimento(self, context: AgentContext) -> Dict[str, Any]:
        """Consulta detalhes de um atendimento"""

        dados = context.metadata.get("dados", {})
        atendimento_id = dados.get("atendimento_id")
        protocolo = dados.get("protocolo")

        # Busca por protocolo
        if protocolo:
            for atd in self.atendimentos.values():
                if atd.protocolo == protocolo:
                    atendimento_id = atd.atendimento_id
                    break

        if not atendimento_id or atendimento_id not in self.atendimentos:
            return {"status": "error", "message": "Atendimento não encontrado"}

        atd = self.atendimentos[atendimento_id]

        return {
            "status": "success",
            "atendimento": {
                "id": atd.atendimento_id,
                "protocolo": atd.protocolo,
                "usuario": atd.usuario_nome,
                "unidade": atd.unidade,
                "categoria": atd.categoria.value,
                "status": atd.status.value,
                "prioridade": atd.prioridade.value,
                "assunto": atd.assunto,
                "canal": atd.canal.value,
                "data_abertura": atd.data_abertura.strftime("%d/%m/%Y %H:%M"),
                "mensagens": len(atd.mensagens),
                "satisfacao": atd.satisfacao
            }
        }

    async def _historico_usuario(self, context: AgentContext) -> Dict[str, Any]:
        """Retorna histórico de atendimentos do usuário"""

        dados = context.metadata.get("dados", {})
        usuario_id = dados.get("usuario_id", context.user_id)

        atendimentos_usuario = []

        for atd in self.atendimentos.values():
            if atd.usuario_id == usuario_id:
                atendimentos_usuario.append({
                    "id": atd.atendimento_id,
                    "protocolo": atd.protocolo,
                    "categoria": atd.categoria.value,
                    "status": atd.status.value,
                    "assunto": atd.assunto,
                    "data": atd.data_abertura.strftime("%d/%m/%Y"),
                    "satisfacao": atd.satisfacao
                })

        # Ordena por data (mais recente primeiro)
        atendimentos_usuario.sort(key=lambda x: x["data"], reverse=True)

        return {
            "status": "success",
            "usuario_id": usuario_id,
            "atendimentos": atendimentos_usuario[:20],  # Últimos 20
            "total": len(atendimentos_usuario)
        }

    async def _listar_atendimentos(self, context: AgentContext) -> Dict[str, Any]:
        """Lista atendimentos (para gestão)"""

        dados = context.metadata.get("dados", {})
        status_filtro = dados.get("status")
        categoria_filtro = dados.get("categoria")
        limite = dados.get("limite", 50)

        atendimentos_filtrados = []

        for atd in self.atendimentos.values():
            if status_filtro and atd.status.value != status_filtro:
                continue
            if categoria_filtro and atd.categoria.value != categoria_filtro:
                continue

            atendimentos_filtrados.append({
                "id": atd.atendimento_id,
                "protocolo": atd.protocolo,
                "usuario": atd.usuario_nome,
                "categoria": atd.categoria.value,
                "status": atd.status.value,
                "prioridade": atd.prioridade.value,
                "canal": atd.canal.value,
                "data": atd.data_abertura.strftime("%d/%m/%Y %H:%M"),
                "sentimento": atd.sentimento.value
            })

        # Ordena por prioridade e data
        prioridade_ordem = {"critica": 0, "alta": 1, "media": 2, "baixa": 3}
        atendimentos_filtrados.sort(key=lambda x: (prioridade_ordem.get(x["prioridade"], 2), x["data"]))

        return {
            "status": "success",
            "atendimentos": atendimentos_filtrados[:limite],
            "total": len(atendimentos_filtrados)
        }

    async def _avaliar_atendimento(self, context: AgentContext) -> Dict[str, Any]:
        """Registra avaliação do atendimento"""

        dados = context.metadata.get("dados", {})
        atendimento_id = dados.get("atendimento_id")
        nota = dados.get("nota")
        comentario = dados.get("comentario")

        if atendimento_id not in self.atendimentos:
            return {"status": "error", "message": "Atendimento não encontrado"}

        if not nota or nota < 1 or nota > 5:
            return {"status": "error", "message": "Nota deve ser entre 1 e 5"}

        atendimento = self.atendimentos[atendimento_id]
        atendimento.satisfacao = nota
        atendimento.status = StatusAtendimento.FECHADO
        atendimento.data_fechamento = datetime.now()

        # Atualiza satisfação média
        notas = [a.satisfacao for a in self.atendimentos.values() if a.satisfacao]
        self.estatisticas["satisfacao_media"] = sum(notas) / len(notas) if notas else 0

        mensagem_agradecimento = "Obrigado pelo seu feedback! " + (
            "😊 Que bom que conseguimos ajudar!" if nota >= 4 else
            "Vamos trabalhar para melhorar!" if nota <= 2 else
            "Sua opinião é muito importante para nós."
        )

        return {
            "status": "success",
            "message": "Avaliação registrada",
            "resposta": {
                "texto": mensagem_agradecimento
            }
        }

    async def _status_filas(self, context: AgentContext) -> Dict[str, Any]:
        """Retorna status das filas de atendimento"""

        status_filas = []

        for fila in self.filas.values():
            atendimentos_em_fila = len(fila.atendimentos)

            status_filas.append({
                "fila": fila.categoria.value,
                "em_espera": atendimentos_em_fila,
                "sla_minutos": fila.sla_minutos,
                "tempo_espera_medio": f"{fila.tempo_espera_medio:.0f} min",
                "status": "OK" if atendimentos_em_fila == 0 else "ATENÇÃO" if atendimentos_em_fila < 5 else "CRÍTICO"
            })

        # Ordena por quantidade em espera
        status_filas.sort(key=lambda x: x["em_espera"], reverse=True)

        return {
            "status": "success",
            "filas": status_filas,
            "total_em_espera": sum(f["em_espera"] for f in status_filas)
        }

    async def _priorizar_atendimento(self, context: AgentContext) -> Dict[str, Any]:
        """Prioriza atendimento na fila"""

        dados = context.metadata.get("dados", {})
        atendimento_id = dados.get("atendimento_id")
        nova_prioridade = PrioridadeAtendimento(dados.get("prioridade", "alta"))

        if atendimento_id not in self.atendimentos:
            return {"status": "error", "message": "Atendimento não encontrado"}

        atendimento = self.atendimentos[atendimento_id]
        atendimento.prioridade = nova_prioridade

        return {
            "status": "success",
            "message": f"Atendimento priorizado como {nova_prioridade.value}"
        }

    async def _criar_resposta_rapida(self, context: AgentContext) -> Dict[str, Any]:
        """Cria resposta rápida"""

        dados = context.metadata.get("dados", {})

        resposta_id = f"RESP-{len(self.respostas_rapidas) + 1:04d}"

        resposta = RespostaRapida(
            resposta_id=resposta_id,
            titulo=dados.get("titulo", ""),
            conteudo=dados.get("conteudo", ""),
            categoria=CategoriaAtendimento(dados.get("categoria", "outros")),
            gatilhos=dados.get("gatilhos", []),
            variaveis=dados.get("variaveis", []),
            uso_count=0,
            efetividade=0.0
        )

        self.respostas_rapidas[resposta_id] = resposta

        return {
            "status": "success",
            "message": f"Resposta rápida {resposta_id} criada",
            "resposta_rapida": {
                "id": resposta_id,
                "titulo": resposta.titulo,
                "gatilhos": resposta.gatilhos
            }
        }

    async def _criar_fluxo(self, context: AgentContext) -> Dict[str, Any]:
        """Cria fluxo de atendimento automatizado"""

        dados = context.metadata.get("dados", {})

        fluxo_id = f"FLUXO-{len(self.fluxos) + 1:04d}"

        fluxo = FluxoAtendimento(
            fluxo_id=fluxo_id,
            nome=dados.get("nome", ""),
            categoria=CategoriaAtendimento(dados.get("categoria", "outros")),
            etapas=dados.get("etapas", []),
            condicoes=dados.get("condicoes", {}),
            ativo=True,
            uso_count=0
        )

        self.fluxos[fluxo_id] = fluxo

        return {
            "status": "success",
            "message": f"Fluxo {fluxo_id} criado",
            "fluxo": {
                "id": fluxo_id,
                "nome": fluxo.nome,
                "etapas": len(fluxo.etapas)
            }
        }

    async def _metricas_atendimento(self, context: AgentContext) -> Dict[str, Any]:
        """Retorna métricas de atendimento"""

        dados = context.metadata.get("dados", {})
        periodo = dados.get("periodo", "hoje")

        # Filtra atendimentos do período
        hoje = datetime.now().date()

        if periodo == "hoje":
            inicio = datetime.combine(hoje, datetime.min.time())
        elif periodo == "semana":
            inicio = datetime.combine(hoje - timedelta(days=7), datetime.min.time())
        elif periodo == "mes":
            inicio = datetime.combine(hoje.replace(day=1), datetime.min.time())
        else:
            inicio = datetime.min

        atendimentos_periodo = [
            a for a in self.atendimentos.values()
            if a.data_abertura >= inicio
        ]

        total = len(atendimentos_periodo)

        if total == 0:
            return {
                "status": "success",
                "periodo": periodo,
                "metricas": {"total": 0}
            }

        # Calcula métricas
        resolvidos = len([a for a in atendimentos_periodo if a.status in [StatusAtendimento.RESOLVIDO, StatusAtendimento.FECHADO]])
        tempo_resposta = [a.tempo_primeira_resposta for a in atendimentos_periodo if a.tempo_primeira_resposta]
        tempo_resolucao = [a.tempo_resolucao for a in atendimentos_periodo if a.tempo_resolucao]
        satisfacoes = [a.satisfacao for a in atendimentos_periodo if a.satisfacao]

        # Por categoria
        por_categoria = {}
        for a in atendimentos_periodo:
            cat = a.categoria.value
            por_categoria[cat] = por_categoria.get(cat, 0) + 1

        # Por canal
        por_canal = {}
        for a in atendimentos_periodo:
            canal = a.canal.value
            por_canal[canal] = por_canal.get(canal, 0) + 1

        # Por sentimento
        por_sentimento = {}
        for a in atendimentos_periodo:
            sent = a.sentimento.value
            por_sentimento[sent] = por_sentimento.get(sent, 0) + 1

        return {
            "status": "success",
            "periodo": periodo,
            "metricas": {
                "total": total,
                "resolvidos": resolvidos,
                "taxa_resolucao": f"{(resolvidos/total*100):.1f}%",
                "tempo_medio_resposta": f"{sum(tempo_resposta)/len(tempo_resposta)/60:.1f} min" if tempo_resposta else "N/A",
                "tempo_medio_resolucao": f"{sum(tempo_resolucao)/len(tempo_resolucao)/60:.1f} min" if tempo_resolucao else "N/A",
                "satisfacao_media": f"{sum(satisfacoes)/len(satisfacoes):.1f}" if satisfacoes else "N/A",
                "por_categoria": por_categoria,
                "por_canal": por_canal,
                "por_sentimento": por_sentimento
            }
        }

    async def _relatorio_satisfacao(self, context: AgentContext) -> Dict[str, Any]:
        """Gera relatório de satisfação"""

        # Coleta avaliações
        avaliacoes = [a for a in self.atendimentos.values() if a.satisfacao]

        if not avaliacoes:
            return {
                "status": "success",
                "relatorio": {"total_avaliacoes": 0}
            }

        # Distribuição de notas
        distribuicao = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for a in avaliacoes:
            distribuicao[a.satisfacao] += 1

        # NPS (Net Promoter Score)
        promotores = distribuicao[5] + distribuicao[4]
        detratores = distribuicao[1] + distribuicao[2]
        total = len(avaliacoes)
        nps = ((promotores - detratores) / total * 100) if total > 0 else 0

        # Por categoria
        por_categoria = {}
        for a in avaliacoes:
            cat = a.categoria.value
            if cat not in por_categoria:
                por_categoria[cat] = []
            por_categoria[cat].append(a.satisfacao)

        media_categoria = {
            cat: sum(notas)/len(notas)
            for cat, notas in por_categoria.items()
        }

        return {
            "status": "success",
            "relatorio": {
                "total_avaliacoes": total,
                "media_geral": sum(a.satisfacao for a in avaliacoes) / total,
                "nps": f"{nps:.0f}",
                "distribuicao": distribuicao,
                "por_categoria": media_categoria,
                "promotores": f"{promotores/total*100:.0f}%",
                "detratores": f"{detratores/total*100:.0f}%"
            }
        }

    async def _analise_sentimento_geral(self, context: AgentContext) -> Dict[str, Any]:
        """Análise de sentimento dos atendimentos"""

        sentimentos = {}
        for a in self.atendimentos.values():
            sent = a.sentimento.value
            sentimentos[sent] = sentimentos.get(sent, 0) + 1

        total = sum(sentimentos.values())

        analise = {
            sent: f"{count/total*100:.1f}%" if total > 0 else "0%"
            for sent, count in sentimentos.items()
        }

        return {
            "status": "success",
            "analise_sentimento": {
                "distribuicao": analise,
                "total_analisados": total,
                "predominante": max(sentimentos, key=sentimentos.get) if sentimentos else "neutro"
            }
        }

    async def _gerar_dashboard(self, context: AgentContext) -> Dict[str, Any]:
        """Gera dashboard da central de atendimento"""

        agora = datetime.now()
        hoje = agora.date()

        # Atendimentos hoje
        atd_hoje = [a for a in self.atendimentos.values()
                   if a.data_abertura.date() == hoje]

        # Em andamento
        em_andamento = len([a for a in self.atendimentos.values()
                          if a.status in [StatusAtendimento.EM_ATENDIMENTO, StatusAtendimento.AGUARDANDO]])

        # Filas
        total_em_fila = sum(len(f.atendimentos) for f in self.filas.values())

        # Críticos (alta prioridade ou emergência)
        criticos = len([a for a in self.atendimentos.values()
                       if a.status not in [StatusAtendimento.RESOLVIDO, StatusAtendimento.FECHADO, StatusAtendimento.CANCELADO]
                       and a.prioridade in [PrioridadeAtendimento.CRITICA, PrioridadeAtendimento.ALTA]])

        # Satisfação média
        satisfacoes = [a.satisfacao for a in self.atendimentos.values() if a.satisfacao]
        satisfacao_media = sum(satisfacoes) / len(satisfacoes) if satisfacoes else 0

        # Top categorias hoje
        categorias_hoje = {}
        for a in atd_hoje:
            cat = a.categoria.value
            categorias_hoje[cat] = categorias_hoje.get(cat, 0) + 1

        top_categorias = sorted(categorias_hoje.items(), key=lambda x: x[1], reverse=True)[:5]

        return {
            "status": "success",
            "dashboard": {
                "resumo": {
                    "atendimentos_hoje": len(atd_hoje),
                    "em_andamento": em_andamento,
                    "aguardando_fila": total_em_fila,
                    "criticos": criticos,
                    "sessoes_ativas": len(self.sessoes_ativas)
                },
                "metricas": {
                    "tempo_medio_resposta": f"{self.estatisticas['tempo_medio_resposta']/60:.1f} min",
                    "tempo_medio_resolucao": f"{self.estatisticas['tempo_medio_resolucao']/60:.1f} min",
                    "satisfacao_media": f"{satisfacao_media:.1f}/5",
                    "total_atendimentos": self.estatisticas["atendimentos_total"]
                },
                "top_categorias": top_categorias,
                "por_canal": self.estatisticas["por_canal"],
                "alertas": {
                    "sla_critico": total_em_fila > 10,
                    "satisfacao_baixa": satisfacao_media < 3.5,
                    "muitos_criticos": criticos > 5
                }
            }
        }

    async def _processar_chat_principal(self, context: AgentContext) -> Dict[str, Any]:
        """Processa mensagem de chat - ponto de entrada principal"""

        # Verifica se é um novo atendimento ou continuação
        usuario_id = context.user_id
        mensagem = context.message

        # Verifica sessão ativa
        sessao = self.sessoes_ativas.get(usuario_id)

        if sessao:
            # Continua atendimento existente
            return await self._processar_mensagem(AgentContext(
                user_id=usuario_id,
                session_id=context.session_id,
                message=mensagem,
                metadata={
                    "dados": {
                        "atendimento_id": sessao.get("atendimento_id"),
                        "mensagem": mensagem
                    }
                }
            ))
        else:
            # Inicia novo atendimento
            return await self._iniciar_atendimento(AgentContext(
                user_id=usuario_id,
                session_id=context.session_id,
                message=mensagem,
                metadata={
                    "dados": {
                        "usuario_id": usuario_id,
                        "canal": context.metadata.get("canal", "app"),
                        "mensagem": mensagem
                    }
                }
            ))


def create_service_center_agent(
    memory: UnifiedMemorySystem,
    llm_client: UnifiedLLMClient,
    tools: ToolRegistry,
    rag: Optional[RAGPipeline] = None
) -> ServiceCenterAgent:
    """Factory function para criar a central de atendimento"""
    return ServiceCenterAgent(memory, llm_client, tools, rag)
