"""
Conecta Plus - Router Banco Cora
Endpoints para integração completa com Cora Bank API V2
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Request, BackgroundTasks, Header
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
from decimal import Decimal
import uuid
import hmac
import hashlib
import json

# Repositories
from repositories.cora import (
    ContaCoraRepository,
    TransacaoCoraRepository,
    CobrancaCoraRepository,
    WebhookCoraRepository,
    CoraTokenRepository,
    SaldoCoraRepository,
    CoraSyncLogRepository,
)

# Integrations
from integrations.cora_bank import CoraBankClient, criar_cliente_cora

# Services
from services.audit_service import audit_service, TipoAcaoAuditoria
from services.webhook_processor import get_webhook_processor
from services.conciliacao_service import get_conciliacao_service

# Rate Limiting
from middleware.rate_limit import rate_limit, rate_limiter

# Database
from database import get_db_session
from sqlalchemy.orm import Session


router = APIRouter(prefix="/api/v1/cora", tags=["Cora Bank"])


# ==================== MODELS ====================

class CoraAuthConfig(BaseModel):
    """Configuração de autenticação Cora"""
    client_id: str
    client_secret: str
    webhook_secret: Optional[str] = None
    ambiente: str = Field(default="production", pattern="^(production|sandbox)$")
    api_version: str = Field(default="v2", pattern="^(v1|v2)$")


class CriarCobrancaRequest(BaseModel):
    """Request para criar cobrança no Cora"""
    boleto_id: Optional[str] = None  # ID do boleto interno (se houver)
    tipo: str = Field(..., pattern="^(boleto|pix|hibrido)$")
    valor: float = Field(..., gt=0)
    vencimento: Optional[str] = None  # YYYY-MM-DD
    descricao: str = "Cobrança Condomínio"

    # Dados do pagador
    pagador_nome: str
    pagador_documento: str
    pagador_email: Optional[str] = None
    pagador_telefone: Optional[str] = None

    # Parcelamento (carnê)
    numero_parcela: Optional[int] = None
    total_parcelas: Optional[int] = None


class ConciliarTransacaoRequest(BaseModel):
    """Request para conciliação manual"""
    transacao_id: str
    boleto_id: Optional[str] = None
    pagamento_id: Optional[str] = None
    lancamento_id: Optional[str] = None
    manual: bool = True


class SincronizarRequest(BaseModel):
    """Request para sincronização"""
    tipo: str = Field(..., pattern="^(extrato|saldo|cobrancas)$")
    data_inicio: Optional[str] = None
    data_fim: Optional[str] = None


# ==================== HELPERS ====================

MOCK_CONDOMINIO_ID = "cond_001"


def get_current_user(request: Request) -> Dict:
    """Extrai usuário do token (mock para desenvolvimento)"""
    # TODO: Implementar extração real do JWT
    return {
        "id": "user_001",
        "email": "admin@conectaplus.com.br",
        "role": "admin",
        "condominio_id": MOCK_CONDOMINIO_ID
    }


async def get_cora_client(
    condominio_id: str,
    db: Session = Depends(get_db_session)
) -> CoraBankClient:
    """
    Obtém cliente Cora autenticado para o condomínio

    Busca conta Cora ativa, verifica token válido e retorna cliente configurado
    """
    # Busca conta Cora do condomínio
    conta_repo = ContaCoraRepository(db)
    conta = conta_repo.get_by_condominio(uuid.UUID(condominio_id))

    if not conta:
        raise HTTPException(
            status_code=404,
            detail="Conta Cora não configurada para este condomínio"
        )

    if not conta.ativa:
        raise HTTPException(
            status_code=400,
            detail="Conta Cora desativada"
        )

    # Obtém credenciais descriptografadas
    credentials = conta_repo.get_credentials(conta.id)
    if not credentials:
        raise HTTPException(
            status_code=500,
            detail="Erro ao descriptografar credenciais Cora"
        )

    # Verifica token válido
    token_repo = CoraTokenRepository(db)
    token_data = token_repo.get_ativo(conta.id)

    # Se não tem token válido, autentica
    if not token_data:
        # Cria cliente temporário para autenticar
        temp_client = criar_cliente_cora(
            client_id=credentials["client_id"],
            client_secret=credentials["client_secret"],
            ambiente=conta.ambiente.value,
            api_version=conta.api_version.value
        )

        # Autentica
        auth_response = await temp_client.autenticar()

        # Armazena token
        expires_at = datetime.utcnow() + timedelta(seconds=auth_response.get("expires_in", 3600))
        token_repo.create(
            conta_cora_id=conta.id,
            access_token=auth_response["access_token"],
            expires_at=expires_at,
            refresh_token=auth_response.get("refresh_token")
        )
        db.commit()

        access_token = auth_response["access_token"]
    else:
        access_token = token_data["access_token"]

    # Cria cliente autenticado
    client = criar_cliente_cora(
        client_id=credentials["client_id"],
        client_secret=credentials["client_secret"],
        ambiente=conta.ambiente.value,
        api_version=conta.api_version.value
    )
    client._access_token = access_token  # Injeta token

    return client


# ==================== AUTENTICAÇÃO ====================

@router.post("/auth")
@rate_limit(requests_per_minute=10)
async def autenticar_cora(
    config: CoraAuthConfig,
    request: Request,
    db: Session = Depends(get_db_session)
):
    """
    Configura autenticação Cora para o condomínio

    Testa credenciais e armazena de forma segura
    """
    user = get_current_user(request)
    condominio_id = uuid.UUID(user["condominio_id"])

    # Testa autenticação
    try:
        client = criar_cliente_cora(
            client_id=config.client_id,
            client_secret=config.client_secret,
            ambiente=config.ambiente,
            api_version=config.api_version
        )

        auth_response = await client.autenticar()
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Falha na autenticação Cora: {str(e)}"
        )

    # Busca ou cria conta Cora
    conta_repo = ContaCoraRepository(db)
    conta = conta_repo.get_by_condominio(condominio_id)

    if conta:
        # Atualiza credenciais
        conta_repo.update_credentials(
            conta_id=conta.id,
            client_id=config.client_id,
            client_secret=config.client_secret,
            webhook_secret=config.webhook_secret
        )
    else:
        # Cria nova conta
        # Precisamos do cora_account_id - vamos consultar
        account_data = await client.consultar_dados_conta()

        conta = conta_repo.create(
            condominio_id=condominio_id,
            cora_account_id=account_data.get("id", f"acc_{condominio_id}"),
            cora_document=account_data.get("documento", ""),
            client_id=config.client_id,
            client_secret=config.client_secret,
            webhook_secret=config.webhook_secret,
            ambiente=config.ambiente,
            api_version=config.api_version
        )

    # Armazena token
    token_repo = CoraTokenRepository(db)
    expires_at = datetime.utcnow() + timedelta(seconds=auth_response.get("expires_in", 3600))
    token_repo.create(
        conta_cora_id=conta.id,
        access_token=auth_response["access_token"],
        expires_at=expires_at,
        refresh_token=auth_response.get("refresh_token")
    )

    db.commit()

    # Auditoria
    audit_service.registrar(
        tipo=TipoAcaoAuditoria.CONFIG_UPDATE,
        descricao=f"Configuração Cora atualizada",
        user_id=user["id"],
        entidade_tipo="conta_cora",
        entidade_id=str(conta.id),
        detalhes={"ambiente": config.ambiente, "api_version": config.api_version}
    )

    return {
        "success": True,
        "message": "Autenticação Cora configurada com sucesso",
        "expires_at": expires_at.isoformat()
    }


# ==================== SALDO ====================

@router.get("/saldo")
@rate_limit(requests_per_minute=30)
async def consultar_saldo(
    request: Request,
    db: Session = Depends(get_db_session)
):
    """
    Consulta saldo da conta Cora

    Usa cache de 10 minutos para reduzir chamadas à API
    """
    user = get_current_user(request)
    condominio_id = user["condominio_id"]

    # Busca conta
    conta_repo = ContaCoraRepository(db)
    conta = conta_repo.get_by_condominio(uuid.UUID(condominio_id))

    if not conta:
        raise HTTPException(status_code=404, detail="Conta Cora não configurada")

    # Verifica cache
    saldo_repo = SaldoCoraRepository(db)
    saldo_cached = saldo_repo.get_ultimo(conta.id)

    if saldo_cached:
        return {
            "saldo_disponivel": float(saldo_cached.saldo_disponivel),
            "saldo_bloqueado": float(saldo_cached.saldo_bloqueado),
            "saldo_total": float(saldo_cached.saldo_total),
            "data_referencia": saldo_cached.data_referencia.isoformat(),
            "from_cache": True
        }

    # Cache expirado - consulta API
    client = await get_cora_client(condominio_id, db)

    try:
        saldo_data = await client.consultar_saldo()
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Erro ao consultar saldo Cora: {str(e)}"
        )

    # Armazena cache
    saldo_repo.create(
        conta_cora_id=conta.id,
        saldo_disponivel=Decimal(str(saldo_data["disponivel"])),
        saldo_bloqueado=Decimal(str(saldo_data.get("bloqueado", 0))),
        data_referencia=datetime.utcnow(),
        ttl_minutos=10
    )
    db.commit()

    return {
        "saldo_disponivel": saldo_data["disponivel"],
        "saldo_bloqueado": saldo_data.get("bloqueado", 0),
        "saldo_total": saldo_data["total"],
        "data_referencia": datetime.utcnow().isoformat(),
        "from_cache": False
    }


# ==================== EXTRATO ====================

@router.get("/extrato")
@rate_limit(requests_per_minute=20)
async def consultar_extrato(
    data_inicio: str = Query(..., description="YYYY-MM-DD"),
    data_fim: str = Query(..., description="YYYY-MM-DD"),
    sincronizar: bool = Query(False, description="Sincronizar com API Cora"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    request: Request = None,
    db: Session = Depends(get_db_session)
):
    """
    Consulta extrato bancário

    Se sincronizar=true, busca da API Cora e armazena no banco
    Senão, retorna dados já sincronizados
    """
    user = get_current_user(request)
    condominio_id = user["condominio_id"]

    # Busca conta
    conta_repo = ContaCoraRepository(db)
    conta = conta_repo.get_by_condominio(uuid.UUID(condominio_id))

    if not conta:
        raise HTTPException(status_code=404, detail="Conta Cora não configurada")

    transacao_repo = TransacaoCoraRepository(db)

    if sincronizar:
        # Sincroniza com API Cora
        client = await get_cora_client(condominio_id, db)

        # Cria log de sync
        sync_repo = CoraSyncLogRepository(db)
        sync_log = sync_repo.criar(
            conta_cora_id=conta.id,
            condominio_id=uuid.UUID(condominio_id),
            tipo="extrato",
            data_inicio=datetime.strptime(data_inicio, "%Y-%m-%d").date(),
            data_fim=datetime.strptime(data_fim, "%Y-%m-%d").date()
        )
        db.commit()

        try:
            # Busca extrato da API
            extrato_data = await client.consultar_extrato(
                data_inicio=data_inicio,
                data_fim=data_fim
            )

            registros_novos = 0
            registros_atualizados = 0

            # Armazena transações
            for item in extrato_data.get("items", []):
                # Verifica se já existe
                exists = transacao_repo.get_by_cora_id(item["id"])

                if not exists:
                    transacao_repo.create(
                        conta_cora_id=conta.id,
                        condominio_id=uuid.UUID(condominio_id),
                        cora_transaction_id=item["id"],
                        data_transacao=datetime.strptime(item["data"], "%Y-%m-%d").date(),
                        tipo=item["tipo"],
                        valor=Decimal(str(item["valor"])),
                        descricao=item.get("descricao", ""),
                        categoria=item.get("categoria"),
                        contrapartida_nome=item.get("contrapartida", {}).get("nome"),
                        contrapartida_documento=item.get("contrapartida", {}).get("documento"),
                        end_to_end_id=item.get("end_to_end_id"),
                        pix_txid=item.get("pix_txid"),
                        raw_data=item
                    )
                    registros_novos += 1
                else:
                    registros_atualizados += 1

            db.commit()

            # Finaliza sync
            sync_repo.finalizar(
                sync_id=sync_log.id,
                status="concluido",
                registros_processados=len(extrato_data.get("items", [])),
                registros_novos=registros_novos,
                registros_atualizados=registros_atualizados
            )
            db.commit()

        except Exception as e:
            # Marca sync como erro
            sync_repo.finalizar(
                sync_id=sync_log.id,
                status="erro",
                erro_mensagem=str(e)
            )
            db.commit()

            raise HTTPException(
                status_code=502,
                detail=f"Erro ao sincronizar extrato: {str(e)}"
            )

    # Busca transações do banco
    transacoes = transacao_repo.list(
        conta_cora_id=conta.id,
        data_inicio=datetime.strptime(data_inicio, "%Y-%m-%d").date(),
        data_fim=datetime.strptime(data_fim, "%Y-%m-%d").date(),
        page=page,
        limit=limit
    )

    return {
        "items": [
            {
                "id": str(t.id),
                "cora_transaction_id": t.cora_transaction_id,
                "data_transacao": t.data_transacao.isoformat(),
                "tipo": t.tipo.value,
                "valor": float(t.valor),
                "descricao": t.descricao,
                "categoria": t.categoria,
                "contrapartida_nome": t.contrapartida_nome,
                "contrapartida_documento": t.contrapartida_documento,
                "conciliado": t.conciliado,
                "boleto_id": str(t.boleto_id) if t.boleto_id else None,
            }
            for t in transacoes["items"]
        ],
        "total": transacoes["total"],
        "page": page,
        "limit": limit
    }


# ==================== COBRANÇAS ====================

@router.post("/cobrancas")
@rate_limit(requests_per_minute=30)
async def criar_cobranca(
    cobranca: CriarCobrancaRequest,
    request: Request,
    db: Session = Depends(get_db_session)
):
    """
    Cria cobrança no Cora (boleto/PIX/híbrido)

    Armazena dados da cobrança e atualiza boleto interno se fornecido
    """
    user = get_current_user(request)
    condominio_id = user["condominio_id"]

    # Obtém cliente Cora
    client = await get_cora_client(condominio_id, db)

    # Busca conta
    conta_repo = ContaCoraRepository(db)
    conta = conta_repo.get_by_condominio(uuid.UUID(condominio_id))

    try:
        # Cria cobrança no Cora
        if cobranca.tipo in ["boleto", "hibrido"]:
            response = await client.criar_boleto(
                valor=cobranca.valor,
                vencimento=cobranca.vencimento,
                pagador={
                    "nome": cobranca.pagador_nome,
                    "documento": cobranca.pagador_documento,
                    "email": cobranca.pagador_email,
                    "telefone": cobranca.pagador_telefone
                },
                descricao=cobranca.descricao,
                hibrido=(cobranca.tipo == "hibrido")
            )
        elif cobranca.tipo == "pix":
            response = await client.criar_cobranca_pix(
                valor=cobranca.valor,
                descricao=cobranca.descricao,
                pagador_nome=cobranca.pagador_nome,
                pagador_documento=cobranca.pagador_documento
            )
        else:
            raise HTTPException(status_code=400, detail="Tipo de cobrança inválido")

    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Erro ao criar cobrança no Cora: {str(e)}"
        )

    # Armazena cobrança no banco
    cobranca_repo = CobrancaCoraRepository(db)

    cobranca_db = cobranca_repo.create(
        conta_cora_id=conta.id,
        condominio_id=uuid.UUID(condominio_id),
        boleto_id=uuid.UUID(cobranca.boleto_id) if cobranca.boleto_id else None,
        cora_invoice_id=response.get("invoice_id"),
        cora_pix_txid=response.get("pix", {}).get("txid"),
        tipo=cobranca.tipo,
        valor=Decimal(str(cobranca.valor)),
        pagador_nome=cobranca.pagador_nome,
        pagador_documento=cobranca.pagador_documento,
        pix_qrcode=response.get("pix", {}).get("qrcode"),
        pix_copia_cola=response.get("pix", {}).get("copia_cola"),
        codigo_barras=response.get("codigo_barras"),
        linha_digitavel=response.get("linha_digitavel"),
        nosso_numero=response.get("nosso_numero"),
        url_pdf=response.get("url_pdf"),
        numero_parcela=cobranca.numero_parcela,
        total_parcelas=cobranca.total_parcelas
    )
    db.commit()

    # Auditoria
    audit_service.registrar(
        tipo=TipoAcaoAuditoria.CREATE,
        descricao=f"Cobrança Cora criada: {cobranca.tipo}",
        user_id=user["id"],
        entidade_tipo="cobranca_cora",
        entidade_id=str(cobranca_db.id),
        detalhes={"valor": cobranca.valor, "tipo": cobranca.tipo}
    )

    return {
        "success": True,
        "id": str(cobranca_db.id),
        "cora_invoice_id": response.get("invoice_id"),
        "tipo": cobranca.tipo,
        "valor": cobranca.valor,
        "codigo_barras": response.get("codigo_barras"),
        "linha_digitavel": response.get("linha_digitavel"),
        "pix_qrcode": response.get("pix", {}).get("qrcode"),
        "pix_copia_cola": response.get("pix", {}).get("copia_cola"),
        "url_pdf": response.get("url_pdf")
    }


@router.get("/cobrancas")
@rate_limit(requests_per_minute=60)
async def listar_cobrancas(
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    request: Request = None,
    db: Session = Depends(get_db_session)
):
    """Lista cobranças Cora com filtros"""
    user = get_current_user(request)
    condominio_id = user["condominio_id"]

    # Busca conta
    conta_repo = ContaCoraRepository(db)
    conta = conta_repo.get_by_condominio(uuid.UUID(condominio_id))

    if not conta:
        raise HTTPException(status_code=404, detail="Conta Cora não configurada")

    # Busca cobranças
    cobranca_repo = CobrancaCoraRepository(db)
    cobrancas = cobranca_repo.list(
        conta_cora_id=conta.id,
        status=status,
        page=page,
        limit=limit
    )

    return {
        "items": [
            {
                "id": str(c.id),
                "tipo": c.tipo.value,
                "status": c.status.value,
                "valor": float(c.valor),
                "valor_pago": float(c.valor_pago) if c.valor_pago else None,
                "data_vencimento": c.data_vencimento.isoformat() if c.data_vencimento else None,
                "data_pagamento": c.data_pagamento.isoformat() if c.data_pagamento else None,
                "nosso_numero": c.nosso_numero,
                "linha_digitavel": c.linha_digitavel,
                "pix_copia_cola": c.pix_copia_cola,
            }
            for c in cobrancas["items"]
        ],
        "total": cobrancas["total"],
        "page": page,
        "limit": limit
    }


# ==================== CONCILIAÇÃO ====================

@router.get("/conciliar/pendentes")
@rate_limit(requests_per_minute=60)
async def listar_pendentes_conciliacao(
    request: Request,
    db: Session = Depends(get_db_session)
):
    """Lista transações não conciliadas"""
    user = get_current_user(request)
    condominio_id = user["condominio_id"]

    # Busca conta
    conta_repo = ContaCoraRepository(db)
    conta = conta_repo.get_by_condominio(uuid.UUID(condominio_id))

    if not conta:
        raise HTTPException(status_code=404, detail="Conta Cora não configurada")

    # Busca transações não conciliadas (apenas créditos)
    transacao_repo = TransacaoCoraRepository(db)
    pendentes = transacao_repo.get_nao_conciliadas(conta_cora_id=conta.id)

    return {
        "items": [
            {
                "id": str(t.id),
                "cora_transaction_id": t.cora_transaction_id,
                "data_transacao": t.data_transacao.isoformat(),
                "valor": float(t.valor),
                "descricao": t.descricao,
                "contrapartida_nome": t.contrapartida_nome,
                "contrapartida_documento": t.contrapartida_documento,
                "end_to_end_id": t.end_to_end_id,
                "pix_txid": t.pix_txid,
            }
            for t in pendentes
        ],
        "total": len(pendentes)
    }


@router.post("/conciliar")
@rate_limit(requests_per_minute=30)
async def conciliar_transacao(
    req: ConciliarTransacaoRequest,
    request: Request,
    db: Session = Depends(get_db_session)
):
    """Concilia transação manualmente"""
    user = get_current_user(request)

    transacao_repo = TransacaoCoraRepository(db)

    # Concilia
    transacao = transacao_repo.conciliar(
        transacao_id=uuid.UUID(req.transacao_id),
        boleto_id=uuid.UUID(req.boleto_id) if req.boleto_id else None,
        pagamento_id=uuid.UUID(req.pagamento_id) if req.pagamento_id else None,
        lancamento_id=uuid.UUID(req.lancamento_id) if req.lancamento_id else None,
        confianca_match=Decimal("100.00") if req.manual else None,
        conciliado_por=uuid.UUID(user["id"]),
        manual=req.manual
    )

    if not transacao:
        raise HTTPException(status_code=404, detail="Transação não encontrada")

    db.commit()

    # Auditoria
    audit_service.registrar(
        tipo=TipoAcaoAuditoria.UPDATE,
        descricao=f"Transação conciliada manualmente",
        user_id=user["id"],
        entidade_tipo="transacao_cora",
        entidade_id=req.transacao_id,
        detalhes={"boleto_id": req.boleto_id, "manual": req.manual}
    )

    return {
        "success": True,
        "message": "Transação conciliada com sucesso",
        "transacao_id": str(transacao.id),
        "conciliado_em": transacao.conciliado_em.isoformat()
    }


@router.get("/conciliar/sugestoes/{transacao_id}")
@rate_limit(requests_per_minute=30)
async def obter_sugestoes_conciliacao(
    transacao_id: str,
    request: Request,
    db: Session = Depends(get_db_session)
):
    """
    Retorna sugestões de matches para uma transação específica

    Útil para conciliação manual na UI. Retorna lista de boletos
    candidatos ordenados por confiança.

    Rate limit: 30 req/min
    """
    user = get_current_user(request)

    # Obtém serviço de conciliação
    conciliacao_service = get_conciliacao_service(db)

    # Busca sugestões
    sugestoes = conciliacao_service.sugerir_matches(
        transacao_id=uuid.UUID(transacao_id)
    )

    return {
        "transacao_id": transacao_id,
        "total_sugestoes": len(sugestoes),
        "sugestoes": sugestoes
    }


@router.post("/conciliar/automatico")
@rate_limit(requests_per_minute=10)
async def conciliar_automatico(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db_session)
):
    """
    Executa conciliação automática

    Algoritmo:
    1. Busca transações não conciliadas (créditos)
    2. Para cada transação, busca boleto com mesmo valor + data + documento
    3. Se 1 match com alta confiança (>95%), concilia
    4. Se múltiplos matches, marca para revisão manual
    """
    user = get_current_user(request)
    condominio_id = user["condominio_id"]

    # Obtém serviço de conciliação
    conciliacao_service = get_conciliacao_service(db)

    # Executa em background para não bloquear request
    background_tasks.add_task(
        _executar_conciliacao_background,
        db=db,
        condominio_id=condominio_id,
        user_id=user["id"]
    )

    return {
        "success": True,
        "message": "Conciliação automática iniciada em background",
        "note": "Verifique os logs de sincronização para acompanhar o progresso"
    }


# ==================== BACKGROUND TASKS ====================

def _executar_conciliacao_background(
    db: Session,
    condominio_id: str,
    user_id: str
):
    """
    Executa conciliação automática em background

    Args:
        db: Sessão de banco de dados
        condominio_id: ID do condomínio
        user_id: ID do usuário que iniciou
    """
    import logging
    logger = logging.getLogger("conciliacao_background")

    try:
        logger.info(f"Iniciando conciliação automática para condomínio {condominio_id}")

        # Obtém serviço de conciliação
        conciliacao_service = get_conciliacao_service(db)

        # Executa conciliação
        resultado = conciliacao_service.executar_conciliacao_automatica(
            condominio_id=condominio_id,
            auto_conciliar=True,
            min_confianca=0.95  # 95% de confiança mínima
        )

        db.commit()

        logger.info(
            f"Conciliação automática concluída: "
            f"{resultado['conciliadas_automaticamente']} conciliadas, "
            f"{resultado['marcadas_para_revisao']} para revisão, "
            f"{resultado['sem_match']} sem match"
        )

        # Registra auditoria
        audit_service.registrar(
            tipo=TipoAcaoAuditoria.EXECUTE,
            descricao=(
                f"Conciliação automática executada: "
                f"{resultado['conciliadas_automaticamente']} transações conciliadas"
            ),
            user_id=user_id,
            entidade_tipo="conciliacao_automatica",
            entidade_id=condominio_id,
            detalhes=resultado
        )

    except Exception as e:
        logger.error(f"Erro na conciliação automática: {str(e)}", exc_info=True)
        db.rollback()

        # Registra erro na auditoria
        audit_service.registrar(
            tipo=TipoAcaoAuditoria.ERROR,
            descricao=f"Erro na conciliação automática: {str(e)}",
            user_id=user_id,
            entidade_tipo="conciliacao_automatica",
            entidade_id=condominio_id,
            detalhes={"erro": str(e)}
        )


# ==================== WEBHOOK ====================

@router.post("/webhook")
async def receber_webhook_cora(
    request: Request,
    x_cora_signature: Optional[str] = Header(None),
    db: Session = Depends(get_db_session)
):
    """
    Recebe webhooks do Cora (PÚBLICO - sem autenticação)

    Valida assinatura HMAC-SHA256 e processa evento em tempo real

    Eventos suportados:
    - invoice.paid: Boleto/PIX pago
    - invoice.overdue: Boleto vencido
    - invoice.cancelled: Boleto cancelado
    - pix.received: PIX recebido
    - payment.created: Pagamento criado
    - payment.failed: Pagamento falhou
    - transfer.completed: Transferência concluída
    - transfer.failed: Transferência falhou
    """
    # Lê body raw (necessário para validação de assinatura)
    body = await request.body()

    # Parseia JSON
    try:
        payload = json.loads(body.decode())
    except:
        raise HTTPException(status_code=400, detail="JSON inválido")

    # Extrai dados do evento
    event_type = payload.get("type")
    event_id = payload.get("id")
    event_data = payload.get("data", {})

    if not event_type or not event_id:
        raise HTTPException(status_code=400, detail="Webhook inválido - faltam campos obrigatórios")

    # Valida assinatura HMAC-SHA256
    signature_valid = False
    webhook_secret = None

    # Tenta identificar conta pela invoice_id ou txid
    if event_data.get("id"):
        # Busca cobrança para obter webhook_secret
        cobranca_repo = CobrancaCoraRepository(db)
        conta_repo = ContaCoraRepository(db)

        # Tenta buscar por invoice_id
        cobranca = cobranca_repo.get_by_invoice_id(event_data.get("id"))
        if cobranca:
            # Busca credenciais da conta
            credentials = conta_repo.get_credentials(cobranca.conta_cora_id)
            if credentials:
                webhook_secret = credentials.get("webhook_secret")

        # Se não achou por invoice, tenta por txid
        if not webhook_secret and event_data.get("txid"):
            cobranca = cobranca_repo.get_by_pix_txid(event_data.get("txid"))
            if cobranca:
                credentials = conta_repo.get_credentials(cobranca.conta_cora_id)
                if credentials:
                    webhook_secret = credentials.get("webhook_secret")

    # Valida assinatura se tiver secret
    if webhook_secret and x_cora_signature:
        processor = get_webhook_processor(db)
        signature_valid = processor.validar_assinatura(
            payload=body,
            signature=x_cora_signature,
            webhook_secret=webhook_secret
        )
    else:
        # Se não tem secret configurado, aceita o webhook (modo desenvolvimento)
        signature_valid = True

    # Registra webhook (IMUTÁVEL)
    webhook_repo = WebhookCoraRepository(db)
    webhook = webhook_repo.create(
        event_type=event_type,
        event_id=event_id,
        body=payload,
        signature=x_cora_signature or "",
        signature_valid=signature_valid,
        ip_origem=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent")
    )
    db.commit()

    # Processa evento em tempo real
    processor = get_webhook_processor(db)

    try:
        # Processa webhook
        resultado = processor.processar_webhook(
            event_type=event_type,
            event_data=event_data,
            webhook_id=webhook.id
        )

        # Marca como processado
        webhook_repo.marcar_processado(
            webhook_id=webhook.id,
            resultado=resultado
        )
        db.commit()

        return {
            "received": True,
            "event_id": event_id,
            "event_type": event_type,
            "processed": True,
            "signature_valid": signature_valid,
            "result": resultado
        }

    except Exception as e:
        # Marca como erro (será retentado depois)
        webhook_repo.marcar_processado(
            webhook_id=webhook.id,
            resultado={},
            erro_mensagem=str(e)
        )
        db.commit()

        # Retorna 200 para o Cora não reenviar
        # (retry será feito internamente pelo nosso sistema)
        return {
            "received": True,
            "event_id": event_id,
            "processed": False,
            "error": str(e),
            "note": "Webhook será reprocessado automaticamente"
        }


@router.post("/webhook/{webhook_id}/retry")
@rate_limit(requests_per_minute=10)
async def retry_webhook(
    webhook_id: str,
    request: Request,
    db: Session = Depends(get_db_session)
):
    """
    Retenta processar webhook que falhou

    Útil para webhooks que falharam temporariamente
    (ex: banco de dados indisponível, timeout, etc)
    """
    user = get_current_user(request)

    processor = get_webhook_processor(db)

    try:
        resultado = processor.retry_webhook(
            webhook_id=uuid.UUID(webhook_id),
            max_retries=3
        )

        return {
            "success": True,
            "webhook_id": webhook_id,
            "resultado": resultado
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao reprocessar webhook: {str(e)}")


# ==================== SINCRONIZAÇÃO ====================

@router.post("/sincronizar")
@rate_limit(requests_per_minute=5)
async def sincronizar_dados(
    req: SincronizarRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db_session)
):
    """
    Sincroniza dados com Cora (extrato/saldo)

    Executa em background para não bloquear
    """
    user = get_current_user(request)
    condominio_id = user["condominio_id"]

    # Busca conta
    conta_repo = ContaCoraRepository(db)
    conta = conta_repo.get_by_condominio(uuid.UUID(condominio_id))

    if not conta:
        raise HTTPException(status_code=404, detail="Conta Cora não configurada")

    # Cria log de sync
    sync_repo = CoraSyncLogRepository(db)
    sync_log = sync_repo.criar(
        conta_cora_id=conta.id,
        condominio_id=uuid.UUID(condominio_id),
        tipo=req.tipo,
        data_inicio=datetime.strptime(req.data_inicio, "%Y-%m-%d").date() if req.data_inicio else None,
        data_fim=datetime.strptime(req.data_fim, "%Y-%m-%d").date() if req.data_fim else None
    )
    db.commit()

    # TODO: Executar sincronização em background

    return {
        "success": True,
        "message": f"Sincronização de {req.tipo} iniciada",
        "sync_id": str(sync_log.id)
    }


# ==================== LOGS ====================

@router.get("/logs/sync")
@rate_limit(requests_per_minute=60)
async def listar_sync_logs(
    limit: int = Query(20, ge=1, le=100),
    request: Request = None,
    db: Session = Depends(get_db_session)
):
    """Lista histórico de sincronizações"""
    user = get_current_user(request)
    condominio_id = user["condominio_id"]

    # Busca conta
    conta_repo = ContaCoraRepository(db)
    conta = conta_repo.get_by_condominio(uuid.UUID(condominio_id))

    if not conta:
        raise HTTPException(status_code=404, detail="Conta Cora não configurada")

    sync_repo = CoraSyncLogRepository(db)
    logs = sync_repo.list_recentes(conta_cora_id=conta.id, limit=limit)

    return {
        "items": [
            {
                "id": str(log.id),
                "tipo": log.tipo.value,
                "status": log.status.value,
                "data_inicio": log.data_inicio.isoformat() if log.data_inicio else None,
                "data_fim": log.data_fim.isoformat() if log.data_fim else None,
                "registros_processados": log.registros_processados,
                "registros_novos": log.registros_novos,
                "registros_erro": log.registros_erro,
                "duracao_segundos": float(log.duracao_segundos) if log.duracao_segundos else None,
                "iniciado_em": log.iniciado_em.isoformat(),
                "finalizado_em": log.finalizado_em.isoformat() if log.finalizado_em else None,
            }
            for log in logs
        ],
        "total": len(logs)
    }


@router.get("/logs/webhooks")
@rate_limit(requests_per_minute=60)
async def listar_webhook_logs(
    processado: Optional[bool] = None,
    limit: int = Query(100, ge=1, le=500),
    request: Request = None,
    db: Session = Depends(get_db_session)
):
    """Lista webhooks recebidos"""
    webhook_repo = WebhookCoraRepository(db)

    if processado is False:
        webhooks = webhook_repo.get_nao_processados(limit=limit)
    else:
        # TODO: Implementar listagem completa com filtros
        webhooks = webhook_repo.get_nao_processados(limit=limit)

    return {
        "items": [
            {
                "id": str(w.id),
                "event_type": w.event_type,
                "event_id": w.event_id,
                "processado": w.processado,
                "processado_em": w.processado_em.isoformat() if w.processado_em else None,
                "tentativas_processamento": w.tentativas_processamento,
                "received_at": w.received_at.isoformat(),
                "signature_valid": w.signature_valid,
            }
            for w in webhooks
        ],
        "total": len(webhooks)
    }
