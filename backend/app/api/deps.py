from datetime import datetime, timedelta, timezone

from fastapi import Cookie, Depends, Header, HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.login_attempt import LoginAttempt
from app.models.user import User
from app.utils.security import decode_token, TokenError
from app.config import get_settings


settings = get_settings()


async def authenticate_access_token(token: str, db: AsyncSession) -> User:
    try:
        subject = decode_token(token, expected_type="access")
    except TokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    result = await db.execute(select(User).where(User.username == subject))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


async def get_current_user(
    authorization: str = Header(default=""),
    access_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = ""
    if authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
    elif access_token:
        token = access_token

    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    return await authenticate_access_token(token, db)


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


async def check_login_rate_limit(username: str, db: AsyncSession) -> None:
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(seconds=settings.login_rate_limit_window_seconds)

    await db.execute(
        delete(LoginAttempt).where(
            LoginAttempt.username == username,
            LoginAttempt.attempted_at < window_start,
        )
    )

    count_result = await db.execute(
        select(func.count(LoginAttempt.id)).where(
            LoginAttempt.username == username,
            LoginAttempt.attempted_at >= window_start,
        )
    )
    attempts = int(count_result.scalar() or 0)

    if attempts >= settings.login_rate_limit_attempts:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many login attempts")


async def record_login_attempt(username: str, db: AsyncSession) -> None:
    db.add(LoginAttempt(username=username, attempted_at=datetime.now(timezone.utc)))
    await db.commit()
