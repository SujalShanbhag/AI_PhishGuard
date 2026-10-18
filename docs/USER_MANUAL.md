# VERITAS AI — Forensic Analyst User Manual

## 1. Quick Start

1. Start the VERITAS AI server:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
2. Open your browser and navigate to: `http://localhost:8000`
3. Log in with the pre-configured forensic analyst account:
   - **Email:** `analyst@veritas.ai`
   - **Password:** `VeritasAdmin2026!`

---

## 2. Media Scanner Workflow

1. Navigate to **Media Scanner** from the sidebar.
2. Drag and drop any image (JPG, PNG, WEBP) or video (MP4, MOV, AVI) into the dropzone.
3. The platform validates the file's binary header magic bytes, calculates its SHA-256 bitstream hash, and initiates PyTorch inference.
4. For images, results display almost immediately. For video files, a live progress indicator tracks frame decoding, face localization, and per-frame inference.
5. Review the **Forensic Assessment Badge**:
   - `POTENTIALLY SUSPICIOUS` (Red): High statistical indicators of manipulation.
   - `NO STRONG EVIDENCE` (Green): No detectable deepfake signatures within evaluated model scope.
   - `INCONCLUSIVE` (Amber): Ambiguous confidence margin or degraded quality.
   - `SETUP REQUIRED` (Purple): Model weights missing; no artificial predictions fabricated.

---

## 3. Evidence Explorer & Visual Saliency

1. From the Media Scanner results box, click **Open in Evidence Explorer**.
2. Inspect the **Primary Face Crop** side-by-side with the **Grad-CAM Saliency Overlay**.
3. For video inputs, scrub across the **Temporal Video Frame Timeline** at the bottom to view frame-by-frame scores and inspect flagged timestamps.
4. Review the explainability disclaimer: highlighted regions represent features influencing the model's prediction, not legally definitive proof.

---

## 4. Privacy-Preserving Likeness Protection

1. Navigate to **Identity Protection**.
2. Check the affirmative consent agreement and upload a clear frontal portrait of yourself.
3. Once registered, select any past media scan from the dropdown.
4. Adjust the similarity threshold slider (default: $75\%$) and click **Evaluate Likeness Correlation**.
5. The system performs cosine similarity comparison between the reference embedding and the target media's primary face.
6. To delete your reference data, click **Delete Profile**.

---

## 5. Generating Official Forensic Reports

1. Click **Forensic Reports** in the sidebar or click **Generate Official PDF Report** directly from any completed scan.
2. The platform uses ReportLab to compile a formal forensic PDF including:
   - System branding & unique case ID.
   - Cryptographic SHA-256 bitstream hash.
   - Executive assessment & confidence margin.
   - Embedded face crops and Grad-CAM saliency heatmaps.
   - Frame timeline tables (for video).
   - Forensic disclaimers and recommended verification steps.
3. Download or save the PDF for case documentation.
