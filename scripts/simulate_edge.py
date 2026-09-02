"""Demo without a camera or model: streams synthetic frames + fake detections to /ws/edge. python scripts/simulate_edge.py"""
import asyncio
import base64
import json
import os
import random
import time

import cv2
import numpy as np
import websockets

API = os.getenv("API_URL", "http://localhost:8000").replace("http", "ws") + "/ws/edge"
CLS = ["screw", "pcb", "filament_spool", "wood_offcut", "cable", "battery"]

def frame():
    img = np.full((720, 1280, 3), 60, np.uint8); dets = []
    for _ in range(random.randint(1, 3)):
        x, y, w, h = random.randint(50, 900), random.randint(50, 500), random.randint(80, 250), random.randint(80, 200)
        cv2.rectangle(img, (x, y), (x + w, y + h), (random.randint(80, 255),) * 3, -1)
        crop = cv2.imencode(".jpg", img[y:y + h, x:x + w])[1]
        dets.append({"cls": random.choice(CLS), "conf": round(random.uniform(0.4, 0.95), 2), "xyxy": [x, y, x + w, y + h],
                     "crop": base64.b64encode(crop).decode()})
    return img, dets

async def main():
    async with websockets.connect(API, proxy=None) as ws:  # LAN service — ignore proxy env
        await ws.send(json.dumps({"type": "hello", "device": "simulator (no camera)", "providers": ["none"], "model": "simulator"}))
        while True:
            img, dets = frame()
            await ws.send(json.dumps({"type": "frame", "device": "simulator (no camera)", "fps": 3.0, "infer_ms": 0.0, "ts": time.time(),
                                      "width": 1280, "height": 720, "detections": dets,
                                      "frame": base64.b64encode(cv2.imencode(".jpg", img)[1]).decode()}))
            await asyncio.sleep(2)
asyncio.run(main())
