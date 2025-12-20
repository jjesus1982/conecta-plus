"""
Conecta Plus - Agente Pet (Nível 7)
Gestor de animais de estimação do condomínio

Capacidades:
1. REATIVO: Cadastrar pets, registrar ocorrências
2. PROATIVO: Alertar vacinas, sugerir serviços
3. PREDITIVO: Prever conflitos, identificar padrões
4. AUTÔNOMO: Gerar advertências, agendar serviços
5. EVOLUTIVO: Aprender comportamentos, melhorar regras
6. COLABORATIVO: Integrar Portaria, Ocorrências, Social
7. TRANSCENDENTE: Gestão completa de pets
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


class TipoPet(Enum):
    CACHORRO = "cachorro"
    GATO = "gato"
    PASSARO = "passaro"
    PEIXE = "peixe"
    ROEDOR = "roedor"
    REPTIL = "reptil"
    OUTRO = "outro"


class PortePet(Enum):
    PEQUENO = "pequeno"
    MEDIO = "medio"
    GRANDE = "grande"


class TipoOcorrenciaPet(Enum):
    BARULHO = "barulho"
    SUJEIRA = "sujeira"
    MORDIDA = "mordida"
    FUGA = "fuga"
    MAUS_TRATOS = "maus_tratos"
    SEM_COLEIRA = "sem_coleira"
    AREA_PROIBIDA = "area_proibida"
    BRIGA = "briga"


class StatusOcorrenciaPet(Enum):
    ABERTA = "aberta"
    EM_ANALISE = "em_analise"
    ADVERTIDO = "advertido"
    RESOLVIDA = "resolvida"
    ARQUIVADA = "arquivada"


class TipoVacina(Enum):
    ANTIRRABICA = "antirrabica"
    V8 = "v8"
    V10 = "v10"
    GRIPE = "gripe"
    GIARDIA = "giardia"
    VERMIFUGO = "vermifugo"
    ANTIPARASITARIO = "antiparasitario"


class TipoServicoPet(Enum):
    BANHO = "banho"
    TOSA = "tosa"
    VETERINARIO = "veterinario"
    ADESTRAMENTO = "adestramento"
    PASSEIO = "passeio"
    HOSPEDAGEM = "hospedagem"
    PET_SITTER = "pet_sitter"


@dataclass
class Pet:
    id: str
    nome: str
    tipo: TipoPet
    raca: str
    porte: PortePet
    cor: str
    idade_anos: float
    castrado: bool
    morador_id: str
    morador_nome: str
    unidade: str
    foto_url: Optional[str] = None
    chip_id: Optional[str] = None
    vacinas: List[Dict] = field(default_factory=list)
    ocorrencias: List[str] = field(default_factory=list)
    observacoes: str = ""
    data_cadastro: datetime = field(default_factory=datetime.now)
    ativo: bool = True


@dataclass
class OcorrenciaPet:
    id: str
    tipo: TipoOcorrenciaPet
    pet_id: str
    pet_nome: str
    unidade: str
    descricao: str
    data_ocorrencia: datetime
    reportado_por: str
    status: StatusOcorrenciaPet
    evidencias: List[str] = field(default_factory=list)
    acao_tomada: Optional[str] = None
    advertencia_gerada: bool = False


@dataclass
class AgendamentoServico:
    id: str
    tipo: TipoServicoPet
    pet_id: str
    pet_nome: str
    morador_id: str
    data_agendamento: datetime
    prestador: Optional[str] = None
    valor: float = 0
    status: str = "agendado"
    observacoes: str = ""


@dataclass
class AlertaVacina:
    id: str
    pet_id: str
    pet_nome: str
    tipo_vacina: TipoVacina
    data_vencimento: datetime
    morador_id: str
    notificado: bool = False


class AgentePet(BaseAgent):
    """Agente Pet - Gestor de Animais Nível 7"""

    def __init__(
        self,
        condominio_id: str,
        llm_client: UnifiedLLMClient = None,
        memory: UnifiedMemorySystem = None,
        tools: ToolRegistry = None,
        evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT,
    ):
        super().__init__(
            agent_id=f"pet_{condominio_id}",
            agent_type="pet",
            condominio_id=condominio_id,
            evolution_level=evolution_level,
            llm_client=llm_client,
            memory_store=memory,
        )
        self.tools = tools

        self._pets: Dict[str, Pet] = {}
        self._ocorrencias: List[OcorrenciaPet] = []
        self._agendamentos: List[AgendamentoServico] = []
        self._alertas_vacina: List[AlertaVacina] = []
        self._prestadores: Dict[str, Dict] = {}

        self.config = {
            "pets_permitidos": ["cachorro", "gato", "passaro", "peixe"],
            "limite_pets_por_unidade": 2,
            "horario_passeio_inicio": "06:00",
            "horario_passeio_fim": "22:00",
            "areas_permitidas": ["areas_comuns", "jardim"],
            "areas_proibidas": ["piscina", "salao_festas", "academia"],
            "dias_alerta_vacina": 30,
            "advertencias_para_multa": 3,
        }

        self._inicializar_regras()

    def _inicializar_regras(self):
        """Regras do regulamento para pets"""
        self._regras = [
            "Todos os pets devem estar cadastrados junto à administração",
            "É obrigatório o uso de coleira e guia nas áreas comuns",
            "O tutor deve recolher dejetos deixados pelo animal",
            "Animais só podem circular em elevador de serviço",
            "É proibida a entrada de pets em: piscina, academia, salão de festas",
            "Horário de passeio nas áreas comuns: 6h às 22h",
            "Animais devem estar com vacinas em dia",
            "Cães de grande porte devem usar focinheira nas áreas comuns",
            "Barulho excessivo (latidos) pode gerar advertência",
            "Em caso de mordida, o tutor é responsável civil e criminalmente",
        ]

    def _register_capabilities(self) -> None:
        self._capabilities["cadastro_pets"] = AgentCapability(
            name="cadastro_pets", description="Cadastrar e gerenciar pets",
            level=EvolutionLevel.REACTIVE
        )
        self._capabilities["controle_vacinas"] = AgentCapability(
            name="controle_vacinas", description="Controlar vacinas e alertas",
            level=EvolutionLevel.PROACTIVE
        )
        self._capabilities["gestao_ocorrencias"] = AgentCapability(
            name="gestao_ocorrencias", description="Gerenciar ocorrências com pets",
            level=EvolutionLevel.AUTONOMOUS
        )
        self._capabilities["servicos_pet"] = AgentCapability(
            name="servicos_pet", description="Agendar serviços para pets",
            level=EvolutionLevel.PROACTIVE
        )
        self._capabilities["gestao_pet_total"] = AgentCapability(
            name="gestao_pet_total", description="Gestão completa de pets",
            level=EvolutionLevel.TRANSCENDENT
        )

    def get_system_prompt(self) -> str:
        return f"""Você é o Agente Pet do Conecta Plus.
