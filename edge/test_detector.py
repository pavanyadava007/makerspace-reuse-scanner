import numpy as np
from detector import nms, postprocess


def test_nms_suppresses_overlap():
    b = np.array([[0, 0, 10, 10], [1, 1, 11, 11], [50, 50, 60, 60]], float)
    s = np.array([0.9, 0.8, 0.7])
    assert nms(b, s, 0.5) == [0, 2]

def test_postprocess_scales_back():
    out = np.zeros((1, 4 + 2, 3), np.float32)
    out[0, :4, 0] = [320, 320, 100, 100]; out[0, 4, 0] = 0.9   # class 0 at centre
    dets = postprocess(out, r=0.5, pad=(0, 80), conf_thr=0.3, iou_thr=0.5)
    assert len(dets) == 1 and dets[0].cls == 0
    x1, y1, x2, y2 = dets[0].xyxy
    assert abs(x1 - 540) < 1 and abs(y1 - 380) < 1 and abs(x2 - 740) < 1


def test_settings_env_overrides(tmp_path, monkeypatch):
    from settings import load_cfg
    p = tmp_path / "c.yaml"; p.write_text("model: /models/a.onnx\ncamera: 0\nmin_conf: 0.35\nimgsz: 640\n")
    cfg = load_cfg(str(p), env={"EDGE_MODEL": "/tmp/b.onnx", "EDGE_MIN_CONF": "0.5", "EDGE_CAMERA": "rtsp://x", "EDGE_IMGSZ": ""})
    assert cfg["model"] == "/tmp/b.onnx" and cfg["min_conf"] == 0.5 and cfg["camera"] == "rtsp://x" and cfg["imgsz"] == 640
