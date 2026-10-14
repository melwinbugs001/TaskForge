from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL

BACKEND_DIR = Path(__file__).resolve().parents[2]


def _default_database_url() -> str:
    return URL.create(
        "sqlite",
        database=str(BACKEND_DIR / "agentforge.db"),
    ).render_as_string(hide_password=False)


class Settings(BaseSettings):
    database_url: str = Field(default_factory=_default_database_url)
    jwt_secret: SecretStr = Field(min_length=32)
    access_token_expire_minutes: int = Field(default=30, gt=0)
    max_task_retries: int = Field(default=2, ge=0)
    web_search_api_key: SecretStr | None = None
    web_search_provider: str | None = None
    vapid_public_key: str | None = None
    vapid_private_key: SecretStr | None = None
    vapid_subject: str = "mailto:push-admin@example.com"
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://127.0.0.1:5173",
            "http://localhost:5173",
        ]
    )

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, origins: list[str]) -> list[str]:
        validated: list[str] = []
        for origin in origins:
            candidate = origin.strip().rstrip("/")
            parsed = urlsplit(candidate)
            if (
                candidate == "*"
                or parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or parsed.username is not None
                or parsed.password is not None
                or parsed.path
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError("CORS entries must be explicit HTTP(S) origins")
            if candidate not in validated:
                validated.append(candidate)
        return validated

    model_config = SettingsConfigDict(
        env_file=(BACKEND_DIR / ".env", BACKEND_DIR / ".env.push"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
