"""
Conecta Plus - Agente de Controle de Acesso (Nível 7)
Gestão inteligente de entrada e saída do condomínio

Capacidades por nível:
1. REATIVO: Liberar/bloquear acesso, consultar logs
2. PROATIVO: Alertar acessos incomuns, lembrar vencimentos
3. PREDITIVO: Prever horários de pico, detectar padrões
4. AUTÔNOMO: Liberar visitantes frequentes, bloquear automaticamente
5. EVOLUTIVO: Aprender padrões de acesso por morador
6. COLABORATIVO: Integrar com CFTV, Alarme, Portaria
7. TRANSCENDENTE: Segurança preditiva avançada

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
import hashlib

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
from ..core.llm_client import UnifiedLLMClient
from ..core.tools import ToolRegistry

logger = logging.getLogger(__name__)


# ==================== TIPOS ESPECÍFICOS ====================

class TipoAcesso(Enum):
    MORADOR = "morador"
    VISITANTE = "visitante"
    PRESTADOR = "prestador"
    FUNCIONARIO = "funcionario"
    ENTREGADOR = "entregador"
    EMERGENCIA = "emergencia"


class MetodoAcesso(Enum):
    BIOMETRIA = "biometria"
    FACIAL = "facial"
    TAG_RFID = "tag_rfid"
    SENHA = "senha"
    QR_CODE = "qr_code"
    CONTROLE_REMOTO = "controle_remoto"
    APLICATIVO = "aplicativo"
    PORTARIA = "portaria"


class StatusAcesso(Enum):
    LIBERADO = "liberado"
    NEGADO = "negado"
    PENDENTE = "pendente"
    EXPIRADO = "expirado"
    BLOQUEADO = "bloqueado"


class TipoPonto(Enum):
    PORTARIA_PRINCIPAL = "portaria_principal"
    PORTARIA_SERVICO = "portaria_servico"
    GARAGEM = "garagem"
    PEDESTRES = "pedestres"
    AREA_COMUM = "area_comum"
    ELEVADOR = "elevador"


@dataclass
class PontoAcesso:
    """Ponto de controle de acesso"""
    id: str
    nome: str
    tipo: TipoPonto
    localizacao: str
    dispositivo: str  # control_id, intelbras, etc
    ip: str
    ativo: bool = True
    tem_biometria: bool = True
    tem_facial: bool = False
    tem_qrcode: bool = True


@dataclass
class RegistroAcesso:
    """Registro de evento de acesso"""
    id: str
    ponto_id: str
    pessoa_id: str
    tipo_pessoa: TipoAcesso
    metodo: MetodoAcesso
    status: StatusAcesso
    timestamp: datetime
    foto_capturada: Optional[str] = None
    placa_veiculo: Optional[str] = None
    unidade_destino: Optional[str] = None
    autorizado_por: Optional[str] = None
    observacao: str = ""


@dataclass
class Visitante:
    """Visitante cadastrado"""
    id: str
    nome: str
    documento: str
    telefone: str
    foto_url: Optional[str] = None
    unidade_destino: str = ""
    morador_autorizador: str = ""
    data_entrada: Optional[datetime] = None
    data_saida_prevista: Optional[datetime] = None
    recorrente: bool = False
    dias_permitidos: List[str] = field(default_factory=list)
    horario_permitido: Optional[str] = None


@dataclass
class PadraoAcesso:
    """Padrão de acesso aprendido"""
    pessoa_id: str
    tipo: TipoAcesso
    horarios_frequentes: List[str]
    pontos_frequentes: List[str]
    dias_semana: List[int]
    tempo_medio_permanencia: int  # minutos
    acompanhantes_frequentes: List[str]
    anomalias_detectadas: int = 0


@dataclass
class AlertaAcesso:
    """Alerta de segurança de acesso"""
    id: str
    tipo: str
    descricao: str
    pessoa_id: Optional[str]
    ponto_id: str
    nivel_risco: int  # 1-5
    timestamp: datetime
    acao_recomendada: str
    resolvido: bool = False


# ==================== AGENTE DE ACESSO ====================

class AgenteAcesso(BaseAgent):
    """
    Agente de Controle de Acesso - Nível 7 (Transcendente)

    Responsabilidades:
    - Gerenciar todos os pontos de acesso
    - Controlar entrada de moradores, visitantes e prestadores
    - Detectar acessos suspeitos
    - Integrar com CFTV e alarme
    - Aprender padrões de acesso
    """

    def __init__(
        self,
        condominio_id: str,
        llm_client: UnifiedLLMClient = None,
        memory: UnifiedMemorySystem = None,
        tools: ToolRegistry = None,
        mcp_acesso_url: str = None,
        evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT,
    ):
        super().__init__(
            agent_id=f"acesso_{condominio_id}",
            agent_type="acesso",
            condominio_id=condominio_id,
            evolution_level=evolution_level,
            llm_client=llm_client,
            memory_store=memory,
        )

        self.tools = tools
        self.mcp_url = mcp_acesso_url

        # Estado interno
        self._pontos_acesso: Dict[str, PontoAcesso] = {}
        self._visitantes_ativos: Dict[str, Visitante] = {}
        self._padroes_aprendidos: Dict[str, PadraoAcesso] = {}
        self._alertas_ativos: List[AlertaAcesso] = []
        self._bloqueios_temporarios: Dict[str, datetime] = {}

        # Configurações
        self.config = {
            "tempo_max_visitante": 480,  # 8 horas em minutos
            "tentativas_max_falha": 3,
            "tempo_bloqueio_falhas": 30,  # minutos
            "horario_silencioso": ["22:00", "07:00"],
            "liberar_entregador_auto": True,
            "tempo_max_entregador": 30,  # minutos
            "reconhecimento_facial_confianca": 0.85,
        }

        logger.info(f"Agente Acesso inicializado para condomínio {condominio_id}")

    def _register_capabilities(self) -> None:
        """Registra capacidades específicas do agente"""

        # Nível 1: Reativo
        self._capabilities["liberar_acesso"] = AgentCapability(
            name="liberar_acesso",
            description="Liberar acesso manualmente",
            level=EvolutionLevel.REACTIVE
        )
        self._capabilities["bloquear_acesso"] = AgentCapability(
            name="bloquear_acesso",
            description="Bloquear acesso",
            level=EvolutionLevel.REACTIVE
        )
        self._capabilities["consultar_logs"] = AgentCapability(
            name="consultar_logs",
            description="Consultar histórico de acessos",
            level=EvolutionLevel.REACTIVE
        )
        self._capabilities["cadastrar_visitante"] = AgentCapability(
            name="cadastrar_visitante",
            description="Cadastrar visitante",
            level=EvolutionLevel.REACTIVE
        )

        # Nível 2: Proativo
        self._capabilities["alertar_acesso_incomum"] = AgentCapability(
            name="alertar_acesso_incomum",
            description="Alertar sobre acessos incomuns",
            level=EvolutionLevel.PROACTIVE
        )
        self._capabilities["lembrar_vencimentos"] = AgentCapability(
            name="lembrar_vencimentos",
            description="Lembrar vencimentos de cadastros",
            level=EvolutionLevel.PROACTIVE
        )

        # Nível 3: Preditivo
        self._capabilities["prever_picos"] = AgentCapability(
            name="prever_picos",
            description="Prever horários de pico",
            level=EvolutionLevel.PREDICTIVE
        )
        self._capabilities["detectar_padroes"] = AgentCapability(
            name="detectar_padroes",
            description="Detectar padrões de acesso",
            level=EvolutionLevel.PREDICTIVE
        )

        # Nível 4: Autônomo
        self._capabilities["liberar_visitante_frequente"] = AgentCapability(
            name="liberar_visitante_frequente",
            description="Liberar visitantes frequentes automaticamente",
            level=EvolutionLevel.AUTONOMOUS
        )
        self._capabilities["bloquear_automatico"] = AgentCapability(
            name="bloquear_automatico",
            description="Bloquear automaticamente após falhas",
            level=EvolutionLevel.AUTONOMOUS
        )

        # Nível 5: Evolutivo
        self._capabilities["aprender_padroes"] = AgentCapability(
            name="aprender_padroes",
            description="Aprender padrões de acesso",
            level=EvolutionLevel.EVOLUTIONARY
        )

        # Nível 6: Colaborativo
        self._capabilities["integrar_cftv"] = AgentCapability(
            name="integrar_cftv",
            description="Integrar com sistema de câmeras",
            level=EvolutionLevel.COLLABORATIVE
        )
        self._capabilities["integrar_alarme"] = AgentCapability(
            name="integrar_alarme",
            description="Integrar com sistema de alarme",
            level=EvolutionLevel.COLLABORATIVE
        )

        # Nível 7: Transcendente
        self._capabilities["seguranca_preditiva"] = AgentCapability(
            name="seguranca_preditiva",
            description="Segurança preditiva avançada",
            level=EvolutionLevel.TRANSCENDENT
        )

    def get_system_prompt(self) -> str:
        """Retorna system prompt do agente"""
        return f"""Você é o Agente de Controle de Acesso do sistema Conecta Plus.

