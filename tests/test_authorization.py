import io
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def create_user_and_get_token(email: str, password: str = "AuthSecret2026!") -> str:
    client.post("/api/auth/register", json={"email": email, "password": password})
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    return res.json()["access_token"]

def test_cross_user_isolation():
    # User 1
    token1 = create_user_and_get_token("user1@veritas.ai")
    # User 2
    token2 = create_user_and_get_token("user2@veritas.ai")

    # User 1 uploads an image
    # Valid JPEG byte stream
    jpeg_data = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00" + b"\x00" * 200
    upload_res = client.post(
        "/api/analysis/image",
        headers={"Authorization": f"Bearer {token1}"},
        files={"file": ("evidence1.jpg", io.BytesIO(jpeg_data), "image/jpeg")}
    )
    assert upload_res.status_code == 200
    analysis_id = upload_res.json()["id"]

    # User 1 can view analysis
    res1 = client.get(f"/api/analysis/{analysis_id}", headers={"Authorization": f"Bearer {token1}"})
    assert res1.status_code == 200

    # User 2 CANNOT view User 1's analysis (404 isolation)
    res2 = client.get(f"/api/analysis/{analysis_id}", headers={"Authorization": f"Bearer {token2}"})
    assert res2.status_code == 404

    # User 1 can delete their own analysis
    del_res = client.delete(f"/api/analysis/{analysis_id}", headers={"Authorization": f"Bearer {token1}"})
    assert del_res.status_code == 200

    # Verification: analysis no longer exists
    res1_after = client.get(f"/api/analysis/{analysis_id}", headers={"Authorization": f"Bearer {token1}"})
    assert res1_after.status_code == 404

def test_purge_all_analyses():
    token = create_user_and_get_token("purge_user@veritas.ai")
    jpeg_data = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00" + b"\x00" * 200
    
    # Upload 2 files
    client.post("/api/analysis/image", headers={"Authorization": f"Bearer {token}"}, files={"file": ("f1.jpg", io.BytesIO(jpeg_data), "image/jpeg")})
    client.post("/api/analysis/image", headers={"Authorization": f"Bearer {token}"}, files={"file": ("f2.jpg", io.BytesIO(jpeg_data), "image/jpeg")})

    # Purge all
    purge_res = client.delete("/api/analysis/all", headers={"Authorization": f"Bearer {token}"})
    assert purge_res.status_code == 200

    # History should be empty
    hist_res = client.get("/api/analysis/history", headers={"Authorization": f"Bearer {token}"})
    assert hist_res.status_code == 200
    assert len(hist_res.json()) == 0
