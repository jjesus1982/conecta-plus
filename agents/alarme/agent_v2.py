"""
Conecta Plus - Agente de Alarme (Nível 7)
Sistema inteligente de alarme e sensores

Capacidades:
1. REATIVO: Armar/desarmar, verificar status, bypass de zonas
2. PROATIVO: Alertar intrusões, monitorar sensores, heartbeat
3. PREDITIVO: Prever falhas, identificar padrões, detectar falsos alarmes
4. AUTÔNOMO: Acionar sirene, notificar emergência, escalar eventos
5. EVOLUTIVO: Aprender horários normais, ajustar sensibilidade
6. COLABORATIVO: Integrar CFTV, Acesso, Portaria, Emergência
7. TRANSCENDENTE: Segurança preditiva total, análise comportamental

Integrações:
- Centrais: JFL, Intelbras, Paradox, DSC, Honeywell
- Protocolo Contact ID para monitoramento 24h
- Cerca elétrica com monitoramento de tensão
- PGMs (saídas programáveis)
- Geofencing para auto-arme
"""

import asyncio
import json
import logging
import hashlib
from datetime import datetime, timedelta, time
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

from ..core.base_agent import (
    BaseAgent, EvolutionLevel, Priority, AgentCapability,
    AgentContext, AgentAction, AgentPrediction,
)
from ..core.memory_store import UnifiedMemorySystem
from ..core.llm_client import UnifiedLLMClient
from ..core.tools import ToolRegistry

logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS - Estados e Tipos
# ============================================================================

class StatusAlarme(Enum):
    DESARMADO = "desarmado"
    ARMADO_TOTAL = "armado_total"
    ARMADO_PARCIAL = "armado_parcial"
    ARMADO_STAY = "armado_stay"  # Em casa
    ARMADO_AWAY = "armado_away"  # Ausente
    ARMADO_NOTURNO = "armado_noturno"
    DISPARADO = "disparado"
    EM_TESTE = "em_teste"
    EM_MANUTENCAO = "em_manutencao"
    FALHA_COMUNICACAO = "falha_comunicacao"


class TipoSensor(Enum):
    INFRAVERMELHO = "infravermelho"
    INFRAVERMELHO_PET = "infravermelho_pet"
    MAGNETICO = "magnetico"
    PRESENCA = "presenca"
    FUMACA = "fumaca"
    GAS = "gas"
    INUNDACAO = "inundacao"
    PANICO = "panico"
    PANICO_SILENCIOSO = "panico_silencioso"
    CERCA_ELETRICA = "cerca_eletrica"
    QUEBRA_VIDRO = "quebra_vidro"
    BARREIRA_IR = "barreira_ir"
    SISMICO = "sismico"
    CORTINA_IR = "cortina_ir"
    DUPLA_TECNOLOGIA = "dupla_tecnologia"
    FOTOELETRICO = "fotoeletrico"


class TipoEvento(Enum):
    DISPARO = "disparo"
    ARME = "arme"
    DESARME = "desarme"
    ARME_FORCADO = "arme_forcado"
    DESARME_COACAO = "desarme_coacao"
    FALHA = "falha"
    RESTAURACAO = "restauracao"
    BATERIA_BAIXA = "bateria_baixa"
    BATERIA_OK = "bateria_ok"
    FALTA_AC = "falta_ac"
    RETORNO_AC = "retorno_ac"
    TAMPER = "tamper"
    TAMPER_RESTAURADO = "tamper_restaurado"
    PANICO = "panico"
    PANICO_SILENCIOSO = "panico_silencioso"
    INCENDIO = "incendio"
    MEDICO = "medico"
    TESTE_PERIODICO = "teste_periodico"
    FALHA_COMUNICACAO = "falha_comunicacao"
    BYPASS = "bypass"
    BYPASS_REMOVIDO = "bypass_removido"
    ZONA_ABERTA = "zona_aberta"
    CERCA_DISPARO = "cerca_disparo"
    CERCA_CORTE = "cerca_corte"
    CERCA_CURTO = "cerca_curto"


class TipoCentral(Enum):
    JFL_ACTIVE = "jfl_active"
    JFL_SMARTCLOUD = "jfl_smartcloud"
    INTELBRAS_AMT = "intelbras_amt"
    INTELBRAS_CLOUD = "intelbras_cloud"
    PARADOX_EVO = "paradox_evo"
    DSC_POWERSERIES = "dsc_powerseries"
    HONEYWELL_VISTA = "honeywell_vista"
    GENERICA = "generica"


class NivelSeveridade(Enum):
    INFO = 1
    BAIXA = 2
    MEDIA = 3
    ALTA = 4
    CRITICA = 5
    EMERGENCIA = 6


class StatusPGM(Enum):
    DESLIGADO = "desligado"
    LIGADO = "ligado"
    PULSADO = "pulsado"


# ============================================================================
# DATACLASSES - Estruturas de Dados
# ============================================================================

@dataclass
class Zona:
    """Representa uma zona do sistema de alarme"""
    id: str
    nome: str
    tipo: TipoSensor
    particao: int
    numero: int  # Número físico na central
    ativa: bool = True
    bypass: bool = False
    aberta: bool = False
    tamper: bool = False
    bateria_baixa: bool = False
    ultimo_disparo: Optional[datetime] = None
    disparos_24h: int = 0
    tempo_resposta_ms: int = 0
    sensibilidade: int = 3  # 1-5
    localizacao: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "nome": self.nome,
            "tipo": self.tipo.value,
            "particao": self.particao,
            "numero": self.numero,
            "ativa": self.ativa,
            "bypass": self.bypass,
            "aberta": self.aberta,
            "tamper": self.tamper,
            "bateria_baixa": self.bateria_baixa,
            "ultimo_disparo": self.ultimo_disparo.isoformat() if self.ultimo_disparo else None,
            "disparos_24h": self.disparos_24h,
            "localizacao": self.localizacao,
        }


@dataclass
class Particao:
    """Representa uma partição do sistema"""
    id: int
    nome: str
    status: StatusAlarme = StatusAlarme.DESARMADO
    zonas: List[str] = field(default_factory=list)
    tempo_entrada: int = 30
    tempo_saida: int = 45
    sirene_interna: bool = True
    sirene_externa: bool = True
    auto_arme: bool = False
    horario_auto_arme: Optional[time] = None
    usuarios_permitidos: List[str] = field(default_factory=list)
    ultimo_arme: Optional[datetime] = None
    ultimo_desarme: Optional[datetime] = None
    armado_por: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "nome": self.nome,
            "status": self.status.value,
            "zonas": self.zonas,
            "tempo_entrada": self.tempo_entrada,
            "tempo_saida": self.tempo_saida,
            "ultimo_arme": self.ultimo_arme.isoformat() if self.ultimo_arme else None,
            "ultimo_desarme": self.ultimo_desarme.isoformat() if self.ultimo_desarme else None,
            "armado_por": self.armado_por,
        }


@dataclass
class EventoAlarme:
    """Evento do sistema de alarme"""
    id: str
    tipo: TipoEvento
    zona_id: Optional[str]
    particao_id: Optional[int]
    timestamp: datetime
    descricao: str
    severidade: NivelSeveridade = NivelSeveridade.MEDIA
    tratado: bool = False
    tratado_por: Optional[str] = None
    tratado_em: Optional[datetime] = None
    contact_id: Optional[str] = None  # Código Contact ID
    notificacoes_enviadas: List[str] = field(default_factory=list)
    verificado_cftv: bool = False
    falso_alarme: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tipo": self.tipo.value,
            "zona_id": self.zona_id,
            "particao_id": self.particao_id,
            "timestamp": self.timestamp.isoformat(),
            "descricao": self.descricao,
            "severidade": self.severidade.value,
            "tratado": self.tratado,
            "contact_id": self.contact_id,
            "falso_alarme": self.falso_alarme,
        }


