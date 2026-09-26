import cv2
import csv
from datetime import datetime
from ultralytics import YOLO

MODEL_PATH = r".\ai-service\models\yolo26n.pt"
VIDEO_PATH = r".\ai-service\videos\demo_cctv.mp4"
OUTPUT_VIDEO = r".\ai-service\videos\counted_cctv.mp4"
OUTPUT_CSV = r".\ai-service\outputs\occupancy_log.csv"

CAPACITY = 20
SAVE_INTERVAL = 1.0

model = YOLO(MODEL_PATH)

cap = cv2.VideoCapture(VIDEO_PATH)

if not cap.isOpened():
    raise RuntimeError("Could not open CCTV video")

fps = cap.get(cv2.CAP_PROP_FPS)
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

if fps <= 0:
    fps = 30

fourcc = cv2.VideoWriter_fourcc(*"mp4v")
out = cv2.VideoWriter(
    OUTPUT_VIDEO,
    fourcc,
    fps,
    (width, height)
)

with open(OUTPUT_CSV, "w", newline="") as csvfile:

    writer = csv.writer(csvfile)

    writer.writerow([
        "timestamp",
        "video_time",
        "person_count",
        "capacity",
        "occupancy_percentage",
        "status"
    ])

    frame_number = 0
    next_save_time = 0

    while True:

        ret, frame = cap.read()

        if not ret:
            break

        video_time = frame_number / fps

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

        occupancy = (person_count / CAPACITY) * 100

        if person_count > CAPACITY:
            status = "OVER_CAPACITY"
        else:
            status = "NORMAL"

        annotated = result.plot()

        cv2.rectangle(
            annotated,
            (10, 10),
            (360, 75),
            (0, 0, 0),
            -1
        )

        cv2.putText(
            annotated,
            f"PERSON COUNT: {person_count}",
            (20, 38),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2
        )

        cv2.putText(
            annotated,
            f"OCCUPANCY: {occupancy:.0f}%",
            (20, 65),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 255),
            2
        )

        out.write(annotated)

        if video_time >= next_save_time:

            timestamp = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            minutes = int(video_time // 60)
            seconds = int(video_time % 60)

            video_timestamp = f"{minutes:02d}:{seconds:02d}"

            writer.writerow([
                timestamp,
                video_timestamp,
                person_count,
                CAPACITY,
                round(occupancy, 2),
                status
            ])

            csvfile.flush()

            print(
                f"{video_timestamp} | "
                f"Persons: {person_count} | "
                f"Occupancy: {occupancy:.0f}% | "
                f"Status: {status}"
            )

            next_save_time += SAVE_INTERVAL

        frame_number += 1

cap.release()
out.release()

print()
print("================================")
print("AI CCTV PROCESSING COMPLETE")
print("================================")
print(f"Video: {OUTPUT_VIDEO}")
print(f"Log:   {OUTPUT_CSV}")
