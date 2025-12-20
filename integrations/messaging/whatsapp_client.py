"""
Conecta Plus - Cliente WhatsApp Business API
Permite envio de mensagens via WhatsApp Business Cloud API

Dependências:
    pip install requests

Uso:
    from whatsapp_client import WhatsAppClient

    client = WhatsAppClient(
        phone_number_id="123456789",
        access_token="seu_token"
    )

    # Enviar mensagem de texto
    client.send_text("5511999999999", "Olá! Esta é uma mensagem de teste.")

    # Enviar template
    client.send_template("5511999999999", "hello_world")
"""

import logging
import requests
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Tipos de mensagem suportados"""
    TEXT = "text"
    IMAGE = "image"
    DOCUMENT = "document"
    AUDIO = "audio"
    VIDEO = "video"
    STICKER = "sticker"
    LOCATION = "location"
    CONTACTS = "contacts"
    TEMPLATE = "template"
    INTERACTIVE = "interactive"


@dataclass
class MessageStatus:
    """Status de uma mensagem"""
    message_id: str
    status: str
    timestamp: str
    recipient: str
    error: Optional[str] = None


class WhatsAppClient:
    """
    Cliente para WhatsApp Business Cloud API

    Funcionalidades:
    - Envio de mensagens de texto
    - Envio de mídia (imagem, vídeo, áudio, documento)
    - Envio de templates aprovados
    - Envio de mensagens interativas (botões, listas)
    - Envio de localização
    - Webhooks para receber mensagens
    """

    BASE_URL = "https://graph.facebook.com/v18.0"

    def __init__(
        self,
        phone_number_id: str,
        access_token: str,
        business_account_id: str = None
    ):
        """
        Inicializa o cliente WhatsApp

        Args:
            phone_number_id: ID do número de telefone no Meta Business
            access_token: Token de acesso da API
            business_account_id: ID da conta business (opcional)
        """
        self.phone_number_id = phone_number_id
        self.access_token = access_token
        self.business_account_id = business_account_id

        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        })

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Dict = None
    ) -> Dict:
        """
        Faz requisição à API

        Args:
            method: Método HTTP
            endpoint: Endpoint da API
            data: Dados para enviar

        Returns:
            Resposta da API
        """
        url = f"{self.BASE_URL}/{endpoint}"

        try:
            if method == "GET":
                response = self._session.get(url, params=data)
            elif method == "POST":
                response = self._session.post(url, json=data)
            else:
                raise ValueError(f"Método inválido: {method}")

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Erro na requisição: {e}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Resposta: {e.response.text}")
            raise

    def send_text(
        self,
        to: str,
        message: str,
        preview_url: bool = False
    ) -> str:
        """
        Envia mensagem de texto

        Args:
            to: Número do destinatário (formato: 5511999999999)
            message: Texto da mensagem
            preview_url: Gerar preview de URLs

        Returns:
            ID da mensagem enviada
        """
        data = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {
                "preview_url": preview_url,
                "body": message
            }
        }

        response = self._make_request(
            "POST",
            f"{self.phone_number_id}/messages",
            data
        )

        message_id = response.get("messages", [{}])[0].get("id")
        logger.info(f"Mensagem enviada para {to}: {message_id}")

        return message_id

    def send_template(
        self,
        to: str,
        template_name: str,
        language_code: str = "pt_BR",
        components: List[Dict] = None
    ) -> str:
        """
        Envia mensagem usando template aprovado

        Args:
            to: Número do destinatário
            template_name: Nome do template
            language_code: Código do idioma
            components: Componentes do template (header, body, buttons)

        Returns:
            ID da mensagem enviada
        """
        template = {
            "name": template_name,
            "language": {"code": language_code}
        }

        if components:
            template["components"] = components

        data = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "template",
            "template": template
        }

        response = self._make_request(
            "POST",
            f"{self.phone_number_id}/messages",
            data
        )

        message_id = response.get("messages", [{}])[0].get("id")
        logger.info(f"Template '{template_name}' enviado para {to}: {message_id}")

        return message_id

    def send_image(
        self,
        to: str,
        image_url: str = None,
        image_id: str = None,
        caption: str = None
    ) -> str:
        """
        Envia imagem

        Args:
            to: Número do destinatário
            image_url: URL da imagem (ou)
            image_id: ID da mídia já enviada
            caption: Legenda da imagem

        Returns:
            ID da mensagem enviada
        """
        image = {}
        if image_url:
            image["link"] = image_url
        elif image_id:
            image["id"] = image_id

        if caption:
            image["caption"] = caption

        data = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "image",
            "image": image
        }

        response = self._make_request(
            "POST",
            f"{self.phone_number_id}/messages",
            data
        )

        return response.get("messages", [{}])[0].get("id")

    def send_document(
        self,
        to: str,
        document_url: str = None,
        document_id: str = None,
        filename: str = None,
        caption: str = None
    ) -> str:
        """
        Envia documento

        Args:
            to: Número do destinatário
            document_url: URL do documento
            document_id: ID da mídia já enviada
            filename: Nome do arquivo
            caption: Legenda

        Returns:
            ID da mensagem enviada
        """
        document = {}
        if document_url:
            document["link"] = document_url
        elif document_id:
            document["id"] = document_id

        if filename:
            document["filename"] = filename
        if caption:
            document["caption"] = caption

        data = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "document",
            "document": document
        }

        response = self._make_request(
            "POST",
            f"{self.phone_number_id}/messages",
            data
        )

        return response.get("messages", [{}])[0].get("id")

    def send_location(
        self,
        to: str,
        latitude: float,
        longitude: float,
        name: str = None,
        address: str = None
    ) -> str:
        """
        Envia localização

        Args:
            to: Número do destinatário
            latitude: Latitude
            longitude: Longitude
            name: Nome do local
            address: Endereço

        Returns:
            ID da mensagem enviada
        """
        location = {
            "latitude": latitude,
            "longitude": longitude
        }

        if name:
            location["name"] = name
        if address:
            location["address"] = address

        data = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "location",
            "location": location
        }

        response = self._make_request(
            "POST",
            f"{self.phone_number_id}/messages",
            data
        )

        return response.get("messages", [{}])[0].get("id")

    def send_interactive_buttons(
        self,
        to: str,
        body_text: str,
        buttons: List[Dict[str, str]],
        header_text: str = None,
        footer_text: str = None
    ) -> str:
        """
        Envia mensagem interativa com botões

        Args:
            to: Número do destinatário
            body_text: Texto principal
            buttons: Lista de botões [{"id": "btn1", "title": "Opção 1"}, ...]
            header_text: Texto do cabeçalho
            footer_text: Texto do rodapé

        Returns:
            ID da mensagem enviada
        """
        interactive = {
            "type": "button",
            "body": {"text": body_text},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": btn}
                    for btn in buttons[:3]  # Máximo 3 botões
                ]
            }
        }

        if header_text:
            interactive["header"] = {"type": "text", "text": header_text}
        if footer_text:
            interactive["footer"] = {"text": footer_text}

        data = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "interactive",
            "interactive": interactive
        }

        response = self._make_request(
            "POST",
            f"{self.phone_number_id}/messages",
            data
        )

        return response.get("messages", [{}])[0].get("id")

    def send_interactive_list(
        self,
        to: str,
        body_text: str,
        button_text: str,
        sections: List[Dict],
        header_text: str = None,
        footer_text: str = None
    ) -> str:
        """
        Envia mensagem interativa com lista

        Args:
            to: Número do destinatário
            body_text: Texto principal
            button_text: Texto do botão que abre a lista
            sections: Seções da lista
            header_text: Texto do cabeçalho
            footer_text: Texto do rodapé

        Returns:
            ID da mensagem enviada
        """
        interactive = {
            "type": "list",
            "body": {"text": body_text},
            "action": {
                "button": button_text,
                "sections": sections
            }
        }

        if header_text:
            interactive["header"] = {"type": "text", "text": header_text}
        if footer_text:
            interactive["footer"] = {"text": footer_text}

        data = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "interactive",
            "interactive": interactive
        }

        response = self._make_request(
            "POST",
            f"{self.phone_number_id}/messages",
            data
        )

        return response.get("messages", [{}])[0].get("id")

    def mark_as_read(self, message_id: str) -> bool:
        """
        Marca mensagem como lida

        Args:
            message_id: ID da mensagem

        Returns:
            True se marcada com sucesso
        """
        data = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id
        }

        try:
            self._make_request(
                "POST",
                f"{self.phone_number_id}/messages",
                data
            )
            return True
        except Exception:
            return False

    def upload_media(
        self,
        file_path: str,
        mime_type: str
    ) -> str:
        """
        Faz upload de mídia para o WhatsApp

        Args:
            file_path: Caminho do arquivo
            mime_type: Tipo MIME do arquivo

        Returns:
            ID da mídia
        """
        url = f"{self.BASE_URL}/{self.phone_number_id}/media"

        with open(file_path, "rb") as f:
            files = {
                "file": (file_path.split("/")[-1], f, mime_type)
            }
            data = {"messaging_product": "whatsapp"}

            response = requests.post(
                url,
                headers={"Authorization": f"Bearer {self.access_token}"},
                files=files,
                data=data
            )

            response.raise_for_status()
            return response.json().get("id")

    def get_media_url(self, media_id: str) -> str:
        """
        Obtém URL de download de uma mídia

        Args:
            media_id: ID da mídia

        Returns:
            URL para download
        """
        response = self._make_request("GET", media_id)
        return response.get("url")


class WebhookHandler:
    """
    Handler para webhooks do WhatsApp

    Processa notificações de:
    - Mensagens recebidas
    - Status de mensagens enviadas
    - Erros
    """

    def __init__(self, verify_token: str):
        """
        Inicializa o handler

        Args:
            verify_token: Token para verificação do webhook
        """
        self.verify_token = verify_token
        self._message_handlers = []
        self._status_handlers = []

    def verify_webhook(self, mode: str, token: str, challenge: str) -> Optional[str]:
        """
        Verifica webhook (GET request do Facebook)

        Args:
            mode: hub.mode
            token: hub.verify_token
            challenge: hub.challenge

        Returns:
            Challenge se verificado, None se inválido
        """
        if mode == "subscribe" and token == self.verify_token:
            logger.info("Webhook verificado com sucesso")
            return challenge
        logger.warning("Verificação de webhook falhou")
        return None

    def process_webhook(self, payload: Dict) -> List[Dict]:
        """
        Processa payload do webhook

        Args:
            payload: Dados recebidos do webhook

        Returns:
            Lista de eventos processados
        """
        events = []

        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                if change.get("field") != "messages":
                    continue

                value = change.get("value", {})

                # Processar mensagens recebidas
                for message in value.get("messages", []):
                    event = self._process_message(message, value)
                    events.append(event)
                    self._notify_message_handlers(event)

                # Processar status de mensagens
                for status in value.get("statuses", []):
                    event = self._process_status(status)
                    events.append(event)
                    self._notify_status_handlers(event)

        return events

    def _process_message(self, message: Dict, value: Dict) -> Dict:
        """Processa mensagem recebida"""
        contact = value.get("contacts", [{}])[0]

        return {
            "type": "message",
            "message_id": message.get("id"),
            "from": message.get("from"),
            "timestamp": message.get("timestamp"),
            "message_type": message.get("type"),
            "content": message.get(message.get("type", "text"), {}),
            "contact_name": contact.get("profile", {}).get("name"),
            "context": message.get("context")  # Resposta a mensagem
        }

    def _process_status(self, status: Dict) -> Dict:
        """Processa status de mensagem"""
        return {
            "type": "status",
            "message_id": status.get("id"),
            "status": status.get("status"),
            "timestamp": status.get("timestamp"),
            "recipient": status.get("recipient_id"),
            "error": status.get("errors", [{}])[0] if status.get("errors") else None
        }

    def on_message(self, handler):
        """Decorator para handlers de mensagens"""
        self._message_handlers.append(handler)
        return handler

    def on_status(self, handler):
        """Decorator para handlers de status"""
        self._status_handlers.append(handler)
        return handler

    def _notify_message_handlers(self, event: Dict):
        for handler in self._message_handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Erro no handler de mensagem: {e}")

    def _notify_status_handlers(self, event: Dict):
        for handler in self._status_handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Erro no handler de status: {e}")


# Exemplo de uso
if __name__ == "__main__":
    print("Cliente WhatsApp Business API")
    print("Uso:")
    print("  client = WhatsAppClient(phone_number_id='123', access_token='token')")
    print("  client.send_text('5511999999999', 'Olá!')")
