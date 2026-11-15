from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[3]
_ENV_FILE = _REPO_ROOT / ".env"

# Allowed signing algorithms for ILKA-issued session tokens. HMAC and "none"
# are excluded so the token header cannot downgrade to an unsafe algorithm.
AUTH_ALGORITHM_ALLOWLIST: frozenset[str] = frozenset(
    {
        "HS256",
        "HS384",
        "HS512",
    }
)


def _asyncpg_compatible_url(url: str) -> str:
    """Drop libpq-only query params. Do not log the result."""
    parsed = urlparse(url)
    if not parsed.scheme.startswith("postgresql"):
        return url
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query.pop("sslmode", None)
    query.pop("channel_binding", None)
    return urlunparse(parsed._replace(query=urlencode(query)))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE if _ENV_FILE.is_file() else ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "ILKA"
    debug: bool = False
    environment: Literal["development", "testing", "production"] = Field(
        default="development",
        validation_alias=AliasChoices("ENVIRONMENT", "APP_ENV", "environment"),
    )
    log_level: str = "INFO"
    service_name: str = "ilka-backend"
    platform_host: str = "0.0.0.0"
    platform_port: int = 8000
    api_cors_origins: str = "http://localhost:5173,http://localhost:3000"
    database_url: str = ""
    ilka_postgres_url: str = ""
    database_pool_size: int = Field(default=5, ge=1, le=50)
    database_max_overflow: int = Field(default=5, ge=0, le=50)

    auth_secret_key: str = Field(
        default="",
        validation_alias=AliasChoices("AUTH_SECRET_KEY"),
    )
    auth_access_token_expire_minutes: int = Field(
        default=15,
        ge=1,
        validation_alias=AliasChoices("AUTH_ACCESS_TOKEN_EXPIRE_MINUTES"),
    )
    auth_refresh_token_expire_days: int = Field(
        default=7,
        ge=1,
        validation_alias=AliasChoices("AUTH_REFRESH_TOKEN_EXPIRE_DAYS"),
    )
    auth_algorithm: str = Field(default="HS256", validation_alias=AliasChoices("AUTH_ALGORITHM"))
    auth_session_cookie_name: str = Field(
        default="ilka_session",
        validation_alias=AliasChoices("AUTH_SESSION_COOKIE_NAME"),
    )
    auth_session_cookie_samesite: str = Field(
        default="lax",
        validation_alias=AliasChoices("AUTH_SESSION_COOKIE_SAMESITE"),
    )
    auth_max_failed_logins: int = Field(
        default=5,
        ge=1,
        validation_alias=AliasChoices("AUTH_MAX_FAILED_LOGINS"),
    )
    auth_lockout_minutes: int = Field(
        default=15,
        ge=1,
        validation_alias=AliasChoices("AUTH_LOCKOUT_MINUTES"),
    )
    auth_test_secret: str = Field(
        default="",
        validation_alias=AliasChoices("ILKA_AUTH_TEST_SECRET"),
    )
    demo_observations_path: str = Field(
        default="",
        validation_alias=AliasChoices("ILKA_DEMO_OBSERVATIONS_PATH"),
    )
    lab_cameras_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("ILKA_LAB_CAMERAS_ENABLED"),
    )
    lab_camera_organization_id: str = Field(
        default="",
        validation_alias=AliasChoices("ILKA_LAB_CAMERA_ORGANIZATION_ID"),
    )
    lab_camera_site_id: str = Field(
        default="",
        validation_alias=AliasChoices("ILKA_LAB_CAMERA_SITE_ID"),
    )
    detection_sample_interval_s: float = Field(
        default=2.0,
        gt=0,
        validation_alias=AliasChoices("ILKA_DETECTION_SAMPLE_INTERVAL_S"),
    )

    @field_validator(
        "auth_secret_key",
        "auth_algorithm",
        "auth_session_cookie_name",
        "auth_session_cookie_samesite",
        "auth_test_secret",
    )
    @classmethod
    def _strip_auth(cls, value: str) -> str:
        return value.strip()

    @property
    def auth_algorithm_list(self) -> list[str]:
        return [part.strip() for part in self.auth_algorithm.split(",") if part.strip()]

    def auth_signing_algorithms(self) -> list[str]:
        """Configured algorithms that are also on the allowlist.

        An empty setting uses the default HS256. Any algorithm outside the
        allowlist fails closed instead of being ignored or taken from the token
        header.
        """
        requested = self.auth_algorithm_list or ["HS256"]
        if any(algorithm not in AUTH_ALGORITHM_ALLOWLIST for algorithm in requested):
            return []
        return list(dict.fromkeys(requested))

    @property
    def auth_is_configured(self) -> bool:
        """True when a session signing secret has been provided."""
        return bool(self.auth_secret_key)

    def require_production_auth(self) -> None:
        if self.environment != "production":
            return
        if not self.auth_secret_key:
            raise RuntimeError("AUTH_SECRET_KEY is required when ENVIRONMENT=production")
        if len(self.auth_secret_key) < 32:
            raise RuntimeError(
                "AUTH_SECRET_KEY must be at least 32 bytes when ENVIRONMENT=production"
            )
        if self.auth_test_secret:
            raise RuntimeError("ILKA_AUTH_TEST_SECRET must not be set when ENVIRONMENT=production")
        if not self.auth_signing_algorithms():
            raise RuntimeError(
                "AUTH_ALGORITHM must list only HMAC algorithms when ENVIRONMENT=production"
            )

    @field_validator("database_url", "ilka_postgres_url")
    @classmethod
    def _strip_url(cls, value: str) -> str:
        return value.strip()

    @property
    def cors_origin_list(self) -> list[str]:
        return [part.strip() for part in self.api_cors_origins.split(",") if part.strip()]

    @property
    def resolved_database_url(self) -> str:
        """Canonical app URL is DATABASE_URL; ILKA_POSTGRES_URL is the Neon/CI fallback."""
        return self.database_url or self.ilka_postgres_url

    @property
    def is_sqlite(self) -> bool:
        return self.resolved_database_url.startswith("sqlite")

    @property
    def sqlalchemy_url(self) -> str:
        url = self.resolved_database_url
        if url.startswith("postgres://"):
            url = "postgresql+asyncpg://" + url[len("postgres://") :]
        elif url.startswith("postgresql://"):
            url = "postgresql+asyncpg://" + url[len("postgresql://") :]
        return _asyncpg_compatible_url(url)

    @property
    def postgres_connect_args(self) -> dict:
        args: dict = {"statement_cache_size": 0, "timeout": 60}
        raw = self.resolved_database_url
        parsed = urlparse(raw)
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        sslmode = query.get("sslmode", "").lower()
        if sslmode == "disable":
            return args
        if sslmode in {"require", "verify-ca", "verify-full"}:
            args["ssl"] = True
        elif "neon.tech" in raw.lower():
            args["ssl"] = True
        return args


@lru_cache
def get_settings() -> Settings:
    return Settings()
