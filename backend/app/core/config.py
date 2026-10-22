from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "AICTE FlowGuard"
    environment: str = "development"
    debug: bool = True

    database_url: str = "sqlite+aiosqlite:///./flowguard.db"
    database_url_sync: str = "sqlite:///./flowguard.db"

    secret_key: str = "dev-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    cors_origins: str = "http://localhost:5173"

    upload_dir: str = "uploads"
    max_upload_size_mb: int = 25

    model_config = {"env_file": ".env", "extra": "ignore"}


DEV_SECRET_KEY = "dev-secret-key-change-in-production"

settings = Settings()

# Refuse to run outside development with the publicly known dev signing key.
if settings.environment.lower() not in ("development", "test") and settings.secret_key in (
    DEV_SECRET_KEY, "change-this-to-a-secure-random-string",
):
    raise RuntimeError("SECRET_KEY must be set to a strong random value outside development")
