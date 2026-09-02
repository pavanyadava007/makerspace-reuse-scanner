from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Detection, Item, Material
from app.schemas import ItemCreate, ItemDetail, ItemOut, ItemPatch, MaterialOut

r = APIRouter(prefix="/api", tags=["inventory"])

@r.get("/items", response_model=list[ItemOut])
def list_items(db: Session = Depends(get_db), status: str | None = None, label: str | None = None,
               material: str | None = None, limit: int = Query(100, le=500), offset: int = 0):
    q = select(Item).order_by(Item.updated_at.desc()).limit(limit).offset(offset)
    if status: q = q.where(Item.status == status)
    if label: q = q.where(Item.label == label)
    if material: q = q.join(Material).where(Material.name == material)
    return list(db.scalars(q).unique())

@r.get("/items/{item_id}", response_model=ItemDetail)
def get_item(item_id: int, db: Session = Depends(get_db)):
    it = db.get(Item, item_id)
    if not it: raise HTTPException(404, "item not found")
    return it

@r.post("/items", response_model=ItemOut, status_code=201)
def create_item(body: ItemCreate, db: Session = Depends(get_db)):
    it = Item(**body.model_dump()); db.add(it); db.commit(); db.refresh(it); return it

@r.patch("/items/{item_id}", response_model=ItemOut)
def patch_item(item_id: int, body: ItemPatch, db: Session = Depends(get_db)):
    it = db.get(Item, item_id)
    if not it: raise HTTPException(404, "item not found")
    for k, v in body.model_dump(exclude_none=True).items(): setattr(it, k, v)
    db.commit(); db.refresh(it); return it

@r.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: int, db: Session = Depends(get_db)):
    it = db.get(Item, item_id)
    if not it: raise HTTPException(404, "item not found")
    db.delete(it); db.commit()

@r.get("/materials", response_model=list[MaterialOut])
def materials(db: Session = Depends(get_db)): return list(db.scalars(select(Material).order_by(Material.name)))

@r.get("/stats")
def stats(db: Session = Depends(get_db)):
    by_status = dict(db.execute(select(Item.status, func.sum(Item.quantity)).group_by(Item.status)).all())
    by_label = dict(db.execute(select(Item.label, func.count()).group_by(Item.label)
                               .order_by(func.count().desc()).limit(10)).all())
    by_category = dict(db.execute(select(Material.category, func.count()).join(Item, Item.material_id == Material.id)
                                  .group_by(Material.category).order_by(func.count().desc())).all())
    return {"by_status": by_status, "top_labels": by_label, "by_category": by_category,
            "items": db.scalar(select(func.count(Item.id))), "detections": db.scalar(select(func.count(Detection.id)))}
