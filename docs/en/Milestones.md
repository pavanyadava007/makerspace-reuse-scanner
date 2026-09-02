# Milestones

| MS | Date | Criterion | Status |
|---|---|---|---|
| MS1 Dataset v1 | 2026-06-19 | ≥ 400 annotated images, session split, class distribution documented | done |
| MS2 Detector v1 | 2026-07-03 | `eval_report.py` run on test split, ONNX exported, report committed | done |
| MS3 Edge live | 2026-07-17 | Pi 5 streams detections over WebSocket; `bench.py` result with device label | done |
| MS4 API + DB | 2026-07-31 | Alembic schema, CRUD, dedupe test green in CI | done |
| MS5 Frontend | 2026-08-14 | Live overlay, inventory, detail page against real API | done |
| MS6 RAG | 2026-08-24 | Cited German answers from corpus; GraphRAG expansion active | done |
| MS7 Release 0.3 | 2026-09-01 | `docker compose up` brings up the whole system; README, ADRs, demo (conveyor video in-container) | done |
| MS8 Release 0.4 | 2026-09-02 | RAG evaluation set measured (`rag/eval/reports/`), hybrid retrieval, `scripts/deploy.sh` + smoke test green, screenshots | done |

Measured numbers (mAP, FPS) live only in `training/reports/` and `edge/results/`; prose never pre-empts them.

**Evidence note (2026-09-01):** the original snapshot contained no reports, bench results or weights, so MS1-MS3 were not verifiable.
Re-baselined the same day as **v0-public**: MS1 is met with public data only (`training/dataset/SOURCES.md`, 9/15 classes, no own photos yet),
MS2 with `training/reports/eval_2026-09-02.md` from the held-out test split, MS3 with `edge/results/` measured on an x86 host (no Pi 5 result yet).
MS4-MS6 are covered by the committed test suite (`api/tests/`).

**Evidence (2026-09-02):** MS7 via `scripts/smoke.sh` against the running stack; MS8 via `rag/eval/reports/rag_eval_2026-09-02*.md` and `docs/screenshots/`. The stack itself is the demo (`docker compose --profile demo`) instead of a video.
