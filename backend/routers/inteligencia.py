"""
Conecta Plus - Q2: Router de Inteligencia Proativa
Endpoints para Previsoes, Sugestoes, Comunicacao e Aprendizado
"""

from datetime import datetime, timedelta
from typing import List, Optional, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.q2.prediction_engine import PredictionEngine
from ..services.q2.suggestion_engine import SuggestionEngine
from ..services.q2.communication_optimizer import CommunicationOptimizer
from ..services.q2.learning_engine import LearningEngine
from ..models import (
    TipoPrevisao, StatusPrevisao,
    TipoSugestao, StatusSugestao, PerfilDestino,
    TipoComunicacao, UrgenciaComunicacao, CanalComunicacao,
    TipoOrigem, ValorFeedback
)

router = APIRouter(prefix="/inteligencia", tags=["Q2 - Inteligencia Proativa"])


# ==========================================
# SCHEMAS
# ==========================================

class PrevisaoResponse(BaseModel):
    id: str
    tipo: str
    subtipo: str
    entidade_tipo: str
    entidade_id: Optional[str]
    entidade_nome: Optional[str]
    probabilidade: float
    confianca: float
    horizonte_dias: int
    sinais: List[Any]
    acao_recomendada: str
    status: str
    impacto_estimado: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


class ValidarPrevisaoRequest(BaseModel):
    confirmada: bool
    motivo: Optional[str] = None


class SugestaoResponse(BaseModel):
    id: str
    tipo: str
    codigo: str
    titulo: str
    descricao: str
    contexto: Optional[str]
    beneficio_estimado: Optional[str]
    perfil_destino: str
    status: str
    prioridade: int
    created_at: str

    class Config:
        from_attributes = True


class RejeitarSugestaoRequest(BaseModel):
    motivo: Optional[str] = None


class FeedbackSugestaoRequest(BaseModel):
    util: bool
    texto: Optional[str] = None
    avaliacao: Optional[int] = Field(None, ge=1, le=5)


class PreferenciasRequest(BaseModel):
    horario_preferido_inicio: Optional[str] = None
    horario_preferido_fim: Optional[str] = None
    canal_primario: Optional[str] = None
    canal_secundario: Optional[str] = None
    max_notificacoes_dia: Optional[int] = Field(None, ge=1, le=20)
    agrupar_similares: Optional[bool] = None
    receber_financeiro: Optional[bool] = None
    receber_manutencao: Optional[bool] = None
    receber_seguranca: Optional[bool] = None
    receber_comunicados: Optional[bool] = None
    receber_sugestoes: Optional[bool] = None
    nao_perturbe_ativo: Optional[bool] = None
    nao_perturbe_inicio: Optional[str] = None
    nao_perturbe_fim: Optional[str] = None


class FeedbackRequest(BaseModel):
    tipo_origem: str
    origem_id: str
    valor: str
    comentario: Optional[str] = None
    avaliacao: Optional[int] = Field(None, ge=1, le=5)


class AgendarComunicacaoRequest(BaseModel):
    tipo: str
    titulo: str
    conteudo: str
    urgencia: Optional[str] = "media"
    origem_id: Optional[str] = None
    origem_tipo: Optional[str] = None
    categoria: Optional[str] = None


# ==========================================
# PREVISOES (RF-05)
# ==========================================

@router.get("/previsoes", response_model=List[PrevisaoResponse])
async def listar_previsoes(
    condominio_id: UUID = Query(..., description="ID do condominio"),
    tipo: Optional[str] = Query(None, description="Filtrar por tipo"),
    limit: int = Query(50, le=100),
    db: Session = Depends(get_db)
):
    """Lista previsoes ativas do condominio"""
    engine = PredictionEngine(db)

    tipo_enum = TipoPrevisao(tipo) if tipo else None
    previsoes = await engine.listar_previsoes_ativas(condominio_id, tipo_enum, limit)

    return [
        PrevisaoResponse(**p.to_dict())
        for p in previsoes
    ]


