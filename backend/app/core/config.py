from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "PortfolioPulse"
    environment: str = "development"
    secret_key: str = "unsafe-development-key-change-me"
    access_token_expire_minutes: int = 60
    database_url: str = "sqlite:///./portfolio.db"
    cors_origins: str = "http://localhost:8501"
    max_upload_bytes: int = 2 * 1024 * 1024
    demo_password: str = "ChangeMe123!"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
