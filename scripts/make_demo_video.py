"""Turn held-out TEST-split images into a slow-pan slideshow video for `edge/capture.py` (EDGE_CAMERA=demo.mp4).
Uses only test images (never seen in training) and shows NO labels - the detector must find the objects itself.
Usage: python scripts/make_demo_video.py [out.mp4] [n_images] [seconds_per_image]"""
import random
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
out = sys.argv[1] if len(sys.argv) > 1 else "demo_makerspace.mp4"
n = int(sys.argv[2]) if len(sys.argv) > 2 else 24
secs = float(sys.argv[3]) if len(sys.argv) > 3 else 2.5
fps, W, H = 10, 1280, 720

imgs = sorted((ROOT / "training/dataset/images/test").glob("*.jpg"))
if not imgs: raise SystemExit("no test images - run training/build_public_dataset.py first")
random.Random(0).shuffle(imgs)
# one image per source prefix first (lvis_, taco_, trashnet_, pcb_, screw_) so every class family appears, then the rest
by_src = {}
for p in imgs: by_src.setdefault(p.name.split("_")[0], []).append(p)
order = [q for k in sorted(by_src) for q in by_src[k][:max(1, n // len(by_src))]][:n]

w = cv2.VideoWriter(out, cv2.VideoWriter_fourcc(*"mp4v"), fps, (W, H))
for p in order:
    im = cv2.imread(str(p)); h, wd = im.shape[:2]; s = min(W / wd, H / h) * 1.08   # slight zoom so a pan is possible
    im = cv2.resize(im, (int(wd * s), int(h * s)))
    canvas_w, canvas_h = max(W, im.shape[1]), max(H, im.shape[0])
    canvas = np.full((canvas_h, canvas_w, 3), 40, np.uint8)
    oy, ox = (canvas_h - im.shape[0]) // 2, (canvas_w - im.shape[1]) // 2
    canvas[oy:oy + im.shape[0], ox:ox + im.shape[1]] = im
    frames = int(secs * fps)
    for i in range(frames):
        t = i / max(1, frames - 1); dx = int((canvas_w - W) * t); dy = int((canvas_h - H) * (1 - t))
        w.write(canvas[dy:dy + H, dx:dx + W])
w.release(); print(f"wrote {out}: {len(order)} test images, {secs}s each")
