# Statusbericht 4 - 02.09.2026

**Berichtszeitraum:** 25.08.-02.09.2026 · **Phase:** AP8 abgeschlossen, Release 0.4 (Gesamtsystem lauffähig und nachprüfbar)

## Erledigt
- **Detektor v0-public** (AP1/AP2): Datensatz aus öffentlichen Quellen (`training/build_public_dataset.py`, Zählungen und Lizenzen in `training/dataset/SOURCES.md`), YOLO11n-Finetuning auf der L4, Auswertung auf dem Test-Split (`training/reports/eval_2026-09-02.md`, mit handgeschriebenem Schwächen-Abschnitt nach Sichtung der Confusion-Matrix), ONNX-Export, Bench mit Gerätelabel (`edge/results/`). 9 von 15 Klassen haben Daten; die 6 makerspace-spezifischen Klassen bleiben leer, bis eigene Fotos vorliegen.
- **GUI v0.4** (AP6): Ask-Seite, System-Seite (Modellkarte aus dem committeten Bericht, Datenablage, Reset), Demo-Quelle (eingebaute/hochgeladene Videos laufen im Container durch den echten Detektor), Bestandsdiagramme, Filter/Sortierung, Detailseite mit klickbarer Detektionshistorie (auf die letzten 200 Sichtungen begrenzt).
- **RAG-Evaluation** (AP7, offener Punkt aus Bericht 3): 25 handgeprüfte Fragen (`rag/eval/questions.yaml`: 20 Korpusfragen DE/EN, 3 Fragen außerhalb des Korpus, 2 Bestandsfragen) und ein Runner (`rag/eval/run_rag_eval.py`), der gegen die laufende API misst und Berichte schreibt. Erste Messung (nur Vektorsuche) zeigte zwei Retrieval-Fehlschläge bei seltenen Literalen („Kamin", „PVC"); daraufhin **hybride Suche** (pgvector + Postgres-Volltext, IDF-gewichtet) eingebaut und mit Test abgesichert. Beide Berichte liegen in `rag/eval/reports/` (Baseline `_vector-only`, danach der aktuelle Stand).
- **Betrieb** (AP8): `scripts/deploy.sh` (ein Befehl: `.env`, Compose, Modell-Pull, Seed, Smoke), `scripts/smoke.sh` (Web, REST, WebSocket-Upgrade durch den Proxy, CRUD, zitierte Antwort), Screenshots aller Seiten in `docs/screenshots/`, Verifikationslog im README.

## Erkenntnisse
- Retrieval ist die eigentliche Halluzinationsbremse, nicht nur der Prompt: fehlte der Altholz-Abschnitt im Kontext, erfand das Modell trotz Kontextbeschränkung eine Begründung („giftige Dämpfe"). Mit dem richtigen Chunk zitiert es die Regel.
- Englische Frage zu beschädigten Lithiumzellen: alle drei EN-Abschnitte lagen im Kontext, das Modell zitierte aber nur die Zustandsbewertung („zur Entsorgung") und nicht die Batteriesammelbox. Als Generierungsschwäche im Bericht dokumentiert, nicht wegoptimiert.
- Ein Bewertungsfehler des Runners (Ablehnung „keinen Hinweis" nicht erkannt) wurde durch Lesen der Antworten gefunden - die Antworten stehen deshalb wörtlich im Bericht.

## Offen (nächste Iteration)
- Eigene Fotos für die 6 leeren Klassen; `battery`/`tool` mit < 100 Boxen unbrauchbar.
- Pi-5-Messung (bisher nur x86 + L4); Tracker statt Zeitfenster-Dedup; Redis-Hub bei mehreren API-Prozessen.
