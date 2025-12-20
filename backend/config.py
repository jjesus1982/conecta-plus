"""
Conecta Plus - Configuracoes da API
Versao 2.0 - Seguranca Aprimorada
"""

import os
import secrets
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import field_validator, SecretStr
from functools import lru_cache


class Settings(BaseSettings):
    """Configuracoes da aplicacao com validacao de seguranca"""

    # App
    APP_NAME: str = "Conecta Plus API"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False  # SEGURANCA: False por padrao
    API_PREFIX: str = "/api/v1"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database - SEM valores default inseguros
    DATABASE_URL: str
    DATABASE_ECHO: bool = False

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT - SEM valores default inseguros
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8  # 8 horas (mais seguro)
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS - SEM wildcard
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 100  # requests por janela
    RATE_LIMIT_WINDOW: int = 60  # segundos

    # Security Headers
    SECURITY_HEADERS_ENABLED: bool = True

    @field_validator('SECRET_KEY')
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Valida que SECRET_KEY e segura"""
        if v in ["your-super-secret-key-change-in-production", "secret", "changeme"]:
            raise ValueError("SECRET_KEY insegura! Configure uma chave forte no .env")
        if len(v) < 32:
            raise ValueError("SECRET_KEY deve ter pelo menos 32 caracteres")
        return v

    @field_validator('CORS_ORIGINS')
    @classmethod
    def validate_cors_origins(cls, v: List[str]) -> List[str]:
        """Valida que CORS nao tem wildcard em producao"""
        if "*" in v:
            # Remove wildcard e loga aviso
            v = [origin for origin in v if origin != "*"]
        return v

    # Upload
    UPLOAD_DIR: str = "/opt/conecta-plus/data/uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB

    # Integrations
    ANTHROPIC_API_KEY: Optional[str] = None

    # OAuth Google
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/google/callback"

    # OAuth Microsoft (Azure AD)
    MICROSOFT_CLIENT_ID: Optional[str] = None
    MICROSOFT_CLIENT_SECRET: Optional[str] = None
    MICROSOFT_TENANT_ID: str = "common"
    MICROSOFT_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/microsoft/callback"

    # LDAP/Active Directory
    LDAP_ENABLED: bool = False
    LDAP_SERVER: str = "ldap://localhost:389"
    LDAP_BASE_DN: str = "dc=example,dc=com"
    LDAP_BIND_DN: Optional[str] = None
    LDAP_BIND_PASSWORD: Optional[str] = None
    LDAP_USER_SEARCH_BASE: str = "ou=users"
    LDAP_USER_SEARCH_FILTER: str = "(sAMAccountName={username})"
    LDAP_GROUP_SEARCH_BASE: str = "ou=groups"
    LDAP_USE_SSL: bool = False
    LDAP_TIMEOUT: int = 10

    # SSO Settings
    SSO_AUTO_CREATE_USER: bool = True
    SSO_DEFAULT_ROLE: str = "morador"

    class Config:
        env_file = "/opt/conecta-plus/.env"
        case_sensitive = True
        extra = "ignore"  # Ignora variaveis extras no .env


@lru_cache()
def get_settings() -> Settings:
    """Retorna instância cacheada das configurações"""
    return Settings()


settings = get_settings()
