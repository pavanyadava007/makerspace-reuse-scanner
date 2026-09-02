# Status report 3 - 2026-08-24 (English summary; German originals in `docs/de/`)

Period 2026-07-21 to 2026-08-24 · WP4-WP7 complete, WP8 in progress.

Done: FastAPI REST + two WebSocket endpoints with CI-tested dedupe; React frontend (live overlay, inventory, detail page with edit + reuse suggestion); RAG over five DE/EN corpus docs via pgvector + Ollama with [n] citations and graph expansion; material stage with CLIP default, Qwen2.5-VL on GPU, class-prior fallback, backend recorded per detection.

Lessons: unconstrained LLM invented disposal rules → system prompt now context-only with explicit "insufficient context" path; CLIP confuses PLA/PETG → material field editable in UI.

Next: 3-minute demo video, README polish, ADR-0004, RAG quality check with 20 hand-verified questions.
