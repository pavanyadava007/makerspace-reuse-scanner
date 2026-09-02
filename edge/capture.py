"""OpenCV capture loop → ONNX inference → WebSocket push to the API. Prints device-labelled FPS."""
from __future__ import annotations

import asyncio
import base64
import json
import os
import time
from collections import deque

import cv2
import numpy as np
import websockets
import yaml
from detector import OnnxYolo
from device import device_label
from settings import load_cfg

CFG = load_cfg()
API_WS = os.getenv("API_URL", "http://localhost:8000").replace("http", "ws") + "/ws/edge"
DEVICE = device_label()
CLASSES = yaml.safe_load(open(CFG["classes"]))["names"]


def open_camera(src):
    """src: int index (webcam), /dev/video path, RTSP/HTTP URL, or a video file (looped)."""
    cap = cv2.VideoCapture(int(src) if str(src).isdigit() else src)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280); cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    if not cap.isOpened():
        raise SystemExit(f"cannot open camera/video {src!r} - webcam index, /dev/videoN, RTSP URL or a video file")
    return cap


def is_file_source(src) -> bool:
    return os.path.isfile(str(src))


def jpeg_b64(img: np.ndarray, q=80) -> str:
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, q])
    return base64.b64encode(buf).decode()


async def run():
    model = OnnxYolo(CFG["model"], CFG["imgsz"])
    print(f"[edge] device={DEVICE} providers={model.providers}")
    cap = open_camera(CFG["camera"]); loop_file = is_file_source(CFG["camera"])
    file_fps = cap.get(cv2.CAP_PROP_FPS) if loop_file else 0
    fps_win: deque[float] = deque(maxlen=60)
    n = 0
    # the API is a LAN service: never route the WebSocket through HTTP(S)_PROXY from the environment
    async for ws in websockets.connect(API_WS, ping_interval=20, proxy=None):
        try:
            await ws.send(json.dumps({"type": "hello", "device": DEVICE, "providers": model.providers,
                                      "model": os.path.basename(CFG["model"])}))
            while True:
                t0 = time.perf_counter()
                ok, frame = cap.read()
                if not ok:
                    if loop_file:  # end of video file → start over
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0); continue
                    await asyncio.sleep(0.05); continue
                dets = model(frame, CFG["min_conf"], CFG["iou"])
                fps_win.append(1 / max(time.perf_counter() - t0, 1e-6))
                fps = sum(fps_win) / len(fps_win)
                n += 1
                if n % CFG["send_every_n"] == 0:
                    h, w = frame.shape[:2]
                    payload = {
                        "type": "frame", "device": DEVICE, "fps": round(fps, 1),
                        "infer_ms": round(model.last_ms, 1), "ts": time.time(),
                        "width": w, "height": h,
                        "detections": [
                            {"cls": CLASSES[d.cls], "conf": round(d.conf, 3), "xyxy": [round(v, 1) for v in d.xyxy],
                             "crop": jpeg_b64(frame[max(0, int(d.xyxy[1])):int(d.xyxy[3]), max(0, int(d.xyxy[0])):int(d.xyxy[2])])
                             if CFG["crop_upload"] and d.xyxy[3] > d.xyxy[1] + 8 and d.xyxy[2] > d.xyxy[0] + 8 else None}
                            for d in dets],
                        "frame": jpeg_b64(cv2.resize(frame, (640, int(640 * h / w))), 60),
                    }
                    await ws.send(json.dumps(payload))
                if n % 30 == 0:
                    print(f"[edge] {DEVICE}: {fps:.1f} FPS end-to-end, {model.last_ms:.1f} ms inference, {len(dets)} dets")
                # a video file would otherwise be consumed as fast as the model runs; pace it to its own frame rate
                await asyncio.sleep(max(0.0, 1 / file_fps - (time.perf_counter() - t0)) if file_fps > 0 else 0)
        except websockets.ConnectionClosed:
            print("[edge] ws closed, reconnecting"); continue


if __name__ == "__main__":
    asyncio.run(run())
