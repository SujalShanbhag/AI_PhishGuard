import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield

def test_user_registration_and_login():
    client = TestClient(app)
    email = f"test_{pytest.__version__}@veritas.ai"
    password = "SecurePassword123!"

    # Register
    res = client.post("/api/auth/register", json={
        "email": email,
        "password": password,
        "full_name": "Test Forensic Agent"
    })
    assert res.status_code in [200, 400]  # 400 if already created

    # Login
    res = client.post("/api/auth/login", json={
        "email": email,
        "password": password
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_invalid_credentials():
    client = TestClient(app)
    res = client.post("/api/auth/login", json={
        "email": "nonexistent@veritas.ai",
        "password": "WrongPassword999!"
    })
    assert res.status_code == 401

def test_unauthenticated_protected_route():
    client = TestClient(app)
    client.cookies.clear()
    res = client.get("/api/auth/me")
    assert res.status_code == 401
