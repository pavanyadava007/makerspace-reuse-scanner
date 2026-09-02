# ADR-0004: Local LLM (Ollama) with citation-only RAG and graph expansion
Date: 2026-08-20 · Status: accepted

## Context
Reuse/disposal advice must follow German rules (ElektroG, BattG, AltholzV, local Wertstoffhof practice) and must not be invented. Data stays on-premise.

## Decision
Ollama serves `nomic-embed-text` (embeddings) and `llama3.1:8b` (generation). Corpus is markdown chunked by heading; prompt restricts the model to the retrieved context and requires [n] citations; temperature 0.2. Retrieval is expanded with neighbours from a small material↔process graph (`rag/graph.py`) - a lightweight GraphRAG.

## Alternatives
- Hosted API: violates on-prem requirement, costs per query.
- Full GraphRAG (community summaries): overkill for a five-document corpus.

## Consequences
- Answer quality bounded by corpus; the corpus is versioned and reviewed like code.
- Evaluation plan: 20 hand-verified questions, measure source hit-rate and manual correctness.

## Addendum 2026-09-02: evaluation done, retrieval made hybrid
The planned evaluation exists: `rag/eval/questions.yaml` (25 hand-verified questions: 20 corpus DE/EN, 3 out-of-corpus, 2 live-inventory)
and `rag/eval/run_rag_eval.py`, which measures against the live API and writes `rag/eval/reports/`. The first run (vector-only) missed the
only chunks containing the rare literal terms "Kamin" and "PVC"; with the chunk absent, the model invented a justification despite the
context-only prompt. Retrieval is therefore hybrid now: top-k cosine from pgvector plus up to two chunks ranked by IDF-weighted rare-term
overlap via Postgres full-text search (`lexical_ids()` in `api/app/services/rag.py`), covered by `test_hybrid_retrieval_finds_rare_literal_terms`.
Both reports are committed (baseline tagged `_vector-only`). Numbers live only there.
