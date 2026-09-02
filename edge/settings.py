"""Edge configuration: config.yaml with environment overrides. Importable without OpenCV/ONNX (unit-testable)."""
from __future__ import annotations

import os

import yaml

# env var → (config key, caster). Documented in .env.example and README.
ENV_OVERRIDES = {
    "EDGE_MODEL": ("model", str),
    "EDGE_CLASSES": ("classes", str),
    "EDGE_CAMERA": ("camera", str),
    "EDGE_IMGSZ": ("imgsz", int),
    "EDGE_MIN_CONF": ("min_conf", float),
    "EDGE_IOU": ("iou", float),
    "EDGE_SEND_EVERY_N": ("send_every_n", int),
    "EDGE_CROP_UPLOAD": ("crop_upload", lambda v: str(v).lower() in ("1", "true", "yes")),
}


def load_cfg(path: str | None = None, env: dict | None = None) -> dict:
    env = os.environ if env is None else env
    path = path or env.get("EDGE_CONFIG", "config.yaml")
    with open(path) as f:
        cfg = yaml.safe_load(f) or {}
    for var, (key, cast) in ENV_OVERRIDES.items():
        if env.get(var) not in (None, ""):
            cfg[key] = cast(env[var])
    return cfg
