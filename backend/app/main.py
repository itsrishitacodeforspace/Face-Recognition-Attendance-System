import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.api import attendance, auth, persons, training, video
from app.database import Base, SessionLocal, engine
from app.models import *  # noqa: F401,F403 - ensure all model metadata is loaded
from app.models.user import User
from app.services.attendance_service import AttendanceService
from app.services.face_recognition import FaceRecognitionService
from app.config import get_settings
from app.utils.security import ensure_password_hashing_compatibility, hash_password
from app.websocket.stream_handler import router as ws_router


logger = logging.getLogger(__name__)
settings = get_settings()

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

# Security: Define specific CORS origins instead of using wildcards
# In development, localhost is allowed. In production, specify your frontend URL.
default_cors_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Load additional origins from environment variable (comma-separated)
configured_cors_origins = [
    origin.strip() 
    for origin in settings.cors_origins.split(",") 
    if origin.strip()
]

# Combine default and configured origins, remove duplicates
allow_origins = sorted(set(default_cors_origins + configured_cors_origins)) if settings.environment != "production" else configured_cors_origins

logger.info(f"CORS allowed origins: {allow_origins}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events with proper error handling.
    """
    # Startup
    try:
        logger.info("Starting application...")

        # Fail fast if password hashing dependencies are incompatible.
        ensure_password_hashing_compatibility()
        
        # Create database tables
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created/verified")
        except SQLAlchemyError as e:
            logger.error(f"Failed to create database tables: {e}")
            raise RuntimeError("Database initialization failed") from e

        # Ensure a default admin exists for first-time setup
        try:
            if settings.is_production and settings.admin_password in {"", "admin123"}:
                raise RuntimeError("ADMIN_PASSWORD must be set to a strong value in production")

            async with SessionLocal() as db:
                result = await db.execute(
                    select(User).where(User.username == settings.admin_username)
                )
                user = result.scalar_one_or_none()
                if user is None:
                    db.add(
                        User(
                            username=settings.admin_username,
                            hashed_password=hash_password(settings.admin_password),
                            is_admin=True,
                        )
                    )
                    await db.commit()
                    logger.info(f"Created default admin user: {settings.admin_username}")
        except SQLAlchemyError as e:
            logger.error(f"Failed to create admin user: {e}")
            raise RuntimeError("Failed to initialize admin user") from e

        # Initialize face recognition service
        try:
            app.state.face_service = FaceRecognitionService()
            app.state.face_service.initialize()
            app.state.face_service.load_index_from_disk()
            logger.info("Face recognition service initialized")
        except Exception as e:
            logger.error(f"Failed to initialize face recognition service: {e}")
            raise RuntimeError("Face recognition service initialization failed") from e

        # Initialize attendance service
        app.state.attendance_service = AttendanceService()

        # Rebuild index if needed
        try:
            async with SessionLocal() as db:
                if not app.state.face_service._index_to_person_id:
                    logger.info("Rebuilding face recognition index...")
                    await app.state.face_service.rebuild_index(db)
        except Exception as e:
            logger.error(f"Failed to rebuild face recognition index: {e}")
            # Don't raise - this is non-critical

        logger.info("Application started successfully")
    except Exception as e:
        logger.error(f"Application startup failed: {e}")
        raise

    yield

    # Shutdown
    logger.info("Application shutting down...")


app = FastAPI(
    title="Face Recognition Attendance System",
    lifespan=lifespan
)

# CORS middleware: Security - specify exact origins instead of wildcards (*)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_origin_regex=settings.cors_origin_regex if settings.environment == "development" else None,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],  # Be specific, don't allow all methods
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(persons.router)
app.include_router(training.router)
app.include_router(attendance.router)
app.include_router(video.router)
app.include_router(ws_router)


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}
