import io
import csv
import json
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.synthetic_dataset import synthetic_dataset_service, validate_verhoeff

client = TestClient(app)


def test_datasets_catalog():
    res = client.get("/api/datasets/catalog")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert "datasets" in data
    assert len(data["datasets"]) >= 4

    keys = [d["key"] for d in data["datasets"]]
    assert "phishing" in keys
    assert "fraud" in keys
    assert "document_forgery" in keys
    assert "synthetic_10k" in keys


def test_preview_real_world_phishing_dataset():
    res = client.get("/api/datasets/preview/phishing?limit=10")
    assert res.status_code == 200
    data = res.json()
    assert data["dataset_key"] == "phishing"
    assert data["total_rows"] >= 1000
    assert "url" in data["columns"]
    assert "classification_label" in data["columns"]
    assert len(data["rows"]) == 10


def test_preview_synthetic_10k_dataset_has_required_fields():
    res = client.get("/api/datasets/preview/synthetic_10k?limit=15")
    assert res.status_code == 200
    data = res.json()
    assert data["total_rows"] == 10000
    assert len(data["columns"]) >= 35

    # Check that all 6 required fields are present in columns
    required_fields = ["name", "phone_no", "blood_group", "gender", "aadhar_no", "income"]
    for field in required_fields:
        assert field in data["columns"], f"Required field {field} missing from columns"

    # Check first row values
    first_row = data["rows"][0]
    for field in required_fields:
        assert first_row[field] is not None and str(first_row[field]).strip() != ""


def test_preview_search_filter():
    res = client.get("/api/datasets/preview/phishing?search=google&limit=10")
    assert res.status_code == 200
    data = res.json()
    for row in data["rows"]:
        row_str = " ".join(str(v).lower() for v in row.values())
        assert "google" in row_str


def test_generate_custom_synthetic_dataset_500_rows():
    req = {
        "rows": 500,
        "format": "csv",
        "extended_columns": True
    }
    res = client.post("/api/datasets/generate", json=req)
    assert res.status_code == 200
    assert res.headers["content-type"] == "text/csv; charset=utf-8"

    # Parse CSV to verify exact row count and columns
    csv_text = res.text
    reader = csv.DictReader(io.StringIO(csv_text))
    rows = list(reader)
    assert len(rows) == 500

    # Verify all 6 mandatory fields
    required_fields = ["name", "phone_no", "blood_group", "gender", "aadhar_no", "income"]
    for field in required_fields:
        assert field in reader.fieldnames, f"Mandatory column {field} missing"

    # Verify Verhoeff checksum on first 5 Aadhaar numbers
    for r in rows[:5]:
        raw_aadhaar = r["aadhar_no"].replace(" ", "")
        assert len(raw_aadhaar) == 12
        assert validate_verhoeff(raw_aadhaar), f"Invalid Aadhaar Verhoeff checksum: {raw_aadhaar}"


def test_download_real_world_dataset():
    res = client.get("/api/datasets/download/fraud")
    assert res.status_code == 200
    assert "real_world_fraud_dataset.csv" in res.headers.get("content-disposition", "")
    assert len(res.text) > 10000
