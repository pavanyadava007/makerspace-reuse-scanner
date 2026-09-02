import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.db import SessionLocal
from app.services.ingest import save_frame
from app.services.ws_manager import hub

r = APIRouter()

@r.websocket("/ws/edge")
async def ws_edge(ws: WebSocket):
    await ws.accept(); device = "unknown"
    try:
        while True:
            msg = json.loads(await ws.receive_text())
            if msg["type"] == "hello":
                device = msg["device"]; hub.edges[device] = {"providers": msg.get("providers"), "model": msg.get("model"), "fps": None}
                await hub.send_status(); continue
            prev = hub.edges.get(device, {})
            hub.edges[device] = {"fps": msg["fps"], "infer_ms": msg["infer_ms"],
                                 "providers": prev.get("providers"), "model": prev.get("model")}
            dets = await asyncio.to_thread(_persist, msg)
            await hub.broadcast({"type": "frame", "device": device, "fps": msg["fps"], "infer_ms": msg["infer_ms"],
                                 "width": msg["width"], "height": msg["height"], "frame": msg["frame"],
                                 "detections": [{"cls": d.cls, "conf": d.conf, "xyxy": [d.x1, d.y1, d.x2, d.y2],
                                                 "material": d.material_pred, "item_id": d.item_id} for d in dets]})
    except WebSocketDisconnect:
        hub.edges.pop(device, None); await hub.send_status()

def _persist(msg):
    with SessionLocal() as db: return save_frame(db, msg)

@r.websocket("/ws/live")
async def ws_live(ws: WebSocket):
    await ws.accept(); hub.viewers.add(ws)
    await ws.send_text(json.dumps({"type": "status", "edges": hub.edges}))
    try:
        while True: await ws.receive_text()
    except WebSocketDisconnect:
        hub.viewers.discard(ws)
