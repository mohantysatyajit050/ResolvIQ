from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "ResolvIQ"
    environment: str = "development"

    database_url: str
    redis_url: str
    cors_origins: list[str] = ["http://localhost:5173"]

    # S3-compatible storage (Silo locally, S3 or R2 in production)
    s3_endpoint_url: str
    s3_access_key: str
    s3_secret_key: str
    s3_bucket: str = "resolviq-evidence"

    # JWT (login tokens)
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Login cookies
    cookie_secure: bool = False  # set COOKIE_SECURE=true when the site runs on HTTPS
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"

    # Evidence uploads
    max_upload_bytes: int = 5 * 1024 * 1024  # 5 MB per file
    max_attachments_per_ticket: int = 5
    download_url_expire_seconds: int = 300  # signed download links last 5 minutes

    # LLM (the key lives only in backend/.env and is never committed)
    llm_provider: str = "groq"
    llm_api_key: str = ""  # empty by default so tests and tools work without a key
    llm_model: str = "openai/gpt-oss-20b"
    llm_timeout_seconds: float = 30.0
    llm_max_retries: int = 3  # waits 1, 2 and 4 seconds between tries
    llm_max_tokens: int = 1000  # room for the model's thinking plus the JSON answer
    llm_reasoning_effort: str = "low"  # gpt-oss: low, medium or high. "off" = do not send


settings = Settings()
