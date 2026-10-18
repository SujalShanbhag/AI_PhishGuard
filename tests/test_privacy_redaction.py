import pytest
from pathlib import Path
import pymupdf
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from app.services.privacy_redaction import privacy_redaction_engine, validate_verhoeff, validate_luhn

client = TestClient(app)

def test_aadhaar_detection_and_redaction():
    # Valid Aadhaar generated with Verhoeff
    sample_text = "Please verify my citizen identity with Aadhaar number 2345 6789 0123 for verification."
    res = privacy_redaction_engine.scan_text(sample_text)
    
    assert res["total_entities_found"] >= 1
    aadhaar_findings = [f for f in res["findings"] if f["category"] == "Aadhaar Number"]
    assert len(aadhaar_findings) == 1
    assert "XXXX-XXXX-0123" in aadhaar_findings[0]["masked_value"]
    assert "AADHAAR_REDACTED" in res["sanitized_text"]
    assert "2345 6789 0123" not in res["sanitized_text"]

def test_pan_card_detection():
    sample_text = "Taxpayer Permanent Account Number is ABCDE1234F submitted for KYC."
    res = privacy_redaction_engine.scan_text(sample_text)
    
    pan_findings = [f for f in res["findings"] if f["category"] == "PAN Card Number"]
    assert len(pan_findings) == 1
    assert pan_findings[0]["value"] == "ABCDE1234F"
    assert "ABCDE****F" in pan_findings[0]["masked_value"]
    assert "ABCDE1234F" not in res["sanitized_text"]

def test_phone_and_email_detection():
    sample_text = "Contact the investigator at +91 9876543210 or email forensics.lead@agency.gov.in immediately."
    res = privacy_redaction_engine.scan_text(sample_text)
    
    categories = [f["category"] for f in res["findings"]]
    assert "Phone Number" in categories
    assert "Email Address" in categories
    assert "9876543210" not in res["sanitized_text"]
    assert "forensics.lead@agency.gov.in" not in res["sanitized_text"]

def test_password_and_secret_keys():
    sample_text = "Database connection: password=SuperSecretPassword2026! and API_KEY=ak_live_89172938471928"
    res = privacy_redaction_engine.scan_text(sample_text)
    
    cred_findings = [f for f in res["findings"] if f["category"] == "Password / Secret Key"]
    assert len(cred_findings) >= 1
    assert "SuperSecretPassword2026!" not in res["sanitized_text"]

def test_bank_account_and_ifsc():
    sample_text = "Remit compensation to Account No: 123456789012 with IFSC: HDFC0001234."
    res = privacy_redaction_engine.scan_text(sample_text)
    
    categories = [f["category"] for f in res["findings"]]
    assert "Bank Account Number" in categories
    assert "Bank Details (IFSC)" in categories
    assert "123456789012" not in res["sanitized_text"]

def test_medical_information():
    sample_text = "Patient diagnosed with malignant tumor in oncology ward, prescribed chemotherapy dosage 50mg."
    res = privacy_redaction_engine.scan_text(sample_text)
    
    med_findings = [f for f in res["findings"] if f["category"] == "Medical Information"]
    assert len(med_findings) >= 1
    assert any("oncology" in f["rule"].lower() or "chemotherapy" in f["rule"].lower() or "tumor" in f["rule"].lower() for f in med_findings)
    assert "MEDICAL_INFO_REDACTED" in res["sanitized_text"]

def test_company_confidential_data():
    sample_text = "STRICTLY CONFIDENTIAL AND PROPRIETARY: Project Titan merger target financial disclosure."
    res = privacy_redaction_engine.scan_text(sample_text)
    
    conf_findings = [f for f in res["findings"] if f["category"] == "Company Confidential Data"]
    assert len(conf_findings) >= 1
    assert res["risk_tier"] in ["CRITICAL", "HIGH", "MEDIUM"]
    assert "COMPANY_CONFIDENTIAL_REDACTED" in res["sanitized_text"]

def test_pdf_document_redaction():
    # Build a test PDF in-memory
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 100), "Confidential Aadhaar: 2345 6789 0123")
    page.insert_text((50, 140), "Email: analyst@secretcorp.com")
    page.insert_text((50, 180), "Salary grade: Strictly Confidential")
    pdf_bytes = doc.tobytes()
    doc.close()

    result = privacy_redaction_engine.redact_pdf_file(pdf_bytes, "test_doc.pdf")
    assert result["total_redactions_applied"] >= 2
    assert "download_url" in result

    # Verify that redacted PDF no longer contains sensitive text
    verify_doc = pymupdf.open(stream=open(Path(settings.REDACTED_DIR) / result["filename"], "rb").read(), filetype="pdf")
    redacted_text = verify_doc[0].get_text()
    verify_doc.close()

    assert "2345 6789 0123" not in redacted_text
    assert "analyst@secretcorp.com" not in redacted_text

