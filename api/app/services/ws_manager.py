import json

from fastapi import WebSocket


class Hub:
    """Fan-out: edge nodes publish frames, browser clients subscribe. Per-process state (see ADR-0003)."""
    def __init__(self): self.viewers: set[WebSocket] = set(); self.edges: dict[str, dict] = {}
    async def broadcast(self, msg: dict):
        data = json.dumps(msg); dead = []
        for ws in list(self.viewers):
            try: await ws.send_text(data)
            except Exception: dead.append(ws)
        for ws in dead: self.viewers.discard(ws)
    async def send_status(self):
        await self.broadcast({"type": "status", "edges": self.edges})
hub = Hub()
