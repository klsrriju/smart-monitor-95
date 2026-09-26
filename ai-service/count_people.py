import cv2
from ultralytics import YOLO

MODEL_PATH = r".\ai-service\models\yolo26n.pt"
VIDEO_PATH = r".\ai-service\videos\demo_cctv.mp4"
OUTPUT_PATH = r".\ai-service\videos\counted_cctv.mp4"

model = YOLO(MODEL_PATH)

cap = cv2.VideoCapture(VIDEO_PATH)

if not cap.isOpened():
    raise RuntimeError("Could not open CCTV video")

fps = cap.get(cv2.CAP_PROP_FPS)
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

fourcc = cv2.VideoWriter_fourcc(*"mp4v")
out = cv2.VideoWriter(OUTPUT_PATH, fourcc, fps, (width, height))

frame_number = 0

while True:
    ret, frame = cap.read()

    if not ret:
        break

    results = model.predict(
        frame,
        classes=[0],
        conf=0.35,
        verbose=False
    )

    result = results[0]

    person_count = 0

    if result.boxes is not None:
        person_count = len(result.boxes)

    annotated = result.plot()

    cv2.rectangle(annotated, (10, 10), (300, 65), (0, 0, 0), -1)

    cv2.putText(
        annotated,
        f"PERSON COUNT: {person_count}",
        (20, 48),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.9,
        (255, 255, 255),
        2
    )

    out.write(annotated)

    frame_number += 1

    if frame_number % 50 == 0:
        print(f"Processed {frame_number} frames | Persons: {person_count}")

cap.release()
out.release()

print()
print("DONE")
print("Output:", OUTPUT_PATH)
