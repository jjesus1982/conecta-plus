"""
Conecta Plus - Schemas de Condomínio
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class EnderecoBase(BaseModel):
    logradouro: Optional[str] = None
    numero: Optional[str] = None
    complemento: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None
    cep: Optional[str] = None


class CondominioBase(BaseModel):
    nome: str
    cnpj: Optional[str] = None
    telefone: Optional[str] = None
    email: Optional[str] = None


class CondominioCreate(CondominioBase):
    endereco: Optional[Dict[str, Any]] = None


class CondominioUpdate(BaseModel):
    nome: Optional[str] = None
    cnpj: Optional[str] = None
    telefone: Optional[str] = None
    email: Optional[str] = None
    endereco: Optional[Dict[str, Any]] = None
    configuracoes: Optional[Dict[str, Any]] = None
    ativo: Optional[bool] = None


class CondominioResponse(CondominioBase):
    id: UUID
    endereco: Optional[Dict[str, Any]] = None
    configuracoes: Optional[Dict[str, Any]] = None
    ativo: bool = True
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
