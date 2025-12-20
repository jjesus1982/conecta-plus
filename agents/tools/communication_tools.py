"""
Conecta Plus - Communication Tools
Ferramentas para envio de comunicações
"""

import asyncio
import logging
import hashlib
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

from .base_tool import (
    BaseTool, ToolContext, ToolResult, ToolMetadata,
    ToolCategory, ToolParameter, ParameterType, tool
)

logger = logging.getLogger(__name__)


class NotificationChannel(Enum):
    """Canais de notificação"""
    PUSH = "push"
    EMAIL = "email"
    SMS = "sms"
    WHATSAPP = "whatsapp"
    IN_APP = "in_app"
    VOICE = "voice"


class NotificationPriority(Enum):
    """Prioridade de notificação"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


# ============================================================
# Send Notification Tool
# ============================================================

@dataclass
class Notification:
    """Notificação"""
    notification_id: str
    channel: NotificationChannel
    recipient: str
    title: str
    message: str
    priority: NotificationPriority = NotificationPriority.NORMAL
    sent_at: datetime = field(default_factory=datetime.now)
    status: str = "sent"
    metadata: Dict[str, Any] = field(default_factory=dict)


@tool(
    name="send_notification",
    version="1.0.0",
    category=ToolCategory.COMMUNICATION,
    description="Envio de notificações multicanal",
    parameters=[
        ToolParameter("channel", ParameterType.ENUM, "Canal de envio",
                     required=True, enum_values=["push", "email", "sms", "whatsapp", "in_app"]),
        ToolParameter("recipient", ParameterType.STRING, "Destinatário", required=True),
        ToolParameter("title", ParameterType.STRING, "Título da notificação", required=True),
        ToolParameter("message", ParameterType.STRING, "Mensagem", required=True),
        ToolParameter("priority", ParameterType.ENUM, "Prioridade",
                     required=False, default="normal", enum_values=["low", "normal", "high", "urgent"]),
        ToolParameter("data", ParameterType.OBJECT, "Dados adicionais", required=False),
        ToolParameter("schedule", ParameterType.DATETIME, "Agendar envio", required=False),
        ToolParameter("ttl", ParameterType.INTEGER, "Time to live (segundos)", required=False),
    ],
    tags=["notification", "push", "alert"],
    rate_limit_per_minute=100
)
class SendNotificationTool(BaseTool):
    """
    Ferramenta para envio de notificações.
    Suporta múltiplos canais e agendamento.
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self._sent_notifications: List[Notification] = []

    async def _execute(self, context: ToolContext, **params) -> ToolResult:
        """Envia notificação"""
        channel = NotificationChannel(params.get("channel"))
        recipient = params.get("recipient")
        title = params.get("title")
        message = params.get("message")
        priority = NotificationPriority(params.get("priority", "normal"))
        data = params.get("data", {})
        schedule = params.get("schedule")
        ttl = params.get("ttl")

        if not recipient or not title or not message:
            return ToolResult.fail("'recipient', 'title' e 'message' são obrigatórios")

        # Validar recipient baseado no canal
        validation = self._validate_recipient(channel, recipient)
        if not validation["valid"]:
            return ToolResult.fail(validation["error"], error_code="INVALID_RECIPIENT")

        # Criar notificação
        notification_id = hashlib.md5(
            f"{channel.value}{recipient}{datetime.now()}".encode()
        ).hexdigest()[:16]

        notification = Notification(
            notification_id=notification_id,
            channel=channel,
            recipient=recipient,
            title=title,
            message=message,
            priority=priority,
            metadata=data
        )

        if schedule:
            notification.status = "scheduled"
            notification.metadata["scheduled_for"] = schedule

        self._sent_notifications.append(notification)

        return ToolResult.ok({
            "notification_id": notification_id,
            "channel": channel.value,
            "recipient": recipient,
            "status": notification.status,
            "priority": priority.value,
            "sent_at": notification.sent_at.isoformat(),
            "ttl": ttl
        })

    def _validate_recipient(self, channel: NotificationChannel, recipient: str) -> Dict:
        """Valida destinatário por canal"""
        if channel == NotificationChannel.EMAIL:
            if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', recipient):
                return {"valid": False, "error": "Email inválido"}

        elif channel in [NotificationChannel.SMS, NotificationChannel.WHATSAPP]:
            digits = re.sub(r'\D', '', recipient)
            if len(digits) < 10:
                return {"valid": False, "error": "Número de telefone inválido"}

        elif channel == NotificationChannel.PUSH:
            if len(recipient) < 10:
                return {"valid": False, "error": "Token push inválido"}

        return {"valid": True, "error": None}


