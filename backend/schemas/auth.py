"""
Conecta Plus - Schemas de Autenticacao
Versao 2.0 - Validacao Robusta
"""

from typing import Optional, List
from pydantic import BaseModel, EmailStr, field_validator, Field
from enum import Enum

from .validators import PasswordValidator, SanitizeString


class AuthProviderEnum(str, Enum):
    LOCAL = "local"
    GOOGLE = "google"
    MICROSOFT = "microsoft"
    LDAP = "ldap"


class LoginRequest(BaseModel):
    """Request de login com validacao."""
    email: EmailStr = Field(..., description="Email do usuario")
    password: str = Field(default=None, min_length=1, max_length=128, description="Senha")
    senha: str = Field(default=None, min_length=1, max_length=128, description="Senha (alias)")
    remember_me: bool = Field(default=False, description="Manter sessao ativa")

    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Normaliza email para minusculas."""
        return v.lower().strip()

    @property
    def effective_password(self) -> str:
        """Retorna senha efetiva (password ou senha)."""
        return self.password or self.senha or ""


class Token(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int
    user_id: Optional[str] = None
    auth_provider: Optional[str] = None


class UserLoginInfo(BaseModel):
    """Informações básicas do usuário para resposta de login."""
    id: str
    email: str
    nome: str
    role: str
    condominioId: Optional[str] = None


class CondominioLoginInfo(BaseModel):
    """Informações básicas do condomínio para resposta de login."""
    id: str
    nome: str
    cnpj: Optional[str] = None
    endereco: Optional[dict] = None  # Pode ser objeto JSON
    telefone: Optional[str] = None
    email: Optional[str] = None
    configuracoes: Optional[dict] = None


class LoginResponse(BaseModel):
    """Resposta completa de login com token e dados do usuário."""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int
    user: UserLoginInfo
    condominio: Optional[CondominioLoginInfo] = None


class TokenData(BaseModel):
    user_id: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    condominio_id: Optional[str] = None
    auth_provider: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class PasswordChangeRequest(BaseModel):
    """Request para troca de senha com validacao robusta."""
    current_password: str = Field(..., min_length=1, description="Senha atual")
    new_password: str = Field(..., min_length=8, max_length=128, description="Nova senha")

    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        """Valida nova senha com requisitos de seguranca."""
        return PasswordValidator.validate(v)


class PasswordResetRequest(BaseModel):
    """Request para solicitar reset de senha."""
    email: EmailStr = Field(..., description="Email cadastrado")

    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        return v.lower().strip()


class PasswordResetConfirm(BaseModel):
    """Confirmacao de reset de senha."""
    token: str = Field(..., min_length=32, max_length=256, description="Token de reset")
    new_password: str = Field(..., min_length=8, max_length=128, description="Nova senha")

    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        """Valida nova senha com requisitos de seguranca."""
        return PasswordValidator.validate(v)


# OAuth Schemas
class OAuthLoginRequest(BaseModel):
    """Request para iniciar fluxo OAuth"""
    provider: AuthProviderEnum
    redirect_uri: Optional[str] = None


class OAuthCallbackRequest(BaseModel):
    """Request de callback OAuth"""
    code: str
    state: Optional[str] = None


class OAuthUserInfo(BaseModel):
    """Informações do usuário obtidas via OAuth"""
    id: str
    email: EmailStr
    name: str
    picture: Optional[str] = None
    provider: AuthProviderEnum


class GoogleTokenResponse(BaseModel):
    """Resposta de token do Google"""
    access_token: str
    refresh_token: Optional[str] = None
    expires_in: int
    token_type: str
    scope: str
    id_token: Optional[str] = None


class GoogleUserInfo(BaseModel):
    """Informações do usuário Google"""
    id: str
    email: str
    verified_email: bool
    name: str
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    picture: Optional[str] = None
    locale: Optional[str] = None


class MicrosoftUserInfo(BaseModel):
    """Informações do usuário Microsoft"""
    id: str
    displayName: str
    mail: Optional[str] = None
    userPrincipalName: str
    givenName: Optional[str] = None
    surname: Optional[str] = None


# LDAP Schemas
class LDAPLoginRequest(BaseModel):
    """Request de login LDAP"""
    username: str
    password: str
    domain: Optional[str] = None


class LDAPUserInfo(BaseModel):
    """Informações do usuário LDAP"""
    dn: str
    username: str
    email: Optional[str] = None
    display_name: str
    groups: List[str] = []
    department: Optional[str] = None
    title: Optional[str] = None


class SSOConfigResponse(BaseModel):
    """Configuração SSO disponível"""
    google_enabled: bool = False
    microsoft_enabled: bool = False
    ldap_enabled: bool = False
    google_client_id: Optional[str] = None
    microsoft_client_id: Optional[str] = None
    microsoft_tenant_id: Optional[str] = None
