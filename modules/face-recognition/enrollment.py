"""
enrollment.py - Build the employee embedding store.

    data/employees/<EMP_ID>/*.jpg -> detect face -> ArcFace embedding
        -> representative embedding per employee -> embeddings/employee_embeddings.npz

Usage:
    python enrollment.py
    python enrollment.py --employees-dir path/to/employees --output path/to/store.npz
    python enrollment.py --policy skip        # skip photos containing more than one face
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np

import config
from recognizer import create_face_analyzer


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def _normalize(v: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(v)
    if norm == 0:
        raise ValueError("zero-length embedding")
    return (v / norm).astype(np.float32)


def _face_area(face) -> float:
    x1, y1, x2, y2 = face.bbox
    return max(0.0, float(x2 - x1)) * max(0.0, float(y2 - y1))


def _is_usable(face) -> bool:
    x1, y1, x2, y2 = face.bbox
    return (float(face.det_score) >= config.MIN_DET_SCORE
            and min(x2 - x1, y2 - y1) >= config.MIN_FACE_SIZE)


def select_face(faces, policy: str) -> Tuple[Optional[object], str]:
    """
    Choose the face to enroll from one photo.
    Returns (face or None, note). A note with a face means "used, but be aware";
    a note without a face is the reason the photo was skipped.
    """
    if not faces:
        return None, "no face detected"

    usable = [f for f in faces if _is_usable(f)]
    if not usable:
        return None, "face found but too small or low detector confidence"
    if len(usable) == 1:
        return usable[0], ""

    usable.sort(key=_face_area, reverse=True)
    n = len(usable)
    if policy == "skip":
        return None, f"{n} faces detected (policy=skip)"

    ratio = _face_area(usable[1]) / _face_area(usable[0])
    if ratio > config.MULTI_FACE_AMBIGUITY_RATIO:
        return None, f"{n} faces of similar size - ambiguous"
    return usable[0], f"{n} faces detected - used the largest"


def list_images(folder: Path) -> List[Path]:
    return sorted(p for p in folder.iterdir()
                  if p.is_file() and p.suffix.lower() in config.IMAGE_EXTENSIONS)


def reject_outliers(embeddings: List[np.ndarray]) -> List[bool]:
    """
    Leave-one-out consistency check: an embedding is kept if it is similar enough to the
    mean of the OTHER photos. Catches a wrong-person photo dropped into a folder.
    """
    n = len(embeddings)
    if n < config.OUTLIER_MIN_PHOTOS:
        return [True] * n
    E = np.stack(embeddings)
    total = E.sum(axis=0)
    keep = []
    for e in E:
        others = total - e
        norm = np.linalg.norm(others)
        keep.append(bool(norm > 0 and float(e @ (others / norm)) >= config.OUTLIER_MIN_SIMILARITY))
    return keep


# --------------------------------------------------------------------------
# Enrollment
# --------------------------------------------------------------------------
def enroll_employee(app, person_id: str, folder: Path, policy: str) -> dict:
    name = config.EMPLOYEE_NAMES.get(person_id)
    issues: List[str] = []
    if name is None:
        name = person_id
        issues.append(f"'{person_id}' is not in config.EMPLOYEE_NAMES - using the ID as the name")

    images = list_images(folder)
    embeddings: List[np.ndarray] = []
    sources: List[str] = []

    for path in images:
        img = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if img is None:
            issues.append(f"{path.name}: unreadable / corrupt image, skipped")
            continue
        face, note = select_face(app.get(img), policy)
        if face is None:
            issues.append(f"{path.name}: {note}, skipped")
            continue
        if note:
            issues.append(f"{path.name}: {note}")
        embeddings.append(_normalize(face.normed_embedding))
        sources.append(path.name)

    # Drop inconsistent photos, then build the representative embedding.
    if embeddings:
        keep = reject_outliers(embeddings)
        for src, k in zip(sources, keep):
            if not k:
                issues.append(f"{src}: does not match the employee's other photos, excluded")
        embeddings = [e for e, k in zip(embeddings, keep) if k]

    representative = _normalize(np.mean(np.stack(embeddings), axis=0)) if embeddings else None

    return {
        "person_id": person_id,
        "name": name,
        "images_found": len(images),
        "images_used": len(embeddings),
        "issues": issues,
        "embedding": representative,
    }


def enroll_all(employees_dir: Path, output_file: Path, policy: str, app=None) -> List[dict]:
    if not employees_dir.is_dir():
        raise FileNotFoundError(f"Employees directory not found: {employees_dir}")

    folders = sorted(p for p in employees_dir.iterdir() if p.is_dir() and not p.name.startswith("."))
    if not folders:
        raise FileNotFoundError(f"No employee folders found in {employees_dir}")

    if app is None:
        print(f"Loading InsightFace model '{config.MODEL_NAME}' ...")
        app = create_face_analyzer()

    results = []
    for folder in folders:
        print(f"Enrolling {folder.name} ...")
        results.append(enroll_employee(app, folder.name, folder, policy))

    enrolled = [r for r in results if r["embedding"] is not None]
    if enrolled:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            output_file,
            person_ids=np.array([r["person_id"] for r in enrolled]),
            names=np.array([r["name"] for r in enrolled]),
            embeddings=np.stack([r["embedding"] for r in enrolled]).astype(np.float32),
            photo_counts=np.array([r["images_used"] for r in enrolled], dtype=np.int32),
            model_name=np.array(config.MODEL_NAME),
        )

    print_summary(results, output_file if enrolled else None)
    warn_similar_employees(enrolled)
    return results


def warn_similar_employees(enrolled: List[dict]) -> None:
    for i in range(len(enrolled)):
        for j in range(i + 1, len(enrolled)):
            sim = float(enrolled[i]["embedding"] @ enrolled[j]["embedding"])
            if sim >= config.DUPLICATE_WARN_SIMILARITY:
                print(f"WARNING: {enrolled[i]['person_id']} and {enrolled[j]['person_id']} have very similar "
                      f"embeddings (similarity {sim:.2f}). Check for a mislabeled folder or duplicate photos.")


def print_summary(results: List[dict], output_file: Optional[Path]) -> None:
    line = "=" * 74
    print(f"\n{line}\nENROLLMENT SUMMARY\n{line}")
    print(f"{'Employee ID':<13}{'Name':<20}{'Photos':>7}{'Used':>6}   Status")
    print("-" * 74)
    for r in results:
        status = "ENROLLED" if r["embedding"] is not None else "FAILED"
        print(f"{r['person_id']:<13}{r['name']:<20}{r['images_found']:>7}{r['images_used']:>6}   {status}")

    for r in results:
        if r["issues"]:
            print(f"\n[{r['person_id']}] notes:")
            for msg in r["issues"]:
                print(f"  - {msg}")
        if r["embedding"] is None:
            print(f"  ! {r['person_id']} was NOT enrolled: no usable face in any photo.")

    ok = sum(r["embedding"] is not None for r in results)
    print(f"\nEnrolled {ok} of {len(results)} employees; "
          f"{sum(r['images_used'] for r in results)} of {sum(r['images_found'] for r in results)} photos used.")
    print(f"Saved to: {output_file}" if output_file else "Nothing saved (no employee could be enrolled).")
    print(line)


def main() -> int:
    parser = argparse.ArgumentParser(description="Enroll employees from photos into a local embedding store.")
    parser.add_argument("--employees-dir", type=Path, default=config.EMPLOYEES_DIR)
    parser.add_argument("--output", type=Path, default=config.EMBEDDINGS_FILE)
    parser.add_argument("--policy", choices=["largest", "skip"], default=config.MULTI_FACE_POLICY,
                        help="what to do with photos containing several faces")
    args = parser.parse_args()

    try:
        results = enroll_all(args.employees_dir, args.output, args.policy)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}")
        return 1
    return 0 if any(r["embedding"] is not None for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
