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

This is the project's real React GUI (Live, Inventory, item detail, Ask, System), built in "browser mode": an in-page shim replaces the
FastAPI backend, the project's own YOLO11n detector (ONNX) runs in a Web Worker with onnxruntime-web on the conveyor-belt clip, an
uploaded video or the webcam, the inventory uses the same dedupe rule as the server, and the cited DE/EN corpus is searched with the
API's lexical scoring (passages verbatim, no language model in the browser). No server, nothing leaves the browser.

Source, tests, ADRs, status reports and the full four-container stack: https://github.com/pavanyadava007/makerspace-reuse-scanner
The About tab lists what differs from the full stack and every measured number with its source file. Weights CC BY-NC-SA 4.0, code MIT.
Author: Pavan Yadav Annappa.
