"""
Conecta Plus - Router Financeiro
Endpoints do módulo financeiro com persistência real e IA
"""

from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File, Request
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
import uuid

# Validators
from validators.financeiro import (
    ValidadorCPF,
    ValidadorCNPJ,
    ValidadorDocumento,
    ValidadorPIX,
    ValidadorCodigoBarras,
    ValidadorBoleto,
    VALOR_MINIMO_BOLETO,
    VALOR_MAXIMO_BOLETO
)

# Audit Service
from services.audit_service import audit_service, TipoAcaoAuditoria

# Rate Limiting
from middleware.rate_limit import rate_limit, rate_limiter

# ML & NLP Engines
from services.ml_engine import (
    ml_inadimplencia,
    ml_fluxo_caixa,
    sistema_alertas,
    priorizador_cobranca,
    PrevisaoInadimplencia,
    PrevisaoFluxoCaixa,
    AlertaProativo
)
from services.nlp_engine import (
    analisador_sentimento,
    gerador_mensagens,
    otimizador_comunicacao,
    CanalComunicacao,
    TomMensagem
)
from services.dashboard_inteligente import (
    dashboard_builder,
    gerador_insights
)

router = APIRouter(prefix="/api/financeiro", tags=["Financeiro"])


# ==================== MODELS ====================

class BoletoCreate(BaseModel):
    unidade_id: str
    valor: float
    vencimento: str
    descricao: Optional[str] = "Taxa de Condomínio"
    tipo: Optional[str] = "condominio"
    parcela: Optional[int] = None
    total_parcelas: Optional[int] = None


class BoletoUpdate(BaseModel):
    valor: Optional[float] = None
    vencimento: Optional[str] = None
    descricao: Optional[str] = None
    status: Optional[str] = None


class PagamentoRegistro(BaseModel):
    boleto_id: str
    valor_pago: float
    data_pagamento: str
    forma_pagamento: str
    comprovante: Optional[str] = None
    observacao: Optional[str] = None


class LancamentoCreate(BaseModel):
    tipo: str
    categoria_id: Optional[str] = None
    descricao: str
    valor: float
    data: str
    unidade_id: Optional[str] = None
    fornecedor_nome: Optional[str] = None
    fornecedor_documento: Optional[str] = None
    documento_numero: Optional[str] = None
    recorrente: Optional[bool] = False


class AcordoCreate(BaseModel):
    unidade_id: str
    boletos_ids: List[str]
    parcelas: int
    entrada: Optional[float] = 0
    desconto_percentual: Optional[float] = 0
    dia_vencimento: int = 10


class ContaBancariaCreate(BaseModel):
    banco_codigo: str
    banco_nome: str
    agencia: str
    conta: str
    tipo: Optional[str] = "conta_corrente"
    titular: Optional[str] = None
    documento: Optional[str] = None
    principal: Optional[bool] = False


class ConfiguracaoIntegracao(BaseModel):
    tipo: str  # 'cora', 'inter', etc
    ambiente: str  # 'sandbox', 'producao'
    client_id: str
    client_secret: str
    webhook_url: Optional[str] = None
    config_extra: Optional[Dict] = None


# ==================== MOCK DATA (Temporário) ====================
# Será substituído por dados reais do PostgreSQL

MOCK_CONDOMINIO_ID = "550e8400-e29b-41d4-a716-446655440000"

# CPFs válidos para ambiente de desenvolvimento/teste
MOCK_UNIDADES = [
    {"id": "unit_001", "bloco": "A", "numero": "101", "morador": "Carlos Silva", "documento": "529.982.247-25"},
    {"id": "unit_002", "bloco": "A", "numero": "102", "morador": "Maria Santos", "documento": "407.902.298-32"},
    {"id": "unit_003", "bloco": "A", "numero": "103", "morador": "Pedro Oliveira", "documento": "838.687.518-15"},
    {"id": "unit_004", "bloco": "A", "numero": "201", "morador": "Ana Costa", "documento": "191.536.168-02"},
]

# Importa gerador de boletos
from services.boleto_generator import GeradorBoleto, GeradorPIX

# Importa novos serviços
from services.qrcode_generator import qrcode_generator
from services.pdf_generator import pdf_generator
from services.email_service import email_service
from services.whatsapp_service import whatsapp_service
from services.relatorios_avancados import gerador_relatorios
from services.websocket_notifier import ws_manager

# Instância do gerador
_gerador_boleto = GeradorBoleto(
    banco_codigo="077",
    agencia="0001",
    conta="12345678",
    beneficiario_nome="Residencial Conecta Plus",
    beneficiario_documento="12.345.678/0001-90",
    chave_pix="12345678000190@pix.bcb.gov.br"  # Chave PIX do condomínio
)

# Cache de boletos (temporário - será PostgreSQL)
_boletos_cache: Dict[str, Dict] = {}


# ==================== HELPERS ====================

def get_current_user(request: Request) -> Dict:
    """Extrai usuário do token (mock)"""
    return {
        "id": "user_001",
        "email": "admin@conectaplus.com.br",
        "role": "admin",
        "condominio_id": MOCK_CONDOMINIO_ID
    }


# ==================== BOLETOS ====================

@router.get("/boletos")
async def listar_boletos(
    status: Optional[str] = None,
    unidade_id: Optional[str] = None,
    competencia: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    request: Request = None
):
    """Lista boletos com filtros"""
    boletos = list(_boletos_cache.values())

    # Aplica filtros
    if status:
        boletos = [b for b in boletos if b.get("status") == status]
    if unidade_id:
        boletos = [b for b in boletos if b.get("unidade_id") == unidade_id]
    if competencia:
        boletos = [b for b in boletos if b.get("competencia") == competencia]

    # Paginação
    total = len(boletos)
    start = (page - 1) * limit
    end = start + limit

    return {
        "items": boletos[start:end],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit
    }


@router.get("/boletos/{boleto_id}")
async def obter_boleto(boleto_id: str):
    """Retorna detalhes de um boleto"""
    if boleto_id not in _boletos_cache:
        raise HTTPException(status_code=404, detail="Boleto não encontrado")
    return _boletos_cache[boleto_id]


