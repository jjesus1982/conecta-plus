"""
Conecta Plus - Agente Social (Nível 7)
Gestor de comunidade, eventos e networking condominial

Capacidades:
1. REATIVO: Responder dúvidas, registrar participações
2. PROATIVO: Sugerir eventos, conectar moradores
3. PREDITIVO: Prever engajamento, tendências de interesse
4. AUTÔNOMO: Organizar eventos, moderar grupos
5. EVOLUTIVO: Aprender preferências da comunidade
6. COLABORATIVO: Integrar Comunicação, Reservas, Financeiro
7. TRANSCENDENTE: Gestor de comunidade completo
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


class TipoEvento(Enum):
    FESTA = "festa"
    REUNIAO = "reuniao"
    CURSO = "curso"
    ESPORTE = "esporte"
    CULTURAL = "cultural"
    INFANTIL = "infantil"
    GASTRONOMIA = "gastronomia"
    SOCIAL = "social"
    BENEFICENTE = "beneficente"


class StatusEvento(Enum):
    PLANEJADO = "planejado"
    CONFIRMADO = "confirmado"
    EM_ANDAMENTO = "em_andamento"
    CONCLUIDO = "concluido"
    CANCELADO = "cancelado"


class TipoGrupo(Enum):
    INTERESSE = "interesse"
    FAIXA_ETARIA = "faixa_etaria"
    ESPORTE = "esporte"
    PROFISSIONAL = "profissional"
    VOLUNTARIADO = "voluntariado"


class TipoAnuncio(Enum):
    VENDA = "venda"
    DOACAO = "doacao"
    TROCA = "troca"
    SERVICO = "servico"
    PROCURA = "procura"


@dataclass
class EventoComunidade:
    id: str
    tipo: TipoEvento
    titulo: str
    descricao: str
    data_evento: datetime
    local: str
    organizador_id: str
    status: StatusEvento
    capacidade: int = 0
    confirmados: List[str] = field(default_factory=list)
    lista_espera: List[str] = field(default_factory=list)
    custo_participante: float = 0
    patrocinadores: List[str] = field(default_factory=list)
    fotos: List[str] = field(default_factory=list)
    avaliacao_media: float = 0
    comentarios: List[Dict] = field(default_factory=list)


@dataclass
class GrupoComunidade:
    id: str
    tipo: TipoGrupo
    nome: str
    descricao: str
    moderador_id: str
    membros: List[str] = field(default_factory=list)
    data_criacao: datetime = field(default_factory=datetime.now)
    ativo: bool = True
    regras: List[str] = field(default_factory=list)


@dataclass
class AnuncioMarketplace:
    id: str
    tipo: TipoAnuncio
    titulo: str
    descricao: str
    preco: float
    anunciante_id: str
    anunciante_nome: str
    data_publicacao: datetime
    fotos: List[str] = field(default_factory=list)
    ativo: bool = True
    interessados: List[str] = field(default_factory=list)
    vendido: bool = False


@dataclass
class PerfilMorador:
    morador_id: str
    nome: str
    unidade: str
    interesses: List[str] = field(default_factory=list)
    habilidades: List[str] = field(default_factory=list)
    disponibilidade_voluntariado: bool = False
    grupos: List[str] = field(default_factory=list)
    eventos_participados: int = 0
    conexoes: List[str] = field(default_factory=list)
    pontos_engajamento: int = 0


class AgenteSocial(BaseAgent):
    """Agente Social - Gestor de Comunidade Nível 7"""

    def __init__(
        self,
        condominio_id: str,
        llm_client: UnifiedLLMClient = None,
        memory: UnifiedMemorySystem = None,
        tools: ToolRegistry = None,
        evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT,
    ):
        super().__init__(
            agent_id=f"social_{condominio_id}",
            agent_type="social",
            condominio_id=condominio_id,
            evolution_level=evolution_level,
            llm_client=llm_client,
            memory_store=memory,
        )
        self.tools = tools

        self._eventos: Dict[str, EventoComunidade] = {}
        self._grupos: Dict[str, GrupoComunidade] = {}
        self._anuncios: Dict[str, AnuncioMarketplace] = {}
        self._perfis: Dict[str, PerfilMorador] = {}
        self._sugestoes_conexao: List[Dict] = []

        self.config = {
            "moderar_anuncios": True,
            "limite_anuncios_mes": 5,
            "gamificacao_ativa": True,
            "matchmaking_ativo": True,
            "eventos_sugeridos": True,
        }

    def _register_capabilities(self) -> None:
        self._capabilities["gestao_eventos"] = AgentCapability(
            name="gestao_eventos", description="Gerenciar eventos da comunidade",
            level=EvolutionLevel.PROACTIVE
        )
        self._capabilities["gestao_grupos"] = AgentCapability(
            name="gestao_grupos", description="Gerenciar grupos de interesse",
            level=EvolutionLevel.PROACTIVE
        )
        self._capabilities["marketplace"] = AgentCapability(
            name="marketplace", description="Gerenciar marketplace interno",
            level=EvolutionLevel.REACTIVE
        )
        self._capabilities["networking"] = AgentCapability(
            name="networking", description="Facilitar networking entre moradores",
            level=EvolutionLevel.PREDICTIVE
        )
        self._capabilities["comunidade_total"] = AgentCapability(
            name="comunidade_total", description="Gestão de comunidade completa",
            level=EvolutionLevel.TRANSCENDENT
        )

    def get_system_prompt(self) -> str:
        return f"""Você é o Agente Social do Conecta Plus.
