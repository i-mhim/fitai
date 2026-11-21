"""SQLAlchemy engine and per-request sessions. Schema changes use Alembic."""
import os
from collections.abc import Iterator
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://fitai:fitai_local_dev_only@localhost:5433/fitai")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

def get_db() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session
