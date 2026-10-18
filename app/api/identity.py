from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.database_models import User, IdentityProfile, Incident
from app.models.schemas import (
    IdentityProfileResponse, IdentityCompareRequest, IdentityCompareResponse,
    IncidentCreate, IncidentUpdate, IncidentResponse
)
from app.security.authentication import get_current_user
from app.security.file_security import validate_file_content
from app.services.identity_protection import identity_protection_service

router = APIRouter(prefix="/api/identity", tags=["Identity Protection"])

@router.post("/profile", response_model=IdentityProfileResponse)
async def create_or_update_identity_profile(
    consent: bool = Form(..., description="Explicit consent required for likeness protection"),
    full_name: Optional[str] = Form(None),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not consent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Explicit user consent is legally and ethically required to create a biometric reference profile."
        )

    file_bytes = await file.read()
    is_valid, err = validate_file_content(file_bytes, file.filename or "face.jpg", "image")
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err)

    result = identity_protection_service.create_or_update_profile(
        user_id=current_user.id,
        image_bytes=file_bytes,
        filename=file.filename or "face.jpg",
        full_name=full_name,
        db=db
    )

    if not result.get("success"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.get("message"))

    profile = db.query(IdentityProfile).filter(IdentityProfile.user_id == current_user.id).first()
    return IdentityProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        full_name=profile.full_name,
        consent_recorded_at=profile.consent_recorded_at,
        created_at=profile.created_at,
        has_reference_image=True,
        message=result["message"]
    )

@router.get("/profile")
def get_identity_profile_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profile = db.query(IdentityProfile).filter(IdentityProfile.user_id == current_user.id).first()
    if not profile:
        return {"has_profile": False, "message": "No identity reference profile registered."}

    return {
        "has_profile": True,
        "id": profile.id,
        "full_name": profile.full_name,
        "consent_recorded_at": profile.consent_recorded_at,
        "created_at": profile.created_at
    }

@router.delete("/profile")
def delete_identity_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    deleted = identity_protection_service.delete_profile(current_user.id, db)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No profile found to delete.")
    return {"message": "Identity reference image and facial embedding wiped securely."}

@router.post("/compare", response_model=IdentityCompareResponse)
def compare_identity(
    req: IdentityCompareRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    result = identity_protection_service.compare_likeness(
        user_id=current_user.id,
        analysis_id=req.analysis_id,
        threshold=req.threshold,
        db=db
    )
    return IdentityCompareResponse(**result)

# Incidents
@router.post("/incidents", response_model=IncidentResponse)
def create_incident(
    incident_in: IncidentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    incident = Incident(
        user_id=current_user.id,
        analysis_id=incident_in.analysis_id,
        title=incident_in.title,
        description=incident_in.description,
        platform_detected=incident_in.platform_detected,
        user_notes=incident_in.user_notes,
        recommended_steps=(
            "1. Export PDF Forensic Report.\n"
            "2. Document exact URL and timestamp of occurrence.\n"
            "3. Submit formal DMCA / synthetic likeness takedown request to hosting platform."
        )
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)
    return IncidentResponse.model_validate(incident)

@router.get("/incidents", response_model=List[IncidentResponse])
def get_user_incidents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    records = db.query(Incident).filter(Incident.user_id == current_user.id).order_by(Incident.created_at.desc()).all()
    return [IncidentResponse.model_validate(rec) for rec in records]

@router.put("/incidents/{incident_id}", response_model=IncidentResponse)
def update_incident(
    incident_id: str,
    inc_update: IncidentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    incident = db.query(Incident).filter(Incident.id == incident_id, Incident.user_id == current_user.id).first()
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident record not found.")

    if inc_update.title:
        incident.title = inc_update.title
    if inc_update.description:
        incident.description = inc_update.description
    if inc_update.status:
        incident.status = inc_update.status
    if inc_update.user_notes:
        incident.user_notes = inc_update.user_notes
    if inc_update.recommended_steps:
        incident.recommended_steps = inc_update.recommended_steps

    db.commit()
    db.refresh(incident)
    return IncidentResponse.model_validate(incident)

@router.delete("/incidents/{incident_id}")
def delete_incident(
    incident_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    incident = db.query(Incident).filter(Incident.id == incident_id, Incident.user_id == current_user.id).first()
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found.")
    db.delete(incident)
    db.commit()
    return {"message": "Incident record deleted."}
