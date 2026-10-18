import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import cv2
import numpy as np
from sqlalchemy.orm import Session

from app.config import settings
from app.models.database_models import Analysis, FrameResult
from app.ai.face_detector import face_detector
from app.ai.deepfake_detector import deepfake_detector
from app.ai.explainability import gradcam_explainer
from app.services.evidence_fusion import evidence_fusion_engine

class ImageAnalysisService:
    def analyze_image(self, analysis_id: str, db: Session) -> Optional[Analysis]:
        """
        Executes end-to-end image deepfake analysis:
        1. Decode image safely.
        2. Detect faces with context margin (ensemble: alt2, default, profile).
        3. If no face is detected, extracts salient central region for whole-image forensics.
        4. Run deepfake inference on region of interest.
        5. Generate Grad-CAM saliency explanation.
        6. Combine evidence with uncertainty-aware fusion.
        """
        analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
        if not analysis or not os.path.exists(analysis.stored_path):
            return None

        analysis.status = "PROCESSING"
        analysis.progress_percent = 20
        db.commit()

        try:
            # Safe image decode with EXIF auto-rotation for smartphone portrait captures & scans
            try:
                from PIL import Image, ImageOps
                with Image.open(analysis.stored_path) as pil_img:
                    pil_img = ImageOps.exif_transpose(pil_img)
                    rgb_arr = np.array(pil_img.convert("RGB"))
                    image_bgr = cv2.cvtColor(rgb_arr, cv2.COLOR_RGB2BGR)
            except Exception:
                image_bgr = cv2.imread(analysis.stored_path)

            if image_bgr is None:
                analysis.status = "FAILED"
                analysis.error_message = "Failed to decode image data into valid bitmap."
                db.commit()
                return analysis

            analysis.progress_percent = 40
            db.commit()

            # Multi-pass face detection
            detected_faces = face_detector.detect_faces(image_bgr)
            face_detected = len(detected_faces) > 0
            analysis.face_detected = face_detected
            analysis.face_count = len(detected_faces)

            evidence_dir = Path(settings.EVIDENCE_DIR)
            evidence_dir.mkdir(parents=True, exist_ok=True)

            # Extract target crop: face crop if present, or fallback salient whole-image region
            if face_detected:
                primary_face = detected_faces[0]
                target_crop = primary_face["face_crop"]
            else:
                target_crop = face_detector.extract_fallback_region(image_bgr)

            # Save inspection crop
            face_filename = f"{analysis_id}_face.jpg"
            face_crop_path = str(evidence_dir / face_filename)
            cv2.imwrite(face_crop_path, target_crop)
            face_crop_rel_path = f"/api/analysis/{analysis_id}/evidence/face"

            analysis.progress_percent = 60
            db.commit()

            # Neural Deepfake & Forensic Signal Inference
            visual_score = None
            sub_measures = None
            pred = deepfake_detector.predict_image(target_crop)
            if pred["status"] == "SUCCESS":
                visual_score = pred["score"]
                sub_measures = pred.get("sub_measures")
            elif pred["status"] == "SETUP_REQUIRED":
                analysis.status = "SETUP_REQUIRED"
                analysis.assessment = "SETUP_REQUIRED"
                analysis.uncertainty_notes = pred["message"]
                analysis.progress_percent = 100
                analysis.completed_at = datetime.utcnow()
                db.commit()
                return analysis

            # Grad-CAM Explainability
            analysis.progress_percent = 80
            db.commit()

            blended, raw_cam, meta = gradcam_explainer.generate_heatmap(target_crop)
            gradcam_filename = f"{analysis_id}_gradcam.jpg"
            gradcam_path = str(evidence_dir / gradcam_filename)
            cv2.imwrite(gradcam_path, blended)
            gradcam_rel_path = f"/api/analysis/{analysis_id}/evidence/gradcam"

            # Combine evidence with fusion engine
            fusion_result = evidence_fusion_engine.combine_evidence(
                visual_score=visual_score,
                audio_score=None,
                sync_result=None,
                face_detected=face_detected,
                is_model_loaded=deepfake_detector.is_loaded
            )

            # Build comprehensive forensic notes with granular sub-measures
            notes = fusion_result.get("uncertainty_notes", "")
            if sub_measures:
                breakdown_str = (
                    f" • Multi-Signal Breakdown: ELA Discontinuity: {sub_measures.get('ela_discontinuity', 0)}%, "
                    f"Spectral Frequency: {sub_measures.get('spectral_frequency', 0)}%, "
                    f"Sensor Noise: {sub_measures.get('noise_residual', 0)}%, "
                    f"Edge Coherence: {sub_measures.get('edge_coherence', 0)}%."
                )
                notes = f"{notes}{breakdown_str}"

            # Update analysis record
            analysis.visual_score = visual_score
            analysis.overall_score = fusion_result.get("overall_score")
            analysis.confidence_margin = fusion_result.get("confidence_margin")
            analysis.assessment = fusion_result.get("assessment")
            analysis.uncertainty_notes = notes
            analysis.primary_face_crop_path = face_crop_rel_path
            analysis.primary_gradcam_path = gradcam_rel_path
            analysis.status = "COMPLETED"
            analysis.progress_percent = 100
            analysis.completed_at = datetime.utcnow()
            analysis.sub_measures = sub_measures

            # Record single frame entry for evidence explorer UI
            frame_entry = FrameResult(
                analysis_id=analysis_id,
                frame_index=0,
                timestamp_seconds=0.0,
                prediction_score=visual_score,
                face_detected=face_detected,
                face_crop_path=face_crop_rel_path,
                gradcam_path=gradcam_rel_path,
                processing_status="COMPLETED",
                flag_for_review=(visual_score is not None and visual_score >= settings.SUSPICIOUS_THRESHOLD)
            )
            db.add(frame_entry)
            db.commit()
            db.refresh(analysis)
            return analysis

        except Exception as e:
            analysis.status = "FAILED"
            analysis.error_message = f"Image processing error: {str(e)}"
            analysis.completed_at = datetime.utcnow()
            db.commit()
            return analysis


image_analysis_service = ImageAnalysisService()
