# Arbeitspakete (AP) — Makerspace Reuse Scanner

| AP | Titel | Inhalt | Ergebnis (Deliverable) | Aufwand |
|---|---|---|---|---|
| AP1 | Datenerhebung & Annotation | ≥ 600 eigene Fotos (Pi Cam 3, 3 Lichtsituationen), TACO/TrashNet-Teilmenge, Label-Studio-Projekt, Session-basierter Split | `training/dataset/`, `label_studio_config.xml`, Datensatz-README | 5 PT |
| AP2 | Detektor | YOLO11n-Finetuning, Export ONNX/TensorRT, Evaluation auf Test-Split, Confusion-Matrix | `models/yolo11n_makerspace.onnx`, `training/reports/eval_*.md` | 4 PT |
| AP3 | Edge-Knoten | OpenCV-Capture, ONNX-Runtime-Inferenz, Geräte-gelabelte FPS-Messung, WebSocket-Client, Docker-Image für arm64 | `edge/`, `edge/results/bench_*.json` | 3 PT |
| AP4 | Materialstufe | Zero-Shot-CLIP, optional Qwen2.5-VL, Fallback Klassen-Prior mit Backend-Kennzeichnung | `vlm/`, `api/app/services/material.py` | 2 PT |
| AP5 | Datenmodell & API | PostgreSQL + pgvector, Alembic-Migration, FastAPI REST + WebSocket, Dedup-Logik, Tests | `api/` | 4 PT |
| AP6 | Frontend | React/Vite: Live-Ansicht mit Overlay, Inventartabelle, Detailseite mit Bearbeitung | `web/` | 4 PT |
| AP7 | Wissensbasis | Korpus deutscher Entsorgungsregeln, Chunking, Ollama-Embeddings, RAG mit Quellenangabe, Material-Prozess-Graph | `rag/`, `/api/ask`, `/api/items/{id}/suggest` | 3 PT |
| AP8 | Betrieb & Doku | Docker Compose, GitHub Actions, zweisprachiges README, ADRs, Statusberichte, Demo-Video | Repo-Root, `docs/` | 3 PT |

Abhängigkeiten: AP2 ← AP1; AP3 ← AP2; AP5 ← AP4; AP6 ← AP5; AP7 ← AP5; AP8 ← alle.
Risiken: geringe Datenmenge (Mitigation: Freeze-Backbone, starke Augmentation, ehrliche mAP-Angabe); Pi-5-Latenz (Mitigation: imgsz 640 → 416 messen, nur jeden n-ten Frame senden); Halluzination im RAG (Mitigation: Antwort nur aus Kontext, Zitate, Temperatur 0.2).
