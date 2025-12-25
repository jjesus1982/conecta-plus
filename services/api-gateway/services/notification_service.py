"""
Conecta Plus - Serviço de Notificações
Envia notificações por múltiplos canais
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger("notification_service")


class TipoNotificacao(str, Enum):
    """Tipos de notificação"""
    PAGAMENTO_RECEBIDO = "pagamento_recebido"
    BOLETO_VENCIDO = "boleto_vencido"
    COBRANCA_CANCELADA = "cobranca_cancelada"
    PIX_RECEBIDO = "pix_recebido"
    TRANSFERENCIA_CONCLUIDA = "transferencia_concluida"
    TRANSFERENCIA_FALHOU = "transferencia_falhou"
    PAGAMENTO_FALHOU = "pagamento_falhou"
    WEBHOOK_ERRO = "webhook_erro"


class CanalNotificacao(str, Enum):
    """Canais de notificação"""
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    WEBSOCKET = "websocket"
    WHATSAPP = "whatsapp"


class NotificationService:
    """
    Serviço de notificações multi-canal

    Suporta:
    - Email
    - SMS
    - Push notifications
    - WebSocket (tempo real)
    - WhatsApp
    """

    def __init__(self):
        self.enabled_channels = {
            CanalNotificacao.EMAIL: True,
            CanalNotificacao.SMS: False,  # Requer configuração
            CanalNotificacao.PUSH: False,  # Requer configuração
            CanalNotificacao.WEBSOCKET: True,
            CanalNotificacao.WHATSAPP: False,  # Requer configuração
        }

    def enviar(
        self,
        tipo: TipoNotificacao,
        destinatarios: List[str],
        dados: Dict[str, Any],
        canais: Optional[List[CanalNotificacao]] = None
    ) -> Dict[str, bool]:
        """
        Envia notificação por múltiplos canais

        Args:
            tipo: Tipo da notificação
            destinatarios: Lista de destinatários (emails, telefones, user_ids)
            dados: Dados da notificação
            canais: Canais a usar (se None, usa todos habilitados)

        Returns:
            Dict com status de envio por canal
        """
        if canais is None:
            canais = [c for c, enabled in self.enabled_channels.items() if enabled]

        resultado = {}

        for canal in canais:
            if not self.enabled_channels.get(canal, False):
                logger.warning(f"Canal {canal} não está habilitado")
                resultado[canal.value] = False
                continue

            try:
                if canal == CanalNotificacao.EMAIL:
                    resultado[canal.value] = self._enviar_email(tipo, destinatarios, dados)

                elif canal == CanalNotificacao.SMS:
                    resultado[canal.value] = self._enviar_sms(tipo, destinatarios, dados)

                elif canal == CanalNotificacao.PUSH:
                    resultado[canal.value] = self._enviar_push(tipo, destinatarios, dados)

                elif canal == CanalNotificacao.WEBSOCKET:
                    resultado[canal.value] = self._enviar_websocket(tipo, destinatarios, dados)

                elif canal == CanalNotificacao.WHATSAPP:
                    resultado[canal.value] = self._enviar_whatsapp(tipo, destinatarios, dados)

            except Exception as e:
                logger.error(f"Erro ao enviar notificação via {canal}: {str(e)}")
                resultado[canal.value] = False

        return resultado

    def _enviar_email(
        self,
        tipo: TipoNotificacao,
        destinatarios: List[str],
        dados: Dict[str, Any]
    ) -> bool:
        """Envia notificação por email"""
        logger.info(f"[EMAIL] {tipo} -> {destinatarios}")

        # TODO: Implementar envio de email real
        # - Usar SMTP ou serviço de email (SendGrid, AWS SES, etc)
        # - Templates HTML
        # - Personalização

        template = self._get_email_template(tipo, dados)

        logger.info(f"Email template: {template['subject']}")

        # Placeholder: simula envio bem-sucedido
        return True

    def _enviar_sms(
        self,
        tipo: TipoNotificacao,
        destinatarios: List[str],
        dados: Dict[str, Any]
    ) -> bool:
        """Envia notificação por SMS"""
        logger.info(f"[SMS] {tipo} -> {destinatarios}")

        # TODO: Implementar envio de SMS
        # - Integração com Twilio, AWS SNS, etc
        # - Validação de número de telefone
        # - Otimização de custo (apenas notificações críticas)

        mensagem = self._get_sms_mensagem(tipo, dados)

        logger.info(f"SMS: {mensagem}")

        return True

    def _enviar_push(
        self,
        tipo: TipoNotificacao,
        destinatarios: List[str],
        dados: Dict[str, Any]
    ) -> bool:
        """Envia push notification"""
        logger.info(f"[PUSH] {tipo} -> {destinatarios}")

        # TODO: Implementar push notifications
        # - Firebase Cloud Messaging (FCM)
        # - Apple Push Notification Service (APNs)
        # - Device tokens management

        return True

    def _enviar_websocket(
        self,
        tipo: TipoNotificacao,
        destinatarios: List[str],
        dados: Dict[str, Any]
    ) -> bool:
        """Envia notificação por WebSocket (tempo real)"""
        logger.info(f"[WEBSOCKET] {tipo} -> {destinatarios}")

        # TODO: Implementar envio via WebSocket
        # - Usar websocket_manager existente
        # - Broadcast para usuários conectados

        try:
            from websocket_manager import manager as ws_manager

            # Prepara mensagem
            mensagem = {
                "type": "notification",
                "notification_type": tipo.value,
                "timestamp": datetime.utcnow().isoformat(),
                "data": dados
            }

            # Envia para cada destinatário conectado
            for user_id in destinatarios:
                # ws_manager.send_personal_message(mensagem, user_id)
                pass  # Implementar quando websocket_manager suportar

            return True

        except Exception as e:
            logger.error(f"Erro ao enviar via WebSocket: {str(e)}")
            return False

    def _enviar_whatsapp(
        self,
        tipo: TipoNotificacao,
        destinatarios: List[str],
        dados: Dict[str, Any]
    ) -> bool:
        """Envia notificação por WhatsApp"""
        logger.info(f"[WHATSAPP] {tipo} -> {destinatarios}")

        # TODO: Implementar WhatsApp Business API
        # - Twilio WhatsApp
        # - Meta WhatsApp Business API
        # - Templates aprovados

        return True

    def _get_email_template(
        self,
        tipo: TipoNotificacao,
        dados: Dict[str, Any]
    ) -> Dict[str, str]:
        """Retorna template de email para cada tipo"""

        templates = {
            TipoNotificacao.PAGAMENTO_RECEBIDO: {
                "subject": "Pagamento Recebido - Condomínio",
                "body": f"""
                <h2>Pagamento Recebido</h2>
                <p>Informamos que recebemos o pagamento:</p>
                <ul>
                    <li>Valor: R$ {dados.get('valor', 0):.2f}</li>
                    <li>Data: {dados.get('data_pagamento', 'N/A')}</li>
                    <li>Forma: {dados.get('forma_pagamento', 'N/A')}</li>
                </ul>
                <p>O pagamento foi processado automaticamente.</p>
                """
            },

            TipoNotificacao.BOLETO_VENCIDO: {
                "subject": "Cobrança Vencida - Condomínio",
                "body": f"""
                <h2>Cobrança Vencida</h2>
                <p>A cobrança a seguir está vencida:</p>
                <ul>
                    <li>Valor: R$ {dados.get('valor', 0):.2f}</li>
                    <li>Vencimento: {dados.get('vencimento', 'N/A')}</li>
                    <li>Nosso Número: {dados.get('nosso_numero', 'N/A')}</li>
                </ul>
                <p>Por favor, regularize sua situação o quanto antes.</p>
                """
            },

            TipoNotificacao.PIX_RECEBIDO: {
                "subject": "PIX Recebido - Condomínio",
                "body": f"""
                <h2>PIX Recebido</h2>
                <p>Recebemos um pagamento via PIX:</p>
                <ul>
                    <li>Valor: R$ {dados.get('valor', 0):.2f}</li>
                    <li>Pagador: {dados.get('pagador_nome', 'N/A')}</li>
                    <li>Data: {dados.get('data', 'N/A')}</li>
                </ul>
                """
            },
        }

        return templates.get(tipo, {
            "subject": f"Notificação - {tipo.value}",
            "body": f"<p>{dados}</p>"
        })

    def _get_sms_mensagem(
        self,
        tipo: TipoNotificacao,
        dados: Dict[str, Any]
    ) -> str:
        """Retorna mensagem SMS curta para cada tipo"""

        mensagens = {
            TipoNotificacao.PAGAMENTO_RECEBIDO: f"Pagamento recebido: R$ {dados.get('valor', 0):.2f}. Obrigado!",
            TipoNotificacao.BOLETO_VENCIDO: f"Cobrança vencida: R$ {dados.get('valor', 0):.2f}. Regularize.",
            TipoNotificacao.PIX_RECEBIDO: f"PIX recebido: R$ {dados.get('valor', 0):.2f}",
        }

        return mensagens.get(tipo, f"Notificação: {tipo.value}")

    def notificar_pagamento_recebido(
        self,
        destinatarios: List[str],
        valor: float,
        data_pagamento: str,
        forma_pagamento: str = "Boleto"
    ):
        """Helper para notificar pagamento recebido"""
        return self.enviar(
            tipo=TipoNotificacao.PAGAMENTO_RECEBIDO,
            destinatarios=destinatarios,
            dados={
                "valor": valor,
                "data_pagamento": data_pagamento,
                "forma_pagamento": forma_pagamento
            }
        )

    def notificar_boleto_vencido(
        self,
        destinatarios: List[str],
        valor: float,
        vencimento: str,
        nosso_numero: str
    ):
        """Helper para notificar boleto vencido"""
        return self.enviar(
            tipo=TipoNotificacao.BOLETO_VENCIDO,
            destinatarios=destinatarios,
            dados={
                "valor": valor,
                "vencimento": vencimento,
                "nosso_numero": nosso_numero
            }
        )

    def notificar_pix_recebido(
        self,
        destinatarios: List[str],
        valor: float,
        pagador_nome: str,
        data: str
    ):
        """Helper para notificar PIX recebido"""
        return self.enviar(
            tipo=TipoNotificacao.PIX_RECEBIDO,
            destinatarios=destinatarios,
            dados={
                "valor": valor,
                "pagador_nome": pagador_nome,
                "data": data
            }
        )


# Instância singleton
notification_service = NotificationService()
