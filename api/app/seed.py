"""Seed material table (idempotent). Run: python -m app.seed"""
from sqlalchemy import select

from app.db import SessionLocal
from app.models import Material

ROWS = [
    ("steel", "metal", True, "Wertstoffhof / Schrott"), ("aluminium", "metal", True, "Wertstoffhof / Schrott"),
    ("copper", "metal", True, "Wertstoffhof / Schrott"), ("PLA plastic", "plastic", False, "Restmüll (nicht Gelber Sack)"),
    ("PETG plastic", "plastic", True, "Gelber Sack (nur Verpackung) / Wertstofftonne"), ("ABS plastic", "plastic", False, "Restmüll"),
    ("acrylic", "plastic", False, "Restmüll / Wertstoffhof"), ("plywood", "wood", True, "Altholz A II, Wertstoffhof"),
    ("solid wood", "wood", True, "Altholz A I"), ("MDF", "wood", True, "Altholz A II"), ("cardboard", "paper", True, "Papiertonne"),
    ("glass", "glass", True, "Glascontainer / Restmüll (Flachglas)"), ("fiberglass PCB", "composite", True, "Elektroschrott (ElektroG)"),
    ("rubber", "other", False, "Restmüll"), ("lithium battery", "hazardous", True, "Batteriesammelbox (BattG) - nie Restmüll"),
]
with SessionLocal() as db:
    have = {m.name for m in db.scalars(select(Material))}
    db.add_all([Material(name=n, category=c, recyclable=r, disposal_de=d) for n, c, r, d in ROWS if n not in have])
    db.commit(); print("materials seeded")
