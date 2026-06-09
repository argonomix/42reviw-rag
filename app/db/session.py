from collections.abc import Generator

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_db_and_tables() -> None:
    from app.db import models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def run_schema_migrations() -> None:
    inspector = inspect(engine)
    config = Config("alembic.ini")
    if inspector.has_table("reviews") and not inspector.has_table("alembic_version"):
        command.stamp(config, "0001_initial_schema")
    command.upgrade(config, "head")
