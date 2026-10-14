from pathlib import Path

import pytest
from sqlalchemy.engine import make_url

from app.core.config import BACKEND_DIR, Settings, get_settings


def test_env_file_path_is_based_on_backend_location() -> None:
    env_files = Settings.model_config["env_file"]
    assert env_files == (BACKEND_DIR / ".env", BACKEND_DIR / ".env.push")
    assert all(Path(env_file).is_absolute() for env_file in env_files)


def test_default_database_is_sqlite_file_in_backend_folder(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    settings = Settings(
        _env_file=None,
        jwt_secret="test-secret-that-is-long-enough-for-tests-only",
    )
    database_url = make_url(settings.database_url)

    assert database_url.get_backend_name() == "sqlite"
    assert Path(database_url.database).resolve() == (
        BACKEND_DIR / "agentforge.db"
    ).resolve()


def test_environment_settings_load_from_project_root(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///agentforge-test.db")
    monkeypatch.setenv(
        "JWT_SECRET", "configuration-test-secret-with-more-than-32-characters"
    )
    get_settings.cache_clear()
    try:
        settings = get_settings()
        assert settings.database_url == "sqlite:///agentforge-test.db"
    finally:
        get_settings.cache_clear()


def test_cors_origins_must_be_explicit_origins() -> None:
    settings = Settings(
        _env_file=None,
        jwt_secret="test-secret-that-is-long-enough-for-tests-only",
        cors_origins=["http://localhost:5173/", "http://localhost:5173"],
    )
    assert settings.cors_origins == ["http://localhost:5173"]
    with pytest.raises(ValueError, match=r"explicit HTTP\(S\) origins"):
        Settings(
            _env_file=None,
            jwt_secret="test-secret-that-is-long-enough-for-tests-only",
            cors_origins=["*"],
        )