@router.get("/previsoes/dashboard")
async def dashboard_previsoes(
    condominio_id: UUID = Query(..., description="ID do condominio"),
    db: Session = Depends(get_db)
):
    """Retorna dashboard de previsoes"""
    engine = PredictionEngine(db)
    return await engine.obter_dashboard(condominio_id)


@router.post("/previsoes/analisar")
async def analisar_previsoes(
    condominio_id: UUID = Query(..., description="ID do condominio"),
    db: Session = Depends(get_db)
):
    """Executa analise completa de previsoes"""
    engine = PredictionEngine(db)
    return await engine.executar_analise_completa(condominio_id)


@router.get("/previsoes/{previsao_id}")
async def obter_previsao(
    previsao_id: UUID,
    db: Session = Depends(get_db)
):
    """Obtem detalhes de uma previsao"""
    from sqlalchemy import select
    from ..models import Previsao

    stmt = select(Previsao).where(Previsao.id == previsao_id)
    result = db.execute(stmt)
    previsao = result.scalar()

    if not previsao:
        raise HTTPException(status_code=404, detail="Previsao nao encontrada")

    return previsao.to_dict()


@router.post("/previsoes/{previsao_id}/validar")
async def validar_previsao(
    previsao_id: UUID,
    dados: ValidarPrevisaoRequest,
    usuario_id: UUID = Query(..., description="ID do usuario validador"),
    db: Session = Depends(get_db)
):
    """Valida uma previsao (confirma ou marca como falso positivo)"""
    engine = PredictionEngine(db)

    try:
        previsao = await engine.validar_previsao(
            previsao_id,
            usuario_id,
            dados.confirmada,
            dados.motivo
        )
        return {"success": True, "previsao": previsao.to_dict()}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ==========================================
# SUGESTOES (RF-06)
# ==========================================

@router.get("/sugestoes", response_model=List[SugestaoResponse])
async def listar_sugestoes(
    condominio_id: UUID = Query(..., description="ID do condominio"),
    perfil: Optional[str] = Query(None, description="Filtrar por perfil destino"),
    limit: int = Query(20, le=50),
    db: Session = Depends(get_db)
):
    """Lista sugestoes pendentes do condominio"""
    engine = SuggestionEngine(db)

    perfil_enum = PerfilDestino(perfil) if perfil else None
    sugestoes = await engine.listar_sugestoes_pendentes(condominio_id, perfil_enum, limit)

    return [
        SugestaoResponse(**s.to_dict())
        for s in sugestoes
    ]


@router.post("/sugestoes/gerar")
async def gerar_sugestoes(
    condominio_id: UUID = Query(..., description="ID do condominio"),
    db: Session = Depends(get_db)
):
    """Gera novas sugestoes para o condominio"""
    engine = SuggestionEngine(db)
    return await engine.gerar_sugestoes(condominio_id)


@router.get("/sugestoes/{sugestao_id}")
async def obter_sugestao(
    sugestao_id: UUID,
    db: Session = Depends(get_db)
):
    """Obtem detalhes de uma sugestao"""
    from sqlalchemy import select
    from ..models import Sugestao

    stmt = select(Sugestao).where(Sugestao.id == sugestao_id)
    result = db.execute(stmt)
    sugestao = result.scalar()

    if not sugestao:
        raise HTTPException(status_code=404, detail="Sugestao nao encontrada")

    return sugestao.to_dict()


@router.post("/sugestoes/{sugestao_id}/aceitar")
async def aceitar_sugestao(
    sugestao_id: UUID,
    usuario_id: UUID = Query(..., description="ID do usuario"),
    db: Session = Depends(get_db)
):
    """Aceita uma sugestao"""
    engine = SuggestionEngine(db)

    try:
        sugestao = await engine.aceitar_sugestao(sugestao_id, usuario_id)
        return {"success": True, "sugestao": sugestao.to_dict()}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/sugestoes/{sugestao_id}/rejeitar")
