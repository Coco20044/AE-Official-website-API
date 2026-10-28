from pydantic_settings import BaseSettings, SettingsConfigDict
class Settings(BaseSettings):
    APP_NAME: str = "AE OFFICIAL WEBSITE API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    BASE_URL: str = "http://127.0.0.1:8000"

    DATABASE_URL: str = ""
    JWT_SECRET_KEY: str = ""
    RESEND_API_KEY: str = ""
    PAYSTACK_SECRET_KEY: str

    EMAIL_FROM: str = "onboarding@resend.dev"
    RATE_LIMIT_STORAGE_URI: str = "memory://"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
settings = Settings()