def test_synthetic_kyc_fields_detection():
    sample_text = (
        "CANDIDATE ONBOARDING KYC RECORD:\n"
        "Full Name: Vikram Aditya Sharma\n"
        "Phone No.: +91 98765 43210\n"
        "Blood Group: O+\n"
        "Gender: Male\n"
        "Aadhar No.: 2345 6789 0123\n"
        "Annual Income: INR 18,50,000 per annum\n"
        "Email Address: vikram.sharma@enterprise.in\n"
        "PAN Card: ABCDE1234F"
    )
    res = privacy_redaction_engine.scan_text(sample_text)
    cats = {f["category"] for f in res["findings"]}

    # All 6 required fields + extra identifiers must be detected
    assert "Full Name" in cats
    assert "Phone Number" in cats
    assert "Blood Group" in cats
    assert "Gender" in cats
    assert "Aadhaar Number" in cats
    assert "Income / Salary" in cats

    # Check redaction tokens in output
    assert "NAME_REDACTED" in res["sanitized_text"]
    assert "PHONE_REDACTED" in res["sanitized_text"]
    assert "BLOOD_GROUP_REDACTED" in res["sanitized_text"]
    assert "GENDER_REDACTED" in res["sanitized_text"]
    assert "AADHAAR_REDACTED" in res["sanitized_text"]
    assert "INCOME_REDACTED" in res["sanitized_text"]

    # Verify calibrated severity
    assert res["risk_tier"] in ["HIGH", "CRITICAL"]

def test_synthetic_dataset_service_generation_all_formats():
    from app.services.synthetic_dataset import synthetic_dataset_service

    records = synthetic_dataset_service.generate_records(count=5)
    assert len(records) == 5

    # Verify all 6 required fields present in every record
    for r in records:
        assert "name" in r and len(r["name"]) > 3
        assert "phone_no" in r and "+91" in r["phone_no"]
        assert "blood_group" in r and any(bg in r["blood_group"] for bg in ["A", "B", "O", "AB"])
        assert "gender" in r and r["gender"] in ["Male", "Female", "Non-binary"]
        assert "aadhar_no" in r and len(r["aadhar_no"].replace(" ", "")) == 12
        assert "income" in r and len(r["income"]) > 5

    # Test export to all formats
    csv_bytes = synthetic_dataset_service.export_csv(records)
    assert b"name,phone_no,blood_group" in csv_bytes

    json_bytes = synthetic_dataset_service.export_json(records)
    assert b"records" in json_bytes

    txt_bytes = synthetic_dataset_service.export_txt(records)
    assert b"Aadhar No." in txt_bytes

    pdf_bytes = synthetic_dataset_service.export_pdf(records)
    assert pdf_bytes.startswith(b"%PDF")

    docx_bytes = synthetic_dataset_service.export_docx(records)
    assert docx_bytes.startswith(b"PK")  # ZIP archive

    xlsx_bytes = synthetic_dataset_service.export_xlsx(records)
    assert xlsx_bytes.startswith(b"PK")  # ZIP archive

    eml_bytes = synthetic_dataset_service.export_eml(records)
    assert b"Subject:" in eml_bytes and b"Blood Group:" in eml_bytes

def test_redact_any_file_all_synthetic_formats():
    from app.services.synthetic_dataset import synthetic_dataset_service

    records = synthetic_dataset_service.generate_records(count=3)
    formats = {
        "dataset.csv": synthetic_dataset_service.export_csv(records),
        "dataset.json": synthetic_dataset_service.export_json(records),
        "dataset.txt": synthetic_dataset_service.export_txt(records),
        "dataset.pdf": synthetic_dataset_service.export_pdf(records),
        "dataset.docx": synthetic_dataset_service.export_docx(records),
        "dataset.xlsx": synthetic_dataset_service.export_xlsx(records),
        "dataset.eml": synthetic_dataset_service.export_eml(records),
    }

    for fname, data in formats.items():
        res = privacy_redaction_engine.redact_any_file(data, fname)
        assert res["total_redactions_applied"] >= 1, f"Failed for {fname}"
        assert res["risk_tier"] in ["MEDIUM", "HIGH", "CRITICAL"], f"Failed tier for {fname}"

