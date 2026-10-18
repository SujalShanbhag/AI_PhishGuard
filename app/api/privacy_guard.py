import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.config import settings
from app.models.database_models import User
from app.security.authentication import get_current_user
from app.services.privacy_redaction import privacy_redaction_engine
from app.services.report_generation import report_generation_service

router = APIRouter(prefix="/api/privacy", tags=["Privacy Guard & Redactor"])

class TextScanRequest(BaseModel):
    text: str

class TextScanResponse(BaseModel):
    risk_score: int
    risk_tier: str
    total_entities_found: int
    findings: List[Dict[str, Any]]
    sanitized_text: str
    compliance_violations: List[Dict[str, Any]]

@router.post("/scan-text", response_model=TextScanResponse)
def scan_and_redact_text(
    req: TextScanRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Scans text for Aadhaar, PAN, phone, email, passwords, bank accounts,
    medical data, and company confidential information.
    Returns sanitized text and privacy risk scoring.
    """
    if not req.text.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Text payload cannot be empty.")

    results = privacy_redaction_engine.scan_text(req.text)
    return TextScanResponse(**results)

@router.post("/redact-document")
async def redact_uploaded_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Performs true bitstream redaction on uploaded PDF or TXT documents,
    blacking out sensitive PII before ingestion into external AI workflows.
    """
    file_bytes = await file.read()
    filename = file.filename or "document.pdf"
    try:
        res = privacy_redaction_engine.redact_any_file(file_bytes, filename)
        return res
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"File ingestion and redaction error: {str(e)}")

@router.get("/download-redacted/{redacted_id}")
def download_redacted_document(
    redacted_id: str,
    current_user: User = Depends(get_current_user)
):
    redacted_dir = Path(settings.REDACTED_DIR)
    matches = list(redacted_dir.glob(f"redacted_{redacted_id[:8]}*"))
    if not matches:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Redacted document not found.")

    target_file = matches[0]
    media_type = "application/pdf" if target_file.suffix == ".pdf" else "text/plain"

    return FileResponse(
        str(target_file),
        media_type=media_type,
        filename=target_file.name,
        headers={"Content-Disposition": f"attachment; filename={target_file.name}"}
    )

class PrivacyReportRequest(BaseModel):
    title: str = "Scanned Document"
    text: Optional[str] = None
    scan_results: Optional[Dict[str, Any]] = None

@router.post("/export-report")
def export_privacy_audit_report(
    req: PrivacyReportRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Generates and returns a downloadable formal Privacy & PII Compliance PDF Report.
    """
    if req.scan_results:
        scan_res = req.scan_results
    elif req.text:
        scan_res = privacy_redaction_engine.scan_text(req.text)
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Must provide text or scan_results.")

    pdf_path = report_generation_service.generate_privacy_pdf_report(
        filename=req.title,
        scan_res=scan_res,
        user_email=current_user.email
    )
    filename = Path(pdf_path).name
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=filename,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# -------------------------------------------------------------
# SYNTHETIC DATASET ENDPOINTS
# -------------------------------------------------------------
from app.services.synthetic_dataset import synthetic_dataset_service

@router.get("/synthetic/generate")
def generate_synthetic_records(
    count: int = 10,
    current_user: User = Depends(get_current_user)
):
    """
    Generates synthetic PII & KYC records on demand containing:
    name, phone no., blood group, gender, aadhar no., and income.
    """
    valid_count = max(1, min(100, count))
    records = synthetic_dataset_service.generate_records(valid_count)
    return {
        "status": "success",
        "total_records": len(records),
        "fields": ["name", "phone_no", "blood_group", "gender", "aadhar_no", "income", "email", "pan_no"],
        "records": records
    }


@router.get("/synthetic/download/{file_format}")
def download_synthetic_dataset(
    file_format: str,
    count: int = 15,
    current_user: User = Depends(get_current_user)
):
    """
    Exports and downloads synthetic datasets in any format:
    csv, json, txt, pdf, docx, xlsx, eml.
    """
    fmt = file_format.lower().lstrip(".")
    records = synthetic_dataset_service.generate_records(max(1, min(50, count)))

    format_map = {
        "csv": ("synthetic_dataset.csv", "text/csv", synthetic_dataset_service.export_csv),
        "json": ("synthetic_dataset.json", "application/json", synthetic_dataset_service.export_json),
        "txt": ("synthetic_dataset.txt", "text/plain", synthetic_dataset_service.export_txt),
        "pdf": ("synthetic_dataset.pdf", "application/pdf", synthetic_dataset_service.export_pdf),
        "docx": ("synthetic_dataset.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", synthetic_dataset_service.export_docx),
        "xlsx": ("synthetic_dataset.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", synthetic_dataset_service.export_xlsx),
        "eml": ("synthetic_dataset.eml", "message/rfc822", synthetic_dataset_service.export_eml)
    }

    if fmt not in format_map:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format '{fmt}'. Choose from: {list(format_map.keys())}"
        )

    filename, media_type, export_fn = format_map[fmt]
    file_bytes = export_fn(records)

    # Save to disk as well
    out_path = Path("data/synthetic_datasets") / filename
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(file_bytes)

    return FileResponse(
        str(out_path),
        media_type=media_type,
        filename=filename,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/synthetic/catalog")
def get_synthetic_dataset_catalog(
    current_user: User = Depends(get_current_user)
):
    """
    Returns the pre-generated synthetic datasets catalog for direct download.
    """
    synthetic_dataset_service.generate_all_sample_files()
    catalog_dir = Path("data/synthetic_datasets")
    files_info = []

    for item in sorted(catalog_dir.iterdir()):
        if item.is_file():
            files_info.append({
                "filename": item.name,
                "format": item.suffix.lstrip(".").upper(),
                "size_bytes": item.stat().st_size,
                "size_display": f"{item.stat().st_size / 1024:.1f} KB" if item.stat().st_size >= 1024 else f"{item.stat().st_size} B",
                "download_url": f"/api/privacy/synthetic/download/{item.suffix.lstrip('.')}"
            })

    return {
        "status": "success",
        "description": "Synthetic KYC & PII datasets containing: Name, Phone No., Blood Group, Gender, Aadhar No., Income",
        "datasets": files_info
    }


