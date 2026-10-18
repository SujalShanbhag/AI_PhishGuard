import os
import uuid
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.database_models import User, Analysis, FrameResult
from app.models.schemas import AnalysisResponse, FrameResultResponse
from app.security.authentication import get_current_user, enforce_rate_limit
from app.security.file_security import (
    sanitize_filename, calculate_sha256, calculate_sha256_bytes, validate_file_content
)
from app.services.image_analysis import image_analysis_service
from app.workers.analysis_worker import dispatch_analysis

router = APIRouter(prefix="/api/analysis", tags=["Media Analysis"])

@router.post("/image", response_model=AnalysisResponse)
async def upload_and_analyze_image(
    req: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    enforce_rate_limit(req, max_requests=20, window_seconds=60)
    
    # Read and check size
    file_bytes = await file.read()
    size_mb = len(file_bytes) / (1024 * 1024)
    if size_mb > settings.MAX_IMAGE_SIZE_MB:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Image file exceeds maximum allowed size of {settings.MAX_IMAGE_SIZE_MB}MB."
        )

    # Validate binary content signature
    is_valid, mime_or_err = validate_file_content(file_bytes, file.filename or "image.jpg", "image")
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=mime_or_err)

    # Compute SHA-256
    file_hash = calculate_sha256_bytes(file_bytes)

    # Save to disk
    analysis_id = str(uuid.uuid4())
    clean_name = sanitize_filename(file.filename or "image.jpg")
    storage_path = str(Path(settings.UPLOAD_DIR) / f"{analysis_id}_{clean_name}")
    
    with open(storage_path, "wb") as f:
        f.write(file_bytes)

    # Create analysis record
    analysis = Analysis(
        id=analysis_id,
        user_id=current_user.id,
        media_type="IMAGE",
        original_filename=clean_name,
        stored_path=storage_path,
        file_hash=file_hash,
        file_size_bytes=len(file_bytes),
        model_name=settings.DEEPFAKE_MODEL_ARCH,
        status="PENDING"
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    # Execute synchronous image analysis for instant dashboard response
    updated_analysis = image_analysis_service.analyze_image(analysis_id, db)
    return AnalysisResponse.model_validate(updated_analysis or analysis)

@router.get("/history", response_model=List[AnalysisResponse])
def get_user_analysis_history(
    media_type: Optional[str] = None,
    assessment: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Analysis).filter(Analysis.user_id == current_user.id)
    if media_type:
        query = query.filter(Analysis.media_type == media_type.upper())
    if assessment:
        query = query.filter(Analysis.assessment == assessment.upper())

    records = query.order_by(Analysis.created_at.desc()).limit(100).all()
    return [AnalysisResponse.model_validate(rec) for rec in records]

@router.get("/{analysis_id}", response_model=AnalysisResponse)
def get_analysis_detail(
    analysis_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id, Analysis.user_id == current_user.id).first()
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis record not found.")
    return AnalysisResponse.model_validate(analysis)

@router.get("/{analysis_id}/frames", response_model=List[FrameResultResponse])
def get_analysis_frames(
    analysis_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id, Analysis.user_id == current_user.id).first()
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis record not found.")

    frames = db.query(FrameResult).filter(FrameResult.analysis_id == analysis_id).order_by(FrameResult.timestamp_seconds).all()
    return [FrameResultResponse.model_validate(f) for f in frames]

@router.get("/{analysis_id}/evidence/{evidence_type}")
def get_evidence_image(
    analysis_id: str,
    evidence_type: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Securely serves face crop or Grad-CAM heatmap only to the authorized user.
    Never exposes internal filesystem paths.
    """
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id, Analysis.user_id == current_user.id).first()
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found.")

    evidence_dir = Path(settings.EVIDENCE_DIR)
    
    if evidence_type in ["face", "primary_face"]:
        target_path = evidence_dir / f"{analysis_id}_best_face.jpg"
        if not target_path.exists():
            target_path = evidence_dir / f"{analysis_id}_face.jpg"
    elif evidence_type in ["gradcam", "primary_gradcam"]:
        target_path = evidence_dir / f"{analysis_id}_best_gradcam.jpg"
        if not target_path.exists():
            target_path = evidence_dir / f"{analysis_id}_gradcam.jpg"
    elif evidence_type.startswith("frame_"):
        parts = evidence_type.split("_")
        idx = parts[1] if len(parts) > 1 else "0"
        target_path = evidence_dir / f"{analysis_id}_f{idx}_face.jpg"
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid evidence type requested.")

    if not target_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence artifact file not found.")

    return FileResponse(str(target_path), media_type="image/jpeg")

@router.delete("/all")
def delete_all_analyses(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    analyses = db.query(Analysis).filter(Analysis.user_id == current_user.id).all()
    count = len(analyses)
    evidence_dir = Path(settings.EVIDENCE_DIR)

    for analysis in analyses:
        if os.path.exists(analysis.stored_path):
            try:
                os.remove(analysis.stored_path)
            except Exception:
                pass

        for p in evidence_dir.glob(f"{analysis.id}*"):
            try:
                p.unlink()
            except Exception:
                pass

        db.delete(analysis)

    db.commit()
    return {"message": f"Successfully deleted {count} analyses and all associated media files."}

@router.delete("/{analysis_id}")
def delete_analysis(
    analysis_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id, Analysis.user_id == current_user.id).first()
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis record not found.")

    # Remove stored media file
    if os.path.exists(analysis.stored_path):
        try:
            os.remove(analysis.stored_path)
        except Exception:
            pass

    # Remove evidence crops
    evidence_dir = Path(settings.EVIDENCE_DIR)
    for p in evidence_dir.glob(f"{analysis_id}*"):
        try:
            p.unlink()
        except Exception:
            pass

    db.delete(analysis)
    db.commit()
    return {"message": "Analysis and associated evidence artifacts deleted successfully."}
