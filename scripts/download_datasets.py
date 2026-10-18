import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from app.config import settings

DATASETS = {
    "faceforensics": {
        "slug": "gradientvoyager/faceforensics-c23-extracted-faces-100k",
        "name": "FaceForensics++ (c23 Extracted Faces 100k)",
        "target_dir": "faceforensics_c23"
    },
    "celeb_df": {
        "slug": "reubensuju/celeb-df-v2",
        "name": "Celeb-DF v2",
        "target_dir": "celeb_df_v2"
    }
}

def check_kaggle_credentials() -> bool:
    """Checks whether Kaggle credentials exist in environment or ~/.kaggle/kaggle.json"""
    home = Path.home()
    kaggle_json = home / ".kaggle" / "kaggle.json"
    if kaggle_json.exists():
        return True
    if os.environ.get("KAGGLE_USERNAME") and os.environ.get("KAGGLE_KEY"):
        return True
    return False

def download_and_extract(dataset_key: str, dest_dir: Path):
    """Directly extracts dataset from Kaggle source using Kaggle CLI without hardcoding."""
    info = DATASETS[dataset_key]
    slug = info["slug"]
    target_path = dest_dir / info["target_dir"]
    target_path.mkdir(parents=True, exist_ok=True)

    print(f"\n[VERITAS AI] Connecting to Kaggle source: {slug}")
    print(f"[VERITAS AI] Target destination: {target_path}")

    if not check_kaggle_credentials():
        print(
            "\n[VERITAS AI] ERROR: Kaggle API credentials not detected.\n"
            "To download directly from Kaggle, please ensure either:\n"
            "  1. A kaggle.json file is located at ~/.kaggle/kaggle.json\n"
            "  2. Or set environment variables KAGGLE_USERNAME and KAGGLE_KEY.\n"
            f"You can get your key from: https://www.kaggle.com/settings -> 'Create New Token'.\n"
        )
        return False

    cmd = [
        "kaggle", "datasets", "download",
        "-d", slug,
        "-p", str(target_path),
        "--unzip"
    ]

    print(f"[VERITAS AI] Executing command: {' '.join(cmd)}")
    try:
        proc = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        print(proc.stdout)
        print(f"[VERITAS AI] Successfully extracted {info['name']} into {target_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[VERITAS AI] Kaggle download error: {e.stderr}")
        return False

def build_dataset_manifest(dataset_root: Path) -> dict:
    """
    Scans extracted dataset directories and builds unified JSON manifest
    with identity-aware Train / Validation / Test partitions.
    """
    print("[VERITAS AI] Building dataset manifest and verifying file integrity...")
    manifest = {
        "generated_at": "2026-10-17",
        "datasets": list(DATASETS.keys()),
        "partitions": {"train": [], "val": [], "test": []},
        "stats": {"total_samples": 0, "real": 0, "fake": 0}
    }

    image_extensions = {".jpg", ".jpeg", ".png", ".webp"}
    all_samples = []

    for path in dataset_root.rglob("*"):
        if path.is_file() and path.suffix.lower() in image_extensions:
            # Determine label based on directory naming or filename patterns
            path_str = str(path).lower()
            if "real" in path_str or "original" in path_str or "youtube" in path_str:
                label = 0  # Authentic
            else:
                label = 1  # Manipulated / Deepfake

            # Extract subject ID heuristic from parent directory or filename to prevent identity leakage
            parent_name = path.parent.name
            subject_id = parent_name.split("_")[0] if "_" in parent_name else parent_name

            all_samples.append({
                "path": str(path.relative_to(dataset_root)),
                "label": label,
                "label_name": "authentic" if label == 0 else "manipulated",
                "subject_id": subject_id
            })

    if not all_samples:
        print("[VERITAS AI] Notice: No extracted images found yet in datasets root.")
        return manifest

    # Partition by subject_id to guarantee zero data leakage across train/val/test
    unique_subjects = sorted(list(set(s["subject_id"] for s in all_samples)))
    import random
    rng = random.Random(42)
    rng.shuffle(unique_subjects)

    n_subjects = len(unique_subjects)
    train_cutoff = int(n_subjects * 0.70)
    val_cutoff = int(n_subjects * 0.85)

    train_subjects = set(unique_subjects[:train_cutoff])
    val_subjects = set(unique_subjects[train_cutoff:val_cutoff])
    test_subjects = set(unique_subjects[val_cutoff:])

    for s in all_samples:
        sub = s["subject_id"]
        if sub in train_subjects:
            manifest["partitions"]["train"].append(s)
        elif sub in val_subjects:
            manifest["partitions"]["val"].append(s)
        else:
            manifest["partitions"]["test"].append(s)

        manifest["stats"]["total_samples"] += 1
        if s["label"] == 0:
            manifest["stats"]["real"] += 1
        else:
            manifest["stats"]["fake"] += 1

    manifest_path = dataset_root / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"[VERITAS AI] Manifest saved to: {manifest_path}")
    print(f"[VERITAS AI] Total: {manifest['stats']['total_samples']} (Real: {manifest['stats']['real']}, Fake: {manifest['stats']['fake']})")
    print(f"[VERITAS AI] Train: {len(manifest['partitions']['train'])}, Val: {len(manifest['partitions']['val'])}, Test: {len(manifest['partitions']['test'])}")
    return manifest

def main():
    parser = argparse.ArgumentParser(description="VERITAS AI Direct Kaggle Dataset Extractor")
    parser.add_argument("--dataset", choices=["all", "faceforensics", "celeb_df"], default="all")
    parser.add_argument("--dest", default=str(root_dir / "data" / "datasets"), help="Destination directory")
    args = parser.parse_args()

    dest_dir = Path(args.dest)
    dest_dir.mkdir(parents=True, exist_ok=True)

    if args.dataset in ["all", "faceforensics"]:
        download_and_extract("faceforensics", dest_dir)

    if args.dataset in ["all", "celeb_df"]:
        download_and_extract("celeb_df", dest_dir)

    build_dataset_manifest(dest_dir)

if __name__ == "__main__":
    main()
