# Statusbericht 3 — 24.08.2026

**Berichtszeitraum:** 21.07.–24.08.2026 · **Phase:** AP4–AP7 abgeschlossen, AP8 laufend

## Erledigt
- FastAPI mit REST (Inventar, Materialien, Statistik) und zwei WebSocket-Endpunkten (Edge-Ingest, Browser-Live); Tests inkl. Dedup grün in GitHub Actions.
- React-Frontend: Live-Overlay mit materialfarbigen Boxen, Inventartabelle mit Filtern, Detailseite mit Bearbeitung und Reuse-Vorschlag.
- RAG: fünf Korpusdokumente (DE/EN) nach Überschriften gechunkt, `nomic-embed-text` in pgvector, Llama 3.1 8B via Ollama, Antworten mit [n]-Zitaten; GraphRAG-Erweiterung über Material-Prozess-Graph.
- Materialstufe: CLIP-Zero-Shot als Standard, Qwen2.5-VL-3B bei GPU, Fallback Klassen-Prior — Backend wird pro Detektion gespeichert.

## Erkenntnisse
- Ohne Kontext-Beschränkung halluzinierte das LLM Entsorgungsregeln → System-Prompt auf „nur Kontext, sonst sagen“ verschärft.
- CLIP verwechselt PLA/PETG; Materialklasse daher als editierbar im Frontend ausgeführt.

## Nächste Schritte (bis 01.09.)
- Demo-Video (3 min), README-Finalisierung, ADR-0004.
- Offene Frage: Qualitätsmetrik für RAG (geplant: 20 handgeprüfte Fragen, Trefferquote der Quellen).
