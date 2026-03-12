from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

from app.config import ROOT_DIR, get_settings


def _resolve_database_url(database_url: str) -> str:
    sqlite_prefix = "sqlite:///"
    if not database_url.startswith(sqlite_prefix):
        return database_url

    path_value = database_url[len(sqlite_prefix):]
    if path_value.startswith("/") or (len(path_value) >= 2 and path_value[1] == ":"):
        return database_url

    resolved_path = (ROOT_DIR / Path(path_value)).resolve()
    return f"{sqlite_prefix}{resolved_path.as_posix()}"


@lru_cache
def get_engine():
    settings = get_settings()
    resolved_database_url = _resolve_database_url(settings.database_url)
    connect_args = {"check_same_thread": False} if resolved_database_url.startswith("sqlite") else {}
    return create_engine(resolved_database_url, connect_args=connect_args)


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(get_engine())


def get_session() -> Iterator[Session]:
    with Session(get_engine()) as session:
        yield session
