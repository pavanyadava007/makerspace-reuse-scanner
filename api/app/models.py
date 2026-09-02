from __future__ import annotations

from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase): pass

class Material(Base):
    __tablename__ = "material"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)
    category: Mapped[str] = mapped_column(String(32))
    recyclable: Mapped[bool] = mapped_column(Boolean, default=True)
    disposal_de: Mapped[str | None] = mapped_column(String(128))

class Image(Base):
    __tablename__ = "image"
    id: Mapped[int] = mapped_column(primary_key=True)
    path: Mapped[str] = mapped_column(String(256))
    width: Mapped[int | None]; height: Mapped[int | None]
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    device: Mapped[str | None] = mapped_column(String(96))

class Item(Base):
    __tablename__ = "item"
    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(String(64), index=True)
    material_id: Mapped[int | None] = mapped_column(ForeignKey("material.id", ondelete="SET NULL"))
    condition: Mapped[str | None] = mapped_column(String(32))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    location: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), default="available")
    first_image_id: Mapped[int | None] = mapped_column(ForeignKey("image.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    material: Mapped[Material | None] = relationship(lazy="joined")
    detections: Mapped[list[Detection]] = relationship(back_populates="item", lazy="selectin", order_by="Detection.created_at.desc()")
    suggestions: Mapped[list[ReuseSuggestion]] = relationship(lazy="selectin", order_by="ReuseSuggestion.created_at.desc()")

class Detection(Base):
    __tablename__ = "detection"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    image_id: Mapped[int] = mapped_column(ForeignKey("image.id", ondelete="CASCADE"))
    item_id: Mapped[int | None] = mapped_column(ForeignKey("item.id", ondelete="SET NULL"), index=True)
    cls: Mapped[str] = mapped_column(String(64)); conf: Mapped[float]
    x1: Mapped[float | None]; y1: Mapped[float | None]; x2: Mapped[float | None]; y2: Mapped[float | None]
    material_pred: Mapped[str | None] = mapped_column(String(64)); material_conf: Mapped[float | None]
    condition_pred: Mapped[str | None] = mapped_column(String(32)); vlm_backend: Mapped[str | None] = mapped_column(String(32))
    infer_ms: Mapped[float | None]; fps: Mapped[float | None]; device: Mapped[str | None] = mapped_column(String(96))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    item: Mapped[Item | None] = relationship(back_populates="detections")

class ReuseSuggestion(Base):
    __tablename__ = "reuse_suggestion"
    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("item.id", ondelete="CASCADE"), index=True)
    text: Mapped[str] = mapped_column(Text); sources: Mapped[list | None] = mapped_column(JSON)
    model: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class RagChunk(Base):
    __tablename__ = "rag_chunk"
    id: Mapped[int] = mapped_column(primary_key=True)
    doc: Mapped[str] = mapped_column(String(128), index=True); section: Mapped[str | None] = mapped_column(String(256))
    lang: Mapped[str | None] = mapped_column(String(2)); text: Mapped[str] = mapped_column(Text)
    embedding = mapped_column(Vector(768))