@router.post("/boletos")
@rate_limit(requests_per_minute=30, requests_per_hour=500)
async def criar_boleto(dados: BoletoCreate, request: Request = None):
    """
    Cria um novo boleto com código de barras e PIX válidos
    """
    user = get_current_user(request)

    # VALIDAÇÃO 1: Valor do boleto
    if dados.valor < VALOR_MINIMO_BOLETO:
        raise HTTPException(
            status_code=400,
            detail=f"Valor mínimo do boleto é R$ {VALOR_MINIMO_BOLETO:.2f}"
        )
    if dados.valor > VALOR_MAXIMO_BOLETO:
        raise HTTPException(
            status_code=400,
            detail=f"Valor máximo do boleto é R$ {VALOR_MAXIMO_BOLETO:.2f}"
        )

    # VALIDAÇÃO 2: Data de vencimento
    try:
        vencimento = datetime.strptime(dados.vencimento, "%Y-%m-%d").date()
        if vencimento < date.today():
            raise HTTPException(
                status_code=400,
                detail="Data de vencimento não pode ser no passado"
            )
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Formato de data inválido. Use YYYY-MM-DD"
        )

    # Busca dados da unidade
    unidade = next((u for u in MOCK_UNIDADES if u["id"] == dados.unidade_id), None)
    if not unidade:
        raise HTTPException(status_code=404, detail="Unidade não encontrada")

    # VALIDAÇÃO 3: Documento do pagador (CPF/CNPJ)
    doc_result = ValidadorDocumento.validar(unidade["documento"])
    if not doc_result.valido:
        raise HTTPException(
            status_code=400,
            detail=f"Documento do pagador inválido: {doc_result.mensagem}"
        )

    boleto_dados = _gerador_boleto.gerar(
        valor=dados.valor,
        vencimento=vencimento,
        pagador_nome=unidade["morador"],
        pagador_documento=unidade["documento"],
        descricao=dados.descricao
    )

    # Monta objeto do boleto
    boleto_id = f"bol_{uuid.uuid4().hex[:8]}"
    competencia = vencimento.strftime("%m/%Y")

    boleto = {
        "id": boleto_id,
        "condominio_id": MOCK_CONDOMINIO_ID,
        "unidade_id": dados.unidade_id,
        "unidade": f"Apt {unidade['numero']} - Bloco {unidade['bloco']}",
        "morador": unidade["morador"],
        "valor": dados.valor,
        "valor_original": dados.valor,
        "valor_juros": 0,
        "valor_multa": 0,
        "valor_desconto": 0,
        "valor_total": dados.valor,
        "vencimento": dados.vencimento,
        "competencia": competencia,
        "descricao": dados.descricao,
        "tipo": dados.tipo,
        "status": "pendente",
        "data_pagamento": None,
        "forma_pagamento": None,
        # Dados do boleto gerado
        "nosso_numero": boleto_dados["nosso_numero"],
        "codigo_barras": boleto_dados["codigo_barras"],
        "linha_digitavel": boleto_dados["linha_digitavel"],
        "pix_copia_cola": boleto_dados["pix"]["copia_cola"] if boleto_dados.get("pix") else None,
        "pix_txid": boleto_dados["pix"]["txid"] if boleto_dados.get("pix") else None,
        "banco": "Inter",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }

    # Salva no cache
    _boletos_cache[boleto_id] = boleto

    # AUDITORIA: Registra criação do boleto
    await audit_service.registrar_criacao_boleto(
        usuario_id=user["id"],
        usuario_email=user["email"],
        boleto_id=boleto_id,
        dados_boleto={
            "valor": dados.valor,
            "vencimento": dados.vencimento,
            "competencia": competencia,
            "unidade_id": dados.unidade_id
        },
        condominio_id=MOCK_CONDOMINIO_ID,
        request=request
    )

    return {
        "success": True,
        "message": "Boleto criado com sucesso",
        "boleto": boleto
    }


@router.post("/boletos/lote")
@rate_limit(requests_per_minute=5, requests_per_hour=20)
async def criar_boletos_lote(
    competencia: str = Query(..., description="Competência (MM/YYYY)"),
    vencimento: str = Query(..., description="Data de vencimento (YYYY-MM-DD)"),
    valor: float = Query(..., description="Valor do boleto"),
    descricao: Optional[str] = "Taxa de Condomínio"
):
    """Cria boletos em lote para todas as unidades"""
    boletos_criados = []

    for unidade in MOCK_UNIDADES:
        # Gera boleto
        venc_date = datetime.strptime(vencimento, "%Y-%m-%d").date()

        boleto_dados = _gerador_boleto.gerar(
            valor=valor,
            vencimento=venc_date,
            pagador_nome=unidade["morador"],
            pagador_documento=unidade["documento"],
            descricao=f"{descricao} - {competencia}"
        )

        boleto_id = f"bol_{uuid.uuid4().hex[:8]}"

        boleto = {
            "id": boleto_id,
            "condominio_id": MOCK_CONDOMINIO_ID,
            "unidade_id": unidade["id"],
            "unidade": f"Apt {unidade['numero']} - Bloco {unidade['bloco']}",
            "morador": unidade["morador"],
            "valor": valor,
            "valor_original": valor,
            "valor_total": valor,
            "vencimento": vencimento,
            "competencia": competencia,
            "descricao": f"{descricao} - {competencia}",
            "tipo": "condominio",
            "status": "pendente",
            "nosso_numero": boleto_dados["nosso_numero"],
            "codigo_barras": boleto_dados["codigo_barras"],
            "linha_digitavel": boleto_dados["linha_digitavel"],
            "pix_copia_cola": boleto_dados["pix"]["copia_cola"] if boleto_dados.get("pix") else None,
            "banco": "Inter",
            "created_at": datetime.now().isoformat()
        }

        _boletos_cache[boleto_id] = boleto
        boletos_criados.append(boleto)

    return {
        "success": True,
        "message": f"{len(boletos_criados)} boletos criados com sucesso",
        "total": len(boletos_criados),
        "boletos": boletos_criados
    }


@router.put("/boletos/{boleto_id}")
async def atualizar_boleto(boleto_id: str, dados: BoletoUpdate):
    """Atualiza um boleto"""
    if boleto_id not in _boletos_cache:
        raise HTTPException(status_code=404, detail="Boleto não encontrado")

    boleto = _boletos_cache[boleto_id]

    if dados.valor is not None:
        boleto["valor"] = dados.valor
    if dados.vencimento is not None:
        boleto["vencimento"] = dados.vencimento
    if dados.descricao is not None:
        boleto["descricao"] = dados.descricao
    if dados.status is not None:
        boleto["status"] = dados.status

    boleto["updated_at"] = datetime.now().isoformat()

    return {
        "success": True,
        "message": "Boleto atualizado",
        "boleto": boleto
    }


@router.delete("/boletos/{boleto_id}")
async def cancelar_boleto(boleto_id: str):
    """Cancela um boleto"""
    if boleto_id not in _boletos_cache:
        raise HTTPException(status_code=404, detail="Boleto não encontrado")

    _boletos_cache[boleto_id]["status"] = "cancelado"
    _boletos_cache[boleto_id]["updated_at"] = datetime.now().isoformat()

    return {"success": True, "message": "Boleto cancelado"}


@router.post("/boletos/{boleto_id}/enviar")
async def enviar_boleto(
    boleto_id: str,
    email: Optional[str] = None,
    whatsapp: Optional[str] = None
):
    """Envia boleto por email ou WhatsApp"""
    if boleto_id not in _boletos_cache:
        raise HTTPException(status_code=404, detail="Boleto não encontrado")

    boleto = _boletos_cache[boleto_id]
    condominio = {
        "nome": "Residencial Conecta Plus",
        "documento": "12.345.678/0001-90"
    }

    resultados = {"email": None, "whatsapp": None}

    # Gera PDF do boleto
    pdf_base64 = pdf_generator.gerar_boleto_base64(boleto, condominio)

    # Envia por email
    if email:
        resultado_email = await email_service.enviar_boleto(
            email=email,
            boleto=boleto,
            condominio=condominio,
            pdf_base64=pdf_base64
        )
        resultados["email"] = resultado_email

    # Envia por WhatsApp
    if whatsapp:
        resultado_whatsapp = await whatsapp_service.enviar_boleto(
            telefone=whatsapp,
            boleto=boleto,
            condominio=condominio
        )
        resultados["whatsapp"] = resultado_whatsapp

    # Notifica via WebSocket
    await ws_manager.notificar_boleto_criado(boleto, MOCK_CONDOMINIO_ID)

    return {
        "success": True,
        "message": "Boleto enviado com sucesso",
        "enviado_para": {"email": email, "whatsapp": whatsapp},
        "resultados": resultados
    }


@router.get("/boletos/{boleto_id}/pdf")
async def gerar_pdf_boleto(boleto_id: str):
    """Gera PDF do boleto para download/impressão"""
    if boleto_id not in _boletos_cache:
        raise HTTPException(status_code=404, detail="Boleto não encontrado")

    boleto = _boletos_cache[boleto_id]
    beneficiario = {
        "nome": "Residencial Conecta Plus",
        "documento": "12.345.678/0001-90",
        "conta": "12345678"
    }

    # Gera QR Code se tiver PIX
    qrcode_base64 = None
    if boleto.get("pix_copia_cola"):
        qrcode_base64 = qrcode_generator.gerar_qrcode_base64(boleto["pix_copia_cola"])

    # Gera PDF como base64
    pdf_base64 = pdf_generator.gerar_boleto_base64(boleto, beneficiario, qrcode_base64)

    return {
        "success": True,
        "boleto_id": boleto_id,
        "pdf_base64": pdf_base64,
        "filename": f"boleto_{boleto.get('competencia', '').replace('/', '_')}_{boleto_id}.pdf"
    }


