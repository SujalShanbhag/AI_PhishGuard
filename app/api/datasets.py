import os
from pathlib import Path
from typing import Optional, List, Dict, Any
import pandas as pd
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse, Response

from app.config import settings
from app.models.database_models import User
from app.security.authentication import get_optional_current_user
from app.services.synthetic_dataset import synthetic_dataset_service

router = APIRouter(prefix="/api/datasets", tags=["Datasets Hub (Real-World & Synthetic)"])

DATASETS_DIR = Path("data/datasets")
SYNTHETIC_DIR = Path("data/synthetic_datasets")


class GenerateDatasetRequest(BaseModel):
    rows: int = Field(default=100, ge=1, le=10000, description="Number of synthetic rows to generate (up to 10,000)")
    format: str = Field(default="csv", description="Export format: csv, json, xlsx, txt, pdf, docx, eml")
    extended_columns: bool = Field(default=True, description="Include all 39+ cyber, financial, demographic fields")


AVAILABLE_DATASETS = {
    "phishing": {
        "title": "Real-World Phishing URLs & Threat Feed",
        "category": "REAL_WORLD",
        "description": "1,500 verified real-world malicious URLs and legitimate enterprise portals with URL character entropy, dot counts, SSL status, and target brand classifications.",
        "filename": "real_world_phishing_dataset.csv",
        "file_path": DATASETS_DIR / "real_world_phishing_dataset.csv",
        "default_format": "CSV"
    },
    "fraud": {
        "title": "Real-World Financial Fraud & Payment Tampering",
        "category": "REAL_WORLD",
        "description": "1,000 real financial transaction records detailing masked sender/receiver accounts, transaction amounts, merchant channels, and fraud detection labels.",
        "filename": "real_world_fraud_dataset.csv",
        "file_path": DATASETS_DIR / "real_world_fraud_dataset.csv",
        "default_format": "CSV"
    },
    "document_forgery": {
        "title": "Real-World Document Forgery & Tampering Benchmarks",
        "category": "REAL_WORLD",
        "description": "500 document forgery cases covering university marks cards, fee receipts, degrees, and government IDs with Error Level Analysis (ELA) and forgery vectors.",
        "filename": "real_world_document_forgery_benchmarks.csv",
        "file_path": DATASETS_DIR / "real_world_document_forgery_benchmarks.csv",
        "default_format": "CSV"
    },
    "synthetic_10k": {
        "title": "Large-Scale Synthetic KYC & Cyber Dataset (10,000 Rows)",
        "category": "SYNTHETIC_LARGE",
        "description": "10,000 records featuring all 6 required fields (Name, Phone No., Blood Group, Gender, Aadhar No., Income) plus 33 cyber risk, PAN, banking, and residential columns.",
        "filename": "synthetic_kyc_cyber_10000rows.csv",
        "file_path": DATASETS_DIR / "synthetic_kyc_cyber_10000rows.csv",
        "default_format": "CSV"
    }
}


@router.get("/catalog")
def get_datasets_catalog(user: Optional[User] = Depends(get_optional_current_user)):
    """
    Returns full catalog of Real-World and Large Synthetic Datasets
    with row counts, column schemas, and direct download links.
    """
    catalog = []
    DATASETS_DIR.mkdir(parents=True, exist_ok=True)

    for key, meta in AVAILABLE_DATASETS.items():
        fp = meta["file_path"]
        rows_count = 0
        cols_count = 0
        file_size_kb = 0.0
        sample_cols = []

        if fp.exists():
            file_size_kb = round(fp.stat().st_size / 1024, 1)
            try:
                # Read just header and row count efficiently
                df_sample = pd.read_csv(fp, nrows=2)
                sample_cols = list(df_sample.columns)
                cols_count = len(sample_cols)
                # Count total rows
                with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                    rows_count = sum(1 for _ in f) - 1
            except Exception:
                rows_count = 0

        catalog.append({
            "key": key,
            "title": meta["title"],
            "category": meta["category"],
            "description": meta["description"],
            "filename": meta["filename"],
            "rows": max(0, rows_count),
            "columns_count": cols_count,
            "columns": sample_cols,
            "size_kb": file_size_kb,
            "size_display": f"{file_size_kb / 1024:.2f} MB" if file_size_kb >= 1024 else f"{file_size_kb} KB",
            "download_url": f"/api/datasets/download/{key}"
        })

    # Also list synthetic pre-generated formats
    synthetic_dataset_service.generate_all_sample_files()
    synthetic_formats = []
    if SYNTHETIC_DIR.exists():
        for item in sorted(SYNTHETIC_DIR.iterdir()):
            if item.is_file():
                synthetic_formats.append({
                    "filename": item.name,
                    "format": item.suffix.lstrip(".").upper(),
                    "size_display": f"{item.stat().st_size / 1024:.1f} KB" if item.stat().st_size >= 1024 else f"{item.stat().st_size} B",
                    "download_url": f"/api/privacy/synthetic/download/{item.suffix.lstrip('.')}"
                })

    return {
        "status": "SUCCESS",
        "datasets": catalog,
        "pregenerated_formats": synthetic_formats,
        "core_required_fields": ["name", "phone_no", "blood_group", "gender", "aadhar_no", "income"],
        "total_available_datasets": len(catalog)
    }


