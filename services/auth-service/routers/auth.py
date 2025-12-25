from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from schemas.auth import LoginRequest, TokenResponse, RefreshRequest, LogoutRequest
from services.auth_service import AuthService
from models.user import User
from datetime import datetime
from typing import Annotated
from dependencies import get_db, get_auth_service

router = APIRouter(prefix="/api/auth", tags=["authentication"])

@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: LoginRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Authenticate user and return JWT tokens"""
    # Find user by email
    result = await db.execute(
        select(User).where(User.email == credentials.email)
    )
    user = result.scalar_one_or_none()

    # Validate credentials
    if not user or not auth_service.verify_password(credentials.senha, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas"
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário inativo"
        )

    # Update last login
    user.last_login = datetime.utcnow()
    await db.commit()

    # Generate tokens
    token_data = {"sub": user.id, "email": user.email, "role": user.role.value}
    access_token = auth_service.create_access_token(token_data)
    refresh_token = auth_service.create_refresh_token({"sub": user.id})

    # Store refresh token
    await auth_service.store_refresh_token(user.id, refresh_token)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=86400  # 24 hours
    )

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Refresh access token using refresh token"""
    # Decode refresh token
    payload = auth_service.decode_token(request.refresh_token, is_refresh=True)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de refresh inválido"
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido"
        )

    # Validate refresh token against stored value
    if not await auth_service.validate_refresh_token(user_id, request.refresh_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de refresh expirado ou inválido"
        )

    # Get user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado ou inativo"
        )

    # Generate new tokens
    token_data = {"sub": user.id, "email": user.email, "role": user.role.value}
    new_access_token = auth_service.create_access_token(token_data)
    new_refresh_token = auth_service.create_refresh_token({"sub": user.id})

    # Store new refresh token
    await auth_service.store_refresh_token(user.id, new_refresh_token)

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        expires_in=86400
    )

@router.post("/logout")
async def logout(
    request: LogoutRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
):
    """Logout user by blacklisting token"""
    # Decode token to get user ID
    payload = auth_service.decode_token(request.token)
    if payload:
        user_id = payload.get("sub")
        if user_id:
            # Revoke all user tokens
            await auth_service.revoke_user_tokens(user_id)

    # Blacklist the token
    await auth_service.blacklist_token(request.token)

    return {"message": "Logout realizado com sucesso"}

@router.post("/verify")
async def verify_token(
    token: str,
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
):
    """Verify if token is valid"""
    # Check if blacklisted
    if await auth_service.is_token_blacklisted(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido"
        )

    # Decode token
    payload = auth_service.decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado"
        )

    return {
        "valid": True,
        "user_id": payload.get("sub"),
        "email": payload.get("email"),
        "role": payload.get("role")
    }
