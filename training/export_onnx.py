import os
import shutil

from ultralytics import YOLO

m = YOLO(os.getenv("MRS_WEIGHTS", os.path.abspath("runs/yolo11n_makerspace/weights/best.pt")))
p = m.export(format="onnx", imgsz=640, opset=17, simplify=True, dynamic=False, half=False)
os.makedirs("../models", exist_ok=True)
shutil.copy(p, "../models/yolo11n_makerspace.onnx"); shutil.copy("classes.yaml", "../models/classes.yaml")
print("exported → models/yolo11n_makerspace.onnx  (Jetson: trtexec --onnx=... --fp16 for a TensorRT engine)")
