"""
Optional live CCTV/YOLO service used by the combined gateway.
"""
from __future__ import annotations
from pathlib import Path
from threading import Lock
from typing import Any, Dict
import time
import cv2

BASE_DIR=Path(__file__).resolve().parents[2]
MODEL_PATH=BASE_DIR/"ai-service"/"models"/"yolo26n.pt"
try:
    from ultralytics import YOLO
    MODEL=YOLO(str(MODEL_PATH)) if MODEL_PATH.exists() else None
except Exception as exc:
    MODEL=None
    print("YOLO unavailable:",exc)

CONFIGS=[
{"camera_id":"CAM-001","camera_name":"Main Hall Camera","location":"Chennai","video_path":"ai-service/videos/demo_cctv.mp4","capacity":20,"status":"ONLINE"},
{"camera_id":"CAM-002","camera_name":"Project Area Camera","location":"Madurai","video_path":"ai-service/videos/mot17_04.mp4","capacity":25,"status":"ONLINE"},
{"camera_id":"CAM-003","camera_name":"Corridor Camera","location":"Coimbatore","video_path":"ai-service/videos/mot17_10.mp4","capacity":15,"status":"ONLINE"},
{"camera_id":"CAM-004","camera_name":"Entrance Camera","location":"Tiruchirappalli","video_path":"ai-service/videos/mot17_11.mp4","capacity":30,"status":"ONLINE"},
]

class Camera:
    def __init__(self,cfg):
        self.cfg=cfg; self.lock=Lock(); self.cap=None; self.latest={}
    def _open(self):
        if self.cap is None or not self.cap.isOpened():
            path=BASE_DIR/self.cfg["video_path"]
            self.cap=cv2.VideoCapture(str(path))
        return self.cap is not None and self.cap.isOpened()
    def _detect(self,frame):
        if MODEL is None: return 0,frame
        try:
            result=MODEL.predict(frame,classes=[0],conf=0.35,verbose=False)[0]
            annotated=result.plot()
            return len(result.boxes),annotated
        except Exception:
            return 0,frame
    def get_status_payload(self):
        with self.lock:
            if not self._open():
                return {**self.cfg,"status":"OFFLINE","people_count":0,"occupancy_percentage":0,"alert_status":"OFFLINE"}
            ok,frame=self.cap.read()
            if not ok:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES,0); ok,frame=self.cap.read()
            count,annotated=self._detect(frame) if ok else (0,frame)
            cap=max(1,int(self.cfg["capacity"])); pct=round(count/cap*100,1)
            alert="OVER_CAPACITY" if pct>=100 else "WARNING" if pct>=80 else "NORMAL"
            self.latest={"camera_id":self.cfg["camera_id"],"people_count":count,"occupancy_percentage":pct,
                         "alert_status":alert,"status":"ONLINE","recorded_at":time.strftime("%Y-%m-%dT%H:%M:%SZ")}
            return {**self.cfg,**self.latest}
    def generate_stream(self):
        while True:
            with self.lock:
                if not self._open():
                    time.sleep(1); continue
                ok,frame=self.cap.read()
                if not ok:
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES,0); continue
                count,frame=self._detect(frame)
                cv2.putText(frame,f"{self.cfg['camera_id']}  People: {count}",(16,32),
                            cv2.FONT_HERSHEY_SIMPLEX,0.9,(255,255,255),2,cv2.LINE_AA)
                ok,buf=cv2.imencode(".jpg",frame)
            if not ok: continue
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n"+buf.tobytes()+b"\r\n"
            time.sleep(0.05)

CAMERA_REGISTRY={c["camera_id"]:Camera(c) for c in CONFIGS}
