import torch
from fastapi import APIRouter
from app.config import settings
from app.ai.deepfake_detector import deepfake_detector
from app.models.schemas import CapabilitiesResponse

router = APIRouter(tags=["Health & Capabilities"])

@router.get("/api/health")
def health_check():
    return {
        "status": "HEALTHY",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV
    }

@router.get("/api/capabilities", response_model=CapabilitiesResponse)
def get_system_capabilities():
    device_str = "CUDA (NVIDIA GPU Acceleration)" if torch.cuda.is_available() else "CPU (Standard Processor)"
    meta = deepfake_detector.get_model_metadata()

    return CapabilitiesResponse(
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        deepfake_detector_loaded=deepfake_detector.is_loaded,
        model_architecture=settings.DEEPFAKE_MODEL_ARCH,
        face_detection_backend=settings.FACE_DETECTION_BACKEND,
        gradcam_available=settings.GRADCAM_ENABLED,
        gemini_copilot_available=True,
        ela_forensics_available=True,
        privacy_guard_available=True,
        datasets_hub_available=True,
        device=device_str,
        disclaimer=(
            "No AI system can provide absolute guarantees of digital media authenticity or manipulation. "
            "All assessments convey statistical likelihoods and algorithmic observations within evaluated scopes."
        )
    )
