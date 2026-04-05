"""Set test env before any application modules load (engine binds to DATABASE_URL)."""

import os
import tempfile
from pathlib import Path

_tmp = Path(tempfile.mkdtemp()) / "pytest_finance.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.as_posix()}"
os.environ["SECRET_KEY"] = "pytest-secret-key-not-for-production"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, engine, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import transaction, user  # noqa: F401,E402


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db_session():
    from sqlalchemy.orm import Session

    session = Session(bind=engine)
    try:
        yield session
    finally:
        session.close()
