# rag/
`corpus/*.md` - reuse/disposal guides (`.de.md` German, `.en.md` English), chunked by heading and embedded with `nomic-embed-text` into pgvector (`api/app/rag_ingest.py`).
`graph.py` - material↔process graph; `neighbours()` expands retrieval (lightweight GraphRAG).
Retrieval is hybrid: top-k by cosine distance in pgvector plus up to 2 chunks that share rare terms with the question (Postgres full-text
search with German/English stemming, IDF-weighted, `api/app/services/rag.py::lexical_ids`). It prefers chunks in the answer language
(`lang=de|en`) and falls back to any language if none match.
`eval/questions.yaml` - 25 hand-verified questions (corpus / out-of-corpus / live-inventory); `eval/run_rag_eval.py` runs them against a
live API and writes `eval/reports/rag_eval_<date>.md` - the only source of RAG quality numbers (`make rag-eval`).
Inside the `api` Docker image this directory lives at `/srv/rag` (see `api/Dockerfile`).
Pull models once: `docker compose exec ollama ollama pull llama3.1:8b && docker compose exec ollama ollama pull nomic-embed-text`.