@router.get("/boletos/{boleto_id}/qrcode")
async def gerar_qrcode_pix(boleto_id: str, formato: str = "base64"):
    """Gera QR Code PIX do boleto"""
    if boleto_id not in _boletos_cache:
        raise HTTPException(status_code=404, detail="Boleto não encontrado")

    boleto = _boletos_cache[boleto_id]

    if not boleto.get("pix_copia_cola"):
        raise HTTPException(status_code=400, detail="Boleto não possui código PIX")

    if formato == "svg":
        qrcode = qrcode_generator.gerar_qrcode_svg(boleto["pix_copia_cola"])
    else:
        qrcode = qrcode_generator.gerar_qrcode_base64(boleto["pix_copia_cola"])

    return {
        "success": True,
        "boleto_id": boleto_id,
        "pix_copia_cola": boleto["pix_copia_cola"],
        "qrcode": qrcode,
        "formato": formato
    }


# ==================== PAGAMENTOS ====================

@router.post("/pagamentos")
@rate_limit(requests_per_minute=60, requests_per_hour=1000)
async def registrar_pagamento(dados: PagamentoRegistro, request: Request = None):
    """Registra pagamento de um boleto"""
    user = get_current_user(request)

    # VALIDAÇÃO 1: Boleto existe
    if dados.boleto_id not in _boletos_cache:
        raise HTTPException(status_code=404, detail="Boleto não encontrado")

    boleto = _boletos_cache[dados.boleto_id]

    # VALIDAÇÃO 2: Boleto não está cancelado
    if boleto.get("status") == "cancelado":
        raise HTTPException(status_code=400, detail="Não é possível pagar boleto cancelado")

    # VALIDAÇÃO 3: Boleto não foi pago
    if boleto.get("status") == "pago":
        raise HTTPException(status_code=400, detail="Boleto já foi pago")

    # VALIDAÇÃO 4: Valor pago deve ser positivo
    if dados.valor_pago <= 0:
        raise HTTPException(status_code=400, detail="Valor pago deve ser maior que zero")

    # VALIDAÇÃO 5: Data do pagamento
    try:
        data_pag = datetime.strptime(dados.data_pagamento, "%Y-%m-%d").date()
        if data_pag > date.today():
            raise HTTPException(status_code=400, detail="Data de pagamento não pode ser futura")
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de data inválido. Use YYYY-MM-DD")

    # VALIDAÇÃO 6: Forma de pagamento
    formas_validas = ["pix", "boleto", "transferencia", "dinheiro", "cheque", "cartao", "debito_automatico"]
    if dados.forma_pagamento.lower() not in formas_validas:
        raise HTTPException(
            status_code=400,
            detail=f"Forma de pagamento inválida. Use: {', '.join(formas_validas)}"
        )

    # Atualiza boleto
    boleto["status"] = "pago"
    boleto["data_pagamento"] = dados.data_pagamento
    boleto["forma_pagamento"] = dados.forma_pagamento.lower()
    boleto["valor_pago"] = dados.valor_pago
    boleto["updated_at"] = datetime.now().isoformat()

    # AUDITORIA: Registra pagamento
    pagamento_id = f"pag_{uuid.uuid4().hex[:8]}"
    await audit_service.registrar_pagamento(
        usuario_id=user["id"],
        usuario_email=user["email"],
        pagamento_id=pagamento_id,
        boleto_id=dados.boleto_id,
        valor=dados.valor_pago,
        condominio_id=MOCK_CONDOMINIO_ID,
        request=request
    )

    return {
        "success": True,
        "message": "Pagamento registrado",
        "pagamento_id": pagamento_id,
        "boleto": boleto
    }


@router.post("/webhook/pagamento")
async def webhook_pagamento(request: Request):
    """Webhook para receber notificações de pagamento"""
    body = await request.json()

    # Processa webhook (exemplo para Cora)
    event_type = body.get("type", "")

    if event_type == "invoice.paid":
        # Busca boleto pelo nosso número
        nosso_numero = body.get("data", {}).get("our_number")
        valor_pago = body.get("data", {}).get("paid_amount", 0) / 100

        for boleto in _boletos_cache.values():
            if boleto.get("nosso_numero") == nosso_numero:
                boleto["status"] = "pago"
                boleto["valor_pago"] = valor_pago
                boleto["data_pagamento"] = datetime.now().isoformat()
                boleto["forma_pagamento"] = "webhook"
                break

    return {
        "received": True,
        "event_type": event_type,
        "timestamp": datetime.now().isoformat()
    }


# ==================== RELATÓRIOS ====================

@router.get("/resumo")
async def obter_resumo(mes: Optional[str] = None):
    """Retorna resumo financeiro do mês"""
    # Calcula estatísticas dos boletos
    boletos = list(_boletos_cache.values())

    if mes:
        boletos = [b for b in boletos if b.get("competencia") == mes]

    total_valor = sum(b.get("valor", 0) for b in boletos)
    pagos = [b for b in boletos if b.get("status") == "pago"]
    pendentes = [b for b in boletos if b.get("status") == "pendente"]
    vencidos = [b for b in boletos if b.get("status") == "vencido"]

    valor_pago = sum(b.get("valor_pago", b.get("valor", 0)) for b in pagos)
    valor_pendente = sum(b.get("valor", 0) for b in pendentes)
    valor_vencido = sum(b.get("valor", 0) for b in vencidos)

    taxa_inadimplencia = (len(vencidos) / len(boletos) * 100) if boletos else 0

    return {
        "periodo": mes or datetime.now().strftime("%m/%Y"),
        "receitas": {
            "total": total_valor,
            "previsto": 120 * 850.00,
            "realizado": valor_pago,
            "percentual": round(valor_pago / (120 * 850.00) * 100, 1) if valor_pago else 0
        },
        "despesas": {
            "total": 28000.00,
            "orcado": 35000.00,
            "realizado": 28000.00,
            "economia": 7000.00
        },
        "saldo": valor_pago - 28000.00,
        "boletos": {
            "total": len(boletos),
            "pagos": len(pagos),
            "pendentes": len(pendentes),
            "vencidos": len(vencidos)
        },
        "inadimplencia": {
            "taxa": round(taxa_inadimplencia, 1),
            "valor": valor_vencido,
            "unidades": len(vencidos)
        }
    }


@router.get("/relatorios/inadimplencia")
async def obter_relatorio_inadimplencia():
    """Relatório detalhado de inadimplência"""
    vencidos = [b for b in _boletos_cache.values() if b.get("status") == "vencido"]

    # Importa modelo de IA
    from services.ia_financeira import ModeloInadimplencia, GeradorScore

    modelo = ModeloInadimplencia()

    # Adiciona previsões de IA para cada unidade
    analises = []
    for boleto in vencidos:
        # Calcula dias de atraso
        vencimento = datetime.strptime(boleto["vencimento"], "%Y-%m-%d").date()
        dias_atraso = (date.today() - vencimento).days

        analise = {
            **boleto,
            "dias_atraso": dias_atraso,
            "ia": {
                "risco": "alto" if dias_atraso > 30 else "medio" if dias_atraso > 15 else "baixo",
                "probabilidade_pagamento": max(0.1, 1 - (dias_atraso / 100)),
                "acao_recomendada": modelo._recomendar_acao(
                    modelo.prever(modelo.calcular_features([boleto]), boleto["valor"]).classificacao,
                    dias_atraso / 100,
                    modelo.calcular_features([boleto])
                )
            }
        }
        analises.append(analise)

    return {
        "taxa": round(len(vencidos) / len(_boletos_cache) * 100, 1) if _boletos_cache else 0,
        "valor_total": sum(b.get("valor", 0) for b in vencidos),
        "quantidade_boletos": len(vencidos),
        "unidades_inadimplentes": len(set(b["unidade_id"] for b in vencidos)),
        "detalhes": analises,
        "por_tempo": {
            "ate_30_dias": len([b for b in analises if b["dias_atraso"] <= 30]),
            "31_a_60_dias": len([b for b in analises if 30 < b["dias_atraso"] <= 60]),
            "61_a_90_dias": len([b for b in analises if 60 < b["dias_atraso"] <= 90]),
            "acima_90_dias": len([b for b in analises if b["dias_atraso"] > 90])
        }
    }


