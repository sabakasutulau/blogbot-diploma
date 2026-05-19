"""
pytest conftest — isolated SQLite (file-based) DB for tests.

Uses a temp file so all connections see the same schema.
"""
import os
import tempfile

# Must happen before any app module is imported.
_tmp_db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp_db_file.close()
_TEST_DB_URL = f"sqlite:///{_tmp_db_file.name}"
os.environ["DATABASE_URL"] = _TEST_DB_URL

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# ── Patch app.db to use our test engine ─────────────────────────────────────
import app.db as _app_db  # noqa: E402

_test_engine = create_engine(
    _TEST_DB_URL,
    connect_args={"check_same_thread": False},
)
_TestSession = sessionmaker(
    bind=_test_engine, autoflush=False, autocommit=False
)

# Redirect all module-level references.
_app_db.engine = _test_engine
_app_db.SessionLocal = _TestSession


def _override_get_db():
    db = _TestSession()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def _setup_db():
    """Create schema once; drop after session."""
    from app import models  # noqa: F401
    from app.db import Base

    Base.metadata.create_all(bind=_test_engine)
    yield
    Base.metadata.drop_all(bind=_test_engine)
    _test_engine.dispose()
    try:
        os.unlink(_tmp_db_file.name)
    except OSError:
        pass


@pytest.fixture(scope="session")
def client(_setup_db):
    from app.main import app
    from app.db import get_db
    from fastapi.testclient import TestClient

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
