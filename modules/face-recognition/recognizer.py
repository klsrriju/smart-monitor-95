"""
recognizer.py - Face recognition engine.

    image -> detect ALL faces -> ArcFace embedding per face
          -> cosine similarity vs. registered employees
          -> RECOGNIZED / UNKNOWN

Public API
----------
    rec = FaceRecognizer()                       # loads embeddings/employee_embeddings.npz
    results = rec.recognize("photo.jpg")         # list of dicts (exact 4-key schema)
    detailed = rec.recognize_detailed("photo.jpg")   # same + bbox / det_score
    annotated = rec.draw_results(image, detailed)    # image with boxes + labels
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Union

import cv2
import numpy as np

import config

ImageInput = Union[str, os.PathLike, np.ndarray]


# --------------------------------------------------------------------------
# Shared model loader (also used by enrollment.py)
# --------------------------------------------------------------------------
def create_face_analyzer(model_name: str = config.MODEL_NAME,
                         det_size=config.DET_SIZE):
    """Create an InsightFace analyzer (detector + ArcFace recognizer only)."""
    from insightface.app import FaceAnalysis  # imported lazily: keeps `import recognizer` cheap

    app = FaceAnalysis(
        name=model_name,
        root=os.path.expanduser(config.MODEL_ROOT),
        allowed_modules=["detection", "recognition"],  # skip landmark/gender-age models we don't need
        providers=config.ONNX_PROVIDERS,
    )
    app.prepare(ctx_id=config.CTX_ID, det_size=det_size)
    return app


def load_image(image: ImageInput) -> np.ndarray:
    """Return a BGR uint8 image from a file path or a NumPy array."""
    if isinstance(image, (str, os.PathLike)):
        path = Path(image)
        if not path.is_file():
            raise FileNotFoundError(f"Image not found: {path}")
        img = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError(f"Could not decode image: {path}")
        return img

    if isinstance(image, np.ndarray):
        if image.ndim == 2:
            return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        if image.ndim == 3 and image.shape[2] == 4:
            return cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
        if image.ndim == 3 and image.shape[2] == 3:
            return image
        raise ValueError(f"Unsupported array shape: {image.shape}")

    raise TypeError("image must be a file path or a NumPy array (BGR, as loaded by cv2.imread)")


class FaceRecognizer:
    """Loads stored employee embeddings and identifies faces in images."""

    def __init__(self,
                 embeddings_file: Union[str, os.PathLike, None] = None,
                 threshold: float | None = None,
                 analyzer=None):
        self.threshold = config.SIMILARITY_THRESHOLD if threshold is None else float(threshold)
        if not 0.0 < self.threshold <= 1.0:
            raise ValueError("threshold must be in the range (0, 1]")

        self.embeddings_file = Path(embeddings_file) if embeddings_file else config.EMBEDDINGS_FILE
        self.person_ids: List[str] = []
        self.names: List[str] = []
        self.embeddings = np.empty((0, 512), dtype=np.float32)
        self._load_embeddings()

        self.analyzer = analyzer if analyzer is not None else create_face_analyzer()

    # ------------------------------------------------------------------
    def _load_embeddings(self) -> None:
        if not self.embeddings_file.is_file():
            raise FileNotFoundError(
                f"Embeddings file not found: {self.embeddings_file}\n"
                f"Run `python enrollment.py` first to enroll employees."
            )
        data = np.load(self.embeddings_file, allow_pickle=False)
        ids = [str(x) for x in data["person_ids"]]
        names = [str(x) for x in data["names"]]
        emb = np.asarray(data["embeddings"], dtype=np.float32)

        if len(ids) == 0 or emb.ndim != 2 or emb.shape[0] != len(ids) or len(names) != len(ids):
            raise ValueError(f"Embeddings file is empty or corrupt: {self.embeddings_file}")

        # Re-normalise so a dot product is exactly cosine similarity.
        norms = np.linalg.norm(emb, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        self.person_ids, self.names, self.embeddings = ids, names, emb / norms

    def reload(self) -> None:
        """Re-read the embeddings file (e.g. after re-running enrollment)."""
        self._load_embeddings()

    # ------------------------------------------------------------------
    def _match(self, embedding: np.ndarray) -> tuple[int, float]:
        """Return (index of best employee, cosine similarity)."""
        emb = np.asarray(embedding, dtype=np.float32)
        emb = emb / (np.linalg.norm(emb) or 1.0)
        sims = self.embeddings @ emb
        best = int(np.argmax(sims))
        return best, float(sims[best])

    def recognize_detailed(self, image: ImageInput) -> List[dict]:
        """
        Detect and identify every face. Each result contains the 4 required keys
        (person_id, name, confidence, status) plus `bbox` [x1, y1, x2, y2] and `det_score`.
        Results are ordered left to right.
        """
        img = load_image(image)
        faces = self.analyzer.get(img)

        results = []
        for face in faces:
            x1, y1, x2, y2 = [float(v) for v in face.bbox]
            if float(face.det_score) < config.MIN_DET_SCORE or min(x2 - x1, y2 - y1) < config.MIN_FACE_SIZE:
                continue  # too small / unreliable to identify

            idx, sim = self._match(face.normed_embedding)
            recognized = sim >= self.threshold
            results.append({
                "person_id": self.person_ids[idx] if recognized else None,
                "name": self.names[idx] if recognized else config.UNKNOWN_NAME,
                "confidence": round(max(0.0, min(1.0, sim)), config.CONFIDENCE_DECIMALS),
                "status": config.STATUS_RECOGNIZED if recognized else config.STATUS_UNKNOWN,
                "bbox": [int(round(x1)), int(round(y1)), int(round(x2)), int(round(y2))],
                "det_score": round(float(face.det_score), 3),
            })

        results.sort(key=lambda r: r["bbox"][0])
        return results

    def recognize(self, image: ImageInput) -> List[dict]:
        """One dict per detected face with EXACTLY: person_id, name, confidence, status."""
        keys = ("person_id", "name", "confidence", "status")
        return [{k: r[k] for k in keys} for r in self.recognize_detailed(image)]

    # ------------------------------------------------------------------
    def draw_results(self, image: ImageInput, detailed_results: List[dict]) -> np.ndarray:
        """Return a copy of the image with a box and label drawn for each face."""
        canvas = load_image(image).copy()
        h, w = canvas.shape[:2]
        scale = max(0.5, min(h, w) / 900.0)
        thickness = max(1, int(round(scale * 2)))

        for r in detailed_results:
            x1, y1, x2, y2 = r["bbox"]
            ok = r["status"] == config.STATUS_RECOGNIZED
            color = config.COLOR_RECOGNIZED if ok else config.COLOR_UNKNOWN
            label = (f'{r["name"]} ({r["person_id"]}) {r["confidence"]:.2f}' if ok
                     else f'{config.UNKNOWN_NAME} {r["confidence"]:.2f}')

            cv2.rectangle(canvas, (x1, y1), (x2, y2), color, thickness)
            (tw, th), base = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, scale * 0.6, thickness)
            top = max(0, y1 - th - base - 4)
            cv2.rectangle(canvas, (x1, top), (x1 + tw + 6, top + th + base + 4), color, -1)
            cv2.putText(canvas, label, (x1 + 3, top + th + 1),
                        cv2.FONT_HERSHEY_SIMPLEX, scale * 0.6, (255, 255, 255), thickness, cv2.LINE_AA)
        return canvas

    def recognize_and_draw(self, image: ImageInput):
        """Convenience: returns (results_with_bbox, annotated_image)."""
        img = load_image(image)
        detailed = self.recognize_detailed(img)
        return detailed, self.draw_results(img, detailed)
