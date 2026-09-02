---
title: Makerspace Reuse Scanner
emoji: ♻️
colorFrom: green
colorTo: blue
sdk: gradio
sdk_version: 6.26.0
app_file: app.py
pinned: false
license: mit
short_description: Edge YOLO11n reuse inventory + cited DE/EN disposal assistant
models:
  - pavanyadava07/makerspace-yolo11n
  - Qwen/Qwen2.5-7B-Instruct
  - intfloat/multilingual-e5-small
---
# Makerspace Reuse Scanner (live demo)

Detects makerspace parts and offcuts with the project's own YOLO11n (ONNX), builds a session inventory with material and the correct German
bin per item, and answers reuse/disposal questions from a cited DE/EN knowledge base. Source, tests, ADRs, status reports and the full
four-container stack: https://github.com/pavanyadava007/makerspace-reuse-scanner

The Space's `About` tab lists what differs from the full stack and every measured number with its source file. The detector weights are
CC BY-NC-SA 4.0 (MVTec share in the training data); the code is MIT. Author: Pavan Yadav Annappa.
