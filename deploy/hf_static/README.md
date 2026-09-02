---
title: Makerspace Reuse Scanner
emoji: ♻️
colorFrom: green
colorTo: blue
sdk: static
pinned: false
license: mit
short_description: YOLO11n reuse scanner in the browser, cited DE/EN corpus
models:
  - pavanyadava07/makerspace-yolo11n
---
# Makerspace Reuse Scanner (live, in your browser)

The project's own YOLO11n detector (ONNX, loaded from the model repo) runs in the browser with onnxruntime-web: conveyor-belt frames,
your own bench photo or the webcam, a session inventory with material and the correct German bin per item, and the cited DE/EN
knowledge base searched with the same rare-term lexical scoring the API uses. No server, nothing leaves the browser.

Source, tests, ADRs, status reports and the full four-container stack: https://github.com/pavanyadava007/makerspace-reuse-scanner
The About tab lists what differs from the full stack and every measured number with its source file. Weights CC BY-NC-SA 4.0, code MIT.
Author: Pavan Yadav Annappa.
