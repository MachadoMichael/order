from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings

_connect_args = (
    {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
)

engine = create_engine(
    settings.database_url,
    echo=settings.echo_sql,
    pool_pre_ping=True,
    connect_args=_connect_args,
)


def init_db() -> None:
    import app.models  # noqa: F401  registra as tabelas no metadata

    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