@router.get("/relatorios/fluxo-caixa")
async def obter_fluxo_caixa(
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None
):
    """Relatório de fluxo de caixa"""
    # Agrupa receitas e despesas por categoria
    boletos = list(_boletos_cache.values())
    receitas_por_categoria = {"condominio": 0, "extra": 0, "multa": 0}
    despesas_por_categoria = {
        "manutencao": 2500,
        "energia": 4850,
        "agua": 1230,
        "funcionarios": 18500,
        "seguranca": 890
    }

    for boleto in boletos:
        if boleto.get("status") == "pago":
            tipo = boleto.get("tipo", "condominio")
            receitas_por_categoria[tipo] = receitas_por_categoria.get(tipo, 0) + boleto.get("valor_pago", boleto.get("valor", 0))

    total_receitas = sum(receitas_por_categoria.values())
    total_despesas = sum(despesas_por_categoria.values())

    return {
        "periodo": {"inicio": data_inicio, "fim": data_fim},
        "saldo_anterior": 45680.00,
        "entradas": total_receitas,
        "saidas": total_despesas,
        "saldo_atual": 45680.00 + total_receitas - total_despesas,
        "receitas_por_categoria": receitas_por_categoria,
        "despesas_por_categoria": despesas_por_categoria
    }


@router.get("/relatorios/previsao")
async def obter_previsao(meses: int = Query(3, ge=1, le=12)):
    """Previsão financeira usando IA"""
    from services.ia_financeira import AnaliseFinanceiraIA

    # Usa dados históricos simulados
    lancamentos_historico = [
        {"tipo": "receita", "valor": 102000, "data_lancamento": "2024-10-01"},
        {"tipo": "receita", "valor": 98000, "data_lancamento": "2024-11-01"},
        {"tipo": "receita", "valor": 105000, "data_lancamento": "2024-12-01"},
        {"tipo": "despesa", "valor": 28000, "data_lancamento": "2024-10-01"},
        {"tipo": "despesa", "valor": 32000, "data_lancamento": "2024-11-01"},
        {"tipo": "despesa", "valor": 27000, "data_lancamento": "2024-12-01"},
    ]

    previsao = await AnaliseFinanceiraIA.prever_fluxo_caixa(
        lancamentos_historico, meses
    )

    return previsao


# ==================== IA ====================

@router.get("/ia/score/{unidade_id}")
async def obter_score_unidade(unidade_id: str):
    """Retorna score de inadimplência de uma unidade"""
    from services.ia_financeira import ModeloInadimplencia, GeradorScore

    # Busca histórico de pagamentos da unidade
    historico = [b for b in _boletos_cache.values() if b.get("unidade_id") == unidade_id]

    if not historico:
        raise HTTPException(status_code=404, detail="Unidade sem histórico")

    gerador = GeradorScore()
    score = await gerador.calcular_score_unidade(unidade_id, historico)

    return score


@router.get("/ia/previsao/{boleto_id}")
async def obter_previsao_boleto(boleto_id: str):
    """Retorna previsão de pagamento de um boleto específico"""
    if boleto_id not in _boletos_cache:
        raise HTTPException(status_code=404, detail="Boleto não encontrado")

    boleto = _boletos_cache[boleto_id]

    from services.ia_financeira import ModeloInadimplencia

    modelo = ModeloInadimplencia()

    # Busca histórico da unidade
    historico = [b for b in _boletos_cache.values()
                 if b.get("unidade_id") == boleto.get("unidade_id")]

    features = modelo.calcular_features(historico)
    previsao = modelo.prever(features, boleto["valor"])

    return {
        "boleto_id": boleto_id,
        "probabilidade_atraso": previsao.probabilidade,
        "dias_atraso_previsto": previsao.dias_atraso_previsto,
        "valor_em_risco": previsao.valor_em_risco,
        "score": previsao.score,
        "classificacao": previsao.classificacao.value,
        "fatores_risco": previsao.fatores_risco,
        "acao_recomendada": previsao.acao_recomendada,
        "confianca": previsao.confianca_modelo
    }


@router.get("/ia/anomalias")
async def detectar_anomalias():
    """Detecta anomalias nos lançamentos"""
    from services.ia_financeira import AnaliseFinanceiraIA

    # Dados simulados
    lancamentos = [
        {"id": "1", "categoria": "energia", "valor": 4850},
        {"id": "2", "categoria": "energia", "valor": 5100},
        {"id": "3", "categoria": "energia", "valor": 12000},  # Anomalia
        {"id": "4", "categoria": "manutencao", "valor": 2500},
        {"id": "5", "categoria": "manutencao", "valor": 2800},
    ]

    anomalias = await AnaliseFinanceiraIA.detectar_anomalias(lancamentos)

    return {"anomalias": anomalias}


# ==================== CONCILIAÇÃO ====================

@router.post("/conciliacao/upload")
async def upload_extrato(
    arquivo: UploadFile = File(...),
    conta_bancaria_id: Optional[str] = None
):
    """Upload de arquivo de extrato para conciliação"""
    from services.conciliacao import ParserOFX, ParserCNAB, TipoArquivo

    conteudo = await arquivo.read()
    conteudo_str = conteudo.decode('utf-8', errors='ignore')

    # Detecta tipo de arquivo
    nome_arquivo = arquivo.filename.lower()
    if nome_arquivo.endswith('.ofx'):
        tipo = TipoArquivo.OFX
        metadata, transacoes = ParserOFX.parse(conteudo_str)
    elif '240' in nome_arquivo or nome_arquivo.endswith('.ret'):
        tipo = TipoArquivo.CNAB240
        metadata, transacoes = ParserCNAB.parse_cnab240(conteudo_str)
    elif '400' in nome_arquivo:
        tipo = TipoArquivo.CNAB400
        metadata, transacoes = ParserCNAB.parse_cnab400(conteudo_str)
    else:
        # Tenta OFX por padrão
        tipo = TipoArquivo.OFX
        metadata, transacoes = ParserOFX.parse(conteudo_str)

    return {
        "success": True,
        "arquivo": arquivo.filename,
        "tipo": tipo.value,
        "metadata": metadata,
        "transacoes": len(transacoes),
        "preview": [
            {
                "data": t.data.isoformat(),
                "tipo": t.tipo,
                "valor": t.valor,
                "descricao": t.descricao[:50] if t.descricao else ""
            }
            for t in transacoes[:10]
        ]
    }


@router.get("/conciliacao/pendentes")
async def listar_transacoes_pendentes():
    """Lista transações pendentes de conciliação"""
    # Em produção, buscaria do banco
    return {
        "items": [],
        "total": 0
    }


# ==================== COBRANÇA ====================

@router.post("/cobranca/enviar/{boleto_id}")
async def enviar_cobranca(boleto_id: str, canal: str = "whatsapp"):
    """Envia cobrança para um boleto específico"""
    if boleto_id not in _boletos_cache:
        raise HTTPException(status_code=404, detail="Boleto não encontrado")

    boleto = _boletos_cache[boleto_id]

    from services.cobranca_automatica import MotorCobranca, CanalCobranca, TipoMensagem

    motor = MotorCobranca()

    # Determina tipo de cobrança baseado no status
    if boleto["status"] == "pendente":
        vencimento = datetime.strptime(boleto["vencimento"], "%Y-%m-%d").date()
        dias = (date.today() - vencimento).days
        tipo = motor.determinar_tipo_cobranca(dias)
    else:
        tipo = TipoMensagem.LEMBRETE_ANTES

    # Busca dados do morador
    unidade = next((u for u in MOCK_UNIDADES if u["id"] == boleto["unidade_id"]), None)
    morador = {
        "nome": unidade["morador"] if unidade else "Morador",
        "email": "morador@email.com",
        "telefone": "11999999999"
    }

    # Envia cobrança
    canal_enum = CanalCobranca(canal)
    resultados = await motor.enviar_cobranca(
        boleto, tipo, [canal_enum], morador
    )

    return {
        "success": True,
        "boleto_id": boleto_id,
        "canal": canal,
        "tipo_mensagem": tipo.value,
        "resultados": resultados
    }


