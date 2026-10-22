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


settings = Settings()