async def rejeitar_sugestao(
    sugestao_id: UUID,
    dados: RejeitarSugestaoRequest,
    usuario_id: UUID = Query(..., description="ID do usuario"),
    db: Session = Depends(get_db)
):
    """Rejeita uma sugestao"""
    engine = SuggestionEngine(db)

    try:
        sugestao = await engine.rejeitar_sugestao(sugestao_id, usuario_id, dados.motivo)
        return {"success": True, "sugestao": sugestao.to_dict()}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/sugestoes/{sugestao_id}/feedback")
async def feedback_sugestao(
    sugestao_id: UUID,
    dados: FeedbackSugestaoRequest,
    db: Session = Depends(get_db)
):
    """Registra feedback sobre uma sugestao"""
    engine = SuggestionEngine(db)

    try:
        sugestao = await engine.registrar_feedback(
            sugestao_id,
            dados.util,
            dados.texto,
            dados.avaliacao
        )
        return {"success": True, "sugestao": sugestao.to_dict()}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ==========================================
# COMUNICACAO (RF-07)
# ==========================================

@router.get("/comunicacao/preferencias")
async def obter_preferencias(
    usuario_id: UUID = Query(..., description="ID do usuario"),
    db: Session = Depends(get_db)
):
    """Obtem preferencias de comunicacao do usuario"""
    optimizer = CommunicationOptimizer(db)
    return await optimizer.obter_preferencias(usuario_id)


@router.put("/comunicacao/preferencias")
async def atualizar_preferencias(
    usuario_id: UUID = Query(..., description="ID do usuario"),
    dados: PreferenciasRequest = Body(...),
    db: Session = Depends(get_db)
):
    """Atualiza preferencias de comunicacao"""
    optimizer = CommunicationOptimizer(db)

    preferencias = await optimizer.atualizar_preferencias(
        usuario_id,
        dados.model_dump(exclude_none=True)
    )

    return {"success": True, "preferencias": preferencias.to_dict()}


@router.get("/comunicacao/historico")
async def obter_historico(
    usuario_id: UUID = Query(..., description="ID do usuario"),
    limit: int = Query(50, le=100),
    offset: int = Query(0),
    db: Session = Depends(get_db)
):
    """Obtem historico de comunicacoes do usuario"""
    optimizer = CommunicationOptimizer(db)
    historico = await optimizer.obter_historico(usuario_id, limit, offset)

    return [h.to_dict() for h in historico]


@router.get("/comunicacao/metricas")
async def metricas_comunicacao(
    condominio_id: UUID = Query(..., description="ID do condominio"),
    db: Session = Depends(get_db)
):
    """Retorna metricas de comunicacao do condominio"""
    optimizer = CommunicationOptimizer(db)
    return await optimizer.obter_metricas(condominio_id)


@router.post("/comunicacao/agendar")
async def agendar_comunicacao(
    usuario_id: UUID = Query(..., description="ID do usuario destinatario"),
    condominio_id: UUID = Query(..., description="ID do condominio"),
    dados: AgendarComunicacaoRequest = Body(...),
    db: Session = Depends(get_db)
):
    """Agenda uma comunicacao com otimizacao de timing e canal"""
    optimizer = CommunicationOptimizer(db)

    item = await optimizer.agendar_comunicacao(
        usuario_id=usuario_id,
        condominio_id=condominio_id,
        tipo=TipoComunicacao(dados.tipo),
        titulo=dados.titulo,
        conteudo=dados.conteudo,
        urgencia=UrgenciaComunicacao(dados.urgencia) if dados.urgencia else UrgenciaComunicacao.MEDIA,
        origem_id=UUID(dados.origem_id) if dados.origem_id else None,
        origem_tipo=dados.origem_tipo,
        categoria=dados.categoria
    )

    return {
        "success": True,
        "item_id": str(item.id),
        "canal": item.canal.value,
        "agendar_para": item.agendar_para.isoformat() if item.agendar_para else None
    }