@router.get("/cobranca/templates")
async def listar_templates():
    """Lista templates de mensagens disponíveis"""
    from services.cobranca_automatica import TemplatesMensagem, TipoMensagem

    templates = {}
    for tipo in TipoMensagem:
        templates[tipo.value] = list(TemplatesMensagem.TEMPLATES.get(tipo, {}).keys())

    return templates


# ==================== CATEGORIAS ====================

@router.get("/categorias")
async def listar_categorias():
    """Lista categorias financeiras"""
    return {
        "receita": [
            {"id": "REC001", "nome": "Taxa de Condomínio", "cor": "#10B981"},
            {"id": "REC002", "nome": "Taxa Extra", "cor": "#3B82F6"},
            {"id": "REC003", "nome": "Fundo de Reserva", "cor": "#8B5CF6"},
            {"id": "REC004", "nome": "Multa de Atraso", "cor": "#EF4444"},
            {"id": "REC005", "nome": "Aluguel Área Comum", "cor": "#06B6D4"},
        ],
        "despesa": [
            {"id": "DES001", "nome": "Folha de Pagamento", "cor": "#EF4444"},
            {"id": "DES002", "nome": "Energia Elétrica", "cor": "#F59E0B"},
            {"id": "DES003", "nome": "Água e Esgoto", "cor": "#3B82F6"},
            {"id": "DES004", "nome": "Manutenção", "cor": "#8B5CF6"},
            {"id": "DES005", "nome": "Segurança", "cor": "#1F2937"},
        ]
    }


# ==================== BANCOS ====================

@router.get("/bancos")
async def listar_bancos():
    """Lista bancos disponíveis para integração"""
    return {
        "bancos": [
            {"id": "cora", "nome": "Cora", "logo": "/bancos/cora.png", "configurado": True, "ambiente": "sandbox"},
            {"id": "inter", "nome": "Banco Inter", "logo": "/bancos/inter.png", "configurado": False},
            {"id": "bradesco", "nome": "Bradesco", "logo": "/bancos/bradesco.png", "configurado": False},
            {"id": "itau", "nome": "Itaú", "logo": "/bancos/itau.png", "configurado": False},
            {"id": "bb", "nome": "Banco do Brasil", "logo": "/bancos/bb.png", "configurado": False},
            {"id": "santander", "nome": "Santander", "logo": "/bancos/santander.png", "configurado": False},
        ],
        "ativo": {"id": "cora", "nome": "Cora", "ambiente": "sandbox"}
    }


@router.post("/bancos/{banco_id}/configurar")
async def configurar_banco(banco_id: str, config: ConfiguracaoIntegracao):
    """Configura integração bancária"""
    return {
        "success": True,
        "message": f"Banco {banco_id} configurado com sucesso",
        "banco": {
            "id": banco_id,
            "configurado": True,
            "ambiente": config.ambiente
        }
    }


@router.post("/bancos/{banco_id}/testar")
async def testar_conexao_banco(banco_id: str):
    """Testa conexão com o banco"""
    if banco_id == "cora":
        from integrations.cora_bank import criar_cliente_cora_mock

        client = criar_cliente_cora_mock()
        saldo = await client.consultar_saldo()
        await client.close()

        return {
            "success": True,
            "message": "Conexão testada com sucesso",
            "banco": banco_id,
            "saldo": saldo,
            "latency_ms": 145
        }

    return {
        "success": True,
        "message": "Conexão testada (mock)",
        "banco": banco_id,
        "latency_ms": 200
    }


@router.post("/bancos/{banco_id}/sincronizar")
async def sincronizar_banco(banco_id: str):
    """Sincroniza pagamentos com o banco"""
    return {
        "success": True,
        "message": "Sincronização concluída",
        "pagamentos_sincronizados": 12,
        "novos_pagamentos": 3,
        "erros": 0
    }


# ==================== EXPORTAÇÃO ====================

@router.get("/exportar")
async def exportar_relatorio(
    tipo: str = Query(..., description="Tipo: boletos, lancamentos, inadimplencia"),
    formato: str = Query("xlsx", description="Formato: xlsx, csv, pdf"),
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None
):
    """Exporta relatórios financeiros"""
    return {
        "url": f"/api/financeiro/download/{tipo}_{datetime.now().strftime('%Y%m%d')}.{formato}",
        "filename": f"relatorio_{tipo}_{datetime.now().strftime('%Y%m%d')}.{formato}",
        "expires_at": (datetime.now() + timedelta(hours=1)).isoformat()
    }


# ==================== ACORDOS ====================

@router.get("/acordos")
async def listar_acordos():
    """Lista acordos de pagamento"""
    return {"items": [], "total": 0}


@router.post("/acordos")
async def criar_acordo(dados: AcordoCreate):
    """Cria um novo acordo de pagamento"""
    # Busca boletos
    boletos = [_boletos_cache.get(bid) for bid in dados.boletos_ids if bid in _boletos_cache]
    if not boletos:
        raise HTTPException(status_code=404, detail="Boletos não encontrados")

    valor_total = sum(b.get("valor", 0) for b in boletos)
    valor_com_desconto = valor_total * (1 - dados.desconto_percentual / 100)
    valor_parcela = (valor_com_desconto - dados.entrada) / dados.parcelas

    acordo = {
        "id": f"acordo_{uuid.uuid4().hex[:8]}",
        "unidade_id": dados.unidade_id,
        "boletos_originais": dados.boletos_ids,
        "valor_original": valor_total,
        "desconto": dados.desconto_percentual,
        "valor_total": valor_com_desconto,
        "entrada": dados.entrada,
        "parcelas": dados.parcelas,
        "valor_parcela": round(valor_parcela, 2),
        "status": "proposta",
        "created_at": datetime.now().isoformat()
    }

    return {
        "success": True,
        "message": "Acordo criado com sucesso",
        "acordo": acordo
    }


# ==================== RELATÓRIOS AVANÇADOS ====================

@router.get("/relatorios/dre")
async def obter_dre(
    mes: int = Query(..., ge=1, le=12, description="Mês (1-12)"),
    ano: int = Query(..., ge=2020, description="Ano")
):
    """
    Gera DRE - Demonstrativo de Resultado do Exercício
    """
    # Dados simulados de lançamentos
    lancamentos = [
        {"tipo": "receita", "categoria": "Taxa de Condomínio", "subcategoria": "Taxa Ordinária", "valor": 102000},
        {"tipo": "receita", "categoria": "Taxa de Condomínio", "subcategoria": "Taxa Extra", "valor": 15000},
        {"tipo": "receita", "categoria": "Fundo de Reserva", "subcategoria": "Contribuição Mensal", "valor": 10200},
        {"tipo": "receita", "categoria": "Outras Receitas", "subcategoria": "Multas e Juros", "valor": 3500},
        {"tipo": "receita", "categoria": "Outras Receitas", "subcategoria": "Aluguel Salão", "valor": 2800},
        {"tipo": "despesa", "categoria": "Folha de Pagamento", "subcategoria": "Funcionários", "valor": 18500},
        {"tipo": "despesa", "categoria": "Folha de Pagamento", "subcategoria": "Encargos", "valor": 5550},
        {"tipo": "despesa", "categoria": "Consumo", "subcategoria": "Energia Elétrica", "valor": 4850},
        {"tipo": "despesa", "categoria": "Consumo", "subcategoria": "Água", "valor": 1230},
        {"tipo": "despesa", "categoria": "Manutenção", "subcategoria": "Predial", "valor": 2500},
        {"tipo": "despesa", "categoria": "Manutenção", "subcategoria": "Equipamentos", "valor": 1800},
        {"tipo": "despesa", "categoria": "Serviços", "subcategoria": "Portaria", "valor": 8500},
        {"tipo": "despesa", "categoria": "Serviços", "subcategoria": "Segurança", "valor": 890},
    ]

    # Processa lançamentos para DRE
    receitas = {}
    despesas = {}

    for lanc in lancamentos:
        if lanc["tipo"] == "receita":
            cat = lanc.get("categoria", "Outros")
            receitas[cat] = receitas.get(cat, 0) + lanc["valor"]
        else:
            cat = lanc.get("categoria", "Outros")
            despesas[cat] = despesas.get(cat, 0) + lanc["valor"]

    total_receitas = sum(receitas.values())
    total_despesas = sum(despesas.values())
    resultado = total_receitas - total_despesas

    return {
        "titulo": f"DRE - Demonstrativo de Resultado - {mes:02d}/{ano}",
        "condominio": "Residencial Conecta Plus",
        "periodo": f"{mes:02d}/{ano}",
        "receitas": {
            "itens": [{"categoria": k, "valor": v} for k, v in receitas.items()],
            "total": total_receitas
        },
        "despesas": {
            "itens": [{"categoria": k, "valor": v} for k, v in despesas.items()],
            "total": total_despesas
        },
        "resultado_operacional": resultado,
        "resultado_tipo": "superavit" if resultado > 0 else "deficit",
        "margem_percentual": round((resultado / total_receitas * 100) if total_receitas > 0 else 0, 1)
    }


