"""Demo-source control and system info: list/select/upload demo videos, model card, inventory reset.

The demo-edge container watches `<demo_dir>/control.json` (see edge/demo_loop.py). Built-in videos live in
`<models_dir>` (host ./models, read-only); uploads go to `<demo_dir>/uploads` on a volume shared with demo-edge.
Paths written into control.json are the DEMO-EDGE container's view: /models/<name> or /demo/uploads/<name>.
"""
import glob
import json
import os
import re

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models import Detection, Image, Item, ReuseSuggestion

r = APIRouter(prefix="/api", tags=["system"])
VIDEO_EXT = (".mp4", ".avi", ".mov", ".mkv")
MAX_UPLOAD = 300 * 1024 * 1024


def _ctrl_path() -> str: return os.path.join(settings.demo_dir, "control.json")


def _videos() -> list[dict]:
    out = []
    for d, kind, edge_prefix in [(settings.models_dir, "builtin", "/models"),
                                 (os.path.join(settings.demo_dir, "uploads"), "uploaded", "/demo/uploads")]:
        if not os.path.isdir(d): continue
        for f in sorted(os.listdir(d)):
            if f.lower().endswith(VIDEO_EXT):
                out.append({"name": f, "kind": kind, "edge_path": f"{edge_prefix}/{f}",
                            "size_mb": round(os.path.getsize(os.path.join(d, f)) / 1e6, 1)})
    return out


@r.get("/demo")
def demo_status():
    sel = None
    try:
        with open(_ctrl_path()) as f: sel = json.load(f).get("video")
    except (FileNotFoundError, json.JSONDecodeError):
        sel = "/models/demo_belt.mp4"  # demo_loop default when no control file exists
    return {"videos": _videos(), "selected": sel}


class SelectIn(BaseModel):
    video: str | None  # a `name` from GET /api/demo, or null to stop


@r.post("/demo/select")
def demo_select(body: SelectIn):
    edge_path = None
    if body.video is not None:
        match = next((v for v in _videos() if v["name"] == body.video), None)
        if not match: raise HTTPException(404, "unknown video - see GET /api/demo")
        edge_path = match["edge_path"]
    os.makedirs(settings.demo_dir, exist_ok=True)
    with open(_ctrl_path(), "w") as f: json.dump({"video": edge_path}, f)
    return {"selected": edge_path}


@r.post("/demo/upload", status_code=201)
async def demo_upload(file: UploadFile):
    name = re.sub(r"[^A-Za-z0-9._-]", "_", os.path.basename(file.filename or "upload.mp4"))
    if not name.lower().endswith(VIDEO_EXT): raise HTTPException(400, f"video files only ({', '.join(VIDEO_EXT)})")
    data = await file.read()
    if len(data) > MAX_UPLOAD: raise HTTPException(413, "max 300 MB")
    if len(data) < 1000: raise HTTPException(400, "file looks empty")
    d = os.path.join(settings.demo_dir, "uploads"); os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, name), "wb") as f: f.write(data)
    return {"name": name, "size_mb": round(len(data) / 1e6, 1)}


@r.get("/model")
def model_card():
    """Detector facts for the GUI - accuracy comes ONLY from the committed eval report (honesty rule)."""
    models = sorted(glob.glob(os.path.join(settings.models_dir, "*.onnx"))) if os.path.isdir(settings.models_dir) else []
    ev = sorted(glob.glob(os.path.join(settings.reports_dir, "eval_*.json"))) if os.path.isdir(settings.reports_dir) else []
    card = {"model": next((os.path.basename(m) for m in models if "makerspace" in m), None), "eval": None}
    if ev:
        with open(ev[-1]) as f: card["eval"] = json.load(f)
    return card


def _purge_frame_files(d: str):
    """Best-effort removal of stored JPEG frames - runs AFTER the response; tens of thousands of unlinks
    on a volume can take minutes and must never block the request (learned from a real 504)."""
    try:
        for e in os.scandir(d):
            if e.is_file():
                try: os.remove(e.path)
                except OSError: pass
    except FileNotFoundError:
        pass


@r.post("/admin/reset")
def reset_inventory(background: BackgroundTasks, db: Session = Depends(get_db)):
    """Clear the live inventory: detections, items, suggestions, image rows (frame files are purged in the
    background). Materials and the RAG corpus are kept. Use before a fresh demo run."""
    counts = {"detections": db.scalar(select(func.count(Detection.id))), "items": db.scalar(select(func.count(Item.id))),
              "images": db.scalar(select(func.count(Image.id)))}
    for t in (Detection, ReuseSuggestion, Item, Image): db.execute(delete(t))
    db.commit()
    background.add_task(_purge_frame_files, settings.image_dir)
    return {"deleted": counts}
