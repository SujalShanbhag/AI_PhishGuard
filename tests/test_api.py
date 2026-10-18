import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_endpoint():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "HEALTHY"
    assert "service" in data

def test_capabilities_endpoint():
    res = client.get("/api/capabilities")
    assert res.status_code == 200
    data = res.json()
    assert "deepfake_detector_loaded" in data
    assert "disclaimer" in data
    assert "No AI system can provide absolute guarantees" in data["disclaimer"]

def test_verify_hash_endpoint():
    # Register and login self-contained test user
    email = "hash_tester@veritas.ai"
    pwd = "HashTestPassword2026!"
    client.post("/api/auth/register", json={"email": email, "password": pwd})
    login_res = client.post("/api/auth/login", json={"email": email, "password": pwd})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]

    dummy_hash = "a" * 64
    res = client.post(
        "/api/evidence/verify-hash",
        headers={"Authorization": f"Bearer {token}"},
        json={"file_hash": dummy_hash}
    )
    assert res.status_code == 200
    data = res.json()
    assert "match_found" in data
    assert "disclaimer" in data
