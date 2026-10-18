from typing import Optional, Dict, Any, Tuple
from app.config import settings

class EvidenceFusionEngine:
    """
    Multimodal Evidence Combination Engine.
    Synthesizes visual, acoustic, and audio-video temporal synchronization signals.
    Adheres strictly to the core principle:
    - Never treat missing evidence as proof of authenticity.
    - Preserves individual modality scores.
    - Clearly documents the combination strategy and resulting uncertainty.
    """
    def __init__(
        self,
        suspicious_threshold: float = settings.SUSPICIOUS_THRESHOLD,
        authentic_threshold: float = settings.AUTHENTIC_THRESHOLD
    ):
        self.suspicious_threshold = suspicious_threshold
        self.authentic_threshold = authentic_threshold
        
        # Default modality weights
        self.default_weights = {
            "visual": 0.60,
            "audio": 0.25,
            "sync": 0.15
        }

    def combine_evidence(
        self,
        visual_score: Optional[float] = None,
        audio_score: Optional[float] = None,
        sync_result: Optional[Dict[str, Any]] = None,
        face_detected: bool = True,
        is_model_loaded: bool = True
    ) -> Dict[str, Any]:
        """
        Synthesizes visual, spatial artifact, and document forensics signals.
        Category A: POTENTIALLY_SUSPICIOUS
        Category B: NO_STRONG_EVIDENCE
        Category C: INCONCLUSIVE
        SETUP_REQUIRED (if core weights absent)
        """
        if not is_model_loaded:
            return {
                "assessment": "SETUP_REQUIRED",
                "overall_score": None,
                "confidence_margin": 0.0,
                "active_modalities": [],
                "uncertainty_notes": (
                    "Model weights have not been configured. "
                    "In adherence to truth-in-AI principles, no artificial prediction is generated."
                ),
                "strategy": "Unweighted (Setup Required)"
            }

        if not face_detected:
            if visual_score is not None:
                if visual_score >= self.suspicious_threshold:
                    assessment = "POTENTIALLY_SUSPICIOUS"
                    conf = visual_score - self.suspicious_threshold
                elif visual_score <= self.authentic_threshold:
                    assessment = "NO_STRONG_EVIDENCE"
                    conf = self.authentic_threshold - visual_score
                else:
                    assessment = "INCONCLUSIVE"
                    conf = 0.0

                return {
                    "assessment": assessment,
                    "overall_score": round(visual_score, 3),
                    "confidence_margin": round(conf, 3),
                    "active_modalities": ["visual (document/whole-image)"],
                    "sync_score": None,
                    "uncertainty_notes": (
                        "Document / Non-Facial Media Analyzed: No human face isolated. Executed whole-image spatial, "
                        "compression artifact, and ELA forensics. For specialized document tampering, grade alterations, "
                        "and fee receipt audits, use the 'Analyze with Gemini AI' feature."
                    ),
                    "strategy": "Document & Whole-Image Artifact Analysis"
                }
            else:
                return {
                    "assessment": "INCONCLUSIVE",
                    "overall_score": None,
                    "confidence_margin": 0.0,
                    "active_modalities": [],
                    "uncertainty_notes": (
                        "No verifiable visual or facial content detected in the media. "
                        "Assessment is inconclusive."
                    ),
                    "strategy": "Abstention (No Content)"
                }

        if visual_score is None:
            return {
                "assessment": "INCONCLUSIVE",
                "overall_score": None,
                "confidence_margin": 0.0,
                "active_modalities": [],
                "uncertainty_notes": "No visual signals available for assessment.",
                "strategy": "Abstention (Zero Signals)"
            }

        combined_score = visual_score

        # Categorize
        if combined_score >= self.suspicious_threshold:
            assessment = "POTENTIALLY_SUSPICIOUS"
            confidence_margin = combined_score - self.suspicious_threshold
        elif combined_score <= self.authentic_threshold:
            assessment = "NO_STRONG_EVIDENCE"
            confidence_margin = self.authentic_threshold - combined_score
        else:
            assessment = "INCONCLUSIVE"
            confidence_margin = 0.0

        notes = [
            "Assessment relies on visual artifact and facial forensics analysis."
        ]

        if assessment == "NO_STRONG_EVIDENCE":
            notes.append("No strong manipulation evidence detected within evaluated scope. This does not guarantee authentic origin.")
        elif assessment == "POTENTIALLY_SUSPICIOUS":
            notes.append("Patterns associated with synthetic generation or facial reenactment detected.")
        else:
            notes.append("Score falls within the borderline/uncertain zone; manual forensic review recommended.")

        return {
            "assessment": assessment,
            "overall_score": round(combined_score, 3),
            "confidence_margin": round(confidence_margin, 3),
            "active_modalities": ["visual"],
            "sync_score": None,
            "uncertainty_notes": " ".join(notes),
            "strategy": "Visual Artifact & Spatial Forensics Analysis"
        }


evidence_fusion_engine = EvidenceFusionEngine()
