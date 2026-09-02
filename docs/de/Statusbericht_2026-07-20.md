# Statusbericht 2 - 20.07.2026

**Berichtszeitraum:** 23.06.-20.07.2026 · **Phase:** AP2-AP3 abgeschlossen, AP5 begonnen

## Erledigt
- YOLO11n finetuned; Evaluation über `eval_report.py` auf Test-Split (Zahlen: `training/reports/`).
- ONNX-Export (opset 17, statisch 640); ONNX-Runtime-Inferenz auf Pi 5 (CPU-EP) und Laptop verglichen, Ergebnisse in `edge/results/` mit Gerätelabel.
- Edge-Client sendet jeden dritten Frame mit Crops per WebSocket; Reconnect-Logik getestet.

## Erkenntnisse
- Pi 5 mit imgsz 640 ist für Live-Overlay zu langsam; imgsz 416 halbiert Latenz bei geringem mAP-Verlust → als Option dokumentiert, nicht als Standard.
- Verwechslungen `nut_bolt` ↔ `screw` dominieren die Confusion-Matrix; mehr Nahaufnahmen geplant.

## Nächste Schritte
- Datenmodell (ADR-0002) und Alembic-Migration; Dedup-Fenster 20 s.
- CI mit Postgres-Service.

## Risiken
- Zeitrisiko Frontend (neue Technologie React) → Umfang auf drei Seiten begrenzt.
