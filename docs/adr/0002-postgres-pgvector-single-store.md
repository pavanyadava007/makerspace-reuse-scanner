# ADR-0002: PostgreSQL + pgvector as the single store (inventory and RAG chunks)
Date: 2026-07-22 · Status: accepted

## Context
Need relational inventory (item ↔ material ↔ detection ↔ image ↔ suggestion) plus vector retrieval for the knowledge base.

## Decision
One PostgreSQL 16 instance with the pgvector extension; Alembic migrations; HNSW index with cosine distance on `rag_chunk.embedding` (768-d, nomic-embed-text). Detections are deduplicated into items by (label, location, 20 s window measured from the item's *last sighting*: every re-detection refreshes `updated_at`). Quantity is the largest number of same-class boxes seen in one frame, so repeated frames of one object never inflate it.

## Alternatives
- Separate vector DB (Chroma/Qdrant): extra service, no transactional link between suggestion and source rows.
- SQLite: no pgvector, no concurrent writers from edge ingest + UI.

## Consequences
- Single backup/migration path; `docker compose` stays at four services.
- Dedupe heuristic is simple; a tracker (ByteTrack) would be the next step if multi-object scenes cause duplicate items.
