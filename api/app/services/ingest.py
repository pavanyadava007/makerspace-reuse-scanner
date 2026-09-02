"""Persist an edge frame: image → detections → dedupe into inventory items."""
from __future__ import annotations

import base64
import os
import time
from collections import Counter
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Detection, Image, Item, Material
from app.services.material import classify


def save_frame(db: Session, msg: dict, location: str = "bench-1") -> list[Detection]:
    os.makedirs(settings.image_dir, exist_ok=True)
    path = os.path.join(settings.image_dir, f"{int(time.time()*1000)}.jpg")
    with open(path, "wb") as f: f.write(base64.b64decode(msg["frame"]))
    img = Image(path=path, width=msg.get("width"), height=msg.get("height"), device=msg.get("device"))
    db.add(img); db.flush()
    mats = {m.name: m for m in db.scalars(select(Material))}
    dets = msg.get("detections", [])
    per_cls = Counter(d["cls"] for d in dets)  # N boxes of one class in ONE frame = N physical objects
    out = []
    for d in dets:
        attr = classify(d["cls"], d.get("crop"))
        item = _find_or_create_item(db, d["cls"], attr, mats, location, img.id, per_cls[d["cls"]])
        det = Detection(image_id=img.id, item_id=item.id, cls=d["cls"], conf=d["conf"],
                        x1=d["xyxy"][0], y1=d["xyxy"][1], x2=d["xyxy"][2], y2=d["xyxy"][3],
                        material_pred=attr.get("material"), material_conf=attr.get("material_conf"),
                        condition_pred=attr.get("condition"), vlm_backend=attr.get("backend"),
                        infer_ms=msg.get("infer_ms"), fps=msg.get("fps"), device=msg.get("device"))
        db.add(det); out.append(det)
    db.commit(); return out

def _find_or_create_item(db, cls, attr, mats, location, image_id, count_in_frame: int = 1) -> Item:
    """Dedupe rule: same label + location seen within `dedupe_window_s` → same item.

    A re-detection refreshes `updated_at`, so an object that stays in view keeps mapping to ONE item
    (the window is measured from the last sighting, not from creation). Quantity is the largest
    number of same-class boxes seen in a single frame - repeated frames of one object never inflate it.
    """
    now = datetime.now(timezone.utc)
    since = now - timedelta(seconds=settings.dedupe_window_s)
    recent = db.scalar(select(Item).where(Item.label == cls, Item.location == location, Item.updated_at >= since)
                       .order_by(Item.updated_at.desc()).limit(1))
    if recent:
        recent.updated_at = now
        if count_in_frame > recent.quantity: recent.quantity = count_in_frame
        db.flush(); return recent
    mat = mats.get(attr.get("material") or "")
    item = Item(label=cls, material_id=mat.id if mat else None, condition=attr.get("condition"),
                location=location, first_image_id=image_id, quantity=max(1, count_in_frame))
    db.add(item); db.flush(); return item
