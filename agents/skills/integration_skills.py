"""
Conecta Plus - Integration Skills
Habilidades de integração com serviços externos
"""

import asyncio
import logging
import re
import json
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

from .base_skill import (
    BaseSkill, SkillContext, SkillResult, SkillMetadata,
    SkillCategory, skill
)

logger = logging.getLogger(__name__)


# ============================================================
# WhatsApp Skill
# ============================================================

class WhatsAppMessageType(Enum):
    """Tipos de mensagem WhatsApp"""
    TEXT = "text"
    IMAGE = "image"
    DOCUMENT = "document"
    AUDIO = "audio"
    VIDEO = "video"
    LOCATION = "location"
    CONTACT = "contact"
    TEMPLATE = "template"
    INTERACTIVE = "interactive"
    REACTION = "reaction"


@dataclass
class WhatsAppMessage:
    """Mensagem WhatsApp"""
    to: str
    type: WhatsAppMessageType
    content: Any

    # Metadados
    reply_to: Optional[str] = None
    preview_url: bool = True

    # Template
    template_name: Optional[str] = None
    template_language: str = "pt_BR"
    template_components: List[Dict] = field(default_factory=list)


@dataclass
class WhatsAppContact:
    """Contato WhatsApp"""
    phone: str
    name: str
    profile_picture: Optional[str] = None
    is_business: bool = False
    business_name: Optional[str] = None


