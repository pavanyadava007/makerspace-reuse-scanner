import base64
import json

import numpy as np
from app.db import SessionLocal
from app.models import Material


def _jpeg():
    import io

    from PIL import Image
    b = io.BytesIO(); Image.fromarray(np.zeros((32, 32, 3), np.uint8)).save(b, "JPEG")
    return base64.b64encode(b.getvalue()).decode()

def test_health(client): assert client.get("/healthz").json() == {"ok": True}

def test_item_crud(client):
    with SessionLocal() as db:
        if not db.query(Material).filter_by(name="steel").first():
            db.add(Material(name="steel", category="metal", recyclable=True)); db.commit()
    r = client.post("/api/items", json={"label": "screw", "quantity": 12}); assert r.status_code == 201
    i = r.json()["id"]
    assert client.patch(f"/api/items/{i}", json={"status": "reused"}).json()["status"] == "reused"
    assert client.get(f"/api/items/{i}").json()["detections"] == []
    st = client.get("/api/stats").json()
    assert {"by_status", "top_labels", "by_category", "items", "detections"} <= set(st)
    assert client.delete(f"/api/items/{i}").status_code == 204

def test_edge_ws_ingest_and_dedupe(client):
    frame = {"type": "frame", "device": "test-cpu", "fps": 9.0, "infer_ms": 80.0, "width": 32, "height": 32, "frame": _jpeg(),
             "detections": [{"cls": "screw", "conf": 0.9, "xyxy": [1, 1, 10, 10], "crop": None}]}
    with client.websocket_connect("/ws/live") as viewer, client.websocket_connect("/ws/edge") as edge:
        assert json.loads(viewer.receive_text())["type"] == "status"
        edge.send_text(json.dumps({"type": "hello", "device": "test-cpu", "providers": ["CPUExecutionProvider"]}))
        assert json.loads(viewer.receive_text())["edges"]["test-cpu"]
        edge.send_text(json.dumps(frame)); edge.send_text(json.dumps(frame))
        a = json.loads(viewer.receive_text()); b = json.loads(viewer.receive_text())
        assert a["type"] == "frame" and a["detections"][0]["material"] == "steel"
        assert a["detections"][0]["item_id"] == b["detections"][0]["item_id"]  # deduped into one inventory item
