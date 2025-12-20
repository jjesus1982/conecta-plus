"""
Conecta Plus - Agente Estacionamento (Nível 7)
Gestor de vagas, veículos e controle de acesso veicular

Capacidades:
1. REATIVO: Registrar veículos, liberar acesso
2. PROATIVO: Detectar irregularidades, alertar violações
3. PREDITIVO: Prever ocupação, identificar padrões
4. AUTÔNOMO: Controlar cancelas, gerar multas automáticas
5. EVOLUTIVO: Aprender fluxos, otimizar distribuição
6. COLABORATIVO: Integrar CFTV, Acesso, Portaria
7. TRANSCENDENTE: Gestão completa de estacionamento
"""

import asyncio
import json
import logging
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


class TipoVaga(Enum):
    NORMAL = "normal"
    COBERTA = "coberta"
    IDOSO = "idoso"
    PCD = "pcd"
    VISITANTE = "visitante"
    CARGA_DESCARGA = "carga_descarga"
    MOTO = "moto"
    BICICLETA = "bicicleta"
    ELETRICO = "eletrico"


class StatusVaga(Enum):
    LIVRE = "livre"
    OCUPADA = "ocupada"
    RESERVADA = "reservada"
    BLOQUEADA = "bloqueada"
    MANUTENCAO = "manutencao"


class TipoVeiculo(Enum):
    CARRO = "carro"
    MOTO = "moto"
    BICICLETA = "bicicleta"
    CAMINHAO = "caminhao"
    VAN = "van"
    ELETRICO = "eletrico"


class TipoInfracao(Enum):
    VAGA_ERRADA = "vaga_errada"
    VAGA_ALHEIA = "vaga_alheia"
    VELOCIDADE = "velocidade"
    MAO_ERRADA = "mao_errada"
    ESTACIONAMENTO_IRREGULAR = "estacionamento_irregular"
    BLOQUEIO_PASSAGEM = "bloqueio_passagem"
    VEICULO_NAO_CADASTRADO = "veiculo_nao_cadastrado"


@dataclass
class Vaga:
    id: str
    numero: str
    tipo: TipoVaga
    status: StatusVaga
    andar: str
    bloco: Optional[str] = None
    proprietario_id: Optional[str] = None
    proprietario_nome: Optional[str] = None
    unidade: Optional[str] = None
    tem_carregador_ev: bool = False
    tamanho: str = "normal"  # normal, grande, compacta


@dataclass
class Veiculo:
    id: str
    placa: str
    tipo: TipoVeiculo
    marca: str
    modelo: str
    cor: str
    ano: int
    morador_id: str
    morador_nome: str
    unidade: str
    vaga_atribuida: Optional[str] = None
    eletrico: bool = False
    tag_rfid: Optional[str] = None
    ativo: bool = True


@dataclass
class RegistroAcesso:
    id: str
    veiculo_id: str
    placa: str
    tipo: str  # entrada, saida
    data_hora: datetime
    ponto_acesso: str
    metodo: str  # tag, placa, manual
    foto_url: Optional[str] = None
    autorizado: bool = True


@dataclass
class Infracao:
    id: str
    tipo: TipoInfracao
    veiculo_id: Optional[str]
    placa: str
    descricao: str
    data_hora: datetime
    local: str
    evidencias: List[str] = field(default_factory=list)
    multa_valor: float = 0
    multa_aplicada: bool = False
    resolvida: bool = False


@dataclass
class ReservaVaga:
    id: str
    vaga_id: str
    solicitante_id: str
    motivo: str
    data_inicio: datetime
    data_fim: datetime
    aprovada: bool = False
    placa_visitante: Optional[str] = None