@router.get("/preview/{dataset_key}")
def preview_dataset(
    dataset_key: str,
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    search: Optional[str] = Query(default=None),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """
    Returns preview data of any real-world or synthetic dataset
    for direct in-browser searching, sorting, and exploration.
    """
    if dataset_key not in AVAILABLE_DATASETS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset '{dataset_key}' not found. Choose from: {list(AVAILABLE_DATASETS.keys())}"
        )

    meta = AVAILABLE_DATASETS[dataset_key]
    fp = meta["file_path"]

    if not fp.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset file {meta['filename']} does not exist on disk."
        )

    try:
        df = pd.read_csv(fp)

        # Apply search if provided
        if search and search.strip():
            s = search.strip().lower()
            mask = df.astype(str).apply(lambda row: row.str.lower().str.contains(s, regex=False)).any(axis=1)
            df = df[mask]

        total_filtered = len(df)
        slice_df = df.iloc[offset: offset + limit]

        # Convert NaN to None for clean JSON serialization
        slice_df = slice_df.where(pd.notnull(slice_df), None)

        return {
            "dataset_key": dataset_key,
            "title": meta["title"],
            "total_rows": total_filtered,
            "columns": list(df.columns),
            "rows": slice_df.to_dict(orient="records"),
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reading dataset: {str(e)}"
        )


@router.get("/download/{dataset_key}")
def download_dataset(
    dataset_key: str,
    user: Optional[User] = Depends(get_optional_current_user)
):
    """Downloads the full real-world or large synthetic dataset file."""
    if dataset_key not in AVAILABLE_DATASETS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found."
        )

    meta = AVAILABLE_DATASETS[dataset_key]
    fp = meta["file_path"]
    if not fp.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File {meta['filename']} not found on disk."
        )

    return FileResponse(
        str(fp),
        media_type="text/csv",
        filename=meta["filename"],
        headers={"Content-Disposition": f"attachment; filename={meta['filename']}"}
    )


@router.post("/generate")
def generate_custom_dataset(
    req: GenerateDatasetRequest,
    user: Optional[User] = Depends(get_optional_current_user)
):
    """
    Generates a custom synthetic dataset with selectable row count
    (e.g., 50, 100, 500, 1000, 5000 rows) and format.
    """
    fmt = req.format.lower().lstrip(".")
    count = req.rows

    records = synthetic_dataset_service.generate_records(count=count, extended=req.extended_columns)

    format_map = {
        "csv": ("synthetic_dataset_custom.csv", "text/csv", synthetic_dataset_service.export_csv),
        "json": ("synthetic_dataset_custom.json", "application/json", synthetic_dataset_service.export_json),
        "xlsx": ("synthetic_dataset_custom.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", synthetic_dataset_service.export_xlsx),
        "txt": ("synthetic_dataset_custom.txt", "text/plain", synthetic_dataset_service.export_txt),
        "pdf": ("synthetic_dataset_custom.pdf", "application/pdf", synthetic_dataset_service.export_pdf),
        "docx": ("synthetic_dataset_custom.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", synthetic_dataset_service.export_docx),
        "eml": ("synthetic_dataset_custom.eml", "message/rfc822", synthetic_dataset_service.export_eml),
    }

    if fmt not in format_map:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format '{fmt}'. Choose from: {list(format_map.keys())}"
        )

    filename, media_type, export_fn = format_map[fmt]
    file_bytes = export_fn(records)

    # Save custom file
    out_path = SYNTHETIC_DIR / filename
    with open(out_path, "wb") as f:
        f.write(file_bytes)

    return Response(
        content=file_bytes,
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "X-Generated-Rows": str(len(records)),
            "X-Generated-Cols": str(len(records[0]) if records else 0)
        }
    )
