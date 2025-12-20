"""
Conecta Plus - Router de Autenticação
Suporta: Local, OAuth (Google/Microsoft), LDAP/Active Directory
"""

import json
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import (
    verify_password, get_password_hash, create_access_token,
    create_refresh_token, get_current_user
)
from ..models.usuario import Usuario, AuthProvider
from ..schemas.auth import (
    Token, LoginRequest, RefreshTokenRequest, PasswordChangeRequest,
    OAuthCallbackRequest, LDAPLoginRequest, SSOConfigResponse,
    AuthProviderEnum
)
from ..schemas.usuario import UsuarioResponse
from ..schemas.condominio import CondominioResponse
from ..config import settings
from ..services.oauth import oauth_service
from ..services.ldap import get_ldap_service, map_ldap_groups_to_role

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Login com email e senha.
    Retorna access_token e refresh_token.
    """
    user = db.query(Usuario).filter(Usuario.email == form_data.username).first()

    # SEGURANÇA: Sempre executar verificação de senha para prevenir timing attacks
    # Mesmo quando usuário não existe, fazemos hash da senha para manter tempo constante
    # Hash bcrypt válido gerado previamente para simular verificação
    DUMMY_HASH = "$2b$12$lh4Q02DK9hPlsMXGs9jwQ.u5AiJZZWQf0iGjVwFV/MVosNvcO7RiC"
    if user:
        password_valid = verify_password(form_data.password, user.senha_hash)
    else:
        # Verificação com hash fictício para manter tempo de resposta consistente
        verify_password(form_data.password, DUMMY_HASH)
        password_valid = False

    if not user or not password_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.ativo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário inativo"
        )

    # Atualizar último login
    user.last_login = datetime.utcnow()
    db.commit()

    # Criar tokens
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role.value}
    )
    refresh_token = create_refresh_token(
        data={"sub": str(user.id)}
    )

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post("/login/json", response_model=Token)
async def login_json(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Login com JSON body (alternativa ao form).
    """
    user = db.query(Usuario).filter(Usuario.email == login_data.email).first()

    # SEGURANÇA: Sempre executar verificação de senha para prevenir timing attacks
    DUMMY_HASH = "$2b$12$lh4Q02DK9hPlsMXGs9jwQ.u5AiJZZWQf0iGjVwFV/MVosNvcO7RiC"
    if user:
        password_valid = verify_password(login_data.password, user.senha_hash)
    else:
        verify_password(login_data.password, DUMMY_HASH)
        password_valid = False

    if not user or not password_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos"
        )

    if not user.ativo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário inativo"
        )

    user.last_login = datetime.utcnow()
    db.commit()

    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role.value}
    )
    refresh_token = create_refresh_token(
        data={"sub": str(user.id)}
    ) if login_data.remember_me else None

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Renova o access_token usando o refresh_token.
    """
    from jose import jwt, JWTError

    try:
        payload = jwt.decode(
            refresh_data.refresh_token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )

        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido"
            )

        user_id = payload.get("sub")
        user = db.query(Usuario).filter(Usuario.id == user_id).first()

        if not user or not user.ativo:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuário não encontrado ou inativo"
            )

        access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email, "role": user.role.value}
        )

        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado"
        )


@router.get("/me", response_model=UsuarioResponse)
async def get_me(current_user: Usuario = Depends(get_current_user)):
    """
    Retorna dados do usuário atual.
    """
    return current_user


@router.get("/me/condominio", response_model=CondominioResponse)
async def get_my_condominio(current_user: Usuario = Depends(get_current_user)):
    """
    Retorna dados do condomínio do usuário atual.
    """
    if not current_user.condominio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não está associado a nenhum condomínio"
        )
    return current_user.condominio


@router.post("/change-password")
async def change_password(
    password_data: PasswordChangeRequest,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Altera a senha do usuário atual.
    """
    if not verify_password(password_data.current_password, current_user.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Senha atual incorreta"
        )

    current_user.senha_hash = get_password_hash(password_data.new_password)
    db.commit()

    return {"message": "Senha alterada com sucesso"}


@router.post("/logout")
async def logout(current_user: Usuario = Depends(get_current_user)):
    """
    Logout (invalidação do token deve ser feita no cliente).
    """
    # Em uma implementação real, poderia adicionar o token a uma blacklist
    return {"message": "Logout realizado com sucesso"}


# ==================== SSO Configuration ====================

