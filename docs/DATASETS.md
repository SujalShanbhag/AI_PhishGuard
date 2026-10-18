# VERITAS AI — Dataset Management & Kaggle Direct Integration

## 1. Supported Forensics Datasets

VERITAS AI directly integrates with the two premier research benchmarks:

1. **FaceForensics++ (c23 Extracted Faces 100k):**
   - Source: `gradientvoyager/faceforensics-c23-extracted-faces-100k`
   - URL: [https://www.kaggle.com/datasets/gradientvoyager/faceforensics-c23-extracted-faces-100k](https://www.kaggle.com/datasets/gradientvoyager/faceforensics-c23-extracted-faces-100k)
   - Content: High-quality extracted face crops covering Deepfakes, Face2Face, FaceSwap, and NeuralTextures.

2. **Celeb-DF v2:**
   - Source: `reubensuju/celeb-df-v2`
   - URL: [https://www.kaggle.com/datasets/reubensuju/celeb-df-v2](https://www.kaggle.com/datasets/reubensuju/celeb-df-v2)
   - Content: Deepfake benchmark generated with improved synthesis algorithms reducing boundary artifacts.

---

## 2. Direct Kaggle Extraction (No Hardcoded Directories)

The application provides a dedicated dataset pipeline script `scripts/download_datasets.py` that directly communicates with the Kaggle CLI / API without hardcoding local directories.

### Setup Kaggle API Credentials:
Either:
1. Place `kaggle.json` in your home folder:
   - Windows: `C:\Users\<username>\.kaggle\kaggle.json`
   - Linux/Mac: `~/.kaggle/kaggle.json`
2. Or export environment variables:
   ```bash
   set KAGGLE_USERNAME=your_kaggle_username
   set KAGGLE_KEY=your_kaggle_api_key
   ```

### Execution:
```bash
# Download and extract all datasets
python scripts/download_datasets.py --dataset all

# Download FaceForensics++ only
python scripts/download_datasets.py --dataset faceforensics

# Download Celeb-DF v2 only
python scripts/download_datasets.py --dataset celeb_df
```

---

## 3. Data Leakage Prevention (Identity-Aware Splits)

To guarantee that evaluation metrics accurately reflect generalization rather than memorization of celebrity facial identities, `scripts/download_datasets.py` implements identity-level clustering:
- Facial images from subject $S_k$ are assigned strictly to **either** Train ($70\%$), Validation ($15\%$), or Test ($15\%$).
- Derived frames or alternate clips of the same subject **never** cross partition boundaries.
- Manifest is exported to `data/datasets/manifest.json`.

---

## 4. Empirical Evaluation Benchmark

To compute empirical metrics on the test partition:

```bash
python scripts/evaluate_model.py --manifest data/datasets/manifest.json --samples 500
```

Calculates:
- **Accuracy**
- **Precision & Recall**
- **F1-Score**
- **ROC-AUC**
- **Confusion Matrix** (TP, FP, TN, FN)
- **False Positive Rate (FPR)** and **False Negative Rate (FNR)**
- **Inference Latency** (ms per sample)
