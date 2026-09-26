"""
config.py - Central configuration for the face-recognition module.

Every tunable value lives here so enrollment.py, recognizer.py and demo.py
stay free of magic numbers.
"""

from pathlib import Path

# --------------------------------------------------------------------------
# Paths (all relative to this module, so the folder can be dropped anywhere)
# --------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
EMPLOYEES_DIR = BASE_DIR / "data" / "employees"
EMBEDDINGS_DIR = BASE_DIR / "embeddings"
EMBEDDINGS_FILE = EMBEDDINGS_DIR / "employee_embeddings.npz"

# --------------------------------------------------------------------------
# Employee ID -> display name.
# The folder name under data/employees/ is the employee ID.
# --------------------------------------------------------------------------
EMPLOYEE_NAMES = {
    "EMP001": "R. Meena",
    "EMP002": "S. Kumar",
    "EMP003": "P. Priya",
}

# --------------------------------------------------------------------------
# InsightFace / ONNX Runtime
# --------------------------------------------------------------------------
MODEL_NAME = "buffalo_l"                 # pretrained pack: RetinaFace/SCRFD detector + ArcFace (w600k_r50)
MODEL_ROOT = "~/.insightface"            # models auto-download here on first run
ONNX_PROVIDERS = ["CPUExecutionProvider"]
# For an NVIDIA GPU (requires `pip install onnxruntime-gpu`), use:
#   ONNX_PROVIDERS = ["CUDAExecutionProvider", "CPUExecutionProvider"]
#   CTX_ID = 0
CTX_ID = -1                              # -1 = CPU, 0 = first GPU
DET_SIZE = (640, 640)                    # detector input size; larger finds smaller faces but is slower

# --------------------------------------------------------------------------
# Face quality filters (used by BOTH enrollment and recognition)
# --------------------------------------------------------------------------
MIN_DET_SCORE = 0.50                     # ignore detections below this detector confidence
MIN_FACE_SIZE = 40                       # ignore faces whose shorter bbox side is below this many pixels

# --------------------------------------------------------------------------
# Enrollment behaviour
# --------------------------------------------------------------------------
MULTI_FACE_POLICY = "largest"            # "largest": use the dominant face | "skip": skip such photos
MULTI_FACE_AMBIGUITY_RATIO = 0.70        # "largest" policy: if 2nd-largest face area / largest area exceeds
                                         # this, the photo is ambiguous and is skipped
OUTLIER_MIN_PHOTOS = 3                   # outlier check only runs with at least this many usable photos
OUTLIER_MIN_SIMILARITY = 0.30            # photo dropped if its similarity to the OTHER photos' mean is below this
DUPLICATE_WARN_SIMILARITY = 0.50         # warn if two different employees' representatives are this similar

# --------------------------------------------------------------------------
# Recognition behaviour
# --------------------------------------------------------------------------
SIMILARITY_THRESHOLD = 0.40              # cosine similarity; best match below this => UNKNOWN. Tune on your data.
CONFIDENCE_DECIMALS = 2                  # rounding of the reported confidence
UNKNOWN_NAME = "UNKNOWN"
STATUS_RECOGNIZED = "RECOGNIZED"
STATUS_UNKNOWN = "UNKNOWN"

# --------------------------------------------------------------------------
# Input images / drawing
# --------------------------------------------------------------------------
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
COLOR_RECOGNIZED = (0, 200, 0)           # BGR (green)
COLOR_UNKNOWN = (0, 0, 255)              # BGR (red)
