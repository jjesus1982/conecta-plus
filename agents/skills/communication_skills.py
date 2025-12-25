"""
Conecta Plus - Communication Skills
Habilidades de comunicação para agentes

Skills:
- NotificationSkill: Envio de notificações multicanal
- MessageFormattingSkill: Formatação de mensagens
- MultiChannelSkill: Orquestração de canais
- EscalationSkill: Escalação de atendimentos
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

from .base_skill import (
    BaseSkill, SkillContext, SkillResult, SkillMetadata,
    SkillCategory, skill
)

logger = logging.getLogger(__name__)


class NotificationChannel(Enum):
    """Canais de notificação"""
    PUSH = "push"
    SMS = "sms"
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    APP = "app"
    VOICE = "voice"
    TELEGRAM = "telegram"


class NotificationPriority(Enum):
    """Prioridade de notificação"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"


@dataclass
class NotificationTemplate:
    """Template de notificação"""
    template_id: str
    name: str
    channels: List[NotificationChannel]
    subject_template: str
    body_template: str
    priority: NotificationPriority = NotificationPriority.NORMAL
    variables: List[str] = field(default_factory=list)


@skill(
    name="notification",
    version="1.0.0",
    category=SkillCategory.COMMUNICATION,
    description="Envia notificações através de múltiplos canais",
    tags=["notification", "push", "sms", "email", "whatsapp"]
)
class NotificationSkill(BaseSkill):
    """
    Skill para envio de notificações multicanal.

    Suporta:
    - Push notifications
    - SMS
    - Email
    - WhatsApp
    - Notificações no app
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self._templates: Dict[str, NotificationTemplate] = {}
        self._channel_handlers: Dict[NotificationChannel, Any] = {}

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="notification",
            version="1.0.0",
            category=SkillCategory.COMMUNICATION,
            description="Envia notificações multicanal",
            required_permissions=["notifications.send"],
            tags=["notification", "communication"],
            config_schema={
                "default_channel": {"type": "string", "default": "push"},
                "retry_count": {"type": "integer", "default": 3},
                "batch_size": {"type": "integer", "default": 100},
            }
        )

    async def _execute(self, context: SkillContext, **params) -> SkillResult:
        """
        Envia notificação.

        Params:
            recipients: Lista de IDs de destinatários
            title: Título da notificação
            message: Corpo da mensagem
            channels: Lista de canais (opcional)
            priority: Prioridade (opcional)
            template_id: ID do template (opcional)
            data: Dados adicionais
        """
        recipients = params.get("recipients", [])
        title = params.get("title", "")
        message = params.get("message", "")
        channels = params.get("channels", [NotificationChannel.PUSH])
        priority = params.get("priority", NotificationPriority.NORMAL)
        template_id = params.get("template_id")
        data = params.get("data", {})

        if not recipients:
            return SkillResult.fail("Nenhum destinatário especificado")

        # Usar template se fornecido
        if template_id and template_id in self._templates:
            template = self._templates[template_id]
            title = self._render_template(template.subject_template, data)
            message = self._render_template(template.body_template, data)
            channels = template.channels
            priority = template.priority

        # Enviar para cada canal
        results = []
        for channel in channels:
            if isinstance(channel, str):
                channel = NotificationChannel(channel)

            result = await self._send_to_channel(
                channel=channel,
                recipients=recipients,
                title=title,
                message=message,
                priority=priority,
                data=data,
                context=context
            )
            results.append({
                "channel": channel.value,
                "success": result["success"],
                "sent": result.get("sent", 0),
                "failed": result.get("failed", 0),
            })

        total_sent = sum(r["sent"] for r in results)
        total_failed = sum(r["failed"] for r in results)

        return SkillResult.ok({
            "total_recipients": len(recipients),
            "total_sent": total_sent,
            "total_failed": total_failed,
            "by_channel": results,
        })

    async def _send_to_channel(
        self,
        channel: NotificationChannel,
        recipients: List[str],
        title: str,
        message: str,
        priority: NotificationPriority,
        data: Dict[str, Any],
        context: SkillContext
    ) -> Dict[str, Any]:
        """Envia para um canal específico"""
        # Implementação simulada - em produção conectaria com serviços reais
        sent = 0
        failed = 0

        for recipient in recipients:
            try:
                # Simular envio
                await asyncio.sleep(0.01)
                sent += 1
                logger.debug(f"Notificação enviada: {channel.value} -> {recipient}")

            except Exception as e:
                failed += 1
                logger.error(f"Erro ao enviar para {recipient}: {e}")

        return {"success": failed == 0, "sent": sent, "failed": failed}

    def _render_template(self, template: str, data: Dict[str, Any]) -> str:
        """Renderiza template com dados"""
        result = template
        for key, value in data.items():
            result = result.replace(f"{{{{{key}}}}}", str(value))
        return result

    def register_template(self, template: NotificationTemplate):
        """Registra template de notificação"""
        self._templates[template.template_id] = template

    async def send_bulk(
        self,
        context: SkillContext,
        notifications: List[Dict[str, Any]]
    ) -> SkillResult:
        """Envia notificações em lote"""
        results = []
        batch_size = self.get_config("batch_size", 100)

        for i in range(0, len(notifications), batch_size):
            batch = notifications[i:i + batch_size]
            batch_results = await asyncio.gather(*[
                self.execute(context, **notif) for notif in batch
            ])
            results.extend(batch_results)

        success_count = sum(1 for r in results if r.success)

        return SkillResult.ok({
            "total": len(notifications),
            "success": success_count,
            "failed": len(notifications) - success_count,
        })


@skill(
    name="message_formatting",
    version="1.0.0",
    category=SkillCategory.COMMUNICATION,
    description="Formata mensagens para diferentes contextos",
    tags=["formatting", "message", "template"]
)
class MessageFormattingSkill(BaseSkill):
    """
    Skill para formatação de mensagens.

    Suporta:
    - Templates com variáveis
    - Formatação para diferentes canais
    - Personalização por idioma
    - Markdown/HTML
    """

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="message_formatting",
            version="1.0.0",
            category=SkillCategory.COMMUNICATION,
            description="Formata mensagens",
            tags=["formatting", "message"],
        )

    async def _execute(self, context: SkillContext, **params) -> SkillResult:
        """
        Formata mensagem.

        Params:
            template: Template da mensagem
            variables: Variáveis para substituição
            format: Formato de saída (text, html, markdown)
            channel: Canal de destino (ajusta formatação)
            language: Idioma
        """
        template = params.get("template", "")
        variables = params.get("variables", {})
        output_format = params.get("format", "text")
        channel = params.get("channel", "app")
        language = params.get("language", "pt-BR")

        # Substituir variáveis
        formatted = self._substitute_variables(template, variables)

        # Aplicar formatação do canal
        formatted = self._format_for_channel(formatted, channel, output_format)

        # Truncar se necessário
        max_length = self._get_max_length(channel)
        if len(formatted) > max_length:
            formatted = formatted[:max_length - 3] + "..."

        return SkillResult.ok({
            "formatted_message": formatted,
            "original_length": len(template),
            "final_length": len(formatted),
            "truncated": len(formatted) < len(template),
        })

    def _substitute_variables(self, template: str, variables: Dict[str, Any]) -> str:
        """Substitui variáveis no template"""
        result = template

        for key, value in variables.items():
            # Suporta {{var}} e {var}
            result = result.replace(f"{{{{{key}}}}}", str(value))
            result = result.replace(f"{{{key}}}", str(value))

        return result

    def _format_for_channel(self, text: str, channel: str, output_format: str) -> str:
        """Ajusta formatação para o canal"""
        if channel == "sms":
            # SMS: remover formatação, limitar caracteres
            text = self._strip_formatting(text)
        elif channel == "whatsapp":
            # WhatsApp: converter para formatação WhatsApp
            text = self._to_whatsapp_format(text)
        elif channel == "email" and output_format == "html":
            # Email HTML: manter/converter para HTML
            text = self._to_html(text)

        return text

    def _strip_formatting(self, text: str) -> str:
        """Remove formatação do texto"""
        import re
        # Remover tags HTML
        text = re.sub(r'<[^>]+>', '', text)
        # Remover markdown
        text = re.sub(r'[*_~`]', '', text)
        return text

    def _to_whatsapp_format(self, text: str) -> str:
        """Converte para formatação WhatsApp"""
        # WhatsApp usa *bold*, _italic_, ~strikethrough~, ```code```
        return text

    def _to_html(self, text: str) -> str:
        """Converte markdown para HTML básico"""
        import re
        # Bold
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
        # Quebras de linha
        text = text.replace('\n', '<br>')
        return text

    def _get_max_length(self, channel: str) -> int:
        """Retorna tamanho máximo por canal"""
        limits = {
            "sms": 160,
            "push": 256,
            "whatsapp": 4096,
            "email": 100000,
            "app": 10000,
        }
        return limits.get(channel, 10000)


@skill(
    name="multi_channel",
    version="1.0.0",
    category=SkillCategory.COMMUNICATION,
    description="Orquestra comunicação em múltiplos canais",
    tags=["multichannel", "communication", "orchestration"]
)
class MultiChannelSkill(BaseSkill):
    """
    Skill para orquestração de comunicação multicanal.

    Funcionalidades:
    - Seleção inteligente de canal
    - Fallback entre canais
    - Preferências do usuário
    - Horários de envio
    """

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="multi_channel",
            version="1.0.0",
            category=SkillCategory.COMMUNICATION,
            description="Orquestra comunicação multicanal",
            dependencies=["notification", "message_formatting"],
            tags=["multichannel", "orchestration"],
        )

    async def _execute(self, context: SkillContext, **params) -> SkillResult:
        """
        Orquestra envio multicanal.

        Params:
            recipient_id: ID do destinatário
            message: Mensagem a enviar
            priority: Prioridade
            respect_preferences: Respeitar preferências do usuário
            fallback_order: Ordem de fallback dos canais
        """
        recipient_id = params.get("recipient_id")
        message = params.get("message", "")
        title = params.get("title", "")
        priority = params.get("priority", "normal")
        respect_preferences = params.get("respect_preferences", True)
        fallback_order = params.get("fallback_order", ["push", "whatsapp", "sms", "email"])

        # Determinar canais a usar
        channels = await self._select_channels(
            recipient_id=recipient_id,
            priority=priority,
            respect_preferences=respect_preferences,
            fallback_order=fallback_order,
            context=context
        )

        # Tentar cada canal até sucesso
        for channel in channels:
            result = await self._try_channel(
                channel=channel,
                recipient_id=recipient_id,
                title=title,
                message=message,
                context=context
            )

            if result["success"]:
                return SkillResult.ok({
                    "channel_used": channel,
                    "recipient": recipient_id,
                    "attempts": channels.index(channel) + 1,
                })

        return SkillResult.fail(
            f"Falha ao enviar para todos os canais: {fallback_order}",
            error_code="ALL_CHANNELS_FAILED"
        )

    async def _select_channels(
        self,
        recipient_id: str,
        priority: str,
        respect_preferences: bool,
        fallback_order: List[str],
        context: SkillContext
    ) -> List[str]:
        """Seleciona canais baseado em preferências e prioridade"""
        channels = fallback_order.copy()

        # Ajustar ordem baseado na prioridade
        if priority in ["urgent", "critical"]:
            # Para urgente, priorizar canais imediatos
            immediate = ["push", "sms", "whatsapp"]
            channels = [c for c in immediate if c in channels] + \
                       [c for c in channels if c not in immediate]

        # Buscar preferências do usuário e reordenar
        if respect_preferences:
            try:
                # Tentar obter preferências do usuário do contexto
                user_prefs = context.get_data("user_preferences", {})

                if user_prefs:
                    # Reordenar baseado nas preferências
                    canal_primario = user_prefs.get("canal_primario")
                    canal_secundario = user_prefs.get("canal_secundario")

                    preferred_order = []

                    # Adicionar canal primário primeiro
                    if canal_primario and canal_primario in channels:
                        preferred_order.append(canal_primario)

                    # Adicionar canal secundário
                    if canal_secundario and canal_secundario in channels:
                        if canal_secundario not in preferred_order:
                            preferred_order.append(canal_secundario)

                    # Adicionar os demais canais na ordem original
                    for channel in channels:
                        if channel not in preferred_order:
                            preferred_order.append(channel)

                    channels = preferred_order

                    logger.debug(
                        f"Canais reordenados por preferências do usuário {recipient_id}: {channels}"
                    )
            except Exception as e:
                logger.warning(f"Erro ao buscar preferências do usuário: {e}")
                # Continuar com a ordem padrão em caso de erro

        return channels

    async def _try_channel(
        self,
        channel: str,
        recipient_id: str,
        title: str,
        message: str,
        context: SkillContext
    ) -> Dict[str, Any]:
        """Tenta enviar por um canal"""
        try:
            # Simular envio
            await asyncio.sleep(0.1)
            return {"success": True, "channel": channel}
        except Exception as e:
            return {"success": False, "error": str(e)}


@skill(
    name="escalation",
    version="1.0.0",
    category=SkillCategory.COMMUNICATION,
    description="Gerencia escalação de atendimentos",
    tags=["escalation", "support", "workflow"]
)
class EscalationSkill(BaseSkill):
    """
    Skill para escalação de atendimentos.

    Funcionalidades:
    - Escalação automática por tempo
    - Escalação por complexidade
    - Notificação de supervisores
    - Histórico de escalações
    """

    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="escalation",
            version="1.0.0",
            category=SkillCategory.COMMUNICATION,
            description="Gerencia escalação",
            required_permissions=["escalation.create"],
            tags=["escalation", "support"],
        )

    async def _execute(self, context: SkillContext, **params) -> SkillResult:
        """
        Processa escalação.

        Params:
            conversation_id: ID da conversa
            reason: Motivo da escalação
            target_level: Nível de escalação (1, 2, 3)
            target_agent: Agente específico (opcional)
            priority: Prioridade
            notes: Notas adicionais
        """
        conversation_id = params.get("conversation_id")
        reason = params.get("reason", "")
        target_level = params.get("target_level", 1)
        target_agent = params.get("target_agent")
        priority = params.get("priority", "normal")
        notes = params.get("notes", "")

        # Validar
        if not conversation_id:
            return SkillResult.fail("conversation_id é obrigatório")

        # Determinar destino da escalação
        target = await self._determine_target(
            target_level=target_level,
            target_agent=target_agent,
            context=context
        )

        # Criar registro de escalação
        escalation = {
            "escalation_id": f"esc_{datetime.now().timestamp()}",
            "conversation_id": conversation_id,
            "from_agent": context.agent_id,
            "to_agent": target["agent_id"],
            "to_level": target_level,
            "reason": reason,
            "priority": priority,
            "notes": notes,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
        }

        # Notificar destino
        await self._notify_target(target, escalation, context)

        return SkillResult.ok({
            "escalation_id": escalation["escalation_id"],
            "target_agent": target["agent_id"],
            "target_level": target_level,
            "status": "escalated",
        })

    async def _determine_target(
        self,
        target_level: int,
        target_agent: str,
        context: SkillContext
    ) -> Dict[str, Any]:
        """Determina destino da escalação"""
        if target_agent:
            return {"agent_id": target_agent, "type": "specific"}

        # Lógica de roteamento por nível
        level_agents = {
            1: "supervisor",
            2: "gerente",
            3: "diretor",
        }

        return {
            "agent_id": level_agents.get(target_level, "supervisor"),
            "type": "level",
            "level": target_level,
        }

    async def _notify_target(
        self,
        target: Dict[str, Any],
        escalation: Dict[str, Any],
        context: SkillContext
    ):
        """Notifica agente destino"""
        # Simular notificação
        logger.info(
            f"Escalação {escalation['escalation_id']} para {target['agent_id']}: "
            f"{escalation['reason']}"
        )
