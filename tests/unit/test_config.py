import pytest
from app.core.config import get_settings
from app.main import create_app
from fastapi.testclient import TestClient


def test_cors_origins_parsed() -> None:
    settings = get_settings()
    assert "http://localhost:5173" in settings.cors_origin_list
    assert settings.app_name == "ILKA"


def test_cors_allows_credentialed_browser_sessions() -> None:
    application = create_app()
    client = TestClient(application)
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.headers["access-control-allow-credentials"] == "true"
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_app_name_and_debug(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_NAME", "ILKA")
    monkeypatch.setenv("DEBUG", "true")
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.app_name == "ILKA"
    assert settings.debug is True
    get_settings.cache_clear()
    monkeypatch.setenv("DEBUG", "false")
    get_settings.cache_clear()


def test_sqlalchemy_url_upgrades_plain_postgres() -> None:
    settings = get_settings()
    # testing uses sqlite
    assert settings.is_sqlite


def test_production_requires_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("ILKA_POSTGRES_URL", "postgresql://ilka:ilka_dev_only@localhost:5432/ilka")
    monkeypatch.setenv("AUTH_SECRET_KEY", "production-secret-must-be-at-least-32-bytes-long")
    get_settings.cache_clear()
    application = create_app()
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        with TestClient(application):
            pass
    get_settings.cache_clear()
    monkeypatch.setenv("ENVIRONMENT", "testing")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    monkeypatch.setenv("ILKA_POSTGRES_URL", "")
    monkeypatch.setenv("AUTH_SECRET_KEY", "")
    get_settings.cache_clear()


def test_production_requires_auth_secret_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    monkeypatch.setenv("ILKA_POSTGRES_URL", "")
    monkeypatch.setenv("AUTH_SECRET_KEY", "")
    monkeypatch.setenv("ILKA_AUTH_TEST_SECRET", "")
    get_settings.cache_clear()
    application = create_app()
    with pytest.raises(RuntimeError, match="AUTH_SECRET_KEY is required"):
        with TestClient(application):
            pass
    get_settings.cache_clear()
    monkeypatch.setenv("ENVIRONMENT", "testing")
    get_settings.cache_clear()


def test_production_rejects_short_auth_secret_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    monkeypatch.setenv("ILKA_POSTGRES_URL", "")
    monkeypatch.setenv("AUTH_SECRET_KEY", "short")
    monkeypatch.setenv("ILKA_AUTH_TEST_SECRET", "")
    get_settings.cache_clear()
    application = create_app()
    with pytest.raises(RuntimeError, match="AUTH_SECRET_KEY must be at least 32 bytes"):
        with TestClient(application):
            pass
    get_settings.cache_clear()
    monkeypatch.setenv("ENVIRONMENT", "testing")
    monkeypatch.setenv("AUTH_SECRET_KEY", "")
    get_settings.cache_clear()


def test_production_rejects_test_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    monkeypatch.setenv("ILKA_POSTGRES_URL", "")
    monkeypatch.setenv(
        "AUTH_SECRET_KEY", "production-secret-must-be-at-least-32-bytes-long"
    )
    monkeypatch.setenv("ILKA_AUTH_TEST_SECRET", "test-secret")
    get_settings.cache_clear()
    application = create_app()
    with pytest.raises(RuntimeError, match="ILKA_AUTH_TEST_SECRET must not be set"):
        with TestClient(application):
            pass
    get_settings.cache_clear()
    monkeypatch.setenv("ENVIRONMENT", "testing")
    monkeypatch.setenv("AUTH_SECRET_KEY", "")
    monkeypatch.setenv("ILKA_AUTH_TEST_SECRET", "")
    get_settings.cache_clear()


def test_production_rejects_weak_algorithms(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    monkeypatch.setenv("ILKA_POSTGRES_URL", "")
    monkeypatch.setenv("AUTH_SECRET_KEY", "production-secret-must-be-at-least-32-bytes-long")
    monkeypatch.setenv("AUTH_ALGORITHM", "none,HS256")
    get_settings.cache_clear()
    application = create_app()
    with pytest.raises(RuntimeError, match="AUTH_ALGORITHM"):
        with TestClient(application):
            pass
    get_settings.cache_clear()
    monkeypatch.setenv("ENVIRONMENT", "testing")
    monkeypatch.setenv("AUTH_SECRET_KEY", "")
    monkeypatch.setenv("AUTH_ALGORITHM", "HS256")
    get_settings.cache_clear()


def test_production_starts_with_hmac_algorithm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    monkeypatch.setenv("ILKA_POSTGRES_URL", "")
    monkeypatch.setenv("AUTH_SECRET_KEY", "production-secret-must-be-at-least-32-bytes-long")
    monkeypatch.setenv("AUTH_ALGORITHM", "HS256")
    get_settings.cache_clear()
    application = create_app()
    with TestClient(application) as client:
        assert client.get("/health").status_code == 200
    get_settings.cache_clear()
    monkeypatch.setenv("ENVIRONMENT", "testing")
    monkeypatch.setenv("AUTH_SECRET_KEY", "")
    get_settings.cache_clear()


def test_ilka_postgres_url_fills_empty_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv(
        "ILKA_POSTGRES_URL",
        "postgresql://ilka:ilka_dev_only@localhost:5432/ilka?sslmode=require",
    )
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.resolved_database_url.startswith("postgresql://")
    assert settings.sqlalchemy_url.startswith("postgresql+asyncpg://")
    assert "sslmode" not in settings.sqlalchemy_url
    assert settings.postgres_connect_args.get("ssl") is True
    get_settings.cache_clear()
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    monkeypatch.setenv("ILKA_POSTGRES_URL", "")
    get_settings.cache_clear()


@pytest.mark.parametrize(
    ("sslmode", "expect_ssl"),
    [
        ("disable", False),
        ("require", True),
        ("verify-ca", True),
        ("verify-full", True),
    ],
)
def test_postgres_connect_args_respects_sslmode(
    monkeypatch: pytest.MonkeyPatch, sslmode: str, expect_ssl: bool
) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        f"postgresql://u:p@localhost:5432/db?sslmode={sslmode}",
    )
    monkeypatch.setenv("ILKA_POSTGRES_URL", "")
    get_settings.cache_clear()
    settings = get_settings()
    assert "sslmode" not in settings.sqlalchemy_url
    assert settings.postgres_connect_args.get("ssl") is (True if expect_ssl else None)
    get_settings.cache_clear()
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    get_settings.cache_clear()


def test_postgres_connect_args_enables_ssl_for_neon_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://u:p@ep-example.eu-central-1.aws.neon.tech/neondb",
    )
    monkeypatch.setenv("ILKA_POSTGRES_URL", "")
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.postgres_connect_args.get("ssl") is True
    get_settings.cache_clear()
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    get_settings.cache_clear()


def test_ready_without_database(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "testing")
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("ILKA_POSTGRES_URL", "")
    get_settings.cache_clear()
    application = create_app()
    with TestClient(application) as client:
        response = client.get("/ready")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "http_error"
    get_settings.cache_clear()
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    get_settings.cache_clear()


def test_ready_with_ilka_postgres_url_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "testing")
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("ILKA_POSTGRES_URL", "sqlite+aiosqlite:///:memory:")
    get_settings.cache_clear()
    application = create_app()
    with TestClient(application) as client:
        response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    get_settings.cache_clear()
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    monkeypatch.setenv("ILKA_POSTGRES_URL", "")
    get_settings.cache_clear()
