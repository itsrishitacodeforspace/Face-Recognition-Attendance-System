from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Security Notes:
    - SECRET_KEY: Must be changed in production. Do not expose in logs.
    - DATABASE_URL: Should use strong credentials stored in environment variables.
    - DEBUG: Must be False in production to prevent sensitive data leakage in logs.
    - CORS_ALLOWED_ORIGINS: Specify exact origins instead of using wildcards.
    """
    model_config: SettingsConfigDict = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

    # Application config
    app_name: str = "Face Recognition Attendance System"
    environment: str = "development"
    debug: bool = False

    # Database (use environment variables for credentials in production)
    database_url: str = "sqlite+aiosqlite:///./attendance.db"

    # Security (CRITICAL: Change in production and never expose in logs)
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Recognition settings
    recognition_threshold: float = 0.6
    recognition_target_confidence: float = 0.8
    min_training_images_per_person: int = 10
    min_training_face_area_ratio: float = 0.08
    min_training_image_sharpness: float = 80.0
    face_detection_threshold: float = 0.35
    attendance_cooldown_seconds: int = 300
    frame_process_interval: float = 0.067

    # GPU settings
    cuda_enabled: bool = True
    gpu_strict_mode: bool = False
    insightface_model: str = "buffalo_l"

    # Video settings
    video_source_type: str = "file"
    video_source_path: str = ""
    auto_train_on_upload: bool = False
    preview_jpeg_quality: int = 70
    preview_max_width: int = 960

    # Rate limiting
    login_rate_limit_attempts: int = 5
    login_rate_limit_window_seconds: int = 300

    # CORS settings (specify exact origins, not wildcards)
    cors_origins: str = Field(default="", alias="CORS_ALLOWED_ORIGINS")
    cors_origin_regex: str = r"https?://(localhost|127\.0\.0\.1)(:\d+)?$"

    # Admin credentials (change in production)
    admin_username: str = "admin"
    admin_password: str = ""

    # Upload limits
    max_image_upload_bytes: int = 5 * 1024 * 1024
    max_video_upload_bytes: int = 100 * 1024 * 1024
    max_ws_frame_bytes: int = 2 * 1024 * 1024

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() in ("production", "prod")


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
