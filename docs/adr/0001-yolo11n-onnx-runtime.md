# ADR-0001: YOLO11n fine-tuned, deployed via ONNX Runtime
Date: 2026-06-24 · Status: accepted

## Context
Edge targets are a Raspberry Pi 5 (CPU, arm64) and optionally a Jetson Orin Nano (GPU). Dataset is small (< 1k images). Live overlay needs ≥ 5 FPS on the Pi.

## Decision
Fine-tune YOLO11n (2.6 M params) with a frozen backbone; export a static 640×640 ONNX graph; run with ONNX Runtime, selecting TensorRT → CUDA → CPU execution providers at runtime. Pre/post-processing (letterbox, NMS) implemented in NumPy so the edge image has no ultralytics/PyTorch dependency.

## Alternatives
- YOLOv8n: nearly identical; 11n gives better mAP at the same cost.
- RT-DETR / larger YOLO: too slow on Pi CPU.
- TFLite: worse tooling for TensorRT path; would split the deployment story.

## Consequences
- Same artifact runs on laptop, Pi and Jetson; FPS must always be labelled by device (`edge/device.py`).
- Accuracy ceiling limited by dataset size — reported honestly from the test split only.