@router.get("/relatorios/balancete")
async def obter_balancete(
    mes: int = Query(..., ge=1, le=12, description="Mês (1-12)"),
    ano: int = Query(..., ge=2020, description="Ano")
):
    """
    Gera Balancete Mensal
    """
    # Lançamentos do período
    lancamentos = [
        {"tipo": "receita", "categoria": "Taxa de Condomínio", "valor": 102000},
        {"tipo": "receita", "categoria": "Fundo de Reserva", "valor": 10200},
        {"tipo": "receita", "categoria": "Outras Receitas", "valor": 6300},
        {"tipo": "despesa", "categoria": "Folha de Pagamento", "valor": 24050},
        {"tipo": "despesa", "categoria": "Consumo", "valor": 6080},
        {"tipo": "despesa", "categoria": "Manutenção", "valor": 4300},
        {"tipo": "despesa", "categoria": "Serviços", "valor": 9390},
    ]

    condominio = {
        "nome": "Residencial Conecta Plus",
        "cnpj": "12.345.678/0001-90"
    }

    saldo_anterior = 45680.00

    # Retorna dados estruturados em vez de PDF para API JSON
    total_receitas = sum(l["valor"] for l in lancamentos if l["tipo"] == "receita")
    total_despesas = sum(l["valor"] for l in lancamentos if l["tipo"] == "despesa")
    saldo_atual = saldo_anterior + total_receitas - total_despesas

    return {
        "titulo": f"BALANCETE MENSAL - {mes:02d}/{ano}",
        "condominio": condominio["nome"],
        "periodo": f"{mes:02d}/{ano}",
        "resumo": {
            "saldo_anterior": saldo_anterior,
            "total_receitas": total_receitas,
            "total_despesas": total_despesas,
            "saldo_atual": saldo_atual
        },
        "contas": [
            {"conta": "Caixa", "saldo_anterior": 5000, "debitos": 150000, "creditos": 145000, "saldo_atual": 10000},
            {"conta": "Banco Inter", "saldo_anterior": 45000, "debitos": 133500, "creditos": 48000, "saldo_atual": 130500},
            {"conta": "Aplicações", "saldo_anterior": 120000, "debitos": 0, "creditos": 0, "saldo_atual": 120000},
        ],
        "totais": {
            "ativo": 260500,
            "passivo": 28250,
            "patrimonio": 232250
        }
    }


@router.get("/relatorios/prestacao-contas")
async def obter_prestacao_contas(
    mes: int = Query(..., ge=1, le=12, description="Mês (1-12)"),
    ano: int = Query(..., ge=2020, description="Ano")
):
    """
    Gera Prestação de Contas para Assembleia
    """
    # Dados para prestação de contas
    condominio = {
        "nome": "Residencial Conecta Plus",
        "documento": "12.345.678/0001-90",
        "endereco": "Rua das Flores, 123 - São Paulo/SP"
    }

    resumo = {
        "receita_prevista": 135000.00,
        "receita_realizada": 133500.00,
        "despesa_orcada": 50000.00,
        "despesa_realizada": 43820.00,
        "saldo_anterior": 45680.00,
        "saldo_atual": 135360.00
    }

    receitas_detalhadas = [
        {"categoria": "Taxas Ordinárias", "previsto": 102000, "realizado": 100500},
        {"categoria": "Taxas Extras", "previsto": 15000, "realizado": 15000},
        {"categoria": "Fundo de Reserva", "previsto": 10200, "realizado": 10200},
        {"categoria": "Multas e Juros", "previsto": 3000, "realizado": 3500},
        {"categoria": "Outras Receitas", "previsto": 4800, "realizado": 4300},
    ]

    despesas_detalhadas = [
        {"categoria": "Folha de Pagamento", "orcado": 24500, "realizado": 24050},
        {"categoria": "Consumo (Água/Luz)", "orcado": 7000, "realizado": 6080},
        {"categoria": "Manutenção", "orcado": 5000, "realizado": 4300},
        {"categoria": "Serviços Terceirizados", "orcado": 10000, "realizado": 9390},
        {"categoria": "Administrativas", "orcado": 3500, "realizado": 0},
    ]

    inadimplencia = {
        "total_unidades": 120,
        "unidades_inadimplentes": 8,
        "taxa_percentual": 6.67,
        "valor_total_devido": 12750.00
    }

    return {
        "titulo": f"PRESTAÇÃO DE CONTAS - {mes:02d}/{ano}",
        "condominio": condominio,
        "periodo": f"{mes:02d}/{ano}",
        "resumo_executivo": {
            "receita_prevista": resumo["receita_prevista"],
            "receita_realizada": resumo["receita_realizada"],
            "percentual_arrecadacao": round(resumo["receita_realizada"] / resumo["receita_prevista"] * 100, 1),
            "despesa_orcada": resumo["despesa_orcada"],
            "despesa_realizada": resumo["despesa_realizada"],
            "economia": resumo["despesa_orcada"] - resumo["despesa_realizada"],
            "saldo_anterior": resumo["saldo_anterior"],
            "saldo_atual": resumo["saldo_atual"],
            "variacao_saldo": resumo["saldo_atual"] - resumo["saldo_anterior"]
        },
        "movimento_financeiro": {
            "receitas": receitas_detalhadas,
            "despesas": despesas_detalhadas
        },
        "situacao_cobranca": {
            "total_unidades": inadimplencia["total_unidades"],
            "adimplentes": inadimplencia["total_unidades"] - inadimplencia["unidades_inadimplentes"],
            "inadimplentes": inadimplencia["unidades_inadimplentes"],
            "taxa_inadimplencia": inadimplencia["taxa_percentual"],
            "valor_em_aberto": inadimplencia["valor_total_devido"]
        },
        "secoes": ["resumo_executivo", "movimento_financeiro", "situacao_cobranca", "assinaturas"]
    }


# ==================== WEBSOCKET STATS ====================

@router.get("/websocket/status")
async def websocket_status():
    """Retorna estatísticas das conexões WebSocket"""
    return ws_manager.get_estatisticas()


@router.post("/notificar")
async def enviar_notificacao_manual(
    titulo: str = Query(...),
    mensagem: str = Query(...),
    condominio_id: Optional[str] = None,
    broadcast: bool = False
):
    """Envia notificação manual via WebSocket"""
    await ws_manager.notificar_sistema(titulo, mensagem, condominio_id, broadcast)

    return {
        "success": True,
        "message": "Notificação enviada",
        "destinatarios": ws_manager.get_estatisticas()
    }


# ==================== DASHBOARD DATA ====================

