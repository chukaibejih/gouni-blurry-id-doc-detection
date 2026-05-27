"""
BLUR DETECTION EVALUATION SCRIPT
==================================
This script evaluates your blur detection system against a labelled dataset
and produces accuracy, precision, recall, F1-score, FAR, processing time,
confusion matrix, and grade distribution — ready to paste into Chapter 4.

FOLDER STRUCTURE REQUIRED:
---------------------------
evaluation_dataset/
    good/           ← sharp, fully readable images (ground truth: usable)
    mild/           ← slight softening (ground truth: usable)
    moderate/       ← noticeable blur (ground truth: unusable)
    severe/         ← heavy blur (ground truth: unusable)

HOW TO RUN:
-----------
1. Create the folder structure above
2. Put your images in the correct folders
3. Run: python evaluate.py
4. Results are printed to terminal AND saved to evaluation_results.txt

GENERATING SYNTHETIC BLUR (optional):
--------------------------------------
Run: python evaluate.py --generate --source path/to/clear/images
This will create blurred variants automatically in the correct folders.
"""

import cv2
import numpy as np
from PIL import Image
import io
import os
import time
import argparse
from pathlib import Path
from datetime import datetime

# ── Configuration ─────────────────────────────────────────────────────────────
MAX_LAPLACIAN          = 500.0   # calibrated from real testing
MAX_TENENGRAD          = 80.0    # calibrated from real testing
THRESHOLD              = 50.0    # default acceptance threshold
MAX_PROCESSING_WIDTH   = 640
MAX_PROCESSING_HEIGHT  = 480

DATASET_DIR    = "evaluation_dataset"
RESULTS_FILE   = "evaluation_results.txt"

GRADE_RANGES = [
    (75.0, 100.0, "Good"),
    (50.0,  74.99, "Mild"),
    (25.0,  49.99, "Moderate"),
    (0.0,   24.99, "Severe"),
]

# Ground truth: Good and Mild = usable (accepted), Moderate and Severe = unusable (rejected)
USABLE_GRADES   = {"good", "mild"}
UNUSABLE_GRADES = {"moderate", "severe"}

SUPPORTED_FORMATS = {".jpg", ".jpeg", ".png"}

# ── Blur Detection Logic (matches your backend exactly) ──────────────────────

