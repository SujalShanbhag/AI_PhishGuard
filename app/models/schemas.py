from datetime import datetime
from typing import Optional, List, Dict, Any
import re
from pydantic import BaseModel, EmailStr, Field, ConfigDict, model_validator

# Authentication
class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Minimum 8 characters")
    full_name: Optional[str] = None
    role: Optional[str] = "analyst"

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    full_name: Optional[str] = None
    role: str
    account_status: str
    retention_days: int
    created_at: datetime

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

# Health & Capabilities
class CapabilitiesResponse(BaseModel):
    app_name: str
    version: str
    deepfake_detector_loaded: bool
    model_architecture: str
    face_detection_backend: str
    gradcam_available: bool
    gemini_copilot_available: bool = True
    ela_forensics_available: bool = True
    privacy_guard_available: bool = True
    datasets_hub_available: bool = True
    device: str
    disclaimer: str

# Frame Results
class FrameResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    frame_index: int
    timestamp_seconds: float
    prediction_score: Optional[float]
    face_detected: bool
    face_crop_url: Optional[str] = None
    gradcam_url: Optional[str] = None
    processing_status: str
    flag_for_review: bool

# Analysis
class AnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    media_type: str
    original_filename: str
    file_hash: str
    file_size_bytes: int
    model_name: str
    model_version: str
    status: str
    progress_percent: int
    assessment: str
    overall_score: Optional[float] = None
    confidence_margin: Optional[float] = None
    uncertainty_notes: Optional[str] = None
    visual_score: Optional[float] = None
    audio_score: Optional[float] = None
    sync_score: Optional[float] = None
    multimodal_fusion_score: Optional[float] = None
    face_detected: bool
    face_count: int
    frame_count: int
    flagged_frame_count: int
    primary_face_crop_url: Optional[str] = None
    primary_gradcam_url: Optional[str] = None
    sub_measures: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    frames: List[FrameResultResponse] = []

    @model_validator(mode="before")
    @classmethod
    def extract_sub_measures(cls, data: Any) -> Any:
        if hasattr(data, "sub_measures") and getattr(data, "sub_measures") is not None:
            return data
        notes = getattr(data, "uncertainty_notes", None) if hasattr(data, "uncertainty_notes") else (data.get("uncertainty_notes") if isinstance(data, dict) else None)
        if notes and "Multi-Signal Breakdown:" in notes:
            m_ela = re.search(r"ELA Discontinuity:\s*([\d\.]+)%", notes)
            m_spec = re.search(r"Spectral Frequency:\s*([\d\.]+)%", notes)
            m_noise = re.search(r"Sensor Noise:\s*([\d\.]+)%", notes)
            m_edge = re.search(r"Edge Coherence:\s*([\d\.]+)%", notes)
            extracted = {}
            if m_ela: extracted["ela_discontinuity"] = float(m_ela.group(1))
            if m_spec: extracted["spectral_frequency"] = float(m_spec.group(1))
            if m_noise: extracted["noise_residual"] = float(m_noise.group(1))
            if m_edge: extracted["edge_coherence"] = float(m_edge.group(1))
            if extracted:
                if isinstance(data, dict):
                    data["sub_measures"] = extracted
                else:
                    try:
                        setattr(data, "sub_measures", extracted)
                    except Exception:
                        pass
        return data

# Evidence Verification
class HashVerifyRequest(BaseModel):
    file_hash: str = Field(..., min_length=64, max_length=64, description="SHA-256 hash to verify")

class HashVerifyResponse(BaseModel):
    target_hash: str
    match_found: bool
    total_matches: int
    matches: List[Dict[str, Any]]
    disclaimer: str

# Identity Protection
class IdentityProfileResponse(BaseModel):
    id: str
    user_id: str
    full_name: Optional[str] = None
    consent_recorded_at: datetime
    created_at: datetime
    has_reference_image: bool
    message: str

class IdentityCompareRequest(BaseModel):
    analysis_id: str
    threshold: float = Field(0.75, ge=0.0, le=1.0)

class IdentityCompareResponse(BaseModel):
    analysis_id: str
    both_faces_detected: bool
    comparison_possible: bool
    similarity_score: Optional[float]
    threshold: float
    likeness_match: bool
    model_name: str
    confidence_notes: str
    disclaimer: str

# Incident Management
class IncidentCreate(BaseModel):
    analysis_id: Optional[str] = None
    title: str = Field(..., max_length=255)
    description: str
    platform_detected: Optional[str] = None
    user_notes: Optional[str] = None

class IncidentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    user_notes: Optional[str] = None
    recommended_steps: Optional[str] = None

class IncidentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    analysis_id: Optional[str] = None
    title: str
    description: str
    platform_detected: Optional[str] = None
    date_discovered: datetime
    status: str
    user_notes: Optional[str] = None
    recommended_steps: Optional[str] = None
    created_at: datetime

# Retention & Settings
class RetentionUpdate(BaseModel):
    retention_days: int = Field(..., ge=1, le=365)
