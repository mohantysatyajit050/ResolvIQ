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


settings = Settings()