def preprocess(image_path: str) -> np.ndarray:
    """
    Matches main.py exactly:
    - PIL Image.open() → convert RGB → numpy array
    - cv2.cvtColor RGB2GRAY (not BGR2GRAY)
    - Aspect-ratio-preserving resize within MAX_PROCESSING_WIDTH x MAX_PROCESSING_HEIGHT
    - int(round()) on new dimensions
    - cv2.INTER_AREA interpolation
    """
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img_array = np.array(img)
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    h, w = gray.shape
    if w > MAX_PROCESSING_WIDTH or h > MAX_PROCESSING_HEIGHT:
        scale = min(MAX_PROCESSING_WIDTH / w, MAX_PROCESSING_HEIGHT / h)
        new_w = max(1, int(round(w * scale)))
        new_h = max(1, int(round(h * scale)))
        gray = cv2.resize(gray, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return gray

def compute_laplacian(gray: np.ndarray) -> float:
    lap = cv2.Laplacian(gray, cv2.CV_64F)
    return float(lap.var())

def compute_tenengrad(gray: np.ndarray) -> float:
    sx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    sy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    mag = np.sqrt(sx**2 + sy**2)
    return float(mag.mean())

def compute_composite(lap: float, ten: float) -> float:
    norm_lap = min(lap / MAX_LAPLACIAN, 1.0) * 100
    norm_ten = min(ten / MAX_TENENGRAD, 1.0) * 100
    return round((0.5 * norm_lap) + (0.5 * norm_ten), 2)

def assign_grade(score: float) -> str:
    for low, high, grade in GRADE_RANGES:
        if low <= score <= high:
            return grade
    return "Severe"

def analyse_image(image_path: str):
    """Run full blur detection pipeline on a single image."""
    start = time.time()
    gray  = preprocess(image_path)
    lap   = compute_laplacian(gray)
    ten   = compute_tenengrad(gray)
    score = compute_composite(lap, ten)
    grade = assign_grade(score)
    decision = "accepted" if score >= THRESHOLD else "rejected"
    elapsed_ms = (time.time() - start) * 1000
    return {
        "score": score,
        "grade": grade,
        "decision": decision,
        "laplacian": round(lap, 4),
        "tenengrad": round(ten, 4),
        "time_ms": round(elapsed_ms, 2)
    }

# ── Synthetic Blur Generation ─────────────────────────────────────────────────

def generate_synthetic_dataset(source_dir: str):
    """
    Takes clear images from source_dir and generates blurred variants.
    Saves them into the correct evaluation_dataset subfolders.
    """
    source_path = Path(source_dir)
    images = [f for f in source_path.iterdir()
              if f.suffix.lower() in SUPPORTED_FORMATS]

    if not images:
        print(f"No images found in {source_dir}")
        return

    configs = {
        "good":     None,           # original clear image
        "mild":     (5, 5, 1.5),    # slight blur
        "moderate": (15, 15, 4.0),  # moderate blur
        "severe":   (31, 31, 10.0), # heavy blur
    }

    for grade, blur_params in configs.items():
        out_dir = Path(DATASET_DIR) / grade
        out_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for img_path in images:
        img = cv2.imread(str(img_path))
        if img is None:
            continue
        stem = img_path.stem

        for grade, blur_params in configs.items():
            out_dir = Path(DATASET_DIR) / grade
            out_path = out_dir / f"{stem}_{grade}{img_path.suffix}"
            if blur_params is None:
                cv2.imwrite(str(out_path), img)
            else:
                kw, kh, sigma = blur_params
                blurred = cv2.GaussianBlur(img, (kw, kh), sigma)
                cv2.imwrite(str(out_path), blurred)
        count += 1

    print(f"\nGenerated synthetic dataset from {count} source images.")
    print(f"Output: {DATASET_DIR}/good, mild, moderate, severe\n")

# ── Evaluation ────────────────────────────────────────────────────────────────

def run_evaluation():
    dataset_path = Path(DATASET_DIR)

    if not dataset_path.exists():
        print(f"\nERROR: Dataset folder '{DATASET_DIR}' not found.")
        print("Create folders: evaluation_dataset/good, mild, moderate, severe")
        print("Or run: python evaluate.py --generate --source path/to/clear/images\n")
        return

    subfolders = ["good", "mild", "moderate", "severe"]
    all_results = []
    missing = []

    print("\n" + "="*60)
    print("  BLUR DETECTION SYSTEM — EVALUATION")
    print("="*60)
    print(f"  Threshold:       {THRESHOLD}/100")
    print(f"  MAX_LAPLACIAN:   {MAX_LAPLACIAN}")
    print(f"  MAX_TENENGRAD:   {MAX_TENENGRAD}")
    print(f"  Dataset folder:  {DATASET_DIR}/")
    print("="*60)

    for folder in subfolders:
        folder_path = dataset_path / folder
        if not folder_path.exists():
            missing.append(folder)
            continue

        images = [f for f in folder_path.iterdir()
                  if f.suffix.lower() in SUPPORTED_FORMATS]

        print(f"\n  Processing [{folder.upper()}] — {len(images)} images")

        for img_path in images:
            try:
                result = analyse_image(str(img_path))
                result["filename"]    = img_path.name
                result["true_folder"] = folder
                result["true_label"]  = "usable" if folder in USABLE_GRADES else "unusable"
                result["pred_label"]  = "usable" if result["decision"] == "accepted" else "unusable"
                all_results.append(result)
                status = "✓" if result["true_label"] == result["pred_label"] else "✗"
                print(f"    {status} {img_path.name[:40]:<40} Score: {result['score']:6.2f}  Grade: {result['grade']:<8}  {result['decision'].upper()}")
            except Exception as e:
                print(f"    ! Could not process {img_path.name}: {e}")

    if missing:
        print(f"\n  WARNING: Missing subfolders: {', '.join(missing)}")

    if not all_results:
        print("\n  No images were processed. Check your dataset folder structure.\n")
        return

    # ── Compute metrics ───────────────────────────────────────────────────────
    total      = len(all_results)
    tp = sum(1 for r in all_results if r["true_label"] == "usable"   and r["pred_label"] == "usable")
    tn = sum(1 for r in all_results if r["true_label"] == "unusable" and r["pred_label"] == "unusable")
    fp = sum(1 for r in all_results if r["true_label"] == "unusable" and r["pred_label"] == "usable")
    fn = sum(1 for r in all_results if r["true_label"] == "usable"   and r["pred_label"] == "unusable")

    correct   = tp + tn
    incorrect = fp + fn

    accuracy  = round((correct / total) * 100, 2) if total > 0 else 0
    precision = round((tp / (tp + fp)) * 100, 2) if (tp + fp) > 0 else 0
    recall    = round((tp / (tp + fn)) * 100, 2) if (tp + fn) > 0 else 0
    f1        = round((2 * precision * recall) / (precision + recall), 2) if (precision + recall) > 0 else 0
    far       = round((fp / (fp + tn)) * 100, 2) if (fp + tn) > 0 else 0
    avg_time  = round(sum(r["time_ms"] for r in all_results) / total, 2)

    # Grade distribution
    grade_counts = {"Good": 0, "Mild": 0, "Moderate": 0, "Severe": 0}
    grade_correct = {"Good": 0, "Mild": 0, "Moderate": 0, "Severe": 0}
    grade_truth = {"good": 0, "mild": 0, "moderate": 0, "severe": 0}

    for r in all_results:
        g = r["grade"]
        tf = r["true_folder"]
        if g in grade_counts:
            grade_counts[g] += 1
        if tf in grade_truth:
            grade_truth[tf] += 1
        # correct grade assignment: system grade matches true folder
        if g.lower() == tf:
            if g in grade_correct:
                grade_correct[g] += 1

    # ── Build report ──────────────────────────────────────────────────────────
    lines = []
    lines.append("")
    lines.append("=" * 60)
    lines.append("  EVALUATION RESULTS")
    lines.append(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 60)
    lines.append("")
    lines.append("  PERFORMANCE METRICS")
    lines.append("  " + "-"*40)
    lines.append(f"  Total Images Evaluated    : {total}")
    lines.append(f"  Correctly Classified      : {correct}")
    lines.append(f"  Incorrectly Classified    : {incorrect}")
    lines.append(f"  Accuracy                  : {accuracy}%")
    lines.append(f"  Precision                 : {precision}%")
    lines.append(f"  Recall                    : {recall}%")
    lines.append(f"  F1-Score                  : {f1}%")
    lines.append(f"  False Acceptance Rate     : {far}%")
    lines.append(f"  Avg Processing Time       : {avg_time} ms per image")
    lines.append("")
    lines.append("  CONFUSION MATRIX")
    lines.append("  " + "-"*40)
    lines.append(f"  {'':30} {'Predicted: Accepted':>20} {'Predicted: Rejected':>20}")
    lines.append(f"  {'Actual: Usable (Good/Mild)':30} {'TP = ' + str(tp):>20} {'FN = ' + str(fn):>20}")
    lines.append(f"  {'Actual: Unusable (Mod/Sev)':30} {'FP = ' + str(fp):>20} {'TN = ' + str(tn):>20}")
    lines.append("")
    lines.append("  GRADE DISTRIBUTION")
    lines.append("  " + "-"*40)
    lines.append(f"  {'Grade':<12} {'Ground Truth':>14} {'System Assigned':>16} {'Correct':>10}")
    for grade in ["Good", "Mild", "Moderate", "Severe"]:
        truth_count   = grade_truth[grade.lower()]
        system_count  = grade_counts[grade]
        correct_count = grade_correct[grade]
        lines.append(f"  {grade:<12} {truth_count:>14} {system_count:>16} {correct_count:>10}")
    lines.append("")
    lines.append("  INDIVIDUAL RESULTS")
    lines.append("  " + "-"*40)
    lines.append(f"  {'File':<40} {'True':>10} {'Score':>7} {'Grade':<10} {'Decision':<10} {'Match':>6}")
    for r in all_results:
        match = "YES" if r["true_label"] == r["pred_label"] else "NO"
        lines.append(
            f"  {r['filename'][:38]:<40} {r['true_folder']:>10} {r['score']:>7.2f} "
            f"{r['grade']:<10} {r['decision']:<10} {match:>6}"
        )
    lines.append("")
    lines.append("=" * 60)

    report = "\n".join(lines)

    # Print to terminal
    print(report)

    # Save to file
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\n  Results saved to: {RESULTS_FILE}\n")

    # ── CSV export ────────────────────────────────────────────────────────────
    csv_path = "evaluation_results.csv"
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("filename,true_folder,true_label,composite_score,laplacian,tenengrad,grade,decision,pred_label,correct,time_ms\n")
        for r in all_results:
            correct_flag = "YES" if r["true_label"] == r["pred_label"] else "NO"
            f.write(
                f"{r['filename']},{r['true_folder']},{r['true_label']},"
                f"{r['score']},{r['laplacian']},{r['tenengrad']},"
                f"{r['grade']},{r['decision']},{r['pred_label']},{correct_flag},{r['time_ms']}\n"
            )
    print(f"  CSV saved to: {csv_path}\n")

# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Blur Detection Evaluation Script")
    parser.add_argument("--generate", action="store_true",
                        help="Generate synthetic blurred dataset from clear source images")
    parser.add_argument("--source", type=str, default="",
                        help="Path to folder of clear source images (used with --generate)")
    parser.add_argument("--threshold", type=float, default=THRESHOLD,
                        help=f"Acceptance threshold (default: {THRESHOLD})")
    args = parser.parse_args()

    THRESHOLD = args.threshold

    if args.generate:
        if not args.source:
            print("\nERROR: --generate requires --source path/to/clear/images\n")
        else:
            generate_synthetic_dataset(args.source)

    run_evaluation()
