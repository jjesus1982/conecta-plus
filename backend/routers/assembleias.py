"""
Conecta Plus - Router de Assembleias
"""

from uuid import UUID
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user, require_gerente
from ..models.usuario import Usuario
from ..models.assembleia import Assembleia, Votacao, Ata, PresencaAssembleia, StatusAssembleia
from ..schemas.assembleia import (
    AssembleiaCreate, AssembleiaUpdate, AssembleiaResponse,
    VotacaoCreate, VotacaoResponse, VotoRequest,
    PresencaRequest, AtaCreate, AtaResponse
)

router = APIRouter(prefix="/assembleias", tags=["Assembleias"])


# --- Assembleias ---

@router.get("/", response_model=List[AssembleiaResponse])
async def listar_assembleias(
    status: Optional[StatusAssembleia] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lista assembleias."""
    query = db.query(Assembleia).filter(
        Assembleia.condominio_id == current_user.condominio_id
    )

    if status:
        query = query.filter(Assembleia.status == status)

    return query.order_by(Assembleia.data.desc()).offset(skip).limit(limit).all()


@router.get("/proxima", response_model=AssembleiaResponse)
async def proxima_assembleia(
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retorna a próxima assembleia agendada."""
    from datetime import date

    assembleia = db.query(Assembleia).filter(
        Assembleia.condominio_id == current_user.condominio_id,
        Assembleia.status == StatusAssembleia.AGENDADA,
        Assembleia.data >= date.today()
    ).order_by(Assembleia.data).first()

    if not assembleia:
        raise HTTPException(status_code=404, detail="Nenhuma assembleia agendada")
    return assembleia


@router.get("/{assembleia_id}", response_model=AssembleiaResponse)
async def obter_assembleia(
    assembleia_id: UUID,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtém uma assembleia."""
    assembleia = db.query(Assembleia).filter(Assembleia.id == assembleia_id).first()
    if not assembleia:
        raise HTTPException(status_code=404, detail="Assembleia não encontrada")
    return assembleia


@router.post("/", response_model=AssembleiaResponse, status_code=201)
async def criar_assembleia(
    data: AssembleiaCreate,
    current_user: Usuario = Depends(require_gerente),
    db: Session = Depends(get_db)
):
    """Cria uma nova assembleia."""
    assembleia = Assembleia(
        **data.model_dump(),
        condominio_id=current_user.condominio_id
    )
    db.add(assembleia)
    db.commit()
    db.refresh(assembleia)
    return assembleia


@router.put("/{assembleia_id}", response_model=AssembleiaResponse)
async def atualizar_assembleia(
    assembleia_id: UUID,
    data: AssembleiaUpdate,
    current_user: Usuario = Depends(require_gerente),
    db: Session = Depends(get_db)
):
    """Atualiza uma assembleia."""
    assembleia = db.query(Assembleia).filter(Assembleia.id == assembleia_id).first()
    if not assembleia:
        raise HTTPException(status_code=404, detail="Assembleia não encontrada")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(assembleia, field, value)

    db.commit()
    db.refresh(assembleia)
    return assembleia


# --- Presença ---

@router.post("/{assembleia_id}/presenca")
async def registrar_presenca(
    assembleia_id: UUID,
    data: PresencaRequest,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Registra presença/confirmação em assembleia."""
    # Verificar se já existe registro
    presenca = db.query(PresencaAssembleia).filter(
        PresencaAssembleia.assembleia_id == assembleia_id,
        PresencaAssembleia.unidade_id == data.unidade_id
    ).first()

    if presenca:
        presenca.confirmado = data.confirmado
        presenca.procuracao = data.procuracao
        presenca.procurador_nome = data.procurador_nome
    else:
        presenca = PresencaAssembleia(
            assembleia_id=assembleia_id,
            unidade_id=data.unidade_id,
            morador_id=data.morador_id,
            confirmado=data.confirmado,
            procuracao=data.procuracao,
            procurador_nome=data.procurador_nome
        )
        db.add(presenca)

    db.commit()
    return {"message": "Presença registrada"}


@router.get("/{assembleia_id}/presencas")
async def listar_presencas(
    assembleia_id: UUID,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lista presenças de uma assembleia."""
    presencas = db.query(PresencaAssembleia).filter(
        PresencaAssembleia.assembleia_id == assembleia_id
    ).all()

    confirmados = sum(1 for p in presencas if p.confirmado)
    presentes = sum(1 for p in presencas if p.presente)

    return {
        "total_confirmados": confirmados,
        "total_presentes": presentes,
        "presencas": presencas
    }


# --- Votações ---

@router.get("/{assembleia_id}/votacoes", response_model=List[VotacaoResponse])
async def listar_votacoes(
    assembleia_id: UUID,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lista votações de uma assembleia."""
    return db.query(Votacao).filter(Votacao.assembleia_id == assembleia_id).all()


@router.post("/{assembleia_id}/votacoes", response_model=VotacaoResponse, status_code=201)
async def criar_votacao(
    assembleia_id: UUID,
    data: VotacaoCreate,
    current_user: Usuario = Depends(require_gerente),
    db: Session = Depends(get_db)
):
    """Cria uma votação."""
    votacao = Votacao(
        titulo=data.titulo,
        descricao=data.descricao,
        assembleia_id=assembleia_id,
        voto_secreto=data.voto_secreto,
        quorum_especial=data.quorum_especial
    )
    db.add(votacao)
    db.commit()
    db.refresh(votacao)
    return votacao


@router.post("/votacoes/{votacao_id}/abrir")
async def abrir_votacao(
    votacao_id: UUID,
    current_user: Usuario = Depends(require_gerente),
    db: Session = Depends(get_db)
):
    """Abre uma votação."""
    votacao = db.query(Votacao).filter(Votacao.id == votacao_id).first()
    if not votacao:
        raise HTTPException(status_code=404, detail="Votação não encontrada")

    votacao.aberta = True
    votacao.data_abertura = datetime.now()
    db.commit()
    return {"message": "Votação aberta"}


@router.post("/votacoes/{votacao_id}/votar")
async def votar(
    votacao_id: UUID,
    data: VotoRequest,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Registra voto em uma votação."""
    votacao = db.query(Votacao).filter(Votacao.id == votacao_id).first()
    if not votacao:
        raise HTTPException(status_code=404, detail="Votação não encontrada")

    if not votacao.aberta:
        raise HTTPException(status_code=400, detail="Votação não está aberta")

    # TODO: Verificar se usuário já votou (implementar tabela de votos)

    if data.voto == "favor":
        votacao.votos_favor += 1
    elif data.voto == "contra":
        votacao.votos_contra += 1
    else:
        votacao.votos_abstencao += 1

    db.commit()
    return {"message": "Voto registrado"}


@router.post("/votacoes/{votacao_id}/encerrar")
async def encerrar_votacao(
    votacao_id: UUID,
    current_user: Usuario = Depends(require_gerente),
    db: Session = Depends(get_db)
):
    """Encerra uma votação e calcula resultado."""
    votacao = db.query(Votacao).filter(Votacao.id == votacao_id).first()
    if not votacao:
        raise HTTPException(status_code=404, detail="Votação não encontrada")

    votacao.aberta = False
    votacao.data_encerramento = datetime.now()

    total = votacao.votos_favor + votacao.votos_contra + votacao.votos_abstencao
    if total > 0:
        votacao.aprovada = votacao.votos_favor > votacao.votos_contra
        votacao.resultado_descricao = f"Aprovada com {votacao.votos_favor} votos" if votacao.aprovada else f"Rejeitada com {votacao.votos_contra} votos contra"

    db.commit()
    return {"message": "Votação encerrada", "aprovada": votacao.aprovada}


# --- Atas ---

@router.get("/{assembleia_id}/atas", response_model=List[AtaResponse])
async def listar_atas(
    assembleia_id: UUID,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lista atas de uma assembleia."""
    return db.query(Ata).filter(Ata.assembleia_id == assembleia_id).all()


@router.post("/{assembleia_id}/atas", response_model=AtaResponse, status_code=201)
async def criar_ata(
    assembleia_id: UUID,
    data: AtaCreate,
    current_user: Usuario = Depends(require_gerente),
    db: Session = Depends(get_db)
):
    """Cria uma ata."""
    ata = Ata(
        assembleia_id=assembleia_id,
        conteudo=data.conteudo
    )
    db.add(ata)
    db.commit()
    db.refresh(ata)
    return ata


@router.post("/atas/{ata_id}/publicar")
async def publicar_ata(
    ata_id: UUID,
    current_user: Usuario = Depends(require_gerente),
    db: Session = Depends(get_db)
):
    """Publica uma ata."""
    ata = db.query(Ata).filter(Ata.id == ata_id).first()
    if not ata:
        raise HTTPException(status_code=404, detail="Ata não encontrada")

    ata.status = "publicada"
    ata.data_publicacao = datetime.now()
    db.commit()

    return {"message": "Ata publicada"}
