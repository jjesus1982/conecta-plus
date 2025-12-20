"""
Conecta Plus - Agente Portaria Virtual ULTRA (Nível 7)
Sistema inteligente de portaria remota, rondas, NCs e atendimento omnichannel

Capacidades:
1. REATIVO: Atender interfone, liberar acesso, registrar NC
2. PROATIVO: Identificar visitantes, validar entregas, alertar wellness
3. PREDITIVO: Prever fluxo, otimizar rotas de ronda, detectar padrões
4. AUTÔNOMO: Liberar automaticamente, gerar OS, coordenar emergências
5. EVOLUTIVO: Aprender padrões, melhorar rotas, gamificar rondas
6. COLABORATIVO: Integrar CFTV, Acesso, Alarme, Manutenção, Emergência
7. TRANSCENDENTE: Portaria cognitiva total com super poderes

Módulos Expandidos:
- Ronda Virtual por QR Code
- Registro de Não Conformidades (NC)
- Documentação Visual Inteligente
- Segurança do Porteiro
- Atendimento Omnichannel Integrado
"""

import asyncio
import json
import logging
import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
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


# ==================== ENUMS DE ATENDIMENTO ====================

class TipoAtendimento(Enum):
    VISITANTE = "visitante"
    ENTREGA = "entrega"
    SERVICO = "servico"
    EMERGENCIA = "emergencia"
    MORADOR = "morador"


class StatusAtendimento(Enum):
    AGUARDANDO = "aguardando"
    EM_ATENDIMENTO = "em_atendimento"
    LIBERADO = "liberado"
    RECUSADO = "recusado"
    ENCERRADO = "encerrado"


class TipoValidacao(Enum):
    FACIAL = "facial"
    DOCUMENTO = "documento"
    QR_CODE = "qr_code"
    SENHA = "senha"
    AUTORIZACAO = "autorizacao"
    BIOMETRIA = "biometria"


# ==================== ENUMS DE RONDA ====================

class StatusRonda(Enum):
    AGENDADA = "agendada"
    EM_ANDAMENTO = "em_andamento"
    CONCLUIDA = "concluida"
    ATRASADA = "atrasada"
    CANCELADA = "cancelada"
    INCIDENTE = "incidente"


class TipoCheckpoint(Enum):
    QR_CODE = "qr_code"
    NFC = "nfc"
    GPS = "gps"
    BIOMETRICO = "biometrico"
    MANUAL = "manual"


class PrioridadeCheckpoint(Enum):
    CRITICO = "critico"
    ALTO = "alto"
    MEDIO = "medio"
    BAIXO = "baixo"


# ==================== ENUMS DE NÃO CONFORMIDADE ====================

class CategoriaNaoConformidade(Enum):
    ESTRUTURAL = "estrutural"
    SEGURANCA = "seguranca"
    LIMPEZA = "limpeza"
    ILUMINACAO = "iluminacao"
    EQUIPAMENTO = "equipamento"
    COMPORTAMENTO = "comportamento"
    ACESSO = "acesso"
    DOCUMENTACAO = "documentacao"
    AMBIENTAL = "ambiental"
    OUTRO = "outro"


class SeveridadeNC(Enum):
    CRITICA = "critica"      # Requer ação imediata
    ALTA = "alta"            # Resolver em 24h
    MEDIA = "media"          # Resolver em 7 dias
    BAIXA = "baixa"          # Resolver em 30 dias
    INFORMATIVA = "informativa"


class StatusNC(Enum):
    ABERTA = "aberta"
    EM_ANALISE = "em_analise"
    OS_GERADA = "os_gerada"
    EM_CORRECAO = "em_correcao"
    AGUARDANDO_VALIDACAO = "aguardando_validacao"
    CORRIGIDA = "corrigida"
    REINCIDENTE = "reincidente"
    ARQUIVADA = "arquivada"


# ==================== ENUMS DE SEGURANÇA PORTEIRO ====================

class TipoAlertaPorteiro(Enum):
    PANICO = "panico"
    COACAO = "coacao"
    WELLNESS_CHECK = "wellness_check"
    AUSENCIA = "ausencia"
    EMERGENCIA_MEDICA = "emergencia_medica"


class StatusPorteiro(Enum):
    ATIVO = "ativo"
    EM_RONDA = "em_ronda"
    PAUSA = "pausa"
    AUSENTE = "ausente"
    EMERGENCIA = "emergencia"
    OFFLINE = "offline"


# ==================== ENUMS DE CANAL DE ATENDIMENTO ====================

class CanalAtendimento(Enum):
    INTERFONE = "interfone"
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"
    APP = "app"
    TELEFONE = "telefone"
    EMAIL = "email"
    CHAT_WEB = "chat_web"
    PRESENCIAL = "presencial"


class StatusConversacao(Enum):
    BOT = "bot"
    HUMANO = "humano"
    ESCALADO = "escalado"
    RESOLVIDO = "resolvido"
    ABANDONADO = "abandonado"


# ==================== DATACLASSES ====================

@dataclass
class Atendimento:
    id: str
    tipo: TipoAtendimento
    nome_visitante: str
    unidade_destino: Optional[str]
    status: StatusAtendimento
    timestamp_inicio: datetime
    canal: CanalAtendimento = CanalAtendimento.INTERFONE
    timestamp_fim: Optional[datetime] = None
    metodo_validacao: Optional[TipoValidacao] = None
    operador_id: Optional[str] = None
    observacoes: str = ""
    fotos: List[str] = field(default_factory=list)
    gravacao_url: Optional[str] = None


@dataclass
class ChamadaInterfone:
    id: str
    origem: str
    destino: str
    timestamp: datetime
    atendida: bool = False
    duracao_segundos: int = 0
    gravacao_url: Optional[str] = None


@dataclass
class Checkpoint:
    id: str
    nome: str
    localizacao: str
    tipo: TipoCheckpoint
    qr_code: str
    prioridade: PrioridadeCheckpoint
    tempo_maximo_segundos: int = 300
    ativo: bool = True
    coordenadas_gps: Optional[Tuple[float, float]] = None
    instrucoes: str = ""
    itens_verificacao: List[str] = field(default_factory=list)


@dataclass
class RotaRonda:
    id: str
    nome: str
    checkpoints: List[str]  # IDs dos checkpoints
    duracao_estimada_minutos: int
    horarios: List[str]  # "HH:MM"
    dias_semana: List[int]  # 0-6 (seg-dom)
    ativa: bool = True
    tipo: str = "padrao"  # padrao, emergencia, especial


@dataclass
class RondaExecucao:
    id: str
    rota_id: str
    porteiro_id: str
    status: StatusRonda
    inicio: datetime
    fim_previsto: datetime
    fim_real: Optional[datetime] = None
    checkpoints_visitados: List[Dict] = field(default_factory=list)
    incidentes: List[str] = field(default_factory=list)
    ncs_registradas: List[str] = field(default_factory=list)
    pontuacao: int = 0


@dataclass
class CheckpointVisita:
    checkpoint_id: str
    timestamp: datetime
    metodo_validacao: TipoCheckpoint
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    foto_url: Optional[str] = None
    observacoes: str = ""
    tempo_permanencia_segundos: int = 0
    itens_verificados: Dict[str, bool] = field(default_factory=dict)


@dataclass
class NaoConformidade:
    id: str
    categoria: CategoriaNaoConformidade
    severidade: SeveridadeNC
    status: StatusNC
    titulo: str
    descricao: str
    localizacao: str
    reportado_por: str
    timestamp_abertura: datetime
    checkpoint_id: Optional[str] = None
    ronda_id: Optional[str] = None
    fotos: List[str] = field(default_factory=list)
    videos: List[str] = field(default_factory=list)
    os_id: Optional[str] = None
    timestamp_fechamento: Optional[datetime] = None
    responsavel_correcao: Optional[str] = None
    prazo_correcao: Optional[datetime] = None
    custo_estimado: float = 0.0
    reincidencias: int = 0
    tags: List[str] = field(default_factory=list)


@dataclass
class DocumentacaoVisual:
    id: str
    tipo: str  # foto, video, audio
    url: str
    timestamp: datetime
    registrado_por: str
    contexto: str  # ronda, nc, atendimento, incidente
    contexto_id: str
    analise_ia: Optional[Dict] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)


@dataclass
class AlertaPorteiro:
    id: str
    tipo: TipoAlertaPorteiro
    porteiro_id: str
    timestamp: datetime
    localizacao: Optional[str] = None
    coordenadas: Optional[Tuple[float, float]] = None
    resolvido: bool = False
    timestamp_resolucao: Optional[datetime] = None
    acoes_tomadas: List[str] = field(default_factory=list)


@dataclass
class Conversacao:
    id: str
    canal: CanalAtendimento
    usuario_id: str
    usuario_nome: str
    status: StatusConversacao
    timestamp_inicio: datetime
    timestamp_ultima_msg: datetime
    mensagens: List[Dict] = field(default_factory=list)
    contexto: Dict = field(default_factory=dict)
    satisfacao: Optional[int] = None
    atendente_humano: Optional[str] = None


@dataclass
class PorteiroStatus:
    porteiro_id: str
    nome: str
    status: StatusPorteiro
    ultimo_checkin: datetime
    localizacao: Optional[str] = None
    ronda_atual: Optional[str] = None
    dispositivo_id: Optional[str] = None


