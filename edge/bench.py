"""Measure inference-only and end-to-end FPS on THIS device; write results/bench.json with device label."""
import json
import os
import statistics
import time

import cv2
import numpy as np
from detector import OnnxYolo
from device import device_label
from settings import load_cfg

cfg = load_cfg()
dev = device_label()
m = OnnxYolo(cfg["model"], cfg["imgsz"])
src = os.getenv("BENCH_VIDEO")  # optional video file; else synthetic frames
cap = cv2.VideoCapture(src) if src else None
frames = []
for _ in range(120):
    if cap:
        ok, f = cap.read()
        if not ok: break
    else:
        f = np.random.randint(0, 255, (720, 1280, 3), np.uint8)
    frames.append(f)
for f in frames[:10]: m(f)  # warm-up
inf, e2e = [], []
for f in frames:
    t = time.perf_counter(); m(f); e2e.append((time.perf_counter() - t) * 1000); inf.append(m.last_ms)
res = {"device": dev, "providers": m.providers, "model": os.path.basename(cfg["model"]), "imgsz": cfg["imgsz"], "n": len(frames),
       "inference_ms_median": round(statistics.median(inf), 2), "e2e_ms_median": round(statistics.median(e2e), 2),
       "fps_e2e": round(1000 / statistics.median(e2e), 1), "measured_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
os.makedirs("results", exist_ok=True)
json.dump(res, open(f"results/bench_{dev.replace(' ', '_').replace('/', '-')}.json", "w"), indent=2)
print(json.dumps(res, indent=2))