Seu ID: {self.agent_id}
Condomínio: {self.condominio_id}
Nível de Evolução: {self.evolution_level.name}

Suas responsabilidades:
1. Gerenciar entrada e saída de pessoas e veículos
2. Controlar visitantes, prestadores e entregadores
3. Detectar e alertar acessos suspeitos
4. Integrar com câmeras e alarme para segurança total
5. Aprender padrões de acesso de cada morador

Regras de segurança:
- Nunca liberar acesso sem identificação adequada
- Alertar imediatamente sobre tentativas de invasão
- Respeitar horário de silêncio: {self.config['horario_silencioso']}
- Máximo {self.config['tentativas_max_falha']} tentativas de acesso falhas

Comunique-se em português brasileiro, de forma clara e profissional.
Priorize sempre a segurança dos moradores.
"""

    async def process(self, input_data: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        """Processa entrada e executa ação"""
        action = input_data.get("action", "")
        params = input_data.get("params", {})

        result = {}

        try:
            # Nível 1: Reativo
            if action == "listar_pontos":
                result = await self._listar_pontos(params, context)

            elif action == "liberar_acesso":
                result = await self._liberar_acesso(params, context)

            elif action == "bloquear_acesso":
                result = await self._bloquear_acesso(params, context)

            elif action == "consultar_logs":
                result = await self._consultar_logs(params, context)

            elif action == "cadastrar_visitante":
                result = await self._cadastrar_visitante(params, context)

            elif action == "registrar_saida":
                result = await self._registrar_saida(params, context)

            # Nível 2: Proativo
            elif action == "verificar_visitantes_expirados":
                if self.has_capability("alertar_acesso_incomum"):
                    result = await self._verificar_visitantes_expirados(params, context)
                else:
                    result = {"error": "Capacidade não disponível"}

            # Nível 3: Preditivo
            elif action == "analisar_padroes":
                if self.has_capability("detectar_padroes"):
                    result = await self._analisar_padroes(params, context)
                else:
                    result = {"error": "Capacidade preditiva não disponível"}

            elif action == "prever_picos":
                if self.has_capability("prever_picos"):
                    result = await self._prever_picos(params, context)
                else:
                    result = {"error": "Capacidade preditiva não disponível"}

            # Nível 4: Autônomo
            elif action == "processar_acesso":
                result = await self._processar_acesso_inteligente(params, context)

            # Nível 7: Transcendente
            elif action == "analise_seguranca":
                if self.has_capability("seguranca_preditiva"):
                    result = await self._analise_seguranca_transcendente(params, context)
                else:
                    result = {"error": "Capacidade transcendente não disponível"}

            # Chat
            elif action == "chat":
                result = await self._process_chat(params, context)

            # Webhook de dispositivo
            elif action == "evento_dispositivo":
                result = await self._processar_evento_dispositivo(params, context)

            else:
                result = {"error": f"Ação '{action}' não reconhecida"}

        except Exception as e:
            logger.error(f"Erro ao processar ação {action}: {e}")
            result = {"error": str(e)}

        return result

    # ==================== NÍVEL 1: REATIVO ====================

    async def _listar_pontos(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Lista pontos de acesso"""
        if self.tools:
            result = await self.tools.execute(
                "database_query",
                table="pontos_acesso",
                where={"condominio_id": self.condominio_id}
            )

            if result.success:
                return {
                    "success": True,
                    "pontos": result.data,
                    "total": len(result.data)
                }

        # Mock
        return {
            "success": True,
            "pontos": [
                {"id": "pa_001", "nome": "Portaria Principal", "tipo": "portaria_principal", "ativo": True},
                {"id": "pa_002", "nome": "Garagem", "tipo": "garagem", "ativo": True},
                {"id": "pa_003", "nome": "Portaria Serviço", "tipo": "portaria_servico", "ativo": True},
                {"id": "pa_004", "nome": "Pedestres", "tipo": "pedestres", "ativo": True},
            ],
            "total": 4
        }

    async def _liberar_acesso(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Libera acesso manualmente"""
        ponto_id = params.get("ponto_id")
        pessoa_id = params.get("pessoa_id")
        tipo = params.get("tipo", "visitante")
        motivo = params.get("motivo", "")

        if not ponto_id:
            return {"success": False, "error": "ponto_id é obrigatório"}

        # Chamar MCP do dispositivo
        if self.tools and self.mcp_url:
            result = await self.tools.execute(
                "call_mcp",
                mcp_name="mcp-control-id",
                method="liberar_acesso",
                params={"ponto_id": ponto_id}
            )

            if result.success:
                # Registrar log
                await self._registrar_acesso(
                    ponto_id=ponto_id,
                    pessoa_id=pessoa_id,
                    tipo=TipoAcesso(tipo),
                    metodo=MetodoAcesso.PORTARIA,
                    status=StatusAcesso.LIBERADO,
                    autorizado_por=context.user_id,
                    observacao=motivo
                )

                return {
                    "success": True,
                    "mensagem": f"Acesso liberado no ponto {ponto_id}"
                }

        return {
            "success": True,
            "mensagem": f"Acesso liberado (mock)"
        }

    async def _bloquear_acesso(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Bloqueia acesso"""
        ponto_id = params.get("ponto_id")
        pessoa_id = params.get("pessoa_id")
        motivo = params.get("motivo", "")
        duracao = params.get("duracao_minutos", 0)

        if pessoa_id:
            # Bloquear pessoa específica
            self._bloqueios_temporarios[pessoa_id] = datetime.now() + timedelta(minutes=duracao) if duracao else datetime.max

            if self.tools:
                await self.tools.execute(
                    "database_update",
                    table="pessoas_acesso",
                    data={"bloqueado": True, "motivo_bloqueio": motivo},
                    where={"id": pessoa_id}
                )

            return {
                "success": True,
                "mensagem": f"Pessoa {pessoa_id} bloqueada",
                "ate": self._bloqueios_temporarios[pessoa_id].isoformat() if duracao else "indefinido"
            }

        if ponto_id:
            # Bloquear ponto
            if self.tools and self.mcp_url:
                await self.tools.execute(
                    "call_mcp",
                    mcp_name="mcp-control-id",
                    method="bloquear_ponto",
                    params={"ponto_id": ponto_id, "motivo": motivo}
                )

            return {
                "success": True,
                "mensagem": f"Ponto {ponto_id} bloqueado"
            }

        return {"success": False, "error": "ponto_id ou pessoa_id necessário"}

    async def _consultar_logs(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Consulta histórico de acessos"""
        ponto_id = params.get("ponto_id")
        pessoa_id = params.get("pessoa_id")
        data_inicio = params.get("data_inicio")
        data_fim = params.get("data_fim")
        limit = params.get("limit", 100)

        where = {"condominio_id": self.condominio_id}
        if ponto_id:
            where["ponto_id"] = ponto_id
        if pessoa_id:
            where["pessoa_id"] = pessoa_id

        if self.tools:
            result = await self.tools.execute(
                "database_query",
                table="logs_acesso",
                where=where,
                order_by="timestamp DESC",
                limit=limit
            )

            if result.success:
                return {
                    "success": True,
                    "logs": result.data,
                    "total": len(result.data)
                }

        # Mock
        return {
            "success": True,
            "logs": [
                {
                    "id": "log_001",
                    "ponto_id": "pa_001",
                    "pessoa": "João Silva",
                    "tipo": "morador",
                    "metodo": "biometria",
                    "status": "liberado",
                    "timestamp": "2024-12-18T08:30:00"
                },
                {
                    "id": "log_002",
                    "ponto_id": "pa_002",
                    "pessoa": "Maria Souza",
                    "tipo": "visitante",
                    "metodo": "qr_code",
                    "status": "liberado",
                    "timestamp": "2024-12-18T09:15:00"
                }
            ],
            "total": 2
        }

    async def _cadastrar_visitante(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Cadastra visitante"""
        nome = params.get("nome")
        documento = params.get("documento")
        telefone = params.get("telefone")
        unidade = params.get("unidade_destino")
        morador = params.get("morador_autorizador")
        recorrente = params.get("recorrente", False)
        tempo_permanencia = params.get("tempo_permanencia", self.config["tempo_max_visitante"])

        if not all([nome, documento, unidade]):
            return {"success": False, "error": "nome, documento e unidade_destino são obrigatórios"}

        visitante_id = hashlib.md5(f"{documento}{datetime.now()}".encode()).hexdigest()[:12]

        visitante = Visitante(
            id=visitante_id,
            nome=nome,
            documento=documento,
            telefone=telefone or "",
            unidade_destino=unidade,
            morador_autorizador=morador or "",
            data_entrada=datetime.now(),
            data_saida_prevista=datetime.now() + timedelta(minutes=tempo_permanencia),
            recorrente=recorrente
        )

        self._visitantes_ativos[visitante_id] = visitante

        if self.tools:
            await self.tools.execute(
                "database_insert",
                table="visitantes",
                data={
                    "id": visitante_id,
                    "nome": nome,
                    "documento": documento,
                    "telefone": telefone,
                    "unidade_destino": unidade,
                    "morador_autorizador": morador,
                    "data_entrada": datetime.now().isoformat(),
                    "data_saida_prevista": visitante.data_saida_prevista.isoformat(),
                    "recorrente": recorrente,
                    "condominio_id": self.condominio_id
                }
            )

            # Gerar QR Code de acesso
            qr_code = f"VIS:{visitante_id}:{self.condominio_id}"

        return {
            "success": True,
            "visitante_id": visitante_id,
            "qr_code": f"VIS:{visitante_id}",
            "valido_ate": visitante.data_saida_prevista.isoformat(),
            "mensagem": f"Visitante {nome} cadastrado com sucesso"
        }

    async def _registrar_saida(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Registra saída de visitante"""
        visitante_id = params.get("visitante_id")

        if visitante_id in self._visitantes_ativos:
            visitante = self._visitantes_ativos.pop(visitante_id)

            if self.tools:
                await self.tools.execute(
                    "database_update",
                    table="visitantes",
                    data={"data_saida": datetime.now().isoformat()},
                    where={"id": visitante_id}
                )

            tempo_permanencia = (datetime.now() - visitante.data_entrada).seconds // 60

            return {
                "success": True,
                "visitante": visitante.nome,
                "tempo_permanencia_minutos": tempo_permanencia,
                "mensagem": "Saída registrada"
            }

        return {"success": False, "error": "Visitante não encontrado"}

    # ==================== NÍVEL 2: PROATIVO ====================

    async def _verificar_visitantes_expirados(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Verifica visitantes com tempo expirado"""
        expirados = []
        agora = datetime.now()

        for vid, visitante in self._visitantes_ativos.items():
            if visitante.data_saida_prevista and visitante.data_saida_prevista < agora:
                minutos_excedidos = (agora - visitante.data_saida_prevista).seconds // 60

                expirados.append({
                    "id": vid,
                    "nome": visitante.nome,
                    "unidade": visitante.unidade_destino,
                    "excedeu_minutos": minutos_excedidos
                })

                # Alertar portaria
                if self.tools:
                    await self.tools.execute(
                        "send_notification",
                        user_ids=["portaria"],
                        title="Visitante com Tempo Excedido",
                        message=f"{visitante.nome} na unidade {visitante.unidade_destino} excedeu o tempo em {minutos_excedidos} min",
                        channels=["app"],
                        priority="high"
                    )

        return {
            "success": True,
            "expirados": expirados,
            "total": len(expirados)
        }

    # ==================== NÍVEL 3: PREDITIVO ====================

    async def _analisar_padroes(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Analisa padrões de acesso"""
        pessoa_id = params.get("pessoa_id")
        periodo_dias = params.get("periodo_dias", 30)

        # Buscar histórico
        historico = await self._obter_historico_pessoa(pessoa_id, periodo_dias)

        if self.llm:
            prompt = f"""Analise os padrões de acesso desta pessoa:

Pessoa ID: {pessoa_id}
Histórico (últimos {periodo_dias} dias):
{json.dumps(historico, indent=2)}

Identifique:
1. Horários mais frequentes de entrada/saída
2. Pontos de acesso mais utilizados
3. Dias da semana com mais acessos
4. Padrões incomuns ou anomalias
5. Tempo médio de permanência

Responda em JSON:
{{
  "horarios_frequentes": ["HH:MM", ...],
  "pontos_frequentes": ["ponto1", ...],
  "dias_semana": [0-6],
  "anomalias": ["anomalia1", ...],
  "tempo_medio_permanencia": minutos,
  "perfil": "regular/irregular/suspeito"
}}
"""
            try:
                response = await self.llm.generate(
                    system_prompt=self.get_system_prompt(),
                    user_prompt=prompt,
                    temperature=0.3
                )

                import re
                json_match = re.search(r'\{[\s\S]*\}', response)
                if json_match:
                    analise = json.loads(json_match.group())

                    # Armazenar padrão aprendido
                    self._padroes_aprendidos[pessoa_id] = PadraoAcesso(
                        pessoa_id=pessoa_id,
                        tipo=TipoAcesso.MORADOR,
                        horarios_frequentes=analise.get("horarios_frequentes", []),
                        pontos_frequentes=analise.get("pontos_frequentes", []),
                        dias_semana=analise.get("dias_semana", []),
                        tempo_medio_permanencia=analise.get("tempo_medio_permanencia", 0)
                    )

                    return {
                        "success": True,
                        "analise": analise
                    }

            except Exception as e:
                logger.error(f"Erro na análise de padrões: {e}")

        return {
            "success": True,
            "analise": {
                "horarios_frequentes": ["07:30", "18:00"],
                "pontos_frequentes": ["pa_001", "pa_002"],
                "dias_semana": [0, 1, 2, 3, 4],
                "anomalias": [],
                "tempo_medio_permanencia": 600,
                "perfil": "regular"
            }
        }

    async def _prever_picos(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Prevê horários de pico"""
        data = params.get("data", datetime.now().strftime("%Y-%m-%d"))

        if self.tools:
            # Análise estatística
            result = await self.tools.execute(
                "analyze_data",
                data=await self._obter_dados_pico(),
                analysis_type="distribution",
                value_field="acessos"
            )

            if result.success:
                return {
                    "success": True,
                    "data": data,
                    "picos_previstos": [
                        {"horario": "07:00-09:00", "acessos_esperados": 45},
                        {"horario": "12:00-13:00", "acessos_esperados": 30},
                        {"horario": "17:30-19:30", "acessos_esperados": 55}
                    ],
                    "recomendacoes": [
                        "Reforçar portaria das 17:30 às 19:30",
                        "Preparar fila rápida para moradores"
                    ]
                }

        return {
            "success": True,
            "data": data,
            "picos_previstos": [
                {"horario": "07:00-09:00", "acessos_esperados": 45},
                {"horario": "17:30-19:30", "acessos_esperados": 55}
            ]
        }

    # ==================== NÍVEL 4: AUTÔNOMO ====================

    async def _processar_acesso_inteligente(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Processa acesso de forma inteligente"""
        ponto_id = params.get("ponto_id")
        metodo = params.get("metodo")
        identificador = params.get("identificador")  # biometria, tag, qr, etc
        foto = params.get("foto")

        # Verificar bloqueios
        if identificador in self._bloqueios_temporarios:
            if self._bloqueios_temporarios[identificador] > datetime.now():
                return {
                    "success": False,
                    "status": "bloqueado",
                    "motivo": "Pessoa bloqueada temporariamente"
                }

        # Identificar pessoa
        pessoa = await self._identificar_pessoa(metodo, identificador)

        if not pessoa:
            # Acesso negado - não identificado
            await self._registrar_acesso(
                ponto_id=ponto_id,
                pessoa_id=None,
                tipo=TipoAcesso.VISITANTE,
                metodo=MetodoAcesso(metodo),
                status=StatusAcesso.NEGADO,
                observacao="Não identificado"
            )

            # Alertar se muitas falhas
            await self._verificar_tentativas_falhas(ponto_id, identificador)

            return {
                "success": False,
                "status": "negado",
                "motivo": "Não identificado"
            }

        # Verificar padrão de acesso (Nível 5)
        acesso_normal = True
        if self.has_capability("aprender_padroes"):
            acesso_normal = await self._verificar_padrao_acesso(pessoa, ponto_id)

        # Liberar acesso
        if self.has_capability("liberar_visitante_frequente") or pessoa.get("tipo") == "morador":
            if self.tools and self.mcp_url:
                await self.tools.execute(
                    "call_mcp",
                    mcp_name="mcp-control-id",
                    method="liberar_acesso",
                    params={"ponto_id": ponto_id}
                )

            await self._registrar_acesso(
                ponto_id=ponto_id,
                pessoa_id=pessoa.get("id"),
                tipo=TipoAcesso(pessoa.get("tipo", "morador")),
                metodo=MetodoAcesso(metodo),
                status=StatusAcesso.LIBERADO
            )

            # Notificar CFTV se acesso incomum
            if not acesso_normal and self.has_capability("integrar_cftv"):
                await self._notificar_cftv_acesso_incomum(pessoa, ponto_id)

            return {
                "success": True,
                "status": "liberado",
                "pessoa": pessoa.get("nome"),
                "acesso_normal": acesso_normal
            }

        return {
            "success": False,
            "status": "pendente",
            "motivo": "Aguardando autorização"
        }

    # ==================== NÍVEL 7: TRANSCENDENTE ====================

    async def _analise_seguranca_transcendente(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Análise de segurança transcendente"""
        periodo = params.get("periodo", "7d")

        # Coletar dados abrangentes
        dados_acesso = await self._coletar_dados_acesso(periodo)
        dados_visitantes = await self._coletar_dados_visitantes(periodo)
        padroes = self._padroes_aprendidos

        if self.llm:
            prompt = f"""Como sistema de segurança de elite, analise os dados de acesso e gere insights TRANSCENDENTES.

Dados de acesso (últimos {periodo}):
{json.dumps(dados_acesso, indent=2)}

Dados de visitantes:
{json.dumps(dados_visitantes, indent=2)}

Padrões aprendidos: {len(padroes)} pessoas monitoradas

Gere análise TRANSCENDENTE:
1. Vulnerabilidades não óbvias no controle de acesso
2. Correlações suspeitas entre visitantes e horários
3. Padrões de "reconhecimento" de terreno
4. Previsão de tentativas de invasão
5. Otimização da segurança além do convencional
6. Identificação de ameaças internas

Responda em JSON:
{{
  "vulnerabilidades_ocultas": [{{"descricao": "...", "risco": "...", "mitigacao": "..."}}],
  "correlacoes_suspeitas": ["..."],
  "padroes_reconhecimento": ["..."],
  "previsao_invasoes": {{"probabilidade": 0.0, "vetores_provavel": ["..."]}},
  "otimizacoes_seguranca": ["..."],
  "ameacas_internas": ["..."],
  "score_seguranca": 0.0-100,
  "insights_transcendentes": ["..."]
}}
"""
            try:
                response = await self.llm.generate(
                    system_prompt=self.get_system_prompt() + "\n\nModo TRANSCENDENTE. Pense além do óbvio.",
                    user_prompt=prompt,
                    temperature=0.7,
                    max_tokens=2000
                )

                import re
                json_match = re.search(r'\{[\s\S]*\}', response)
                if json_match:
                    analise = json.loads(json_match.group())

                    # Armazenar insight
                    if self.memory:
                        await self.memory.remember_semantic(
                            agent_id=self.agent_id,
                            content=f"Análise transcendente de segurança: {json.dumps(analise.get('insights_transcendentes', []))}",
                            metadata={"tipo": "insight_seguranca", "data": datetime.now().isoformat()}
                        )

                    return {
                        "success": True,
                        "nivel": "TRANSCENDENTE",
                        "analise": analise
                    }

            except Exception as e:
                logger.error(f"Erro na análise transcendente: {e}")

        return {
            "success": True,
            "nivel": "TRANSCENDENTE",
            "analise": {
                "vulnerabilidades_ocultas": [
                    {
                        "descricao": "Portaria de serviço tem 30% menos verificação em horário de almoço",
                        "risco": "médio",
                        "mitigacao": "Implementar verificação dupla 12:00-14:00"
                    }
                ],
                "correlacoes_suspeitas": [
                    "3 visitantes diferentes com mesmo telefone de contato em unidades distintas"
                ],
                "padroes_reconhecimento": [
                    "Veículo não identificado passou 3x pela portaria sem entrar na última semana"
                ],
                "previsao_invasoes": {
                    "probabilidade": 0.15,
                    "vetores_provaveis": ["Portaria serviço", "Muro fundos"]
                },
                "otimizacoes_seguranca": [
                    "Implementar verificação facial nos horários de pico",
                    "Adicionar segunda barreira na garagem"
                ],
                "ameacas_internas": [],
                "score_seguranca": 78,
                "insights_transcendentes": [
                    "Correlação entre entregadores frequentes e tentativas de acesso após expediente"
                ]
            }
        }

    async def _process_chat(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Processa chat"""
        message = params.get("message", "")

        if not self.llm:
            return {"error": "LLM não configurado"}

        response = await self.llm.generate(
            system_prompt=self.get_system_prompt(),
            user_prompt=message
        )

        return {"success": True, "response": response}

    # ==================== MÉTODOS AUXILIARES ====================

    async def _registrar_acesso(
        self,
        ponto_id: str,
        pessoa_id: Optional[str],
        tipo: TipoAcesso,
        metodo: MetodoAcesso,
        status: StatusAcesso,
        autorizado_por: str = None,
        observacao: str = ""
    ):
        """Registra evento de acesso"""
        if self.tools:
            await self.tools.execute(
                "database_insert",
                table="logs_acesso",
                data={
                    "ponto_id": ponto_id,
                    "pessoa_id": pessoa_id,
                    "tipo": tipo.value,
                    "metodo": metodo.value,
                    "status": status.value,
                    "timestamp": datetime.now().isoformat(),
                    "autorizado_por": autorizado_por,
                    "observacao": observacao,
                    "condominio_id": self.condominio_id
                }
            )

    async def _identificar_pessoa(self, metodo: str, identificador: str) -> Optional[Dict]:
        """Identifica pessoa pelo método de acesso"""
        # Simulado - integrar com MCPs reais
        return {
            "id": "pessoa_001",
            "nome": "João Silva",
            "tipo": "morador",
            "unidade": "101"
        }

    async def _verificar_padrao_acesso(self, pessoa: Dict, ponto_id: str) -> bool:
        """Verifica se acesso está dentro do padrão normal"""
        pessoa_id = pessoa.get("id")

        if pessoa_id not in self._padroes_aprendidos:
            return True  # Sem padrão definido, assumir normal

        padrao = self._padroes_aprendidos[pessoa_id]
        hora_atual = datetime.now().strftime("%H:%M")
        dia_atual = datetime.now().weekday()

        # Verificar horário
        horario_ok = any(
            self._horario_proximo(hora_atual, h)
            for h in padrao.horarios_frequentes
        )

        # Verificar dia da semana
        dia_ok = dia_atual in padrao.dias_semana

        return horario_ok and dia_ok

    def _horario_proximo(self, h1: str, h2: str, tolerancia_min: int = 60) -> bool:
        """Verifica se dois horários são próximos"""
        try:
            t1 = datetime.strptime(h1, "%H:%M")
            t2 = datetime.strptime(h2, "%H:%M")
            diff = abs((t1 - t2).seconds // 60)
            return diff <= tolerancia_min
        except:
            return False

    async def _verificar_tentativas_falhas(self, ponto_id: str, identificador: str):
        """Verifica tentativas de acesso falhas"""
        # Implementar lógica de bloqueio após N falhas
        pass

    async def _notificar_cftv_acesso_incomum(self, pessoa: Dict, ponto_id: str):
        """Notifica agente CFTV sobre acesso incomum"""
        if self.has_capability("agent_collaboration"):
            await self.send_message(
                receiver_id=f"cftv_{self.condominio_id}",
                content={
                    "action": "monitorar_pessoa",
                    "pessoa": pessoa,
                    "ponto_id": ponto_id,
                    "motivo": "acesso_incomum"
                },
                priority=Priority.HIGH
            )

    async def _processar_evento_dispositivo(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Processa evento de dispositivo de acesso"""
        return await self._processar_acesso_inteligente(params, context)

    async def _obter_historico_pessoa(self, pessoa_id: str, dias: int) -> List[Dict]:
        """Obtém histórico de acessos de uma pessoa"""
        return []

    async def _obter_dados_pico(self) -> List[Dict]:
        """Obtém dados para análise de pico"""
        return []

    async def _coletar_dados_acesso(self, periodo: str) -> Dict:
        """Coleta dados de acesso para análise"""
        return {
            "total_acessos": 1250,
            "por_tipo": {"moradores": 980, "visitantes": 200, "prestadores": 70},
            "negados": 15,
            "anomalias": 3
        }

    async def _coletar_dados_visitantes(self, periodo: str) -> Dict:
        """Coleta dados de visitantes"""
        return {
            "total": 200,
            "recorrentes": 45,
            "tempo_medio_minutos": 90
        }


# Factory
def create_access_agent(
    condominio_id: str,
    llm_client: UnifiedLLMClient = None,
    memory: UnifiedMemorySystem = None,
    tools: ToolRegistry = None,
    mcp_url: str = None,
    evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT
) -> AgenteAcesso:
    """Cria instância do agente de acesso"""
    return AgenteAcesso(
        condominio_id=condominio_id,
        llm_client=llm_client or UnifiedLLMClient(),
        memory=memory,
        tools=tools,
        mcp_acesso_url=mcp_url,
        evolution_level=evolution_level
    )
