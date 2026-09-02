---
license: cc-by-nc-sa-4.0
tags: [object-detection, yolo11, onnx, ultralytics, makerspace, reuse, circular-economy]
library_name: ultralytics
pipeline_tag: object-detection
model-index:
- name: yolo11n_makerspace v0-public
  results:
  - task: {type: object-detection}
    dataset: {name: "v0-public test split (LVIS/TACO/TrashNet/PCB/MVTec-screw, 497 images)", type: mixed}
    metrics:
    - {type: mAP50, value: 0.410}
    - {type: mAP50-95, value: 0.303}
    - {type: precision, value: 0.525}
    - {type: recall, value: 0.423}
---
# YOLO11n makerspace detector, v0-public

Detector of the [Makerspace Reuse Scanner](https://github.com/pavanyadava007/makerspace-reuse-scanner): a camera at the bench detects parts
and offcuts, the API keeps a reuse inventory and a cited local knowledge base answers "how do I reuse or dispose of this?".
Live demo: [Space pavanyadava07/makerspace-reuse-scanner](https://huggingface.co/spaces/pavanyadava07/makerspace-reuse-scanner).

**Files:** `yolo11n_makerspace.onnx` (static 640×640, opset 17, output 1×19×8400, runs with ONNX Runtime and NumPy pre/post-processing,
see `edge/detector.py` in the repo) · `yolo11n_makerspace.pt` (Ultralytics checkpoint) · `classes.yaml` (15 classes) ·
`eval_2026-09-02.{md,json}` (the only source of accuracy numbers) · `bench_*.json` (device-labelled throughput) · `SOURCES.md` (data + licences).

## Measured on the held-out test split (2026-09-02)
| overall | mAP50 | mAP50-95 | precision | recall |
|---|---|---|---|---|
| all classes | 0.410 | 0.303 | 0.525 | 0.423 |

| class | AP50 | AP50-95 |
|---|---|---|
| screw | 0.995 | 0.872 |
| nut_bolt | 0.226 | 0.086 |
| pcb | 0.994 | 0.917 |
| motor | 0.441 | 0.243 |
| battery | 0.030 | 0.016 |
| tool | 0.049 | 0.019 |
| plastic_container | 0.482 | 0.265 |
| cardboard | 0.179 | 0.121 |
| glass | 0.295 | 0.189 |

Read before trusting these: `screw` and `pcb` test images are single-object studio shots, so their scores flatter the model; `battery`
and `tool` have too little data to be usable; the dominant failure is missed small or distant objects, not class confusion. Six of the
15 classes (filament_spool, wood_offcut, cable, 3d_print_part, acrylic_sheet, metal_profile) have **no training data yet** and are never
predicted. Throughput: 96.09 ms median inference on an x86 CPU execution provider (`bench_*.json`); no Raspberry Pi 5 number yet.

## Training data and licence
Trained by `training/build_public_dataset.py` on public data only: LVIS on COCO images (CC BY 4.0), TACO (CC BY 4.0), TrashNet (research
use), a cropped-PCB set from Hugging Face (no licence declared) and MVTec AD screws (CC BY-NC-SA 4.0), plus train-only copy-paste composites.
Because of the MVTec share these weights are released **non-commercial, share-alike (CC BY-NC-SA 4.0)**. Recipe: YOLO11n, frozen first
10 layers, 80 epochs, imgsz 640, seed 0 (`training/train.py`).

## Use
```python
import onnxruntime as ort, numpy as np
sess = ort.InferenceSession("yolo11n_makerspace.onnx", providers=["CPUExecutionProvider"])
# input: 1×3×640×640 float32 RGB in [0,1], letterboxed; output: 1×19×8400 = (cx, cy, w, h, 15 class scores) per anchor
```
Author: Pavan Yadav Annappa · MIT for the code, CC BY-NC-SA 4.0 for these weights.
