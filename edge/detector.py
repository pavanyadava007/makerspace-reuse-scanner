"""ONNX Runtime YOLO11 detector: letterbox → infer → NMS. Device-agnostic."""
from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np

try:
    import onnxruntime as ort
except ImportError:  # unit tests without ORT
    ort = None


@dataclass
class Det:
    cls: int
    conf: float
    xyxy: tuple[float, float, float, float]  # original-image pixel coords


def letterbox(img: np.ndarray, size: int = 640) -> tuple[np.ndarray, float, tuple[int, int]]:
    h, w = img.shape[:2]
    r = size / max(h, w)
    nh, nw = int(round(h * r)), int(round(w * r))
    import cv2
    resized = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_LINEAR)
    canvas = np.full((size, size, 3), 114, dtype=np.uint8)
    top, left = (size - nh) // 2, (size - nw) // 2
    canvas[top:top + nh, left:left + nw] = resized
    return canvas, r, (left, top)


def nms(boxes: np.ndarray, scores: np.ndarray, iou_thr: float) -> list[int]:
    order = scores.argsort()[::-1]
    keep: list[int] = []
    while order.size:
        i = order[0]
        keep.append(int(i))
        if order.size == 1:
            break
        xx1 = np.maximum(boxes[i, 0], boxes[order[1:], 0])
        yy1 = np.maximum(boxes[i, 1], boxes[order[1:], 1])
        xx2 = np.minimum(boxes[i, 2], boxes[order[1:], 2])
        yy2 = np.minimum(boxes[i, 3], boxes[order[1:], 3])
        inter = np.clip(xx2 - xx1, 0, None) * np.clip(yy2 - yy1, 0, None)
        a = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
        iou = inter / (a[i] + a[order[1:]] - inter + 1e-9)
        order = order[1:][iou < iou_thr]
    return keep


def postprocess(out: np.ndarray, r: float, pad: tuple[int, int], conf_thr: float, iou_thr: float) -> list[Det]:
    """out: (1, 4+nc, N) from ultralytics ONNX export."""
    pred = out[0].T  # (N, 4+nc)
    xywh, cls_scores = pred[:, :4], pred[:, 4:]
    cls = cls_scores.argmax(1)
    conf = cls_scores.max(1)
    m = conf > conf_thr
    xywh, cls, conf = xywh[m], cls[m], conf[m]
    if not len(xywh):
        return []
    xyxy = np.stack([xywh[:, 0] - xywh[:, 2] / 2, xywh[:, 1] - xywh[:, 3] / 2,
                     xywh[:, 0] + xywh[:, 2] / 2, xywh[:, 1] + xywh[:, 3] / 2], 1)
    xyxy[:, [0, 2]] = (xyxy[:, [0, 2]] - pad[0]) / r
    xyxy[:, [1, 3]] = (xyxy[:, [1, 3]] - pad[1]) / r
    dets: list[Det] = []
    for c in np.unique(cls):
        idx = np.where(cls == c)[0]
        for k in nms(xyxy[idx], conf[idx], iou_thr):
            j = idx[k]
            dets.append(Det(int(c), float(conf[j]), tuple(map(float, xyxy[j]))))
    return dets


class OnnxYolo:
    def __init__(self, model_path: str, imgsz: int = 640, providers: list[str] | None = None):
        if ort is None:
            raise RuntimeError("onnxruntime not installed")
        avail = ort.get_available_providers()
        pref = providers or ["TensorrtExecutionProvider", "CUDAExecutionProvider", "CPUExecutionProvider"]
        self.providers = [p for p in pref if p in avail]
        so = ort.SessionOptions()
        so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        self.sess = ort.InferenceSession(model_path, so, providers=self.providers)
        self.inp = self.sess.get_inputs()[0].name
        self.imgsz = imgsz
        self.last_ms = 0.0

    def __call__(self, bgr: np.ndarray, conf_thr=0.35, iou_thr=0.5) -> list[Det]:
        lb, r, pad = letterbox(bgr, self.imgsz)
        x = lb[:, :, ::-1].transpose(2, 0, 1)[None].astype(np.float32) / 255.0
        t0 = time.perf_counter()
        out = self.sess.run(None, {self.inp: np.ascontiguousarray(x)})[0]
        self.last_ms = (time.perf_counter() - t0) * 1000
        return postprocess(out, r, pad, conf_thr, iou_thr)
