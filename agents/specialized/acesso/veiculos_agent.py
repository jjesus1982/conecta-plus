"""
Conecta Plus - Acesso Veículos Agent
Agente especializado em controle de acesso de veículos
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

from ..base_specialized import (
    BaseSpecializedAgent, SpecializedAgentConfig, DomainKnowledge,
    SpecializedContext, AgentResponse, SpecializedDomain, AgentCapability
)

logger = logging.getLogger(__name__)


@dataclass
class Veiculo:
    """Veículo cadastrado"""
    placa: str
    modelo: str
    cor: str
    tipo: str  # carro, moto, caminhao
    unidade: str
    proprietario: str
    tag_id: Optional[str] = None
    vaga: Optional[str] = None
    autorizado: bool = True


class AcessoVeiculosAgent(BaseSpecializedAgent):
    """
    Agente especializado em controle de acesso de veículos.

    Responsabilidades:
    - Liberação de portões para veículos
    - Gestão de tags de acesso
    - Controle de vagas
    - Registro de entradas/saídas
    """

    def __init__(self, config: SpecializedAgentConfig = None):
        if config is None:
            config = SpecializedAgentConfig(
                domain=SpecializedDomain.ACESSO,
                name="Acesso Veículos",
                description="Controle de acesso de veículos",
                capabilities=[
                    AgentCapability.READ,
                    AgentCapability.WRITE,
                    AgentCapability.EXECUTE,
                    AgentCapability.NOTIFY
                ],
                allowed_tools=["access_control", "camera", "gate"],
                auto_escalate=True
            )
        super().__init__(config)

        # Base de veículos (simulada)
        self._veiculos: Dict[str, Veiculo] = {}
        self._historico: List[Dict] = []

    @property
    def knowledge(self) -> DomainKnowledge:
        """Conhecimento de domínio"""
        return DomainKnowledge(
            domain=SpecializedDomain.ACESSO,
            expertise_level=4,
            supported_intents=[
                "liberar_portao",
                "consultar_veiculo",
                "cadastrar_veiculo",
                "bloquear_veiculo",
                "consultar_vagas",
                "historico_acesso",
                "solicitar_tag"
            ],
            procedures=[
                {
                    "intent": "liberar_portao",
                    "steps": [
                        {"type": "action", "action": "verificar_placa"},
                        {"type": "action", "action": "liberar_cancela"}
                    ],
                    "completion_message": "Portão liberado!"
                }
            ],
            faq=[
                {
                    "keywords": ["tag", "controle", "como funciona"],
                    "answer": "A tag de acesso é um dispositivo que permite a abertura automática do portão. Para solicitar, entre em contato com a administração."
                },
                {
                    "keywords": ["vaga", "estacionamento", "onde"],
                    "answer": "As vagas são definidas por unidade. Você pode consultar sua vaga através do aplicativo ou na portaria."
                }
            ],
            response_templates={
                "veiculo_autorizado": "Veículo {placa} autorizado. Portão liberado.",
                "veiculo_nao_autorizado": "Veículo {placa} não está autorizado. Por favor, aguarde verificação.",
                "vaga_ocupada": "Sua vaga ({vaga}) está atualmente ocupada.",
                "vaga_livre": "Sua vaga ({vaga}) está disponível."
            }
        )

    async def handle_intent(
        self,
        intent: str,
        context: SpecializedContext,
        entities: Dict[str, Any]
    ) -> AgentResponse:
        """Processa intents de acesso de veículos"""

        if intent == "liberar_portao":
            return await self._liberar_portao(context, entities)

        elif intent == "consultar_veiculo":
            return await self._consultar_veiculo(context, entities)

        elif intent == "cadastrar_veiculo":
            return await self._cadastrar_veiculo(context, entities)

        elif intent == "bloquear_veiculo":
            return await self._bloquear_veiculo(context, entities)

        elif intent == "consultar_vagas":
            return await self._consultar_vagas(context, entities)

        elif intent == "historico_acesso":
            return await self._historico_acesso(context, entities)

        elif intent == "solicitar_tag":
            return await self._solicitar_tag(context, entities)

        else:
            # Tentar FAQ
            faq_response = self.get_faq_response(context.current_intent or "")
            if faq_response:
                return AgentResponse(message=faq_response)

            return AgentResponse(
                message="Não entendi seu pedido sobre veículos. Posso ajudar com liberação de portão, consulta de veículos ou vagas.",
                suggestions=["Liberar portão", "Consultar meu veículo", "Ver vagas disponíveis"]
            )

    async def execute_action(
        self,
        action: str,
        context: SpecializedContext,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Executa ações de acesso de veículos"""

        if action == "verificar_placa":
            placa = params.get("placa") or context.extracted_entities.get("placa")
            veiculo = self._veiculos.get(placa)
            return {
                "success": veiculo is not None and veiculo.autorizado,
                "veiculo": veiculo.__dict__ if veiculo else None
            }

        elif action == "liberar_cancela":
            # Em produção, chamaria tool de gate
            return {
                "success": True,
                "gate_id": "gate_001",
                "status": "open"
            }

        elif action == "registrar_acesso":
            placa = params.get("placa")
            tipo = params.get("tipo", "entrada")
            self._historico.append({
                "placa": placa,
                "tipo": tipo,
                "timestamp": datetime.now().isoformat()
            })
            return {"success": True}

        return {"success": False, "error": f"Ação desconhecida: {action}"}

    async def _liberar_portao(
        self,
        context: SpecializedContext,
        entities: Dict
    ) -> AgentResponse:
        """Libera portão para veículo"""
        placa = entities.get("placa")

        if not placa:
            return AgentResponse(
                message="Por favor, informe a placa do veículo para liberação.",
                requires_input=True,
                input_type="text"
            )

        # Verificar veículo
        veiculo = self._veiculos.get(placa.upper())

        if not veiculo:
            return AgentResponse(
                message=f"Veículo com placa {placa} não encontrado no cadastro. Deseja solicitar liberação de visitante?",
                requires_input=True,
                input_type="confirmation",
                choices=["Sim, é visitante", "Não, é morador"]
            )

        if not veiculo.autorizado:
            return AgentResponse(
                message=f"Veículo {placa} está com acesso bloqueado. Entre em contato com a administração.",
                should_escalate=True,
                escalation_reason="Veículo bloqueado"
            )

        # Liberar
        await self.execute_action("liberar_cancela", context, {"placa": placa})
        await self.execute_action("registrar_acesso", context, {"placa": placa, "tipo": "entrada"})

        context.record_action("liberar_portao", {"placa": placa})

        return AgentResponse(
            message=f"✅ Portão liberado para o veículo {placa} ({veiculo.modelo} {veiculo.cor}).",
            actions_executed=[{"action": "liberar_portao", "placa": placa}]
        )

    async def _consultar_veiculo(
        self,
        context: SpecializedContext,
        entities: Dict
    ) -> AgentResponse:
        """Consulta dados do veículo"""
        placa = entities.get("placa")

        if not placa:
            return AgentResponse(
                message="Informe a placa do veículo que deseja consultar.",
                requires_input=True
            )

        veiculo = self._veiculos.get(placa.upper())

        if not veiculo:
            return AgentResponse(message=f"Veículo {placa} não encontrado no cadastro.")

        status = "Autorizado ✅" if veiculo.autorizado else "Bloqueado ❌"

        return AgentResponse(
            message=f"**Veículo {placa}**\n"
                   f"Modelo: {veiculo.modelo}\n"
                   f"Cor: {veiculo.cor}\n"
                   f"Unidade: {veiculo.unidade}\n"
                   f"Vaga: {veiculo.vaga or 'Não definida'}\n"
                   f"Status: {status}"
        )

    async def _cadastrar_veiculo(
        self,
        context: SpecializedContext,
        entities: Dict
    ) -> AgentResponse:
        """Cadastra novo veículo"""
        return AgentResponse(
            message="Para cadastrar um novo veículo, por favor forneça:\n"
                   "• Placa\n• Modelo\n• Cor\n• Sua unidade",
            requires_input=True,
            suggestions=["Cadastrar carro", "Cadastrar moto"]
        )

    async def _bloquear_veiculo(
        self,
        context: SpecializedContext,
        entities: Dict
    ) -> AgentResponse:
        """Bloqueia acesso de veículo"""
        if not context.has_permission("admin"):
            return AgentResponse(
                message="Você não tem permissão para bloquear veículos. Deseja escalonar para a administração?",
                should_escalate=True
            )

        placa = entities.get("placa")
        if not placa:
            return AgentResponse(
                message="Informe a placa do veículo a ser bloqueado.",
                requires_input=True
            )

        return AgentResponse(
            message=f"Veículo {placa} bloqueado com sucesso.",
            actions_executed=[{"action": "bloquear_veiculo", "placa": placa}]
        )

    async def _consultar_vagas(
        self,
        context: SpecializedContext,
        entities: Dict
    ) -> AgentResponse:
        """Consulta vagas de estacionamento"""
        unidade = entities.get("unidade")

        if unidade:
            # Buscar vaga específica
            for v in self._veiculos.values():
                if v.unidade == unidade:
                    return AgentResponse(
                        message=f"Unidade {unidade}: Vaga {v.vaga or 'não atribuída'}"
                    )

        # Resumo geral
        return AgentResponse(
            message="**Situação do Estacionamento**\n"
                   "Vagas totais: 100\n"
                   "Ocupadas: 75\n"
                   "Livres: 25\n"
                   "Visitantes: 5 vagas disponíveis",
            suggestions=["Consultar minha vaga", "Ver vagas de visitante"]
        )

    async def _historico_acesso(
        self,
        context: SpecializedContext,
        entities: Dict
    ) -> AgentResponse:
        """Retorna histórico de acessos"""
        placa = entities.get("placa")

        historico = self._historico
        if placa:
            historico = [h for h in historico if h.get("placa") == placa.upper()]

        if not historico:
            return AgentResponse(message="Nenhum registro de acesso encontrado.")

        ultimos = historico[-5:]
        registros = "\n".join([
            f"• {h['placa']} - {h['tipo']} - {h['timestamp']}"
            for h in ultimos
        ])

        return AgentResponse(
            message=f"**Últimos acessos:**\n{registros}"
        )

    async def _solicitar_tag(
        self,
        context: SpecializedContext,
        entities: Dict
    ) -> AgentResponse:
        """Solicita tag de acesso"""
        return AgentResponse(
            message="Para solicitar uma tag de acesso:\n\n"
                   "1. Preencha o formulário na administração\n"
                   "2. Apresente documento do veículo\n"
                   "3. Taxa: R$ 50,00\n"
                   "4. Prazo: 5 dias úteis\n\n"
                   "Deseja agendar atendimento?",
            requires_input=True,
            input_type="confirmation"
        )
