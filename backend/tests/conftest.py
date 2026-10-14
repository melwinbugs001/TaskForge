import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models
from app.core.config import Settings, get_settings
from app.db.base import Base
from app.db.database import get_db
from app.main import app

TEST_SETTINGS = Settings(
    database_url="sqlite://",
    jwt_secret="test-secret-that-is-long-enough-for-tests-only",
)


@pytest.fixture
def db_session() -> Session: # type: ignore
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = testing_session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def client(db_session: Session) -> TestClient: # type: ignore
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_settings] = lambda: TEST_SETTINGS
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "owner@example.com", "password": "secure-pass-123"},
    )
    assert response.status_code == 201
    token_response = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@example.com", "password": "secure-pass-123"},
    )
    assert token_response.status_code == 200
    return {"Authorization": f"Bearer {token_response.json()['access_token']}"}

