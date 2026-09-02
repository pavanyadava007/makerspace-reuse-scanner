"""Material/condition stage. Uses vlm/ (CLIP or Qwen2.5-VL) if importable; otherwise a labelled class-prior fallback."""
from __future__ import annotations

import base64
import io
import os
import sys

from PIL import Image

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "..", "vlm"))
_backend = None
CLASS_PRIOR = {"screw": "steel", "nut_bolt": "steel", "pcb": "fiberglass PCB", "filament_spool": "PLA plastic",
               "wood_offcut": "plywood", "cable": "copper", "3d_print_part": "PLA plastic", "acrylic_sheet": "acrylic",
               "metal_profile": "aluminium", "motor": "steel", "battery": "lithium battery", "tool": "steel",
               "plastic_container": "PETG plastic", "cardboard": "cardboard", "glass": "glass",
               # bridge for the COCO-pretrained stand-in model (models/yolo11n_coco.onnx) used for webcam demos
               # before makerspace weights exist; everything else COCO detects stays "unknown".
               "bottle": "PETG plastic", "cup": "glass", "wine glass": "glass", "fork": "steel", "knife": "steel",
               "spoon": "steel", "scissors": "steel", "cell phone": "fiberglass PCB", "laptop": "fiberglass PCB",
               "keyboard": "fiberglass PCB", "mouse": "fiberglass PCB", "remote": "fiberglass PCB", "book": "cardboard",
               "chair": "solid wood", "dining table": "plywood", "bench": "solid wood", "vase": "glass"}

def _get():
    global _backend
    if _backend is None:
        try:
            from material_qwen import get_backend
            _backend = get_backend()
        except Exception:
            _backend = False
    return _backend

def classify(cls: str, crop_b64: str | None) -> dict:
    b = _get()
    if b and crop_b64:
        try:
            img = Image.open(io.BytesIO(base64.b64decode(crop_b64))).convert("RGB")
            return b(img)
        except Exception:
            pass
    return {"material": CLASS_PRIOR.get(cls, "unknown"), "material_conf": None, "condition": None, "backend": "class-prior"}