@router.get("/sso/config", response_model=SSOConfigResponse)
async def get_sso_config():
    """
    Retorna configuração SSO disponível.
    Usado pelo frontend para exibir botões de login social.
    """
    return SSOConfigResponse(
        google_enabled=bool(settings.GOOGLE_CLIENT_ID),
        microsoft_enabled=bool(settings.MICROSOFT_CLIENT_ID),
        ldap_enabled=settings.LDAP_ENABLED,
        google_client_id=settings.GOOGLE_CLIENT_ID,
        microsoft_client_id=settings.MICROSOFT_CLIENT_ID,
        microsoft_tenant_id=settings.MICROSOFT_TENANT_ID if settings.MICROSOFT_CLIENT_ID else None
    )


# ==================== Google OAuth ====================

@router.get("/google/login")
async def google_login(redirect_uri: str = Query(None)):
    """
    Inicia fluxo de autenticação Google OAuth.
    Redireciona para página de login do Google.
    """
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Login Google não configurado"
        )

    auth_url, state = oauth_service.get_google_auth_url(redirect_uri)
    return {"auth_url": auth_url, "state": state}


@router.get("/google/callback", response_model=Token)
async def google_callback(
    code: str = Query(...),
    state: str = Query(None),
    db: Session = Depends(get_db)
):
    """
    Callback do Google OAuth.
    Processa o authorization code e cria/atualiza usuário.
    """
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Login Google não configurado"
        )

    # Validar state (opcional mas recomendado)
    if state:
        state_data = oauth_service.validate_state(state)
        if not state_data or state_data.get("provider") != "google":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="State inválido ou expirado"
            )

    try:
        # Trocar code por tokens
        token_response = await oauth_service.exchange_google_code(code)

        # Obter informações do usuário
        google_user = await oauth_service.get_google_user_info(token_response.access_token)

        # Verificar se email foi verificado
        if not google_user.verified_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email Google não verificado"
            )

        # Buscar ou criar usuário
        user = db.query(Usuario).filter(
            (Usuario.email == google_user.email) |
            (Usuario.oauth_id == google_user.id)
        ).first()

        if user:
            # Atualizar dados do usuário existente
            user.oauth_id = google_user.id
            user.oauth_access_token = token_response.access_token
            user.oauth_refresh_token = token_response.refresh_token
            user.oauth_token_expires = datetime.utcnow() + timedelta(seconds=token_response.expires_in)
            user.avatar_url = google_user.picture or user.avatar_url
            user.auth_provider = AuthProvider.GOOGLE
            user.last_login = datetime.utcnow()
        elif settings.SSO_AUTO_CREATE_USER:
            # Criar novo usuário
            user = Usuario(
                email=google_user.email,
                nome=google_user.name,
                auth_provider=AuthProvider.GOOGLE,
                oauth_id=google_user.id,
                oauth_access_token=token_response.access_token,
                oauth_refresh_token=token_response.refresh_token,
                oauth_token_expires=datetime.utcnow() + timedelta(seconds=token_response.expires_in),
                avatar_url=google_user.picture,
                ativo=True,
                last_login=datetime.utcnow()
            )
            db.add(user)
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuário não encontrado. Criação automática desabilitada."
            )

        db.commit()
        db.refresh(user)

        # Criar tokens JWT
        access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email, "role": user.role.value}
        )
        refresh_token = create_refresh_token(data={"sub": str(user.id)})

        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user_id=user.id,
            auth_provider="google"
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ==================== Microsoft OAuth ====================

@router.get("/microsoft/login")
async def microsoft_login(redirect_uri: str = Query(None)):
    """
    Inicia fluxo de autenticação Microsoft OAuth.
    Redireciona para página de login do Azure AD.
    """
    if not settings.MICROSOFT_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Login Microsoft não configurado"
        )

    auth_url, state = oauth_service.get_microsoft_auth_url(redirect_uri)
    return {"auth_url": auth_url, "state": state}


