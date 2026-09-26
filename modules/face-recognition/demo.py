"""
demo.py - Try the recognizer on an image.

Usage:
    python demo.py --image path/to/photo.jpg
    python demo.py --image group.jpg --threshold 0.45 --show
    python demo.py                      # smoke test: uses the first enrolled photo it finds

Prints one JSON object per detected face and saves an annotated image
(default: <image name>_result.jpg next to the input).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2

import config
from recognizer import FaceRecognizer


def find_sample_image() -> Path | None:
    for folder in sorted(p for p in config.EMPLOYEES_DIR.glob("*") if p.is_dir()):
        for f in sorted(folder.iterdir()):
            if f.is_file() and f.suffix.lower() in config.IMAGE_EXTENSIONS:
                return f
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Face recognition demo")
    parser.add_argument("--image", type=Path, help="image to analyse")
    parser.add_argument("--threshold", type=float, default=None,
                        help=f"similarity threshold (default {config.SIMILARITY_THRESHOLD})")
    parser.add_argument("--output", type=Path, help="where to save the annotated image")
    parser.add_argument("--no-save", action="store_true", help="do not save the annotated image")
    parser.add_argument("--show", action="store_true", help="display the annotated image in a window")
    args = parser.parse_args()

    image_path = args.image or find_sample_image()
    if image_path is None:
        print("No --image given and no photos found in data/employees/. Add photos and run enrollment.py first.")
        return 1
    if args.image is None:
        print(f"No --image given; using sample photo: {image_path}")

    try:
        recognizer = FaceRecognizer(threshold=args.threshold)
        detailed, annotated = recognizer.recognize_and_draw(image_path)
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1

    results = [{k: r[k] for k in ("person_id", "name", "confidence", "status")} for r in detailed]
    print(f"Faces detected: {len(results)}  (threshold = {recognizer.threshold})")
    print(json.dumps(results, indent=2))

    if not args.no_save and results:
        out = args.output or image_path.with_name(f"{image_path.stem}_result.jpg")
        cv2.imwrite(str(out), annotated)
        print(f"Annotated image saved to: {out}")

    if args.show:
        cv2.imshow("Face Recognition", annotated)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    sys.exit(main())
