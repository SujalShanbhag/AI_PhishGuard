import argparse
import json
import os
import sys
import time
from pathlib import Path
import cv2
import numpy as np
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from app.config import settings
from app.ai.deepfake_detector import deepfake_detector

def run_evaluation(manifest_path: str, max_samples: int = 500):
    eval_dir = Path(settings.EVALUATIONS_DIR)
    eval_dir.mkdir(parents=True, exist_ok=True)
    report_file = eval_dir / "latest_evaluation_report.json"

    print("=================================================================")
    print(" VERITAS AI — EMPIRICAL MODEL EVALUATION & FORENSIC BENCHMARK")
    print("=================================================================")

    if not deepfake_detector.is_loaded:
        print("[VERITAS AI] Model weights not loaded. Status: SETUP_REQUIRED.")
        print("[VERITAS AI] Cannot execute evaluation without model weights.")
        pending_report = {
            "status": "EVALUATION_PENDING",
            "reason": "Model weights not configured. Strictly adhering to no-fabrication policy.",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC")
        }
        with open(report_file, "w") as f:
            json.dump(pending_report, f, indent=2)
        return

    m_path = Path(manifest_path)
    if not m_path.exists():
        print(f"[VERITAS AI] Dataset manifest not found at: {m_path}")
        print("[VERITAS AI] Run 'python scripts/download_datasets.py' first to extract datasets.")
        return

    with open(m_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    test_samples = manifest.get("partitions", {}).get("test", [])
    if not test_samples:
        print("[VERITAS AI] Test partition contains 0 samples. Evaluation aborted.")
        return

    dataset_root = m_path.parent
    samples_to_eval = test_samples[:max_samples]

    print(f"[VERITAS AI] Evaluating {len(samples_to_eval)} test samples on {deepfake_detector.architecture}...")

    y_true = []
    y_scores = []
    latencies = []

    for idx, item in enumerate(samples_to_eval):
        img_full_path = dataset_root / item["path"]
        if not img_full_path.exists():
            continue

        img_bgr = cv2.imread(str(img_full_path))
        if img_bgr is None:
            continue

        t0 = time.time()
        pred = deepfake_detector.predict_frame(img_bgr)
        lat = (time.time() - t0) * 1000.0  # ms
        latencies.append(lat)

        if pred["status"] == "SUCCESS":
            y_true.append(item["label"])
            y_scores.append(pred["score"])

        if (idx + 1) % 50 == 0 or (idx + 1) == len(samples_to_eval):
            print(f" -> Processed {idx + 1}/{len(samples_to_eval)} samples (avg latency: {np.mean(latencies):.1f}ms/sample)")

    if len(y_true) < 10:
        print("[VERITAS AI] Insufficient test samples processed to calculate reliable forensic metrics.")
        return

    y_true = np.array(y_true)
    y_scores = np.array(y_scores)
    y_pred = (y_scores >= settings.SUSPICIOUS_THRESHOLD).astype(int)

    acc = float(accuracy_score(y_true, y_pred))
    prec = float(precision_score(y_true, y_pred, zero_division=0))
    rec = float(recall_score(y_true, y_pred, zero_division=0))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))

    try:
        auc = float(roc_auc_score(y_true, y_scores))
    except Exception:
        auc = 0.5

    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    fpr = float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0
    fnr = float(fn / (fn + tp)) if (fn + tp) > 0 else 0.0
    avg_lat = float(np.mean(latencies))

    eval_results = {
        "status": "COMPLETED",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "model_architecture": deepfake_detector.architecture,
        "device": str(deepfake_detector.device),
        "total_evaluated_samples": len(y_true),
        "threshold": settings.SUSPICIOUS_THRESHOLD,
        "metrics": {
            "accuracy": round(acc, 4),
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1_score": round(f1, 4),
            "roc_auc": round(auc, 4),
            "false_positive_rate": round(fpr, 4),
            "false_negative_rate": round(fnr, 4),
            "average_latency_ms": round(avg_lat, 2)
        },
        "confusion_matrix": {
            "true_negatives": int(tn),
            "false_positives": int(fp),
            "false_negatives": int(fn),
            "true_positives": int(tp)
        },
        "disclaimer": (
            "Empirical results obtained strictly on held-out test partition. "
            "Real-world forensic performance varies according to compression, lighting, and synthetic generator novelty."
        )
    }

    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(eval_results, f, indent=2)

    print("\n---------------- EVALUATION SUMMARY ----------------")
    print(f"Accuracy:  {acc * 100:.2f}%")
    print(f"Precision: {prec * 100:.2f}%")
    print(f"Recall:    {rec * 100:.2f}%")
    print(f"F1-Score:  {f1:.4f}")
    print(f"ROC-AUC:   {auc:.4f}")
    print(f"FPR:       {fpr * 100:.2f}% | FNR: {fnr * 100:.2f}%")
    print(f"Avg Latency: {avg_lat:.2f} ms/frame")
    print(f"Report saved to: {report_file}")
    print("----------------------------------------------------\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default=str(root_dir / "data" / "datasets" / "manifest.json"))
    parser.add_argument("--samples", type=int, default=500)
    args = parser.parse_args()
    run_evaluation(args.manifest, args.samples)
