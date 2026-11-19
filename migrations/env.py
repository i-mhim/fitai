"""Alembic environment reading DATABASE_URL from application configuration."""
from logging.config import fileConfig
from alembic import context
from app.core.db import Base, engine
from app.core import models  # noqa: F401 - registers mapped classes

config = context.config
if config.config_file_name and config.get_section("loggers"):
    fileConfig(config.config_file_name)
target_metadata = Base.metadata


def run_migrations_online():
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
