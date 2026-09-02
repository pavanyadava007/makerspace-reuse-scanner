# Status report 4 — 2026-09-02 (English summary; German original in `docs/de/`)

Period 2026-08-25 to 2026-09-02 · WP8 complete, release 0.4 (whole system runs and is verifiable).

Done: v0-public detector (public data, test-split report with a hand-written weaknesses section, ONNX, device-labelled bench); GUI v0.4 (Ask, System, demo source, charts, capped detection history); RAG evaluation set (25 hand-verified questions) with a runner that measures against the live API — the first vector-only run missed two chunks with rare literal terms, so retrieval is now hybrid (pgvector + Postgres full-text, IDF-weighted) and covered by a test; one-command deploy and smoke scripts; screenshots.

Lessons: retrieval, not only the prompt, is what stops hallucination (with the Altholz chunk missing the model invented "toxic fumes"); one English answer cited the condition section instead of the battery box — documented, not tuned away; a scorer bug was caught only because the answers are printed verbatim in the report.

Open: own photos for the six empty classes; Pi 5 measurement; a tracker instead of the time-window dedupe; Redis hub for multi-process API.