# ============================================================
# Send Email Tool
# ============================================================

@tool(
    name="send_email",
    version="1.0.0",
    category=ToolCategory.COMMUNICATION,
    description="Envio de emails",
    parameters=[
        ToolParameter("to", ParameterType.STRING, "Destinatário(s)", required=True),
        ToolParameter("subject", ParameterType.STRING, "Assunto", required=True),
        ToolParameter("body", ParameterType.STRING, "Corpo do email", required=True),
        ToolParameter("html", ParameterType.BOOLEAN, "Corpo em HTML", required=False, default=False),
        ToolParameter("cc", ParameterType.STRING, "Cópia", required=False),
        ToolParameter("bcc", ParameterType.STRING, "Cópia oculta", required=False),
        ToolParameter("reply_to", ParameterType.STRING, "Responder para", required=False),
        ToolParameter("attachments", ParameterType.ARRAY, "Anexos", required=False),
        ToolParameter("template", ParameterType.STRING, "Template de email", required=False),
        ToolParameter("variables", ParameterType.OBJECT, "Variáveis do template", required=False),
    ],
    tags=["email", "smtp", "communication"],
    rate_limit_per_minute=30
)
class SendEmailTool(BaseTool):
    """
    Ferramenta para envio de emails.
    Suporta HTML, anexos e templates.
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self._email_templates = {
            "welcome": {
                "subject": "Bem-vindo ao {{condominio}}",
                "body": "Olá {{nome}},\n\nSeja bem-vindo ao {{condominio}}!"
            },
            "boleto": {
                "subject": "Boleto {{competencia}} - {{condominio}}",
                "body": "Seu boleto no valor de R$ {{valor}} vence em {{vencimento}}."
            },
            "comunicado": {
                "subject": "{{assunto}}",
                "body": "{{corpo}}"
            }
        }

    async def _execute(self, context: ToolContext, **params) -> ToolResult:
        """Envia email"""
        to = params.get("to")
        subject = params.get("subject")
        body = params.get("body")
        html = params.get("html", False)
        cc = params.get("cc")
        bcc = params.get("bcc")
        reply_to = params.get("reply_to")
        attachments = params.get("attachments", [])
        template = params.get("template")
        variables = params.get("variables", {})

        if not to:
            return ToolResult.fail("'to' é obrigatório")

        # Se usar template
        if template:
            tpl = self._email_templates.get(template)
            if not tpl:
                return ToolResult.fail(f"Template não encontrado: {template}")

            subject = tpl["subject"]
            body = tpl["body"]

            # Substituir variáveis
            for key, value in variables.items():
                subject = subject.replace(f"{{{{{key}}}}}", str(value))
                body = body.replace(f"{{{{{key}}}}}", str(value))

        if not subject or not body:
            return ToolResult.fail("'subject' e 'body' são obrigatórios")

        # Validar emails
        recipients = [e.strip() for e in to.split(",")]
        for email in recipients:
            if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
                return ToolResult.fail(f"Email inválido: {email}")

        # Gerar ID da mensagem
        message_id = hashlib.md5(
            f"{to}{subject}{datetime.now()}".encode()
        ).hexdigest()[:16]

        result = {
            "message_id": message_id,
            "to": recipients,
            "subject": subject,
            "status": "sent",
            "sent_at": datetime.now().isoformat()
        }

        if cc:
            result["cc"] = [e.strip() for e in cc.split(",")]
        if bcc:
            result["bcc"] = [e.strip() for e in bcc.split(",")]
        if attachments:
            result["attachments_count"] = len(attachments)

        return ToolResult.ok(result)


# ============================================================
# Send SMS Tool
# ============================================================

@tool(
    name="send_sms",
    version="1.0.0",
    category=ToolCategory.COMMUNICATION,
    description="Envio de SMS",
    parameters=[
        ToolParameter("to", ParameterType.STRING, "Número de telefone", required=True),
        ToolParameter("message", ParameterType.STRING, "Mensagem", required=True, max_length=160),
        ToolParameter("sender_id", ParameterType.STRING, "ID do remetente", required=False),
        ToolParameter("flash", ParameterType.BOOLEAN, "SMS flash", required=False, default=False),
        ToolParameter("schedule", ParameterType.DATETIME, "Agendar envio", required=False),
    ],
    tags=["sms", "text", "communication"],
    rate_limit_per_minute=20
)
class SendSMSTool(BaseTool):
    """
    Ferramenta para envio de SMS.
    Suporta SMS padrão e flash.
    """

    async def _execute(self, context: ToolContext, **params) -> ToolResult:
        """Envia SMS"""
        to = params.get("to")
        message = params.get("message")
        sender_id = params.get("sender_id", "CONECTA")
        flash = params.get("flash", False)
        schedule = params.get("schedule")

        if not to or not message:
            return ToolResult.fail("'to' e 'message' são obrigatórios")

        # Normalizar número
        phone = re.sub(r'\D', '', to)
        if len(phone) < 10:
            return ToolResult.fail("Número de telefone inválido")

        if not phone.startswith("55"):
            phone = "55" + phone

        # Verificar tamanho da mensagem
        if len(message) > 160:
            # Dividir em partes
            parts = [message[i:i+153] for i in range(0, len(message), 153)]
            return await self._send_multipart(phone, parts, sender_id)

        # Gerar ID
        sms_id = hashlib.md5(
            f"{phone}{message}{datetime.now()}".encode()
        ).hexdigest()[:12]

        result = {
            "sms_id": sms_id,
            "to": phone,
            "message_length": len(message),
            "parts": 1,
            "status": "sent" if not schedule else "scheduled",
            "sender_id": sender_id,
            "flash": flash,
            "sent_at": datetime.now().isoformat()
        }

        if schedule:
            result["scheduled_for"] = schedule

        return ToolResult.ok(result)

    async def _send_multipart(
        self,
        phone: str,
        parts: List[str],
        sender_id: str
    ) -> ToolResult:
        """Envia SMS multipart"""
        results = []

        for i, part in enumerate(parts):
            sms_id = hashlib.md5(
                f"{phone}{part}{i}{datetime.now()}".encode()
            ).hexdigest()[:12]

            results.append({
                "sms_id": sms_id,
                "part": i + 1,
                "status": "sent"
            })

        return ToolResult.ok({
            "to": phone,
            "total_parts": len(parts),
            "sender_id": sender_id,
            "status": "sent",
            "parts": results,
            "sent_at": datetime.now().isoformat()
        })


# ============================================================
# Send WhatsApp Tool
# ============================================================

class WhatsAppMessageType(Enum):
    """Tipos de mensagem WhatsApp"""
    TEXT = "text"
    IMAGE = "image"
    DOCUMENT = "document"
    TEMPLATE = "template"
    INTERACTIVE = "interactive"
    LOCATION = "location"


@tool(
    name="send_whatsapp",
    version="1.0.0",
    category=ToolCategory.COMMUNICATION,
    description="Envio de mensagens WhatsApp",
    parameters=[
        ToolParameter("to", ParameterType.STRING, "Número de telefone", required=True),
        ToolParameter("type", ParameterType.ENUM, "Tipo de mensagem",
                     required=False, default="text",
                     enum_values=["text", "image", "document", "template", "interactive", "location"]),
        ToolParameter("message", ParameterType.STRING, "Mensagem de texto", required=False),
        ToolParameter("template_name", ParameterType.STRING, "Nome do template", required=False),
        ToolParameter("template_params", ParameterType.ARRAY, "Parâmetros do template", required=False),
        ToolParameter("media_url", ParameterType.STRING, "URL da mídia", required=False),
        ToolParameter("caption", ParameterType.STRING, "Legenda da mídia", required=False),
        ToolParameter("buttons", ParameterType.ARRAY, "Botões interativos", required=False),
    ],
    tags=["whatsapp", "messaging", "communication"],
    rate_limit_per_minute=30
)
class SendWhatsAppTool(BaseTool):
    """
    Ferramenta para envio de WhatsApp.
    Suporta texto, mídia, templates e mensagens interativas.
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self._templates = {
            "boleto_vencendo": {
                "components": [
                    {"type": "header", "format": "text"},
                    {"type": "body", "text": "Olá {{1}}, seu boleto no valor de R$ {{2}} vence em {{3}}."},
                    {"type": "buttons", "buttons": [{"type": "url", "text": "Ver boleto"}]}
                ]
            },
            "confirmacao_reserva": {
                "components": [
                    {"type": "body", "text": "Sua reserva de {{1}} para {{2}} foi confirmada."}
                ]
            }
        }

    async def _execute(self, context: ToolContext, **params) -> ToolResult:
        """Envia mensagem WhatsApp"""
        to = params.get("to")
        msg_type = WhatsAppMessageType(params.get("type", "text"))
        message = params.get("message")
        template_name = params.get("template_name")
        template_params = params.get("template_params", [])
        media_url = params.get("media_url")
        caption = params.get("caption")
        buttons = params.get("buttons", [])

        if not to:
            return ToolResult.fail("'to' é obrigatório")

        # Normalizar número
        phone = re.sub(r'\D', '', to)
        if not phone.startswith("55"):
            phone = "55" + phone

        # Validar por tipo
        if msg_type == WhatsAppMessageType.TEXT and not message:
            return ToolResult.fail("'message' é obrigatório para mensagens de texto")

        if msg_type == WhatsAppMessageType.TEMPLATE and not template_name:
            return ToolResult.fail("'template_name' é obrigatório para templates")

        if msg_type in [WhatsAppMessageType.IMAGE, WhatsAppMessageType.DOCUMENT] and not media_url:
            return ToolResult.fail("'media_url' é obrigatório para mídia")

        # Gerar ID
        wa_id = f"wamid.{hashlib.md5(f'{phone}{datetime.now()}'.encode()).hexdigest()}"

        result = {
            "message_id": wa_id,
            "to": phone,
            "type": msg_type.value,
            "status": "sent",
            "sent_at": datetime.now().isoformat()
        }

        if msg_type == WhatsAppMessageType.TEXT:
            result["message"] = message

        elif msg_type == WhatsAppMessageType.TEMPLATE:
            result["template"] = template_name
            result["params"] = template_params

        elif msg_type in [WhatsAppMessageType.IMAGE, WhatsAppMessageType.DOCUMENT]:
            result["media_url"] = media_url
            if caption:
                result["caption"] = caption

        elif msg_type == WhatsAppMessageType.INTERACTIVE:
            result["buttons"] = len(buttons)

        return ToolResult.ok(result)


