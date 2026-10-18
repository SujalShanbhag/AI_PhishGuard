import io
from PIL import Image
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.gemini_service import gemini_copilot_service

client = TestClient(app)


def create_test_image_bytes(width=200, height=200, color="white"):
    im = Image.new("RGB", (width, height), color=color)
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def test_copilot_status():
    res = client.get("/api/copilot/status")
    assert res.status_code == 200
    data = res.json()
    assert "model" in data
    assert "engine" in data
    assert "capabilities" in data
    assert len(data["capabilities"]) > 0


def test_copilot_chat_local_fallback():
    # Chat with questions about marks cards and document tampering
    req = {
        "message": "How do I verify if an academic marks card has altered grades?",
        "history": []
    }
    res = client.post("/api/copilot/chat", json=req)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert "reply" in data
    assert "Marks Card" in data["reply"] or "Academic" in data["reply"] or "forensic" in data["reply"].lower()


def test_copilot_chat_receipt_fraud():
    req = {
        "message": "Inspect payment fee receipt for photoshopped UTR and amount tampering",
        "history": []
    }
    res = client.post("/api/copilot/chat", json=req)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert "UTR" in data["reply"] or "Receipt" in data["reply"] or "transaction" in data["reply"].lower()


def test_copilot_chat_dpdp_privacy():
    req = {
        "message": "Explain DPDP Act 2023 redaction rules for Aadhaar and PAN numbers",
        "history": []
    }
    res = client.post("/api/copilot/chat", json=req)
    assert res.status_code == 200
    data = res.json()
    assert "Aadhaar" in data["reply"] or "PAN" in data["reply"] or "DPDP" in data["reply"]


def test_copilot_inspect_file():
    img_bytes = create_test_image_bytes(300, 300, "white")
    files = {"file": ("marks_card_sample.jpg", img_bytes, "image/jpeg")}
    data = {"prompt": "Check if this document has tampered numbers"}

    res = client.post("/api/copilot/inspect-file", files=files, data=data)
    assert res.status_code == 200
    resp_data = res.json()
    assert resp_data["status"] == "SUCCESS"
    assert "analysis" in resp_data
    assert "ela_heatmap_url" in resp_data or "metrics" in resp_data.get("ela_metrics", {})
    assert resp_data["filename"] == "marks_card_sample.jpg"


def test_copilot_inspect_actual_user_marks_card():
    # Test on actual user marks card file if present
    import os
    path = "data/uploads/241cc3f6-25ad-4f1c-a587-5b6d1b993976_marks_card.jpeg"
    if os.path.exists(path):
        with open(path, "rb") as f:
            content = f.read()
        res = gemini_copilot_service.inspect_media(content, "marks_card.jpeg")
        assert res["status"] == "SUCCESS"
        assert res["doc_type"] == "Academic Document / Marks Card"
        assert "ela_metrics" in res
        assert res["ela_metrics"]["dimensions"] == "1350x1600"
