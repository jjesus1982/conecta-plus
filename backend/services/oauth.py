"""
Conecta Plus - Serviço de OAuth
Suporta Google e Microsoft OAuth2
Com Circuit Breaker para resiliência
"""

import httpx
import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple
from urllib.parse import urlencode

from ..config import settings
from ..schemas.auth import (
    GoogleTokenResponse, GoogleUserInfo, MicrosoftUserInfo,
    OAuthUserInfo, AuthProviderEnum
)
from .resilience import with_circuit_breaker, get_http_client


class OAuthService:
    """Serviço para autenticação OAuth2"""

    # Google OAuth URLs
    GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
    GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
    GOOGLE_SCOPES = [
        "openid",
        "email",
        "profile"
    ]

    # Microsoft OAuth URLs
    MICROSOFT_AUTH_URL = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize"
    MICROSOFT_TOKEN_URL = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
    MICROSOFT_USERINFO_URL = "https://graph.microsoft.com/v1.0/me"
    MICROSOFT_SCOPES = [
        "openid",
        "email",
        "profile",
        "User.Read"
    ]

    def __init__(self):
        self._state_store: dict = {}  # Em produção, usar Redis

    def generate_state(self, provider: str, extra_data: dict = None) -> str:
        """Gera um state token para prevenir CSRF"""
        state = secrets.token_urlsafe(32)
        self._state_store[state] = {
            "provider": provider,
            "created_at": datetime.utcnow(),
            "extra_data": extra_data or {}
        }
        return state

    def validate_state(self, state: str) -> Optional[dict]:
        """Valida um state token"""
        if state not in self._state_store:
            return None

        state_data = self._state_store.pop(state)

        # Verificar expiração (15 minutos)
        if datetime.utcnow() - state_data["created_at"] > timedelta(minutes=15):
            return None

        return state_data

    # ==================== GOOGLE OAuth ====================

    def get_google_auth_url(self, redirect_uri: str = None) -> Tuple[str, str]:
        """
        Gera URL de autenticação do Google
        Retorna (url, state)
        """
        if not settings.GOOGLE_CLIENT_ID:
            raise ValueError("GOOGLE_CLIENT_ID não configurado")

        state = self.generate_state("google")
        redirect = redirect_uri or settings.GOOGLE_REDIRECT_URI

        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": redirect,
            "response_type": "code",
            "scope": " ".join(self.GOOGLE_SCOPES),
            "state": state,
            "access_type": "offline",
            "prompt": "consent"
        }

        url = f"{self.GOOGLE_AUTH_URL}?{urlencode(params)}"
        return url, state

    @with_circuit_breaker("google-token-exchange", service_type="oauth")
    async def exchange_google_code(self, code: str, redirect_uri: str = None) -> GoogleTokenResponse:
        """
        Troca o authorization code por tokens
        Protegido por Circuit Breaker
        """
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            raise ValueError("Credenciais Google não configuradas")

        redirect = redirect_uri or settings.GOOGLE_REDIRECT_URI

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.GOOGLE_TOKEN_URL,
                data={
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": redirect,
                    "grant_type": "authorization_code"
                }
            )

            if response.status_code != 200:
                error_data = response.json()
                raise ValueError(f"Erro ao obter token: {error_data.get('error_description', 'Unknown error')}")

            data = response.json()
            return GoogleTokenResponse(**data)

    @with_circuit_breaker("google-userinfo", service_type="oauth")
    async def get_google_user_info(self, access_token: str) -> GoogleUserInfo:
        """
        Obtém informações do usuário do Google
        Protegido por Circuit Breaker
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"}
            )

            if response.status_code != 200:
                raise ValueError("Erro ao obter informações do usuário")

            data = response.json()
            return GoogleUserInfo(**data)

    @with_circuit_breaker("google-token-refresh", service_type="oauth")
    async def refresh_google_token(self, refresh_token: str) -> GoogleTokenResponse:
        """
        Renova o access token usando refresh token
        Protegido por Circuit Breaker
        """
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            raise ValueError("Credenciais Google não configuradas")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.GOOGLE_TOKEN_URL,
                data={
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token"
                }
            )

            if response.status_code != 200:
                raise ValueError("Erro ao renovar token")

            data = response.json()
            return GoogleTokenResponse(**data)

    # ==================== MICROSOFT OAuth ====================

    def get_microsoft_auth_url(self, redirect_uri: str = None) -> Tuple[str, str]:
        """
        Gera URL de autenticação do Microsoft
        Retorna (url, state)
        """
        if not settings.MICROSOFT_CLIENT_ID:
            raise ValueError("MICROSOFT_CLIENT_ID não configurado")

        state = self.generate_state("microsoft")
        redirect = redirect_uri or settings.MICROSOFT_REDIRECT_URI
        tenant = settings.MICROSOFT_TENANT_ID or "common"

        params = {
            "client_id": settings.MICROSOFT_CLIENT_ID,
            "redirect_uri": redirect,
            "response_type": "code",
            "scope": " ".join(self.MICROSOFT_SCOPES),
            "state": state,
            "response_mode": "query"
        }

        base_url = self.MICROSOFT_AUTH_URL.format(tenant=tenant)
        url = f"{base_url}?{urlencode(params)}"
        return url, state

    @with_circuit_breaker("microsoft-token-exchange", service_type="oauth")
    async def exchange_microsoft_code(self, code: str, redirect_uri: str = None) -> dict:
        """
        Troca o authorization code por tokens do Microsoft
        Protegido por Circuit Breaker
        """
        if not settings.MICROSOFT_CLIENT_ID or not settings.MICROSOFT_CLIENT_SECRET:
            raise ValueError("Credenciais Microsoft não configuradas")

        redirect = redirect_uri or settings.MICROSOFT_REDIRECT_URI
        tenant = settings.MICROSOFT_TENANT_ID or "common"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.MICROSOFT_TOKEN_URL.format(tenant=tenant),
                data={
                    "client_id": settings.MICROSOFT_CLIENT_ID,
                    "client_secret": settings.MICROSOFT_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": redirect,
                    "grant_type": "authorization_code",
                    "scope": " ".join(self.MICROSOFT_SCOPES)
                }
            )

            if response.status_code != 200:
                error_data = response.json()
                raise ValueError(f"Erro ao obter token: {error_data.get('error_description', 'Unknown error')}")

            return response.json()

    @with_circuit_breaker("microsoft-userinfo", service_type="oauth")
    async def get_microsoft_user_info(self, access_token: str) -> MicrosoftUserInfo:
        """
        Obtém informações do usuário do Microsoft Graph
        Protegido por Circuit Breaker
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.MICROSOFT_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"}
            )

            if response.status_code != 200:
                raise ValueError("Erro ao obter informações do usuário")

            data = response.json()
            return MicrosoftUserInfo(**data)

    # ==================== Helper Methods ====================

    def to_oauth_user_info(
        self,
        provider: AuthProviderEnum,
        google_info: GoogleUserInfo = None,
        microsoft_info: MicrosoftUserInfo = None
    ) -> OAuthUserInfo:
        """
        Converte informações do provider para formato unificado
        """
        if provider == AuthProviderEnum.GOOGLE and google_info:
            return OAuthUserInfo(
                id=google_info.id,
                email=google_info.email,
                name=google_info.name,
                picture=google_info.picture,
                provider=provider
            )
        elif provider == AuthProviderEnum.MICROSOFT and microsoft_info:
            email = microsoft_info.mail or microsoft_info.userPrincipalName
            return OAuthUserInfo(
                id=microsoft_info.id,
                email=email,
                name=microsoft_info.displayName,
                picture=None,
                provider=provider
            )
        else:
            raise ValueError(f"Provider não suportado: {provider}")


# Instância global
oauth_service = OAuthService()
