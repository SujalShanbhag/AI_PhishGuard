import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text
)
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    role = Column(String(50), default="analyst")
    account_status = Column(String(50), default="active")
    retention_days = Column(Integer, default=30)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    analyses = relationship("Analysis", back_populates="user", cascade="all, delete-orphan")
    identity_profile = relationship("IdentityProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    incidents = relationship("Incident", back_populates="user", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="user", cascade="all, delete-orphan")


class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    media_type = Column(String(20), nullable=False)  # IMAGE, VIDEO, AUDIO
    original_filename = Column(String(255), nullable=False)
    stored_path = Column(String(500), nullable=False)
    file_hash = Column(String(64), index=True, nullable=False)  # SHA-256
    file_size_bytes = Column(Integer, default=0)
    
    # Model tracking
    model_name = Column(String(100), default="VERITAS-EfficientNet-B4")
    model_version = Column(String(50), default="v1.0.0")
    
    # Status and scores
    status = Column(String(30), default="PENDING")  # PENDING, PROCESSING, COMPLETED, FAILED, SETUP_REQUIRED
    progress_percent = Column(Integer, default=0)
    assessment = Column(String(50), default="INCONCLUSIVE")  # POTENTIALLY_SUSPICIOUS, NO_STRONG_EVIDENCE, INCONCLUSIVE, SETUP_REQUIRED
    overall_score = Column(Float, nullable=True)
    confidence_margin = Column(Float, nullable=True)
    uncertainty_notes = Column(Text, nullable=True)
    
    # Modality scores
    visual_score = Column(Float, nullable=True)
    audio_score = Column(Float, nullable=True)
    sync_score = Column(Float, nullable=True)
    multimodal_fusion_score = Column(Float, nullable=True)
    
    # Metadata & outputs
    face_detected = Column(Boolean, default=False)
    face_count = Column(Integer, default=0)
    frame_count = Column(Integer, default=1)
    flagged_frame_count = Column(Integer, default=0)
    
    primary_face_crop_path = Column(String(500), nullable=True)
    primary_gradcam_path = Column(String(500), nullable=True)
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="analyses")
    frames = relationship("FrameResult", back_populates="analysis", cascade="all, delete-orphan", order_by="FrameResult.timestamp_seconds")
    reports = relationship("Report", back_populates="analysis", cascade="all, delete-orphan")
    incidents = relationship("Incident", back_populates="analysis")


class FrameResult(Base):
    __tablename__ = "frame_results"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    analysis_id = Column(String(36), ForeignKey("analyses.id"), nullable=False, index=True)
    frame_index = Column(Integer, nullable=False)
    timestamp_seconds = Column(Float, nullable=False)
    prediction_score = Column(Float, nullable=True)
    face_detected = Column(Boolean, default=False)
    face_crop_path = Column(String(500), nullable=True)
    gradcam_path = Column(String(500), nullable=True)
    processing_status = Column(String(30), default="PROCESSED")
    flag_for_review = Column(Boolean, default=False)

    analysis = relationship("Analysis", back_populates="frames")


class IdentityProfile(Base):
    __tablename__ = "identity_profiles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), unique=True, nullable=False)
    full_name = Column(String(255), nullable=True)
    reference_image_path = Column(String(500), nullable=False)
    embedding_json = Column(Text, nullable=True)  # Biometric embedding vector stored privately
    consent_recorded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="identity_profile")


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    analysis_id = Column(String(36), ForeignKey("analyses.id"), nullable=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    platform_detected = Column(String(100), nullable=True)
    date_discovered = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50), default="INVESTIGATING")  # INVESTIGATING, REPORTED, TAKEDOWN_REQUESTED, RESOLVED
    user_notes = Column(Text, nullable=True)
    recommended_steps = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="incidents")
    analysis = relationship("Analysis", back_populates="incidents")


class Report(Base):
    __tablename__ = "reports"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    analysis_id = Column(String(36), ForeignKey("analyses.id"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    report_path = Column(String(500), nullable=False)
    report_type = Column(String(10), default="PDF")  # PDF or JSON
    sha256_hash = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="reports")
    analysis = relationship("Analysis", back_populates="reports")
