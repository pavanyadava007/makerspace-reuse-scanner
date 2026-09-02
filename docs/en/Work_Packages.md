# Work packages - Makerspace Reuse Scanner

| WP | Title | Scope | Deliverable | Effort |
|---|---|---|---|---|
| WP1 | Data collection & annotation | ≥ 600 own photos (Pi Cam 3, 3 lighting setups), TACO/TrashNet subset, Label Studio project, session-based split | `training/dataset/`, `label_studio_config.xml` | 5 PD |
| WP2 | Detector | YOLO11n fine-tune, ONNX/TensorRT export, test-split evaluation, confusion matrix | `models/*.onnx`, `training/reports/eval_*.md` | 4 PD |
| WP3 | Edge node | OpenCV capture, ONNX Runtime inference, device-labelled FPS, WebSocket client, arm64 image | `edge/`, `edge/results/bench_*.json` | 3 PD |
| WP4 | Material stage | Zero-shot CLIP, optional Qwen2.5-VL, class-prior fallback with backend tag | `vlm/`, `api/app/services/material.py` | 2 PD |
| WP5 | Data model & API | PostgreSQL + pgvector, Alembic, FastAPI REST + WebSocket, dedupe, tests | `api/` | 4 PD |
| WP6 | Frontend | React/Vite: live overlay, inventory table, item detail with editing | `web/` | 4 PD |
| WP7 | Knowledge base | German disposal-rule corpus, chunking, Ollama embeddings, cited RAG, material-process graph | `rag/`, `/api/ask`, `/api/items/{id}/suggest` | 3 PD |
| WP8 | Ops & docs | Docker Compose, GitHub Actions, bilingual README, ADRs, status reports, demo video | repo root, `docs/` | 3 PD |

Dependencies: WP2 ← WP1; WP3 ← WP2; WP5 ← WP4; WP6 ← WP5; WP7 ← WP5; WP8 ← all.
Risks: small dataset (freeze backbone, strong augmentation, honest mAP); Pi 5 latency (measure imgsz 416, send every n-th frame); RAG hallucination (context-only answers, citations, temperature 0.2).
