"""Render a conveyor-belt demo video from REAL held-out test-split objects (screws, PCBs, glass,
plastic, cardboard cut out of `training/dataset/images/test`) sliding across a rendered belt.
Feed it to the edge node (EDGE_CAMERA=models/demo_belt.mp4) to show the full pipeline working.
Usage: python scripts/make_belt_video.py [out.mp4] [seconds]"""
from __future__ import annotations

import random
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "training"))
from build_public_dataset import threshold_box  # noqa: E402  (reuse the same cut-out logic as the dataset)

OUT = sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "models" / "demo_belt.mp4")
SECS = float(sys.argv[2]) if len(sys.argv) > 2 else 48
W, H, FPS, SPEED = 1280, 720, 12, 110  # px/s belt speed
TEST = ROOT / "training" / "dataset" / "images" / "test"


def cutouts(rng: random.Random) -> list[tuple[np.ndarray, np.ndarray]]:
    out = []
    for pat, tight in [("screw_*.jpg", False), ("pcb_*.jpg", True), ("trashnet_*.jpg", False)]:
        files = sorted(TEST.glob(pat)); rng.shuffle(files)
        for p in files[:6 if tight else 8]:
            im = cv2.imread(str(p))
            if im is None: continue
            if tight:
                out.append((im, np.ones(im.shape[:2], np.uint8)))
            else:
                tb = threshold_box(cv2.cvtColor(im, cv2.COLOR_BGR2RGB))
                if tb is None: continue
                m, (x1, y1, x2, y2) = tb
                out.append((im[y1:y2, x1:x2], m[y1:y2, x1:x2]))
    return out


def scaled(obj: np.ndarray, mask: np.ndarray, rng: random.Random) -> tuple[np.ndarray, np.ndarray]:
    target = rng.uniform(150, 260); s = target / max(obj.shape[:2])
    o = cv2.resize(obj, (max(10, int(obj.shape[1] * s)), max(10, int(obj.shape[0] * s))))
    m = cv2.resize(mask, (o.shape[1], o.shape[0]), interpolation=cv2.INTER_NEAREST)
    if rng.random() < 0.5: o, m = o[:, ::-1], m[:, ::-1]
    return o, m


def main():
    rng = random.Random(0)
    pool = cutouts(rng)
    if not pool: raise SystemExit("no test images found - run training/build_public_dataset.py first")
    rng.shuffle(pool)  # mix the classes along the belt
    cycle = W + 500
    lanes = [150, 400]
    objs = []
    for i in range(10):
        o, m = scaled(*pool[i % len(pool)], rng)
        objs.append({"img": o, "mask": m, "y": lanes[i % 2] + rng.randint(-30, 30), "off": i * cycle / 10 + rng.randint(-60, 60)})

    Path(OUT).parent.mkdir(parents=True, exist_ok=True)
    vw = cv2.VideoWriter(OUT, cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))
    n = int(SECS * FPS)
    for f in range(n):
        t = f / FPS
        frame = np.full((H, W, 3), (44, 42, 40), np.uint8)              # floor
        frame[70:650] = (78, 76, 72)                                     # belt
        for x0 in range(-160, W + 160, 160):                             # moving belt seams
            x = int(x0 - (t * SPEED) % 160)
            cv2.line(frame, (x, 70), (x, 650), (64, 62, 58), 3)
        cv2.rectangle(frame, (0, 52), (W, 70), (30, 30, 32), -1)         # rails
        cv2.rectangle(frame, (0, 650), (W, 668), (30, 30, 32), -1)
        for ob in objs:
            o, m = ob["img"], ob["mask"]; oh, ow = o.shape[:2]
            x = int(W - ((t * SPEED + ob["off"]) % cycle)); y = int(ob["y"])
            if x + ow < 0 or x > W: continue
            xs, xe = max(0, x), min(W, x + ow); ys, ye = max(0, y), min(H, y + oh)
            if xe - xs < 4 or ye - ys < 4: continue
            osl = o[ys - y:ye - y, xs - x:xe - x]; msl = m[ys - y:ye - y, xs - x:xe - x]
            sh = np.clip(msl.astype(np.float32), 0, 1)[..., None]
            sy, sx = min(H, ys + 8), min(W, xs + 8)                      # soft shadow, offset 8 px
            reg = frame[sy:sy + (ye - ys), sx:sx + (xe - xs)]
            reg[:] = (reg * (1 - 0.35 * sh[:reg.shape[0], :reg.shape[1]])).astype(np.uint8)
            a = cv2.GaussianBlur(msl.astype(np.float32), (5, 5), 0)[..., None]
            roi = frame[ys:ye, xs:xe].astype(np.float32)
            frame[ys:ye, xs:xe] = (roi * (1 - a) + osl.astype(np.float32) * a).astype(np.uint8)
        vw.write(frame)
    vw.release()
    print(f"wrote {OUT}: {SECS:.0f}s @ {FPS}fps, {len(objs)} objects from {len(pool)} test cut-outs (loops via capture.py)")


if __name__ == "__main__":
    main()
