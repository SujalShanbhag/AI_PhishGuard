# VERITAS AI — Model Setup & Neural Inference Guide

## 1. Supported Architectures

VERITAS AI supports standard computer vision backbones adapted for binary face forensics:
- **Default Backbone:** `EfficientNet-B4` (Input resolution: $380 \times 380$, 3 channels, ImageNet normalized)
- **Alternative Backbone:** `ResNet50` (Input resolution: $224 \times 224$, 3 channels, ImageNet normalized)

Classification Head:
- 2 Classes:
  - Class 0: **Authentic** (Original, unmanipulated capture)
  - Class 1: **Manipulated** (Synthetic face swap, reenactment, or neural texture alteration)

---

## 2. Model Provenance & Truth-in-AI Guarantee

In adherence to the core VERITAS charter:
- **No Fabricated Predictions:** If model weights are not loaded, the system will explicitly return `status: "SETUP_REQUIRED"` rather than generating synthetic or random confidence scores.
- **Pretrained Checkpoint Location:** `./data/models/veritas_detector.pt`
- **License:** Apache 2.0 / BSD 3-Clause

---

## 3. Initializing Local Baseline Model Checkpoint

To initialize the verified local PyTorch model checkpoint out-of-the-box:

```bash
python scripts/initialize_models.py
```

This script:
1. Instantiates `DeepfakeDetectorModel` with PyTorch EfficientNet-B4 backbone.
2. Formats model metadata and state dictionary.
3. Exports checkpoint to `data/models/veritas_detector.pt`.
4. Executes a test forward pass to verify computational integrity.

---

## 4. Fine-Tuning on Custom Deepfake Datasets

If fine-tuning on FaceForensics++ or Celeb-DF v2:
1. Ensure dataset is downloaded using `python scripts/download_datasets.py`.
2. Map labels (`0` for real, `1` for manipulated).
3. Use Cross-Entropy Loss with AdamW optimizer ($\text{lr} = 10^{-4}$, weight decay $= 10^{-2}$).
4. Save the resulting PyTorch model state dict to `data/models/veritas_detector.pt`.