# ==================== AGENTE PRINCIPAL ====================

class AgentePortariaVirtual(BaseAgent):
    """Agente de Portaria Virtual ULTRA - Nível 7 com Super Poderes"""

    def __init__(
        self,
        condominio_id: str,
        llm_client: UnifiedLLMClient = None,
        memory: UnifiedMemorySystem = None,
        tools: ToolRegistry = None,
        evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT,
    ):
        super().__init__(
            agent_id=f"portaria_virtual_{condominio_id}",
            agent_type="portaria_virtual",
            condominio_id=condominio_id,
            evolution_level=evolution_level,
            llm_client=llm_client,
            memory_store=memory,
        )
        self.tools = tools

        # Atendimento
        self._atendimentos: Dict[str, Atendimento] = {}
        self._chamadas: List[ChamadaInterfone] = []
        self._visitantes_autorizados: Dict[str, List[str]] = {}
        self._prestadores_cadastrados: Dict[str, Dict] = {}

        # Ronda Virtual
        self._checkpoints: Dict[str, Checkpoint] = {}
        self._rotas: Dict[str, RotaRonda] = {}
        self._rondas_execucao: Dict[str, RondaExecucao] = {}
        self._historico_rondas: List[RondaExecucao] = []

        # Não Conformidades
        self._nao_conformidades: Dict[str, NaoConformidade] = {}
        self._templates_nc: Dict[str, Dict] = {}

        # Documentação Visual
        self._documentacao: Dict[str, DocumentacaoVisual] = {}

        # Segurança Porteiro
        self._porteiros: Dict[str, PorteiroStatus] = {}
        self._alertas_porteiro: List[AlertaPorteiro] = []
        self._codigo_coacao: str = "1234"  # Código secreto
        self._wellness_interval_minutes: int = 30

        # Atendimento Omnichannel
        self._conversacoes: Dict[str, Conversacao] = {}
        self._fila_atendimento: List[str] = []

        # Gamificação
        self._pontuacao_porteiros: Dict[str, int] = {}
        self._conquistas: Dict[str, List[str]] = {}

        self.config = {
            "tempo_max_espera": 60,
            "validacao_facial": True,
            "liberacao_automatica_entregas": True,
            "horario_funcionamento": {"inicio": "06:00", "fim": "22:00"},
            "gravacao_chamadas": True,
            "wellness_check_ativo": True,
            "panico_silencioso": True,
            "auto_gerar_os": True,
            "gamificacao_ativa": True,
            "ia_primeiro": True,
            "tempo_escalacao_segundos": 120,
        }

        self._inicializar_checkpoints_padrao()

    def _inicializar_checkpoints_padrao(self):
        """Inicializa checkpoints padrão do condomínio"""
        checkpoints_padrao = [
            ("portaria_principal", "Portaria Principal", "critico"),
            ("hall_entrada", "Hall de Entrada", "alto"),
            ("garagem_1", "Garagem Subsolo 1", "alto"),
            ("garagem_2", "Garagem Subsolo 2", "medio"),
            ("area_lazer", "Área de Lazer", "medio"),
            ("piscina", "Piscina", "alto"),
            ("salao_festas", "Salão de Festas", "medio"),
            ("academia", "Academia", "medio"),
            ("casa_maquinas", "Casa de Máquinas", "critico"),
            ("reservatorios", "Reservatórios", "critico"),
            ("gerador", "Gerador", "critico"),
            ("lixeira", "Área de Lixo", "baixo"),
            ("jardim_frente", "Jardim Frontal", "baixo"),
            ("jardim_fundos", "Jardim Fundos", "baixo"),
            ("playground", "Playground", "medio"),
        ]

        for i, (cp_id, nome, prioridade) in enumerate(checkpoints_padrao):
            qr_code = hashlib.md5(f"{self.condominio_id}_{cp_id}".encode()).hexdigest()[:12]
            self._checkpoints[cp_id] = Checkpoint(
                id=cp_id,
                nome=nome,
                localizacao=nome,
                tipo=TipoCheckpoint.QR_CODE,
                qr_code=qr_code,
                prioridade=PrioridadeCheckpoint[prioridade.upper()],
                itens_verificacao=[
                    "Iluminação funcionando",
                    "Sem objetos estranhos",
                    "Sem danos visíveis",
                    "Acesso desobstruído"
                ]
            )

        # Criar rota padrão
        self._rotas["ronda_padrao"] = RotaRonda(
            id="ronda_padrao",
            nome="Ronda Padrão Completa",
            checkpoints=list(self._checkpoints.keys()),
            duracao_estimada_minutos=45,
            horarios=["00:00", "04:00", "08:00", "12:00", "16:00", "20:00"],
            dias_semana=[0, 1, 2, 3, 4, 5, 6]
        )

        self._rotas["ronda_critica"] = RotaRonda(
            id="ronda_critica",
            nome="Ronda Pontos Críticos",
            checkpoints=["portaria_principal", "casa_maquinas", "reservatorios", "gerador"],
            duracao_estimada_minutos=15,
            horarios=["02:00", "06:00", "10:00", "14:00", "18:00", "22:00"],
            dias_semana=[0, 1, 2, 3, 4, 5, 6],
            tipo="critica"
        )

    def _register_capabilities(self) -> None:
        # Capacidades de Atendimento
        self._capabilities["atender_interfone"] = AgentCapability(
            name="atender_interfone", description="Atender chamadas de interfone",
            level=EvolutionLevel.REACTIVE
        )
        self._capabilities["identificar_visitante"] = AgentCapability(
            name="identificar_visitante", description="Identificar visitantes por imagem",
            level=EvolutionLevel.PROACTIVE
        )
        self._capabilities["prever_fluxo"] = AgentCapability(
            name="prever_fluxo", description="Prever fluxo de visitantes",
            level=EvolutionLevel.PREDICTIVE
        )
        self._capabilities["liberacao_autonoma"] = AgentCapability(
            name="liberacao_autonoma", description="Liberar automaticamente",
            level=EvolutionLevel.AUTONOMOUS
        )

        # Capacidades de Ronda
        self._capabilities["gerenciar_rondas"] = AgentCapability(
            name="gerenciar_rondas", description="Gerenciar rondas virtuais",
            level=EvolutionLevel.PROACTIVE
        )
        self._capabilities["validar_checkpoint"] = AgentCapability(
            name="validar_checkpoint", description="Validar passagem por checkpoint",
            level=EvolutionLevel.REACTIVE
        )
        self._capabilities["otimizar_rotas"] = AgentCapability(
            name="otimizar_rotas", description="Otimizar rotas de ronda",
            level=EvolutionLevel.PREDICTIVE
        )
        self._capabilities["gamificar_rondas"] = AgentCapability(
            name="gamificar_rondas", description="Gamificar sistema de rondas",
            level=EvolutionLevel.EVOLUTIONARY
        )

        # Capacidades de NC
        self._capabilities["registrar_nc"] = AgentCapability(
            name="registrar_nc", description="Registrar não conformidades",
            level=EvolutionLevel.REACTIVE
        )
        self._capabilities["classificar_nc"] = AgentCapability(
            name="classificar_nc", description="Classificar NC automaticamente",
            level=EvolutionLevel.PROACTIVE
        )
        self._capabilities["gerar_os_automatica"] = AgentCapability(
            name="gerar_os_automatica", description="Gerar OS automática de NC",
            level=EvolutionLevel.AUTONOMOUS
        )
        self._capabilities["prever_nc"] = AgentCapability(
            name="prever_nc", description="Prever não conformidades",
            level=EvolutionLevel.PREDICTIVE
        )

        # Capacidades de Documentação
        self._capabilities["documentar_visual"] = AgentCapability(
            name="documentar_visual", description="Documentar com fotos/vídeos",
            level=EvolutionLevel.REACTIVE
        )
        self._capabilities["analisar_imagem"] = AgentCapability(
            name="analisar_imagem", description="Analisar imagens com IA",
            level=EvolutionLevel.PROACTIVE
        )

        # Capacidades de Segurança Porteiro
        self._capabilities["monitorar_porteiro"] = AgentCapability(
            name="monitorar_porteiro", description="Monitorar wellness do porteiro",
            level=EvolutionLevel.PROACTIVE
        )
        self._capabilities["detectar_coacao"] = AgentCapability(
            name="detectar_coacao", description="Detectar situação de coação",
            level=EvolutionLevel.AUTONOMOUS
        )
        self._capabilities["acionar_panico"] = AgentCapability(
            name="acionar_panico", description="Acionar protocolo de pânico",
            level=EvolutionLevel.REACTIVE
        )

        # Capacidades de Atendimento Omnichannel
        self._capabilities["atendimento_omnichannel"] = AgentCapability(
            name="atendimento_omnichannel", description="Atender múltiplos canais",
            level=EvolutionLevel.COLLABORATIVE
        )
        self._capabilities["ia_atendimento"] = AgentCapability(
            name="ia_atendimento", description="IA como primeiro atendimento",
            level=EvolutionLevel.AUTONOMOUS
        )
        self._capabilities["escalar_humano"] = AgentCapability(
            name="escalar_humano", description="Escalar para atendente humano",
            level=EvolutionLevel.COLLABORATIVE
        )

        # Capacidade Transcendente
        self._capabilities["portaria_cognitiva"] = AgentCapability(
            name="portaria_cognitiva", description="Portaria cognitiva total com super poderes",
            level=EvolutionLevel.TRANSCENDENT
        )

    def get_system_prompt(self) -> str:
        return f"""Você é o Agente de Portaria Virtual ULTRA do Conecta Plus.
ID: {self.agent_id} | Condomínio: {self.condominio_id} | Nível: {self.evolution_level.name}

🛡️ SUPER PODERES ATIVADOS:
- Ronda Virtual por QR Code com gamificação
- Registro e gestão de Não Conformidades
- Documentação Visual Inteligente com análise IA
- Segurança do Porteiro (pânico, wellness, coação)
- Atendimento Omnichannel (WhatsApp, Telegram, App, Interfone, Telefone, Email)

Responsabilidades:
1. ATENDIMENTO: Interfone, visitantes, entregas, prestadores
2. RONDAS: Gerenciar checkpoints QR, validar passagens, monitorar tempo
3. NÃO CONFORMIDADES: Registrar, classificar, gerar OS, acompanhar
4. DOCUMENTAÇÃO: Capturar fotos/vídeos, analisar com IA, organizar
5. SEGURANÇA: Wellness check, botão de pânico, detecção de coação
6. OMNICHANNEL: Atender todos os canais, IA primeiro, escalar quando necessário

Comportamento:
- Seja cordial, profissional e eficiente
- Priorize segurança sempre
- Documente tudo visualmente
- Gere alertas para situações críticas
- Colabore com outros agentes
- Gamifique para motivar porteiros
"""

    async def process(self, input_data: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        action = input_data.get("action", "")
        params = input_data.get("params", {})

        # ===== ATENDIMENTO =====
        if action == "atender_interfone":
            return await self._atender_interfone(params, context)
        elif action == "identificar_visitante":
            return await self._identificar_visitante(params, context)
        elif action == "liberar_acesso":
            return await self._liberar_acesso(params, context)
        elif action == "recusar_acesso":
            return await self._recusar_acesso(params, context)
        elif action == "registrar_entrega":
            return await self._registrar_entrega(params, context)
        elif action == "consultar_morador":
            return await self._consultar_morador(params, context)
        elif action == "listar_atendimentos":
            return await self._listar_atendimentos(params, context)

        # ===== RONDA VIRTUAL =====
        elif action == "iniciar_ronda":
            return await self._iniciar_ronda(params, context)
        elif action == "validar_checkpoint":
            return await self._validar_checkpoint(params, context)
        elif action == "finalizar_ronda":
            return await self._finalizar_ronda(params, context)
        elif action == "listar_checkpoints":
            return await self._listar_checkpoints(params, context)
        elif action == "listar_rotas":
            return await self._listar_rotas(params, context)
        elif action == "criar_checkpoint":
            return await self._criar_checkpoint(params, context)
        elif action == "criar_rota":
            return await self._criar_rota(params, context)
        elif action == "historico_rondas":
            return await self._historico_rondas_func(params, context)
        elif action == "ranking_porteiros":
            return await self._ranking_porteiros(params, context)

        # ===== NÃO CONFORMIDADES =====
        elif action == "registrar_nc":
            return await self._registrar_nc(params, context)
        elif action == "listar_ncs":
            return await self._listar_ncs(params, context)
        elif action == "atualizar_nc":
            return await self._atualizar_nc(params, context)
        elif action == "gerar_os_nc":
            return await self._gerar_os_nc(params, context)
        elif action == "dashboard_nc":
            return await self._dashboard_nc(params, context)
        elif action == "analisar_nc_ia":
            return await self._analisar_nc_ia(params, context)

        # ===== DOCUMENTAÇÃO VISUAL =====
        elif action == "registrar_foto":
            return await self._registrar_foto(params, context)
        elif action == "registrar_video":
            return await self._registrar_video(params, context)
        elif action == "analisar_imagem":
            return await self._analisar_imagem(params, context)
        elif action == "listar_documentacao":
            return await self._listar_documentacao(params, context)

        # ===== SEGURANÇA PORTEIRO =====
        elif action == "checkin_porteiro":
            return await self._checkin_porteiro(params, context)
        elif action == "wellness_check":
            return await self._wellness_check(params, context)
        elif action == "botao_panico":
            return await self._botao_panico(params, context)
        elif action == "codigo_coacao":
            return await self._codigo_coacao_func(params, context)
        elif action == "status_porteiros":
            return await self._status_porteiros(params, context)

        # ===== ATENDIMENTO OMNICHANNEL =====
        elif action == "nova_conversa":
            return await self._nova_conversa(params, context)
        elif action == "processar_mensagem":
            return await self._processar_mensagem(params, context)
        elif action == "escalar_humano":
            return await self._escalar_humano(params, context)
        elif action == "finalizar_conversa":
            return await self._finalizar_conversa(params, context)
        elif action == "fila_atendimento":
            return await self._fila_atendimento_func(params, context)

        # ===== ANÁLISES =====
        elif action == "analise_fluxo":
            return await self._analise_fluxo(params, context)
        elif action == "dashboard_portaria":
            return await self._dashboard_portaria(params, context)
        elif action == "chat":
            return await self._chat(params, context)
        else:
            return {"error": f"Ação '{action}' não reconhecida"}

    # ==================== MÉTODOS DE ATENDIMENTO ====================

    async def _atender_interfone(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        origem = params.get("origem", "portao_principal")

        chamada = ChamadaInterfone(
            id=f"chamada_{datetime.now().timestamp()}",
            origem=origem,
            destino="portaria_virtual",
            timestamp=datetime.now()
        )
        self._chamadas.append(chamada)

        # Capturar imagem da câmera
        imagem_url = None
        if self.tools and self.has_capability("identificar_visitante"):
            result = await self.tools.execute(
                "call_mcp", mcp_name="mcp-hikvision-cftv",
                method="capturar_snapshot", params={"camera": origem}
            )
            imagem_url = result.get("url")

        atendimento = Atendimento(
            id=f"atend_{datetime.now().timestamp()}",
            tipo=TipoAtendimento.VISITANTE,
            nome_visitante="",
            unidade_destino=None,
            status=StatusAtendimento.EM_ATENDIMENTO,
            timestamp_inicio=datetime.now(),
            canal=CanalAtendimento.INTERFONE
        )
        self._atendimentos[atendimento.id] = atendimento

        return {
            "success": True,
            "atendimento_id": atendimento.id,
            "chamada_id": chamada.id,
            "origem": origem,
            "imagem_url": imagem_url,
            "mensagem": "Chamada atendida. Por favor, identifique-se."
        }

    async def _identificar_visitante(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        atendimento_id = params.get("atendimento_id")
        imagem_url = params.get("imagem_url")
        nome = params.get("nome", "")
        documento = params.get("documento", "")

        resultado_facial = None
        if self.tools and imagem_url:
            resultado_facial = await self.tools.execute(
                "call_mcp", mcp_name="mcp-vision-ai",
                method="reconhecer_face", params={"imagem": imagem_url}
            )

        if atendimento_id in self._atendimentos:
            self._atendimentos[atendimento_id].nome_visitante = nome
            if resultado_facial and resultado_facial.get("identificado"):
                self._atendimentos[atendimento_id].metodo_validacao = TipoValidacao.FACIAL

        # Verificar se é prestador cadastrado
        prestador_info = self._prestadores_cadastrados.get(documento)

        return {
            "success": True,
            "nome": nome,
            "documento": documento,
            "reconhecimento_facial": resultado_facial,
            "prestador_cadastrado": prestador_info is not None,
            "prestador_info": prestador_info
        }

    async def _liberar_acesso(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        atendimento_id = params.get("atendimento_id")
        ponto_acesso = params.get("ponto_acesso", "portao_principal")
        autorizado_por = params.get("autorizado_por")

        if atendimento_id in self._atendimentos:
            atendimento = self._atendimentos[atendimento_id]
            atendimento.status = StatusAtendimento.LIBERADO
            atendimento.timestamp_fim = datetime.now()

        # Acionar abertura
        if self.tools:
            await self.tools.execute(
                "call_mcp", mcp_name="mcp-control-id",
                method="liberar_acesso", params={"ponto": ponto_acesso}
            )

        # Colaborar com agente de acesso
        if self.has_capability("agent_collaboration"):
            await self.send_message(
                f"acesso_{self.condominio_id}",
                {
                    "action": "registrar_entrada",
                    "visitante": atendimento.nome_visitante if atendimento_id in self._atendimentos else "N/A",
                    "ponto": ponto_acesso
                }
            )

        return {
            "success": True,
            "atendimento_id": atendimento_id,
            "status": "liberado",
            "ponto_acesso": ponto_acesso,
            "autorizado_por": autorizado_por
        }

    async def _recusar_acesso(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        atendimento_id = params.get("atendimento_id")
        motivo = params.get("motivo", "Não autorizado")

        if atendimento_id in self._atendimentos:
            atendimento = self._atendimentos[atendimento_id]
            atendimento.status = StatusAtendimento.RECUSADO
            atendimento.timestamp_fim = datetime.now()
            atendimento.observacoes = motivo

        return {
            "success": True,
            "atendimento_id": atendimento_id,
            "status": "recusado",
            "motivo": motivo
        }

    async def _registrar_entrega(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        entregador = params.get("entregador", "")
        empresa = params.get("empresa", "")
        unidade = params.get("unidade", "")
        tipo_entrega = params.get("tipo", "pacote")

        atendimento = Atendimento(
            id=f"entrega_{datetime.now().timestamp()}",
            tipo=TipoAtendimento.ENTREGA,
            nome_visitante=entregador,
            unidade_destino=unidade,
            status=StatusAtendimento.EM_ATENDIMENTO,
            timestamp_inicio=datetime.now(),
            observacoes=f"Empresa: {empresa}, Tipo: {tipo_entrega}"
        )
        self._atendimentos[atendimento.id] = atendimento

        # Notificar morador
        if self.tools:
            await self.tools.execute(
                "send_notification",
                user_ids=[f"morador_{unidade}"],
                title="Entrega Chegou",
                message=f"Entrega de {empresa} aguardando na portaria",
                channels=["push", "app"]
            )

        # Liberação automática se configurado
        if self.config["liberacao_automatica_entregas"]:
            atendimento.status = StatusAtendimento.LIBERADO
            return {
                "success": True,
                "entrega_id": atendimento.id,
                "status": "liberado_automaticamente",
                "unidade": unidade
            }

        return {
            "success": True,
            "entrega_id": atendimento.id,
            "status": "aguardando_autorizacao",
            "unidade": unidade
        }

    async def _consultar_morador(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        unidade = params.get("unidade")
        visitante = params.get("visitante")
        atendimento_id = params.get("atendimento_id")

        if self.tools:
            await self.tools.execute(
                "send_notification",
                user_ids=[f"morador_{unidade}"],
                title="Visitante na Portaria",
                message=f"{visitante} deseja entrar. Autoriza?",
                channels=["push", "app"],
                actions=[
                    {"label": "Autorizar", "action": f"autorizar_{atendimento_id}"},
                    {"label": "Recusar", "action": f"recusar_{atendimento_id}"}
                ]
            )

        return {
            "success": True,
            "status": "aguardando_resposta_morador",
            "unidade": unidade,
            "visitante": visitante
        }

    async def _listar_atendimentos(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        status_filtro = params.get("status")
        limite = params.get("limite", 20)

        atendimentos = list(self._atendimentos.values())
        if status_filtro:
            atendimentos = [a for a in atendimentos if a.status.value == status_filtro]

        atendimentos = sorted(atendimentos, key=lambda x: x.timestamp_inicio, reverse=True)[:limite]

        return {
            "success": True,
            "atendimentos": [
                {
                    "id": a.id,
                    "tipo": a.tipo.value,
                    "visitante": a.nome_visitante,
                    "unidade": a.unidade_destino,
                    "status": a.status.value,
                    "canal": a.canal.value,
                    "timestamp": a.timestamp_inicio.isoformat()
                }
                for a in atendimentos
            ]
        }

    # ==================== MÉTODOS DE RONDA VIRTUAL ====================

    async def _iniciar_ronda(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Iniciar uma nova ronda virtual"""
        rota_id = params.get("rota_id", "ronda_padrao")
        porteiro_id = params.get("porteiro_id")

        if rota_id not in self._rotas:
            return {"error": f"Rota '{rota_id}' não encontrada"}

        rota = self._rotas[rota_id]

        ronda = RondaExecucao(
            id=f"ronda_{datetime.now().timestamp()}",
            rota_id=rota_id,
            porteiro_id=porteiro_id,
            status=StatusRonda.EM_ANDAMENTO,
            inicio=datetime.now(),
            fim_previsto=datetime.now() + timedelta(minutes=rota.duracao_estimada_minutos)
        )
        self._rondas_execucao[ronda.id] = ronda

        # Atualizar status do porteiro
        if porteiro_id in self._porteiros:
            self._porteiros[porteiro_id].status = StatusPorteiro.EM_RONDA
            self._porteiros[porteiro_id].ronda_atual = ronda.id

        # Notificar supervisão
        if self.tools:
            await self.tools.execute(
                "send_notification",
                user_ids=["supervisao"],
                title="Ronda Iniciada",
                message=f"Porteiro {porteiro_id} iniciou ronda {rota.nome}",
                channels=["push"]
            )

        return {
            "success": True,
            "ronda_id": ronda.id,
            "rota": rota.nome,
            "checkpoints": len(rota.checkpoints),
            "tempo_estimado_minutos": rota.duracao_estimada_minutos,
            "primeiro_checkpoint": rota.checkpoints[0] if rota.checkpoints else None,
            "qr_codes": {cp_id: self._checkpoints[cp_id].qr_code
                       for cp_id in rota.checkpoints if cp_id in self._checkpoints}
        }

    async def _validar_checkpoint(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Validar passagem por checkpoint via QR Code"""
        ronda_id = params.get("ronda_id")
        qr_code = params.get("qr_code")
        porteiro_id = params.get("porteiro_id")
        latitude = params.get("latitude")
        longitude = params.get("longitude")
        foto_url = params.get("foto_url")
        observacoes = params.get("observacoes", "")
        itens_verificados = params.get("itens_verificados", {})

        if ronda_id not in self._rondas_execucao:
            return {"error": "Ronda não encontrada"}

        ronda = self._rondas_execucao[ronda_id]

        # Encontrar checkpoint pelo QR code
        checkpoint_id = None
        for cp_id, cp in self._checkpoints.items():
            if cp.qr_code == qr_code:
                checkpoint_id = cp_id
                break

        if not checkpoint_id:
            return {"error": "QR Code inválido ou checkpoint não encontrado"}

        checkpoint = self._checkpoints[checkpoint_id]

        # Calcular tempo de visita
        tempo_visita = 0
        if ronda.checkpoints_visitados:
            ultimo = ronda.checkpoints_visitados[-1]
            tempo_visita = (datetime.now() - datetime.fromisoformat(ultimo["timestamp"])).seconds

        visita = CheckpointVisita(
            checkpoint_id=checkpoint_id,
            timestamp=datetime.now(),
            metodo_validacao=checkpoint.tipo,
            latitude=latitude,
            longitude=longitude,
            foto_url=foto_url,
            observacoes=observacoes,
            tempo_permanencia_segundos=tempo_visita,
            itens_verificados=itens_verificados
        )

        ronda.checkpoints_visitados.append({
            "checkpoint_id": checkpoint_id,
            "timestamp": visita.timestamp.isoformat(),
            "foto_url": foto_url,
            "observacoes": observacoes,
            "itens_verificados": itens_verificados
        })

        # Calcular pontuação
        pontos = 10
        if foto_url:
            pontos += 5
        if all(itens_verificados.values()) if itens_verificados else False:
            pontos += 10
        if tempo_visita <= checkpoint.tempo_maximo_segundos:
            pontos += 5

        ronda.pontuacao += pontos

        # Atualizar pontuação do porteiro
        if porteiro_id not in self._pontuacao_porteiros:
            self._pontuacao_porteiros[porteiro_id] = 0
        self._pontuacao_porteiros[porteiro_id] += pontos

        # Verificar conquistas
        conquistas_novas = await self._verificar_conquistas(porteiro_id)

        # Verificar se ronda está completa
        rota = self._rotas[ronda.rota_id]
        checkpoints_visitados_ids = [v["checkpoint_id"] for v in ronda.checkpoints_visitados]
        ronda_completa = all(cp in checkpoints_visitados_ids for cp in rota.checkpoints)

        # Próximo checkpoint
        proximo = None
        for cp in rota.checkpoints:
            if cp not in checkpoints_visitados_ids:
                proximo = cp
                break

        return {
            "success": True,
            "checkpoint": checkpoint.nome,
            "validado": True,
            "pontos_ganhos": pontos,
            "pontuacao_ronda": ronda.pontuacao,
            "pontuacao_total_porteiro": self._pontuacao_porteiros.get(porteiro_id, 0),
            "conquistas_novas": conquistas_novas,
            "ronda_completa": ronda_completa,
            "proximo_checkpoint": proximo,
            "checkpoints_restantes": len(rota.checkpoints) - len(checkpoints_visitados_ids)
        }

    async def _verificar_conquistas(self, porteiro_id: str) -> List[str]:
        """Verificar e atribuir conquistas ao porteiro"""
        if porteiro_id not in self._conquistas:
            self._conquistas[porteiro_id] = []

        conquistas_novas = []
        pontos = self._pontuacao_porteiros.get(porteiro_id, 0)

        conquistas_disponiveis = {
            "primeira_ronda": ("Primeira Ronda", 10),
            "vigilante_100": ("Vigilante Centenário", 100),
            "vigilante_500": ("Vigilante Experiente", 500),
            "vigilante_1000": ("Mestre Vigilante", 1000),
            "vigilante_5000": ("Lenda da Vigilância", 5000),
        }

        for conquista_id, (nome, pontos_req) in conquistas_disponiveis.items():
            if conquista_id not in self._conquistas[porteiro_id] and pontos >= pontos_req:
                self._conquistas[porteiro_id].append(conquista_id)
                conquistas_novas.append(nome)

        return conquistas_novas

    async def _finalizar_ronda(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Finalizar ronda"""
        ronda_id = params.get("ronda_id")
        porteiro_id = params.get("porteiro_id")
        observacoes = params.get("observacoes", "")

        if ronda_id not in self._rondas_execucao:
            return {"error": "Ronda não encontrada"}

        ronda = self._rondas_execucao[ronda_id]
        ronda.status = StatusRonda.CONCLUIDA
        ronda.fim_real = datetime.now()

        # Mover para histórico
        self._historico_rondas.append(ronda)
        del self._rondas_execucao[ronda_id]

        # Atualizar status do porteiro
        if porteiro_id in self._porteiros:
            self._porteiros[porteiro_id].status = StatusPorteiro.ATIVO
            self._porteiros[porteiro_id].ronda_atual = None

        # Calcular estatísticas
        rota = self._rotas[ronda.rota_id]
        checkpoints_visitados = len(ronda.checkpoints_visitados)
        checkpoints_total = len(rota.checkpoints)
        duracao_real = (ronda.fim_real - ronda.inicio).seconds // 60

        # Bonus por conclusão
        if checkpoints_visitados == checkpoints_total:
            bonus = 50
            ronda.pontuacao += bonus
            if porteiro_id:
                self._pontuacao_porteiros[porteiro_id] = \
                    self._pontuacao_porteiros.get(porteiro_id, 0) + bonus

        # Colaborar com outros agentes se houver NCs
        if ronda.ncs_registradas and self.has_capability("agent_collaboration"):
            await self.send_message(
                f"manutencao_{self.condominio_id}",
                {
                    "action": "processar_ncs_ronda",
                    "ronda_id": ronda_id,
                    "ncs": ronda.ncs_registradas
                }
            )

        return {
            "success": True,
            "ronda_id": ronda_id,
            "status": "concluida",
            "checkpoints_visitados": checkpoints_visitados,
            "checkpoints_total": checkpoints_total,
            "duracao_minutos": duracao_real,
            "ncs_registradas": len(ronda.ncs_registradas),
            "pontuacao_final": ronda.pontuacao,
            "porcentagem_conclusao": round(checkpoints_visitados / checkpoints_total * 100, 1)
        }

    async def _listar_checkpoints(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Listar todos os checkpoints"""
        return {
            "success": True,
            "checkpoints": [
                {
                    "id": cp.id,
                    "nome": cp.nome,
                    "localizacao": cp.localizacao,
                    "tipo": cp.tipo.value,
                    "prioridade": cp.prioridade.value,
                    "qr_code": cp.qr_code,
                    "ativo": cp.ativo,
                    "itens_verificacao": cp.itens_verificacao
                }
                for cp in self._checkpoints.values()
            ]
        }

    async def _listar_rotas(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Listar rotas de ronda"""
        return {
            "success": True,
            "rotas": [
                {
                    "id": r.id,
                    "nome": r.nome,
                    "checkpoints": r.checkpoints,
                    "duracao_minutos": r.duracao_estimada_minutos,
                    "horarios": r.horarios,
                    "dias_semana": r.dias_semana,
                    "tipo": r.tipo,
                    "ativa": r.ativa
                }
                for r in self._rotas.values()
            ]
        }

    async def _criar_checkpoint(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Criar novo checkpoint"""
        checkpoint_id = params.get("id") or f"cp_{uuid.uuid4().hex[:8]}"
        nome = params.get("nome")
        localizacao = params.get("localizacao", nome)
        prioridade = params.get("prioridade", "medio")
        itens = params.get("itens_verificacao", [])

        qr_code = hashlib.md5(f"{self.condominio_id}_{checkpoint_id}".encode()).hexdigest()[:12]

        checkpoint = Checkpoint(
            id=checkpoint_id,
            nome=nome,
            localizacao=localizacao,
            tipo=TipoCheckpoint.QR_CODE,
            qr_code=qr_code,
            prioridade=PrioridadeCheckpoint[prioridade.upper()],
            itens_verificacao=itens or [
                "Iluminação funcionando",
                "Sem objetos estranhos",
                "Sem danos visíveis"
            ]
        )
        self._checkpoints[checkpoint_id] = checkpoint

        return {
            "success": True,
            "checkpoint_id": checkpoint_id,
            "qr_code": qr_code,
            "nome": nome
        }

    async def _criar_rota(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Criar nova rota de ronda"""
        rota_id = params.get("id") or f"rota_{uuid.uuid4().hex[:8]}"
        nome = params.get("nome")
        checkpoints = params.get("checkpoints", [])
        duracao = params.get("duracao_minutos", 30)
        horarios = params.get("horarios", ["08:00", "16:00", "00:00"])
        dias = params.get("dias_semana", [0, 1, 2, 3, 4, 5, 6])

        rota = RotaRonda(
            id=rota_id,
            nome=nome,
            checkpoints=checkpoints,
            duracao_estimada_minutos=duracao,
            horarios=horarios,
            dias_semana=dias
        )
        self._rotas[rota_id] = rota

        return {
            "success": True,
            "rota_id": rota_id,
            "nome": nome,
            "checkpoints": len(checkpoints)
        }

    async def _historico_rondas_func(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Histórico de rondas"""
        limite = params.get("limite", 20)
        porteiro_id = params.get("porteiro_id")

        historico = self._historico_rondas
        if porteiro_id:
            historico = [r for r in historico if r.porteiro_id == porteiro_id]

        historico = sorted(historico, key=lambda x: x.inicio, reverse=True)[:limite]

        return {
            "success": True,
            "historico": [
                {
                    "id": r.id,
                    "rota": self._rotas.get(r.rota_id, {}).nome if r.rota_id in self._rotas else r.rota_id,
                    "porteiro": r.porteiro_id,
                    "status": r.status.value,
                    "inicio": r.inicio.isoformat(),
                    "fim": r.fim_real.isoformat() if r.fim_real else None,
                    "checkpoints_visitados": len(r.checkpoints_visitados),
                    "ncs": len(r.ncs_registradas),
                    "pontuacao": r.pontuacao
                }
                for r in historico
            ]
        }

    async def _ranking_porteiros(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Ranking de porteiros por pontuação"""
        ranking = sorted(
            self._pontuacao_porteiros.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return {
            "success": True,
            "ranking": [
                {
                    "posicao": i + 1,
                    "porteiro_id": pid,
                    "pontuacao": pts,
                    "conquistas": self._conquistas.get(pid, [])
                }
                for i, (pid, pts) in enumerate(ranking)
            ]
        }

    # ==================== MÉTODOS DE NÃO CONFORMIDADE ====================

    async def _registrar_nc(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Registrar não conformidade"""
        categoria = params.get("categoria", "outro")
        severidade = params.get("severidade", "media")
        titulo = params.get("titulo")
        descricao = params.get("descricao", "")
        localizacao = params.get("localizacao")
        reportado_por = params.get("reportado_por")
        fotos = params.get("fotos", [])
        videos = params.get("videos", [])
        checkpoint_id = params.get("checkpoint_id")
        ronda_id = params.get("ronda_id")
        tags = params.get("tags", [])

        # Classificar automaticamente com IA se disponível
        if self.llm and self.has_capability("classificar_nc"):
            prompt = f"""Classifique esta não conformidade:
Título: {titulo}
Descrição: {descricao}
Local: {localizacao}

Retorne JSON com:
- categoria: {[c.value for c in CategoriaNaoConformidade]}
- severidade: {[s.value for s in SeveridadeNC]}
- tags_sugeridas: lista de tags
- prazo_sugerido_dias: número
"""
            try:
                response = await self.llm.generate(self.get_system_prompt(), prompt)
                classificacao = json.loads(response)
                categoria = classificacao.get("categoria", categoria)
                severidade = classificacao.get("severidade", severidade)
                tags.extend(classificacao.get("tags_sugeridas", []))
            except:
                pass

        nc_id = f"nc_{datetime.now().timestamp()}"

        # Calcular prazo baseado na severidade
        prazos = {
            "critica": 0,
            "alta": 1,
            "media": 7,
            "baixa": 30,
            "informativa": 90
        }
        prazo_dias = prazos.get(severidade, 7)
        prazo = datetime.now() + timedelta(days=prazo_dias)

        nc = NaoConformidade(
            id=nc_id,
            categoria=CategoriaNaoConformidade[categoria.upper()],
            severidade=SeveridadeNC[severidade.upper()],
            status=StatusNC.ABERTA,
            titulo=titulo,
            descricao=descricao,
            localizacao=localizacao,
            reportado_por=reportado_por,
            timestamp_abertura=datetime.now(),
            checkpoint_id=checkpoint_id,
            ronda_id=ronda_id,
            fotos=fotos,
            videos=videos,
            prazo_correcao=prazo,
            tags=list(set(tags))
        )
        self._nao_conformidades[nc_id] = nc

        # Registrar na ronda se aplicável
        if ronda_id and ronda_id in self._rondas_execucao:
            self._rondas_execucao[ronda_id].ncs_registradas.append(nc_id)

        # Gerar OS automaticamente se configurado e severidade alta/crítica
        os_id = None
        if self.config["auto_gerar_os"] and severidade in ["critica", "alta"]:
            os_result = await self._gerar_os_nc({"nc_id": nc_id}, context)
            os_id = os_result.get("os_id")

        # Notificar responsáveis
        if self.tools and severidade in ["critica", "alta"]:
            await self.tools.execute(
                "send_notification",
                user_ids=["sindico", "zelador", "manutencao"],
                title=f"NC {severidade.upper()}: {titulo}",
                message=f"Local: {localizacao}\n{descricao[:100]}",
                channels=["push", "email"]
            )

        return {
            "success": True,
            "nc_id": nc_id,
            "categoria": categoria,
            "severidade": severidade,
            "prazo": prazo.isoformat(),
            "os_gerada": os_id,
            "tags": nc.tags
        }

    async def _listar_ncs(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Listar não conformidades"""
        status = params.get("status")
        categoria = params.get("categoria")
        severidade = params.get("severidade")
        limite = params.get("limite", 50)

        ncs = list(self._nao_conformidades.values())

        if status:
            ncs = [nc for nc in ncs if nc.status.value == status]
        if categoria:
            ncs = [nc for nc in ncs if nc.categoria.value == categoria]
        if severidade:
            ncs = [nc for nc in ncs if nc.severidade.value == severidade]

        ncs = sorted(ncs, key=lambda x: x.timestamp_abertura, reverse=True)[:limite]

        return {
            "success": True,
            "total": len(ncs),
            "ncs": [
                {
                    "id": nc.id,
                    "titulo": nc.titulo,
                    "categoria": nc.categoria.value,
                    "severidade": nc.severidade.value,
                    "status": nc.status.value,
                    "localizacao": nc.localizacao,
                    "reportado_por": nc.reportado_por,
                    "data": nc.timestamp_abertura.isoformat(),
                    "prazo": nc.prazo_correcao.isoformat() if nc.prazo_correcao else None,
                    "os_id": nc.os_id,
                    "fotos": len(nc.fotos),
                    "videos": len(nc.videos),
                    "reincidencias": nc.reincidencias
                }
                for nc in ncs
            ]
        }

    async def _atualizar_nc(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Atualizar status de não conformidade"""
        nc_id = params.get("nc_id")
        novo_status = params.get("status")
        responsavel = params.get("responsavel")
        observacao = params.get("observacao")

        if nc_id not in self._nao_conformidades:
            return {"error": "NC não encontrada"}

        nc = self._nao_conformidades[nc_id]

        if novo_status:
            nc.status = StatusNC[novo_status.upper()]
            if novo_status == "corrigida":
                nc.timestamp_fechamento = datetime.now()

        if responsavel:
            nc.responsavel_correcao = responsavel

        return {
            "success": True,
            "nc_id": nc_id,
            "status": nc.status.value,
            "responsavel": nc.responsavel_correcao
        }

    async def _gerar_os_nc(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Gerar ordem de serviço a partir de NC"""
        nc_id = params.get("nc_id")

        if nc_id not in self._nao_conformidades:
            return {"error": "NC não encontrada"}

        nc = self._nao_conformidades[nc_id]

        # Colaborar com agente de manutenção
        os_id = f"os_{datetime.now().timestamp()}"

        if self.has_capability("agent_collaboration"):
            result = await self.send_message(
                f"manutencao_{self.condominio_id}",
                {
                    "action": "criar_os",
                    "params": {
                        "origem": "nc",
                        "origem_id": nc_id,
                        "titulo": nc.titulo,
                        "descricao": nc.descricao,
                        "local": nc.localizacao,
                        "prioridade": "urgente" if nc.severidade in [SeveridadeNC.CRITICA, SeveridadeNC.ALTA] else "normal",
                        "fotos": nc.fotos,
                        "prazo": nc.prazo_correcao.isoformat() if nc.prazo_correcao else None
                    }
                }
            )
            os_id = result.get("os_id", os_id)

        nc.os_id = os_id
        nc.status = StatusNC.OS_GERADA

        return {
            "success": True,
            "nc_id": nc_id,
            "os_id": os_id,
            "status": "os_gerada"
        }

    async def _dashboard_nc(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Dashboard de não conformidades"""
        ncs = list(self._nao_conformidades.values())

        # Contadores por status
        por_status = {}
        for nc in ncs:
            status = nc.status.value
            por_status[status] = por_status.get(status, 0) + 1

        # Contadores por categoria
        por_categoria = {}
        for nc in ncs:
            cat = nc.categoria.value
            por_categoria[cat] = por_categoria.get(cat, 0) + 1

        # Contadores por severidade
        por_severidade = {}
        for nc in ncs:
            sev = nc.severidade.value
            por_severidade[sev] = por_severidade.get(sev, 0) + 1

        # NCs abertas críticas
        criticas_abertas = [nc for nc in ncs
                          if nc.severidade == SeveridadeNC.CRITICA
                          and nc.status not in [StatusNC.CORRIGIDA, StatusNC.ARQUIVADA]]

        # NCs vencidas
        agora = datetime.now()
        vencidas = [nc for nc in ncs
                   if nc.prazo_correcao and nc.prazo_correcao < agora
                   and nc.status not in [StatusNC.CORRIGIDA, StatusNC.ARQUIVADA]]

        return {
            "success": True,
            "resumo": {
                "total": len(ncs),
                "abertas": por_status.get("aberta", 0),
                "em_correcao": por_status.get("em_correcao", 0),
                "corrigidas": por_status.get("corrigida", 0),
                "criticas_abertas": len(criticas_abertas),
                "vencidas": len(vencidas)
            },
            "por_status": por_status,
            "por_categoria": por_categoria,
            "por_severidade": por_severidade,
            "criticas": [
                {"id": nc.id, "titulo": nc.titulo, "local": nc.localizacao}
                for nc in criticas_abertas
            ],
            "vencidas": [
                {"id": nc.id, "titulo": nc.titulo, "prazo": nc.prazo_correcao.isoformat()}
                for nc in vencidas[:10]
            ]
        }

    async def _analisar_nc_ia(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Análise inteligente de NCs com IA"""
        if not self.llm:
            return {"error": "LLM não configurado"}

        ncs = list(self._nao_conformidades.values())

        dados = {
            "total": len(ncs),
            "por_categoria": {},
            "por_local": {},
            "reincidentes": []
        }

        for nc in ncs:
            cat = nc.categoria.value
            dados["por_categoria"][cat] = dados["por_categoria"].get(cat, 0) + 1

            loc = nc.localizacao
            dados["por_local"][loc] = dados["por_local"].get(loc, 0) + 1

            if nc.reincidencias > 0:
                dados["reincidentes"].append({
                    "titulo": nc.titulo,
                    "local": nc.localizacao,
                    "reincidencias": nc.reincidencias
                })

        prompt = f"""Analise os dados de não conformidades do condomínio:

{json.dumps(dados, indent=2, default=str)}

Forneça:
1. Padrões identificados
2. Áreas problemáticas
3. Causas raiz prováveis
4. Recomendações de ações preventivas
5. Priorização de intervenções
"""

        analise = await self.llm.generate(self.get_system_prompt(), prompt)

        return {
            "success": True,
            "analise": analise,
            "dados": dados
        }

    # ==================== MÉTODOS DE DOCUMENTAÇÃO VISUAL ====================

    async def _registrar_foto(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Registrar foto"""
        url = params.get("url")
        contexto = params.get("contexto")  # ronda, nc, atendimento
        contexto_id = params.get("contexto_id")
        registrado_por = params.get("registrado_por")
        tags = params.get("tags", [])

        doc_id = f"foto_{datetime.now().timestamp()}"

        # Analisar imagem com IA
        analise = None
        if self.tools and self.has_capability("analisar_imagem"):
            result = await self.tools.execute(
                "call_mcp", mcp_name="mcp-vision-ai",
                method="analisar_imagem", params={"url": url}
            )
            analise = result

        doc = DocumentacaoVisual(
            id=doc_id,
            tipo="foto",
            url=url,
            timestamp=datetime.now(),
            registrado_por=registrado_por,
            contexto=contexto,
            contexto_id=contexto_id,
            analise_ia=analise,
            tags=tags
        )
        self._documentacao[doc_id] = doc

        # Associar ao contexto
        if contexto == "nc" and contexto_id in self._nao_conformidades:
            self._nao_conformidades[contexto_id].fotos.append(url)

        return {
            "success": True,
            "doc_id": doc_id,
            "analise_ia": analise,
            "tags_detectadas": analise.get("tags", []) if analise else []
        }

    async def _registrar_video(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Registrar vídeo"""
        url = params.get("url")
        contexto = params.get("contexto")
        contexto_id = params.get("contexto_id")
        registrado_por = params.get("registrado_por")
        duracao = params.get("duracao_segundos", 0)

        doc_id = f"video_{datetime.now().timestamp()}"

        doc = DocumentacaoVisual(
            id=doc_id,
            tipo="video",
            url=url,
            timestamp=datetime.now(),
            registrado_por=registrado_por,
            contexto=contexto,
            contexto_id=contexto_id,
            metadata={"duracao_segundos": duracao}
        )
        self._documentacao[doc_id] = doc

        # Associar ao contexto
        if contexto == "nc" and contexto_id in self._nao_conformidades:
            self._nao_conformidades[contexto_id].videos.append(url)

        return {
            "success": True,
            "doc_id": doc_id,
            "duracao": duracao
        }

    async def _analisar_imagem(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Analisar imagem com IA"""
        url = params.get("url")
        tipo_analise = params.get("tipo", "geral")  # geral, nc, seguranca

        if not self.tools:
            return {"error": "Tools não configurados"}

        result = await self.tools.execute(
            "call_mcp", mcp_name="mcp-vision-ai",
            method="analisar_imagem",
            params={"url": url, "tipo": tipo_analise}
        )

        # Se detectar problema, sugerir criar NC
        sugestao_nc = None
        if result.get("problemas_detectados"):
            sugestao_nc = {
                "titulo": result.get("descricao_problema"),
                "categoria": result.get("categoria_sugerida"),
                "severidade": result.get("severidade_sugerida")
            }

        return {
            "success": True,
            "analise": result,
            "sugestao_nc": sugestao_nc
        }

    async def _listar_documentacao(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Listar documentação visual"""
        contexto = params.get("contexto")
        contexto_id = params.get("contexto_id")
        tipo = params.get("tipo")
        limite = params.get("limite", 50)

        docs = list(self._documentacao.values())

        if contexto:
            docs = [d for d in docs if d.contexto == contexto]
        if contexto_id:
            docs = [d for d in docs if d.contexto_id == contexto_id]
        if tipo:
            docs = [d for d in docs if d.tipo == tipo]

        docs = sorted(docs, key=lambda x: x.timestamp, reverse=True)[:limite]

        return {
            "success": True,
            "total": len(docs),
            "documentos": [
                {
                    "id": d.id,
                    "tipo": d.tipo,
                    "url": d.url,
                    "timestamp": d.timestamp.isoformat(),
                    "contexto": d.contexto,
                    "contexto_id": d.contexto_id,
                    "tags": d.tags,
                    "analise_ia": d.analise_ia is not None
                }
                for d in docs
            ]
        }

    # ==================== MÉTODOS DE SEGURANÇA DO PORTEIRO ====================

    async def _checkin_porteiro(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Check-in do porteiro"""
        porteiro_id = params.get("porteiro_id")
        nome = params.get("nome")
        dispositivo_id = params.get("dispositivo_id")
        localizacao = params.get("localizacao", "portaria_principal")

        if porteiro_id not in self._porteiros:
            self._porteiros[porteiro_id] = PorteiroStatus(
                porteiro_id=porteiro_id,
                nome=nome,
                status=StatusPorteiro.ATIVO,
                ultimo_checkin=datetime.now(),
                localizacao=localizacao,
                dispositivo_id=dispositivo_id
            )
        else:
            self._porteiros[porteiro_id].status = StatusPorteiro.ATIVO
            self._porteiros[porteiro_id].ultimo_checkin = datetime.now()
            self._porteiros[porteiro_id].localizacao = localizacao

        # Agendar wellness check
        if self.config["wellness_check_ativo"]:
            asyncio.create_task(
                self._agendar_wellness_check(porteiro_id)
            )

        return {
            "success": True,
            "porteiro_id": porteiro_id,
            "status": "ativo",
            "proximo_wellness": self._wellness_interval_minutes
        }

    async def _agendar_wellness_check(self, porteiro_id: str):
        """Agenda verificação periódica do porteiro"""
        await asyncio.sleep(self._wellness_interval_minutes * 60)

        if porteiro_id in self._porteiros:
            porteiro = self._porteiros[porteiro_id]
            tempo_sem_atividade = (datetime.now() - porteiro.ultimo_checkin).seconds // 60

            if tempo_sem_atividade >= self._wellness_interval_minutes:
                # Enviar notificação de wellness
                if self.tools:
                    await self.tools.execute(
                        "send_notification",
                        user_ids=[porteiro_id],
                        title="Wellness Check",
                        message="Tudo bem? Confirme sua presença.",
                        channels=["push"],
                        actions=[
                            {"label": "Estou bem", "action": "wellness_ok"},
                            {"label": "Preciso de ajuda", "action": "wellness_help"}
                        ]
                    )

                # Criar alerta
                alerta = AlertaPorteiro(
                    id=f"wellness_{datetime.now().timestamp()}",
                    tipo=TipoAlertaPorteiro.WELLNESS_CHECK,
                    porteiro_id=porteiro_id,
                    timestamp=datetime.now()
                )
                self._alertas_porteiro.append(alerta)

    async def _wellness_check(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Responder wellness check"""
        porteiro_id = params.get("porteiro_id")
        resposta = params.get("resposta")  # ok, help

        if porteiro_id in self._porteiros:
            self._porteiros[porteiro_id].ultimo_checkin = datetime.now()

        if resposta == "help":
            # Acionar protocolo de ajuda
            return await self._botao_panico({
                "porteiro_id": porteiro_id,
                "tipo": "emergencia_medica"
            }, context)

        return {
            "success": True,
            "status": "wellness_confirmado",
            "proximo_check_minutos": self._wellness_interval_minutes
        }

    async def _botao_panico(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Acionar botão de pânico"""
        porteiro_id = params.get("porteiro_id")
        tipo = params.get("tipo", "panico")
        localizacao = params.get("localizacao")
        coordenadas = params.get("coordenadas")
        silencioso = params.get("silencioso", self.config["panico_silencioso"])

        alerta = AlertaPorteiro(
            id=f"panico_{datetime.now().timestamp()}",
            tipo=TipoAlertaPorteiro[tipo.upper()],
            porteiro_id=porteiro_id,
            timestamp=datetime.now(),
            localizacao=localizacao,
            coordenadas=tuple(coordenadas) if coordenadas else None
        )
        self._alertas_porteiro.append(alerta)

        if porteiro_id in self._porteiros:
            self._porteiros[porteiro_id].status = StatusPorteiro.EMERGENCIA

        # Notificar supervisão e segurança
        if self.tools:
            await self.tools.execute(
                "send_notification",
                user_ids=["supervisao", "seguranca", "sindico"],
                title=f"EMERGÊNCIA: {tipo.upper()}",
                message=f"Porteiro {porteiro_id} acionou pânico!\nLocal: {localizacao}",
                channels=["push", "sms", "call"],
                priority="urgent"
            )

        # Colaborar com agente de emergência
        if self.has_capability("agent_collaboration"):
            await self.send_message(
                f"emergencia_{self.condominio_id}",
                {
                    "action": "alerta_panico",
                    "porteiro_id": porteiro_id,
                    "tipo": tipo,
                    "localizacao": localizacao,
                    "silencioso": silencioso
                }
            )

        # Ativar câmeras da área
        if self.tools:
            await self.tools.execute(
                "call_mcp", mcp_name="mcp-hikvision-cftv",
                method="iniciar_gravacao_emergencia",
                params={"area": localizacao or "portaria_principal"}
            )

        return {
            "success": True,
            "alerta_id": alerta.id,
            "tipo": tipo,
            "protocolo_ativado": True,
            "notificacoes_enviadas": ["supervisao", "seguranca", "sindico"],
            "cameras_ativadas": True
        }

    async def _codigo_coacao_func(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Verificar código de coação (porteiro sob ameaça)"""
        porteiro_id = params.get("porteiro_id")
        codigo = params.get("codigo")

        if codigo == self._codigo_coacao:
            # Código de coação detectado - acionar silenciosamente
            return await self._botao_panico({
                "porteiro_id": porteiro_id,
                "tipo": "coacao",
                "silencioso": True
            }, context)

        return {
            "success": True,
            "validado": False
        }

    async def _status_porteiros(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Status de todos os porteiros"""
        return {
            "success": True,
            "porteiros": [
                {
                    "id": p.porteiro_id,
                    "nome": p.nome,
                    "status": p.status.value,
                    "ultimo_checkin": p.ultimo_checkin.isoformat(),
                    "localizacao": p.localizacao,
                    "ronda_atual": p.ronda_atual
                }
                for p in self._porteiros.values()
            ],
            "alertas_ativos": [
                {
                    "id": a.id,
                    "tipo": a.tipo.value,
                    "porteiro": a.porteiro_id,
                    "timestamp": a.timestamp.isoformat(),
                    "resolvido": a.resolvido
                }
                for a in self._alertas_porteiro if not a.resolvido
            ]
        }

    # ==================== MÉTODOS DE ATENDIMENTO OMNICHANNEL ====================

    async def _nova_conversa(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Iniciar nova conversa"""
        canal = params.get("canal", "app")
        usuario_id = params.get("usuario_id")
        usuario_nome = params.get("usuario_nome", "Visitante")
        mensagem_inicial = params.get("mensagem")

        conversa_id = f"conv_{datetime.now().timestamp()}"

        conversa = Conversacao(
            id=conversa_id,
            canal=CanalAtendimento[canal.upper()],
            usuario_id=usuario_id,
            usuario_nome=usuario_nome,
            status=StatusConversacao.BOT,
            timestamp_inicio=datetime.now(),
            timestamp_ultima_msg=datetime.now(),
            mensagens=[{
                "de": usuario_id,
                "texto": mensagem_inicial,
                "timestamp": datetime.now().isoformat()
            }] if mensagem_inicial else []
        )
        self._conversacoes[conversa_id] = conversa

        # Processar mensagem inicial com IA
        resposta = None
        if mensagem_inicial and self.config["ia_primeiro"]:
            result = await self._processar_mensagem({
                "conversa_id": conversa_id,
                "mensagem": mensagem_inicial
            }, context)
            resposta = result.get("resposta")

        return {
            "success": True,
            "conversa_id": conversa_id,
            "canal": canal,
            "status": "bot",
            "resposta_ia": resposta
        }

    async def _processar_mensagem(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Processar mensagem do usuário"""
        conversa_id = params.get("conversa_id")
        mensagem = params.get("mensagem")

        if conversa_id not in self._conversacoes:
            return {"error": "Conversa não encontrada"}

        conversa = self._conversacoes[conversa_id]
        conversa.timestamp_ultima_msg = datetime.now()

        conversa.mensagens.append({
            "de": conversa.usuario_id,
            "texto": mensagem,
            "timestamp": datetime.now().isoformat()
        })

        # Se já escalou para humano, não processar com IA
        if conversa.status == StatusConversacao.HUMANO:
            return {
                "success": True,
                "status": "aguardando_atendente",
                "atendente": conversa.atendente_humano
            }

        # Processar com IA
        resposta = None
        escalar = False

        if self.llm:
            historico = "\n".join([
                f"{m['de']}: {m['texto']}"
                for m in conversa.mensagens[-10:]
            ])

            prompt = f"""Você é o assistente da portaria. Responda de forma cordial e útil.
Canal: {conversa.canal.value}
Usuário: {conversa.usuario_nome}

Histórico:
{historico}

Responda a última mensagem. Se não conseguir resolver ou for assunto sensível,
responda com [ESCALAR] no início.
"""
            resposta = await self.llm.generate(self.get_system_prompt(), prompt)

            if "[ESCALAR]" in resposta:
                escalar = True
                resposta = resposta.replace("[ESCALAR]", "").strip()

        conversa.mensagens.append({
            "de": "bot",
            "texto": resposta or "Entendido. Um momento.",
            "timestamp": datetime.now().isoformat()
        })

        # Escalar se necessário
        if escalar or (datetime.now() - conversa.timestamp_inicio).seconds > self.config["tempo_escalacao_segundos"]:
            await self._escalar_humano({"conversa_id": conversa_id}, context)

        return {
            "success": True,
            "resposta": resposta,
            "escalar": escalar,
            "status": conversa.status.value
        }

    async def _escalar_humano(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Escalar para atendente humano"""
        conversa_id = params.get("conversa_id")
        motivo = params.get("motivo", "Solicitação de atendimento humano")

        if conversa_id not in self._conversacoes:
            return {"error": "Conversa não encontrada"}

        conversa = self._conversacoes[conversa_id]
        conversa.status = StatusConversacao.ESCALADO

        # Adicionar à fila
        if conversa_id not in self._fila_atendimento:
            self._fila_atendimento.append(conversa_id)

        # Notificar atendentes
        if self.tools:
            await self.tools.execute(
                "send_notification",
                user_ids=["atendentes"],
                title="Nova conversa na fila",
                message=f"Canal: {conversa.canal.value}\nUsuário: {conversa.usuario_nome}\nMotivo: {motivo}",
                channels=["push"]
            )

        return {
            "success": True,
            "conversa_id": conversa_id,
            "status": "escalado",
            "posicao_fila": self._fila_atendimento.index(conversa_id) + 1
        }

    async def _finalizar_conversa(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Finalizar conversa"""
        conversa_id = params.get("conversa_id")
        satisfacao = params.get("satisfacao")  # 1-5

        if conversa_id not in self._conversacoes:
            return {"error": "Conversa não encontrada"}

        conversa = self._conversacoes[conversa_id]
        conversa.status = StatusConversacao.RESOLVIDO
        conversa.satisfacao = satisfacao

        # Remover da fila se estiver
        if conversa_id in self._fila_atendimento:
            self._fila_atendimento.remove(conversa_id)

        return {
            "success": True,
            "conversa_id": conversa_id,
            "status": "resolvido",
            "duracao_minutos": (datetime.now() - conversa.timestamp_inicio).seconds // 60,
            "total_mensagens": len(conversa.mensagens),
            "satisfacao": satisfacao
        }

    async def _fila_atendimento_func(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Ver fila de atendimento"""
        return {
            "success": True,
            "tamanho_fila": len(self._fila_atendimento),
            "conversas": [
                {
                    "id": cid,
                    "canal": self._conversacoes[cid].canal.value,
                    "usuario": self._conversacoes[cid].usuario_nome,
                    "tempo_espera_minutos": (datetime.now() - self._conversacoes[cid].timestamp_inicio).seconds // 60,
                    "mensagens": len(self._conversacoes[cid].mensagens)
                }
                for cid in self._fila_atendimento
                if cid in self._conversacoes
            ]
        }

    # ==================== ANÁLISES E DASHBOARD ====================

    async def _analise_fluxo(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        if not self.has_capability("portaria_cognitiva"):
            return {"error": "Capacidade transcendente não disponível"}

        periodo = params.get("periodo", "dia")

        total_atendimentos = len(self._atendimentos)
        por_tipo = {}
        for a in self._atendimentos.values():
            tipo = a.tipo.value
            por_tipo[tipo] = por_tipo.get(tipo, 0) + 1

        if self.llm:
            prompt = f"""Analise o fluxo da portaria virtual ULTRA:
Total de atendimentos: {total_atendimentos}
Por tipo: {por_tipo}
Período: {periodo}
Rondas realizadas: {len(self._historico_rondas)}
NCs abertas: {len([nc for nc in self._nao_conformidades.values() if nc.status == StatusNC.ABERTA])}
Conversas ativas: {len([c for c in self._conversacoes.values() if c.status not in [StatusConversacao.RESOLVIDO, StatusConversacao.ABANDONADO]])}

Gere análise TRANSCENDENTE com:
1. Padrões de fluxo
2. Eficiência das rondas
3. Áreas com mais NCs
4. Qualidade do atendimento
5. Recomendações de otimização
"""
            response = await self.llm.generate(self.get_system_prompt(), prompt)
            return {"success": True, "analise": response}

        return {
            "success": True,
            "total_atendimentos": total_atendimentos,
            "por_tipo": por_tipo
        }

    async def _dashboard_portaria(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Dashboard completo da portaria"""
        agora = datetime.now()

        # Atendimentos
        atendimentos_hoje = [a for a in self._atendimentos.values()
                           if a.timestamp_inicio.date() == agora.date()]

        # Rondas
        rondas_hoje = [r for r in self._historico_rondas
                      if r.inicio.date() == agora.date()]
        rondas_ativas = len(self._rondas_execucao)

        # NCs
        ncs_abertas = len([nc for nc in self._nao_conformidades.values()
                         if nc.status not in [StatusNC.CORRIGIDA, StatusNC.ARQUIVADA]])
        ncs_criticas = len([nc for nc in self._nao_conformidades.values()
                          if nc.severidade == SeveridadeNC.CRITICA
                          and nc.status not in [StatusNC.CORRIGIDA, StatusNC.ARQUIVADA]])

        # Porteiros
        porteiros_ativos = len([p for p in self._porteiros.values()
                               if p.status in [StatusPorteiro.ATIVO, StatusPorteiro.EM_RONDA]])
        alertas_ativos = len([a for a in self._alertas_porteiro if not a.resolvido])

        # Atendimento
        fila = len(self._fila_atendimento)
        conversas_ativas = len([c for c in self._conversacoes.values()
                               if c.status not in [StatusConversacao.RESOLVIDO, StatusConversacao.ABANDONADO]])

        return {
            "success": True,
            "timestamp": agora.isoformat(),
            "atendimento": {
                "total_hoje": len(atendimentos_hoje),
                "por_tipo": {
                    tipo.value: len([a for a in atendimentos_hoje if a.tipo == tipo])
                    for tipo in TipoAtendimento
                },
                "em_andamento": len([a for a in self._atendimentos.values()
                                    if a.status == StatusAtendimento.EM_ATENDIMENTO])
            },
            "rondas": {
                "ativas": rondas_ativas,
                "concluidas_hoje": len(rondas_hoje),
                "checkpoints_total": len(self._checkpoints),
                "rotas_ativas": len([r for r in self._rotas.values() if r.ativa])
            },
            "nao_conformidades": {
                "abertas": ncs_abertas,
                "criticas": ncs_criticas,
                "hoje": len([nc for nc in self._nao_conformidades.values()
                            if nc.timestamp_abertura.date() == agora.date()])
            },
            "seguranca": {
                "porteiros_ativos": porteiros_ativos,
                "alertas_ativos": alertas_ativos,
                "total_porteiros": len(self._porteiros)
            },
            "omnichannel": {
                "fila": fila,
                "conversas_ativas": conversas_ativas,
                "total_conversas_hoje": len([c for c in self._conversacoes.values()
                                            if c.timestamp_inicio.date() == agora.date()])
            },
            "gamificacao": {
                "top_porteiro": max(self._pontuacao_porteiros.items(),
                                   key=lambda x: x[1])[0] if self._pontuacao_porteiros else None,
                "total_pontos_hoje": sum(r.pontuacao for r in rondas_hoje)
            }
        }

    async def _chat(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        if self.llm:
            response = await self.llm.generate(
                self.get_system_prompt(), params.get("message", "")
            )
            return {"success": True, "response": response}
        return {"error": "LLM não configurado"}


# ==================== FACTORY FUNCTION ====================

def create_virtual_doorman_agent(
    condominio_id: str,
    llm_client: UnifiedLLMClient = None,
    memory: UnifiedMemorySystem = None,
    tools: ToolRegistry = None,
    evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT
) -> AgentePortariaVirtual:
    """Factory function para criar agente de portaria virtual ULTRA"""
    return AgentePortariaVirtual(
        condominio_id=condominio_id,
        llm_client=llm_client or UnifiedLLMClient(),
        memory=memory,
        tools=tools,
        evolution_level=evolution_level
    )