@router.post("/comunicacao/processar-fila")
async def processar_fila(
    limit: int = Query(50, le=100),
    db: Session = Depends(get_db)
):
    """Processa fila de comunicacoes pendentes"""
    optimizer = CommunicationOptimizer(db)
    return await optimizer.processar_fila(limit)


@router.post("/comunicacao/{historico_id}/abertura")
async def registrar_abertura(
    historico_id: UUID,
    db: Session = Depends(get_db)
):
    """Registra que usuario abriu a comunicacao"""
    optimizer = CommunicationOptimizer(db)
    await optimizer.registrar_abertura(historico_id)
    return {"success": True}


@router.post("/comunicacao/{historico_id}/clique")
async def registrar_clique(
    historico_id: UUID,
    db: Session = Depends(get_db)
):
    """Registra que usuario clicou na comunicacao"""
    optimizer = CommunicationOptimizer(db)
    await optimizer.registrar_clique(historico_id)
    return {"success": True}


# ==========================================
# APRENDIZADO (RF-08)
# ==========================================

@router.post("/feedback")
async def registrar_feedback(
    condominio_id: UUID = Query(..., description="ID do condominio"),
    usuario_id: Optional[UUID] = Query(None, description="ID do usuario"),
    dados: FeedbackRequest = Body(...),
    db: Session = Depends(get_db)
):
    """Registra feedback sobre previsao, sugestao ou comunicacao"""
    engine = LearningEngine(db)

    feedback = await engine.registrar_feedback(
        condominio_id=condominio_id,
        tipo_origem=TipoOrigem(dados.tipo_origem),
        origem_id=UUID(dados.origem_id),
        valor=ValorFeedback(dados.valor),
        usuario_id=usuario_id,
        comentario=dados.comentario,
        avaliacao=dados.avaliacao
    )

    return {"success": True, "feedback_id": str(feedback.id)}


@router.post("/aprendizado/coletar")
async def coletar_feedback_automatico(
    condominio_id: UUID = Query(..., description="ID do condominio"),
    db: Session = Depends(get_db)
):
    """Coleta feedback automatico de eventos do sistema"""
    engine = LearningEngine(db)
    return await engine.coletar_feedback_automatico(condominio_id)


@router.get("/aprendizado/dashboard")
async def dashboard_aprendizado(
    condominio_id: Optional[UUID] = Query(None, description="ID do condominio (opcional)"),
    db: Session = Depends(get_db)
):
    """Retorna dashboard de aprendizado"""
    engine = LearningEngine(db)
    return await engine.obter_dashboard(condominio_id)


@router.get("/metricas/modelo/{modelo}")
async def metricas_modelo(
    modelo: str,
    limite: int = Query(10, le=50),
    db: Session = Depends(get_db)
):
    """Retorna historico de metricas de um modelo"""
    engine = LearningEngine(db)
    metricas = await engine.obter_metricas_modelo(modelo, limite)

    return [m.to_dict() for m in metricas]


@router.post("/metricas/calcular")
async def calcular_metricas(
    modelo: str = Query(..., description="Nome do modelo"),
    dias: int = Query(30, description="Periodo em dias"),
    condominio_id: Optional[UUID] = Query(None, description="ID do condominio"),
    db: Session = Depends(get_db)
):
    """Calcula metricas de um modelo para um periodo"""
    engine = LearningEngine(db)

    periodo_fim = datetime.utcnow()
    periodo_inicio = periodo_fim - timedelta(days=dias)

    metrica = await engine.calcular_metricas_periodo(
        modelo,
        periodo_inicio,
        periodo_fim,
        condominio_id
    )

    return metrica.to_dict()


@router.get("/metricas/comparar")
async def comparar_versoes(
    modelo: str = Query(..., description="Nome do modelo"),
    versao_a: str = Query(..., description="Versao A"),
    versao_b: str = Query(..., description="Versao B"),
    db: Session = Depends(get_db)
):
    """Compara metricas entre duas versoes de um modelo"""
    engine = LearningEngine(db)
    return await engine.comparar_versoes(modelo, versao_a, versao_b)