@skill(
    name="whatsapp",
    version="1.0.0",
    category=SkillCategory.INTEGRATION,
    description="Integração com WhatsApp Business API",
    tags=["whatsapp", "messaging", "communication"]
)
class WhatsAppSkill(BaseSkill):
    """
    Skill para integração com WhatsApp Business API.
    Suporta envio de mensagens, templates, mídia e interações.
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.api_url = self.get_config("api_url", "https://graph.facebook.com/v18.0")
        self.phone_number_id = self.get_config("phone_number_id")
        self.access_token = self.get_config("access_token")
        self._message_queue: List[WhatsAppMessage] = []

    async def _on_initialize(self):
        """Verifica conexão com API"""
        # Em produção, verificaria token
        pass

    async def _execute(self, context: SkillContext, **params) -> SkillResult:
        """Executa ação do WhatsApp"""
        action = params.get("action", "send_message")

        if action == "send_message":
            return await self._send_message(context, params)
        elif action == "send_template":
            return await self._send_template(context, params)
        elif action == "send_media":
            return await self._send_media(context, params)
        elif action == "send_interactive":
            return await self._send_interactive(context, params)
        elif action == "get_profile":
            return await self._get_profile(context, params)
        elif action == "mark_read":
            return await self._mark_read(context, params)
        else:
            return SkillResult.fail(f"Ação desconhecida: {action}")

    async def _send_message(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Envia mensagem de texto"""
        to = params.get("to")
        text = params.get("text")

        if not to or not text:
            return SkillResult.fail("'to' e 'text' são obrigatórios")

        # Normalizar número
        phone = self._normalize_phone(to)

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": phone,
            "type": "text",
            "text": {"body": text}
        }

        if params.get("preview_url", True):
            payload["text"]["preview_url"] = True

        if params.get("reply_to"):
            payload["context"] = {"message_id": params["reply_to"]}

        # Simular envio (em produção, chamaria API)
        message_id = f"wamid.{hashlib.md5(f'{phone}{text}{datetime.now()}'.encode()).hexdigest()}"

        return SkillResult.ok({
            "message_id": message_id,
            "to": phone,
            "type": "text",
            "status": "sent"
        })

    async def _send_template(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Envia mensagem de template"""
        to = params.get("to")
        template_name = params.get("template_name")

        if not to or not template_name:
            return SkillResult.fail("'to' e 'template_name' são obrigatórios")

        phone = self._normalize_phone(to)
        language = params.get("language", "pt_BR")
        components = params.get("components", [])

        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language},
                "components": components
            }
        }

        message_id = f"wamid.{hashlib.md5(f'{phone}{template_name}{datetime.now()}'.encode()).hexdigest()}"

        return SkillResult.ok({
            "message_id": message_id,
            "to": phone,
            "type": "template",
            "template": template_name,
            "status": "sent"
        })

    async def _send_media(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Envia mídia"""
        to = params.get("to")
        media_type = params.get("media_type", "image")
        media_url = params.get("url")
        media_id = params.get("media_id")
        caption = params.get("caption")

        if not to or (not media_url and not media_id):
            return SkillResult.fail("'to' e 'url' ou 'media_id' são obrigatórios")

        phone = self._normalize_phone(to)

        media_payload = {}
        if media_url:
            media_payload["link"] = media_url
        else:
            media_payload["id"] = media_id

        if caption and media_type in ["image", "video", "document"]:
            media_payload["caption"] = caption

        if media_type == "document":
            media_payload["filename"] = params.get("filename", "document")

        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": media_type,
            media_type: media_payload
        }

        message_id = f"wamid.{hashlib.md5(f'{phone}{media_type}{datetime.now()}'.encode()).hexdigest()}"

        return SkillResult.ok({
            "message_id": message_id,
            "to": phone,
            "type": media_type,
            "status": "sent"
        })

    async def _send_interactive(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Envia mensagem interativa (botões, lista)"""
        to = params.get("to")
        interactive_type = params.get("interactive_type", "button")

        if not to:
            return SkillResult.fail("'to' é obrigatório")

        phone = self._normalize_phone(to)

        interactive = {
            "type": interactive_type,
            "body": {"text": params.get("body", "")}
        }

        if params.get("header"):
            interactive["header"] = params["header"]

        if params.get("footer"):
            interactive["footer"] = {"text": params["footer"]}

        if interactive_type == "button":
            buttons = params.get("buttons", [])
            interactive["action"] = {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {"id": b.get("id", str(i)), "title": b["title"]}
                    }
                    for i, b in enumerate(buttons[:3])  # Max 3 botões
                ]
            }
        elif interactive_type == "list":
            sections = params.get("sections", [])
            interactive["action"] = {
                "button": params.get("button_text", "Ver opções"),
                "sections": sections
            }

        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "interactive",
            "interactive": interactive
        }

        message_id = f"wamid.{hashlib.md5(f'{phone}interactive{datetime.now()}'.encode()).hexdigest()}"

        return SkillResult.ok({
            "message_id": message_id,
            "to": phone,
            "type": "interactive",
            "interactive_type": interactive_type,
            "status": "sent"
        })

    async def _get_profile(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Obtém perfil do contato"""
        phone = params.get("phone")
        if not phone:
            return SkillResult.fail("'phone' é obrigatório")

        phone = self._normalize_phone(phone)

        # Em produção, buscaria da API
        return SkillResult.ok({
            "phone": phone,
            "name": None,
            "profile_picture": None,
            "status": "unknown"
        })

    async def _mark_read(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Marca mensagem como lida"""
        message_id = params.get("message_id")
        if not message_id:
            return SkillResult.fail("'message_id' é obrigatório")

        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id
        }

        return SkillResult.ok({
            "message_id": message_id,
            "status": "read"
        })

    def _normalize_phone(self, phone: str) -> str:
        """Normaliza número de telefone"""
        # Remove caracteres não numéricos
        digits = re.sub(r'\D', '', phone)

        # Adiciona código do país se necessário
        if len(digits) == 11 and digits.startswith('9'):
            digits = '55' + digits
        elif len(digits) == 10:
            digits = '55' + digits
        elif not digits.startswith('55') and len(digits) < 13:
            digits = '55' + digits

        return digits


# ============================================================
# Email Skill
# ============================================================

class EmailPriority(Enum):
    """Prioridade do email"""
    LOW = 1
    NORMAL = 3
    HIGH = 5


@dataclass
class EmailAttachment:
    """Anexo de email"""
    filename: str
    content: bytes
    content_type: str = "application/octet-stream"
    content_id: Optional[str] = None  # Para inline


@dataclass
class EmailMessage:
    """Mensagem de email"""
    to: List[str]
    subject: str
    body: str

    # Opcionais
    cc: List[str] = field(default_factory=list)
    bcc: List[str] = field(default_factory=list)
    reply_to: Optional[str] = None

    # Conteúdo
    html_body: Optional[str] = None
    attachments: List[EmailAttachment] = field(default_factory=list)

    # Configurações
    priority: EmailPriority = EmailPriority.NORMAL
    headers: Dict[str, str] = field(default_factory=dict)


@skill(
    name="email",
    version="1.0.0",
    category=SkillCategory.INTEGRATION,
    description="Envio e processamento de emails",
    tags=["email", "smtp", "communication"]
)
class EmailSkill(BaseSkill):
    """
    Skill para envio de emails via SMTP.
    Suporta HTML, anexos, templates e tracking.
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.smtp_host = self.get_config("smtp_host", "localhost")
        self.smtp_port = self.get_config("smtp_port", 587)
        self.smtp_user = self.get_config("smtp_user")
        self.smtp_password = self.get_config("smtp_password")
        self.from_address = self.get_config("from_address", "noreply@conectaplus.com")
        self.from_name = self.get_config("from_name", "Conecta Plus")
        self._templates: Dict[str, str] = {}

    async def _execute(self, context: SkillContext, **params) -> SkillResult:
        """Executa ação de email"""
        action = params.get("action", "send")

        if action == "send":
            return await self._send_email(context, params)
        elif action == "send_template":
            return await self._send_template(context, params)
        elif action == "validate":
            return await self._validate_email(context, params)
        elif action == "bulk_send":
            return await self._bulk_send(context, params)
        else:
            return SkillResult.fail(f"Ação desconhecida: {action}")

    async def _send_email(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Envia email"""
        to = params.get("to")
        subject = params.get("subject")
        body = params.get("body")

        if not to or not subject or not body:
            return SkillResult.fail("'to', 'subject' e 'body' são obrigatórios")

        # Normalizar destinatários
        recipients = to if isinstance(to, list) else [to]

        # Validar emails
        for email in recipients:
            if not self._is_valid_email(email):
                return SkillResult.fail(f"Email inválido: {email}")

        # Construir mensagem
        html_body = params.get("html_body")
        if not html_body and params.get("use_html", True):
            html_body = self._text_to_html(body)

        # Gerar ID da mensagem
        message_id = f"<{hashlib.md5(f'{recipients}{subject}{datetime.now()}'.encode()).hexdigest()}@conectaplus.com>"

        # Em produção, enviaria via SMTP
        result = {
            "message_id": message_id,
            "to": recipients,
            "subject": subject,
            "status": "sent",
            "timestamp": datetime.now().isoformat()
        }

        if params.get("cc"):
            result["cc"] = params["cc"]
        if params.get("bcc"):
            result["bcc"] = params["bcc"]

        return SkillResult.ok(result)

    async def _send_template(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Envia email usando template"""
        to = params.get("to")
        template_name = params.get("template_name")
        variables = params.get("variables", {})

        if not to or not template_name:
            return SkillResult.fail("'to' e 'template_name' são obrigatórios")

        # Buscar template
        template = self._get_template(template_name)
        if not template:
            return SkillResult.fail(f"Template não encontrado: {template_name}")

        # Substituir variáveis
        subject = template.get("subject", "")
        body = template.get("body", "")
        html_body = template.get("html_body", "")

        for key, value in variables.items():
            placeholder = f"{{{{{key}}}}}"
            subject = subject.replace(placeholder, str(value))
            body = body.replace(placeholder, str(value))
            html_body = html_body.replace(placeholder, str(value))

        return await self._send_email(context, {
            "to": to,
            "subject": subject,
            "body": body,
            "html_body": html_body,
            **params
        })

    async def _validate_email(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Valida endereço de email"""
        email = params.get("email")
        if not email:
            return SkillResult.fail("'email' é obrigatório")

        is_valid = self._is_valid_email(email)

        # Análise adicional
        domain = email.split("@")[1] if "@" in email else ""

        return SkillResult.ok({
            "email": email,
            "valid": is_valid,
            "domain": domain,
            "is_free_provider": domain in [
                "gmail.com", "hotmail.com", "outlook.com",
                "yahoo.com", "yahoo.com.br", "bol.com.br"
            ]
        })

    async def _bulk_send(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Envio em massa"""
        recipients = params.get("recipients", [])
        subject = params.get("subject")
        body = params.get("body")

        if not recipients or not subject or not body:
            return SkillResult.fail("'recipients', 'subject' e 'body' são obrigatórios")

        results = []
        success_count = 0

        for recipient in recipients:
            email = recipient if isinstance(recipient, str) else recipient.get("email")
            variables = recipient.get("variables", {}) if isinstance(recipient, dict) else {}

            # Personalizar corpo
            personalized_body = body
            for key, value in variables.items():
                personalized_body = personalized_body.replace(f"{{{{{key}}}}}", str(value))

            result = await self._send_email(context, {
                "to": email,
                "subject": subject,
                "body": personalized_body
            })

            if result.success:
                success_count += 1

            results.append({
                "email": email,
                "success": result.success,
                "error": result.error
            })

        return SkillResult.ok({
            "total": len(recipients),
            "success": success_count,
            "failed": len(recipients) - success_count,
            "results": results
        })

    def _is_valid_email(self, email: str) -> bool:
        """Valida formato de email"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    def _text_to_html(self, text: str) -> str:
        """Converte texto para HTML"""
        html = text.replace("\n", "<br>\n")
        return f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="utf-8"></head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6;">
            {html}
        </body>
        </html>
        """

    def _get_template(self, name: str) -> Optional[Dict]:
        """Retorna template de email"""
        templates = {
            "welcome": {
                "subject": "Bem-vindo ao {{condominio}}",
                "body": "Olá {{nome}},\n\nSeja bem-vindo ao {{condominio}}!",
                "html_body": "<h1>Bem-vindo!</h1><p>Olá {{nome}},</p><p>Seja bem-vindo ao {{condominio}}!</p>"
            },
            "notification": {
                "subject": "{{assunto}} - {{condominio}}",
                "body": "{{mensagem}}",
                "html_body": "<p>{{mensagem}}</p>"
            },
            "boleto": {
                "subject": "Boleto Disponível - {{condominio}}",
                "body": "Olá {{nome}},\n\nSeu boleto está disponível.\nValor: R$ {{valor}}\nVencimento: {{vencimento}}",
                "html_body": "<p>Olá {{nome}},</p><p>Seu boleto está disponível.</p><p><strong>Valor:</strong> R$ {{valor}}<br><strong>Vencimento:</strong> {{vencimento}}</p>"
            }
        }
        return templates.get(name)


# ============================================================
# SMS Skill
# ============================================================

@skill(
    name="sms",
    version="1.0.0",
    category=SkillCategory.INTEGRATION,
    description="Envio de SMS",
    tags=["sms", "messaging", "communication"]
)
class SMSSkill(BaseSkill):
    """
    Skill para envio de SMS.
    Suporta múltiplos providers e verificação de entrega.
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.provider = self.get_config("provider", "twilio")
        self.api_key = self.get_config("api_key")
        self.sender_id = self.get_config("sender_id", "CONECTAPLUS")
        self.max_length = self.get_config("max_length", 160)

    async def _execute(self, context: SkillContext, **params) -> SkillResult:
        """Executa ação de SMS"""
        action = params.get("action", "send")

        if action == "send":
            return await self._send_sms(context, params)
        elif action == "bulk_send":
            return await self._bulk_send(context, params)
        elif action == "check_status":
            return await self._check_status(context, params)
        elif action == "estimate_cost":
            return await self._estimate_cost(context, params)
        else:
            return SkillResult.fail(f"Ação desconhecida: {action}")

    async def _send_sms(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Envia SMS"""
        to = params.get("to")
        message = params.get("message")

        if not to or not message:
            return SkillResult.fail("'to' e 'message' são obrigatórios")

        # Normalizar número
        phone = self._normalize_phone(to)

        # Verificar tamanho
        if len(message) > self.max_length:
            parts = self._split_message(message)
            return await self._send_multipart(context, phone, parts)

        # Simular envio
        message_id = f"sms_{hashlib.md5(f'{phone}{message}{datetime.now()}'.encode()).hexdigest()[:16]}"

        return SkillResult.ok({
            "message_id": message_id,
            "to": phone,
            "message": message,
            "parts": 1,
            "status": "sent",
            "timestamp": datetime.now().isoformat()
        })

    async def _send_multipart(
        self,
        context: SkillContext,
        phone: str,
        parts: List[str]
    ) -> SkillResult:
        """Envia SMS multipart"""
        results = []

        for i, part in enumerate(parts):
            message_id = f"sms_{hashlib.md5(f'{phone}{part}{datetime.now()}{i}'.encode()).hexdigest()[:16]}"
            results.append({
                "message_id": message_id,
                "part": i + 1,
                "status": "sent"
            })

        return SkillResult.ok({
            "to": phone,
            "parts": len(parts),
            "status": "sent",
            "results": results
        })

    async def _bulk_send(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Envio em massa"""
        recipients = params.get("recipients", [])
        message = params.get("message")

        if not recipients or not message:
            return SkillResult.fail("'recipients' e 'message' são obrigatórios")

        results = []
        success_count = 0

        for recipient in recipients:
            phone = recipient if isinstance(recipient, str) else recipient.get("phone")

            result = await self._send_sms(context, {
                "to": phone,
                "message": message
            })

            if result.success:
                success_count += 1

            results.append({
                "phone": phone,
                "success": result.success,
                "message_id": result.data.get("message_id") if result.success else None
            })

        return SkillResult.ok({
            "total": len(recipients),
            "success": success_count,
            "failed": len(recipients) - success_count,
            "results": results
        })

    async def _check_status(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Verifica status de entrega"""
        message_id = params.get("message_id")
        if not message_id:
            return SkillResult.fail("'message_id' é obrigatório")

        # Em produção, consultaria API do provider
        return SkillResult.ok({
            "message_id": message_id,
            "status": "delivered",
            "delivered_at": datetime.now().isoformat()
        })

    async def _estimate_cost(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Estima custo de envio"""
        message = params.get("message", "")
        count = params.get("count", 1)

        parts = len(self._split_message(message)) if message else 1
        cost_per_part = 0.05  # R$ por parte

        return SkillResult.ok({
            "message_length": len(message),
            "parts": parts,
            "recipients": count,
            "cost_per_message": cost_per_part * parts,
            "total_cost": cost_per_part * parts * count,
            "currency": "BRL"
        })

    def _normalize_phone(self, phone: str) -> str:
        """Normaliza número de telefone"""
        digits = re.sub(r'\D', '', phone)

        if not digits.startswith('55') and len(digits) <= 11:
            digits = '55' + digits

        return digits

    def _split_message(self, message: str) -> List[str]:
        """Divide mensagem em partes"""
        if len(message) <= self.max_length:
            return [message]

        # SMS multipart usa 153 chars por parte
        part_length = 153
        parts = []

        while message:
            if len(message) <= part_length:
                parts.append(message)
                break

            # Encontrar ponto de quebra
            split_point = message.rfind(' ', 0, part_length)
            if split_point == -1:
                split_point = part_length

            parts.append(message[:split_point].strip())
            message = message[split_point:].strip()

        return parts


# ============================================================
# VoIP Skill
# ============================================================

class CallStatus(Enum):
    """Status de chamada"""
    QUEUED = "queued"
    RINGING = "ringing"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BUSY = "busy"
    NO_ANSWER = "no_answer"
    CANCELED = "canceled"


@skill(
    name="voip",
    version="1.0.0",
    category=SkillCategory.INTEGRATION,
    description="Integração VoIP para chamadas de voz",
    tags=["voip", "call", "voice", "communication"]
)
class VoIPSkill(BaseSkill):
    """
    Skill para integração VoIP.
    Suporta originar chamadas, IVR e gravação.
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.provider = self.get_config("provider", "asterisk")
        self.api_url = self.get_config("api_url")
        self.caller_id = self.get_config("caller_id")
        self._active_calls: Dict[str, Dict] = {}

    async def _execute(self, context: SkillContext, **params) -> SkillResult:
        """Executa ação VoIP"""
        action = params.get("action", "call")

        if action == "call":
            return await self._make_call(context, params)
        elif action == "hangup":
            return await self._hangup(context, params)
        elif action == "transfer":
            return await self._transfer(context, params)
        elif action == "play_audio":
            return await self._play_audio(context, params)
        elif action == "get_status":
            return await self._get_status(context, params)
        elif action == "ivr":
            return await self._create_ivr(context, params)
        else:
            return SkillResult.fail(f"Ação desconhecida: {action}")

    async def _make_call(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Origina chamada"""
        to = params.get("to")

        if not to:
            return SkillResult.fail("'to' é obrigatório")

        phone = self._normalize_phone(to)

        call_id = f"call_{hashlib.md5(f'{phone}{datetime.now()}'.encode()).hexdigest()[:16]}"

        call_info = {
            "call_id": call_id,
            "to": phone,
            "from": self.caller_id,
            "status": CallStatus.QUEUED.value,
            "started_at": datetime.now().isoformat(),
            "record": params.get("record", False),
            "timeout": params.get("timeout", 30)
        }

        self._active_calls[call_id] = call_info

        return SkillResult.ok(call_info)

    async def _hangup(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Encerra chamada"""
        call_id = params.get("call_id")
        if not call_id:
            return SkillResult.fail("'call_id' é obrigatório")

        if call_id in self._active_calls:
            self._active_calls[call_id]["status"] = CallStatus.COMPLETED.value
            self._active_calls[call_id]["ended_at"] = datetime.now().isoformat()

        return SkillResult.ok({
            "call_id": call_id,
            "status": "completed"
        })

    async def _transfer(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Transfere chamada"""
        call_id = params.get("call_id")
        destination = params.get("destination")

        if not call_id or not destination:
            return SkillResult.fail("'call_id' e 'destination' são obrigatórios")

        return SkillResult.ok({
            "call_id": call_id,
            "transferred_to": destination,
            "status": "transferred"
        })

    async def _play_audio(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Reproduz áudio na chamada"""
        call_id = params.get("call_id")
        audio_url = params.get("audio_url")
        tts_text = params.get("tts_text")

        if not call_id:
            return SkillResult.fail("'call_id' é obrigatório")

        if not audio_url and not tts_text:
            return SkillResult.fail("'audio_url' ou 'tts_text' é obrigatório")

        return SkillResult.ok({
            "call_id": call_id,
            "audio_played": True,
            "type": "tts" if tts_text else "file"
        })

    async def _get_status(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Obtém status da chamada"""
        call_id = params.get("call_id")
        if not call_id:
            return SkillResult.fail("'call_id' é obrigatório")

        if call_id in self._active_calls:
            return SkillResult.ok(self._active_calls[call_id])

        return SkillResult.ok({
            "call_id": call_id,
            "status": "unknown"
        })

    async def _create_ivr(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Cria menu IVR"""
        name = params.get("name")
        greeting = params.get("greeting")
        options = params.get("options", [])

        if not name or not options:
            return SkillResult.fail("'name' e 'options' são obrigatórios")

        ivr_config = {
            "name": name,
            "greeting": greeting,
            "options": [
                {
                    "digit": opt.get("digit"),
                    "description": opt.get("description"),
                    "action": opt.get("action"),
                    "destination": opt.get("destination")
                }
                for opt in options
            ],
            "timeout_action": params.get("timeout_action", "repeat"),
            "max_retries": params.get("max_retries", 3)
        }

        return SkillResult.ok({
            "ivr_id": f"ivr_{name}",
            "config": ivr_config,
            "status": "created"
        })

    def _normalize_phone(self, phone: str) -> str:
        """Normaliza número"""
        return re.sub(r'\D', '', phone)


# ============================================================
# Webhook Skill
# ============================================================

class WebhookMethod(Enum):
    """Métodos HTTP"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


@skill(
    name="webhook",
    version="1.0.0",
    category=SkillCategory.INTEGRATION,
    description="Integração via webhooks",
    tags=["webhook", "http", "api", "integration"]
)
class WebhookSkill(BaseSkill):
    """
    Skill para integração via webhooks.
    Suporta envio e recebimento de webhooks com retry.
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.default_timeout = self.get_config("timeout", 30)
        self.max_retries = self.get_config("max_retries", 3)
        self.retry_delay = self.get_config("retry_delay", 1.0)
        self._registered_webhooks: Dict[str, Dict] = {}

    async def _execute(self, context: SkillContext, **params) -> SkillResult:
        """Executa ação de webhook"""
        action = params.get("action", "send")

        if action == "send":
            return await self._send_webhook(context, params)
        elif action == "register":
            return await self._register_webhook(context, params)
        elif action == "unregister":
            return await self._unregister_webhook(context, params)
        elif action == "list":
            return await self._list_webhooks(context, params)
        elif action == "verify":
            return await self._verify_signature(context, params)
        else:
            return SkillResult.fail(f"Ação desconhecida: {action}")

    async def _send_webhook(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Envia webhook"""
        url = params.get("url")
        method = params.get("method", "POST")
        payload = params.get("payload", {})

        if not url:
            return SkillResult.fail("'url' é obrigatório")

        headers = params.get("headers", {})
        headers.setdefault("Content-Type", "application/json")
        headers.setdefault("User-Agent", "ConectaPlus-Webhook/1.0")

        # Adicionar timestamp e assinatura
        timestamp = datetime.now().isoformat()
        payload["_timestamp"] = timestamp

        if params.get("sign", True):
            secret = params.get("secret", context.get_config("webhook_secret", ""))
            signature = self._generate_signature(payload, secret)
            headers["X-Webhook-Signature"] = signature
            headers["X-Webhook-Timestamp"] = timestamp

        # Simular envio (em produção, usaria aiohttp/httpx)
        request_id = hashlib.md5(f'{url}{timestamp}'.encode()).hexdigest()[:16]

        return SkillResult.ok({
            "request_id": request_id,
            "url": url,
            "method": method,
            "status_code": 200,
            "response_time_ms": 150,
            "timestamp": timestamp
        })

    async def _register_webhook(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Registra endpoint para receber webhooks"""
        name = params.get("name")
        events = params.get("events", [])
        callback_url = params.get("callback_url")

        if not name or not callback_url:
            return SkillResult.fail("'name' e 'callback_url' são obrigatórios")

        webhook_id = f"wh_{hashlib.md5(f'{name}{callback_url}'.encode()).hexdigest()[:12]}"
        secret = params.get("secret") or hashlib.sha256(
            f'{webhook_id}{datetime.now()}'.encode()
        ).hexdigest()[:32]

        webhook_config = {
            "webhook_id": webhook_id,
            "name": name,
            "callback_url": callback_url,
            "events": events,
            "secret": secret,
            "active": True,
            "created_at": datetime.now().isoformat()
        }

        self._registered_webhooks[webhook_id] = webhook_config

        return SkillResult.ok(webhook_config)

    async def _unregister_webhook(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Remove webhook registrado"""
        webhook_id = params.get("webhook_id")
        if not webhook_id:
            return SkillResult.fail("'webhook_id' é obrigatório")

        if webhook_id in self._registered_webhooks:
            del self._registered_webhooks[webhook_id]
            return SkillResult.ok({
                "webhook_id": webhook_id,
                "status": "removed"
            })

        return SkillResult.fail(f"Webhook não encontrado: {webhook_id}")

    async def _list_webhooks(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Lista webhooks registrados"""
        return SkillResult.ok({
            "webhooks": list(self._registered_webhooks.values()),
            "count": len(self._registered_webhooks)
        })

    async def _verify_signature(
        self,
        context: SkillContext,
        params: Dict
    ) -> SkillResult:
        """Verifica assinatura de webhook recebido"""
        payload = params.get("payload")
        signature = params.get("signature")
        secret = params.get("secret")

        if not all([payload, signature, secret]):
            return SkillResult.fail("'payload', 'signature' e 'secret' são obrigatórios")

        expected_signature = self._generate_signature(payload, secret)
        is_valid = hmac.compare_digest(signature, expected_signature)

        return SkillResult.ok({
            "valid": is_valid,
            "expected": expected_signature if not is_valid else None
        })

    def _generate_signature(self, payload: Any, secret: str) -> str:
        """Gera assinatura HMAC"""
        if isinstance(payload, dict):
            payload = json.dumps(payload, sort_keys=True, separators=(',', ':'))

        return hmac.new(
            secret.encode(),
            payload.encode() if isinstance(payload, str) else payload,
            hashlib.sha256
        ).hexdigest()


# Função de inicialização do módulo
def register_integration_skills():
    """Registra todas as skills de integração"""
    # As skills são registradas automaticamente via decorator
    pass
