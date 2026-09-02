# ADR-0003: FastAPI with REST for inventory and WebSocket for live detections
Date: 2026-07-25 · Status: accepted

## Context
Edge nodes push ~3 frames/s with base64 JPEG + crops; browsers need low-latency overlay; inventory is CRUD.

## Decision
`/ws/edge` (edge → API, persisted synchronously in a thread) and `/ws/live` (API → browsers, fan-out via in-memory hub). REST under `/api` for items, materials, stats, images, ask/suggest. Pydantic v2 schemas; SQLAlchemy 2.0 typed models.

## Alternatives
- MQTT broker: better for many edge nodes; adds a service — deferred until > 3 devices.
- Server-Sent Events: one-directional; edge → API still needs another channel.

## Consequences
- Hub state is per-process; horizontal scaling would need Redis pub/sub (documented, not built).
