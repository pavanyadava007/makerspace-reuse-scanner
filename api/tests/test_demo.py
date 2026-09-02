"""Demo-source control, model card, and inventory reset."""
import io
import json
import os

from app.config import settings
from app.db import SessionLocal
from app.models import Item


def test_demo_list_select_upload(client, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "demo_dir", str(tmp_path / "demo"))
    monkeypatch.setattr(settings, "models_dir", str(tmp_path / "models"))
    os.makedirs(tmp_path / "models"); (tmp_path / "models" / "demo_belt.mp4").write_bytes(b"x" * 2000)
    d = client.get("/api/demo").json()
    assert [v["name"] for v in d["videos"]] == ["demo_belt.mp4"] and d["videos"][0]["kind"] == "builtin"
    assert client.post("/api/demo/select", json={"video": "demo_belt.mp4"}).json()["selected"] == "/models/demo_belt.mp4"
    assert json.load(open(tmp_path / "demo" / "control.json"))["video"] == "/models/demo_belt.mp4"
    assert client.post("/api/demo/select", json={"video": "nope.mp4"}).status_code == 404
    up = client.post("/api/demo/upload", files={"file": ("my belt!.mp4", io.BytesIO(b"y" * 5000), "video/mp4")})
    assert up.status_code == 201 and up.json()["name"] == "my_belt_.mp4"
    d = client.get("/api/demo").json()
    assert any(v["kind"] == "uploaded" and v["name"] == "my_belt_.mp4" for v in d["videos"])
    client.post("/api/demo/select", json={"video": "my_belt_.mp4"})
    assert client.get("/api/demo").json()["selected"] == "/demo/uploads/my_belt_.mp4"
    assert client.post("/api/demo/select", json={"video": None}).json()["selected"] is None  # stop
    assert client.post("/api/demo/upload", files={"file": ("x.txt", io.BytesIO(b"z" * 2000), "text/plain")}).status_code == 400


def test_model_card(client, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "models_dir", str(tmp_path)); monkeypatch.setattr(settings, "reports_dir", str(tmp_path))
    (tmp_path / "yolo11n_makerspace.onnx").write_bytes(b"o")
    (tmp_path / "eval_2026-09-02.json").write_text(json.dumps({"date": "2026-09-02", "map50": 0.41, "per_class": {}}))
    c = client.get("/api/model").json()
    assert c["model"] == "yolo11n_makerspace.onnx" and c["eval"]["map50"] == 0.41


def test_admin_reset(client):
    client.post("/api/items", json={"label": "screw", "quantity": 2})
    assert client.get("/api/stats").json()["items"] >= 1
    out = client.post("/api/admin/reset").json()
    assert out["deleted"]["items"] >= 1
    with SessionLocal() as db: assert db.query(Item).count() == 0
    assert client.get("/api/stats").json() == {"by_status": {}, "top_labels": {}, "by_category": {}, "items": 0, "detections": 0}
