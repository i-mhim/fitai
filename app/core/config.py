"""Shared environment loading, before database engines or tokens are initialized.

A real process environment variable wins over values from a local .env file.
Do not store production credentials in this repository.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE_URL = (
    "postgresql+psycopg://fitai:fitai_local_dev_only@localhost:5433/fitai"
)
EXAMPLE_SECRET_PLACEHOLDER = "REPLACE_WITH_RANDOM_SECRET_AT_LEAST_32_CHARACTERS"


def load_environment() -> None:
    load_dotenv(dotenv_path=PROJECT_ROOT / ".env", override=False)


# Import this module before reading configuration in either db.py or security.py.
load_environment()


def get_database_url() -> str:
    return os.getenv("DATABASE_URL") or DEFAULT_DATABASE_URL


def get_jwt_secret() -> str:
    value = os.getenv("FITAI_JWT_SECRET")
    if not value or value == EXAMPLE_SECRET_PLACEHOLDER or len(value) < 32:
        raise RuntimeError(
            "Set FITAI_JWT_SECRET in your untracked .env file to a randomly "
            "generated secret of at least 32 characters"
        )
    return value
