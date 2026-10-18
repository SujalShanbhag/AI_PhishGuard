from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.database_models import User, Analysis
from app.models.schemas import HashVerifyRequest, HashVerifyResponse
from app.security.authentication import get_current_user

router = APIRouter(prefix="/api/evidence", tags=["Evidence Integrity"])

EVIDENCE_HASH_DISCLAIMER = (
    "A matching cryptographic SHA-256 hash verifies identical digital bitstream contents down to the single byte. "
    "A differing hash indicates bit-level alterations (such as compression or re-encoding), but does not prove whether "
    "the underlying visual scene represents authentic capture or synthetic manipulation."
)

@router.get("/{analysis_id}/hash")
def get_analysis_hash_record(
    analysis_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id, Analysis.user_id == current_user.id).first()
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis record not found.")

    return {
        "analysis_id": analysis.id,
        "original_filename": analysis.original_filename,
        "sha256_hash": analysis.file_hash,
        "file_size_bytes": analysis.file_size_bytes,
        "created_at": analysis.created_at,
        "disclaimer": EVIDENCE_HASH_DISCLAIMER
    }

@router.post("/verify-hash", response_model=HashVerifyResponse)
def verify_evidence_hash(
    req: HashVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    matches = db.query(Analysis).filter(
        Analysis.file_hash == req.file_hash.lower(),
        Analysis.user_id == current_user.id
    ).all()

    match_list = [
        {
            "analysis_id": m.id,
            "filename": m.original_filename,
            "media_type": m.media_type,
            "assessment": m.assessment,
            "timestamp": m.created_at.isoformat()
        }
        for m in matches
    ]

    return HashVerifyResponse(
        target_hash=req.file_hash.lower(),
        match_found=len(match_list) > 0,
        total_matches=len(match_list),
        matches=match_list,
        disclaimer=EVIDENCE_HASH_DISCLAIMER
    )
