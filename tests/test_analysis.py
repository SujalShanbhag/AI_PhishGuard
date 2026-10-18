import numpy as np
import pytest
from app.ai.face_detector import face_detector
from app.ai.deepfake_detector import deepfake_detector
from app.ai.explainability import gradcam_explainer, EXPLAINABILITY_DISCLAIMER
from app.services.evidence_fusion import evidence_fusion_engine

def test_deepfake_detector_interface():
    meta = deepfake_detector.get_model_metadata()
    assert "model_name" in meta
    assert "architecture" in meta
    assert "known_limitations" in meta
    assert len(meta["known_limitations"]) > 0

def test_face_detector_synthetic_image():
    # Blank 200x200 image -> 0 faces
    blank = np.zeros((200, 200, 3), dtype=np.uint8)
    faces = face_detector.detect_faces(blank)
    assert isinstance(faces, list)
    assert len(faces) == 0

def test_gradcam_explainer_with_disclaimer():
    test_face = np.full((128, 128, 3), 120, dtype=np.uint8)
    blended, heatmap, meta = gradcam_explainer.generate_heatmap(test_face)
    
    assert blended.shape == (128, 128, 3)
    assert heatmap.shape == (128, 128)
    assert "disclaimer" in meta
    assert meta["disclaimer"] == EXPLAINABILITY_DISCLAIMER

def test_evidence_fusion_uncertainty_no_content():
    result = evidence_fusion_engine.combine_evidence(
        visual_score=None,
        audio_score=None,
        sync_result=None,
        face_detected=False,
        is_model_loaded=True
    )
    assert result["assessment"] == "INCONCLUSIVE"
    assert "No verifiable visual or facial content" in result["uncertainty_notes"]

def test_evidence_fusion_whole_image_fallback():
    result = evidence_fusion_engine.combine_evidence(
        visual_score=0.85,
        audio_score=None,
        sync_result=None,
        face_detected=False,
        is_model_loaded=True
    )
    assert result["assessment"] == "POTENTIALLY_SUSPICIOUS"
    assert "whole-image" in result["uncertainty_notes"].lower()

def test_evidence_fusion_suspicious_verdict():
    result = evidence_fusion_engine.combine_evidence(
        visual_score=0.85,
        audio_score=0.75,
        sync_result=None,
        face_detected=True,
        is_model_loaded=True
    )
    assert result["assessment"] == "POTENTIALLY_SUSPICIOUS"
    assert result["overall_score"] >= 0.65

def test_evidence_fusion_clean_verdict():
    result = evidence_fusion_engine.combine_evidence(
        visual_score=0.20,
        audio_score=0.15,
        sync_result=None,
        face_detected=True,
        is_model_loaded=True
    )
    assert result["assessment"] == "NO_STRONG_EVIDENCE"
    assert result["overall_score"] <= 0.35

def test_deepfake_detector_multi_signal_forensics():
    # Synthetic test image
    img = np.random.randint(50, 200, (224, 224, 3), dtype=np.uint8)
    res = deepfake_detector.predict_image(img)
    assert res["status"] == "SUCCESS"
    # Ensure score is not pinned at the 0.501 bug
    assert res["score"] != 0.501
    assert 0.0 <= res["score"] <= 1.0
    # Ensure sub_measures are present
    assert "sub_measures" in res
    subs = res["sub_measures"]
    assert "ela_discontinuity" in subs
    assert "spectral_frequency" in subs
    assert "noise_residual" in subs
    assert "edge_coherence" in subs
    assert all(0 <= v <= 100 for v in subs.values())

def test_face_detector_fallback_and_rotation():
    # Blank image returns no faces, fallback extracts region
    blank = np.zeros((300, 300, 3), dtype=np.uint8)
    fallback = face_detector.extract_fallback_region(blank)
    assert fallback.shape[0] > 0 and fallback.shape[1] > 0

    # Test multi-rotation returns list without error
    faces = face_detector.detect_faces(blank)
    assert isinstance(faces, list)
    assert len(faces) == 0

def test_analysis_response_schema_sub_measures():
    from app.models.schemas import AnalysisResponse
    from datetime import datetime

    payload = {
        "id": "test-id-123",
        "user_id": "user-456",
        "media_type": "IMAGE",
        "original_filename": "sample.jpg",
        "file_hash": "a" * 64,
        "file_size_bytes": 1024,
        "model_name": "VERITAS",
        "model_version": "v1.0",
        "status": "COMPLETED",
        "progress_percent": 100,
        "assessment": "NO_STRONG_EVIDENCE",
        "uncertainty_notes": "Clean image. • Multi-Signal Breakdown: ELA Discontinuity: 14.5%, Spectral Frequency: 22.1%, Sensor Noise: 31.0%, Edge Coherence: 18.2%.",
        "face_detected": True,
        "face_count": 1,
        "frame_count": 1,
        "flagged_frame_count": 0,
        "created_at": datetime.utcnow()
    }
    resp = AnalysisResponse.model_validate(payload)
    assert resp.sub_measures is not None
    assert resp.sub_measures["ela_discontinuity"] == 14.5
    assert resp.sub_measures["spectral_frequency"] == 22.1
    assert resp.sub_measures["noise_residual"] == 31.0
    assert resp.sub_measures["edge_coherence"] == 18.2

