"""
Conecta Plus - Repositórios: Integração Banco Cora
Data Access Layer para modelos Cora
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID
from decimal import Decimal
from sqlalchemy import select, update, delete, and_, or_, func, desc
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from models.cora import (
    ContaCora,
    TransacaoCora,
    CobrancaCora,
    WebhookCora,
    CoraToken,
    SaldoCora,
    CoraSyncLog,
    TipoTransacaoCora,
    TipoCobrancaCora,
    StatusCobrancaCora,
    TipoSyncCora,
    StatusSyncCora,
    AmbienteCora,
    VersaoAPICora,
)
from services.crypto_service import crypto_service


# ==================== CONTA CORA REPOSITORY ====================

class ContaCoraRepository:
    """Repositório para gerenciar contas Cora"""

    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, conta_id: UUID) -> Optional[ContaCora]:
        """
        Busca conta por ID

        Args:
            conta_id: ID da conta

        Returns:
            Conta Cora ou None
        """
        return self.session.query(ContaCora).filter(
            ContaCora.id == conta_id
        ).first()

    def get_by_condominio(self, condominio_id: UUID, ativa: bool = True) -> Optional[ContaCora]:
        """
        Busca conta ativa de um condomínio

        Args:
            condominio_id: ID do condomínio
            ativa: Filtrar apenas contas ativas

        Returns:
            Conta Cora ou None
        """
        query = self.session.query(ContaCora).filter(
            ContaCora.condominio_id == condominio_id
        )

        if ativa:
            query = query.filter(ContaCora.ativa == True)

        return query.first()

    def get_by_account_id(self, cora_account_id: str) -> Optional[ContaCora]:
        """
        Busca conta por account ID Cora

        Args:
            cora_account_id: ID da conta no Cora

        Returns:
            Conta Cora ou None
        """
        return self.session.query(ContaCora).filter(
            ContaCora.cora_account_id == cora_account_id
        ).first()

    def create(
        self,
        condominio_id: UUID,
        cora_account_id: str,
        cora_document: str,
        client_id: str,
        client_secret: str,
        webhook_secret: str,
        ambiente: str = "production",
        api_version: str = "v2",
        **kwargs
    ) -> ContaCora:
        """
        Cria nova conta Cora

        Args:
            condominio_id: ID do condomínio
            cora_account_id: ID da conta no Cora
            cora_document: CNPJ do condomínio
            client_id: Client ID OAuth2
            client_secret: Client Secret OAuth2
            webhook_secret: Secret para validação de webhooks
            ambiente: production ou sandbox
            api_version: v1 ou v2
            **kwargs: Campos adicionais

        Returns:
            Conta Cora criada
        """
        # Criptografa credenciais
        client_id_enc, client_id_salt = crypto_service.criptografar(client_id)
        client_secret_enc, client_secret_salt = crypto_service.criptografar(client_secret)
        webhook_secret_enc, webhook_secret_salt = crypto_service.criptografar(webhook_secret)

        conta = ContaCora(
            condominio_id=condominio_id,
            cora_account_id=cora_account_id,
            cora_document=cora_document,
            ambiente=AmbienteCora(ambiente),
            api_version=VersaoAPICora(api_version),
            client_id_encrypted=client_id_enc,
            client_id_salt=client_id_salt,
            client_secret_encrypted=client_secret_enc,
            client_secret_salt=client_secret_salt,
            webhook_secret_encrypted=webhook_secret_enc,
            webhook_secret_salt=webhook_secret_salt,
            **kwargs
        )

        self.session.add(conta)
        self.session.flush()
        return conta

    def update_status(self, conta_id: UUID, ativa: bool) -> Optional[ContaCora]:
        """
        Ativa/desativa uma conta

        Args:
            conta_id: ID da conta
            ativa: True para ativar, False para desativar

        Returns:
            Conta atualizada ou None
        """
        conta = self.get_by_id(conta_id)
        if conta:
            conta.ativa = ativa
            self.session.flush()
        return conta

    def get_credentials(self, conta_id: UUID) -> Optional[Dict[str, str]]:
        """
        Obtém credenciais descriptografadas da conta

        Args:
            conta_id: ID da conta

        Returns:
            Dict com client_id, client_secret, webhook_secret ou None
        """
        conta = self.get_by_id(conta_id)
        if not conta:
            return None

        try:
            return {
                "client_id": crypto_service.descriptografar(
                    conta.client_id_encrypted,
                    conta.client_id_salt
                ),
                "client_secret": crypto_service.descriptografar(
                    conta.client_secret_encrypted,
                    conta.client_secret_salt
                ),
                "webhook_secret": crypto_service.descriptografar(
                    conta.webhook_secret_encrypted,
                    conta.webhook_secret_salt
                ) if conta.webhook_secret_encrypted else None,
            }
        except Exception:
            return None

    def list_all(self, ativa: Optional[bool] = None) -> List[ContaCora]:
        """
        Lista todas as contas

        Args:
            ativa: Filtrar por status

        Returns:
            Lista de contas
        """
        query = self.session.query(ContaCora)

        if ativa is not None:
            query = query.filter(ContaCora.ativa == ativa)

        return query.all()


# ==================== TRANSACAO CORA REPOSITORY ====================

class TransacaoCoraRepository:
    """Repositório para gerenciar transações do extrato Cora"""

    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, transacao_id: UUID) -> Optional[TransacaoCora]:
        """Busca transação por ID"""
        return self.session.query(TransacaoCora).filter(
            TransacaoCora.id == transacao_id
        ).first()

    def get_by_cora_id(self, cora_transaction_id: str) -> Optional[TransacaoCora]:
        """Busca transação por ID Cora"""
        return self.session.query(TransacaoCora).filter(
            TransacaoCora.cora_transaction_id == cora_transaction_id
        ).first()

    def list(
        self,
        conta_cora_id: Optional[UUID] = None,
        condominio_id: Optional[UUID] = None,
        data_inicio: Optional[str] = None,
        data_fim: Optional[str] = None,
        tipo: Optional[str] = None,
        conciliado: Optional[bool] = None,
        page: int = 1,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Lista transações com filtros e paginação

        Returns:
            Dict com items, total, page, per_page
        """
        query = self.session.query(TransacaoCora)

        # Filtros
        if conta_cora_id:
            query = query.filter(TransacaoCora.conta_cora_id == conta_cora_id)

        if condominio_id:
            query = query.filter(TransacaoCora.condominio_id == condominio_id)

        if data_inicio:
            query = query.filter(TransacaoCora.data_transacao >= data_inicio)

        if data_fim:
            query = query.filter(TransacaoCora.data_transacao <= data_fim)

        if tipo:
            query = query.filter(TransacaoCora.tipo == TipoTransacaoCora(tipo))

        if conciliado is not None:
            query = query.filter(TransacaoCora.conciliado == conciliado)

        # Total
        total = query.count()

        # Paginação
        offset = (page - 1) * limit
        items = query.order_by(desc(TransacaoCora.data_transacao)).offset(offset).limit(limit).all()

        return {
            "items": items,
            "total": total,
            "page": page,
            "per_page": limit
        }

    def create(
        self,
        conta_cora_id: UUID,
        condominio_id: UUID,
        cora_transaction_id: str,
        data_transacao: str,
        tipo: str,
        valor: Decimal,
        descricao: str,
        **kwargs
    ) -> TransacaoCora:
        """
        Cria nova transação

        Verifica se já existe para evitar duplicatas
        """
        # Verifica se já existe
        existing = self.get_by_cora_id(cora_transaction_id)
        if existing:
            return existing

        transacao = TransacaoCora(
            conta_cora_id=conta_cora_id,
            condominio_id=condominio_id,
            cora_transaction_id=cora_transaction_id,
            data_transacao=data_transacao,
            tipo=TipoTransacaoCora(tipo),
            valor=valor,
            descricao=descricao,
            **kwargs
        )

        self.session.add(transacao)
        self.session.flush()
        return transacao

    def conciliar(
        self,
        transacao_id: UUID,
        boleto_id: Optional[UUID] = None,
        pagamento_id: Optional[UUID] = None,
        lancamento_id: Optional[UUID] = None,
        confianca_match: Optional[Decimal] = None,
        conciliado_por: Optional[UUID] = None,
        manual: bool = False
    ) -> Optional[TransacaoCora]:
        """
        Marca transação como conciliada

        Args:
            transacao_id: ID da transação
            boleto_id: ID do boleto conciliado
            pagamento_id: ID do pagamento conciliado
            lancamento_id: ID do lançamento conciliado
            confianca_match: Percentual de confiança (0-100)
            conciliado_por: ID do usuário que conciliou
            manual: Se a conciliação foi manual

        Returns:
            Transação atualizada ou None
        """
        transacao = self.get_by_id(transacao_id)
        if not transacao:
            return None

        transacao.conciliado = True
        transacao.boleto_id = boleto_id
        transacao.pagamento_id = pagamento_id
        transacao.lancamento_id = lancamento_id
        transacao.confianca_match = confianca_match
        transacao.conciliado_em = datetime.utcnow()
        transacao.conciliado_por = conciliado_por
        transacao.conciliacao_manual = manual

        self.session.flush()
        return transacao

    def get_nao_conciliadas(
        self,
        conta_cora_id: Optional[UUID] = None,
        tipo: str = "C",  # Apenas créditos por padrão
        limit: int = 100
    ) -> List[TransacaoCora]:
        """
        Lista transações não conciliadas

        Args:
            conta_cora_id: Filtrar por conta
            tipo: C (crédito) ou D (débito)
            limit: Limite de resultados

        Returns:
            Lista de transações
        """
        query = self.session.query(TransacaoCora).filter(
            TransacaoCora.conciliado == False,
            TransacaoCora.tipo == TipoTransacaoCora(tipo)
        )

        if conta_cora_id:
            query = query.filter(TransacaoCora.conta_cora_id == conta_cora_id)

        return query.order_by(desc(TransacaoCora.data_transacao)).limit(limit).all()


