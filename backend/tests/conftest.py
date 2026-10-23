import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app import models  # noqa: F401  (loads every table class)
from app.core.config import settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app as fastapi_app
from app.models.user import User, UserRole

TEST_DB_NAME = "resolviq_test"
_CONNECT_ARGS = {"connect_timeout": 5}  # fail in 5 seconds if Postgres is not running

_base_url = make_url(settings.database_url)
_test_url = _base_url.set(database=TEST_DB_NAME)


def _ensure_test_database() -> None:
    """Create the separate test database the first time, so tests never touch dev data."""
    admin_engine = create_engine(
        _base_url.set(database="postgres"),
        isolation_level="AUTOCOMMIT",
        connect_args=_CONNECT_ARGS,
    )
    with admin_engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": TEST_DB_NAME},
        ).scalar()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{TEST_DB_NAME}"'))
    admin_engine.dispose()


@pytest.fixture(scope="session")
def engine():
    _ensure_test_database()
    test_engine = create_engine(_test_url, pool_pre_ping=True, connect_args=_CONNECT_ARGS)
    Base.metadata.drop_all(test_engine)
    Base.metadata.create_all(test_engine)
    yield test_engine
    test_engine.dispose()


@pytest.fixture()
def db_session(engine):
    session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()
        # empty every table after each test so tests don't affect each other
        with engine.begin() as conn:
            for table in reversed(Base.metadata.sorted_tables):
                conn.execute(table.delete())


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    fastapi_app.dependency_overrides[get_db] = override_get_db
    with TestClient(fastapi_app) as test_client:
        yield test_client
    fastapi_app.dependency_overrides.clear()


@pytest.fixture()
def make_user(db_session):
    """Create a user straight in the test database (register only makes customers)."""

    def _make(
        email: str = "user@example.com",
        password: str = "StrongPass123",
        role: UserRole = UserRole.CUSTOMER,
        is_active: bool = True,
        name: str = "Test User",
    ) -> User:
        user = User(
            name=name,
            email=email.lower(),
            password_hash=hash_password(password),
            role=role.value,
            is_active=is_active,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    return _make