ID: {self.agent_id} | Condomínio: {self.condominio_id} | Nível: {self.evolution_level.name}

RESPONSABILIDADES:
- Organização de eventos comunitários
- Gestão de grupos de interesse
- Marketplace interno (vendas, trocas, doações)
- Networking entre moradores
- Gamificação e engajamento
- Voluntariado e ações sociais

COMPORTAMENTO:
- Promova integração e convivência
- Sugira conexões relevantes
- Modere conteúdos adequadamente
- Incentive participação
"""

    async def process(self, input_data: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        action = input_data.get("action", "")
        params = input_data.get("params", {})

        # Eventos
        if action == "criar_evento":
            return await self._criar_evento(params, context)
        elif action == "confirmar_presenca":
            return await self._confirmar_presenca(params, context)
        elif action == "cancelar_presenca":
            return await self._cancelar_presenca(params, context)
        elif action == "listar_eventos":
            return await self._listar_eventos(params, context)
        elif action == "avaliar_evento":
            return await self._avaliar_evento(params, context)

        # Grupos
        elif action == "criar_grupo":
            return await self._criar_grupo(params, context)
        elif action == "entrar_grupo":
            return await self._entrar_grupo(params, context)
        elif action == "sair_grupo":
            return await self._sair_grupo(params, context)
        elif action == "listar_grupos":
            return await self._listar_grupos(params, context)

        # Marketplace
        elif action == "criar_anuncio":
            return await self._criar_anuncio(params, context)
        elif action == "listar_anuncios":
            return await self._listar_anuncios(params, context)
        elif action == "interesse_anuncio":
            return await self._interesse_anuncio(params, context)
        elif action == "finalizar_anuncio":
            return await self._finalizar_anuncio(params, context)

        # Perfil e Networking
        elif action == "atualizar_perfil":
            return await self._atualizar_perfil(params, context)
        elif action == "buscar_conexoes":
            return await self._buscar_conexoes(params, context)
        elif action == "conectar":
            return await self._conectar(params, context)
        elif action == "ranking_engajamento":
            return await self._ranking_engajamento(params, context)

        # Dashboard
        elif action == "dashboard":
            return await self._dashboard(params, context)
        elif action == "sugerir_eventos":
            return await self._sugerir_eventos(params, context)
        elif action == "chat":
            return await self._chat(params, context)
        else:
            return {"error": f"Ação '{action}' não reconhecida"}

    async def _criar_evento(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Criar evento comunitário"""
        tipo = params.get("tipo", "social")
        titulo = params.get("titulo")
        descricao = params.get("descricao", "")
        data_evento = params.get("data_evento")
        local = params.get("local")
        organizador_id = params.get("organizador_id")
        capacidade = params.get("capacidade", 0)
        custo = params.get("custo_participante", 0)

        evento = EventoComunidade(
            id=f"evento_{datetime.now().timestamp()}",
            tipo=TipoEvento[tipo.upper()],
            titulo=titulo,
            descricao=descricao,
            data_evento=datetime.fromisoformat(data_evento) if data_evento else datetime.now() + timedelta(days=7),
            local=local,
            organizador_id=organizador_id,
            status=StatusEvento.PLANEJADO,
            capacidade=capacidade,
            custo_participante=custo
        )
        self._eventos[evento.id] = evento

        # Notificar moradores interessados
        if self.tools:
            await self.tools.execute(
                "send_notification",
                user_ids=["all_residents"],
                title=f"Novo Evento: {titulo}",
                message=f"{descricao[:100]}...\nData: {evento.data_evento.strftime('%d/%m às %H:%M')}",
                channels=["push", "app"]
            )

        # Colaborar com agente de reservas
        if self.has_capability("agent_collaboration"):
            await self.send_message(
                f"reservas_{self.condominio_id}",
                {
                    "action": "bloquear_espaco",
                    "local": local,
                    "data": evento.data_evento.isoformat(),
                    "evento_id": evento.id
                }
            )

        return {
            "success": True,
            "evento_id": evento.id,
            "titulo": titulo,
            "data": evento.data_evento.isoformat(),
            "local": local
        }

    async def _confirmar_presenca(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Confirmar presença em evento"""
        evento_id = params.get("evento_id")
        morador_id = params.get("morador_id")

        if evento_id not in self._eventos:
            return {"error": "Evento não encontrado"}

        evento = self._eventos[evento_id]

        if morador_id in evento.confirmados:
            return {"error": "Já confirmado neste evento"}

        if evento.capacidade > 0 and len(evento.confirmados) >= evento.capacidade:
            evento.lista_espera.append(morador_id)
            return {
                "success": True,
                "status": "lista_espera",
                "posicao": len(evento.lista_espera)
            }

        evento.confirmados.append(morador_id)

        # Atualizar perfil
        if morador_id in self._perfis:
            self._perfis[morador_id].eventos_participados += 1
            self._perfis[morador_id].pontos_engajamento += 10

        return {
            "success": True,
            "status": "confirmado",
            "total_confirmados": len(evento.confirmados)
        }

    async def _cancelar_presenca(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Cancelar presença em evento"""
        evento_id = params.get("evento_id")
        morador_id = params.get("morador_id")

        if evento_id not in self._eventos:
            return {"error": "Evento não encontrado"}

        evento = self._eventos[evento_id]

        if morador_id in evento.confirmados:
            evento.confirmados.remove(morador_id)

            # Chamar próximo da lista de espera
            if evento.lista_espera:
                proximo = evento.lista_espera.pop(0)
                evento.confirmados.append(proximo)

                if self.tools:
                    await self.tools.execute(
                        "send_notification",
                        user_ids=[proximo],
                        title=f"Vaga liberada: {evento.titulo}",
                        message="Sua vaga foi confirmada!",
                        channels=["push"]
                    )

        return {"success": True, "status": "cancelado"}

    async def _listar_eventos(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Listar eventos"""
        tipo = params.get("tipo")
        status = params.get("status")
        futuro = params.get("futuro", True)

        eventos = list(self._eventos.values())

        if tipo:
            eventos = [e for e in eventos if e.tipo.value == tipo]
        if status:
            eventos = [e for e in eventos if e.status.value == status]
        if futuro:
            eventos = [e for e in eventos if e.data_evento > datetime.now()]

        eventos = sorted(eventos, key=lambda x: x.data_evento)

        return {
            "success": True,
            "total": len(eventos),
            "eventos": [
                {
                    "id": e.id,
                    "tipo": e.tipo.value,
                    "titulo": e.titulo,
                    "data": e.data_evento.isoformat(),
                    "local": e.local,
                    "confirmados": len(e.confirmados),
                    "capacidade": e.capacidade,
                    "custo": e.custo_participante,
                    "avaliacao": e.avaliacao_media
                }
                for e in eventos
            ]
        }

    async def _avaliar_evento(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Avaliar evento"""
        evento_id = params.get("evento_id")
        morador_id = params.get("morador_id")
        nota = params.get("nota", 5)
        comentario = params.get("comentario", "")

        if evento_id not in self._eventos:
            return {"error": "Evento não encontrado"}

        evento = self._eventos[evento_id]

        if morador_id not in evento.confirmados:
            return {"error": "Apenas participantes podem avaliar"}

        evento.comentarios.append({
            "morador_id": morador_id,
            "nota": nota,
            "comentario": comentario,
            "data": datetime.now().isoformat()
        })

        # Recalcular média
        notas = [c["nota"] for c in evento.comentarios]
        evento.avaliacao_media = sum(notas) / len(notas)

        return {
            "success": True,
            "evento_id": evento_id,
            "nota": nota,
            "avaliacao_media": round(evento.avaliacao_media, 1)
        }

    async def _criar_grupo(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Criar grupo de interesse"""
        tipo = params.get("tipo", "interesse")
        nome = params.get("nome")
        descricao = params.get("descricao", "")
        moderador_id = params.get("moderador_id")
        regras = params.get("regras", [])

        grupo = GrupoComunidade(
            id=f"grupo_{datetime.now().timestamp()}",
            tipo=TipoGrupo[tipo.upper()],
            nome=nome,
            descricao=descricao,
            moderador_id=moderador_id,
            membros=[moderador_id],
            regras=regras
        )
        self._grupos[grupo.id] = grupo

        return {
            "success": True,
            "grupo_id": grupo.id,
            "nome": nome,
            "tipo": tipo
        }

    async def _entrar_grupo(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Entrar em grupo"""
        grupo_id = params.get("grupo_id")
        morador_id = params.get("morador_id")

        if grupo_id not in self._grupos:
            return {"error": "Grupo não encontrado"}

        grupo = self._grupos[grupo_id]

        if morador_id in grupo.membros:
            return {"error": "Já é membro deste grupo"}

        grupo.membros.append(morador_id)

        # Atualizar perfil
        if morador_id in self._perfis:
            self._perfis[morador_id].grupos.append(grupo_id)
            self._perfis[morador_id].pontos_engajamento += 5

        return {
            "success": True,
            "grupo_id": grupo_id,
            "total_membros": len(grupo.membros)
        }

    async def _sair_grupo(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Sair de grupo"""
        grupo_id = params.get("grupo_id")
        morador_id = params.get("morador_id")

        if grupo_id not in self._grupos:
            return {"error": "Grupo não encontrado"}

        grupo = self._grupos[grupo_id]

        if morador_id == grupo.moderador_id:
            return {"error": "Moderador não pode sair. Transfira a moderação primeiro."}

        if morador_id in grupo.membros:
            grupo.membros.remove(morador_id)

        return {"success": True, "status": "saiu_do_grupo"}

    async def _listar_grupos(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Listar grupos"""
        tipo = params.get("tipo")

        grupos = list(self._grupos.values())
        if tipo:
            grupos = [g for g in grupos if g.tipo.value == tipo]

        return {
            "success": True,
            "total": len(grupos),
            "grupos": [
                {
                    "id": g.id,
                    "tipo": g.tipo.value,
                    "nome": g.nome,
                    "descricao": g.descricao[:100],
                    "membros": len(g.membros),
                    "ativo": g.ativo
                }
                for g in grupos if g.ativo
            ]
        }

    async def _criar_anuncio(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Criar anúncio no marketplace"""
        tipo = params.get("tipo", "venda")
        titulo = params.get("titulo")
        descricao = params.get("descricao", "")
        preco = params.get("preco", 0)
        anunciante_id = params.get("anunciante_id")
        anunciante_nome = params.get("anunciante_nome")
        fotos = params.get("fotos", [])

        # Verificar limite mensal
        anuncios_mes = [
            a for a in self._anuncios.values()
            if a.anunciante_id == anunciante_id
            and a.data_publicacao.month == datetime.now().month
        ]
        if len(anuncios_mes) >= self.config["limite_anuncios_mes"]:
            return {"error": f"Limite de {self.config['limite_anuncios_mes']} anúncios/mês atingido"}

        anuncio = AnuncioMarketplace(
            id=f"anuncio_{datetime.now().timestamp()}",
            tipo=TipoAnuncio[tipo.upper()],
            titulo=titulo,
            descricao=descricao,
            preco=preco,
            anunciante_id=anunciante_id,
            anunciante_nome=anunciante_nome,
            data_publicacao=datetime.now(),
            fotos=fotos
        )
        self._anuncios[anuncio.id] = anuncio

        return {
            "success": True,
            "anuncio_id": anuncio.id,
            "titulo": titulo,
            "tipo": tipo
        }

    async def _listar_anuncios(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Listar anúncios"""
        tipo = params.get("tipo")
        limite = params.get("limite", 20)

        anuncios = [a for a in self._anuncios.values() if a.ativo and not a.vendido]

        if tipo:
            anuncios = [a for a in anuncios if a.tipo.value == tipo]

        anuncios = sorted(anuncios, key=lambda x: x.data_publicacao, reverse=True)[:limite]

        return {
            "success": True,
            "total": len(anuncios),
            "anuncios": [
                {
                    "id": a.id,
                    "tipo": a.tipo.value,
                    "titulo": a.titulo,
                    "preco": a.preco,
                    "anunciante": a.anunciante_nome,
                    "data": a.data_publicacao.isoformat(),
                    "fotos": len(a.fotos),
                    "interessados": len(a.interessados)
                }
                for a in anuncios
            ]
        }

    async def _interesse_anuncio(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Manifestar interesse em anúncio"""
        anuncio_id = params.get("anuncio_id")
        morador_id = params.get("morador_id")

        if anuncio_id not in self._anuncios:
            return {"error": "Anúncio não encontrado"}

        anuncio = self._anuncios[anuncio_id]

        if morador_id not in anuncio.interessados:
            anuncio.interessados.append(morador_id)

            # Notificar anunciante
            if self.tools:
                await self.tools.execute(
                    "send_notification",
                    user_ids=[anuncio.anunciante_id],
                    title=f"Interesse em: {anuncio.titulo}",
                    message=f"Alguém demonstrou interesse no seu anúncio",
                    channels=["push"]
                )

        return {
            "success": True,
            "anuncio_id": anuncio_id,
            "total_interessados": len(anuncio.interessados)
        }

    async def _finalizar_anuncio(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Finalizar anúncio"""
        anuncio_id = params.get("anuncio_id")
        vendido = params.get("vendido", True)

        if anuncio_id not in self._anuncios:
            return {"error": "Anúncio não encontrado"}

        anuncio = self._anuncios[anuncio_id]
        anuncio.ativo = False
        anuncio.vendido = vendido

        return {
            "success": True,
            "anuncio_id": anuncio_id,
            "status": "vendido" if vendido else "removido"
        }

    async def _atualizar_perfil(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Atualizar perfil de morador"""
        morador_id = params.get("morador_id")
        nome = params.get("nome")
        unidade = params.get("unidade")
        interesses = params.get("interesses", [])
        habilidades = params.get("habilidades", [])
        voluntariado = params.get("voluntariado", False)

        if morador_id not in self._perfis:
            self._perfis[morador_id] = PerfilMorador(
                morador_id=morador_id,
                nome=nome,
                unidade=unidade
            )

        perfil = self._perfis[morador_id]
        if nome:
            perfil.nome = nome
        if unidade:
            perfil.unidade = unidade
        if interesses:
            perfil.interesses = interesses
        if habilidades:
            perfil.habilidades = habilidades
        perfil.disponibilidade_voluntariado = voluntariado

        return {
            "success": True,
            "morador_id": morador_id,
            "perfil_atualizado": True
        }

    async def _buscar_conexoes(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Buscar conexões com interesses similares"""
        morador_id = params.get("morador_id")

        if morador_id not in self._perfis:
            return {"error": "Perfil não encontrado"}

        perfil = self._perfis[morador_id]
        sugestoes = []

        for outro_id, outro_perfil in self._perfis.items():
            if outro_id == morador_id or outro_id in perfil.conexoes:
                continue

            # Calcular compatibilidade
            interesses_comum = set(perfil.interesses) & set(outro_perfil.interesses)
            habilidades_comum = set(perfil.habilidades) & set(outro_perfil.habilidades)

            score = len(interesses_comum) * 10 + len(habilidades_comum) * 5

            if score > 0:
                sugestoes.append({
                    "morador_id": outro_id,
                    "nome": outro_perfil.nome,
                    "unidade": outro_perfil.unidade,
                    "interesses_comum": list(interesses_comum),
                    "score": score
                })

        sugestoes = sorted(sugestoes, key=lambda x: x["score"], reverse=True)[:10]

        return {
            "success": True,
            "sugestoes": sugestoes
        }

    async def _conectar(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Conectar com outro morador"""
        morador_id = params.get("morador_id")
        outro_id = params.get("outro_id")

        if morador_id not in self._perfis or outro_id not in self._perfis:
            return {"error": "Perfil não encontrado"}

        perfil = self._perfis[morador_id]
        outro = self._perfis[outro_id]

        if outro_id not in perfil.conexoes:
            perfil.conexoes.append(outro_id)
            perfil.pontos_engajamento += 5

        if morador_id not in outro.conexoes:
            outro.conexoes.append(morador_id)
            outro.pontos_engajamento += 5

        return {
            "success": True,
            "conexao_estabelecida": True,
            "total_conexoes": len(perfil.conexoes)
        }

    async def _ranking_engajamento(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Ranking de engajamento"""
        limite = params.get("limite", 10)

        ranking = sorted(
            self._perfis.values(),
            key=lambda x: x.pontos_engajamento,
            reverse=True
        )[:limite]

        return {
            "success": True,
            "ranking": [
                {
                    "posicao": i + 1,
                    "nome": p.nome,
                    "unidade": p.unidade,
                    "pontos": p.pontos_engajamento,
                    "eventos": p.eventos_participados,
                    "conexoes": len(p.conexoes)
                }
                for i, p in enumerate(ranking)
            ]
        }

    async def _sugerir_eventos(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Sugerir eventos baseado em histórico"""
        morador_id = params.get("morador_id")

        if not self.llm:
            return {"error": "LLM não configurado"}

        perfil = self._perfis.get(morador_id)
        eventos_anteriores = list(self._eventos.values())[-20:]

        prompt = f"""Sugira 3 tipos de eventos para o condomínio baseado em:

Perfil do morador (se disponível): {perfil.interesses if perfil else "Não disponível"}

Eventos anteriores populares:
{json.dumps([{"tipo": e.tipo.value, "titulo": e.titulo, "avaliacao": e.avaliacao_media} for e in eventos_anteriores], indent=2)}

Sugira eventos que promovam integração e tenham boa aceitação.
"""

        sugestoes = await self.llm.generate(self.get_system_prompt(), prompt)

        return {
            "success": True,
            "sugestoes": sugestoes
        }

    async def _dashboard(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Dashboard social"""
        eventos_futuros = [e for e in self._eventos.values() if e.data_evento > datetime.now()]
        grupos_ativos = [g for g in self._grupos.values() if g.ativo]
        anuncios_ativos = [a for a in self._anuncios.values() if a.ativo and not a.vendido]

        return {
            "success": True,
            "resumo": {
                "eventos_proximos": len(eventos_futuros),
                "grupos_ativos": len(grupos_ativos),
                "anuncios_ativos": len(anuncios_ativos),
                "moradores_engajados": len(self._perfis),
                "total_conexoes": sum(len(p.conexoes) for p in self._perfis.values()) // 2
            },
            "proximos_eventos": [
                {"titulo": e.titulo, "data": e.data_evento.isoformat(), "confirmados": len(e.confirmados)}
                for e in sorted(eventos_futuros, key=lambda x: x.data_evento)[:5]
            ],
            "grupos_populares": [
                {"nome": g.nome, "membros": len(g.membros)}
                for g in sorted(grupos_ativos, key=lambda x: len(x.membros), reverse=True)[:5]
            ],
            "anuncios_recentes": [
                {"titulo": a.titulo, "tipo": a.tipo.value, "preco": a.preco}
                for a in sorted(anuncios_ativos, key=lambda x: x.data_publicacao, reverse=True)[:5]
            ]
        }

    async def _chat(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        if self.llm:
            response = await self.llm.generate(
                self.get_system_prompt(), params.get("message", "")
            )
            return {"success": True, "response": response}
        return {"error": "LLM não configurado"}


def create_social_agent(
    condominio_id: str,
    llm_client: UnifiedLLMClient = None,
    memory: UnifiedMemorySystem = None,
    tools: ToolRegistry = None,
    evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT
) -> AgenteSocial:
    """Factory function para criar agente social"""
    return AgenteSocial(
        condominio_id=condominio_id,
        llm_client=llm_client or UnifiedLLMClient(),
        memory=memory,
        tools=tools,
        evolution_level=evolution_level
    )
