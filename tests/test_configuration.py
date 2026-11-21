"""Configuration source precedence and JWT placeholder guardrails."""
import os
from pathlib import Path

import pytest

from app.core import config
from app.auth.security import jwt_secret


def test_existing_environment_beats_dotenv(tmp_path: Path, monkeypatch):
    (tmp_path / ".env").write_text(
        "DATABASE_URL=sqlite:///file-value.db\n"
        "FITAI_JWT_SECRET=an-example-key-from-dotenv-only-1234567890\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(config, "PROJECT_ROOT", tmp_path)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///provided-by-process.db")
    monkeypatch.setenv("FITAI_JWT_SECRET", "secret-provided-by-process-at-least-32-chars")
    config.load_environment()
    assert config.get_database_url() == "sqlite:///provided-by-process.db"
    assert jwt_secret() == "secret-provided-by-process-at-least-32-chars"


def test_dotenv_is_loaded_when_environment_missing(tmp_path: Path, monkeypatch):
    (tmp_path / ".env").write_text(
        "DATABASE_URL=sqlite:///from-local-dotenv.db\n"
        "FITAI_JWT_SECRET=a-strong-random-dev-secret-example-123456789\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(config, "PROJECT_ROOT", tmp_path)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("FITAI_JWT_SECRET", raising=False)
    config.load_environment()
    assert config.get_database_url() == "sqlite:///from-local-dotenv.db"
    assert jwt_secret() == "a-strong-random-dev-secret-example-123456789"


def test_database_fallback_matches_compose_host_port(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert config.get_database_url().endswith("@localhost:5433/fitai")


@pytest.mark.parametrize(
    "invalid",
    [
        "",
        "short",
        "REPLACE_WITH_RANDOM_SECRET_AT_LEAST_32_CHARACTERS",
    ],
)
def test_missing_or_template_secret_is_rejected(monkeypatch, invalid):
    monkeypatch.setenv("FITAI_JWT_SECRET", invalid)
    with pytest.raises(RuntimeError, match="FITAI_JWT_SECRET"):
        jwt_secret()


def test_database_engine_respects_preconfigured_test_environment():
    # tests/conftest.py configures an isolated SQLite database before app imports.
    # With config.py imported first, the already configured process env wins.
    from app.core.db import DATABASE_URL
    assert DATABASE_URL.startswith("sqlite:///")
    assert DATABASE_URL == os.environ["DATABASE_URL"]
