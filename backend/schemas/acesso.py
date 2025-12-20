"""
Conecta Plus - Schemas de Acesso
"""

from typing import Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel

from ..models.acesso import TipoAcesso, TipoPonto, MetodoAcesso


class PontoAcessoResponse(BaseModel):
    id: UUID
    nome: str
    tipo: TipoPonto
    descricao: Optional[str] = None
    online: bool
    status: str
    camera_id: Optional[str] = None

    class Config:
        from_attributes = True


class PontoAcessoComando(BaseModel):
    acao: str  # abrir, fechar, travar
    tempo: Optional[int] = 5  # segundos para manter aberto


class RegistroAcessoCreate(BaseModel):
    tipo: TipoAcesso
    metodo: MetodoAcesso
    ponto_id: UUID
    morador_id: Optional[UUID] = None
    veiculo_id: Optional[UUID] = None
    visitante_nome: Optional[str] = None
    visitante_documento: Optional[str] = None
    destino_unidade_id: Optional[UUID] = None
    autorizado_por: Optional[str] = None
    placa_capturada: Optional[str] = None
    observacao: Optional[str] = None


class RegistroAcessoResponse(BaseModel):
    id: UUID
    tipo: TipoAcesso
    metodo: MetodoAcesso
    ponto_id: UUID
    morador_id: Optional[UUID] = None
    veiculo_id: Optional[UUID] = None
    visitante_nome: Optional[str] = None
    autorizado: bool
    autorizado_por: Optional[str] = None
    foto_captura_url: Optional[str] = None
    placa_capturada: Optional[str] = None
    data_hora: datetime

    class Config:
        from_attributes = True


class RegistroAcessoFiltro(BaseModel):
    data_inicio: Optional[datetime] = None
    data_fim: Optional[datetime] = None
    tipo: Optional[TipoAcesso] = None
    ponto_id: Optional[UUID] = None
    morador_id: Optional[UUID] = None
    unidade_id: Optional[UUID] = None
