import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import check_login_rate_limit, record_login_attempt
from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshRequest, TokenResponse
from app.config import get_settings
from app.utils.security import (
    TokenError,
    create_access_token,
    create_refresh_token,
    verify_password,
    decode_token,
)


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """
    User login endpoint.
    
    Security: Passwords are hashed with bcrypt (rounds=12).
    JWT tokens are created with HS256 algorithm.
    """
    await check_login_rate_limit(payload.username, db)
    result = await db.execute(select(User).where(User.username == payload.username))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.hashed_password):
        await record_login_attempt(payload.username, db)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    access_token, expires_at = create_access_token(user.username)
    refresh_token, _ = create_refresh_token(user.username)

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        path="/",
        max_age=max(1, int((expires_at - datetime.now(timezone.utc)).total_seconds())),
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        path="/",
    )
    return TokenResponse(access_token=access_token, refresh_token=refresh_token, expires_at=expires_at)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    response: Response,
    payload: RefreshRequest | None = None,
    refresh_token_cookie: str | None = Cookie(default=None, alias="refresh_token"),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Token refresh endpoint.
    
    Security: Refresh tokens are validated before issuing new access tokens.
    Errors are logged without exposing sensitive data (no JWT secret in logs).
    """
    refresh_token = (payload.refresh_token if payload else None) or refresh_token_cookie
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    try:
        subject = decode_token(refresh_token, expected_type="refresh")
    except TokenError as exc:
        # Security: Log the error type but not the token or secret
        logger.warning("Token refresh failed: invalid refresh token")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token") from exc

    result = await db.execute(select(User).where(User.username == subject))
    user = result.scalar_one_or_none()
    if user is None:
        logger.warning(f"Token refresh failed: user not found (username: {subject})")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    access_token, expires_at = create_access_token(user.username)
    refresh_token, _ = create_refresh_token(user.username)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        path="/",
        max_age=max(1, int((expires_at - datetime.now(timezone.utc)).total_seconds())),
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        path="/",
    )
    return TokenResponse(access_token=access_token, refresh_token=refresh_token, expires_at=expires_at)


@router.post("/logout")
async def logout(response: Response) -> dict[str, str]:
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return {"message": "Logged out"}


@router.get("/me")
async def me(current_user: User = Depends(get_current_user)) -> dict[str, object]:
    return {
        "username": current_user.username,
        "is_admin": current_user.is_admin,
    }