@dataclass
class UsuarioAlarme:
    """Usuário do sistema de alarme"""
    id: str
    nome: str
    codigo: str  # Hash da senha
    keyfob_id: Optional[str] = None
    biometria_id: Optional[str] = None
    particoes_permitidas: List[int] = field(default_factory=list)
    nivel_acesso: int = 1  # 1=Usuario, 2=Master, 3=Instalador
    ativo: bool = True
    codigo_coacao: Optional[str] = None  # Senha de coação
    ultimo_acesso: Optional[datetime] = None
    tentativas_falhas: int = 0
    bloqueado_ate: Optional[datetime] = None


@dataclass
class CercaEletrica:
    """Setor de cerca elétrica"""
    id: str
    nome: str
    setor: int
    tensao_nominal: float = 8000.0  # Volts
    tensao_atual: float = 0.0
    ativa: bool = True
    disparada: bool = False
    corte_detectado: bool = False
    curto_detectado: bool = False
    ultimo_disparo: Optional[datetime] = None


@dataclass
class PGM:
    """Saída programável (PGM)"""
    id: str
    nome: str
    numero: int
    status: StatusPGM = StatusPGM.DESLIGADO
    tipo_acionamento: str = "continuo"  # continuo, pulsado, temporizado
    tempo_acionamento: int = 0  # segundos
    vinculada_evento: Optional[TipoEvento] = None


@dataclass
class ConfiguracaoAutoArme:
    """Configuração de auto-arme"""
    habilitado: bool = True
    horario: time = field(default_factory=lambda: time(23, 0))
    dias_semana: List[int] = field(default_factory=lambda: [0, 1, 2, 3, 4, 5, 6])
    modo: str = "total"  # total, parcial, noturno
    particoes: List[int] = field(default_factory=list)
    ignorar_zonas_abertas: bool = False


@dataclass
class ConfiguracaoGeofence:
    """Configuração de geofencing"""
    habilitado: bool = False
    latitude: float = 0.0
    longitude: float = 0.0
    raio_metros: int = 100
    armar_ao_sair: bool = True
    desarmar_ao_chegar: bool = True
    usuarios: List[str] = field(default_factory=list)


# ============================================================================
# CONTACT ID - Protocolo de Monitoramento
# ============================================================================

CONTACT_ID_CODES = {
    # Alarmes
    "1110": ("INCENDIO", TipoEvento.INCENDIO, NivelSeveridade.EMERGENCIA),
    "1120": ("PANICO", TipoEvento.PANICO, NivelSeveridade.EMERGENCIA),
    "1130": ("ARROMBAMENTO", TipoEvento.DISPARO, NivelSeveridade.CRITICA),
    "1131": ("PERIMETRAL", TipoEvento.DISPARO, NivelSeveridade.ALTA),
    "1132": ("INTERIOR", TipoEvento.DISPARO, NivelSeveridade.ALTA),
    "1133": ("24H", TipoEvento.DISPARO, NivelSeveridade.ALTA),
    "1134": ("ENTRADA_SAIDA", TipoEvento.DISPARO, NivelSeveridade.MEDIA),
    "1137": ("TAMPER", TipoEvento.TAMPER, NivelSeveridade.ALTA),
    "1144": ("PANICO_SILENCIOSO", TipoEvento.PANICO_SILENCIOSO, NivelSeveridade.EMERGENCIA),

    # Supervisão
    "1301": ("FALTA_AC", TipoEvento.FALTA_AC, NivelSeveridade.MEDIA),
    "1302": ("BATERIA_BAIXA", TipoEvento.BATERIA_BAIXA, NivelSeveridade.MEDIA),
    "1305": ("RESET_SISTEMA", TipoEvento.RESTAURACAO, NivelSeveridade.INFO),
    "1350": ("FALHA_COMUNICACAO", TipoEvento.FALHA_COMUNICACAO, NivelSeveridade.ALTA),

    # Arme/Desarme
    "1401": ("ARME_USUARIO", TipoEvento.ARME, NivelSeveridade.INFO),
    "1403": ("ARME_AUTO", TipoEvento.ARME, NivelSeveridade.INFO),
    "1406": ("ARME_REMOTO", TipoEvento.ARME, NivelSeveridade.INFO),
    "1407": ("ARME_FORCADO", TipoEvento.ARME_FORCADO, NivelSeveridade.BAIXA),
    "1441": ("DESARME_USUARIO", TipoEvento.DESARME, NivelSeveridade.INFO),
    "1456": ("DESARME_COACAO", TipoEvento.DESARME_COACAO, NivelSeveridade.EMERGENCIA),

    # Bypass
    "1570": ("BYPASS_ZONA", TipoEvento.BYPASS, NivelSeveridade.BAIXA),

    # Teste
    "1602": ("TESTE_PERIODICO", TipoEvento.TESTE_PERIODICO, NivelSeveridade.INFO),
}


# ============================================================================
# AGENTE PRINCIPAL
# ============================================================================

