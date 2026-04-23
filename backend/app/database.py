from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


settings = get_settings()

# Security: Only enable echo (SQL logs) in development, never in production
# SQL logs can expose sensitive data like passwords, API keys, etc.
engine = create_async_engine(
    settings.database_url, 
    future=True, 
    echo=settings.debug  # Only log SQL in debug/development mode
)
SessionLocal = async_sessionmaker(
    bind=engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
