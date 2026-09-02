"""Build `dataset/` (v0-public) from public sources, reproducibly. Run: python build_public_dataset.py

Sources (all fetched from their public hosts; nothing is bundled):
  LVIS v1 train+val annotations (CC BY 4.0) on COCO 2017 images → nut_bolt, motor, battery, tool, glass, plastic_container, cardboard
  TACO (CC BY 4.0, Flickr images)                                 → battery, glass, plastic_container, cardboard (cluttered scenes)
  TrashNet (Yang & Thung 2016, GitHub)                            → cardboard, glass, plastic_container (studio shots, box by threshold)
  HF SanderGi/pcb-detection-cropped-pcbs (no licence declared)    → pcb (tight crops, full-frame box)
  HF shrish23/screw-dataset = MVTec AD "screw" (CC BY-NC-SA 4.0)  → screw (grey background, box by threshold)
  Copy-paste composites (TRAIN split only): PCB/screw/TrashNet cut-outs pasted into LVIS scenes that verifiably
  contain none of our classes → teaches localisation for the studio-only classes.

Classes without any public detection data stay empty: filament_spool, wood_offcut, cable, 3d_print_part, acrylic_sheet, metal_profile.
Split: deterministic 70/20/10 by md5 of a *session key* (LVIS image id, TACO batch, TrashNet file, PCB board name, screw file);
composites go to train only. Writes dataset/stats.json and dataset/SOURCES.md — the only place counts may come from.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import random
import zipfile
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import cv2
import numpy as np
import requests
import yaml
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent
DS = ROOT / "dataset"
CACHE = Path(os.getenv("MRS_DATA_CACHE", DS / "_cache"))
MAXSIDE = 1024
SEED = 0
N_COMPOSITES = int(os.getenv("MRS_COMPOSITES", 900))
NAMES: dict[int, str] = yaml.safe_load(open(ROOT / "classes.yaml"))["names"]
IDX = {v: k for k, v in NAMES.items()}

LVIS_MAP = {"bolt": "nut_bolt", "nut": "nut_bolt", "motor": "motor", "battery": "battery",
            "screwdriver": "tool", "wrench": "tool", "pliers": "tool", "hammer": "tool", "handsaw": "tool", "drill": "tool",
            "tape_measure": "tool", "glass_(drink_container)": "glass", "wineglass": "glass", "jar": "glass",
            "wine_bottle": "glass", "beer_bottle": "glass", "water_bottle": "plastic_container", "box": "cardboard", "carton": "cardboard"}
LVIS_CAP = {"glass": 450, "cardboard": 450, "plastic_container": 300}   # image cap per class; other classes take everything
TACO_MAP = {"Battery": "battery", "Glass bottle": "glass", "Glass jar": "glass", "Glass cup": "glass", "Broken glass": "glass",
            "Other plastic bottle": "plastic_container", "Clear plastic bottle": "plastic_container",
            "Other plastic container": "plastic_container", "Disposable plastic cup": "plastic_container",
            "Other plastic cup": "plastic_container", "Corrugated carton": "cardboard", "Other carton": "cardboard",
            "Egg carton": "cardboard", "Drink carton": "cardboard", "Meal carton": "cardboard"}
TRASHNET_MAP = {"cardboard": "cardboard", "glass": "glass", "plastic": "plastic_container"}
TRASHNET_CAP = 350
HF = "https://huggingface.co/datasets"
SESSION = requests.Session(); SESSION.headers["User-Agent"] = "mrs-dataset-builder/0.3"


def split_of(key: str) -> str:
    h = int(hashlib.md5(key.encode()).hexdigest(), 16) % 1000
    return "train" if h < 700 else "val" if h < 900 else "test"


def fetch(url: str, tries: int = 3) -> bytes | None:
    for _ in range(tries):
        try:
            r = SESSION.get(url, timeout=60)
            if r.status_code == 200 and len(r.content) > 1000: return r.content
        except requests.RequestException:
            pass
    return None


def load_rgb(data: bytes, exif: bool = False) -> np.ndarray | None:
    try:
        im = Image.open(io.BytesIO(data))
        if exif: im = ImageOps.exif_transpose(im)
        return np.asarray(im.convert("RGB"))
    except Exception:
        return None


def write_sample(name: str, split: str, rgb: np.ndarray, boxes: list[tuple[str, float, float, float, float]]):
    """boxes: (cls, x1, y1, x2, y2) in pixels of `rgb`. Resizes to MAXSIDE, writes jpg + YOLO txt."""
    h, w = rgb.shape[:2]; s = min(1.0, MAXSIDE / max(h, w))
    if s < 1: rgb = cv2.resize(rgb, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA); h, w = rgb.shape[:2]
    lines = []
    for cls, x1, y1, x2, y2 in boxes:
        x1, y1, x2, y2 = max(0, x1 * s), max(0, y1 * s), min(w, x2 * s), min(h, y2 * s)
        if x2 - x1 < 4 or y2 - y1 < 4: continue
        lines.append(f"{IDX[cls]} {(x1 + x2) / 2 / w:.6f} {(y1 + y2) / 2 / h:.6f} {(x2 - x1) / w:.6f} {(y2 - y1) / h:.6f}")
    if not lines: return False
    (DS / "images" / split).mkdir(parents=True, exist_ok=True); (DS / "labels" / split).mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(DS / "images" / split / f"{name}.jpg"), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 90])
    (DS / "labels" / split / f"{name}.txt").write_text("\n".join(lines))
    return True


def threshold_box(rgb: np.ndarray, margin: float = 0.02) -> tuple[np.ndarray, tuple[int, int, int, int]] | None:
    """Object on a plain light background → (mask, box). Background level = median of the image border."""
    g = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY); hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    b = np.concatenate([g[:8].ravel(), g[-8:].ravel(), g[:, :8].ravel(), g[:, -8:].ravel()])
    bg = np.median(b)
    mask = ((np.abs(g.astype(int) - bg) > 45) | (hsv[..., 1] > 60)).astype(np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(mask)
    if n < 2: return None
    areas = stats[1:, cv2.CC_STAT_AREA]; big = areas.max()
    keep = [i + 1 for i, a in enumerate(areas) if a >= max(0.02 * big, 200)]
    if not keep: return None
    m = np.isin(lab, keep).astype(np.uint8)
    ys, xs = np.where(m)
    if len(xs) == 0: return None
    h, w = g.shape; x1, x2, y1, y2 = xs.min(), xs.max(), ys.min(), ys.max()
    if (x2 - x1) * (y2 - y1) < 0.02 * h * w or (x2 - x1) * (y2 - y1) > 0.9 * h * w: return None
    mx, my = int(margin * w), int(margin * h)
    return m, (max(0, x1 - mx), max(0, y1 - my), min(w, x2 + mx), min(h, y2 + my))


# ----------------------------------------------------------------------------------------------------------------- LVIS
def build_lvis(cutouts_bg: list[np.ndarray]) -> Counter:
    stats = Counter(); imgs, anns = {}, defaultdict(list); cats = {}
    for f in ("lvis_v1_train.json", "lvis_v1_val.json"):
        d = json.load(open(CACHE / f)); cats.update({c["id"]: c["name"] for c in d["categories"]})
        for im in d["images"]: imgs[im["id"]] = im
        for a in d["annotations"]: anns[a["image_id"]].append(a)
    our_cat_ids = {cid for cid, n in cats.items() if n in LVIS_MAP}
    per_class = Counter(); jobs = []; bg_jobs = []
    for iid in sorted(imgs):
        im = imgs[iid]; a_list = anns.get(iid, [])
        present = {a["category_id"] for a in a_list} & our_cat_ids
        if not present:
            # background for composites: at least one of our classes verified absent, none annotated present
            if len(set(im.get("neg_category_ids", [])) & our_cat_ids) >= 1 and len(bg_jobs) < 600: bg_jobs.append(im)
            continue
        if present & set(im.get("not_exhaustive_category_ids", [])): continue   # unlabeled instances of our classes → skip
        classes = {LVIS_MAP[cats[c]] for c in present}
        if all(per_class[c] >= LVIS_CAP.get(c, 10**9) for c in classes): continue
        for c in classes: per_class[c] += 1
        boxes = [(LVIS_MAP[cats[a["category_id"]]], a["bbox"][0], a["bbox"][1], a["bbox"][0] + a["bbox"][2], a["bbox"][1] + a["bbox"][3])
                 for a in a_list if a["category_id"] in our_cat_ids]
        jobs.append((im, boxes))
    print(f"[lvis] {len(jobs)} images selected, per class {dict(per_class)}; {len(bg_jobs)} verified-negative backgrounds")

    def do(job):
        im, boxes = job; data = fetch(im["coco_url"])
        rgb = load_rgb(data) if data else None
        if rgb is None or rgb.shape[1] != im["width"]: return None
        return write_sample(f"lvis_{im['id']}", split_of(f"lvis{im['id']}"), rgb, boxes), [b[0] for b in boxes], split_of(f"lvis{im['id']}")

    with ThreadPoolExecutor(24) as ex:
        for r in ex.map(do, jobs):
            if r and r[0]:
                for c in r[1]: stats[(r[2], c)] += 1

    def do_bg(im):
        data = fetch(im["coco_url"]); rgb = load_rgb(data) if data else None
        if rgb is None: return None
        h, w = rgb.shape[:2]; s = min(1.0, 800 / max(h, w))
        return cv2.resize(rgb, (int(w * s), int(h * s))) if s < 1 else rgb

    with ThreadPoolExecutor(24) as ex:
        cutouts_bg.extend([r for r in ex.map(do_bg, bg_jobs) if r is not None])
    return stats


# ----------------------------------------------------------------------------------------------------------------- TACO
def build_taco() -> Counter:
    stats = Counter(); d = json.load(open(CACHE / "taco.json")); cats = {c["id"]: c["name"] for c in d["categories"]}
    anns = defaultdict(list)
    for a in d["annotations"]: anns[a["image_id"]].append(a)
    jobs = []
    for im in d["images"]:
        boxes = [(TACO_MAP[cats[a["category_id"]]], a["bbox"][0], a["bbox"][1], a["bbox"][0] + a["bbox"][2], a["bbox"][1] + a["bbox"][3])
                 for a in anns.get(im["id"], []) if cats[a["category_id"]] in TACO_MAP]
        if boxes: jobs.append((im, boxes))
    print(f"[taco] {len(jobs)} images with mapped classes")

    def do(job):
        im, boxes = job; data = fetch(im["flickr_url"])
        if not data: return None
        rgb = load_rgb(data, exif=True)
        if rgb is None or (rgb.shape[1], rgb.shape[0]) != (im["width"], im["height"]):
            rgb = load_rgb(data, exif=False)
            if rgb is None or (rgb.shape[1], rgb.shape[0]) != (im["width"], im["height"]): return None
        batch = im["file_name"].split("/")[0]; split = split_of(f"taco{batch}")   # batch = capture session
        return write_sample(f"taco_{im['id']}", split, rgb, boxes), [b[0] for b in boxes], split

    with ThreadPoolExecutor(16) as ex:
        for r in ex.map(do, jobs):
            if r and r[0]:
                for c in r[1]: stats[(r[2], c)] += 1
    return stats


# ------------------------------------------------------------------------------------------------------------- TrashNet
def build_trashnet(cutouts: dict[str, list]) -> Counter:
    stats = Counter(); z = CACHE / "trashnet.zip"
    if not z.exists(): z.write_bytes(fetch("https://github.com/garythung/trashnet/raw/master/data/dataset-resized.zip", 1))
    with zipfile.ZipFile(z) as zf:
        names = sorted(n for n in zf.namelist() if n.endswith(".jpg") and n.split("/")[-2] in TRASHNET_MAP)
        per = Counter()
        for n in names:
            src = n.split("/")[-2]; cls = TRASHNET_MAP[src]
            if per[cls] >= TRASHNET_CAP: continue
            rgb = load_rgb(zf.read(n))
            tb = threshold_box(rgb) if rgb is not None else None
            if tb is None: continue
            mask, (x1, y1, x2, y2) = tb; per[cls] += 1
            key = Path(n).stem; split = split_of(f"trashnet{key}")
            if write_sample(f"trashnet_{key}", split, rgb, [(cls, x1, y1, x2, y2)]):
                stats[(split, cls)] += 1
                if split == "train" and len(cutouts[cls]) < 120: cutouts[cls].append((rgb[y1:y2, x1:x2], mask[y1:y2, x1:x2]))
    return stats


# ------------------------------------------------------------------------------------------------------ HuggingFace sets
def hf_files(repo: str) -> list[str]:
    return [s["rfilename"] for s in SESSION.get(f"{HF.replace('/datasets', '')}/api/datasets/{repo}", timeout=60).json()["siblings"]]


def build_pcb(cutouts: dict[str, list]) -> Counter:
    stats = Counter(); repo = "SanderGi/pcb-detection-cropped-pcbs"
    files = [f for f in hf_files(repo) if f.lower().endswith((".png", ".jpg", ".jpeg"))]
    print(f"[pcb] {len(files)} cropped boards")

    def do(f):
        data = fetch(f"{HF}/{repo}/resolve/main/{f}"); rgb = load_rgb(data) if data else None
        if rgb is None: return None
        h, w = rgb.shape[:2]; m = 0.01
        board = f.split("_")[0]; split = split_of(f"pcb{board}")            # Top/Bottom of one board stay together
        name = "pcb_" + Path(f).stem.replace(" ", "_")
        ok = write_sample(name, split, rgb, [("pcb", m * w, m * h, (1 - m) * w, (1 - m) * h)])
        return ok, split, rgb if split == "train" else None

    with ThreadPoolExecutor(16) as ex:
        for r in ex.map(do, files):
            if r and r[0]:
                stats[(r[1], "pcb")] += 1
                if r[2] is not None and len(cutouts["pcb"]) < 150:
                    rgb = r[2]; s = 512 / max(rgb.shape[:2]); small = cv2.resize(rgb, (int(rgb.shape[1] * s), int(rgb.shape[0] * s)))
                    cutouts["pcb"].append((small, np.ones(small.shape[:2], np.uint8)))
    return stats


def build_screws(cutouts: dict[str, list]) -> Counter:
    stats = Counter(); repo = "shrish23/screw-dataset"
    files = [f for f in hf_files(repo) if "/images/" in f and f.lower().endswith(".png")]
    print(f"[screw] {len(files)} MVTec screw images")

    def do(f):
        data = fetch(f"{HF}/{repo}/resolve/main/{f}"); rgb = load_rgb(data) if data else None
        tb = threshold_box(rgb, 0.03) if rgb is not None else None
        if tb is None: return None
        mask, (x1, y1, x2, y2) = tb; split = split_of(f"screw{f}")
        ok = write_sample("screw_" + f.split("/")[-3] + "_" + Path(f).stem, split, rgb, [("screw", x1, y1, x2, y2)])
        return ok, split, (rgb[y1:y2, x1:x2], mask[y1:y2, x1:x2]) if split == "train" else None

    with ThreadPoolExecutor(16) as ex:
        for r in ex.map(do, files):
            if r and r[0]:
                stats[(r[1], "screw")] += 1
                if r[2] is not None and len(cutouts["screw"]) < 150: cutouts["screw"].append(r[2])
    return stats


# ----------------------------------------------------------------------------------------------------------- composites
def paste(bg: np.ndarray, obj: np.ndarray, mask: np.ndarray, rng: random.Random) -> tuple[np.ndarray, tuple[int, int, int, int]] | None:
    H, W = bg.shape[:2]; oh, ow = obj.shape[:2]
    target = rng.uniform(0.12, 0.42) * W; s = target / max(oh, ow)
    obj = cv2.resize(obj, (max(8, int(ow * s)), max(8, int(oh * s))))
    mask = cv2.resize(mask, (obj.shape[1], obj.shape[0]), interpolation=cv2.INTER_NEAREST)
    if rng.random() < 0.5: obj, mask = obj[:, ::-1], mask[:, ::-1]
    ang = rng.uniform(-180, 180)
    M = cv2.getRotationMatrix2D((obj.shape[1] / 2, obj.shape[0] / 2), ang, 1.0)
    cos, sin = abs(M[0, 0]), abs(M[0, 1])
    nw, nh = int(obj.shape[0] * sin + obj.shape[1] * cos), int(obj.shape[0] * cos + obj.shape[1] * sin)
    M[0, 2] += nw / 2 - obj.shape[1] / 2; M[1, 2] += nh / 2 - obj.shape[0] / 2
    obj = cv2.warpAffine(obj, M, (nw, nh)); mask = cv2.warpAffine(mask, M, (nw, nh), flags=cv2.INTER_NEAREST)
    if nw >= W or nh >= H: return None
    x, y = rng.randint(0, W - nw), rng.randint(0, H - nh)
    ys, xs = np.where(mask > 0)
    if len(xs) < 50: return None
    a = cv2.GaussianBlur(mask.astype(np.float32), (5, 5), 0)[..., None]
    roi = bg[y:y + nh, x:x + nw].astype(np.float32)
    bg[y:y + nh, x:x + nw] = (roi * (1 - a) + obj.astype(np.float32) * a).astype(np.uint8)
    return bg, (x + xs.min(), y + ys.min(), x + xs.max(), y + ys.max())


def build_composites(bgs: list[np.ndarray], cutouts: dict[str, list]) -> Counter:
    stats = Counter(); rng = random.Random(SEED)
    pool = [(c, o, m) for c, lst in cutouts.items() for o, m in lst]
    weights = {"pcb": 3, "screw": 3, "glass": 1, "plastic_container": 1, "cardboard": 1}
    if not bgs or not pool: print("[composites] nothing to paste"); return stats
    print(f"[composites] {len(bgs)} backgrounds × cut-outs { {c: len(v) for c, v in cutouts.items()} }")
    for i in range(N_COMPOSITES):
        bg = bgs[rng.randrange(len(bgs))].copy(); boxes = []
        for _ in range(rng.randint(1, 4)):
            c, o, m = rng.choices(pool, weights=[weights.get(p[0], 1) for p in pool])[0]
            r = paste(bg, o, m, rng)
            if r: bg, (x1, y1, x2, y2) = r; boxes.append((c, x1, y1, x2, y2))
        if boxes and write_sample(f"comp_{i:04d}", "train", bg, boxes):
            for b in boxes: stats[("train", b[0])] += 1
    return stats


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    for sub in ("images", "labels"):
        for sp in ("train", "val", "test"): (DS / sub / sp).mkdir(parents=True, exist_ok=True)
    cutouts: dict[str, list] = defaultdict(list); bgs: list[np.ndarray] = []
    total = Counter(); per_source = {}
    for name, fn in [("lvis", lambda: build_lvis(bgs)), ("taco", build_taco), ("trashnet", lambda: build_trashnet(cutouts)),
                     ("pcb", lambda: build_pcb(cutouts)), ("screw", lambda: build_screws(cutouts)),
                     ("composites", lambda: build_composites(bgs, cutouts))]:
        st = fn(); per_source[name] = {f"{sp}/{c}": n for (sp, c), n in sorted(st.items())}; total += st
        print(f"[{name}] instances: {sum(st.values())}")
    imgs = {sp: len(list((DS / "images" / sp).glob("*.jpg"))) for sp in ("train", "val", "test")}
    rows = [(c, total[("train", c)], total[("val", c)], total[("test", c)]) for c in NAMES.values()]
    md = ["# Dataset sources — v0-public (generated by build_public_dataset.py)", "",
          "Boxes per class and split (instances, not images). Composites are train-only. Classes with 0/0/0 have no public data yet.", "",
          "| class | train | val | test |", "|---|---|---|---|"] + [f"| {c} | {a} | {b} | {d} |" for c, a, b, d in rows] + [
          "", f"Images: train {imgs['train']} · val {imgs['val']} · test {imgs['test']} (val/test contain no composites).", "",
          "Licences: LVIS annotations CC BY 4.0 (COCO images: Flickr, various CC); TACO CC BY 4.0; TrashNet research use (Yang & Thung);",
          "MVTec AD screw CC BY-NC-SA 4.0 (non-commercial); SanderGi cropped PCBs: no licence declared on Hugging Face.",
          "", "Caveats: `screw` and `pcb` val/test images are single-object studio shots, so their AP reflects recognition more than",
          "localisation in clutter; the other classes are evaluated on real scenes (LVIS/TACO). Nothing here was hand-checked box by box."]
    (DS / "SOURCES.md").write_text("\n".join(md) + "\n")
    json.dump({"images": imgs, "instances": {f"{sp}/{c}": n for (sp, c), n in sorted(total.items())}, "per_source": per_source},
              open(DS / "stats.json", "w"), indent=2)
    print("\n".join(md))


if __name__ == "__main__":
    main()
