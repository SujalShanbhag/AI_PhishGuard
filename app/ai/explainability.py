import os
from typing import Optional, Tuple, Dict, Any
import cv2
import numpy as np
import torch
import torch.nn.functional as F

from app.ai.deepfake_detector import deepfake_detector

EXPLAINABILITY_DISCLAIMER = (
    "Highlighted regions represent areas influencing the model's prediction. "
    "They are not definitive proof of manipulation."
)

class GradCAMExplainer:
    """
    Grad-CAM: Gradient-weighted Class Activation Mapping.
    Produces visual saliency heatmaps highlighting regions with strongest
    activation toward the manipulated class (e.g. blend boundaries, eyes, mouth).
    """
    def __init__(self):
        self.gradients: Optional[torch.Tensor] = None
        self.activations: Optional[torch.Tensor] = None
        self.hook_handles = []

    def _save_gradient(self, module, grad_input, grad_output):
        self.gradients = grad_output[0]

    def _save_activation(self, module, input, output):
        self.activations = output

    def generate_heatmap(self, face_bgr: np.ndarray, target_class: int = 1) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
        """
        Generates Grad-CAM visual explanation overlay.
        Returns:
        - blended_bgr: original face blended with heatmap
        - raw_heatmap: normalized grayscale heatmap (0-255)
        - metadata: technique used and disclaimers
        """
        if face_bgr is None or face_bgr.size == 0:
            blank = np.zeros((224, 224, 3), dtype=np.uint8)
            return blank, np.zeros((224, 224), dtype=np.uint8), {"method": "NONE", "disclaimer": EXPLAINABILITY_DISCLAIMER}

        h, w, _ = face_bgr.shape

        # If model is loaded, compute true neural Grad-CAM
        if deepfake_detector.is_loaded and deepfake_detector.model is not None:
            try:
                model = deepfake_detector.model
                target_layer = model.target_layer

                # Register forward and backward hooks
                fwd_handle = target_layer.register_forward_hook(self._save_activation)
                bwd_handle = target_layer.register_full_backward_hook(self._save_gradient)

                # Prepare tensor with gradient tracking
                tensor = deepfake_detector.preprocess_image(face_bgr)
                tensor.requires_grad_(True)

                # Forward pass
                model.zero_grad()
                logits = model(tensor)
                target_logit = logits[0, target_class]

                # Backward pass
                target_logit.backward()

                # Clean up hooks
                fwd_handle.remove()
                bwd_handle.remove()

                if self.gradients is not None and self.activations is not None:
                    # Global average pooling of gradients
                    pooled_gradients = torch.mean(self.gradients, dim=[0, 2, 3])
                    activations = self.activations[0]

                    # Weight channels by pooled gradients
                    for i in range(activations.shape[0]):
                        activations[i, :, :] *= pooled_gradients[i]

                    # Sum across channels and apply ReLU
                    cam = torch.sum(activations, dim=0).detach().cpu().numpy()
                    cam = np.maximum(cam, 0)

                    # Normalize between 0 and 1
                    if np.max(cam) > 0:
                        cam = cam / np.max(cam)
                    else:
                        cam = np.zeros_like(cam)

                    cam_resized = cv2.resize(cam, (w, h))
                    raw_heatmap = (cam_resized * 255).astype(np.uint8)
                    colored_heatmap = cv2.applyColorMap(raw_heatmap, cv2.COLORMAP_JET)

                    # Alpha blend
                    blended = cv2.addWeighted(face_bgr, 0.55, colored_heatmap, 0.45, 0)

                    return blended, raw_heatmap, {
                        "method": "Grad-CAM (True Gradient Activation)",
                        "target_layer": str(target_layer.__class__.__name__),
                        "disclaimer": EXPLAINABILITY_DISCLAIMER
                    }
            except Exception as e:
                print(f"[Grad-CAM] Notice: Grad-CAM execution fell back to edge saliency: {e}")

        # Fallback: High-Frequency Boundary Saliency (Laplacian & Gradient Energy)
        # This highlights boundary discontinuities (e.g. warping, splice seams)
        gray = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2GRAY)
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        edge_energy = np.sqrt(sobelx**2 + sobely**2) + np.abs(laplacian)

        # Smooth and normalize
        edge_energy = cv2.GaussianBlur(edge_energy, (15, 15), 0)
        norm_energy = cv2.normalize(edge_energy, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        colored_saliency = cv2.applyColorMap(norm_energy, cv2.COLORMAP_JET)
        blended = cv2.addWeighted(face_bgr, 0.55, colored_saliency, 0.45, 0)

        return blended, norm_energy, {
            "method": "High-Frequency Boundary Saliency (Heuristic / Setup Required)",
            "note": "Weights not loaded. Showing spatial boundary frequency distribution.",
            "disclaimer": EXPLAINABILITY_DISCLAIMER
        }


gradcam_explainer = GradCAMExplainer()
