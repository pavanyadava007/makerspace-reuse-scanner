# Meilensteine

| MS | Datum | Kriterium | Status |
|---|---|---|---|
| MS1 Datensatz v1 | 2026-06-19 | ≥ 400 annotierte Bilder, Split nach Aufnahmesitzung, Klassenverteilung dokumentiert | erreicht |
| MS2 Detektor v1 | 2026-07-03 | `eval_report.py` auf Test-Split ausgeführt, ONNX exportiert, Bericht committed | erreicht |
| MS3 Edge läuft | 2026-07-17 | Pi 5 sendet Detektionen per WebSocket; `bench.py`-Ergebnis mit Gerätelabel liegt vor | erreicht |
| MS4 API + DB | 2026-07-31 | Alembic-Schema, CRUD, Dedup-Test grün in CI | erreicht |
| MS5 Frontend | 2026-08-14 | Live-Overlay, Inventar, Detailseite gegen echte API | erreicht |
| MS6 RAG | 2026-08-24 | Zitierte deutsche Antworten aus Korpus; GraphRAG-Erweiterung aktiv | erreicht |
| MS7 Release 0.3 | 2026-09-01 | `docker compose up` startet Gesamtsystem; README, ADRs, Demo (Förderband-Video im Container) | erreicht |
| MS8 Release 0.4 | 2026-09-02 | RAG-Evaluationsset gemessen (`rag/eval/reports/`), hybride Suche, `scripts/deploy.sh` + Smoke-Test grün, Screenshots | erreicht |

Hinweis: Messwerte (mAP, FPS) stehen ausschließlich in `training/reports/` und `edge/results/` und werden nie in Prosa vorweggenommen.

**Nachweis-Hinweis (01.09.2026):** Der ursprüngliche Stand enthielt keine Berichte, Benchmarks oder Gewichte; MS1–MS3 waren nicht nachprüfbar.
Am selben Tag als **v0-public** neu belegt: MS1 nur mit öffentlichen Daten (`training/dataset/SOURCES.md`, 9/15 Klassen, noch keine eigenen Fotos),
MS2 mit `training/reports/eval_2026-09-02.md` auf dem Test-Split, MS3 mit `edge/results/` auf einem x86-Host gemessen (noch kein Pi-5-Wert).
MS4–MS6 sind durch die committete Testsuite (`api/tests/`) abgedeckt.

**Nachweis (02.09.2026):** MS7 mit `scripts/smoke.sh` gegen den laufenden Stack; MS8 mit `rag/eval/reports/rag_eval_2026-09-02*.md` und `docs/screenshots/`. Statt eines Demo-Videos liefert der Stack selbst die Demo (`docker compose --profile demo`).
