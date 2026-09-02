# Interview talking points (keep private)

**One-liner:** "Edge YOLO on a Pi feeds a FastAPI/Postgres inventory; a local VLM tags material; a cited German RAG tells you how to reuse or dispose. Four containers, one `compose up`."

**Likely questions → answers grounded in the repo**
- *Why YOLO11n over v8/RT-DETR?* ADR-0001: Pi CPU budget; same ONNX runs TensorRT on Jetson via EP fallback.
- *How do you avoid overclaiming with a small dataset?* Session-based split; mAP only from `eval_report.py` on test split; class-prior fallback is labelled, not hidden.
- *Dedupe?* (label, location, 20 s since last sighting) in `services/ingest.py`; quantity = max same-class boxes in one frame. Tested in `test_api.py` + `test_ingest.py` (window refresh, quantity). Next step: ByteTrack IDs.
- *Why does the WS test need `with TestClient(app)`?* Starlette gives each `websocket_connect` its own event loop unless the client is entered as a context manager; a cross-socket broadcast then never wakes the viewer. Real uvicorn has one loop.
- *Why pgvector and not a vector DB?* ADR-0002: one transactional store, suggestion rows reference chunk rows.
- *Hallucination control?* ADR-0004: context-only system prompt, [n] citations, T=0.2, explicit "insufficient context" path.
- *What is GraphRAG here?* `rag/graph.py` neighbours → extra retrievals (e.g. PLA → filament recycler, Restmüll). Honest framing: lightweight, not community-summary GraphRAG.
- *Scaling?* Hub is in-process → Redis pub/sub; MQTT once > 3 edge nodes (ADR-0003).
- *What broke?* Status report 2: Pi at 640 too slow → 416 measured; report 3: LLM invented rules → prompt tightened.

- *Where did the training data come from?* No own photos yet → `training/build_public_dataset.py` pulls LVIS (bolt/nut/motor/battery/tools/glass/box on COCO images), TACO (litter in context, has `Battery`), TrashNet (studio cardboard/glass/plastic, box by thresholding), a cropped-PCB set and MVTec AD screws; PCB/screw cut-outs are copy-pasted into LVIS scenes for localisation (train split only). 9/15 classes covered; the 6 makerspace-only classes are honestly at zero. Split is by session key (LVIS image, TACO batch, PCB board).
- *Weak spots you know about?* `screw`/`pcb` test images are studio shots (AP flatters them); `battery` has < 100 boxes; composites are crude for transparent objects; MVTec screws are CC BY-NC-SA (demo only).
**Do not say** numbers you have not measured. Point to `training/reports/` and `edge/results/`.