class AgenteEstacionamento(BaseAgent):
    """Agente Estacionamento - Gestor de Vagas Nível 7"""

    def __init__(
        self,
        condominio_id: str,
        llm_client: UnifiedLLMClient = None,
        memory: UnifiedMemorySystem = None,
        tools: ToolRegistry = None,
        evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT,
    ):
        super().__init__(
            agent_id=f"estacionamento_{condominio_id}",
            agent_type="estacionamento",
            condominio_id=condominio_id,
            evolution_level=evolution_level,
            llm_client=llm_client,
            memory_store=memory,
        )
        self.tools = tools

        self._vagas: Dict[str, Vaga] = {}
        self._veiculos: Dict[str, Veiculo] = {}
        self._acessos: List[RegistroAcesso] = []
        self._infracoes: List[Infracao] = []
        self._reservas: List[ReservaVaga] = []
        self._veiculos_dentro: Dict[str, datetime] = {}  # placa: hora_entrada

        self.config = {
            "vagas_visitante": 5,
            "tempo_max_visitante_horas": 4,
            "velocidade_maxima_kmh": 20,
            "valor_multa_base": 100,
            "lpr_ativo": True,  # License Plate Recognition
            "cancela_automatica": True,
        }

    def _register_capabilities(self) -> None:
        self._capabilities["gestao_vagas"] = AgentCapability(
            name="gestao_vagas", description="Gerenciar vagas de estacionamento",
            level=EvolutionLevel.REACTIVE
        )
        self._capabilities["controle_acesso"] = AgentCapability(
            name="controle_acesso", description="Controlar acesso de veículos",
            level=EvolutionLevel.PROACTIVE
        )
        self._capabilities["deteccao_infracoes"] = AgentCapability(
            name="deteccao_infracoes", description="Detectar infrações",
            level=EvolutionLevel.AUTONOMOUS
        )
        self._capabilities["lpr"] = AgentCapability(
            name="lpr", description="Reconhecimento de placas",
            level=EvolutionLevel.PROACTIVE
        )
        self._capabilities["gestao_estacionamento_total"] = AgentCapability(
            name="gestao_estacionamento_total", description="Gestão completa",
            level=EvolutionLevel.TRANSCENDENT
        )

    def get_system_prompt(self) -> str:
        return f"""Você é o Agente de Estacionamento do Conecta Plus.
ID: {self.agent_id} | Condomínio: {self.condominio_id} | Nível: {self.evolution_level.name}

RESPONSABILIDADES:
- Gestão de vagas e veículos
- Controle de acesso veicular (cancelas)
- Reconhecimento de placas (LPR)
- Detecção de infrações
- Reserva de vagas para visitantes
- Controle de carregadores EV
- Geração de multas

COMPORTAMENTO:
- Priorize segurança e fluxo
- Detecte veículos não autorizados
- Monitore ocupação em tempo real
- Alerte sobre irregularidades
"""

    async def process(self, input_data: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        action = input_data.get("action", "")
        params = input_data.get("params", {})

        if action == "cadastrar_vaga":
            return await self._cadastrar_vaga(params, context)
        elif action == "cadastrar_veiculo":
            return await self._cadastrar_veiculo(params, context)
        elif action == "atribuir_vaga":
            return await self._atribuir_vaga(params, context)
        elif action == "listar_vagas":
            return await self._listar_vagas(params, context)
        elif action == "listar_veiculos":
            return await self._listar_veiculos(params, context)
        elif action == "registrar_entrada":
            return await self._registrar_entrada(params, context)
        elif action == "registrar_saida":
            return await self._registrar_saida(params, context)
        elif action == "consultar_placa":
            return await self._consultar_placa(params, context)
        elif action == "registrar_infracao":
            return await self._registrar_infracao(params, context)
        elif action == "listar_infracoes":
            return await self._listar_infracoes(params, context)
        elif action == "reservar_vaga_visitante":
            return await self._reservar_vaga_visitante(params, context)
        elif action == "liberar_visitante":
            return await self._liberar_visitante(params, context)
        elif action == "ocupacao_tempo_real":
            return await self._ocupacao_tempo_real(params, context)
        elif action == "veiculos_dentro":
            return await self._veiculos_dentro_func(params, context)
        elif action == "historico_acessos":
            return await self._historico_acessos(params, context)
        elif action == "dashboard":
            return await self._dashboard(params, context)
        elif action == "chat":
            return await self._chat(params, context)
        else:
            return {"error": f"Ação '{action}' não reconhecida"}

    async def _cadastrar_vaga(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Cadastrar vaga"""
        numero = params.get("numero")
        tipo = params.get("tipo", "normal")
        andar = params.get("andar", "G")
        bloco = params.get("bloco")
        proprietario_id = params.get("proprietario_id")
        proprietario_nome = params.get("proprietario_nome")
        unidade = params.get("unidade")
        carregador_ev = params.get("carregador_ev", False)

        vaga_id = f"vaga_{andar}_{numero}"

        vaga = Vaga(
            id=vaga_id,
            numero=numero,
            tipo=TipoVaga[tipo.upper()],
            status=StatusVaga.LIVRE,
            andar=andar,
            bloco=bloco,
            proprietario_id=proprietario_id,
            proprietario_nome=proprietario_nome,
            unidade=unidade,
            tem_carregador_ev=carregador_ev
        )
        self._vagas[vaga_id] = vaga

        return {
            "success": True,
            "vaga_id": vaga_id,
            "numero": numero,
            "tipo": tipo
        }

    async def _cadastrar_veiculo(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Cadastrar veículo"""
        placa = params.get("placa", "").upper()
        tipo = params.get("tipo", "carro")
        marca = params.get("marca")
        modelo = params.get("modelo")
        cor = params.get("cor")
        ano = params.get("ano", 2020)
        morador_id = params.get("morador_id")
        morador_nome = params.get("morador_nome")
        unidade = params.get("unidade")
        tag_rfid = params.get("tag_rfid")
        eletrico = params.get("eletrico", False)

        # Verificar se placa já existe
        for v in self._veiculos.values():
            if v.placa == placa:
                return {"error": "Placa já cadastrada"}

        veiculo = Veiculo(
            id=f"veic_{datetime.now().timestamp()}",
            placa=placa,
            tipo=TipoVeiculo[tipo.upper()],
            marca=marca,
            modelo=modelo,
            cor=cor,
            ano=ano,
            morador_id=morador_id,
            morador_nome=morador_nome,
            unidade=unidade,
            tag_rfid=tag_rfid,
            eletrico=eletrico
        )
        self._veiculos[veiculo.id] = veiculo

        return {
            "success": True,
            "veiculo_id": veiculo.id,
            "placa": placa,
            "modelo": f"{marca} {modelo}"
        }

    async def _atribuir_vaga(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Atribuir vaga a veículo"""
        veiculo_id = params.get("veiculo_id")
        vaga_id = params.get("vaga_id")

        if veiculo_id not in self._veiculos:
            return {"error": "Veículo não encontrado"}
        if vaga_id not in self._vagas:
            return {"error": "Vaga não encontrada"}

        veiculo = self._veiculos[veiculo_id]
        vaga = self._vagas[vaga_id]

        if vaga.proprietario_id and vaga.proprietario_id != veiculo.morador_id:
            return {"error": "Vaga pertence a outro morador"}

        veiculo.vaga_atribuida = vaga_id

        return {
            "success": True,
            "veiculo": veiculo.placa,
            "vaga": vaga.numero
        }

    async def _listar_vagas(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Listar vagas"""
        tipo = params.get("tipo")
        status = params.get("status")
        andar = params.get("andar")

        vagas = list(self._vagas.values())

        if tipo:
            vagas = [v for v in vagas if v.tipo.value == tipo]
        if status:
            vagas = [v for v in vagas if v.status.value == status]
        if andar:
            vagas = [v for v in vagas if v.andar == andar]

        return {
            "success": True,
            "total": len(vagas),
            "vagas": [
                {
                    "id": v.id,
                    "numero": v.numero,
                    "tipo": v.tipo.value,
                    "status": v.status.value,
                    "andar": v.andar,
                    "unidade": v.unidade,
                    "carregador_ev": v.tem_carregador_ev
                }
                for v in vagas
            ]
        }

    async def _listar_veiculos(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Listar veículos"""
        unidade = params.get("unidade")
        tipo = params.get("tipo")

        veiculos = [v for v in self._veiculos.values() if v.ativo]

        if unidade:
            veiculos = [v for v in veiculos if v.unidade == unidade]
        if tipo:
            veiculos = [v for v in veiculos if v.tipo.value == tipo]

        return {
            "success": True,
            "total": len(veiculos),
            "veiculos": [
                {
                    "id": v.id,
                    "placa": v.placa,
                    "modelo": f"{v.marca} {v.modelo}",
                    "cor": v.cor,
                    "unidade": v.unidade,
                    "proprietario": v.morador_nome,
                    "vaga": v.vaga_atribuida,
                    "eletrico": v.eletrico
                }
                for v in veiculos
            ]
        }

    async def _registrar_entrada(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Registrar entrada de veículo"""
        placa = params.get("placa", "").upper()
        ponto_acesso = params.get("ponto_acesso", "entrada_principal")
        metodo = params.get("metodo", "placa")  # placa, tag, manual
        foto_url = params.get("foto_url")

        # Buscar veículo
        veiculo = next((v for v in self._veiculos.values() if v.placa == placa), None)

        autorizado = veiculo is not None and veiculo.ativo

        # Se não autorizado, verificar se é visitante com reserva
        if not autorizado:
            reserva_ativa = next(
                (r for r in self._reservas
                 if r.placa_visitante == placa
                 and r.aprovada
                 and r.data_inicio <= datetime.now() <= r.data_fim),
                None
            )
            autorizado = reserva_ativa is not None

        registro = RegistroAcesso(
            id=f"acesso_{datetime.now().timestamp()}",
            veiculo_id=veiculo.id if veiculo else None,
            placa=placa,
            tipo="entrada",
            data_hora=datetime.now(),
            ponto_acesso=ponto_acesso,
            metodo=metodo,
            foto_url=foto_url,
            autorizado=autorizado
        )
        self._acessos.append(registro)

        if autorizado:
            self._veiculos_dentro[placa] = datetime.now()

            # Atualizar status da vaga
            if veiculo and veiculo.vaga_atribuida:
                if veiculo.vaga_atribuida in self._vagas:
                    self._vagas[veiculo.vaga_atribuida].status = StatusVaga.OCUPADA

            # Abrir cancela automaticamente
            if self.config["cancela_automatica"] and self.tools:
                await self.tools.execute(
                    "call_mcp", mcp_name="mcp-control-id",
                    method="abrir_cancela", params={"ponto": ponto_acesso}
                )

        else:
            # Registrar infração
            await self._registrar_infracao({
                "tipo": "veiculo_nao_cadastrado",
                "placa": placa,
                "descricao": f"Tentativa de entrada de veículo não cadastrado: {placa}",
                "local": ponto_acesso
            }, context)

            # Alertar portaria
            if self.tools:
                await self.tools.execute(
                    "send_notification",
                    user_ids=["portaria"],
                    title="Veículo não autorizado",
                    message=f"Placa: {placa} tentou entrar por {ponto_acesso}",
                    channels=["push"],
                    priority="alta"
                )

        return {
            "success": True,
            "registro_id": registro.id,
            "placa": placa,
            "autorizado": autorizado,
            "veiculo_cadastrado": veiculo is not None,
            "cancela_aberta": autorizado and self.config["cancela_automatica"]
        }

    async def _registrar_saida(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Registrar saída de veículo"""
        placa = params.get("placa", "").upper()
        ponto_acesso = params.get("ponto_acesso", "saida_principal")

        veiculo = next((v for v in self._veiculos.values() if v.placa == placa), None)

        registro = RegistroAcesso(
            id=f"acesso_{datetime.now().timestamp()}",
            veiculo_id=veiculo.id if veiculo else None,
            placa=placa,
            tipo="saida",
            data_hora=datetime.now(),
            ponto_acesso=ponto_acesso,
            metodo="placa",
            autorizado=True
        )
        self._acessos.append(registro)

        # Calcular tempo de permanência
        tempo_permanencia = None
        if placa in self._veiculos_dentro:
            entrada = self._veiculos_dentro.pop(placa)
            tempo_permanencia = (datetime.now() - entrada).total_seconds() / 3600  # horas

        # Atualizar status da vaga
        if veiculo and veiculo.vaga_atribuida:
            if veiculo.vaga_atribuida in self._vagas:
                self._vagas[veiculo.vaga_atribuida].status = StatusVaga.LIVRE

        # Abrir cancela
        if self.config["cancela_automatica"] and self.tools:
            await self.tools.execute(
                "call_mcp", mcp_name="mcp-control-id",
                method="abrir_cancela", params={"ponto": ponto_acesso}
            )

        return {
            "success": True,
            "registro_id": registro.id,
            "placa": placa,
            "tempo_permanencia_horas": round(tempo_permanencia, 2) if tempo_permanencia else None
        }

    async def _consultar_placa(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Consultar placa"""
        placa = params.get("placa", "").upper()

        veiculo = next((v for v in self._veiculos.values() if v.placa == placa), None)

        if not veiculo:
            return {
                "success": True,
                "encontrado": False,
                "placa": placa
            }

        # Histórico de acessos
        acessos = [a for a in self._acessos if a.placa == placa][-10:]

        # Infrações
        infracoes = [i for i in self._infracoes if i.placa == placa]

        return {
            "success": True,
            "encontrado": True,
            "veiculo": {
                "id": veiculo.id,
                "placa": veiculo.placa,
                "modelo": f"{veiculo.marca} {veiculo.modelo}",
                "cor": veiculo.cor,
                "proprietario": veiculo.morador_nome,
                "unidade": veiculo.unidade,
                "vaga": veiculo.vaga_atribuida
            },
            "dentro_condominio": placa in self._veiculos_dentro,
            "ultimos_acessos": [
                {"tipo": a.tipo, "data": a.data_hora.isoformat(), "ponto": a.ponto_acesso}
                for a in acessos
            ],
            "infracoes": len(infracoes)
        }

    async def _registrar_infracao(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Registrar infração"""
        tipo = params.get("tipo")
        placa = params.get("placa", "").upper()
        descricao = params.get("descricao")
        local = params.get("local")
        evidencias = params.get("evidencias", [])
        aplicar_multa = params.get("aplicar_multa", False)

        veiculo = next((v for v in self._veiculos.values() if v.placa == placa), None)

        infracao = Infracao(
            id=f"inf_{datetime.now().timestamp()}",
            tipo=TipoInfracao[tipo.upper()],
            veiculo_id=veiculo.id if veiculo else None,
            placa=placa,
            descricao=descricao,
            data_hora=datetime.now(),
            local=local,
            evidencias=evidencias,
            multa_valor=self.config["valor_multa_base"] if aplicar_multa else 0,
            multa_aplicada=aplicar_multa
        )
        self._infracoes.append(infracao)

        # Notificar proprietário
        if veiculo and self.tools:
            await self.tools.execute(
                "send_notification",
                user_ids=[veiculo.morador_id],
                title="Infração de estacionamento",
                message=f"Seu veículo {placa} foi flagrado: {descricao}",
                channels=["push", "app"]
            )

        return {
            "success": True,
            "infracao_id": infracao.id,
            "tipo": tipo,
            "placa": placa,
            "multa_aplicada": aplicar_multa
        }

    async def _listar_infracoes(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Listar infrações"""
        placa = params.get("placa")
        tipo = params.get("tipo")
        pendentes = params.get("pendentes", False)

        infracoes = self._infracoes

        if placa:
            infracoes = [i for i in infracoes if i.placa == placa.upper()]
        if tipo:
            infracoes = [i for i in infracoes if i.tipo.value == tipo]
        if pendentes:
            infracoes = [i for i in infracoes if not i.resolvida]

        return {
            "success": True,
            "total": len(infracoes),
            "infracoes": [
                {
                    "id": i.id,
                    "tipo": i.tipo.value,
                    "placa": i.placa,
                    "descricao": i.descricao,
                    "data": i.data_hora.isoformat(),
                    "local": i.local,
                    "multa": i.multa_valor,
                    "resolvida": i.resolvida
                }
                for i in sorted(infracoes, key=lambda x: x.data_hora, reverse=True)
            ]
        }

    async def _reservar_vaga_visitante(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Reservar vaga para visitante"""
        solicitante_id = params.get("solicitante_id")
        placa_visitante = params.get("placa_visitante", "").upper()
        motivo = params.get("motivo")
        data_inicio = params.get("data_inicio")
        duracao_horas = params.get("duracao_horas", 4)

        # Verificar vagas de visitante disponíveis
        vagas_visitante = [
            v for v in self._vagas.values()
            if v.tipo == TipoVaga.VISITANTE and v.status == StatusVaga.LIVRE
        ]

        if not vagas_visitante:
            return {"error": "Não há vagas de visitante disponíveis"}

        vaga = vagas_visitante[0]

        inicio = datetime.fromisoformat(data_inicio) if data_inicio else datetime.now()
        fim = inicio + timedelta(hours=min(duracao_horas, self.config["tempo_max_visitante_horas"]))

        reserva = ReservaVaga(
            id=f"reserva_{datetime.now().timestamp()}",
            vaga_id=vaga.id,
            solicitante_id=solicitante_id,
            motivo=motivo,
            data_inicio=inicio,
            data_fim=fim,
            aprovada=True,
            placa_visitante=placa_visitante
        )
        self._reservas.append(reserva)

        vaga.status = StatusVaga.RESERVADA

        return {
            "success": True,
            "reserva_id": reserva.id,
            "vaga": vaga.numero,
            "placa": placa_visitante,
            "validade": f"{inicio.strftime('%H:%M')} às {fim.strftime('%H:%M')}"
        }

    async def _liberar_visitante(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Liberar entrada de visitante"""
        placa = params.get("placa", "").upper()

        reserva = next(
            (r for r in self._reservas
             if r.placa_visitante == placa
             and r.aprovada
             and r.data_inicio <= datetime.now() <= r.data_fim),
            None
        )

        if not reserva:
            return {"error": "Não há reserva ativa para esta placa"}

        # Abrir cancela
        if self.config["cancela_automatica"] and self.tools:
            await self.tools.execute(
                "call_mcp", mcp_name="mcp-control-id",
                method="abrir_cancela", params={"ponto": "entrada_principal"}
            )

        return {
            "success": True,
            "placa": placa,
            "vaga": reserva.vaga_id,
            "validade_ate": reserva.data_fim.isoformat()
        }

    async def _ocupacao_tempo_real(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Ocupação em tempo real"""
        vagas = list(self._vagas.values())

        total = len(vagas)
        ocupadas = len([v for v in vagas if v.status == StatusVaga.OCUPADA])
        livres = len([v for v in vagas if v.status == StatusVaga.LIVRE])
        reservadas = len([v for v in vagas if v.status == StatusVaga.RESERVADA])

        por_andar = {}
        for vaga in vagas:
            if vaga.andar not in por_andar:
                por_andar[vaga.andar] = {"total": 0, "ocupadas": 0}
            por_andar[vaga.andar]["total"] += 1
            if vaga.status == StatusVaga.OCUPADA:
                por_andar[vaga.andar]["ocupadas"] += 1

        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "resumo": {
                "total": total,
                "ocupadas": ocupadas,
                "livres": livres,
                "reservadas": reservadas,
                "taxa_ocupacao": round(ocupadas / total * 100, 1) if total else 0
            },
            "por_andar": por_andar,
            "veiculos_dentro": len(self._veiculos_dentro)
        }

    async def _veiculos_dentro_func(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Listar veículos dentro do condomínio"""
        veiculos = []

        for placa, entrada in self._veiculos_dentro.items():
            veiculo = next((v for v in self._veiculos.values() if v.placa == placa), None)
            tempo = (datetime.now() - entrada).total_seconds() / 3600

            veiculos.append({
                "placa": placa,
                "modelo": f"{veiculo.marca} {veiculo.modelo}" if veiculo else "Visitante",
                "unidade": veiculo.unidade if veiculo else "N/A",
                "entrada": entrada.isoformat(),
                "tempo_horas": round(tempo, 2)
            })

        return {
            "success": True,
            "total": len(veiculos),
            "veiculos": sorted(veiculos, key=lambda x: x["entrada"])
        }

    async def _historico_acessos(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Histórico de acessos"""
        placa = params.get("placa")
        tipo = params.get("tipo")
        limite = params.get("limite", 50)

        acessos = self._acessos

        if placa:
            acessos = [a for a in acessos if a.placa == placa.upper()]
        if tipo:
            acessos = [a for a in acessos if a.tipo == tipo]

        acessos = sorted(acessos, key=lambda x: x.data_hora, reverse=True)[:limite]

        return {
            "success": True,
            "total": len(acessos),
            "acessos": [
                {
                    "id": a.id,
                    "placa": a.placa,
                    "tipo": a.tipo,
                    "data": a.data_hora.isoformat(),
                    "ponto": a.ponto_acesso,
                    "metodo": a.metodo,
                    "autorizado": a.autorizado
                }
                for a in acessos
            ]
        }

    async def _dashboard(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Dashboard do estacionamento"""
        vagas = list(self._vagas.values())
        veiculos = [v for v in self._veiculos.values() if v.ativo]

        hoje = datetime.now().date()
        acessos_hoje = [a for a in self._acessos if a.data_hora.date() == hoje]
        infracoes_mes = [i for i in self._infracoes if i.data_hora.month == datetime.now().month]

        return {
            "success": True,
            "resumo": {
                "total_vagas": len(vagas),
                "vagas_ocupadas": len([v for v in vagas if v.status == StatusVaga.OCUPADA]),
                "vagas_livres": len([v for v in vagas if v.status == StatusVaga.LIVRE]),
                "total_veiculos_cadastrados": len(veiculos),
                "veiculos_dentro": len(self._veiculos_dentro),
                "acessos_hoje": len(acessos_hoje),
                "infracoes_mes": len(infracoes_mes)
            },
            "por_tipo_vaga": {
                tipo.value: len([v for v in vagas if v.tipo == tipo])
                for tipo in TipoVaga
            },
            "por_tipo_veiculo": {
                tipo.value: len([v for v in veiculos if v.tipo == tipo])
                for tipo in TipoVeiculo
            },
            "vagas_ev": {
                "total": len([v for v in vagas if v.tem_carregador_ev]),
                "ocupadas": len([v for v in vagas if v.tem_carregador_ev and v.status == StatusVaga.OCUPADA])
            }
        }

    async def _chat(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        if self.llm:
            response = await self.llm.generate(
                self.get_system_prompt(), params.get("message", "")
            )
            return {"success": True, "response": response}
        return {"error": "LLM não configurado"}


def create_parking_agent(
    condominio_id: str,
    llm_client: UnifiedLLMClient = None,
    memory: UnifiedMemorySystem = None,
    tools: ToolRegistry = None,
    evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT
) -> AgenteEstacionamento:
    """Factory function para criar agente de estacionamento"""
    return AgenteEstacionamento(
        condominio_id=condominio_id,
        llm_client=llm_client or UnifiedLLMClient(),
        memory=memory,
        tools=tools,
        evolution_level=evolution_level
    )
