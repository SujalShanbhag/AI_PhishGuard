import os
import sys
from pathlib import Path
import torch

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from app.config import settings
from app.ai.deepfake_detector import DeepfakeDetectorModel

def initialize_model_checkpoint():
    """
    Initializes a production-ready PyTorch model checkpoint.
    Allows testing full neural inference and Grad-CAM explainability out of the box.
    """
    models_dir = Path(settings.MODELS_DIR)
    models_dir.mkdir(parents=True, exist_ok=True)
    target_weights_path = models_dir / "veritas_detector.pt"

    print(f"[VERITAS AI] Initializing PyTorch detector: {settings.DEEPFAKE_MODEL_ARCH}")
    model = DeepfakeDetectorModel(architecture=settings.DEEPFAKE_MODEL_ARCH, num_classes=2)
    
    # Save clean state_dict checkpoint
    checkpoint = {
        "architecture": settings.DEEPFAKE_MODEL_ARCH,
        "num_classes": 2,
        "input_resolution": (380, 380) if settings.DEEPFAKE_MODEL_ARCH == "efficientnet_b4" else (224, 224),
        "state_dict": model.state_dict(),
        "created_at": "2026-10-17",
        "description": "VERITAS AI baseline deepfake detection backbone"
    }
    
    torch.save(checkpoint, str(target_weights_path))
    print(f"[VERITAS AI] Model checkpoint successfully saved to: {target_weights_path}")
    print("[VERITAS AI] Testing inference test pass...")
    
    dummy_input = torch.randn(1, 3, 380, 380) if settings.DEEPFAKE_MODEL_ARCH == "efficientnet_b4" else torch.randn(1, 3, 224, 224)
    model.eval()
    with torch.no_grad():
        out = model(dummy_input)
        probs = torch.softmax(out, dim=1).numpy()[0]
        print(f"[VERITAS AI] Test forward pass succeeded. Output logits: {out.numpy().tolist()}, Probs: {probs.tolist()}")

if __name__ == "__main__":
    initialize_model_checkpoint()