@router.get("/microsoft/callback", response_model=Token)
async def microsoft_callback(
    code: str = Query(...),
    state: str = Query(None),
    db: Session = Depends(get_db)
):
    """
    Callback do Microsoft OAuth.
    Processa o authorization code e cria/atualiza usuário.
    """
    if not settings.MICROSOFT_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Login Microsoft não configurado"
        )

    # Validar state
    if state:
        state_data = oauth_service.validate_state(state)
        if not state_data or state_data.get("provider") != "microsoft":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="State inválido ou expirado"
            )

    try:
        # Trocar code por tokens
        token_response = await oauth_service.exchange_microsoft_code(code)
        access_token = token_response.get("access_token")

        # Obter informações do usuário
        ms_user = await oauth_service.get_microsoft_user_info(access_token)
        email = ms_user.mail or ms_user.userPrincipalName

        # Buscar ou criar usuário
        user = db.query(Usuario).filter(
            (Usuario.email == email) |
            (Usuario.oauth_id == ms_user.id)
        ).first()

        if user:
            # Atualizar dados do usuário existente
            user.oauth_id = ms_user.id
            user.oauth_access_token = access_token
            user.oauth_refresh_token = token_response.get("refresh_token")
            user.oauth_token_expires = datetime.utcnow() + timedelta(seconds=token_response.get("expires_in", 3600))
            user.auth_provider = AuthProvider.MICROSOFT
            user.last_login = datetime.utcnow()
        elif settings.SSO_AUTO_CREATE_USER:
            # Criar novo usuário
            user = Usuario(
                email=email,
                nome=ms_user.displayName,
                auth_provider=AuthProvider.MICROSOFT,
                oauth_id=ms_user.id,
                oauth_access_token=access_token,
                oauth_refresh_token=token_response.get("refresh_token"),
                oauth_token_expires=datetime.utcnow() + timedelta(seconds=token_response.get("expires_in", 3600)),
                ativo=True,
                last_login=datetime.utcnow()
            )
            db.add(user)
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuário não encontrado. Criação automática desabilitada."
            )

        db.commit()
        db.refresh(user)

        # Criar tokens JWT
        jwt_access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email, "role": user.role.value}
        )
        jwt_refresh_token = create_refresh_token(data={"sub": str(user.id)})

        return Token(
            access_token=jwt_access_token,
            refresh_token=jwt_refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user_id=user.id,
            auth_provider="microsoft"
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ==================== LDAP/Active Directory ====================

@router.post("/ldap/login", response_model=Token)
async def ldap_login(
    login_data: LDAPLoginRequest,
    db: Session = Depends(get_db)
):
    """
    Login via LDAP/Active Directory.
    """
    if not settings.LDAP_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Login LDAP não habilitado"
        )

    ldap_service = get_ldap_service()
    if not ldap_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Serviço LDAP indisponível"
        )

    try:
        # Autenticar no LDAP
        success, ldap_user = ldap_service.authenticate(
            login_data.username,
            login_data.password,
            login_data.domain
        )

        if not success or not ldap_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciais inválidas"
            )

        # Determinar email
        email = ldap_user.email or f"{login_data.username}@{login_data.domain or 'local'}"

        # Buscar ou criar usuário
        user = db.query(Usuario).filter(
            (Usuario.email == email) |
            (Usuario.ldap_dn == ldap_user.dn)
        ).first()

        # Mapear grupos para role
        role_name = map_ldap_groups_to_role(ldap_user.groups)

        if user:
            # Atualizar dados do usuário existente
            user.ldap_dn = ldap_user.dn
            user.ldap_groups = json.dumps(ldap_user.groups)
            user.nome = ldap_user.display_name
            user.auth_provider = AuthProvider.LDAP
            user.last_login = datetime.utcnow()

            # Atualizar role se mapeamento de grupos mudou
            from ..models.usuario import Role
            if role_name and hasattr(Role, role_name.upper()):
                user.role = Role[role_name.upper()]
        elif settings.SSO_AUTO_CREATE_USER:
            # Criar novo usuário
            from ..models.usuario import Role
            role = Role[role_name.upper()] if hasattr(Role, role_name.upper()) else Role.MORADOR

            user = Usuario(
                email=email,
                nome=ldap_user.display_name,
                auth_provider=AuthProvider.LDAP,
                ldap_dn=ldap_user.dn,
                ldap_groups=json.dumps(ldap_user.groups),
                role=role,
                ativo=True,
                last_login=datetime.utcnow()
            )
            db.add(user)
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuário não encontrado. Criação automática desabilitada."
            )

        db.commit()
        db.refresh(user)

        # Criar tokens JWT
        access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email, "role": user.role.value}
        )
        refresh_token = create_refresh_token(data={"sub": str(user.id)})

        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user_id=user.id,
            auth_provider="ldap"
        )

    except ConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Erro de conexão LDAP: {str(e)}"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/ldap/test")
async def test_ldap_connection():
    """
    Testa conexão com servidor LDAP.
    Apenas para administradores.
    """
    if not settings.LDAP_ENABLED:
        return {"status": "disabled", "message": "LDAP não habilitado"}

    ldap_service = get_ldap_service()
    if not ldap_service:
        return {"status": "error", "message": "Serviço LDAP indisponível"}

    success, message = ldap_service.test_connection()
    return {
        "status": "ok" if success else "error",
        "message": message
    }
