import re
from urllib.parse import urlsplit

from pydantic import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

_DEVELOPMENT_SECRET = "unsafe-development-key-change-me"
_DEVELOPMENT_DATABASE_URL = "sqlite:///./portfolio.db"
_DEVELOPMENT_CORS_ORIGINS = "http://localhost:8501"
_DEVELOPMENT_DEMO_PASSWORD = "ChangeMe123!"
class Settings(BaseSettings):
    app_name: str = "PortfolioPulse"
    environment: str = ""
    secret_key: str = _DEVELOPMENT_SECRET
    access_token_expire_minutes: int = 60
    database_url: str = ""
    cors_origins: str = ""
    max_upload_bytes: int = 2 * 1024 * 1024
    demo_password: str | None = None
    enable_demo_seeding: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
    )

    def __init__(self, **values):
        try:
            super().__init__(**values)
        except ValidationError as error:
            fields = sorted({str(item["loc"][0]).upper() for item in error.errors()})
            field_list = ", ".join(fields) or "settings"
            raise ValueError(f"Invalid application configuration for: {field_list}.") from None

        self._validate_configuration()

    def _validate_configuration(self) -> None:
        self.environment = self.environment.strip().lower()
        if self.environment not in {"development", "production"}:
            raise ValueError(
                "ENVIRONMENT must be explicitly set to 'development' or 'production'."
            )

        if self.environment == "development":
            if not self.database_url.strip():
                self.database_url = _DEVELOPMENT_DATABASE_URL
            if not self.cors_origins.strip():
                self.cors_origins = _DEVELOPMENT_CORS_ORIGINS
            if self.demo_password is None:
                self.demo_password = _DEVELOPMENT_DEMO_PASSWORD
            self._validate_cors_origins(require_https=False)
            return

        if not re.fullmatch(r"[0-9a-fA-F]{64}", self.secret_key):
            raise ValueError(
                "Production SECRET_KEY must be a randomly generated "
                "64-character hexadecimal secret."
            )

        if not self.database_url.strip():
            raise ValueError("DATABASE_URL is required in production.")
        try:
            database_url = make_url(self.database_url)
        except (ArgumentError, TypeError, ValueError):
            raise ValueError("DATABASE_URL is invalid.") from None
        if not (
            database_url.drivername == "postgresql"
            or database_url.drivername.startswith("postgresql+")
        ):
            raise ValueError("DATABASE_URL must use PostgreSQL in production.")
        if database_url.password == "portfolio":
            raise ValueError("DATABASE_URL must not use the development database password.")

        if not self.cors_origins.strip():
            raise ValueError("CORS_ORIGINS must be explicitly configured in production.")
        if self.demo_password:
            raise ValueError("DEMO_PASSWORD must not be configured in production.")
        if self.enable_demo_seeding:
            raise ValueError("ENABLE_DEMO_SEEDING cannot be enabled in production.")

        self._validate_cors_origins(require_https=True)

    def _validate_cors_origins(self, *, require_https: bool) -> None:
        origins = [origin.strip() for origin in self.cors_origins.split(",")]
        if not origins or any(not origin or origin == "*" for origin in origins):
            raise ValueError("CORS_ORIGINS must contain explicit trusted origins.")

        for origin in origins:
            try:
                parsed = urlsplit(origin)
                hostname = parsed.hostname
                parsed.port
                valid_url = True
            except ValueError:
                hostname = None
                valid_url = False
            if (
                not valid_url
                or parsed.scheme
                not in ({"https"} if require_https else {"http", "https"})
                or not hostname
                or "*" in hostname
                or parsed.username is not None
                or parsed.password is not None
                or parsed.path not in ("", "/")
                or parsed.query
                or parsed.fragment
            ):
                message = (
                    "Production CORS origins must be HTTPS origins."
                    if require_https
                    else "CORS_ORIGINS must contain valid HTTP or HTTPS origins."
                )
                raise ValueError(message)

    @property
    def trusted_cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]


settings = Settings()
