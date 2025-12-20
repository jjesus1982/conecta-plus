"""
Conecta Plus - Agente Emergência (Nível 7)
Gestor de crises e emergências do condomínio

Capacidades:
1. REATIVO: Receber alertas, acionar protocolos
2. PROATIVO: Monitorar riscos, prevenir emergências
3. PREDITIVO: Prever situações de risco, antecipar crises
4. AUTÔNOMO: Coordenar resposta, acionar autoridades
5. EVOLUTIVO: Aprender com incidentes, melhorar protocolos
6. COLABORATIVO: Integrar todos os agentes em emergências
7. TRANSCENDENTE: Gestão de crises completa
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
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


class TipoEmergencia(Enum):
    INCENDIO = "incendio"
    MEDICA = "medica"
    SEGURANCA = "seguranca"
    INVASAO = "invasao"
    VAZAMENTO_GAS = "vazamento_gas"
    VAZAMENTO_AGUA = "vazamento_agua"
    ELEVADOR = "elevador"
    QUEDA_ENERGIA = "queda_energia"
    ALAGAMENTO = "alagamento"
    DESABAMENTO = "desabamento"
    PANICO = "panico"
    NATURAL = "natural"  # tempestade, vendaval


class GravidadeEmergencia(Enum):
    BAIXA = "baixa"
    MEDIA = "media"
    ALTA = "alta"
    CRITICA = "critica"


class StatusEmergencia(Enum):
    ATIVA = "ativa"
    EM_ATENDIMENTO = "em_atendimento"
    CONTROLADA = "controlada"
    ENCERRADA = "encerrada"
    FALSO_ALARME = "falso_alarme"


class TipoProtocolo(Enum):
    EVACUACAO = "evacuacao"
    LOCKDOWN = "lockdown"
    ABRIGO = "abrigo"
    ISOLAMENTO = "isolamento"
    COMUNICACAO = "comunicacao"


@dataclass
class Emergencia:
    id: str
    tipo: TipoEmergencia
    gravidade: GravidadeEmergencia
    status: StatusEmergencia
    descricao: str
    local: str
    data_inicio: datetime
    reportado_por: str
    data_fim: Optional[datetime] = None
    vitimas: int = 0
    feridos: int = 0
    danos_estimados: float = 0
    autoridades_acionadas: List[str] = field(default_factory=list)
    protocolos_ativados: List[str] = field(default_factory=list)
    timeline: List[Dict] = field(default_factory=list)
    observacoes: str = ""


@dataclass
class Protocolo:
    id: str
    tipo: TipoProtocolo
    nome: str
    descricao: str
    passos: List[str]
    responsaveis: List[str]
    recursos_necessarios: List[str]
    tempo_estimado_minutos: int
    ativo: bool = True


@dataclass
class ContatoEmergencia:
    id: str
    nome: str
    tipo: str  # bombeiro, policia, samu, zelador, sindico
    telefone: str
    prioridade: int
    disponivel_24h: bool = True


@dataclass
class SimulacaoEmergencia:
    id: str
    tipo: TipoEmergencia
    data_realizada: datetime
    participantes: int
    tempo_evacuacao_minutos: float
    pontos_melhorar: List[str]
    avaliacao: float  # 0-10


@dataclass
class AlertaPreventivo:
    id: str
    tipo: str
    descricao: str
    nivel: str  # amarelo, laranja, vermelho
    data_inicio: datetime
    data_fim: Optional[datetime] = None
    ativo: bool = True


class AgenteEmergencia(BaseAgent):
    """Agente Emergência - Gestor de Crises Nível 7"""

    def __init__(
        self,
        condominio_id: str,
        llm_client: UnifiedLLMClient = None,
        memory: UnifiedMemorySystem = None,
        tools: ToolRegistry = None,
        evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT,
    ):
        super().__init__(
            agent_id=f"emergencia_{condominio_id}",
            agent_type="emergencia",
            condominio_id=condominio_id,
            evolution_level=evolution_level,
            llm_client=llm_client,
            memory_store=memory,
        )
        self.tools = tools

        self._emergencias: Dict[str, Emergencia] = {}
        self._protocolos: Dict[str, Protocolo] = {}
        self._contatos: Dict[str, ContatoEmergencia] = {}
        self._simulacoes: List[SimulacaoEmergencia] = []
        self._alertas: List[AlertaPreventivo] = []
        self._emergencia_ativa: Optional[str] = None

        self.config = {
            "tempo_resposta_maximo": 5,  # minutos
            "auto_acionar_autoridades": True,
            "notificar_todos_emergencia_critica": True,
            "gravar_cameras_emergencia": True,
        }

        self._inicializar_protocolos()
        self._inicializar_contatos()

    def _inicializar_protocolos(self):
        """Inicializar protocolos padrão"""
        protocolos = [
            {
                "tipo": "evacuacao",
                "nome": "Evacuação Geral",
                "descricao": "Protocolo de evacuação completa do edifício",
                "passos": [
                    "Acionar alarme de incêndio",
                    "Comunicar por alto-falante",
                    "Desligar elevadores (exceto bombeiros)",
                    "Abrir portas de emergência",
                    "Direcionar moradores para ponto de encontro",
                    "Verificar apartamentos vazios",
                    "Confirmar evacuação completa"
                ],
                "responsaveis": ["zelador", "porteiro", "brigadista"],
                "recursos": ["alto_falante", "lanternas", "lista_moradores"],
                "tempo": 15
            },
            {
                "tipo": "lockdown",
                "nome": "Bloqueio Total",
                "descricao": "Protocolo de segurança para invasão",
                "passos": [
                    "Bloquear todas as entradas",
                    "Acionar câmeras de segurança",
                    "Comunicar moradores para permanecerem em casa",
                    "Acionar polícia",
                    "Monitorar situação",
                    "Aguardar liberação das autoridades"
                ],
                "responsaveis": ["porteiro", "vigilante"],
                "recursos": ["cameras", "radio", "telefone"],
                "tempo": 5
            },
            {
                "tipo": "abrigo",
                "nome": "Abrigo no Local",
                "descricao": "Protocolo para tempestades severas",
                "passos": [
                    "Alertar moradores para permanecerem em casa",
                    "Fechar janelas de áreas comuns",
                    "Verificar gerador de emergência",
                    "Desligar equipamentos sensíveis",
                    "Monitorar condições climáticas",
                    "Comunicar quando seguro sair"
                ],
                "responsaveis": ["zelador", "porteiro"],
                "recursos": ["gerador", "radio", "lanterna"],
                "tempo": 10
            },
        ]

        for p in protocolos:
            protocolo = Protocolo(
                id=f"protocolo_{p['tipo']}",
                tipo=TipoProtocolo[p["tipo"].upper()],
                nome=p["nome"],
                descricao=p["descricao"],
                passos=p["passos"],
                responsaveis=p["responsaveis"],
                recursos_necessarios=p["recursos"],
                tempo_estimado_minutos=p["tempo"]
            )
            self._protocolos[protocolo.id] = protocolo

    def _inicializar_contatos(self):
        """Inicializar contatos de emergência"""
        contatos = [
            ("Bombeiros", "bombeiro", "193", 1),
            ("SAMU", "samu", "192", 1),
            ("Polícia Militar", "policia", "190", 1),
            ("Polícia Civil", "policia", "197", 2),
            ("Defesa Civil", "defesa_civil", "199", 2),
            ("Copasa/Sabesp", "agua", "115", 3),
            ("Cemig/Eletropaulo", "energia", "116", 3),
            ("Comgás", "gas", "0800-024-0197", 2),
        ]

        for nome, tipo, telefone, prioridade in contatos:
            contato = ContatoEmergencia(
                id=f"contato_{tipo}",
                nome=nome,
                tipo=tipo,
                telefone=telefone,
                prioridade=prioridade
            )
            self._contatos[contato.id] = contato

    def _register_capabilities(self) -> None:
        self._capabilities["receber_alerta"] = AgentCapability(
            name="receber_alerta", description="Receber e processar alertas",
            level=EvolutionLevel.REACTIVE
        )
        self._capabilities["ativar_protocolo"] = AgentCapability(
            name="ativar_protocolo", description="Ativar protocolos de emergência",
            level=EvolutionLevel.AUTONOMOUS
        )
        self._capabilities["coordenar_resposta"] = AgentCapability(
            name="coordenar_resposta", description="Coordenar resposta à emergência",
            level=EvolutionLevel.COLLABORATIVE
        )
        self._capabilities["gestao_crises"] = AgentCapability(
            name="gestao_crises", description="Gestão completa de crises",
            level=EvolutionLevel.TRANSCENDENT
        )

    def get_system_prompt(self) -> str:
        return f"""Você é o Agente de Emergência do Conecta Plus.