# ==================== COBRANCA CORA REPOSITORY ====================

class CobrancaCoraRepository:
    """Repositório para gerenciar cobranças Cora (boletos e PIX)"""

    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, cobranca_id: UUID) -> Optional[CobrancaCora]:
        """Busca cobrança por ID"""
        cobranca = self.session.query(CobrancaCora).filter(
            CobrancaCora.id == cobranca_id
        ).first()

        if cobranca:
            # Descriptografa dados sensíveis
            cobranca = self._decrypt_cobranca(cobranca)

        return cobranca

    def get_by_invoice_id(self, cora_invoice_id: str) -> Optional[CobrancaCora]:
        """Busca cobrança por invoice ID Cora"""
        cobranca = self.session.query(CobrancaCora).filter(
            CobrancaCora.cora_invoice_id == cora_invoice_id
        ).first()

        if cobranca:
            cobranca = self._decrypt_cobranca(cobranca)

        return cobranca

    def get_by_pix_txid(self, cora_pix_txid: str) -> Optional[CobrancaCora]:
        """Busca cobrança por PIX TXID"""
        cobranca = self.session.query(CobrancaCora).filter(
            CobrancaCora.cora_pix_txid == cora_pix_txid
        ).first()

        if cobranca:
            cobranca = self._decrypt_cobranca(cobranca)

        return cobranca

    def create(
        self,
        conta_cora_id: UUID,
        condominio_id: UUID,
        tipo: str,
        valor: Decimal,
        pagador_nome: Optional[str] = None,
        pagador_documento: Optional[str] = None,
        pagador_email: Optional[str] = None,
        **kwargs
    ) -> CobrancaCora:
        """
        Cria nova cobrança

        Args:
            conta_cora_id: ID da conta Cora
            condominio_id: ID do condomínio
            tipo: boleto, pix ou hibrido
            valor: Valor da cobrança
            pagador_nome: Nome do pagador
            pagador_documento: CPF/CNPJ (será criptografado)
            pagador_email: Email (será criptografado)
            **kwargs: Campos adicionais

        Returns:
            Cobrança criada
        """
        # Criptografa dados sensíveis
        doc_enc, doc_salt = None, None
        email_enc, email_salt = None, None

        if pagador_documento:
            doc_enc, doc_salt = crypto_service.criptografar(pagador_documento)

        if pagador_email:
            email_enc, email_salt = crypto_service.criptografar(pagador_email)

        cobranca = CobrancaCora(
            conta_cora_id=conta_cora_id,
            condominio_id=condominio_id,
            tipo=TipoCobrancaCora(tipo),
            valor=valor,
            pagador_nome=pagador_nome,
            pagador_documento_encrypted=doc_enc,
            pagador_documento_salt=doc_salt,
            pagador_email_encrypted=email_enc,
            pagador_email_salt=email_salt,
            **kwargs
        )

        self.session.add(cobranca)
        self.session.flush()
        return cobranca

    def update_status(
        self,
        cobranca_id: UUID,
        status: str,
        valor_pago: Optional[Decimal] = None,
        data_pagamento: Optional[datetime] = None
    ) -> Optional[CobrancaCora]:
        """
        Atualiza status da cobrança

        Args:
            cobranca_id: ID da cobrança
            status: Novo status
            valor_pago: Valor efetivamente pago
            data_pagamento: Data do pagamento

        Returns:
            Cobrança atualizada ou None
        """
        cobranca = self.get_by_id(cobranca_id)
        if not cobranca:
            return None

        cobranca.status = StatusCobrancaCora(status)

        if valor_pago is not None:
            cobranca.valor_pago = valor_pago

        if data_pagamento:
            cobranca.data_pagamento = data_pagamento

        self.session.flush()
        return cobranca

    def list_pendentes(
        self,
        conta_cora_id: Optional[UUID] = None,
        condominio_id: Optional[UUID] = None,
        vencidas: bool = False
    ) -> List[CobrancaCora]:
        """
        Lista cobranças pendentes ou vencidas

        Args:
            conta_cora_id: Filtrar por conta
            condominio_id: Filtrar por condomínio
            vencidas: Se True, retorna apenas vencidas

        Returns:
            Lista de cobranças
        """
        query = self.session.query(CobrancaCora).filter(
            CobrancaCora.status.in_([StatusCobrancaCora.PENDENTE, StatusCobrancaCora.VENCIDO])
        )

        if conta_cora_id:
            query = query.filter(CobrancaCora.conta_cora_id == conta_cora_id)

        if condominio_id:
            query = query.filter(CobrancaCora.condominio_id == condominio_id)

        if vencidas:
            today = datetime.now().date()
            query = query.filter(CobrancaCora.data_vencimento < today)

        results = query.order_by(CobrancaCora.data_vencimento).all()

        # Descriptografa
        return [self._decrypt_cobranca(c) for c in results]

    def _decrypt_cobranca(self, cobranca: CobrancaCora) -> CobrancaCora:
        """Descriptografa dados sensíveis da cobrança"""
        if cobranca.pagador_documento_encrypted and cobranca.pagador_documento_salt:
            try:
                cobranca.pagador_documento = crypto_service.descriptografar(
                    cobranca.pagador_documento_encrypted,
                    cobranca.pagador_documento_salt
                )
            except:
                cobranca.pagador_documento = None

        if cobranca.pagador_email_encrypted and cobranca.pagador_email_salt:
            try:
                cobranca.pagador_email = crypto_service.descriptografar(
                    cobranca.pagador_email_encrypted,
                    cobranca.pagador_email_salt
                )
            except:
                cobranca.pagador_email = None

        return cobranca


