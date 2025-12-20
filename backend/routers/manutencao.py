"""
Conecta Plus - Router de Manutenção
"""

from uuid import UUID
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import uuid

from ..database import get_db
from ..dependencies import get_current_user, require_gerente
from ..models.usuario import Usuario
from ..models.manutencao import OrdemServico, Fornecedor, StatusOS, TipoOS
from ..schemas.manutencao import (
    OrdemServicoCreate, OrdemServicoUpdate, OrdemServicoResponse,
    FornecedorCreate, FornecedorResponse
)

router = APIRouter(prefix="/manutencao", tags=["Manutenção"])


def gerar_numero_os():
    """Gera número único para ordem de serviço."""
    return f"OS-{datetime.now().strftime('%Y')}-{uuid.uuid4().hex[:6].upper()}"


# --- Ordens de Serviço ---

@router.get("/ordens", response_model=List[OrdemServicoResponse])
async def listar_ordens(
    status: Optional[StatusOS] = None,
    tipo: Optional[TipoOS] = None,
    fornecedor_id: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lista ordens de serviço."""
    query = db.query(OrdemServico)

    if status:
        query = query.filter(OrdemServico.status == status)
    if tipo:
        query = query.filter(OrdemServico.tipo == tipo)
    if fornecedor_id:
        query = query.filter(OrdemServico.fornecedor_id == fornecedor_id)

    return query.order_by(OrdemServico.data_abertura.desc()).offset(skip).limit(limit).all()


@router.get("/ordens/{os_id}", response_model=OrdemServicoResponse)
async def obter_ordem(
    os_id: UUID,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtém uma ordem de serviço."""
    os = db.query(OrdemServico).filter(OrdemServico.id == os_id).first()
    if not os:
        raise HTTPException(status_code=404, detail="Ordem de serviço não encontrada")
    return os


@router.post("/ordens", response_model=OrdemServicoResponse, status_code=201)
async def criar_ordem(
    data: OrdemServicoCreate,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cria uma nova ordem de serviço."""
    os = OrdemServico(
        numero=gerar_numero_os(),
        titulo=data.titulo,
        descricao=data.descricao,
        tipo=data.tipo,
        prioridade=data.prioridade,
        local=data.local,
        equipamento=data.equipamento,
        solicitante_nome=data.solicitante_nome or current_user.nome,
        solicitante_id=current_user.id,
        fornecedor_id=data.fornecedor_id,
        custo_estimado=data.custo_estimado,
        data_previsao=data.data_previsao,
        historico=[{
            "data": datetime.now().isoformat(),
            "usuario": current_user.nome,
            "acao": "OS criada"
        }]
    )

    db.add(os)
    db.commit()
    db.refresh(os)
    return os


@router.put("/ordens/{os_id}", response_model=OrdemServicoResponse)
async def atualizar_ordem(
    os_id: UUID,
    data: OrdemServicoUpdate,
    current_user: Usuario = Depends(require_gerente),
    db: Session = Depends(get_db)
):
    """Atualiza uma ordem de serviço."""
    os = db.query(OrdemServico).filter(OrdemServico.id == os_id).first()
    if not os:
        raise HTTPException(status_code=404, detail="OS não encontrada")

    # Histórico
    historico = os.historico or []
    historico.append({
        "data": datetime.now().isoformat(),
        "usuario": current_user.nome,
        "acao": f"OS atualizada - Status: {data.status.value if data.status else 'mantido'}"
    })
    os.historico = historico

    for field, value in data.model_dump(exclude_unset=True).items():
        if field != "observacao":
            setattr(os, field, value)

    if data.status == StatusOS.EM_ANDAMENTO and not os.data_inicio:
        os.data_inicio = datetime.now()
    elif data.status == StatusOS.CONCLUIDA:
        os.data_conclusao = datetime.now()

    db.commit()
    db.refresh(os)
    return os


# --- Fornecedores ---

@router.get("/fornecedores", response_model=List[FornecedorResponse])
async def listar_fornecedores(
    especialidade: Optional[str] = None,
    ativo: bool = True,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lista fornecedores."""
    query = db.query(Fornecedor).filter(
        Fornecedor.condominio_id == current_user.condominio_id,
        Fornecedor.ativo == ativo
    )

    if especialidade:
        query = query.filter(Fornecedor.especialidade.ilike(f"%{especialidade}%"))

    return query.all()


@router.post("/fornecedores", response_model=FornecedorResponse, status_code=201)
async def criar_fornecedor(
    data: FornecedorCreate,
    current_user: Usuario = Depends(require_gerente),
    db: Session = Depends(get_db)
):
    """Cria um novo fornecedor."""
    fornecedor = Fornecedor(**data.model_dump())
    db.add(fornecedor)
    db.commit()
    db.refresh(fornecedor)
    return fornecedor


@router.get("/estatisticas")
async def estatisticas_manutencao(
    current_user: Usuario = Depends(require_gerente),
    db: Session = Depends(get_db)
):
    """Estatísticas de manutenção."""
    query = db.query(OrdemServico)

    total = query.count()
    abertas = query.filter(OrdemServico.status == StatusOS.ABERTA).count()
    em_andamento = query.filter(OrdemServico.status == StatusOS.EM_ANDAMENTO).count()
    concluidas = query.filter(OrdemServico.status == StatusOS.CONCLUIDA).count()

    return {
        "total": total,
        "abertas": abertas,
        "em_andamento": em_andamento,
        "concluidas": concluidas
    }
