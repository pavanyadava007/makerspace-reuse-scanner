"""Publish to Hugging Face: the detector as a model repo and the Gradio demo as a Space (ZeroGPU).
    python scripts/publish_hf.py --model          # upload models/*.onnx, best.pt, classes, eval/bench reports, sources + model card
    python scripts/publish_hf.py --space          # assemble deploy/hf_space + corpus + assets in a staging dir and upload
Needs a write token (`hf auth login`). Model card lives in deploy/hf_model_card.md."""
from __future__ import annotations

import argparse
import os
import shutil
import tempfile
from pathlib import Path

from huggingface_hub import HfApi

ROOT = Path(__file__).resolve().parents[1]
USER = os.getenv("HF_USER", "pavanyadava07")
MODEL_ID, SPACE_ID = f"{USER}/makerspace-yolo11n", f"{USER}/makerspace-reuse-scanner"


def stage_model(d: Path):
    pairs = [("models/yolo11n_makerspace.onnx", "yolo11n_makerspace.onnx"),
             ("training/runs/yolo11n_makerspace/weights/best.pt", "yolo11n_makerspace.pt"),
             ("models/classes.yaml", "classes.yaml"), ("training/reports/eval_2026-09-02.md", "eval_2026-09-02.md"),
             ("training/reports/eval_2026-09-02.json", "eval_2026-09-02.json"),
             ("edge/results/bench_x86_64_+_NVIDIA_L4.json", "bench_x86_64_+_NVIDIA_L4.json"),
             ("training/dataset/SOURCES.md", "SOURCES.md"), ("deploy/hf_model_card.md", "README.md")]
    for src, dst in pairs:
        if (ROOT / src).exists(): shutil.copy(ROOT / src, d / dst)
        else: print("  missing (skipped):", src)


def stage_space(d: Path):
    for f in (ROOT / "deploy/hf_space").iterdir(): shutil.copy(f, d / f.name)
    shutil.copy(ROOT / "edge/detector.py", d / "detector.py")
    shutil.copy(ROOT / "models/classes.yaml", d / "classes.yaml")
    shutil.copy(ROOT / "training/reports/eval_2026-09-02.json", d / "eval_2026-09-02.json")
    (d / "corpus").mkdir(); [shutil.copy(f, d / "corpus" / f.name) for f in (ROOT / "rag/corpus").glob("*.md")]
    (d / "screenshots").mkdir(); [shutil.copy(f, d / "screenshots" / f.name) for f in (ROOT / "docs/screenshots").glob("*.png")]
    belt = ROOT / "models/demo_belt.mp4"
    if belt.exists():
        shutil.copy(belt, d / "demo_belt.mp4")
        import cv2
        (d / "examples").mkdir(); cap = cv2.VideoCapture(str(belt))
        for k, i in enumerate([40, 130, 220, 310, 400, 490]):
            cap.set(cv2.CAP_PROP_POS_FRAMES, i); ok, f = cap.read()
            if ok: cv2.imwrite(str(d / "examples" / f"belt_{k+1}.jpg"), f, [cv2.IMWRITE_JPEG_QUALITY, 88])
    else: print("  models/demo_belt.mp4 missing: run scripts/make_belt_video.py first")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--model", action="store_true"); ap.add_argument("--space", action="store_true")
    ap.add_argument("--hardware", default="zero-a10g"); a = ap.parse_args(); api = HfApi()
    if a.model:
        with tempfile.TemporaryDirectory() as t:
            d = Path(t); stage_model(d); api.create_repo(MODEL_ID, repo_type="model", exist_ok=True)
            r = api.upload_folder(folder_path=t, repo_id=MODEL_ID, repo_type="model", commit_message="publish_hf.py: model files + card")
            print(r.commit_url)
    if a.space:
        with tempfile.TemporaryDirectory() as t:
            d = Path(t); stage_space(d); api.create_repo(SPACE_ID, repo_type="space", space_sdk="gradio", exist_ok=True)
            r = api.upload_folder(folder_path=t, repo_id=SPACE_ID, repo_type="space", commit_message="publish_hf.py: space files")
            print(r.commit_url)
        if a.hardware:
            try: api.request_space_hardware(SPACE_ID, a.hardware); print("hardware requested:", a.hardware)
            except Exception as e: print("hardware request failed (set it in the Space settings):", e)  # noqa: BLE001
        print(f"https://huggingface.co/spaces/{SPACE_ID}")


if __name__ == "__main__": main()
