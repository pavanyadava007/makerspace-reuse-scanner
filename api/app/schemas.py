from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MaterialOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; name: str; category: str; recyclable: bool; disposal_de: str | None

class DetectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; image_id: int; cls: str; conf: float
    x1: float | None; y1: float | None; x2: float | None; y2: float | None
    material_pred: str | None; material_conf: float | None; condition_pred: str | None; vlm_backend: str | None
    infer_ms: float | None; fps: float | None; device: str | None; created_at: datetime

class SuggestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; text: str; sources: list | None; model: str | None; created_at: datetime

class ItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int; label: str; condition: str | None; quantity: int; location: str | None; status: str
    first_image_id: int | None; created_at: datetime; updated_at: datetime
    material: MaterialOut | None

class ItemDetail(ItemOut):
    detections: list[DetectionOut]; suggestions: list[SuggestionOut]

class ItemPatch(BaseModel):
    condition: str | None = None; quantity: int | None = None; location: str | None = None; status: str | None = None
    material_id: int | None = None

class ItemCreate(BaseModel):
    label: str; material_id: int | None = None; condition: str | None = None; quantity: int = 1; location: str | None = None

class AskIn(BaseModel):
    question: str; lang: str = "de"; k: int = 4

class AskOut(BaseModel):
    answer: str; sources: list[dict]; model: str
