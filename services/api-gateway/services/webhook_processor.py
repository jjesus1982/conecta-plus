"""
Conecta Plus - Processador de Webhooks Cora
Processa eventos recebidos do Banco Cora em tempo real
"""

import hmac
import hashlib
from typing import Dict, Optional, Any
from datetime import datetime
from decimal import Decimal
from uuid import UUID
import logging

from sqlalchemy.orm import Session

from repositories.cora import (
    CobrancaCoraRepository,
    TransacaoCoraRepository,
    WebhookCoraRepository,
    ContaCoraRepository,
)

# Services
from services.notification_service import notification_service

# Configurar logger
logger = logging.getLogger("webhook_processor")


class WebhookProcessor:
    """
    Processador de webhooks do Banco Cora

    Responsável por:
    - Validar assinatura HMAC-SHA256
    - Processar eventos
    - Atualizar status de cobranças
    - Registrar transações
    - Retry automático em caso de falha
    """

    def __init__(self, db: Session):
        self.db = db
        self.cobranca_repo = CobrancaCoraRepository(db)
        self.transacao_repo = TransacaoCoraRepository(db)
        self.webhook_repo = WebhookCoraRepository(db)
        self.conta_repo = ContaCoraRepository(db)

    def validar_assinatura(
        self,
        payload: bytes,
        signature: str,
        webhook_secret: str
    ) -> bool:
        """
        Valida assinatura HMAC-SHA256 do webhook

        Args:
            payload: Body raw do webhook
            signature: Assinatura recebida no header X-Cora-Signature
            webhook_secret: Secret configurado para webhooks

        Returns:
            True se válida, False caso contrário
        """
        if not webhook_secret or not signature:
            return False

        # Calcula assinatura esperada
        expected_signature = hmac.new(
            webhook_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()

        # Compara de forma segura (timing-safe)
        return hmac.compare_digest(expected_signature, signature)

    def processar_webhook(
        self,
        event_type: str,
        event_data: Dict[str, Any],
        webhook_id: UUID
    ) -> Dict[str, Any]:
        """
        Processa webhook baseado no tipo de evento

        Args:
            event_type: Tipo do evento (invoice.paid, pix.received, etc)
            event_data: Dados do evento
            webhook_id: ID do webhook registrado

        Returns:
            Resultado do processamento
        """
        logger.info(f"Processando webhook {webhook_id}: {event_type}")

        try:
            # Roteamento por tipo de evento
            if event_type == "invoice.paid":
                return self._processar_invoice_paid(event_data, webhook_id)

            elif event_type == "invoice.overdue":
                return self._processar_invoice_overdue(event_data, webhook_id)

            elif event_type == "invoice.cancelled":
                return self._processar_invoice_cancelled(event_data, webhook_id)

            elif event_type == "pix.received":
                return self._processar_pix_received(event_data, webhook_id)

            elif event_type == "payment.created":
                return self._processar_payment_created(event_data, webhook_id)

            elif event_type == "payment.failed":
                return self._processar_payment_failed(event_data, webhook_id)

            elif event_type == "transfer.completed":
                return self._processar_transfer_completed(event_data, webhook_id)

            elif event_type == "transfer.failed":
                return self._processar_transfer_failed(event_data, webhook_id)

            else:
                logger.warning(f"Tipo de evento desconhecido: {event_type}")
                return {
                    "status": "ignored",
                    "message": f"Tipo de evento não tratado: {event_type}"
                }

        except Exception as e:
            logger.error(f"Erro ao processar webhook {webhook_id}: {str(e)}")
            raise

    def _processar_invoice_paid(
        self,
        event_data: Dict[str, Any],
        webhook_id: UUID
    ) -> Dict[str, Any]:
        """
        Processa evento de boleto pago

        Ações:
        1. Atualiza status da cobrança para 'pago'
        2. Registra valor e data de pagamento
        3. Cria pagamento vinculado ao boleto interno (se houver)
        4. Envia notificação de pagamento recebido
        """
        invoice_id = event_data.get("id")
        paid_amount = event_data.get("paid_amount", 0) / 100  # Centavos para reais
        paid_at_str = event_data.get("paid_at")

        if not invoice_id:
            raise ValueError("invoice.paid sem ID da cobrança")

        # Busca cobrança
        cobranca = self.cobranca_repo.get_by_invoice_id(invoice_id)

        if not cobranca:
            logger.warning(f"Cobrança não encontrada para invoice_id: {invoice_id}")
            return {
                "status": "not_found",
                "message": f"Cobrança {invoice_id} não encontrada no sistema"
            }

        # Converte data de pagamento
        paid_at = None
        if paid_at_str:
            try:
                paid_at = datetime.fromisoformat(paid_at_str.replace("Z", "+00:00"))
            except:
                paid_at = datetime.utcnow()

        # Atualiza status da cobrança
        self.cobranca_repo.update_status(
            cobranca_id=cobranca.id,
            status="pago",
            valor_pago=Decimal(str(paid_amount)),
            data_pagamento=paid_at or datetime.utcnow()
        )

        # TODO: Criar pagamento vinculado ao boleto interno
        # if cobranca.boleto_id:
        #     self._criar_pagamento_boleto(cobranca, paid_amount, paid_at)

        # Envia notificação de pagamento recebido
        try:
            # TODO: Buscar emails dos responsáveis pelo condomínio
            destinatarios = ["admin@condominio.com"]  # Placeholder

            notification_service.notificar_pagamento_recebido(
                destinatarios=destinatarios,
                valor=paid_amount,
                data_pagamento=paid_at.isoformat() if paid_at else datetime.utcnow().isoformat(),
                forma_pagamento="Boleto/PIX"
            )
        except Exception as e:
            logger.warning(f"Erro ao enviar notificação: {str(e)}")

        self.db.commit()

        logger.info(f"Cobrança {invoice_id} marcada como paga: R$ {paid_amount}")

        return {
            "status": "success",
            "cobranca_id": str(cobranca.id),
            "valor_pago": paid_amount,
            "data_pagamento": paid_at.isoformat() if paid_at else None
        }

    def _processar_invoice_overdue(
        self,
        event_data: Dict[str, Any],
        webhook_id: UUID
    ) -> Dict[str, Any]:
        """
        Processa evento de boleto vencido

        Ações:
        1. Atualiza status da cobrança para 'vencido'
        2. Envia notificação de cobrança vencida
        3. Ativa fluxo de cobrança automática (se configurado)
        """
        invoice_id = event_data.get("id")

        if not invoice_id:
            raise ValueError("invoice.overdue sem ID da cobrança")

        # Busca cobrança
        cobranca = self.cobranca_repo.get_by_invoice_id(invoice_id)

        if not cobranca:
            logger.warning(f"Cobrança não encontrada para invoice_id: {invoice_id}")
            return {
                "status": "not_found",
                "message": f"Cobrança {invoice_id} não encontrada"
            }

        # Atualiza status
        self.cobranca_repo.update_status(
            cobranca_id=cobranca.id,
            status="vencido"
        )

        # Envia notificação de vencimento
        try:
            # TODO: Buscar emails dos responsáveis
            destinatarios = ["admin@condominio.com"]  # Placeholder

            notification_service.notificar_boleto_vencido(
                destinatarios=destinatarios,
                valor=float(cobranca.valor),
                vencimento=cobranca.data_vencimento.isoformat() if cobranca.data_vencimento else "N/A",
                nosso_numero=cobranca.nosso_numero or "N/A"
            )
        except Exception as e:
            logger.warning(f"Erro ao enviar notificação: {str(e)}")

        # TODO: Ativar fluxo de cobrança
        # self._ativar_fluxo_cobranca(cobranca)

        self.db.commit()

        logger.info(f"Cobrança {invoice_id} marcada como vencida")

        return {
            "status": "success",
            "cobranca_id": str(cobranca.id),
            "acao": "marcada_como_vencida"
        }

    def _processar_invoice_cancelled(
        self,
        event_data: Dict[str, Any],
        webhook_id: UUID
    ) -> Dict[str, Any]:
        """
        Processa evento de boleto cancelado

        Ações:
        1. Atualiza status da cobrança para 'cancelado'
        2. Registra motivo do cancelamento
        3. Envia notificação (se necessário)
        """
        invoice_id = event_data.get("id")
        cancellation_reason = event_data.get("cancellation_reason", "Não especificado")

        if not invoice_id:
            raise ValueError("invoice.cancelled sem ID da cobrança")

        # Busca cobrança
        cobranca = self.cobranca_repo.get_by_invoice_id(invoice_id)

        if not cobranca:
            logger.warning(f"Cobrança não encontrada para invoice_id: {invoice_id}")
            return {
                "status": "not_found",
                "message": f"Cobrança {invoice_id} não encontrada"
            }

        # Atualiza status
        self.cobranca_repo.update_status(
            cobranca_id=cobranca.id,
            status="cancelado",
            data_cancelamento=datetime.utcnow()
        )

        self.db.commit()

        logger.info(f"Cobrança {invoice_id} cancelada: {cancellation_reason}")

        return {
            "status": "success",
            "cobranca_id": str(cobranca.id),
            "motivo": cancellation_reason
        }

    def _processar_pix_received(
        self,
        event_data: Dict[str, Any],
        webhook_id: UUID
    ) -> Dict[str, Any]:
        """
        Processa evento de PIX recebido

        Ações:
        1. Registra transação de crédito
        2. Se tiver txid, tenta vincular a cobrança
        3. Se não tiver, marca para conciliação manual
        4. Envia notificação de PIX recebido
        """
        txid = event_data.get("txid")
        amount = event_data.get("amount", 0) / 100
        end_to_end_id = event_data.get("end_to_end_id")
        payer_name = event_data.get("payer", {}).get("name")
        payer_document = event_data.get("payer", {}).get("document")
        transaction_date = event_data.get("transaction_date")

        # Converte data
        data_transacao = None
        if transaction_date:
            try:
                data_transacao = datetime.fromisoformat(transaction_date.replace("Z", "+00:00")).date()
            except:
                data_transacao = datetime.utcnow().date()

        # Busca cobrança por txid (se houver)
        cobranca = None
        if txid:
            cobranca = self.cobranca_repo.get_by_pix_txid(txid)

            if cobranca:
                # Atualiza cobrança como paga
                self.cobranca_repo.update_status(
                    cobranca_id=cobranca.id,
                    status="pago",
                    valor_pago=Decimal(str(amount)),
                    data_pagamento=datetime.utcnow()
                )

        # TODO: Registrar transação
        # Aqui precisamos do conta_cora_id, que não vem no webhook
        # Precisaria buscar pela conta que tem esse txid cadastrado
        # Por ora, só logamos

        # Envia notificação de PIX recebido
        try:
            # TODO: Buscar emails dos responsáveis
            destinatarios = ["admin@condominio.com"]  # Placeholder

            notification_service.notificar_pix_recebido(
                destinatarios=destinatarios,
                valor=amount,
                pagador_nome=payer_name or "Não identificado",
                data=datetime.utcnow().isoformat()
            )
        except Exception as e:
            logger.warning(f"Erro ao enviar notificação: {str(e)}")

        self.db.commit()

        logger.info(f"PIX recebido: R$ {amount} - txid: {txid} - e2e: {end_to_end_id}")

        return {
            "status": "success",
            "valor": amount,
            "txid": txid,
            "cobranca_vinculada": str(cobranca.id) if cobranca else None,
            "requer_conciliacao": cobranca is None
        }

    def _processar_payment_created(
        self,
        event_data: Dict[str, Any],
        webhook_id: UUID
    ) -> Dict[str, Any]:
        """
        Processa evento de pagamento criado

        Registra que um pagamento foi iniciado
        """
        payment_id = event_data.get("id")
        payment_type = event_data.get("payment_type")
        amount = event_data.get("amount", 0) / 100

        logger.info(f"Pagamento criado: {payment_id} - Tipo: {payment_type} - Valor: R$ {amount}")

        return {
            "status": "success",
            "payment_id": payment_id,
            "payment_type": payment_type,
            "amount": amount
        }

    def _processar_payment_failed(
        self,
        event_data: Dict[str, Any],
        webhook_id: UUID
    ) -> Dict[str, Any]:
        """
        Processa evento de pagamento falho

        Registra falha e envia alerta
        """
        payment_id = event_data.get("id")
        failure_reason = event_data.get("failure_reason", "Não especificado")
        error_code = event_data.get("error_code")

        logger.warning(f"Pagamento falhou: {payment_id} - Motivo: {failure_reason} - Código: {error_code}")

        # TODO: Enviar alerta
        # self._enviar_alerta_pagamento_falho(payment_id, failure_reason)

        return {
            "status": "success",
            "payment_id": payment_id,
            "failure_reason": failure_reason,
            "error_code": error_code
        }

    def _processar_transfer_completed(
        self,
        event_data: Dict[str, Any],
        webhook_id: UUID
    ) -> Dict[str, Any]:
        """
        Processa evento de transferência concluída

        Registra transferência bem-sucedida
        """
        transfer_id = event_data.get("id")
        amount = event_data.get("amount", 0) / 100
        beneficiary_name = event_data.get("beneficiary", {}).get("name")

        logger.info(f"Transferência concluída: {transfer_id} - Valor: R$ {amount} - Beneficiário: {beneficiary_name}")

        return {
            "status": "success",
            "transfer_id": transfer_id,
            "amount": amount,
            "beneficiary": beneficiary_name
        }

    def _processar_transfer_failed(
        self,
        event_data: Dict[str, Any],
        webhook_id: UUID
    ) -> Dict[str, Any]:
        """
        Processa evento de transferência falha

        Registra falha e envia alerta
        """
        transfer_id = event_data.get("id")
        failure_reason = event_data.get("failure_reason", "Não especificado")

        logger.warning(f"Transferência falhou: {transfer_id} - Motivo: {failure_reason}")

        # TODO: Enviar alerta
        # self._enviar_alerta_transferencia_falha(transfer_id, failure_reason)

        return {
            "status": "success",
            "transfer_id": transfer_id,
            "failure_reason": failure_reason
        }

    def retry_webhook(
        self,
        webhook_id: UUID,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Tenta reprocessar webhook que falhou

        Args:
            webhook_id: ID do webhook
            max_retries: Número máximo de tentativas

        Returns:
            Resultado do reprocessamento
        """
        # Busca webhook
        webhook = self.db.query(
            self.webhook_repo.model_class
        ).filter_by(id=webhook_id).first()

        if not webhook:
            raise ValueError(f"Webhook {webhook_id} não encontrado")

        if webhook.tentativas_processamento >= max_retries:
            logger.error(f"Webhook {webhook_id} atingiu limite de tentativas ({max_retries})")
            return {
                "status": "max_retries_exceeded",
                "tentativas": webhook.tentativas_processamento
            }

        # Tenta processar novamente
        try:
            resultado = self.processar_webhook(
                event_type=webhook.event_type,
                event_data=webhook.body.get("data", {}),
                webhook_id=webhook.id
            )

            # Marca como processado
            self.webhook_repo.marcar_processado(
                webhook_id=webhook.id,
                resultado=resultado
            )

            self.db.commit()

            logger.info(f"Webhook {webhook_id} reprocessado com sucesso")

            return resultado

        except Exception as e:
            # Incrementa tentativas
            webhook.tentativas_processamento += 1
            self.db.commit()

            logger.error(f"Erro ao reprocessar webhook {webhook_id}: {str(e)}")

            raise


# Instância global (singleton pattern)
_processor_instance = None


def get_webhook_processor(db: Session) -> WebhookProcessor:
    """Retorna instância do processador de webhooks"""
    return WebhookProcessor(db)