ID: {self.agent_id} | Condomínio: {self.condominio_id} | Nível: {self.evolution_level.name}

RESPONSABILIDADES:
- Cadastro de animais de estimação
- Controle de vacinas e vermífugos
- Registro de ocorrências
- Agendamento de serviços pet
- Aplicação do regulamento
- Mediação de conflitos

REGRAS DO CONDOMÍNIO:
{chr(10).join(f'- {r}' for r in self._regras)}

COMPORTAMENTO:
- Seja amigável com tutores
- Priorize bem-estar animal
- Aplique regras com justiça
- Previna conflitos
"""

    async def process(self, input_data: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        action = input_data.get("action", "")
        params = input_data.get("params", {})

        if action == "cadastrar_pet":
            return await self._cadastrar_pet(params, context)
        elif action == "atualizar_pet":
            return await self._atualizar_pet(params, context)
        elif action == "listar_pets":
            return await self._listar_pets(params, context)
        elif action == "registrar_vacina":
            return await self._registrar_vacina(params, context)
        elif action == "verificar_vacinas":
            return await self._verificar_vacinas(params, context)
        elif action == "registrar_ocorrencia":
            return await self._registrar_ocorrencia(params, context)
        elif action == "listar_ocorrencias":
            return await self._listar_ocorrencias(params, context)
        elif action == "resolver_ocorrencia":
            return await self._resolver_ocorrencia(params, context)
        elif action == "agendar_servico":
            return await self._agendar_servico(params, context)
        elif action == "listar_servicos":
            return await self._listar_servicos(params, context)
        elif action == "cadastrar_prestador":
            return await self._cadastrar_prestador(params, context)
        elif action == "listar_prestadores":
            return await self._listar_prestadores(params, context)
        elif action == "consultar_regras":
            return await self._consultar_regras(params, context)
        elif action == "historico_pet":
            return await self._historico_pet(params, context)
        elif action == "dashboard":
            return await self._dashboard(params, context)
        elif action == "chat":
            return await self._chat(params, context)
        else:
            return {"error": f"Ação '{action}' não reconhecida"}

    async def _cadastrar_pet(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Cadastrar pet"""
        nome = params.get("nome")
        tipo = params.get("tipo", "cachorro")
        raca = params.get("raca", "SRD")
        porte = params.get("porte", "medio")
        cor = params.get("cor", "")
        idade = params.get("idade_anos", 0)
        castrado = params.get("castrado", False)
        morador_id = params.get("morador_id")
        morador_nome = params.get("morador_nome")
        unidade = params.get("unidade")
        foto_url = params.get("foto_url")
        chip_id = params.get("chip_id")

        # Verificar se tipo é permitido
        if tipo not in self.config["pets_permitidos"]:
            return {"error": f"Tipo '{tipo}' não permitido no condomínio"}

        # Verificar limite por unidade
        pets_unidade = [p for p in self._pets.values() if p.unidade == unidade and p.ativo]
        if len(pets_unidade) >= self.config["limite_pets_por_unidade"]:
            return {"error": f"Limite de {self.config['limite_pets_por_unidade']} pets por unidade atingido"}

        pet = Pet(
            id=f"pet_{datetime.now().timestamp()}",
            nome=nome,
            tipo=TipoPet[tipo.upper()],
            raca=raca,
            porte=PortePet[porte.upper()],
            cor=cor,
            idade_anos=idade,
            castrado=castrado,
            morador_id=morador_id,
            morador_nome=morador_nome,
            unidade=unidade,
            foto_url=foto_url,
            chip_id=chip_id
        )
        self._pets[pet.id] = pet

        # Alertar sobre vacinas
        await self._criar_alertas_vacina(pet)

        return {
            "success": True,
            "pet_id": pet.id,
            "nome": nome,
            "tipo": tipo,
            "unidade": unidade,
            "mensagem": "Pet cadastrado com sucesso! Lembre-se de manter as vacinas em dia."
        }

    async def _criar_alertas_vacina(self, pet: Pet):
        """Criar alertas de vacina para novo pet"""
        vacinas_obrigatorias = [TipoVacina.ANTIRRABICA]

        if pet.tipo == TipoPet.CACHORRO:
            vacinas_obrigatorias.extend([TipoVacina.V10, TipoVacina.VERMIFUGO])
        elif pet.tipo == TipoPet.GATO:
            vacinas_obrigatorias.extend([TipoVacina.V8, TipoVacina.VERMIFUGO])

        for vacina in vacinas_obrigatorias:
            alerta = AlertaVacina(
                id=f"alerta_{pet.id}_{vacina.value}",
                pet_id=pet.id,
                pet_nome=pet.nome,
                tipo_vacina=vacina,
                data_vencimento=datetime.now(),  # Imediato para novo cadastro
                morador_id=pet.morador_id
            )
            self._alertas_vacina.append(alerta)

    async def _atualizar_pet(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Atualizar dados do pet"""
        pet_id = params.get("pet_id")

        if pet_id not in self._pets:
            return {"error": "Pet não encontrado"}

        pet = self._pets[pet_id]

        if "nome" in params:
            pet.nome = params["nome"]
        if "castrado" in params:
            pet.castrado = params["castrado"]
        if "foto_url" in params:
            pet.foto_url = params["foto_url"]
        if "observacoes" in params:
            pet.observacoes = params["observacoes"]
        if "ativo" in params:
            pet.ativo = params["ativo"]

        return {
            "success": True,
            "pet_id": pet_id,
            "atualizado": True
        }

    async def _listar_pets(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Listar pets"""
        unidade = params.get("unidade")
        tipo = params.get("tipo")
        ativos = params.get("ativos", True)

        pets = list(self._pets.values())

        if ativos:
            pets = [p for p in pets if p.ativo]
        if unidade:
            pets = [p for p in pets if p.unidade == unidade]
        if tipo:
            pets = [p for p in pets if p.tipo.value == tipo]

        return {
            "success": True,
            "total": len(pets),
            "pets": [
                {
                    "id": p.id,
                    "nome": p.nome,
                    "tipo": p.tipo.value,
                    "raca": p.raca,
                    "porte": p.porte.value,
                    "unidade": p.unidade,
                    "tutor": p.morador_nome,
                    "castrado": p.castrado,
                    "vacinas_dia": len([v for v in p.vacinas if datetime.fromisoformat(v.get("data_vencimento", "2000-01-01")) > datetime.now()]),
                    "ocorrencias": len(p.ocorrencias)
                }
                for p in pets
            ]
        }

    async def _registrar_vacina(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Registrar vacina aplicada"""
        pet_id = params.get("pet_id")
        tipo_vacina = params.get("tipo_vacina")
        data_aplicacao = params.get("data_aplicacao")
        veterinario = params.get("veterinario")
        proxima_dose = params.get("proxima_dose")
        comprovante = params.get("comprovante_url")

        if pet_id not in self._pets:
            return {"error": "Pet não encontrado"}

        pet = self._pets[pet_id]

        vacina = {
            "tipo": tipo_vacina,
            "data_aplicacao": data_aplicacao or datetime.now().isoformat(),
            "veterinario": veterinario,
            "data_vencimento": proxima_dose,
            "comprovante": comprovante
        }
        pet.vacinas.append(vacina)

        # Atualizar alerta
        for alerta in self._alertas_vacina:
            if alerta.pet_id == pet_id and alerta.tipo_vacina.value == tipo_vacina:
                if proxima_dose:
                    alerta.data_vencimento = datetime.fromisoformat(proxima_dose)
                    alerta.notificado = False
                else:
                    self._alertas_vacina.remove(alerta)
                break

        return {
            "success": True,
            "pet_id": pet_id,
            "vacina": tipo_vacina,
            "proxima_dose": proxima_dose
        }

    async def _verificar_vacinas(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Verificar vacinas vencidas ou próximas do vencimento"""
        dias = params.get("dias", self.config["dias_alerta_vacina"])

        limite = datetime.now() + timedelta(days=dias)
        alertas = []

        for alerta in self._alertas_vacina:
            if alerta.data_vencimento <= limite:
                dias_restantes = (alerta.data_vencimento - datetime.now()).days
                alertas.append({
                    "pet_id": alerta.pet_id,
                    "pet_nome": alerta.pet_nome,
                    "vacina": alerta.tipo_vacina.value,
                    "vencimento": alerta.data_vencimento.isoformat(),
                    "dias_restantes": dias_restantes,
                    "status": "vencida" if dias_restantes < 0 else "proxima"
                })

                # Notificar se ainda não notificado
                if not alerta.notificado and self.tools:
                    await self.tools.execute(
                        "send_notification",
                        user_ids=[alerta.morador_id],
                        title=f"Vacina do {alerta.pet_nome}",
                        message=f"A vacina {alerta.tipo_vacina.value} está {'vencida' if dias_restantes < 0 else f'vencendo em {dias_restantes} dias'}",
                        channels=["push", "app"]
                    )
                    alerta.notificado = True

        return {
            "success": True,
            "total_alertas": len(alertas),
            "alertas": sorted(alertas, key=lambda x: x["dias_restantes"])
        }

    async def _registrar_ocorrencia(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Registrar ocorrência com pet"""
        tipo = params.get("tipo")
        pet_id = params.get("pet_id")
        descricao = params.get("descricao")
        reportado_por = params.get("reportado_por")
        evidencias = params.get("evidencias", [])

        if pet_id not in self._pets:
            return {"error": "Pet não encontrado"}

        pet = self._pets[pet_id]

        ocorrencia = OcorrenciaPet(
            id=f"oc_pet_{datetime.now().timestamp()}",
            tipo=TipoOcorrenciaPet[tipo.upper()],
            pet_id=pet_id,
            pet_nome=pet.nome,
            unidade=pet.unidade,
            descricao=descricao,
            data_ocorrencia=datetime.now(),
            reportado_por=reportado_por,
            status=StatusOcorrenciaPet.ABERTA,
            evidencias=evidencias
        )
        self._ocorrencias.append(ocorrencia)
        pet.ocorrencias.append(ocorrencia.id)

        # Verificar se precisa gerar advertência automática
        ocorrencias_pet = [o for o in self._ocorrencias if o.pet_id == pet_id]
        if len(ocorrencias_pet) >= self.config["advertencias_para_multa"]:
            # Colaborar com agente jurídico
            if self.has_capability("agent_collaboration"):
                await self.send_message(
                    f"juridico_{self.condominio_id}",
                    {
                        "action": "gerar_advertencia",
                        "params": {
                            "nome_morador": pet.morador_nome,
                            "unidade": pet.unidade,
                            "descricao_infracao": f"Múltiplas ocorrências com pet ({pet.nome}): {descricao}",
                            "artigo_regulamento": "Regulamento de Pets"
                        }
                    }
                )
            ocorrencia.advertencia_gerada = True

        # Notificar tutor
        if self.tools:
            await self.tools.execute(
                "send_notification",
                user_ids=[pet.morador_id],
                title=f"Ocorrência registrada - {pet.nome}",
                message=f"Tipo: {tipo}\n{descricao[:100]}",
                channels=["push", "app"]
            )

        return {
            "success": True,
            "ocorrencia_id": ocorrencia.id,
            "pet": pet.nome,
            "tipo": tipo,
            "advertencia_gerada": ocorrencia.advertencia_gerada
        }

    async def _listar_ocorrencias(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Listar ocorrências"""
        pet_id = params.get("pet_id")
        status = params.get("status")
        tipo = params.get("tipo")

        ocorrencias = self._ocorrencias

        if pet_id:
            ocorrencias = [o for o in ocorrencias if o.pet_id == pet_id]
        if status:
            ocorrencias = [o for o in ocorrencias if o.status.value == status]
        if tipo:
            ocorrencias = [o for o in ocorrencias if o.tipo.value == tipo]

        ocorrencias = sorted(ocorrencias, key=lambda x: x.data_ocorrencia, reverse=True)

        return {
            "success": True,
            "total": len(ocorrencias),
            "ocorrencias": [
                {
                    "id": o.id,
                    "tipo": o.tipo.value,
                    "pet": o.pet_nome,
                    "unidade": o.unidade,
                    "data": o.data_ocorrencia.isoformat(),
                    "status": o.status.value,
                    "advertencia": o.advertencia_gerada
                }
                for o in ocorrencias
            ]
        }

    async def _resolver_ocorrencia(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Resolver ocorrência"""
        ocorrencia_id = params.get("ocorrencia_id")
        acao_tomada = params.get("acao_tomada")
        status = params.get("status", "resolvida")

        ocorrencia = next((o for o in self._ocorrencias if o.id == ocorrencia_id), None)
        if not ocorrencia:
            return {"error": "Ocorrência não encontrada"}

        ocorrencia.status = StatusOcorrenciaPet[status.upper()]
        ocorrencia.acao_tomada = acao_tomada

        return {
            "success": True,
            "ocorrencia_id": ocorrencia_id,
            "status": status,
            "acao": acao_tomada
        }

    async def _agendar_servico(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Agendar serviço para pet"""
        tipo = params.get("tipo")
        pet_id = params.get("pet_id")
        morador_id = params.get("morador_id")
        data = params.get("data")
        prestador_id = params.get("prestador_id")
        observacoes = params.get("observacoes", "")

        if pet_id not in self._pets:
            return {"error": "Pet não encontrado"}

        pet = self._pets[pet_id]

        prestador = self._prestadores.get(prestador_id)
        valor = prestador.get("precos", {}).get(tipo, 0) if prestador else 0

        agendamento = AgendamentoServico(
            id=f"serv_{datetime.now().timestamp()}",
            tipo=TipoServicoPet[tipo.upper()],
            pet_id=pet_id,
            pet_nome=pet.nome,
            morador_id=morador_id,
            data_agendamento=datetime.fromisoformat(data) if data else datetime.now() + timedelta(days=1),
            prestador=prestador.get("nome") if prestador else None,
            valor=valor,
            observacoes=observacoes
        )
        self._agendamentos.append(agendamento)

        return {
            "success": True,
            "agendamento_id": agendamento.id,
            "servico": tipo,
            "pet": pet.nome,
            "data": agendamento.data_agendamento.isoformat(),
            "valor": valor
        }

    async def _listar_servicos(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Listar serviços agendados"""
        pet_id = params.get("pet_id")
        morador_id = params.get("morador_id")
        futuros = params.get("futuros", True)

        servicos = self._agendamentos

        if pet_id:
            servicos = [s for s in servicos if s.pet_id == pet_id]
        if morador_id:
            servicos = [s for s in servicos if s.morador_id == morador_id]
        if futuros:
            servicos = [s for s in servicos if s.data_agendamento > datetime.now()]

        return {
            "success": True,
            "total": len(servicos),
            "servicos": [
                {
                    "id": s.id,
                    "tipo": s.tipo.value,
                    "pet": s.pet_nome,
                    "data": s.data_agendamento.isoformat(),
                    "prestador": s.prestador,
                    "valor": s.valor,
                    "status": s.status
                }
                for s in sorted(servicos, key=lambda x: x.data_agendamento)
            ]
        }

    async def _cadastrar_prestador(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Cadastrar prestador de serviços pet"""
        nome = params.get("nome")
        servicos = params.get("servicos", [])
        telefone = params.get("telefone")
        precos = params.get("precos", {})
        avaliacao = params.get("avaliacao", 0)

        prestador_id = f"prest_{datetime.now().timestamp()}"

        self._prestadores[prestador_id] = {
            "id": prestador_id,
            "nome": nome,
            "servicos": servicos,
            "telefone": telefone,
            "precos": precos,
            "avaliacao": avaliacao,
            "ativo": True
        }

        return {
            "success": True,
            "prestador_id": prestador_id,
            "nome": nome,
            "servicos": servicos
        }

    async def _listar_prestadores(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Listar prestadores"""
        servico = params.get("servico")

        prestadores = list(self._prestadores.values())

        if servico:
            prestadores = [p for p in prestadores if servico in p.get("servicos", [])]

        prestadores = [p for p in prestadores if p.get("ativo", True)]

        return {
            "success": True,
            "total": len(prestadores),
            "prestadores": [
                {
                    "id": p["id"],
                    "nome": p["nome"],
                    "servicos": p["servicos"],
                    "telefone": p["telefone"],
                    "avaliacao": p["avaliacao"]
                }
                for p in sorted(prestadores, key=lambda x: x.get("avaliacao", 0), reverse=True)
            ]
        }

    async def _consultar_regras(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Consultar regras para pets"""
        return {
            "success": True,
            "config": {
                "pets_permitidos": self.config["pets_permitidos"],
                "limite_por_unidade": self.config["limite_pets_por_unidade"],
                "horario_passeio": f"{self.config['horario_passeio_inicio']} às {self.config['horario_passeio_fim']}",
                "areas_proibidas": self.config["areas_proibidas"]
            },
            "regras": self._regras
        }

    async def _historico_pet(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Histórico completo do pet"""
        pet_id = params.get("pet_id")

        if pet_id not in self._pets:
            return {"error": "Pet não encontrado"}

        pet = self._pets[pet_id]

        ocorrencias = [o for o in self._ocorrencias if o.pet_id == pet_id]
        servicos = [s for s in self._agendamentos if s.pet_id == pet_id]

        return {
            "success": True,
            "pet": {
                "id": pet.id,
                "nome": pet.nome,
                "tipo": pet.tipo.value,
                "raca": pet.raca,
                "idade": pet.idade_anos,
                "unidade": pet.unidade,
                "tutor": pet.morador_nome,
                "cadastro": pet.data_cadastro.isoformat()
            },
            "vacinas": pet.vacinas,
            "ocorrencias": [
                {"id": o.id, "tipo": o.tipo.value, "data": o.data_ocorrencia.isoformat(), "status": o.status.value}
                for o in ocorrencias
            ],
            "servicos": [
                {"id": s.id, "tipo": s.tipo.value, "data": s.data_agendamento.isoformat()}
                for s in servicos
            ]
        }

    async def _dashboard(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        """Dashboard de pets"""
        pets_ativos = [p for p in self._pets.values() if p.ativo]

        # Vacinas vencidas
        vacinas_vencidas = [a for a in self._alertas_vacina if a.data_vencimento < datetime.now()]

        # Ocorrências abertas
        ocorrencias_abertas = [o for o in self._ocorrencias if o.status == StatusOcorrenciaPet.ABERTA]

        # Serviços próximos
        servicos_proximos = [
            s for s in self._agendamentos
            if s.data_agendamento > datetime.now()
            and s.data_agendamento < datetime.now() + timedelta(days=7)
        ]

        return {
            "success": True,
            "resumo": {
                "total_pets": len(pets_ativos),
                "cachorros": len([p for p in pets_ativos if p.tipo == TipoPet.CACHORRO]),
                "gatos": len([p for p in pets_ativos if p.tipo == TipoPet.GATO]),
                "outros": len([p for p in pets_ativos if p.tipo not in [TipoPet.CACHORRO, TipoPet.GATO]]),
                "vacinas_pendentes": len(vacinas_vencidas),
                "ocorrencias_abertas": len(ocorrencias_abertas),
                "servicos_semana": len(servicos_proximos)
            },
            "por_porte": {
                porte.value: len([p for p in pets_ativos if p.porte == porte])
                for porte in PortePet
            },
            "alertas": {
                "vacinas_vencidas": [
                    {"pet": a.pet_nome, "vacina": a.tipo_vacina.value}
                    for a in vacinas_vencidas[:5]
                ],
                "ocorrencias_recentes": [
                    {"pet": o.pet_nome, "tipo": o.tipo.value, "data": o.data_ocorrencia.isoformat()}
                    for o in sorted(ocorrencias_abertas, key=lambda x: x.data_ocorrencia, reverse=True)[:5]
                ]
            }
        }

    async def _chat(self, params: Dict, context: AgentContext) -> Dict[str, Any]:
        if self.llm:
            response = await self.llm.generate(
                self.get_system_prompt(), params.get("message", "")
            )
            return {"success": True, "response": response}
        return {"error": "LLM não configurado"}


def create_pet_agent(
    condominio_id: str,
    llm_client: UnifiedLLMClient = None,
    memory: UnifiedMemorySystem = None,
    tools: ToolRegistry = None,
    evolution_level: EvolutionLevel = EvolutionLevel.TRANSCENDENT
) -> AgentePet:
    """Factory function para criar agente pet"""
    return AgentePet(
        condominio_id=condominio_id,
        llm_client=llm_client or UnifiedLLMClient(),
        memory=memory,
        tools=tools,
        evolution_level=evolution_level
    )