# ==================== WEBHOOK CORA REPOSITORY ====================

class WebhookCoraRepository:
    """Repositório para gerenciar webhooks Cora (IMUTÁVEL)"""

    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, webhook_id: UUID) -> Optional[WebhookCora]:
        """Busca webhook por ID"""
        return self.session.query(WebhookCora).filter(
            WebhookCora.id == webhook_id
        ).first()

    def get_by_event_id(self, event_id: str) -> Optional[WebhookCora]:
        """Busca webhook por event ID"""
        return self.session.query(WebhookCora).filter(
            WebhookCora.event_id == event_id
        ).first()

    def create(
        self,
        event_type: str,
        event_id: str,
        body: Dict,
        signature: str,
        signature_valid: bool,
        ip_origem: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> WebhookCora:
        """
        Registra webhook recebido (IMUTÁVEL)

        Args:
            event_type: Tipo do evento
            event_id: ID único do evento
            body: Corpo do webhook
            signature: Assinatura recebida
            signature_valid: Se a assinatura é válida
            ip_origem: IP de origem
            user_agent: User agent

        Returns:
            Webhook criado
        """
        # Verifica se já existe (evita duplicatas)
        existing = self.get_by_event_id(event_id)
        if existing:
            return existing

        webhook = WebhookCora(
            event_type=event_type,
            event_id=event_id,
            body=body,
            signature=signature,
            signature_valid=signature_valid,
            ip_origem=ip_origem,
            user_agent=user_agent
        )

        self.session.add(webhook)
        self.session.flush()
        return webhook

    def marcar_processado(
        self,
        webhook_id: UUID,
        resultado: Optional[Dict] = None,
        erro_mensagem: Optional[str] = None
    ) -> Optional[WebhookCora]:
        """
        Marca webhook como processado

        ATENÇÃO: Este é o ÚNICO UPDATE permitido na tabela webhooks

        Args:
            webhook_id: ID do webhook
            resultado: Resultado do processamento
            erro_mensagem: Mensagem de erro (se houver)

        Returns:
            Webhook atualizado ou None
        """
        webhook = self.get_by_id(webhook_id)
        if not webhook:
            return None

        webhook.processado = True
        webhook.processado_em = datetime.utcnow()
        webhook.resultado = resultado
        webhook.erro_mensagem = erro_mensagem
        webhook.tentativas_processamento += 1

        self.session.flush()
        return webhook

    def get_nao_processados(self, limit: int = 100) -> List[WebhookCora]:
        """
        Lista webhooks não processados

        Args:
            limit: Limite de resultados

        Returns:
            Lista de webhooks (máximo 100)
        """
        return self.session.query(WebhookCora).filter(
            WebhookCora.processado == False,
            WebhookCora.signature_valid == True  # Só processa se assinatura válida
        ).order_by(WebhookCora.received_at).limit(min(limit, 100)).all()


# ==================== CORA TOKEN REPOSITORY ====================

class CoraTokenRepository:
    """Repositório para gerenciar tokens OAuth2 Cora"""

    def __init__(self, session: Session):
        self.session = session

    def get_ativo(self, conta_cora_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Obtém token ativo e válido da conta

        Args:
            conta_cora_id: ID da conta Cora

        Returns:
            Dict com access_token, refresh_token, expires_at ou None
        """
        token = self.session.query(CoraToken).filter(
            CoraToken.conta_cora_id == conta_cora_id,
            CoraToken.ativo == True,
            CoraToken.revogado == False,
            CoraToken.expires_at > datetime.utcnow()
        ).first()

        if not token:
            return None

        try:
            return {
                "access_token": crypto_service.descriptografar(
                    token.access_token_encrypted,
                    token.access_token_salt
                ),
                "refresh_token": crypto_service.descriptografar(
                    token.refresh_token_encrypted,
                    token.refresh_token_salt
                ) if token.refresh_token_encrypted else None,
                "expires_at": token.expires_at,
                "token_type": token.token_type
            }
        except:
            return None

    def create(
        self,
        conta_cora_id: UUID,
        access_token: str,
        expires_at: datetime,
        refresh_token: Optional[str] = None,
        token_type: str = "Bearer"
    ) -> CoraToken:
        """
        Cria novo token (desativa anteriores automaticamente)

        Args:
            conta_cora_id: ID da conta Cora
            access_token: Access token
            expires_at: Data de expiração
            refresh_token: Refresh token (opcional)
            token_type: Tipo do token

        Returns:
            Token criado
        """
        # Desativa tokens anteriores
        self.session.query(CoraToken).filter(
            CoraToken.conta_cora_id == conta_cora_id,
            CoraToken.ativo == True
        ).update({"ativo": False})

        # Criptografa tokens
        access_enc, access_salt = crypto_service.criptografar(access_token)

        refresh_enc, refresh_salt = None, None
        if refresh_token:
            refresh_enc, refresh_salt = crypto_service.criptografar(refresh_token)

        token = CoraToken(
            conta_cora_id=conta_cora_id,
            access_token_encrypted=access_enc,
            access_token_salt=access_salt,
            refresh_token_encrypted=refresh_enc,
            refresh_token_salt=refresh_salt,
            expires_at=expires_at,
            token_type=token_type,
            ativo=True
        )

        self.session.add(token)
        self.session.flush()
        return token

    def revogar(self, conta_cora_id: UUID, motivo: Optional[str] = None) -> int:
        """
        Revoga todos os tokens de uma conta

        Args:
            conta_cora_id: ID da conta
            motivo: Motivo da revogação

        Returns:
            Número de tokens revogados
        """
        count = self.session.query(CoraToken).filter(
            CoraToken.conta_cora_id == conta_cora_id,
            CoraToken.ativo == True
        ).update({
            "ativo": False,
            "revogado": True,
            "revogado_em": datetime.utcnow(),
            "revogado_motivo": motivo
        })

        self.session.flush()
        return count


# ==================== SALDO CORA REPOSITORY ====================

class SaldoCoraRepository:
    """Repositório para cache de saldo Cora"""

    def __init__(self, session: Session):
        self.session = session

    def get_ultimo(self, conta_cora_id: UUID) -> Optional[SaldoCora]:
        """
        Obtém último saldo válido (cache)

        Args:
            conta_cora_id: ID da conta

        Returns:
            Saldo ou None se expirado/inexistente
        """
        saldo = self.session.query(SaldoCora).filter(
            SaldoCora.conta_cora_id == conta_cora_id
        ).first()

        if not saldo:
            return None

        # Verifica se cache ainda é válido
        if datetime.utcnow() > saldo.valido_ate:
            return None

        return saldo

    def create(
        self,
        conta_cora_id: UUID,
        saldo_disponivel: Decimal,
        saldo_bloqueado: Decimal,
        data_referencia: datetime,
        ttl_minutos: int = 10
    ) -> SaldoCora:
        """
        Atualiza saldo (UPSERT)

        Args:
            conta_cora_id: ID da conta
            saldo_disponivel: Saldo disponível
            saldo_bloqueado: Saldo bloqueado
            data_referencia: Data/hora do saldo na API
            ttl_minutos: Tempo de vida do cache em minutos

        Returns:
            Saldo criado/atualizado
        """
        saldo_total = saldo_disponivel + saldo_bloqueado
        valido_ate = datetime.utcnow() + timedelta(minutes=ttl_minutos)

        # Tenta atualizar existente
        existing = self.session.query(SaldoCora).filter(
            SaldoCora.conta_cora_id == conta_cora_id
        ).first()

        if existing:
            existing.saldo_disponivel = saldo_disponivel
            existing.saldo_bloqueado = saldo_bloqueado
            existing.saldo_total = saldo_total
            existing.data_referencia = data_referencia
            existing.valido_ate = valido_ate
            self.session.flush()
            return existing

        # Cria novo
        saldo = SaldoCora(
            conta_cora_id=conta_cora_id,
            saldo_disponivel=saldo_disponivel,
            saldo_bloqueado=saldo_bloqueado,
            saldo_total=saldo_total,
            data_referencia=data_referencia,
            valido_ate=valido_ate
        )

        self.session.add(saldo)
        self.session.flush()
        return saldo


# ==================== CORA SYNC LOG REPOSITORY ====================

class CoraSyncLogRepository:
    """Repositório para logs de sincronização"""

    def __init__(self, session: Session):
        self.session = session

    def criar(
        self,
        conta_cora_id: UUID,
        condominio_id: UUID,
        tipo: str,
        data_inicio: Optional[str] = None,
        data_fim: Optional[str] = None,
        parametros: Optional[Dict] = None,
        iniciado_por: Optional[UUID] = None
    ) -> CoraSyncLog:
        """
        Inicia log de sincronização

        Args:
            conta_cora_id: ID da conta
            condominio_id: ID do condomínio
            tipo: extrato, cobrancas ou saldo
            data_inicio: Data inicial (para extrato)
            data_fim: Data final (para extrato)
            parametros: Parâmetros da sincronização
            iniciado_por: ID do usuário (None se automático)

        Returns:
            Log criado
        """
        log = CoraSyncLog(
            conta_cora_id=conta_cora_id,
            condominio_id=condominio_id,
            tipo=TipoSyncCora(tipo),
            status=StatusSyncCora.INICIADO,
            data_inicio=data_inicio,
            data_fim=data_fim,
            parametros=parametros,
            iniciado_por=iniciado_por
        )

        self.session.add(log)
        self.session.flush()
        return log

    def finalizar(
        self,
        sync_id: UUID,
        status: str,
        registros_processados: int = 0,
        registros_novos: int = 0,
        registros_atualizados: int = 0,
        registros_erro: int = 0,
        erro_mensagem: Optional[str] = None,
        resultado: Optional[Dict] = None
    ) -> Optional[CoraSyncLog]:
        """
        Finaliza log de sincronização

        Args:
            sync_id: ID do log
            status: concluido ou erro
            registros_processados: Total de registros processados
            registros_novos: Registros novos criados
            registros_atualizados: Registros atualizados
            registros_erro: Registros com erro
            erro_mensagem: Mensagem de erro (se houver)
            resultado: Resultado detalhado

        Returns:
            Log atualizado ou None
        """
        log = self.session.query(CoraSyncLog).filter(
            CoraSyncLog.id == sync_id
        ).first()

        if not log:
            return None

        # Calcula duração
        duracao = (datetime.utcnow() - log.iniciado_em).total_seconds()

        log.status = StatusSyncCora(status)
        log.finalizado_em = datetime.utcnow()
        log.duracao_segundos = Decimal(str(duracao))
        log.registros_processados = registros_processados
        log.registros_novos = registros_novos
        log.registros_atualizados = registros_atualizados
        log.registros_erro = registros_erro
        log.erro_mensagem = erro_mensagem
        log.resultado = resultado

        self.session.flush()
        return log

    def list_recentes(
        self,
        conta_cora_id: Optional[UUID] = None,
        condominio_id: Optional[UUID] = None,
        tipo: Optional[str] = None,
        limit: int = 20
    ) -> List[CoraSyncLog]:
        """
        Lista logs de sincronização recentes

        Args:
            conta_cora_id: Filtrar por conta
            condominio_id: Filtrar por condomínio
            tipo: Filtrar por tipo
            limit: Limite de resultados

        Returns:
            Lista de logs
        """
        query = self.session.query(CoraSyncLog)

        if conta_cora_id:
            query = query.filter(CoraSyncLog.conta_cora_id == conta_cora_id)

        if condominio_id:
            query = query.filter(CoraSyncLog.condominio_id == condominio_id)

        if tipo:
            query = query.filter(CoraSyncLog.tipo == TipoSyncCora(tipo))

        return query.order_by(desc(CoraSyncLog.iniciado_em)).limit(limit).all()