# ============================================================
# Broadcast Tool
# ============================================================

@dataclass
class BroadcastResult:
    """Resultado de broadcast"""
    broadcast_id: str
    total: int
    sent: int
    failed: int
    status: str
    results: List[Dict] = field(default_factory=list)


@tool(
    name="broadcast",
    version="1.0.0",
    category=ToolCategory.COMMUNICATION,
    description="Envio em massa para múltiplos destinatários",
    parameters=[
        ToolParameter("channel", ParameterType.ENUM, "Canal de envio",
                     required=True, enum_values=["push", "email", "sms", "whatsapp"]),
        ToolParameter("recipients", ParameterType.ARRAY, "Lista de destinatários", required=True),
        ToolParameter("title", ParameterType.STRING, "Título/Assunto", required=True),
        ToolParameter("message", ParameterType.STRING, "Mensagem", required=True),
        ToolParameter("personalize", ParameterType.BOOLEAN, "Personalizar por destinatário", required=False, default=False),
        ToolParameter("batch_size", ParameterType.INTEGER, "Tamanho do lote", required=False, default=100),
        ToolParameter("delay_ms", ParameterType.INTEGER, "Delay entre lotes (ms)", required=False, default=1000),
        ToolParameter("fail_fast", ParameterType.BOOLEAN, "Parar no primeiro erro", required=False, default=False),
    ],
    tags=["broadcast", "mass", "bulk", "communication"],
    required_permissions=["broadcast"],
    rate_limit_per_hour=10
)
class BroadcastTool(BaseTool):
    """
    Ferramenta para envio em massa.
    Suporta múltiplos canais e personalização.
    """

    async def _execute(self, context: ToolContext, **params) -> ToolResult:
        """Executa broadcast"""
        channel = NotificationChannel(params.get("channel"))
        recipients = params.get("recipients", [])
        title = params.get("title")
        message = params.get("message")
        personalize = params.get("personalize", False)
        batch_size = params.get("batch_size", 100)
        delay_ms = params.get("delay_ms", 1000)
        fail_fast = params.get("fail_fast", False)

        if not recipients:
            return ToolResult.fail("'recipients' é obrigatório")

        if not title or not message:
            return ToolResult.fail("'title' e 'message' são obrigatórios")

        # Gerar ID do broadcast
        broadcast_id = hashlib.md5(
            f"{channel.value}{len(recipients)}{datetime.now()}".encode()
        ).hexdigest()[:12]

        # Processar em lotes (simulado)
        results = []
        sent = 0
        failed = 0

        for i, recipient in enumerate(recipients):
            # Extrair dados do recipient
            if isinstance(recipient, dict):
                address = recipient.get("address") or recipient.get("email") or recipient.get("phone")
                variables = recipient.get("variables", {})
            else:
                address = recipient
                variables = {}

            # Personalizar mensagem
            if personalize and variables:
                personalized_message = message
                personalized_title = title
                for key, value in variables.items():
                    personalized_message = personalized_message.replace(f"{{{{{key}}}}}", str(value))
                    personalized_title = personalized_title.replace(f"{{{{{key}}}}}", str(value))
            else:
                personalized_message = message
                personalized_title = title

            # Simular envio
            success = True  # Em produção, verificaria resultado real

            if success:
                sent += 1
                results.append({
                    "recipient": address,
                    "status": "sent",
                    "message_id": f"msg_{broadcast_id}_{i}"
                })
            else:
                failed += 1
                results.append({
                    "recipient": address,
                    "status": "failed",
                    "error": "Simulated error"
                })

                if fail_fast:
                    break

        status = "completed" if failed == 0 else "partial" if sent > 0 else "failed"

        return ToolResult.ok({
            "broadcast_id": broadcast_id,
            "channel": channel.value,
            "total": len(recipients),
            "sent": sent,
            "failed": failed,
            "status": status,
            "results": results[:100],  # Limitar resultados retornados
            "started_at": datetime.now().isoformat()
        })


def register_communication_tools():
    """Registra todas as ferramentas de comunicação"""
    pass
