import pytest
from app.core.config import Settings

_PRODUCTION_SECRET = "0123456789abcdef" * 4
_PRODUCTION_DATABASE_URL = (
    "postgresql+psycopg://app_user:isolated-test-password@db.example.test:5432/app"
)
_PRODUCTION_CORS = "https://reports.example.test"


def _production_settings(**overrides):
    values = {
        "_env_file": None,
        "environment": "production",
        "secret_key": _PRODUCTION_SECRET,
        "database_url": _PRODUCTION_DATABASE_URL,
        "cors_origins": _PRODUCTION_CORS,
    }
    values.update(overrides)
    return Settings(**values)


def test_development_configuration_keeps_local_defaults():
    settings = Settings(
        _env_file=None,
        environment="development",
        database_url="",
    )

    assert settings.database_url == "sqlite:///./portfolio.db"
    assert settings.cors_origins == "http://localhost:8501"
    assert settings.demo_password == "ChangeMe123!"
    assert settings.enable_demo_seeding is False


def test_environment_must_be_explicit_and_supported():
    with pytest.raises(ValueError, match="ENVIRONMENT must be explicitly set"):
        Settings(_env_file=None, environment="")

    with pytest.raises(ValueError, match="ENVIRONMENT must be explicitly set"):
        Settings(_env_file=None, environment="staging")


def test_production_rejects_missing_jwt_secret():
    with pytest.raises(ValueError, match="SECRET_KEY"):
        _production_settings(secret_key="")


def test_production_rejects_descriptive_weak_jwt_secret():
    with pytest.raises(
        ValueError,
        match="randomly generated 64-character hexadecimal secret",
    ):
        _production_settings(
            secret_key="development-secret-please-change-this-before-production"
        )


def test_production_rejects_known_development_jwt_secret():
    with pytest.raises(ValueError, match="64-character hexadecimal secret"):
        _production_settings(secret_key="unsafe-development-key-change-me")

    with pytest.raises(ValueError, match="64-character hexadecimal secret"):
        _production_settings(
            secret_key="replace-with-a-random-development-value"
        )


@pytest.mark.parametrize(
    "secret_key",
    ["", "g" * 64, "a" * 63, "a" * 65, "a" * 63 + "!"],
)
def test_production_rejects_empty_or_malformed_jwt_secrets(secret_key):
    with pytest.raises(ValueError, match="64-character hexadecimal secret"):
        _production_settings(secret_key=secret_key)


def test_production_accepts_64_character_hexadecimal_jwt_secret():
    settings = _production_settings()

    assert settings.secret_key == _PRODUCTION_SECRET


def test_production_requires_explicit_database_url():
    with pytest.raises(ValueError, match="DATABASE_URL is required"):
        _production_settings(database_url="")


def test_production_rejects_sqlite_database_url():
    with pytest.raises(ValueError, match="must use PostgreSQL"):
        _production_settings(database_url="sqlite:///./portfolio.db")


def test_invalid_database_url_errors_do_not_echo_the_url():
    database_url = "postgresql://user:sensitive-password@[::1"

    with pytest.raises(ValueError) as error:
        _production_settings(database_url=database_url)

    assert database_url not in str(error.value)


def test_production_rejects_development_database_password():
    with pytest.raises(ValueError, match="development database password"):
        _production_settings(
            database_url="postgresql://portfolio:portfolio@db:5432/portfolio"
        )


def test_production_rejects_demo_seeding_and_demo_password():
    with pytest.raises(ValueError, match="ENABLE_DEMO_SEEDING"):
        _production_settings(enable_demo_seeding=True)

    with pytest.raises(ValueError, match="DEMO_PASSWORD"):
        _production_settings(demo_password="local-demo-only")


def test_development_can_explicitly_enable_demo_seeding():
    settings = Settings(
        _env_file=None,
        environment="development",
        enable_demo_seeding=True,
    )

    assert settings.enable_demo_seeding is True


@pytest.mark.parametrize(
    ("cors_origins", "message"),
    [
        ("", "explicitly configured"),
        ("*", "explicit trusted origins"),
        ("http://reports.example.test", "HTTPS origins"),
        ("https://reports.example.test/path", "HTTPS origins"),
        ("https://reports.example.test:invalid", "HTTPS origins"),
        ("https://*.example.test", "HTTPS origins"),
    ],
)
def test_production_requires_safe_explicit_cors_origins(cors_origins, message):
    with pytest.raises(ValueError, match=message):
        _production_settings(cors_origins=cors_origins)


def test_configuration_errors_do_not_include_secret_values():
    secret_value = "development-secret-please-change-this-before-production"

    with pytest.raises(ValueError) as error:
        _production_settings(secret_key=secret_value)

    assert "randomly generated 64-character hexadecimal secret" in str(error.value)
    assert secret_value not in str(error.value)
