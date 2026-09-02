"""Publish to Hugging Face: the detector as a model repo and the Gradio demo as a Space (ZeroGPU).
    python scripts/publish_hf.py --model          # upload models/*.onnx, best.pt, classes, eval/bench reports, sources + model card
    python scripts/publish_hf.py --static         # FREE static Space: deploy/hf_static (detector in the browser via onnxruntime-web)
    python scripts/publish_hf.py --space          # Gradio Space (needs a PRO plan): deploy/hf_space + corpus + assets, ZeroGPU answers
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


def transcode_h264(src: Path, dst: Path):
    """Browser-playable H.264/yuv420p copy via the ffmpeg bundled with imageio-ffmpeg; falls back to a plain copy."""
    try:
        import subprocess

        import imageio_ffmpeg
        cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-i", str(src), "-c:v", "libx264", "-pix_fmt", "yuv420p",
               "-crf", "23", "-movflags", "+faststart", "-an", str(dst)]
        subprocess.run(cmd, check=True)
    except Exception as e:  # noqa: BLE001
        print("  ffmpeg transcode failed, copying as-is:", e); shutil.copy(src, dst)


def stage_assets(d: Path):
    (d / "corpus").mkdir(); [shutil.copy(f, d / "corpus" / f.name) for f in (ROOT / "rag/corpus").glob("*.md")]
    (d / "screenshots").mkdir(); [shutil.copy(f, d / "screenshots" / f.name) for f in (ROOT / "docs/screenshots").glob("*.png")]
    belt = ROOT / "models/demo_belt.mp4"
    if belt.exists():
        transcode_h264(belt, d / "demo_belt.mp4")   # OpenCV writes MPEG-4 Part 2, which browsers cannot play
        import cv2
        (d / "examples").mkdir(); cap = cv2.VideoCapture(str(belt))
        for k, i in enumerate([40, 130, 220, 310, 400, 490]):
            cap.set(cv2.CAP_PROP_POS_FRAMES, i); ok, f = cap.read()
            if ok: cv2.imwrite(str(d / "examples" / f"belt_{k+1}.jpg"), f, [cv2.IMWRITE_JPEG_QUALITY, 88])
    else: print("  models/demo_belt.mp4 missing: run scripts/make_belt_video.py first")


def stage_space(d: Path):
    for f in (ROOT / "deploy/hf_space").iterdir(): shutil.copy(f, d / f.name)
    shutil.copy(ROOT / "edge/detector.py", d / "detector.py")
    shutil.copy(ROOT / "models/classes.yaml", d / "classes.yaml")
    shutil.copy(ROOT / "training/reports/eval_2026-09-02.json", d / "eval_2026-09-02.json")
    stage_assets(d)


def stage_static(d: Path):
    for f in (ROOT / "deploy/hf_static").iterdir(): shutil.copy(f, d / f.name)
    shutil.copy(ROOT / "models/yolo11n_makerspace.onnx", d / "yolo11n_makerspace.onnx")   # fallback copy; primary load is the model repo
    stage_assets(d)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--model", action="store_true"); ap.add_argument("--space", action="store_true")
    ap.add_argument("--static", action="store_true")
    ap.add_argument("--hardware", default="zero-a10g"); a = ap.parse_args(); api = HfApi()
    if a.model:
        with tempfile.TemporaryDirectory() as t:
            d = Path(t); stage_model(d); api.create_repo(MODEL_ID, repo_type="model", exist_ok=True)
            r = api.upload_folder(folder_path=t, repo_id=MODEL_ID, repo_type="model", commit_message="publish_hf.py: model files + card")
            print(r.commit_url)
    if a.static:
        with tempfile.TemporaryDirectory() as t:
            d = Path(t); stage_static(d); api.create_repo(SPACE_ID, repo_type="space", space_sdk="static", exist_ok=True)
            r = api.upload_folder(folder_path=t, repo_id=SPACE_ID, repo_type="space", commit_message="publish_hf.py: static demo")
            print(r.commit_url); print(f"https://huggingface.co/spaces/{SPACE_ID}")
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