ID: {self.agent_id} | Condomínio: {self.condominio_id} | Nível: {self.evolution_level.name}

RESPONSABILIDADES CRÍTICAS:
- Receber e processar alertas de emergência
- Ativar protocolos apropriados
- Coordenar resposta com todos os agentes
- Acionar autoridades quando necessário
- Comunicar moradores
- Documentar incidentes
- Realizar simulações preventivas

PRIORIDADE MÁXIMA:
Segurança de vidas > Segurança patrimonial > Outras considerações

COMPORTAMENTO:
- Resposta IMEDIATA a qualquer alerta
- Mantenha calma nas comunicações
- Siga protocolos estabelecidos
- Documente todas as ações
- Aprenda com cada incidente
"""

    async def process(self, input_data: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        action = input_data.get("action", "")
        params = input_data.get("params", {})

        if action == "alerta_emergencia":
            return await self._alerta_emergencia(params, context)
        elif action == "atualizar_emergencia":
            return await self._atualizar_emergencia(params, context)
        elif action == "encerrar_emergencia":
            return await self._encerrar_emergencia(params, context)
        elif action == "ativar_protocolo":
            return await self._ativar_protocolo(params, context)
        elif action == "listar_emergencias":
            return await self._listar_emergencias(params, context)
        elif action == "listar_protocolos":
            return await self._listar_protocolos(params, context)
        elif action == "listar_contatos":
            return await self._listar_contatos(params, context)
        elif action == "adicionar_contato":
            return await self._adicionar_contato(params, context)
        elif action == "acionar_autoridade":
            return await self._acionar_autoridade(params, context)
        elif action == "comunicar_moradores":
            return await self._comunicar_moradores(params, context)
        elif action == "registrar_simulacao":
            return await self._registrar_simulacao(params, context)
        elif action == "criar_alerta_preventivo":
            return await self._criar_alerta_preventivo(params, context)
        elif action == "status_emergencia_ativa":
            return await self._status_emergencia_ativa(params, context)
        elif action == "historico_emergencias":
            return await self._historico_emergencias(params, context)
        elif action == "dashboard":
            return await self._dashboard(params, context)
        elif action == "alerta_panico":
            return await self._alerta_panico(params, context)
        elif action == "chat":
            return await self._chat(params, context)
        else:
            return {"error": f"Ação '{action}' não reconhecida"}

    async def _alerta_emergencia(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Receber e processar alerta de emergência"""
        tipo = params.get("tipo")
        gravidade = params.get("gravidade", "media")
        descricao = params.get("descricao")
        local = params.get("local")
        reportado_por = params.get("reportado_por")

        emergencia = Emergencia(
            id=f"emerg_{datetime.now().timestamp()}",
            tipo=TipoEmergencia[tipo.upper()],
            gravidade=GravidadeEmergencia[gravidade.upper()],
            status=StatusEmergencia.ATIVA,
            descricao=descricao,
            local=local,
            data_inicio=datetime.now(),
            reportado_por=reportado_por,
            timeline=[{
                "acao": "Emergência reportada",
                "timestamp": datetime.now().isoformat(),
                "responsavel": reportado_por
            }]
        )
        self._emergencias[emergencia.id] = emergencia
        self._emergencia_ativa = emergencia.id

        # Determinar protocolo a ativar
        protocolo_map = {
            TipoEmergencia.INCENDIO: "protocolo_evacuacao",
            TipoEmergencia.INVASAO: "protocolo_lockdown",
            TipoEmergencia.NATURAL: "protocolo_abrigo",
        }

        protocolo_id = protocolo_map.get(emergencia.tipo)
        if protocolo_id and protocolo_id in self._protocolos:
            await self._ativar_protocolo({"protocolo_id": protocolo_id, "emergencia_id": emergencia.id}, context)

        # Notificar moradores se crítica
        if emergencia.gravidade == GravidadeEmergencia.CRITICA and self.config["notificar_todos_emergencia_critica"]:
            await self._comunicar_moradores({
                "emergencia_id": emergencia.id,
                "mensagem": f"EMERGÊNCIA: {descricao}. Local: {local}. Siga instruções.",
                "prioridade": "urgente"
            }, context)

        # Acionar autoridades automaticamente para emergências críticas
        if self.config["auto_acionar_autoridades"] and emergencia.gravidade in [GravidadeEmergencia.ALTA, GravidadeEmergencia.CRITICA]:
            autoridades_map = {
                TipoEmergencia.INCENDIO: "bombeiro",
                TipoEmergencia.MEDICA: "samu",
                TipoEmergencia.INVASAO: "policia",
                TipoEmergencia.SEGURANCA: "policia",
                TipoEmergencia.VAZAMENTO_GAS: "bombeiro",
            }
            autoridade = autoridades_map.get(emergencia.tipo)
            if autoridade:
                await self._acionar_autoridade({"tipo": autoridade, "emergencia_id": emergencia.id}, context)

        # Ativar gravação de câmeras
        if self.config["gravar_cameras_emergencia"] and self.tools:
            await self.tools.execute(
                "call_mcp", mcp_name="mcp-hikvision-cftv",
                method="iniciar_gravacao_emergencia",
                params={"area": local, "emergencia_id": emergencia.id}
            )

        # Colaborar com outros agentes
        if self.has_capability("agent_collaboration"):
            # Alertar portaria
            await self.send_message(
                f"portaria_virtual_{self.condominio_id}",
                {"action": "alerta_emergencia", "emergencia_id": emergencia.id, "tipo": tipo, "local": local}
            )

            # Alertar CFTV
            await self.send_message(
                f"cftv_{self.condominio_id}",
                {"action": "monitorar_area", "area": local, "emergencia_id": emergencia.id}
            )

            # Alertar alarme se necessário
            if emergencia.tipo in [TipoEmergencia.INCENDIO, TipoEmergencia.INVASAO]:
                await self.send_message(
                    f"alarme_{self.condominio_id}",
                    {"action": "ativar_alarme", "tipo": tipo, "zona": local}
                )

        return {
            "success": True,
            "emergencia_id": emergencia.id,
            "tipo": tipo,
            "gravidade": gravidade,
            "status": "ativa",
            "protocolo_ativado": protocolo_id,
            "autoridades_notificadas": emergencia.autoridades_acionadas
        }

    async def _atualizar_emergencia(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Atualizar status da emergência"""
        emergencia_id = params.get("emergencia_id")
        status = params.get("status")
        observacao = params.get("observacao")
        vitimas = params.get("vitimas")
        feridos = params.get("feridos")

        if emergencia_id not in self._emergencias:
            return {"error": "Emergência não encontrada"}

        emergencia = self._emergencias[emergencia_id]

        if status:
            emergencia.status = StatusEmergencia[status.upper()]
            emergencia.timeline.append({
                "acao": f"Status alterado para {status}",
                "timestamp": datetime.now().isoformat(),
                "responsavel": "sistema"
            })

        if observacao:
            emergencia.observacoes += f"\n{datetime.now().isoformat()}: {observacao}"
            emergencia.timeline.append({
                "acao": observacao,
                "timestamp": datetime.now().isoformat(),
                "responsavel": "operador"
            })

        if vitimas is not None:
            emergencia.vitimas = vitimas
        if feridos is not None:
            emergencia.feridos = feridos

        return {
            "success": True,
            "emergencia_id": emergencia_id,
            "status": emergencia.status.value,
            "timeline_eventos": len(emergencia.timeline)
        }

    async def _encerrar_emergencia(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Encerrar emergência"""
        emergencia_id = params.get("emergencia_id")
        danos_estimados = params.get("danos_estimados", 0)
        relatorio_final = params.get("relatorio_final")

        if emergencia_id not in self._emergencias:
            return {"error": "Emergência não encontrada"}

        emergencia = self._emergencias[emergencia_id]
        emergencia.status = StatusEmergencia.ENCERRADA
        emergencia.data_fim = datetime.now()
        emergencia.danos_estimados = danos_estimados

        if relatorio_final:
            emergencia.observacoes += f"\n\nRELATÓRIO FINAL:\n{relatorio_final}"

        emergencia.timeline.append({
            "acao": "Emergência encerrada",
            "timestamp": datetime.now().isoformat(),
            "responsavel": "sistema"
        })

        if self._emergencia_ativa == emergencia_id:
            self._emergencia_ativa = None

        # Comunicar encerramento
        await self._comunicar_moradores({
            "emergencia_id": emergencia_id,
            "mensagem": f"A emergência ({emergencia.tipo.value}) foi controlada. Situação normalizada.",
            "prioridade": "normal"
        }, context)

        duracao = (emergencia.data_fim - emergencia.data_inicio).total_seconds() / 60

        return {
            "success": True,
            "emergencia_id": emergencia_id,
            "status": "encerrada",
            "duracao_minutos": round(duracao, 1),
            "vitimas": emergencia.vitimas,
            "feridos": emergencia.feridos,
            "danos_estimados": danos_estimados
        }

    async def _ativar_protocolo(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Ativar protocolo de emergência"""
        protocolo_id = params.get("protocolo_id")
        emergencia_id = params.get("emergencia_id")

        if protocolo_id not in self._protocolos:
            return {"error": "Protocolo não encontrado"}

        protocolo = self._protocolos[protocolo_id]

        if emergencia_id and emergencia_id in self._emergencias:
            emergencia = self._emergencias[emergencia_id]
            emergencia.protocolos_ativados.append(protocolo_id)
            emergencia.timeline.append({
                "acao": f"Protocolo ativado: {protocolo.nome}",
                "timestamp": datetime.now().isoformat(),
                "responsavel": "sistema"
            })

        # Notificar responsáveis
        if self.tools:
            await self.tools.execute(
                "send_notification",
                user_ids=protocolo.responsaveis,
                title=f"PROTOCOLO ATIVADO: {protocolo.nome}",
                message=f"Siga os passos do protocolo de {protocolo.tipo.value}",
                channels=["push", "sms"],
                priority="urgente"
            )

        return {
            "success": True,
            "protocolo_id": protocolo_id,
            "nome": protocolo.nome,
            "passos": protocolo.passos,
            "responsaveis": protocolo.responsaveis,
            "tempo_estimado": protocolo.tempo_estimado_minutos
        }

    async def _listar_emergencias(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Listar emergências"""
        status = params.get("status")
        tipo = params.get("tipo")
        limite = params.get("limite", 20)

        emergencias = list(self._emergencias.values())

        if status:
            emergencias = [e for e in emergencias if e.status.value == status]
        if tipo:
            emergencias = [e for e in emergencias if e.tipo.value == tipo]

        emergencias = sorted(emergencias, key=lambda x: x.data_inicio, reverse=True)[:limite]

        return {
            "success": True,
            "total": len(emergencias),
            "emergencias": [
                {
                    "id": e.id,
                    "tipo": e.tipo.value,
                    "gravidade": e.gravidade.value,
                    "status": e.status.value,
                    "local": e.local,
                    "data_inicio": e.data_inicio.isoformat(),
                    "data_fim": e.data_fim.isoformat() if e.data_fim else None,
                    "vitimas": e.vitimas,
                    "feridos": e.feridos
                }
                for e in emergencias
            ]
        }

    async def _listar_protocolos(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Listar protocolos"""
        return {
            "success": True,
            "protocolos": [
                {
                    "id": p.id,
                    "tipo": p.tipo.value,
                    "nome": p.nome,
                    "descricao": p.descricao,
                    "passos": p.passos,
                    "tempo_estimado": p.tempo_estimado_minutos
                }
                for p in self._protocolos.values() if p.ativo
            ]
        }

    async def _listar_contatos(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Listar contatos de emergência"""
        return {
            "success": True,
            "contatos": [
                {
                    "id": c.id,
                    "nome": c.nome,
                    "tipo": c.tipo,
                    "telefone": c.telefone,
                    "prioridade": c.prioridade,
                    "disponivel_24h": c.disponivel_24h
                }
                for c in sorted(self._contatos.values(), key=lambda x: x.prioridade)
            ]
        }

    async def _adicionar_contato(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Adicionar contato de emergência"""
        nome = params.get("nome")
        tipo = params.get("tipo")
        telefone = params.get("telefone")
        prioridade = params.get("prioridade", 5)

        contato = ContatoEmergencia(
            id=f"contato_{datetime.now().timestamp()}",
            nome=nome,
            tipo=tipo,
            telefone=telefone,
            prioridade=prioridade
        )
        self._contatos[contato.id] = contato

        return {
            "success": True,
            "contato_id": contato.id,
            "nome": nome
        }

    async def _acionar_autoridade(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Acionar autoridade"""
        tipo = params.get("tipo")
        emergencia_id = params.get("emergencia_id")

        contato = next((c for c in self._contatos.values() if c.tipo == tipo), None)
        if not contato:
            return {"error": f"Contato de {tipo} não encontrado"}

        # Registrar acionamento
        if emergencia_id and emergencia_id in self._emergencias:
            emergencia = self._emergencias[emergencia_id]
            emergencia.autoridades_acionadas.append(contato.nome)
            emergencia.timeline.append({
                "acao": f"Autoridade acionada: {contato.nome} ({contato.telefone})",
                "timestamp": datetime.now().isoformat(),
                "responsavel": "sistema"
            })

        # Em produção, integraria com sistema de telefonia
        logger.info(f"Acionando {contato.nome}: {contato.telefone}")

        return {
            "success": True,
            "autoridade": contato.nome,
            "telefone": contato.telefone,
            "acionado": True
        }

    async def _comunicar_moradores(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Comunicar moradores sobre emergência"""
        emergencia_id = params.get("emergencia_id")
        mensagem = params.get("mensagem")
        prioridade = params.get("prioridade", "normal")

        if self.tools:
            canais = ["push", "app"]
            if prioridade == "urgente":
                canais.extend(["sms", "email"])

            await self.tools.execute(
                "send_notification",
                user_ids=["all_residents"],
                title="COMUNICADO DE EMERGÊNCIA",
                message=mensagem,
                channels=canais,
                priority=prioridade
            )

        if emergencia_id and emergencia_id in self._emergencias:
            self._emergencias[emergencia_id].timeline.append({
                "acao": f"Comunicado enviado: {mensagem[:50]}...",
                "timestamp": datetime.now().isoformat(),
                "responsavel": "sistema"
            })

        return {
            "success": True,
            "mensagem_enviada": True,
            "prioridade": prioridade
        }

    async def _registrar_simulacao(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Registrar simulação de emergência"""
        tipo = params.get("tipo")
        participantes = params.get("participantes", 0)
        tempo_evacuacao = params.get("tempo_evacuacao_minutos", 0)
        pontos_melhorar = params.get("pontos_melhorar", [])
        avaliacao = params.get("avaliacao", 0)

        simulacao = SimulacaoEmergencia(
            id=f"sim_{datetime.now().timestamp()}",
            tipo=TipoEmergencia[tipo.upper()],
            data_realizada=datetime.now(),
            participantes=participantes,
            tempo_evacuacao_minutos=tempo_evacuacao,
            pontos_melhorar=pontos_melhorar,
            avaliacao=avaliacao
        )
        self._simulacoes.append(simulacao)

        return {
            "success": True,
            "simulacao_id": simulacao.id,
            "tipo": tipo,
            "participantes": participantes,
            "avaliacao": avaliacao
        }

    async def _criar_alerta_preventivo(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Criar alerta preventivo"""
        tipo = params.get("tipo")
        descricao = params.get("descricao")
        nivel = params.get("nivel", "amarelo")
        duracao_horas = params.get("duracao_horas")

        alerta = AlertaPreventivo(
            id=f"alerta_{datetime.now().timestamp()}",
            tipo=tipo,
            descricao=descricao,
            nivel=nivel,
            data_inicio=datetime.now(),
            data_fim=datetime.now() + timedelta(hours=duracao_horas) if duracao_horas else None
        )
        self._alertas.append(alerta)

        # Notificar moradores
        await self._comunicar_moradores({
            "mensagem": f"ALERTA {nivel.upper()}: {descricao}",
            "prioridade": "alta" if nivel in ["laranja", "vermelho"] else "normal"
        }, context)

        return {
            "success": True,
            "alerta_id": alerta.id,
            "tipo": tipo,
            "nivel": nivel
        }

    async def _status_emergencia_ativa(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Status da emergência ativa"""
        if not self._emergencia_ativa:
            return {
                "success": True,
                "emergencia_ativa": False
            }

        emergencia = self._emergencias.get(self._emergencia_ativa)
        if not emergencia:
            return {
                "success": True,
                "emergencia_ativa": False
            }

        duracao = (datetime.now() - emergencia.data_inicio).total_seconds() / 60

        return {
            "success": True,
            "emergencia_ativa": True,
            "emergencia": {
                "id": emergencia.id,
                "tipo": emergencia.tipo.value,
                "gravidade": emergencia.gravidade.value,
                "status": emergencia.status.value,
                "local": emergencia.local,
                "duracao_minutos": round(duracao, 1),
                "protocolos_ativos": emergencia.protocolos_ativados,
                "autoridades_acionadas": emergencia.autoridades_acionadas,
                "timeline": emergencia.timeline[-5:]
            }
        }

    async def _historico_emergencias(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Histórico de emergências"""
        ano = params.get("ano", datetime.now().year)

        emergencias = [
            e for e in self._emergencias.values()
            if e.data_inicio.year == ano
        ]

        por_tipo = {}
        for tipo in TipoEmergencia:
            por_tipo[tipo.value] = len([e for e in emergencias if e.tipo == tipo])

        por_gravidade = {}
        for grav in GravidadeEmergencia:
            por_gravidade[grav.value] = len([e for e in emergencias if e.gravidade == grav])

        return {
            "success": True,
            "ano": ano,
            "total_emergencias": len(emergencias),
            "por_tipo": por_tipo,
            "por_gravidade": por_gravidade,
            "total_vitimas": sum(e.vitimas for e in emergencias),
            "total_feridos": sum(e.feridos for e in emergencias),
            "danos_totais": sum(e.danos_estimados for e in emergencias),
            "simulacoes_realizadas": len([s for s in self._simulacoes if s.data_realizada.year == ano])
        }

    async def _alerta_panico(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Receber alerta de pânico (do agente portaria)"""
        porteiro_id = params.get("porteiro_id")
        tipo = params.get("tipo", "panico")
        localizacao = params.get("localizacao")
        silencioso = params.get("silencioso", False)

        # Criar emergência automaticamente
        result = await self._alerta_emergencia({
            "tipo": "seguranca",
            "gravidade": "critica",
            "descricao": f"Alerta de {tipo} acionado por porteiro {porteiro_id}",
            "local": localizacao or "portaria",
            "reportado_por": porteiro_id
        }, context)

        # Acionar polícia se não for silencioso
        if not silencioso:
            await self._acionar_autoridade({
                "tipo": "policia",
                "emergencia_id": result.get("emergencia_id")
            }, context)

        return {
            "success": True,
            "emergencia_id": result.get("emergencia_id"),
            "tipo": tipo,
            "resposta_automatica": True
        }

    async def _dashboard(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Dashboard de emergência"""
        ano = datetime.now().year

        emergencias_ano = [e for e in self._emergencias.values() if e.data_inicio.year == ano]
        alertas_ativos = [a for a in self._alertas if a.ativo]

        return {
            "success": True,
            "status_geral": "emergencia_ativa" if self._emergencia_ativa else "normal",
            "emergencia_ativa": self._emergencia_ativa is not None,
            "resumo_ano": {
                "total_emergencias": len(emergencias_ano),
                "criticas": len([e for e in emergencias_ano if e.gravidade == GravidadeEmergencia.CRITICA]),
                "vitimas": sum(e.vitimas for e in emergencias_ano),
                "feridos": sum(e.feridos for e in emergencias_ano),
                "simulacoes": len([s for s in self._simulacoes if s.data_realizada.year == ano])
            },
            "alertas_ativos": len(alertas_ativos),
            "contatos_emergencia": len(self._contatos),
            "protocolos_cadastrados": len(self._protocolos),
            "ultima_simulacao": self._simulacoes[-1].data_realizada.isoformat() if self._simulacoes else None
        }

    async def _chat(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        if self.llm:
            response = await self.llm.generate(
                self.get_system_prompt(), params.get("message", "")
            )
            return {"success": True, "response": response}
        return {"error": "LLM não configurado"}


def create_emergency_agent(
    condominio_id: str,
    llm_client: UnifiedLLMClient = None,
    memory: UnifiedMemorySystem = None,
    tools: ToolRegistry = None,
    evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT
) -> AgenteEmergencia:
    """Factory function para criar agente de emergência"""
    return AgenteEmergencia(
        condominio_id=condominio_id,
        llm_client=llm_client or UnifiedLLMClient(),
        memory=memory,
        tools=tools,
        evolution_level=evolution_level
    )
