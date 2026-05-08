from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str

    # Supabase (for Auth verification)
    supabase_url: str = ""
    supabase_secret_key: str = ""

    # Encryption
    encryption_key: str  # Base64-encoded 32-byte key

    # Cloudflare R2
    r2_access_key_id: str
    r2_secret_access_key: str
    r2_bucket_name: str
    r2_endpoint_url: str

    # Anthropic (OCR)
    anthropic_api_key: str

    # Resend (email)
    resend_api_key: str
    resend_from_email: str = "noreply@cognify.com"

    # JWT (admin auth)
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7

    # App
    environment: str = "development"
    allowed_origins: list[str] = ["https://cognify-document-processer.pages.dev", "http://localhost:3000"]


settings = Settings()
