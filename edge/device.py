"""Identify the edge device so every FPS number is labelled honestly."""
import os
import platform
import subprocess


def device_label() -> str:
    forced = os.getenv("EDGE_DEVICE", "auto")
    if forced != "auto":
        return forced
    try:
        model = open("/proc/device-tree/model").read().strip("\x00")
        if "Raspberry Pi" in model:
            return model.replace("Raspberry Pi", "RPi").strip()
        if "Jetson" in model or "NVIDIA" in model:
            return model
    except FileNotFoundError:
        pass
    try:
        gpu = subprocess.check_output(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], timeout=2).decode().strip()
        return f"{platform.machine()} + {gpu}"
    except Exception:
        return f"{platform.machine()} CPU ({platform.processor() or platform.system()})"