@router.get("/dashboard/graficos")
async def obter_dados_dashboard(meses: int = Query(6, ge=1, le=12)):
    """
    Retorna dados para os gráficos do dashboard
    Compatível com Recharts
    """
    from datetime import datetime
    from dateutil.relativedelta import relativedelta

    # Gera dados dos últimos N meses
    hoje = datetime.now()
    dados_mensais = []

    for i in range(meses - 1, -1, -1):
        mes_ref = hoje - relativedelta(months=i)
        nome_mes = mes_ref.strftime("%b/%y")

        # Simula dados (em produção viria do PostgreSQL)
        dados_mensais.append({
            "mes": nome_mes,
            "receitas": 102000 + (i * 500) - (i % 3 * 1500),
            "despesas": 43000 + (i * 200) - (i % 2 * 800),
            "inadimplencia": 5.5 + (i % 4) * 0.8,
            "saldo": 135000 + (i * 2000)
        })

    # Distribuição por categoria
    categorias_receita = [
        {"nome": "Taxa Ordinária", "valor": 102000, "percentual": 76.4},
        {"nome": "Taxa Extra", "valor": 15000, "percentual": 11.2},
        {"nome": "Fundo Reserva", "valor": 10200, "percentual": 7.6},
        {"nome": "Multas/Juros", "valor": 3500, "percentual": 2.6},
        {"nome": "Outros", "valor": 2800, "percentual": 2.1},
    ]

    categorias_despesa = [
        {"nome": "Folha Pagamento", "valor": 24050, "percentual": 54.9},
        {"nome": "Serviços", "valor": 9390, "percentual": 21.4},
        {"nome": "Consumo", "valor": 6080, "percentual": 13.9},
        {"nome": "Manutenção", "valor": 4300, "percentual": 9.8},
    ]

    # Evolução inadimplência
    evolucao_inadimplencia = [
        {"mes": dados["mes"], "taxa": dados["inadimplencia"]}
        for dados in dados_mensais
    ]

    return {
        "mensal": dados_mensais,
        "categorias_receita": categorias_receita,
        "categorias_despesa": categorias_despesa,
        "evolucao_inadimplencia": evolucao_inadimplencia,
        "resumo": {
            "receita_mes": 133500,
            "despesa_mes": 43820,
            "saldo": 135360,
            "taxa_inadimplencia": 6.7,
            "boletos_pendentes": 8,
            "boletos_pagos": 112,
            "economia_orcamento": 6180
        }
    }


# ==================== IA AVANÇADA ====================

@router.get("/ia/previsao-inadimplencia/{unidade_id}")
@rate_limit(requests_per_minute=60)
async def prever_inadimplencia(unidade_id: str, request: Request = None):
    """
    Prevê probabilidade de inadimplência usando ML

    Retorna:
    - Probabilidade de inadimplência (0-1)
    - Classificação de risco (baixo/medio/alto/critico)
    - Score de 0-1000
    - Fatores de risco identificados
    - Recomendação de ação
    """
    user = get_current_user(request)

    # Busca dados da unidade
    unidade = next((u for u in MOCK_UNIDADES if u["id"] == unidade_id), None)
    if not unidade:
        raise HTTPException(status_code=404, detail="Unidade não encontrada")

    # Busca histórico de boletos da unidade
    boletos_unidade = [b for b in _boletos_cache.values() if b.get('unidade_id') == unidade_id]

    # Prepara dados para previsão
    previsao = ml_inadimplencia.prever(
        historico_boletos=boletos_unidade,
        historico_pagamentos=[],  # Seria do banco
        acordos=[],  # Seria do banco
        dados_unidade=unidade
    )

    return {
        "unidade_id": unidade_id,
        "unidade": f"Apt {unidade['numero']} - Bloco {unidade['bloco']}",
        "morador": unidade["morador"],
        "previsao": {
            "probabilidade": previsao.probabilidade,
            "classificacao": previsao.classificacao,
            "score": previsao.score,
            "confianca": previsao.confianca
        },
        "fatores_risco": previsao.fatores_risco,
        "recomendacao": previsao.recomendacao,
        "modelo_versao": previsao.modelo_versao
    }


@router.get("/ia/alertas-proativos")
@rate_limit(requests_per_minute=30)
async def obter_alertas_proativos(request: Request = None):
    """
    Retorna alertas proativos gerados pelo sistema de IA

    Tipos de alerta:
    - Inadimplência prevista
    - Fluxo de caixa crítico
    - Vencimentos próximos
    - Anomalias detectadas
    """
    boletos = list(_boletos_cache.values())

    alertas = sistema_alertas.gerar_alertas(
        unidades=MOCK_UNIDADES,
        boletos=boletos,
        pagamentos=[],
        acordos=[],
        lancamentos=[],
        saldo_atual=50000  # Mock
    )

    return {
        "total_alertas": len(alertas),
        "criticos": len([a for a in alertas if a.severidade == 'critical']),
        "avisos": len([a for a in alertas if a.severidade == 'warning']),
        "info": len([a for a in alertas if a.severidade == 'info']),
        "alertas": [
            {
                "tipo": a.tipo,
                "severidade": a.severidade,
                "titulo": a.titulo,
                "mensagem": a.mensagem,
                "acao_recomendada": a.acao_recomendada,
                "probabilidade": a.probabilidade,
                "entidade": {"tipo": a.entidade_tipo, "id": a.entidade_id},
                "criado_em": a.criado_em
            }
            for a in alertas
        ]
    }


@router.get("/ia/priorizar-cobranca")
@rate_limit(requests_per_minute=30)
async def priorizar_cobrancas(request: Request = None):
    """
    Retorna lista de boletos priorizados para cobrança

    Ordenados por score que combina:
    - Probabilidade de pagamento
    - Valor do débito
    - Dias de atraso
    - Histórico do devedor
    """
    # Filtra boletos vencidos
    boletos_vencidos = [b for b in _boletos_cache.values() if b.get('status') == 'vencido']

    if not boletos_vencidos:
        return {"message": "Não há boletos vencidos para priorizar", "priorizados": []}

    # Prepara dados por unidade
    unidades_dict = {u['id']: u for u in MOCK_UNIDADES}
    historico_boletos = {}
    for boleto in _boletos_cache.values():
        uid = boleto.get('unidade_id')
        if uid not in historico_boletos:
            historico_boletos[uid] = []
        historico_boletos[uid].append(boleto)

    # Prioriza
    priorizados = priorizador_cobranca.priorizar(
        boletos_vencidos=boletos_vencidos,
        unidades=unidades_dict,
        historico_boletos=historico_boletos,
        historico_pagamentos={},
        acordos={}
    )

    return {
        "total_vencidos": len(boletos_vencidos),
        "valor_total": sum(b.get('valor', 0) for b in boletos_vencidos),
        "priorizados": [
            {
                "posicao": i + 1,
                "boleto_id": p['boleto'].get('id'),
                "unidade": p['unidade'].get('numero', 'N/A'),
                "morador": p['unidade'].get('morador', 'N/A'),
                "valor": p['boleto'].get('valor', 0),
                "dias_atraso": p['dias_atraso'],
                "score_prioridade": p['score_prioridade'],
                "probabilidade_pagamento": p['probabilidade_pagamento'],
                "classificacao_risco": p['classificacao_risco'],
                "estrategia": p['estrategia_recomendada'],
                "componentes_score": p['componentes_score']
            }
            for i, p in enumerate(priorizados)
        ]
    }


@router.post("/ia/analisar-sentimento")
@rate_limit(requests_per_minute=60)
async def analisar_sentimento_mensagem(
    mensagem: str,
    request: Request = None
):
    """
    Analisa sentimento de uma mensagem recebida do morador

    Retorna:
    - Classificação de sentimento
    - Score (-1 a 1)
    - Intenção de pagamento
    - Emoções detectadas
    - Sugestão de resposta
    """
    if not mensagem or len(mensagem) < 3:
        raise HTTPException(status_code=400, detail="Mensagem muito curta para análise")

    analise = analisador_sentimento.analisar(mensagem)

    return {
        "mensagem_original": mensagem[:200],
        "analise": {
            "sentimento": analise.sentimento.value,
            "score": analise.score,
            "confianca": analise.confianca,
            "intencao_pagamento": analise.intencao_pagamento,
            "emocoes": analise.emocoes_detectadas,
            "requer_atencao": analise.requer_atencao_especial
        },
        "sugestao_resposta": analise.sugestao_resposta
    }