class AgenteAlarme(BaseAgent):
    """
    Agente de Alarme - Nível 7 (Transcendente)

    Gerencia sistema completo de alarme com:
    - Múltiplas partições e zonas
    - Integração com centrais JFL, Intelbras, Paradox
    - Protocolo Contact ID para monitoramento
    - Cerca elétrica
    - Análise preditiva de falsos alarmes
    - Geofencing para auto-arme
    """

    def __init__(
        self,
        condominio_id: str,
        llm_client: UnifiedLLMClient = None,
        memory: UnifiedMemorySystem = None,
        tools: ToolRegistry = None,
        evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT,
    ):
        super().__init__(
            agent_id=f"alarme_{condominio_id}",
            agent_type="alarme",
            condominio_id=condominio_id,
            evolution_level=evolution_level,
            llm_client=llm_client,
            memory_store=memory,
        )
        self.tools = tools

        # Estruturas de dados
        self._zonas: Dict[str, Zona] = {}
        self._particoes: Dict[int, Particao] = {}
        self._usuarios: Dict[str, UsuarioAlarme] = {}
        self._eventos: List[EventoAlarme] = []
        self._cercas: Dict[str, CercaEletrica] = {}
        self._pgms: Dict[str, PGM] = {}

        # Configurações
        self._tipo_central: TipoCentral = TipoCentral.JFL_SMARTCLOUD
        self._auto_arme: ConfiguracaoAutoArme = ConfiguracaoAutoArme()
        self._geofence: ConfiguracaoGeofence = ConfiguracaoGeofence()

        # Estatísticas e análise
        self._disparos_por_zona: Dict[str, List[datetime]] = defaultdict(list)
        self._padroes_falsos_alarmes: Dict[str, int] = defaultdict(int)
        self._horarios_normais: Dict[str, List[Tuple[time, time]]] = {}

        # Estado
        self._sirene_ativa: bool = False
        self._tempo_entrada_ativo: bool = False
        self._countdown_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._ultimo_heartbeat: Optional[datetime] = None

        # Configurações gerais
        self.config = {
            "tempo_entrada_padrao": 30,
            "tempo_saida_padrao": 45,
            "tentativas_senha_max": 3,
            "tempo_bloqueio": 300,  # 5 minutos
            "sirene_duracao": 180,  # 3 minutos
            "heartbeat_intervalo": 60,  # 1 minuto
            "monitoramento_24h": True,
            "verificacao_cftv": True,
            "notificar_bateria_baixa": True,
            "limiar_falso_alarme": 3,  # Disparos na mesma zona em 1h
        }

    def _register_capabilities(self) -> None:
        """Registra capacidades do agente"""
        # Nível 1 - Reativo
        self._capabilities["armar_desarmar"] = AgentCapability(
            name="armar_desarmar",
            description="Armar e desarmar partições do alarme",
            level=EvolutionLevel.REACTIVE
        )
        self._capabilities["verificar_status"] = AgentCapability(
            name="verificar_status",
            description="Verificar status completo do sistema",
            level=EvolutionLevel.REACTIVE
        )
        self._capabilities["gerenciar_zonas"] = AgentCapability(
            name="gerenciar_zonas",
            description="Gerenciar zonas e bypass",
            level=EvolutionLevel.REACTIVE
        )

        # Nível 2 - Proativo
        self._capabilities["alertar_intrusao"] = AgentCapability(
            name="alertar_intrusao",
            description="Alertar sobre intrusões e disparos",
            level=EvolutionLevel.PROACTIVE
        )
        self._capabilities["monitorar_sensores"] = AgentCapability(
            name="monitorar_sensores",
            description="Monitorar saúde dos sensores",
            level=EvolutionLevel.PROACTIVE
        )
        self._capabilities["heartbeat"] = AgentCapability(
            name="heartbeat",
            description="Heartbeat para monitoramento 24h",
            level=EvolutionLevel.PROACTIVE
        )

        # Nível 3 - Preditivo
        self._capabilities["prever_falhas"] = AgentCapability(
            name="prever_falhas",
            description="Prever falhas de sensores e bateria",
            level=EvolutionLevel.PREDICTIVE
        )
        self._capabilities["detectar_falsos_alarmes"] = AgentCapability(
            name="detectar_falsos_alarmes",
            description="Detectar padrões de falsos alarmes",
            level=EvolutionLevel.PREDICTIVE
        )

        # Nível 4 - Autônomo
        self._capabilities["acionar_sirene"] = AgentCapability(
            name="acionar_sirene",
            description="Acionar sirene automaticamente",
            level=EvolutionLevel.AUTONOMOUS
        )
        self._capabilities["escalar_eventos"] = AgentCapability(
            name="escalar_eventos",
            description="Escalar eventos para autoridades",
            level=EvolutionLevel.AUTONOMOUS
        )
        self._capabilities["auto_arme"] = AgentCapability(
            name="auto_arme",
            description="Auto-arme por horário ou geofence",
            level=EvolutionLevel.AUTONOMOUS
        )

        # Nível 5 - Evolutivo
        self._capabilities["aprender_horarios"] = AgentCapability(
            name="aprender_horarios",
            description="Aprender horários normais de uso",
            level=EvolutionLevel.EVOLVING
        )
        self._capabilities["ajustar_sensibilidade"] = AgentCapability(
            name="ajustar_sensibilidade",
            description="Ajustar sensibilidade com base em padrões",
            level=EvolutionLevel.EVOLVING
        )

        # Nível 6 - Colaborativo
        self._capabilities["integracao_cftv"] = AgentCapability(
            name="integracao_cftv",
            description="Integração com CFTV para verificação",
            level=EvolutionLevel.COLLABORATIVE
        )
        self._capabilities["integracao_acesso"] = AgentCapability(
            name="integracao_acesso",
            description="Integração com controle de acesso",
            level=EvolutionLevel.COLLABORATIVE
        )

        # Nível 7 - Transcendente
        self._capabilities["seguranca_total"] = AgentCapability(
            name="seguranca_total",
            description="Segurança preditiva integrada total",
            level=EvolutionLevel.TRANSCENDENT
        )
        self._capabilities["analise_comportamental"] = AgentCapability(
            name="analise_comportamental",
            description="Análise comportamental de ameaças",
            level=EvolutionLevel.TRANSCENDENT
        )

    def get_system_prompt(self) -> str:
        """Retorna prompt do sistema"""
        zonas_resumo = f"{len(self._zonas)} zonas configuradas"
        particoes_resumo = ", ".join(
            f"P{p.id}:{p.status.value}" for p in self._particoes.values()
        )

        return f"""Você é o Agente de Alarme do Conecta Plus - Sistema de Segurança Inteligente.

IDENTIFICAÇÃO:
- ID: {self.agent_id}
- Condomínio: {self.condominio_id}
- Nível Evolutivo: {self.evolution_level.name}
- Central: {self._tipo_central.value}

ESTADO ATUAL:
- {zonas_resumo}
- Partições: {particoes_resumo or "Nenhuma configurada"}
- Sirene: {"ATIVA" if self._sirene_ativa else "Inativa"}
- Eventos pendentes: {len([e for e in self._eventos if not e.tratado])}

RESPONSABILIDADES:
1. Gerenciar arme/desarme de partições
2. Monitorar todas as zonas e sensores
3. Detectar e responder a intrusões
4. Integrar com CFTV para verificação visual
5. Gerenciar cerca elétrica
6. Enviar eventos para monitoramento 24h
7. Acionar emergências quando necessário
8. Detectar e prevenir falsos alarmes
9. Auto-arme por horário e geofence

PROTOCOLOS:
- Contact ID para comunicação com central de monitoramento
- Integração com polícia, bombeiros e ambulância
- Verificação visual obrigatória antes de despacho

PRIORIDADES:
- EMERGÊNCIA: Pânico, incêndio, invasão confirmada
- CRÍTICA: Disparo com verificação CFTV positiva
- ALTA: Disparo sem verificação, tamper
- MÉDIA: Bateria baixa, falha de comunicação
- BAIXA: Bypass, arme/desarme
"""

    async def process(self, input_data: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        """Processa requisições ao agente"""
        action = input_data.get("action", "")
        params = input_data.get("params", {})

        # Ações de arme/desarme
        if action == "armar":
            return await self._armar(params, context)
        elif action == "desarmar":
            return await self._desarmar(params, context)
        elif action == "armar_stay":
            return await self._armar_stay(params, context)
        elif action == "armar_away":
            return await self._armar_away(params, context)

        # Ações de status
        elif action == "status":
            return await self._get_status(params, context)
        elif action == "status_detalhado":
            return await self._get_status_detalhado(params, context)

        # Gestão de zonas
        elif action == "listar_zonas":
            return await self._listar_zonas(params, context)
        elif action == "bypass_zona":
            return await self._bypass_zona(params, context)
        elif action == "remover_bypass":
            return await self._remover_bypass(params, context)
        elif action == "configurar_zona":
            return await self._configurar_zona(params, context)

        # Eventos
        elif action == "evento_sensor":
            return await self._processar_evento_sensor(params, context)
        elif action == "evento_contact_id":
            return await self._processar_contact_id(params, context)
        elif action == "listar_eventos":
            return await self._listar_eventos(params, context)
        elif action == "tratar_evento":
            return await self._tratar_evento(params, context)

        # Pânico e emergência
        elif action == "panico":
            return await self._acionar_panico(params, context)
        elif action == "panico_silencioso":
            return await self._acionar_panico_silencioso(params, context)
        elif action == "emergencia":
            return await self._acionar_emergencia(params, context)

        # Cerca elétrica
        elif action == "status_cerca":
            return await self._status_cerca(params, context)
        elif action == "evento_cerca":
            return await self._processar_evento_cerca(params, context)

        # PGMs
        elif action == "acionar_pgm":
            return await self._acionar_pgm(params, context)
        elif action == "status_pgms":
            return await self._status_pgms(params, context)

        # Usuários
        elif action == "validar_senha":
            return await self._validar_senha(params, context)
        elif action == "gerenciar_usuario":
            return await self._gerenciar_usuario(params, context)

        # Análise e relatórios
        elif action == "analise_seguranca":
            return await self._analise_seguranca(params, context)
        elif action == "relatorio_eventos":
            return await self._relatorio_eventos(params, context)
        elif action == "analise_falsos_alarmes":
            return await self._analise_falsos_alarmes(params, context)

        # Configurações
        elif action == "configurar_auto_arme":
            return await self._configurar_auto_arme(params, context)
        elif action == "configurar_geofence":
            return await self._configurar_geofence(params, context)

        # Testes
        elif action == "teste_sirene":
            return await self._teste_sirene(params, context)
        elif action == "walk_test":
            return await self._walk_test(params, context)

        # Chat
        elif action == "chat":
            return await self._chat(params, context)

        else:
            return {"error": f"Ação '{action}' não reconhecida", "acoes_disponiveis": self._listar_acoes()}

    # ========================================================================
    # ARME/DESARME
    # ========================================================================

    async def _armar(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Arma uma partição"""
        particao_id = params.get("particao", 1)
        modo = params.get("modo", "total")
        senha = params.get("senha")
        usuario_id = params.get("usuario_id")
        forcado = params.get("forcado", False)

        # Validar partição
        if particao_id not in self._particoes:
            self._particoes[particao_id] = Particao(id=particao_id, nome=f"Partição {particao_id}")

        particao = self._particoes[particao_id]

        # Verificar zonas abertas
        zonas_abertas = self._verificar_zonas_abertas(particao_id)
        if zonas_abertas and not forcado:
            return {
                "success": False,
                "error": "zonas_abertas",
                "zonas": [z.to_dict() for z in zonas_abertas],
                "message": f"{len(zonas_abertas)} zona(s) aberta(s). Use forcado=true para armar mesmo assim."
            }

        # Definir status baseado no modo
        status_map = {
            "total": StatusAlarme.ARMADO_TOTAL,
            "parcial": StatusAlarme.ARMADO_PARCIAL,
            "stay": StatusAlarme.ARMADO_STAY,
            "away": StatusAlarme.ARMADO_AWAY,
            "noturno": StatusAlarme.ARMADO_NOTURNO,
        }
        novo_status = status_map.get(modo, StatusAlarme.ARMADO_TOTAL)

        # Atualizar partição
        particao.status = novo_status
        particao.ultimo_arme = datetime.now()
        particao.armado_por = usuario_id

        # Se foi forçado, fazer bypass automático
        if forcado and zonas_abertas:
            for zona in zonas_abertas:
                zona.bypass = True

        # Comunicar com central
        if self.tools:
            await self.tools.execute(
                "call_mcp",
                mcp_name="mcp-jfl-alarme",
                method="armar",
                params={
                    "particao": particao_id,
                    "modo": modo,
                    "forcado": forcado
                }
            )

        # Registrar evento
        evento = await self._registrar_evento(
            tipo=TipoEvento.ARME_FORCADO if forcado else TipoEvento.ARME,
            particao_id=particao_id,
            descricao=f"Partição {particao_id} armada em modo {modo}" +
                      (f" (forçado, {len(zonas_abertas)} zonas em bypass)" if forcado else ""),
            contact_id="1407" if forcado else "1401"
        )

        return {
            "success": True,
            "particao": particao_id,
            "status": novo_status.value,
            "modo": modo,
            "tempo_saida": particao.tempo_saida,
            "forcado": forcado,
            "zonas_bypass": len(zonas_abertas) if forcado else 0,
            "evento_id": evento.id
        }

    async def _desarmar(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Desarma uma partição"""
        particao_id = params.get("particao", 1)
        senha = params.get("senha")
        usuario_id = params.get("usuario_id")
        coacao = params.get("coacao", False)

        if particao_id not in self._particoes:
            return {"success": False, "error": "Partição não encontrada"}

        particao = self._particoes[particao_id]
        particao.status = StatusAlarme.DESARMADO
        particao.ultimo_desarme = datetime.now()

        # Cancelar tempo de entrada se ativo
        if self._countdown_task:
            self._countdown_task.cancel()
            self._tempo_entrada_ativo = False

        # Desativar sirene se ativa
        if self._sirene_ativa:
            await self._desativar_sirene()

        # Remover bypass de todas as zonas
        for zona_id in particao.zonas:
            if zona_id in self._zonas:
                self._zonas[zona_id].bypass = False

        # Evento de desarme
        tipo_evento = TipoEvento.DESARME_COACAO if coacao else TipoEvento.DESARME
        contact_id = "1456" if coacao else "1441"

        evento = await self._registrar_evento(
            tipo=tipo_evento,
            particao_id=particao_id,
            descricao=f"Partição {particao_id} desarmada" + (" (COAÇÃO!)" if coacao else ""),
            contact_id=contact_id,
            severidade=NivelSeveridade.EMERGENCIA if coacao else NivelSeveridade.INFO
        )

        # Se coação, alertar silenciosamente
        if coacao:
            await self._alertar_coacao(particao_id, usuario_id)

        # Comunicar com central
        if self.tools:
            await self.tools.execute(
                "call_mcp",
                mcp_name="mcp-jfl-alarme",
                method="desarmar",
                params={"particao": particao_id}
            )

        return {
            "success": True,
            "particao": particao_id,
            "status": "desarmado",
            "evento_id": evento.id
        }

    async def _armar_stay(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Arma em modo Stay (em casa)"""
        params["modo"] = "stay"
        return await self._armar(params, context)

    async def _armar_away(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Arma em modo Away (ausente)"""
        params["modo"] = "away"
        return await self._armar(params, context)

    # ========================================================================
    # STATUS
    # ========================================================================

    async def _get_status(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Retorna status resumido"""
        return {
            "success": True,
            "particoes": {k: v.status.value for k, v in self._particoes.items()},
            "zonas_total": len(self._zonas),
            "zonas_ativas": len([z for z in self._zonas.values() if z.ativa]),
            "zonas_bypass": len([z for z in self._zonas.values() if z.bypass]),
            "zonas_abertas": len([z for z in self._zonas.values() if z.aberta]),
            "eventos_pendentes": len([e for e in self._eventos if not e.tratado]),
            "sirene_ativa": self._sirene_ativa,
            "cercas_ok": all(not c.disparada for c in self._cercas.values()),
            "ultimo_heartbeat": self._ultimo_heartbeat.isoformat() if self._ultimo_heartbeat else None
        }

    async def _get_status_detalhado(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Retorna status detalhado completo"""
        return {
            "success": True,
            "particoes": [p.to_dict() for p in self._particoes.values()],
            "zonas": [z.to_dict() for z in self._zonas.values()],
            "eventos_recentes": [e.to_dict() for e in self._eventos[-20:]],
            "cercas": [
                {
                    "id": c.id,
                    "nome": c.nome,
                    "tensao": c.tensao_atual,
                    "status": "disparada" if c.disparada else "ok"
                }
                for c in self._cercas.values()
            ],
            "pgms": [
                {"id": p.id, "nome": p.nome, "status": p.status.value}
                for p in self._pgms.values()
            ],
            "configuracoes": {
                "central": self._tipo_central.value,
                "auto_arme": self._auto_arme.habilitado,
                "geofence": self._geofence.habilitado,
                "monitoramento_24h": self.config["monitoramento_24h"]
            }
        }

    # ========================================================================
    # ZONAS
    # ========================================================================

    async def _listar_zonas(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Lista todas as zonas"""
        particao = params.get("particao")
        tipo = params.get("tipo")

        zonas = list(self._zonas.values())

        if particao:
            zonas = [z for z in zonas if z.particao == particao]
        if tipo:
            zonas = [z for z in zonas if z.tipo.value == tipo]

        return {
            "success": True,
            "total": len(zonas),
            "zonas": [z.to_dict() for z in zonas]
        }

    async def _bypass_zona(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Coloca zona em bypass"""
        zona_id = params.get("zona_id")

        if zona_id not in self._zonas:
            return {"success": False, "error": "Zona não encontrada"}

        zona = self._zonas[zona_id]
        zona.bypass = True

        await self._registrar_evento(
            tipo=TipoEvento.BYPASS,
            zona_id=zona_id,
            descricao=f"Zona {zona.nome} em bypass",
            contact_id="1570"
        )

        return {"success": True, "zona_id": zona_id, "bypass": True}

    async def _remover_bypass(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Remove bypass da zona"""
        zona_id = params.get("zona_id")

        if zona_id not in self._zonas:
            return {"success": False, "error": "Zona não encontrada"}

        self._zonas[zona_id].bypass = False

        await self._registrar_evento(
            tipo=TipoEvento.BYPASS_REMOVIDO,
            zona_id=zona_id,
            descricao=f"Bypass removido da zona"
        )

        return {"success": True, "zona_id": zona_id, "bypass": False}

    async def _configurar_zona(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Configura uma zona"""
        zona_id = params.get("zona_id")

        if zona_id and zona_id in self._zonas:
            zona = self._zonas[zona_id]
        else:
            zona_id = params.get("id", f"zona_{len(self._zonas) + 1}")
            zona = Zona(
                id=zona_id,
                nome=params.get("nome", f"Zona {len(self._zonas) + 1}"),
                tipo=TipoSensor(params.get("tipo", "infravermelho")),
                particao=params.get("particao", 1),
                numero=params.get("numero", len(self._zonas) + 1)
            )
            self._zonas[zona_id] = zona

        # Atualizar campos
        if "nome" in params:
            zona.nome = params["nome"]
        if "sensibilidade" in params:
            zona.sensibilidade = params["sensibilidade"]
        if "localizacao" in params:
            zona.localizacao = params["localizacao"]
        if "ativa" in params:
            zona.ativa = params["ativa"]

        return {"success": True, "zona": zona.to_dict()}

    def _verificar_zonas_abertas(self, particao_id: int) -> List[Zona]:
        """Verifica zonas abertas em uma partição"""
        return [
            z for z in self._zonas.values()
            if z.particao == particao_id and z.aberta and not z.bypass
        ]

    # ========================================================================
    # EVENTOS
    # ========================================================================

    async def _processar_evento_sensor(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Processa evento de sensor"""
        zona_id = params.get("zona_id")
        tipo = TipoEvento(params.get("tipo", "disparo"))

        if zona_id and zona_id not in self._zonas:
            return {"success": False, "error": "Zona não encontrada"}

        zona = self._zonas.get(zona_id) if zona_id else None
        particao_id = zona.particao if zona else params.get("particao", 1)
        particao = self._particoes.get(particao_id)

        # Verificar se é falso alarme potencial
        is_falso_alarme = await self._detectar_falso_alarme(zona_id) if zona_id else False

        # Registrar evento
        evento = await self._registrar_evento(
            tipo=tipo,
            zona_id=zona_id,
            particao_id=particao_id,
            descricao=params.get("descricao", f"Evento {tipo.value} na zona {zona.nome if zona else 'N/A'}"),
            severidade=self._calcular_severidade(tipo, zona)
        )

        # Ações baseadas no tipo de evento e status da partição
        acoes_tomadas = []

        if tipo == TipoEvento.DISPARO and particao and particao.status != StatusAlarme.DESARMADO:
            if zona and zona.bypass:
                acoes_tomadas.append("zona_em_bypass_ignorada")
            elif is_falso_alarme:
                evento.falso_alarme = True
                acoes_tomadas.append("possivel_falso_alarme_detectado")
            else:
                # Iniciar tempo de entrada ou acionar sirene
                if zona and zona.tipo in [TipoSensor.MAGNETICO, TipoSensor.INFRAVERMELHO]:
                    if not self._tempo_entrada_ativo:
                        await self._iniciar_tempo_entrada(particao)
                        acoes_tomadas.append("tempo_entrada_iniciado")
                else:
                    await self._acionar_sirene(zona_id)
                    acoes_tomadas.append("sirene_acionada")

                # Solicitar verificação CFTV
                if self.config["verificacao_cftv"] and self.has_capability("integracao_cftv"):
                    await self._solicitar_verificacao_cftv(zona_id, evento.id)
                    acoes_tomadas.append("verificacao_cftv_solicitada")

                # Notificar
                await self._notificar_disparo(evento, zona)
                acoes_tomadas.append("notificacoes_enviadas")

        elif tipo == TipoEvento.TAMPER:
            await self._notificar_tamper(zona, evento)
            acoes_tomadas.append("alerta_tamper_enviado")

        elif tipo == TipoEvento.BATERIA_BAIXA:
            if self.config["notificar_bateria_baixa"]:
                await self._notificar_bateria_baixa(zona)
                acoes_tomadas.append("alerta_bateria_enviado")

        # Atualizar estatísticas
        if zona_id:
            self._disparos_por_zona[zona_id].append(datetime.now())
            if zona:
                zona.ultimo_disparo = datetime.now()
                zona.disparos_24h = len([
                    d for d in self._disparos_por_zona[zona_id]
                    if d > datetime.now() - timedelta(hours=24)
                ])

        return {
            "success": True,
            "evento_id": evento.id,
            "tipo": tipo.value,
            "severidade": evento.severidade.value,
            "falso_alarme": is_falso_alarme,
            "acoes_tomadas": acoes_tomadas
        }

    async def _processar_contact_id(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Processa evento no formato Contact ID"""
        codigo = params.get("codigo")
        conta = params.get("conta")
        zona = params.get("zona")
        particao = params.get("particao", 1)

        if codigo not in CONTACT_ID_CODES:
            return {"success": False, "error": f"Código Contact ID '{codigo}' desconhecido"}

        nome, tipo_evento, severidade = CONTACT_ID_CODES[codigo]

        evento = await self._registrar_evento(
            tipo=tipo_evento,
            zona_id=f"zona_{zona}" if zona else None,
            particao_id=particao,
            descricao=f"Contact ID: {nome}",
            contact_id=codigo,
            severidade=severidade
        )

        return {
            "success": True,
            "evento_id": evento.id,
            "codigo": codigo,
            "nome": nome,
            "severidade": severidade.value
        }

    async def _listar_eventos(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Lista eventos"""
        limite = params.get("limite", 50)
        apenas_pendentes = params.get("apenas_pendentes", False)
        tipo = params.get("tipo")

        eventos = self._eventos

        if apenas_pendentes:
            eventos = [e for e in eventos if not e.tratado]
        if tipo:
            eventos = [e for e in eventos if e.tipo.value == tipo]

        eventos = eventos[-limite:]

        return {
            "success": True,
            "total": len(eventos),
            "eventos": [e.to_dict() for e in eventos]
        }

    async def _tratar_evento(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Marca evento como tratado"""
        evento_id = params.get("evento_id")
        tratado_por = params.get("tratado_por")
        falso_alarme = params.get("falso_alarme", False)

        for evento in self._eventos:
            if evento.id == evento_id:
                evento.tratado = True
                evento.tratado_por = tratado_por
                evento.tratado_em = datetime.now()
                evento.falso_alarme = falso_alarme

                if falso_alarme and evento.zona_id:
                    self._padroes_falsos_alarmes[evento.zona_id] += 1

                return {"success": True, "evento_id": evento_id}

        return {"success": False, "error": "Evento não encontrado"}

    async def _registrar_evento(
        self,
        tipo: TipoEvento,
        descricao: str,
        zona_id: Optional[str] = None,
        particao_id: Optional[int] = None,
        contact_id: Optional[str] = None,
        severidade: NivelSeveridade = NivelSeveridade.MEDIA
    ) -> EventoAlarme:
        """Registra um novo evento"""
        evento = EventoAlarme(
            id=f"evt_{datetime.now().timestamp()}_{len(self._eventos)}",
            tipo=tipo,
            zona_id=zona_id,
            particao_id=particao_id,
            timestamp=datetime.now(),
            descricao=descricao,
            contact_id=contact_id,
            severidade=severidade
        )
        self._eventos.append(evento)

        # Enviar para monitoramento 24h
        if self.config["monitoramento_24h"] and contact_id:
            await self._enviar_monitoramento(evento)

        # Salvar em memória
        if self.memory:
            await self.memory.store(
                key=f"evento:{evento.id}",
                value=evento.to_dict(),
                memory_type="operational"
            )

        return evento

    # ========================================================================
    # PÂNICO E EMERGÊNCIA
    # ========================================================================

    async def _acionar_panico(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Aciona botão de pânico"""
        localizacao = params.get("localizacao", "desconhecida")
        usuario = params.get("usuario")

        # Acionar sirene
        await self._acionar_sirene(None)

        # Registrar evento crítico
        evento = await self._registrar_evento(
            tipo=TipoEvento.PANICO,
            descricao=f"PÂNICO acionado - Local: {localizacao}",
            contact_id="1120",
            severidade=NivelSeveridade.EMERGENCIA
        )

        # Notificar todos
        if self.tools:
            await self.tools.execute(
                "send_notification",
                user_ids=["portaria", "sindico", "seguranca", "zelador"],
                title="🚨 PÂNICO ACIONADO",
                message=f"Botão de pânico acionado!\nLocal: {localizacao}\nUsuário: {usuario or 'N/A'}",
                channels=["push", "sms", "whatsapp", "app"],
                priority="urgent"
            )

        # Solicitar CFTV
        if self.has_capability("integracao_cftv"):
            await self.send_message(
                f"cftv_{self.condominio_id}",
                {"action": "gravar_emergencia", "tipo": "panico", "localizacao": localizacao},
                priority=Priority.CRITICAL
            )

        return {
            "success": True,
            "evento_id": evento.id,
            "status": "panico_acionado",
            "sirene": True
        }

    async def _acionar_panico_silencioso(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Aciona pânico silencioso (sem sirene)"""
        localizacao = params.get("localizacao", "desconhecida")

        evento = await self._registrar_evento(
            tipo=TipoEvento.PANICO_SILENCIOSO,
            descricao=f"Pânico silencioso - Local: {localizacao}",
            contact_id="1144",
            severidade=NivelSeveridade.EMERGENCIA
        )

        # Notificar apenas segurança e polícia
        if self.tools:
            await self.tools.execute(
                "send_notification",
                user_ids=["seguranca"],
                title="⚠️ PÂNICO SILENCIOSO",
                message=f"Pânico silencioso acionado - {localizacao}",
                channels=["push", "sms"],
                priority="urgent"
            )

        # Gravar CFTV silenciosamente
        if self.has_capability("integracao_cftv"):
            await self.send_message(
                f"cftv_{self.condominio_id}",
                {"action": "gravar_emergencia", "tipo": "panico_silencioso", "silencioso": True},
                priority=Priority.CRITICAL
            )

        return {"success": True, "evento_id": evento.id, "status": "panico_silencioso_acionado"}

    async def _acionar_emergencia(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Aciona protocolo de emergência completo"""
        tipo = params.get("tipo", "invasao")  # invasao, incendio, medico
        localizacao = params.get("localizacao")

        # Acionar sirene para invasão/incêndio
        if tipo in ["invasao", "incendio"]:
            await self._acionar_sirene(None)

        # Determinar serviço de emergência
        servicos = {
            "invasao": ["190", "policia"],
            "incendio": ["193", "bombeiros"],
            "medico": ["192", "samu"]
        }

        evento = await self._registrar_evento(
            tipo=TipoEvento.INCENDIO if tipo == "incendio" else TipoEvento.DISPARO,
            descricao=f"EMERGÊNCIA: {tipo.upper()} - {localizacao}",
            severidade=NivelSeveridade.EMERGENCIA
        )

        return {
            "success": True,
            "evento_id": evento.id,
            "tipo_emergencia": tipo,
            "servicos_acionados": servicos.get(tipo, []),
            "sirene": tipo in ["invasao", "incendio"]
        }

    async def _alertar_coacao(self, particao_id: int, usuario_id: Optional[str]):
        """Alerta silencioso de coação"""
        if self.tools:
            await self.tools.execute(
                "send_notification",
                user_ids=["seguranca"],
                title="⚠️ ALERTA COAÇÃO",
                message=f"Desarme sob coação detectado - Partição {particao_id}",
                channels=["sms"],
                priority="urgent"
            )

    # ========================================================================
    # SIRENE
    # ========================================================================

    async def _acionar_sirene(self, zona_id: Optional[str]):
        """Aciona sirene"""
        self._sirene_ativa = True

        if self.tools:
            await self.tools.execute(
                "call_mcp",
                mcp_name="mcp-jfl-alarme",
                method="sirene",
                params={"ativar": True, "duracao": self.config["sirene_duracao"]}
            )

        # Desativar automaticamente após tempo configurado
        asyncio.create_task(self._auto_desativar_sirene())

    async def _desativar_sirene(self):
        """Desativa sirene"""
        self._sirene_ativa = False

        if self.tools:
            await self.tools.execute(
                "call_mcp",
                mcp_name="mcp-jfl-alarme",
                method="sirene",
                params={"ativar": False}
            )

    async def _auto_desativar_sirene(self):
        """Desativa sirene automaticamente após tempo"""
        await asyncio.sleep(self.config["sirene_duracao"])
        if self._sirene_ativa:
            await self._desativar_sirene()

    async def _teste_sirene(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Testa sirene brevemente"""
        duracao = params.get("duracao", 3)  # 3 segundos padrão

        if self.tools:
            await self.tools.execute(
                "call_mcp",
                mcp_name="mcp-jfl-alarme",
                method="sirene",
                params={"ativar": True, "duracao": duracao}
            )

        return {"success": True, "duracao": duracao}

    # ========================================================================
    # CERCA ELÉTRICA
    # ========================================================================

    async def _status_cerca(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Status da cerca elétrica"""
        return {
            "success": True,
            "setores": [
                {
                    "id": c.id,
                    "nome": c.nome,
                    "setor": c.setor,
                    "tensao_nominal": c.tensao_nominal,
                    "tensao_atual": c.tensao_atual,
                    "status": "normal" if not c.disparada else "disparada",
                    "corte": c.corte_detectado,
                    "curto": c.curto_detectado
                }
                for c in self._cercas.values()
            ]
        }

    async def _processar_evento_cerca(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Processa evento de cerca elétrica"""
        setor_id = params.get("setor_id")
        tipo = params.get("tipo")  # disparo, corte, curto
        tensao = params.get("tensao", 0)

        if setor_id in self._cercas:
            cerca = self._cercas[setor_id]
            cerca.tensao_atual = tensao

            if tipo == "disparo":
                cerca.disparada = True
                evento_tipo = TipoEvento.CERCA_DISPARO
            elif tipo == "corte":
                cerca.corte_detectado = True
                evento_tipo = TipoEvento.CERCA_CORTE
            elif tipo == "curto":
                cerca.curto_detectado = True
                evento_tipo = TipoEvento.CERCA_CURTO
            else:
                evento_tipo = TipoEvento.DISPARO

            cerca.ultimo_disparo = datetime.now()
        else:
            evento_tipo = TipoEvento.DISPARO

        evento = await self._registrar_evento(
            tipo=evento_tipo,
            descricao=f"Cerca elétrica: {tipo} no setor {setor_id}",
            severidade=NivelSeveridade.ALTA
        )

        # Acionar sirene
        await self._acionar_sirene(None)

        return {"success": True, "evento_id": evento.id, "tipo": tipo}

    # ========================================================================
    # PGMs
    # ========================================================================

    async def _acionar_pgm(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Aciona saída PGM"""
        pgm_id = params.get("pgm_id")
        acao = params.get("acao", "ligar")  # ligar, desligar, pulsar
        tempo = params.get("tempo", 0)

        if pgm_id not in self._pgms:
            return {"success": False, "error": "PGM não encontrada"}

        pgm = self._pgms[pgm_id]

        if acao == "ligar":
            pgm.status = StatusPGM.LIGADO
        elif acao == "desligar":
            pgm.status = StatusPGM.DESLIGADO
        elif acao == "pulsar":
            pgm.status = StatusPGM.PULSADO

        if self.tools:
            await self.tools.execute(
                "call_mcp",
                mcp_name="mcp-jfl-alarme",
                method="pgm",
                params={"numero": pgm.numero, "acao": acao, "tempo": tempo}
            )

        return {"success": True, "pgm_id": pgm_id, "status": pgm.status.value}

    async def _status_pgms(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Status das PGMs"""
        return {
            "success": True,
            "pgms": [
                {"id": p.id, "nome": p.nome, "numero": p.numero, "status": p.status.value}
                for p in self._pgms.values()
            ]
        }

    # ========================================================================
    # ANÁLISE E INTELIGÊNCIA
    # ========================================================================

    async def _detectar_falso_alarme(self, zona_id: str) -> bool:
        """Detecta possível falso alarme baseado em padrões"""
        if not self.has_capability("detectar_falsos_alarmes"):
            return False

        # Verificar disparos recentes na mesma zona
        disparos_recentes = [
            d for d in self._disparos_por_zona.get(zona_id, [])
            if d > datetime.now() - timedelta(hours=1)
        ]

        if len(disparos_recentes) >= self.config["limiar_falso_alarme"]:
            return True

        # Verificar histórico de falsos alarmes
        if self._padroes_falsos_alarmes.get(zona_id, 0) > 5:
            return True

        return False

    async def _analise_seguranca(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Análise completa de segurança"""
        if not self.has_capability("seguranca_total"):
            return {"error": "Capacidade transcendente não disponível"}

        # Coletar métricas
        eventos_24h = [e for e in self._eventos if e.timestamp > datetime.now() - timedelta(hours=24)]
        disparos = [e for e in eventos_24h if e.tipo == TipoEvento.DISPARO]
        falsos = [e for e in eventos_24h if e.falso_alarme]

        zonas_problematicas = [
            zona_id for zona_id, count in self._padroes_falsos_alarmes.items()
            if count > 3
        ]

        analise = {
            "periodo": "24h",
            "eventos_total": len(eventos_24h),
            "disparos": len(disparos),
            "falsos_alarmes": len(falsos),
            "taxa_falsos": round(len(falsos) / max(len(disparos), 1) * 100, 1),
            "zonas_problematicas": zonas_problematicas,
            "status_geral": "normal" if len(disparos) < 5 else "atenção",
        }

        # Análise LLM se disponível
        if self.llm:
            prompt = f"""Analise a segurança do sistema de alarme:

Métricas 24h:
- Eventos: {len(eventos_24h)}
- Disparos: {len(disparos)}
- Falsos alarmes: {len(falsos)}
- Zonas problemáticas: {zonas_problematicas}
- Partições: {len(self._particoes)}
- Zonas totais: {len(self._zonas)}

Gere análise de segurança com:
1. Avaliação de risco atual
2. Zonas que precisam atenção
3. Recomendações de melhoria
4. Sugestões de configuração
"""
            response = await self.llm.generate(self.get_system_prompt(), prompt)
            analise["analise_ia"] = response

        return {"success": True, **analise}

    async def _analise_falsos_alarmes(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Análise detalhada de falsos alarmes"""
        return {
            "success": True,
            "zonas_com_falsos": dict(self._padroes_falsos_alarmes),
            "recomendacoes": [
                f"Zona {z}: Verificar sensibilidade ou posicionamento"
                for z in self._padroes_falsos_alarmes.keys()
                if self._padroes_falsos_alarmes[z] > 3
            ]
        }

    async def _relatorio_eventos(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Gera relatório de eventos"""
        dias = params.get("dias", 7)
        data_inicio = datetime.now() - timedelta(days=dias)

        eventos_periodo = [e for e in self._eventos if e.timestamp > data_inicio]

        por_tipo = defaultdict(int)
        por_severidade = defaultdict(int)
        por_zona = defaultdict(int)

        for e in eventos_periodo:
            por_tipo[e.tipo.value] += 1
            por_severidade[e.severidade.name] += 1
            if e.zona_id:
                por_zona[e.zona_id] += 1

        return {
            "success": True,
            "periodo_dias": dias,
            "total_eventos": len(eventos_periodo),
            "por_tipo": dict(por_tipo),
            "por_severidade": dict(por_severidade),
            "por_zona": dict(por_zona),
            "tratados": len([e for e in eventos_periodo if e.tratado]),
            "pendentes": len([e for e in eventos_periodo if not e.tratado])
        }

    # ========================================================================
    # AUTO-ARME E GEOFENCE
    # ========================================================================

    async def _configurar_auto_arme(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Configura auto-arme"""
        self._auto_arme.habilitado = params.get("habilitado", True)

        if "horario" in params:
            h, m = map(int, params["horario"].split(":"))
            self._auto_arme.horario = time(h, m)

        if "modo" in params:
            self._auto_arme.modo = params["modo"]

        if "dias" in params:
            self._auto_arme.dias_semana = params["dias"]

        return {"success": True, "auto_arme": {
            "habilitado": self._auto_arme.habilitado,
            "horario": self._auto_arme.horario.strftime("%H:%M"),
            "modo": self._auto_arme.modo
        }}

    async def _configurar_geofence(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Configura geofencing"""
        self._geofence.habilitado = params.get("habilitado", True)
        self._geofence.latitude = params.get("latitude", 0)
        self._geofence.longitude = params.get("longitude", 0)
        self._geofence.raio_metros = params.get("raio", 100)

        return {"success": True, "geofence": {
            "habilitado": self._geofence.habilitado,
            "coordenadas": f"{self._geofence.latitude}, {self._geofence.longitude}",
            "raio": self._geofence.raio_metros
        }}

    # ========================================================================
    # TESTES
    # ========================================================================

    async def _walk_test(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Inicia modo walk test"""
        particao = params.get("particao", 1)

        if particao in self._particoes:
            self._particoes[particao].status = StatusAlarme.EM_TESTE

        return {
            "success": True,
            "modo": "walk_test",
            "particao": particao,
            "instrucoes": "Caminhe pelo ambiente. Cada sensor ativado emitirá um beep."
        }

    # ========================================================================
    # USUÁRIOS
    # ========================================================================

    async def _validar_senha(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Valida senha de usuário"""
        senha = params.get("senha")
        usuario_id = params.get("usuario_id")

        if usuario_id and usuario_id in self._usuarios:
            usuario = self._usuarios[usuario_id]

            if usuario.bloqueado_ate and datetime.now() < usuario.bloqueado_ate:
                return {"success": False, "error": "Usuário bloqueado", "bloqueado_ate": usuario.bloqueado_ate.isoformat()}

            senha_hash = hashlib.sha256(senha.encode()).hexdigest()

            if senha_hash == usuario.codigo:
                usuario.tentativas_falhas = 0
                usuario.ultimo_acesso = datetime.now()
                return {"success": True, "usuario": usuario.nome, "nivel": usuario.nivel_acesso}

            if senha_hash == usuario.codigo_coacao:
                return {"success": True, "usuario": usuario.nome, "coacao": True}

            usuario.tentativas_falhas += 1
            if usuario.tentativas_falhas >= self.config["tentativas_senha_max"]:
                usuario.bloqueado_ate = datetime.now() + timedelta(seconds=self.config["tempo_bloqueio"])

            return {"success": False, "error": "Senha incorreta", "tentativas": usuario.tentativas_falhas}

        return {"success": False, "error": "Usuário não encontrado"}

    async def _gerenciar_usuario(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Gerencia usuários do alarme"""
        acao = params.get("acao", "criar")
        usuario_id = params.get("usuario_id")

        if acao == "criar":
            novo = UsuarioAlarme(
                id=usuario_id or f"user_{len(self._usuarios)}",
                nome=params.get("nome", "Novo Usuário"),
                codigo=hashlib.sha256(params.get("senha", "1234").encode()).hexdigest(),
                nivel_acesso=params.get("nivel", 1)
            )
            self._usuarios[novo.id] = novo
            return {"success": True, "usuario_id": novo.id}

        elif acao == "remover":
            if usuario_id in self._usuarios:
                del self._usuarios[usuario_id]
                return {"success": True}

        return {"success": False, "error": "Ação inválida"}

    # ========================================================================
    # HELPERS E INTEGRAÇÕES
    # ========================================================================

    async def _iniciar_tempo_entrada(self, particao: Particao):
        """Inicia countdown de tempo de entrada"""
        self._tempo_entrada_ativo = True
        tempo = particao.tempo_entrada

        async def countdown():
            await asyncio.sleep(tempo)
            if self._tempo_entrada_ativo:
                await self._acionar_sirene(None)

        self._countdown_task = asyncio.create_task(countdown())

    async def _solicitar_verificacao_cftv(self, zona_id: str, evento_id: str):
        """Solicita verificação visual do CFTV"""
        if self.has_capability("integracao_cftv"):
            await self.send_message(
                f"cftv_{self.condominio_id}",
                {
                    "action": "verificar_alarme",
                    "zona_id": zona_id,
                    "evento_id": evento_id,
                    "prioridade": "alta"
                },
                priority=Priority.HIGH
            )

    async def _notificar_disparo(self, evento: EventoAlarme, zona: Optional[Zona]):
        """Notifica disparo de alarme"""
        if self.tools:
            await self.tools.execute(
                "send_notification",
                user_ids=["portaria", "sindico", "seguranca"],
                title="🚨 ALARME DISPARADO",
                message=f"Disparo na zona {zona.nome if zona else 'N/A'}\n{evento.descricao}",
                channels=["push", "sms", "app"],
                priority="urgent"
            )
            evento.notificacoes_enviadas.append("disparo")

    async def _notificar_tamper(self, zona: Optional[Zona], evento: EventoAlarme):
        """Notifica violação de tamper"""
        if self.tools:
            await self.tools.execute(
                "send_notification",
                user_ids=["sindico", "seguranca"],
                title="⚠️ TAMPER VIOLADO",
                message=f"Sensor violado: {zona.nome if zona else 'N/A'}",
                channels=["push", "app"],
                priority="high"
            )

    async def _notificar_bateria_baixa(self, zona: Optional[Zona]):
        """Notifica bateria baixa"""
        if self.tools and zona:
            await self.tools.execute(
                "send_notification",
                user_ids=["zelador", "manutencao"],
                title="🔋 Bateria Baixa",
                message=f"Sensor {zona.nome} com bateria baixa",
                channels=["app"],
                priority="normal"
            )

    async def _enviar_monitoramento(self, evento: EventoAlarme):
        """Envia evento para central de monitoramento"""
        if self.tools and evento.contact_id:
            await self.tools.execute(
                "call_mcp",
                mcp_name="mcp-monitoramento",
                method="enviar_evento",
                params={
                    "contact_id": evento.contact_id,
                    "evento": evento.to_dict()
                }
            )

    def _calcular_severidade(self, tipo: TipoEvento, zona: Optional[Zona]) -> NivelSeveridade:
        """Calcula severidade do evento"""
        severidades = {
            TipoEvento.PANICO: NivelSeveridade.EMERGENCIA,
            TipoEvento.PANICO_SILENCIOSO: NivelSeveridade.EMERGENCIA,
            TipoEvento.INCENDIO: NivelSeveridade.EMERGENCIA,
            TipoEvento.DESARME_COACAO: NivelSeveridade.EMERGENCIA,
            TipoEvento.DISPARO: NivelSeveridade.ALTA,
            TipoEvento.TAMPER: NivelSeveridade.ALTA,
            TipoEvento.FALHA_COMUNICACAO: NivelSeveridade.ALTA,
            TipoEvento.BATERIA_BAIXA: NivelSeveridade.MEDIA,
            TipoEvento.FALTA_AC: NivelSeveridade.MEDIA,
            TipoEvento.BYPASS: NivelSeveridade.BAIXA,
            TipoEvento.ARME: NivelSeveridade.INFO,
            TipoEvento.DESARME: NivelSeveridade.INFO,
        }
        return severidades.get(tipo, NivelSeveridade.MEDIA)

    def _listar_acoes(self) -> List[str]:
        """Lista ações disponíveis"""
        return [
            "armar", "desarmar", "armar_stay", "armar_away",
            "status", "status_detalhado",
            "listar_zonas", "bypass_zona", "remover_bypass", "configurar_zona",
            "evento_sensor", "evento_contact_id", "listar_eventos", "tratar_evento",
            "panico", "panico_silencioso", "emergencia",
            "status_cerca", "evento_cerca",
            "acionar_pgm", "status_pgms",
            "validar_senha", "gerenciar_usuario",
            "analise_seguranca", "relatorio_eventos", "analise_falsos_alarmes",
            "configurar_auto_arme", "configurar_geofence",
            "teste_sirene", "walk_test",
            "chat"
        ]

    async def _chat(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Chat com o agente via LLM"""
        if self.llm:
            response = await self.llm.generate(
                self.get_system_prompt(),
                params.get("message", "")
            )
            return {"success": True, "response": response}
        return {"error": "LLM não configurado"}


# ============================================================================
# FACTORY
# ============================================================================

def create_alarm_agent(
    condominio_id: str,
    llm_client: UnifiedLLMClient = None,
    memory: UnifiedMemorySystem = None,
    tools: ToolRegistry = None,
    evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT
) -> AgenteAlarme:
    """Cria instância do agente de alarme"""
    return AgenteAlarme(
        condominio_id=condominio_id,
        llm_client=llm_client or UnifiedLLMClient(),
        memory=memory,
        tools=tools,
        evolution_level=evolution_level
    )
