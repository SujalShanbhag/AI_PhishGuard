import os
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.database_models import User, Analysis
from app.security.authentication import get_optional_current_user, enforce_rate_limit
from app.services.gemini_service import gemini_copilot_service

router = APIRouter(prefix="/api/copilot", tags=["Gemini AI Copilot & Forensics"])


class ChatMessage(BaseModel):
    role: str = "user"
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User prompt or forensic question")
    history: Optional[List[ChatMessage]] = Field(default_factory=list)
    api_key: Optional[str] = None
    system_instruction: Optional[str] = None


class SetKeyRequest(BaseModel):
    api_key: str = Field(..., min_length=8, description="Google Gemini API Key")


@router.get("/status")
def get_copilot_status():
    """Returns Gemini AI Copilot status and active model information."""
    is_conf = gemini_copilot_service.is_configured()
    return {
        "configured": is_conf,
        "model": settings.GEMINI_MODEL,
        "engine": "Google Gemini 2.5 Flash" if is_conf else "Local Forensic Intelligence Engine",
        "capabilities": [
            "Multimodal Document & Marks Card Forgery Inspection",
            "Fee Receipt & Payment Tampering Detection",
            "Error Level Analysis (ELA) Heatmap Generation",
            "Phishing Email & Malicious Domain Dissection",
            "Indian DPDP Act 2023 & GDPR Privacy Compliance Advisory",
            "Deepfake Grad-CAM & Saliency Map Explanations"
        ],
        "has_runtime_key": is_conf
    }


@router.post("/set-key")
def set_gemini_api_key(req: SetKeyRequest):
    """Configures and tests Gemini API Key."""
    test_res = gemini_copilot_service.test_connection(req.api_key)
    if not test_res.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=test_res.get("message", "Invalid Gemini API key or connection failed.")
        )
    gemini_copilot_service.set_api_key(req.api_key)
    return {
        "status": "SUCCESS",
        "message": f"Gemini API key successfully verified and activated! Using {settings.GEMINI_MODEL}.",
        "model": settings.GEMINI_MODEL
    }


@router.post("/test-connection")
def test_connection(api_key: Optional[str] = None):
    """Tests connection to Gemini API."""
    res = gemini_copilot_service.test_connection(api_key)
    return res


@router.post("/chat")
def copilot_chat(
    req_body: ChatRequest,
    request: Request,
    user: Optional[User] = Depends(get_optional_current_user)
):
    """Processes conversational questions via Gemini AI or Local Forensic Engine."""
    enforce_rate_limit(request, max_requests=40, window_seconds=60)

    # Format history as dictionaries
    history_dicts = []
    if req_body.history:
        for m in req_body.history:
            history_dicts.append({"role": m.role, "content": m.content})
    
    # Append current message
    history_dicts.append({"role": "user", "content": req_body.message})

    response = gemini_copilot_service.chat(
        messages=history_dicts,
        api_key=req_body.api_key,
        system_instruction=req_body.system_instruction
    )
    return response


@router.post("/inspect-file")
async def inspect_uploaded_file(
    request: Request,
    file: UploadFile = File(...),
    prompt: Optional[str] = Form(None),
    api_key: Optional[str] = Form(None),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """Uploads any document or media file for multimodal forensic inspection."""
    enforce_rate_limit(request, max_requests=20, window_seconds=60)

    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > 25:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds maximum allowed size of 25MB for forensic inspection."
        )

    result = gemini_copilot_service.inspect_media(
        file_path_or_bytes=content,
        filename=file.filename or "uploaded_media.jpg",
        mime_type=file.content_type,
        prompt=prompt,
        api_key=api_key
    )
    return result


@router.post("/inspect-analysis/{analysis_id}")
def inspect_analysis_media(
    analysis_id: str,
    prompt: Optional[str] = None,
    api_key: Optional[str] = None,
    user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """Inspects media from an existing scan record using Gemini multimodal vision."""
    query = db.query(Analysis).filter(Analysis.id == analysis_id)
    if user and user.role != "admin":
        query = query.filter(Analysis.user_id == user.id)
    
    analysis = query.first()
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis record not found or access denied."
        )

    if not os.path.exists(analysis.stored_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Underlying media file is not available on disk."
        )

    result = gemini_copilot_service.inspect_media(
        file_path_or_bytes=analysis.stored_path,
        filename=analysis.original_filename,
        prompt=prompt,
        api_key=api_key
    )
    return result
