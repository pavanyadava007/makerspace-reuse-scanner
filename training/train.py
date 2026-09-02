"""Fine-tune YOLO11n. Small dataset → freeze backbone first 10 layers, strong aug, early stop.
Env overrides (for smoke tests / CI only, defaults are the real recipe): MRS_EPOCHS, MRS_IMGSZ, MRS_BATCH, MRS_DEVICE."""
import os

from ultralytics import YOLO

RUNS = os.path.abspath("runs")  # absolute: a relative `project` is nested under runs/detect/ by ultralytics ≥ 8.4
m = YOLO("yolo11n.pt")
m.train(data="data.yaml", epochs=int(os.getenv("MRS_EPOCHS", 80)), imgsz=int(os.getenv("MRS_IMGSZ", 640)),
        batch=int(os.getenv("MRS_BATCH", 16)), device=os.getenv("MRS_DEVICE", None), freeze=10, patience=15,
        mosaic=1.0, mixup=0.1, hsv_v=0.5, degrees=10, fliplr=0.5,
        project=RUNS, name="yolo11n_makerspace", exist_ok=True, seed=0, deterministic=True)
