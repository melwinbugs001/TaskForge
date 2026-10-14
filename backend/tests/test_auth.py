from fastapi.testclient import TestClient


def test_register_login_and_get_current_user(client: TestClient) -> None:
    registered = client.post(
        "/api/v1/auth/register",
        json={"email": "Person@Example.com", "password": "correct-horse-123"},
    )
    assert registered.status_code == 201
    assert registered.json()["email"] == "person@example.com"
    assert "hashed_password" not in registered.json()

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "person@example.com", "password": "correct-horse-123"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    assert login.json()["token_type"] == "bearer"

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "person@example.com"


def test_registration_rejects_invalid_input_and_duplicate_email(
    client: TestClient,
) -> None:
    invalid = client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "password": "short"},
    )
    assert invalid.status_code == 422

    payload = {"email": "duplicate@example.com", "password": "secure-pass-123"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    duplicate = client.post(
        "/api/v1/auth/register",
        json={"email": "DUPLICATE@example.com", "password": "secure-pass-123"},
    )
    assert duplicate.status_code == 409


def test_login_rejects_invalid_credentials(client: TestClient) -> None:
    client.post(
        "/api/v1/auth/register",
        json={"email": "person@example.com", "password": "secure-pass-123"},
    )
    invalid = client.post(
        "/api/v1/auth/login",
        json={"email": "person@example.com", "password": "wrong-pass-123"},
    )
    assert invalid.status_code == 401


def test_me_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
