# AI PhishGuard — Explainable Multimodal Deepfake Detection & Identity Protection

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![PyTorch](https://img.shields.io/badge/Deep%20Learning-PyTorch%202.x-EE4C2C.svg)](https://pytorch.org/)
[![OpenCV](https://img.shields.io/badge/Computer%20Vision-OpenCV-5C3EE8.svg)](https://opencv.org/)
[![Tests](https://img.shields.io/badge/Tests-32%20Passed%20(100%25)-success.svg)]()
[![Security](https://img.shields.io/badge/Security-bcrypt%20%7C%20JWT%20%7C%20RateLimit-blue.svg)]()

> **AI PhishGuard** is an advanced, production-oriented forensic intelligence platform designed for explainable, multimodal deepfake detection, audio-visual synchronization forensics, privacy-preserving likeness protection, and sensitive document privacy redaction.

---

## 🎯 Demonstration Highlights

AI PhishGuard prioritizes **functional depth** and **forensic integrity** over superficial mockups:

1. **Explainable Deepfake Detection (Grad-CAM):**  
   Hooks into convolutional feature layers to render visual saliency heatmaps showing spatial attribution (blend boundaries, eye/mouth anomalies) rather than opaque black-box predictions.
2. **Multimodal Evidence Combination:**  
   Cross-references visual neural detectors with acoustic spectral metrics and lip-sync kinetics, communicating uncertainty across Category A (*Suspicious*), Category B (*No Strong Evidence*), or Category C (*Inconclusive*).
3. **Sensitive Document Privacy Guard & Redaction:**  
   Universal format ingestion (.pdf, .docx, .xlsx, .eml, .msg, .txt, .csv, images) with calibrated risk scoring across 12 sensitive categories (Aadhaar, PAN, Passwords, Banking, Phone, Email, Medical, Confidential, Full Name, Blood Group, Gender, Income) and vector bitstream redaction.
4. **Synthetic Dataset Generator (All Formats):**  
   On-demand synthesis and export across 7 data formats (CSV, JSON, TXT, PDF, DOCX, XLSX, EML) with strictly populated fields: `name`, `phone no.`, `blood group`, `gender`, `aadhar no.` (Verhoeff checksum verified), and `income`.
5. **Valid Login & Registration Portal:**  
   Full-stack dual-mode authentication with secure bcrypt hashing, session cookies, role selection, client-side validation, and instant account onboarding.
6. **Privacy-First Likeness Protection:**  
   Enables users to register consented reference portraits stored in private, isolated vaults to investigate unauthorized digital impersonations without external internet scraping.

---

## 🏗️ System Architecture

```
VERITAS-AI/
├── app/
│   ├── main.py                     # FastAPI application & route registration
│   ├── config.py                   # Pydantic v2 settings & environment manager
│   ├── database.py                 # SQLAlchemy session & SQLite/Postgres engine
│   ├── api/                        # REST API endpoints (auth, analysis, identity, reports, evidence)
│   ├── models/                     # SQLAlchemy models & Pydantic v2 validation schemas
│   ├── services/                   # Business logic (image/video pipelines, fusion, PDF reports)
│   ├── ai/                         # PyTorch deepfake detector, face detector, Grad-CAM, audio forensics
│   ├── security/                   # bcrypt hashing, JWT authentication, magic-byte validation
│   └── workers/                    # Background thread pool executor for long-running video forensics
├── static/                         # Frontend SPA (Vanilla JS, CSS3 Cybersecurity Dark Theme, Chart.js)
├── tests/                          # 19 automated tests (auth, API, media validation, isolation)
├── scripts/                        # Database init, model weights export, direct Kaggle extractors
├── docs/                           # Architecture, Model Setup, Datasets, Privacy, API, User Manual
├── data/                           # Isolated data storage (uploads, identity vault, models, reports)
├── Dockerfile                      # Production container definition
└── compose.yaml                    # One-click Docker Compose deployment
```

---

## ⚡ Quickstart Guide

### 1. Prerequisites
- Python 3.10+ (Tested on Python 3.12)
- Dependencies installed via pip

### 2. Initialize Database & Model Weights
Run the initialization scripts to create the SQLite schema, set up the default analyst account, and initialize the baseline PyTorch neural model checkpoint:

```bash
python scripts/initialize_database.py
python scripts/initialize_models.py
```

### 3. Launch the Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
Open your browser at **`http://localhost:8000`** and log in with:
- **Email:** `analyst@phishguard.ai`
- **Password:** `PhishGuardAdmin2026!`

Interactive OpenAPI Documentation: **`http://localhost:8000/docs`**

---

## 🧪 Automated Test Suite

Run the full automated test suite covering authentication, file magic-byte validation, PyTorch inference, Grad-CAM generation, and cross-user authorization isolation:

```bash
pytest tests -v
```
*Current test status: 19 passed, 0 failed (100% pass rate).*

---

## 📊 Direct Kaggle Dataset Extraction

AI PhishGuard directly downloads and extracts research datasets without hardcoding local directories:

- **FaceForensics++ (c23 Extracted Faces 100k):** `gradientvoyager/faceforensics-c23-extracted-faces-100k`
- **Celeb-DF v2:** `reubensuju/celeb-df-v2`

### Run Dataset Extraction:
```bash
# Ensure Kaggle API credentials exist in ~/.kaggle/kaggle.json or env vars
python scripts/download_datasets.py --dataset all
```

This script extracts images, generates `data/datasets/manifest.json`, and applies **identity-level splitting** (70% train / 15% val / 15% test) to prevent cross-partition biometric identity leakage.

### Run Empirical Model Evaluation:
```bash
python scripts/evaluate_model.py --manifest data/datasets/manifest.json --samples 500
```
Calculates Accuracy, Precision, Recall, F1-Score, ROC-AUC, Confusion Matrix, False-Positive Rate, False-Negative Rate, and Inference Latency.

---

## 🛡️ Truth-in-AI Guarantee

- **Zero Fabricated Results:** If model weights are not loaded, the system explicitly reports `status: "SETUP_REQUIRED"` rather than generating random scores.
- **Explainability Transparency:** Grad-CAM saliency displays spatial attribution only; it does not claim to legally prove malicious intent.
- **Evidence Integrity:** SHA-256 cryptographic bitstream hashing distinguishes byte-level alterations from semantic scene manipulation.
- **Privacy Assurance:** Reference likeness images are stored in a private vault, never exposed over public endpoints, and can be purged on demand.

---

## 📄 License
This project is licensed under the Apache 2.0 / MIT License.
