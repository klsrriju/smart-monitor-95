# Face Recognition Module (SmartMonitor - Member 1)

Standalone Python module: employee photos -> ArcFace embeddings -> recognize every face in an image
as `RECOGNIZED` (employee ID + name + confidence) or `UNKNOWN`.

Uses a **pretrained** InsightFace `buffalo_l` pack (face detector + ArcFace recognition model) on
ONNX Runtime. Nothing is trained. No database, no dependency on any other SmartMonitor code.

```
face-recognition-module/
├── data/employees/EMP001|EMP002|EMP003/   # put 1.jpg, 2.jpg, 3.jpg ... here
├── embeddings/                            # employee_embeddings.npz is written here
├── enrollment.py                          # photos -> embeddings
├── recognizer.py                          # FaceRecognizer engine
├── config.py                              # paths, names, threshold, model settings
├── demo.py                                # try it on an image
├── requirements.txt
└── README.md
```

## 1. Install

Python 3.9 - 3.11 is recommended (best wheel support for InsightFace).

```bash
python -m venv venv
venv\Scripts\activate          # Windows   (Linux/macOS: source venv/bin/activate)
pip install -r requirements.txt
```

* The `buffalo_l` model (~280 MB) is downloaded automatically to `~/.insightface/models` on the
  **first run** - internet is needed once. To work offline, copy that folder to the target machine.
* Windows: if `pip install insightface` fails while building, install
  *Microsoft C++ Build Tools*, or use a prebuilt wheel matching your Python version.
* GPU (optional): install `onnxruntime-gpu` instead of `onnxruntime` and edit `ONNX_PROVIDERS` / `CTX_ID` in `config.py`.

## 2. Add employee photos

The **folder name is the employee ID**. Several photos per employee are supported and recommended
(3-5, varied angle and lighting, one clearly visible face each):

```
data/employees/EMP001/1.jpg  2.jpg  3.jpg
data/employees/EMP002/1.jpg  2.jpg  3.jpg
data/employees/EMP003/1.jpg  2.jpg  3.jpg
```

Names come from `EMPLOYEE_NAMES` in `config.py` (`EMP001 -> R. Meena`, `EMP002 -> S. Kumar`, `EMP003 -> P. Priya`).
Add a line there for every new employee folder.

## 3. Enroll

```bash
python enrollment.py
```

For each employee it detects the face in every photo, computes a 512-d ArcFace embedding, averages
them into one L2-normalised **representative embedding**, and saves everything to
`embeddings/employee_embeddings.npz`. A summary table is printed (photos found / used, skipped photos with reasons).

How problem photos are handled:

| Situation | Behaviour |
|---|---|
| No face detected / face too small / low detector score | Photo skipped, reason printed |
| Corrupt or unreadable file | Photo skipped, reason printed |
| Several faces, one clearly dominant (largest area) | Largest face used, warning printed |
| Several faces of similar size | Photo skipped as ambiguous (enrolling the wrong person is worse than skipping) |
| A photo that doesn't match the employee's other photos (needs >= 3 photos) | Excluded as an outlier, warning printed |
| Two employees end up with near-identical embeddings | Warning printed (mislabeled folder / duplicate photos) |
| Employee with no usable photo | Marked `FAILED`, not saved |
| Folder ID missing from `EMPLOYEE_NAMES` | Enrolled with the ID as the name, warning printed |

Re-run `python enrollment.py` whenever photos change; it rebuilds the file from scratch.

## 4. Recognize

```bash
python demo.py --image path/to/photo.jpg
python demo.py --image group.jpg --threshold 0.45 --show
```

Prints one entry per face and saves an annotated image (green = recognized, red = unknown) as `<name>_result.jpg`.

### Output format

```json
{ "person_id": "EMP001", "name": "R. Meena", "confidence": 0.87, "status": "RECOGNIZED" }
{ "person_id": null,     "name": "UNKNOWN",  "confidence": 0.31, "status": "UNKNOWN" }
```

`confidence` is the cosine similarity to the best-matching employee (clipped to 0-1). For `UNKNOWN`
it is the similarity to the closest employee, which was below the threshold.

## 5. Use from Python (for integration)

```python
from recognizer import FaceRecognizer

rec = FaceRecognizer()                    # loads the model + embeddings ONCE; reuse this object
results = rec.recognize("photo.jpg")      # path, or a BGR NumPy array (e.g. a cv2 video frame)
# -> [{"person_id": "EMP001", "name": "R. Meena", "confidence": 0.87, "status": "RECOGNIZED"}, ...]

detailed = rec.recognize_detailed(frame)  # same dicts + "bbox": [x1, y1, x2, y2] and "det_score"
annotated = rec.draw_results(frame, detailed)
rec.reload()                              # pick up a re-run enrollment without restarting
```

* `recognize()` returns exactly the four documented keys; use `recognize_detailed()` when you also need the box.
* Results are ordered left to right. An image with no faces returns `[]`.
* Create the `FaceRecognizer` once at startup - loading the model is the slow part.

## 6. Tuning the threshold

Set `SIMILARITY_THRESHOLD` in `config.py` (default **0.40**) or pass `threshold=` / `--threshold`.

* Too many strangers accepted -> raise it (0.45 - 0.55).
* Too many real employees marked UNKNOWN -> lower it (0.30 - 0.38) or enroll more/better photos.

The right value depends on your camera and photos; test with a few images of employees and of people who are not enrolled.

## Notes / limitations

* Every detected face is matched independently, so two faces can both match the same employee.
* Faces smaller than `MIN_FACE_SIZE` (40 px) or below `MIN_DET_SCORE` are ignored. For CCTV-distance faces, raise `DET_SIZE` in `config.py`.
* Photos of photos, masks and heavy occlusion are not detected as spoofing - liveness detection is out of scope.
* All numeric settings live in `config.py`.
