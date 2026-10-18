import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
import cv2
import numpy as np
from sqlalchemy.orm import Session

from app.config import settings
from app.models.database_models import IdentityProfile, Analysis
from app.ai.face_detector import face_detector

IDENTITY_DISCLAIMER = (
    "Face similarity does not constitute biometric identity verification or legal proof of likeness ownership. "
    "Similar facial features do not establish malicious impersonation, copyright violation, or criminal intent. "
    "VERITAS AI strictly does not conduct external internet or social media scraping."
)

class IdentityProtectionService:
    def create_or_update_profile(
        self,
        user_id: str,
        image_bytes: bytes,
        filename: str,
        full_name: Optional[str],
        db: Session
    ) -> Dict[str, Any]:
        """
        Registers consented reference face profile in private directory.
        Calculates and stores privacy-preserving normalized embedding.
        """
        # Save to private identity directory (isolated from public web server)
        identity_dir = Path(settings.IDENTITY_DIR)
        identity_dir.mkdir(parents=True, exist_ok=True)

        user_img_path = str(identity_dir / f"ref_{user_id}.jpg")
        with open(user_img_path, "wb") as f:
            f.write(image_bytes)

        # Detect face
        img_bgr = cv2.imread(user_img_path)
        if img_bgr is None:
            if os.path.exists(user_img_path):
                os.remove(user_img_path)
            return {"success": False, "message": "Failed to decode reference photograph."}

        faces = face_detector.detect_faces(img_bgr)
        if not faces:
            if os.path.exists(user_img_path):
                os.remove(user_img_path)
            return {
                "success": False,
                "message": "No clearly identifiable human face detected in reference photo. Please upload a clear frontal portrait."
            }

        # Extract normalized embedding
        primary_crop = faces[0]["face_crop"]
        embedding = face_detector.extract_face_embedding(primary_crop)
        embedding_json = json.dumps(embedding.tolist())

        # Update or create database record
        profile = db.query(IdentityProfile).filter(IdentityProfile.user_id == user_id).first()
        if not profile:
            profile = IdentityProfile(
                user_id=user_id,
                full_name=full_name,
                reference_image_path=user_img_path,
                embedding_json=embedding_json
            )
            db.add(profile)
        else:
            profile.full_name = full_name
            profile.reference_image_path = user_img_path
            profile.embedding_json = embedding_json

        db.commit()
        db.refresh(profile)

        return {
            "success": True,
            "message": "Consented identity reference profile registered successfully.",
            "profile_id": profile.id,
            "has_reference_image": True
        }

    def delete_profile(self, user_id: str, db: Session) -> bool:
        """Securely deletes user's reference image and biometric embedding records."""
        profile = db.query(IdentityProfile).filter(IdentityProfile.user_id == user_id).first()
        if not profile:
            return False

        if os.path.exists(profile.reference_image_path):
            try:
                os.remove(profile.reference_image_path)
            except Exception:
                pass

        db.delete(profile)
        db.commit()
        return True

    def compare_likeness(
        self,
        user_id: str,
        analysis_id: str,
        threshold: float,
        db: Session
    ) -> Dict[str, Any]:
        """
        Computes cosine similarity between user's consented reference profile
        and the primary face identified in an analyzed media artifact.
        """
        profile = db.query(IdentityProfile).filter(IdentityProfile.user_id == user_id).first()
        if not profile or not profile.embedding_json:
            return {
                "analysis_id": analysis_id,
                "both_faces_detected": False,
                "comparison_possible": False,
                "similarity_score": None,
                "threshold": threshold,
                "likeness_match": False,
                "model_name": "VERITAS-Biometric-Cosine-v1",
                "confidence_notes": "User does not have an active identity profile with a consented reference photograph.",
                "disclaimer": IDENTITY_DISCLAIMER
            }

        analysis = db.query(Analysis).filter(Analysis.id == analysis_id, Analysis.user_id == user_id).first()
        if not analysis:
            return {
                "analysis_id": analysis_id,
                "both_faces_detected": False,
                "comparison_possible": False,
                "similarity_score": None,
                "threshold": threshold,
                "likeness_match": False,
                "model_name": "VERITAS-Biometric-Cosine-v1",
                "confidence_notes": "Analysis record not found or unauthorized.",
                "disclaimer": IDENTITY_DISCLAIMER
            }

        if not analysis.face_detected:
            return {
                "analysis_id": analysis_id,
                "both_faces_detected": False,
                "comparison_possible": False,
                "similarity_score": None,
                "threshold": threshold,
                "likeness_match": False,
                "model_name": "VERITAS-Biometric-Cosine-v1",
                "confidence_notes": "The target media contains no detected face to compare against.",
                "disclaimer": IDENTITY_DISCLAIMER
            }

        # Load reference embedding
        ref_vec = np.array(json.loads(profile.embedding_json), dtype=np.float32)

        # Detect face in target media file
        target_bgr = cv2.imread(analysis.stored_path)
        if target_bgr is None:
            # Fallback if video: try to read best face crop from evidence dir
            p_crop = Path(settings.EVIDENCE_DIR) / f"{analysis_id}_best_face.jpg"
            if not p_crop.exists():
                p_crop = Path(settings.EVIDENCE_DIR) / f"{analysis_id}_face.jpg"
            if p_crop.exists():
                target_face = cv2.imread(str(p_crop))
            else:
                target_face = None
        else:
            faces = face_detector.detect_faces(target_bgr)
            target_face = faces[0]["face_crop"] if faces else None

        if target_face is None:
            return {
                "analysis_id": analysis_id,
                "both_faces_detected": False,
                "comparison_possible": False,
                "similarity_score": None,
                "threshold": threshold,
                "likeness_match": False,
                "model_name": "VERITAS-Biometric-Cosine-v1",
                "confidence_notes": "Could not extract face bitmap from target media.",
                "disclaimer": IDENTITY_DISCLAIMER
            }

        target_vec = face_detector.extract_face_embedding(target_face)

        # Cosine Similarity: dot product of L2 normalized vectors
        similarity = float(np.dot(ref_vec, target_vec))
        # Clamp to [0.0, 1.0]
        similarity = max(0.0, min(1.0, similarity))

        is_match = similarity >= threshold

        return {
            "analysis_id": analysis_id,
            "both_faces_detected": True,
            "comparison_possible": True,
            "similarity_score": round(similarity, 3),
            "threshold": threshold,
            "likeness_match": is_match,
            "model_name": "VERITAS-Biometric-Cosine-v1",
            "confidence_notes": (
                f"Facial similarity computed at {similarity * 100:.1f}%. "
                f"Evaluation against configured threshold {threshold * 100:.1f}% indicates "
                f"{'potential likeness overlap' if is_match else 'no significant likeness correlation'}."
            ),
            "disclaimer": IDENTITY_DISCLAIMER
        }


identity_protection_service = IdentityProtectionService()