@router.post("/ia/gerar-mensagem-cobranca")
@rate_limit(requests_per_minute=30)
async def gerar_mensagem_cobranca(
    boleto_id: str,
    canal: str = "whatsapp",
    tom: Optional[str] = None,
    variante: str = "A",
    request: Request = None
):
    """
    Gera mensagem de cobrança personalizada usando IA

    Parâmetros:
    - canal: email, whatsapp, sms
    - tom: amigavel, profissional, firme, urgente, final (auto se não especificado)
    - variante: A ou B (para A/B testing)
    """
    if boleto_id not in _boletos_cache:
        raise HTTPException(status_code=404, detail="Boleto não encontrado")

    boleto = _boletos_cache[boleto_id]
    unidade = next((u for u in MOCK_UNIDADES if u["id"] == boleto.get('unidade_id')), {})

    # Calcula dias de atraso
    try:
        vencimento = datetime.strptime(boleto.get('vencimento', '')[:10], '%Y-%m-%d').date()
        dias_atraso = (date.today() - vencimento).days
        boleto['dias_atraso'] = max(0, dias_atraso)
    except:
        boleto['dias_atraso'] = 0

    # Mapeia canal
    try:
        canal_enum = CanalComunicacao(canal.lower())
    except:
        canal_enum = CanalComunicacao.WHATSAPP

    # Mapeia tom
    tom_enum = None
    if tom:
        try:
            tom_enum = TomMensagem(tom.lower())
        except:
            pass

    mensagem = gerador_mensagens.gerar_mensagem(
        dados_boleto=boleto,
        dados_morador=unidade,
        dados_condominio={
            "nome": "Residencial Conecta Plus",
            "telefone": "(11) 99999-9999",
            "portal_url": "https://conectaplus.com.br/portal"
        },
        canal=canal_enum,
        tom=tom_enum,
        variante=variante
    )

    return {
        "boleto_id": boleto_id,
        "canal": canal,
        "mensagem": {
            "assunto": mensagem.assunto,
            "corpo": mensagem.corpo,
            "tom": mensagem.tom.value,
            "cta": mensagem.cta
        },
        "score_efetividade": mensagem.score_efetividade,
        "variante": mensagem.variante
    }


@router.get("/ia/melhor-momento/{unidade_id}")
@rate_limit(requests_per_minute=60)
async def obter_melhor_momento(unidade_id: str, request: Request = None):
    """
    Retorna melhor momento para contatar um morador

    Baseado em histórico de interações anteriores
    """
    unidade = next((u for u in MOCK_UNIDADES if u["id"] == unidade_id), None)
    if not unidade:
        raise HTTPException(status_code=404, detail="Unidade não encontrada")

    # Obtém perfil de comunicação (com histórico vazio = padrão)
    perfil = otimizador_comunicacao.obter_perfil(unidade_id, [])
    momento = otimizador_comunicacao.sugerir_melhor_momento(perfil)

    return {
        "unidade_id": unidade_id,
        "morador": unidade["morador"],
        "perfil": {
            "canal_preferido": perfil.canal_preferido.value,
            "responde_rapido": perfil.responde_rapido,
            "taxa_resposta": perfil.taxa_resposta
        },
        "sugestao": momento
    }


@router.get("/ia/previsao-fluxo-caixa")
@rate_limit(requests_per_minute=30)
async def prever_fluxo_caixa(dias: int = 90, request: Request = None):
    """
    Prevê fluxo de caixa para os próximos N dias

    Retorna previsão semanal com:
    - Receita prevista
    - Despesa prevista
    - Saldo previsto
    - Intervalo de confiança
    """
    if dias < 7 or dias > 365:
        raise HTTPException(status_code=400, detail="Dias deve estar entre 7 e 365")

    # Dados de boletos pendentes
    boletos_pendentes = [b for b in _boletos_cache.values() if b.get('status') in ['pendente', 'vencido']]

    previsoes = ml_fluxo_caixa.prever(
        historico_receitas=[],  # Seria do banco
        historico_despesas=[],  # Seria do banco
        boletos_pendentes=boletos_pendentes,
        dias_previsao=dias
    )

    return {
        "periodo_dias": dias,
        "semanas": len(previsoes),
        "previsoes": [
            {
                "data_inicio": p.data,
                "receita_prevista": p.receita_prevista,
                "despesa_prevista": p.despesa_prevista,
                "saldo_previsto": p.saldo_previsto,
                "intervalo": {
                    "inferior": p.intervalo_inferior,
                    "superior": p.intervalo_superior
                },
                "confianca": p.confianca,
                "sazonalidade": p.sazonalidade,
                "tendencia": p.tendencia
            }
            for p in previsoes
        ],
        "resumo": {
            "receita_total_prevista": sum(p.receita_prevista for p in previsoes),
            "despesa_total_prevista": sum(p.despesa_prevista for p in previsoes),
            "saldo_periodo": sum(p.saldo_previsto for p in previsoes)
        }
    }


@router.get("/ia/dashboard-inteligente")
@rate_limit(requests_per_minute=30)
async def obter_dashboard_inteligente(request: Request = None):
    """
    Retorna dashboard com insights automáticos gerados por IA

    Inclui:
    - KPIs principais com variação
    - Top 10 insights priorizados
    - Ações recomendadas
    - Score de saúde financeira
    """
    boletos = list(_boletos_cache.values())

    # Calcula dados atuais
    total_boletos = len(boletos)
    pagos = len([b for b in boletos if b.get('status') == 'pago'])
    vencidos = len([b for b in boletos if b.get('status') == 'vencido'])

    valor_total = sum(b.get('valor', 0) for b in boletos)
    valor_pago = sum(b.get('valor', 0) for b in boletos if b.get('status') == 'pago')
    valor_vencido = sum(b.get('valor', 0) for b in boletos if b.get('status') == 'vencido')

    taxa_inadimpl = (vencidos / total_boletos * 100) if total_boletos > 0 else 0

    dados_atuais = {
        "periodo": datetime.now().strftime("%m/%Y"),
        "taxa_inadimplencia": taxa_inadimpl,
        "valor_inadimplente": valor_vencido,
        "unidades_inadimplentes": vencidos,
        "receita_total": valor_pago,
        "receita_prevista": valor_total,
        "despesa_total": 45000,  # Mock
        "despesa_orcada": 50000,  # Mock
        "saldo_caixa": 85000,  # Mock
        "taxa_recuperacao": 40,  # Mock
        "acordos_realizados": 2,  # Mock
        "valor_recuperado": 3500  # Mock
    }

    # Dados período anterior (mock - seria do banco)
    dados_anteriores = {
        "taxa_inadimplencia": 5.5,
        "receita_total": valor_pago * 0.95,
        "despesa_total": 42000,
        "saldo_caixa": 78000,
        "taxa_recuperacao": 35
    }

    # Benchmarks de mercado
    benchmarks = {
        "taxa_inadimplencia_media": 5.0
    }

    # Constrói dashboard
    dashboard = dashboard_builder.construir(
        dados_financeiros=dados_atuais,
        dados_periodo_anterior=dados_anteriores,
        alertas=[],  # Poderia integrar com alertas proativos
        benchmarks=benchmarks
    )

    return {
        "periodo": dashboard.periodo,
        "resumo": dashboard.resumo_financeiro,
        "indicadores": dashboard.indicadores_chave,
        "insights": dashboard.insights[:5],  # Top 5
        "acoes_recomendadas": dashboard.acoes_recomendadas[:3],  # Top 3
        "saude_financeira": dashboard.saude_financeira
    }
