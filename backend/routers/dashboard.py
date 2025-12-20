"""
Conecta Plus - Router do Dashboard
"""

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..database import get_db
from ..dependencies import get_current_user
from ..models.usuario import Usuario
from ..models.ocorrencia import Ocorrencia, StatusOcorrencia
from ..models.manutencao import OrdemServico, StatusOS
from ..models.financeiro import Boleto, StatusBoleto
from ..models.acesso import RegistroAcesso, PontoAcesso
from ..models.alarme import EventoAlarme, ZonaAlarme
from ..models.unidade import Unidade

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/resumo")
async def resumo_geral(
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retorna resumo geral para o dashboard."""
    condominio_id = current_user.condominio_id
    hoje = datetime.now().date()
    inicio_mes = hoje.replace(day=1)

    # Total de unidades
    total_unidades = db.query(Unidade).filter(
        Unidade.condominio_id == condominio_id
    ).count()

    # Ocorrências abertas
    ocorrencias_abertas = db.query(Ocorrencia).join(Unidade).filter(
        Unidade.condominio_id == condominio_id,
        Ocorrencia.status.in_([StatusOcorrencia.ABERTA, StatusOcorrencia.EM_ANDAMENTO])
    ).count()

    # OS em andamento
    os_andamento = db.query(OrdemServico).filter(
        OrdemServico.status.in_([StatusOS.ABERTA, StatusOS.EM_ANDAMENTO])
    ).count()

    # Inadimplência
    boletos_vencidos = db.query(Boleto).filter(
        Boleto.condominio_id == condominio_id,
        Boleto.status == StatusBoleto.VENCIDO
    ).count()

    # Acessos hoje
    acessos_hoje = db.query(RegistroAcesso).join(PontoAcesso).filter(
        PontoAcesso.condominio_id == condominio_id,
        func.date(RegistroAcesso.data_hora) == hoje
    ).count()

    # Alertas (eventos de alarme não tratados)
    alertas_pendentes = db.query(EventoAlarme).join(ZonaAlarme).filter(
        ZonaAlarme.condominio_id == condominio_id,
        EventoAlarme.tratado == False
    ).count()

    return {
        "total_unidades": total_unidades,
        "ocorrencias_abertas": ocorrencias_abertas,
        "os_andamento": os_andamento,
        "boletos_vencidos": boletos_vencidos,
        "inadimplencia_percentual": round((boletos_vencidos / total_unidades * 100), 1) if total_unidades > 0 else 0,
        "acessos_hoje": acessos_hoje,
        "alertas_pendentes": alertas_pendentes
    }


@router.get("/ocorrencias-recentes")
async def ocorrencias_recentes(
    limite: int = 5,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retorna ocorrências recentes."""
    ocorrencias = db.query(Ocorrencia).join(Unidade).filter(
        Unidade.condominio_id == current_user.condominio_id
    ).order_by(Ocorrencia.data_abertura.desc()).limit(limite).all()

    return [
        {
            "id": o.id,
            "protocolo": o.protocolo,
            "titulo": o.titulo,
            "tipo": o.tipo.value,
            "status": o.status.value,
            "prioridade": o.prioridade.value,
            "data_abertura": o.data_abertura.isoformat()
        }
        for o in ocorrencias
    ]


@router.get("/acessos-recentes")
async def acessos_recentes(
    limite: int = 10,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retorna acessos recentes."""
    acessos = db.query(RegistroAcesso).join(PontoAcesso).filter(
        PontoAcesso.condominio_id == current_user.condominio_id
    ).order_by(RegistroAcesso.data_hora.desc()).limit(limite).all()

    return [
        {
            "id": a.id,
            "tipo": a.tipo.value,
            "ponto": a.ponto.nome,
            "visitante": a.visitante_nome,
            "placa": a.placa_capturada,
            "data_hora": a.data_hora.isoformat()
        }
        for a in acessos
    ]


@router.get("/alertas-ativos")
async def alertas_ativos(
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retorna alertas ativos."""
    eventos = db.query(EventoAlarme).join(ZonaAlarme).filter(
        ZonaAlarme.condominio_id == current_user.condominio_id,
        EventoAlarme.tratado == False
    ).order_by(EventoAlarme.data_hora.desc()).limit(10).all()

    return [
        {
            "id": e.id,
            "tipo": e.tipo.value,
            "zona": e.zona.nome,
            "descricao": e.descricao,
            "data_hora": e.data_hora.isoformat()
        }
        for e in eventos
    ]


@router.get("/estatisticas-semana")
async def estatisticas_semana(
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retorna estatísticas da última semana."""
    hoje = datetime.now()
    semana_atras = hoje - timedelta(days=7)

    dados_diarios = []
    for i in range(7):
        dia = (semana_atras + timedelta(days=i+1)).date()

        acessos = db.query(RegistroAcesso).join(PontoAcesso).filter(
            PontoAcesso.condominio_id == current_user.condominio_id,
            func.date(RegistroAcesso.data_hora) == dia
        ).count()

        ocorrencias = db.query(Ocorrencia).join(Unidade).filter(
            Unidade.condominio_id == current_user.condominio_id,
            func.date(Ocorrencia.data_abertura) == dia
        ).count()

        dados_diarios.append({
            "data": dia.isoformat(),
            "acessos": acessos,
            "ocorrencias": ocorrencias
        })

    return dados_diarios
