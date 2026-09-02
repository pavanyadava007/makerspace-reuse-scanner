import os

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Detection, Image
from app.schemas import DetectionOut

r = APIRouter(prefix="/api", tags=["detections"])

@r.get("/detections", response_model=list[DetectionOut])
def recent(db: Session = Depends(get_db), limit: int = Query(50, le=500), item_id: int | None = None):
    q = select(Detection).order_by(Detection.created_at.desc()).limit(limit)
    if item_id: q = q.where(Detection.item_id == item_id)
    return list(db.scalars(q))

@r.get("/images/{image_id}")
def image(image_id: int, db: Session = Depends(get_db)):
    img = db.get(Image, image_id)
    if not img: raise HTTPException(404, "image not found")
    if not os.path.isfile(img.path): raise HTTPException(404, "image file missing on disk")
    return FileResponse(img.path, media_type="image/jpeg")
