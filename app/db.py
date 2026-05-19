from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


def _engine_kwargs(database_url: str) -> dict:
    if database_url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    return {}


engine = create_engine(settings.database_url, echo=False, future=True, **_engine_kwargs(settings.database_url))
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _run_migrations(conn) -> None:
    """
    Safe ALTER TABLE migrations for SQLite.
    Each column is added only if it does not already exist.
    """
    migrations = [
        # Telegram channel publication fields
        "ALTER TABLE posts ADD COLUMN telegram_channel_id VARCHAR(100)",
        "ALTER TABLE posts ADD COLUMN telegram_message_id BIGINT",
        "ALTER TABLE posts ADD COLUMN telegram_message_url VARCHAR(300)",
        "ALTER TABLE posts ADD COLUMN published_to_channel_at DATETIME",
    ]
    for sql in migrations:
        try:
            conn.execute(text(sql))
        except Exception:
            # Column already exists — ignore
            pass
    conn.commit()


def init_db() -> None:
    # Import models before metadata creation.
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)

    # Run safe column-level migrations for existing databases.
    if settings.database_url.startswith("sqlite"):
        with engine.connect() as conn:
            _run_migrations(conn)
