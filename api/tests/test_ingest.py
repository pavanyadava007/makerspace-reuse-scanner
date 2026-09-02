"""Dedupe semantics of services/ingest.py, exercised through the /ws/edge socket."""
import json
from datetime import datetime, timedelta, timezone

from app.db import SessionLocal
from app.models import Item
from tests.test_api import _jpeg


def _frame(dets):
    return {"type": "frame", "device": "test-cpu", "fps": 9.0, "infer_ms": 80.0, "width": 32, "height": 32, "frame": _jpeg(),
            "detections": [{"cls": c, "conf": 0.9, "xyxy": [i, 1, i + 5, 10], "crop": None} for i, c in enumerate(dets)]}


def _item_ids(viewer):
    return sorted({d["item_id"] for d in json.loads(viewer.receive_text())["detections"]})


def test_quantity_is_max_per_frame_not_frame_count(client):
    with client.websocket_connect("/ws/live") as viewer, client.websocket_connect("/ws/edge") as edge:
        viewer.receive_text()
        edge.send_text(json.dumps(_frame(["nut_bolt", "nut_bolt", "nut_bolt"])))   # 3 bolts in one frame
        ids = _item_ids(viewer); assert len(ids) == 1
        for _ in range(4): edge.send_text(json.dumps(_frame(["nut_bolt", "nut_bolt"])))  # 4 more frames, 2 visible
        for _ in range(4): assert _item_ids(viewer) == ids
    with SessionLocal() as db:
        it = db.get(Item, ids[0]); assert it.quantity == 3 and len(it.detections) == 3 + 4 * 2


def test_redetection_refreshes_window(client):
    """An object that stays in view longer than the window must still map to ONE item."""
    with client.websocket_connect("/ws/live") as viewer, client.websocket_connect("/ws/edge") as edge:
        viewer.receive_text()
        edge.send_text(json.dumps(_frame(["motor"]))); (a,) = _item_ids(viewer)
        with SessionLocal() as db:  # age the item to just inside the window, as if 19 s passed since last sighting
            it = db.get(Item, a); it.updated_at = datetime.now(timezone.utc) - timedelta(seconds=19); db.commit()
        edge.send_text(json.dumps(_frame(["motor"]))); assert _item_ids(viewer) == [a]
        with SessionLocal() as db:
            assert db.get(Item, a).updated_at > datetime.now(timezone.utc) - timedelta(seconds=5)  # refreshed
        with SessionLocal() as db:  # now age it beyond the window → a new item is expected
            it = db.get(Item, a); it.updated_at = datetime.now(timezone.utc) - timedelta(seconds=60); db.commit()
        edge.send_text(json.dumps(_frame(["motor"]))); (b,) = _item_ids(viewer); assert b != a


def test_image_404(client):
    assert client.get("/api/images/999999999").status_code == 404
