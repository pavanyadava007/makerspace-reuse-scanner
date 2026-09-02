"""Hugging Face Space for the Makerspace Reuse Scanner (https://github.com/pavanyadava007/makerspace-reuse-scanner).

What runs here vs. the full stack: the SAME exported detector (ONNX, from the model repo) and the SAME corpus and retrieval idea,
but with a per-session inventory instead of PostgreSQL, a local embedding model instead of Ollama/pgvector, and Qwen2.5-7B-Instruct on
ZeroGPU instead of llama3.1:8b. The About tab lists every difference. Author: Pavan Yadav Annappa."""
from __future__ import annotations

import json
import os
import time
from collections import Counter

import cv2
import gradio as gr
import numpy as np
import rag_lite
import yaml
from detector import OnnxYolo
from huggingface_hub import hf_hub_download

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_REPO = "pavanyadava07/makerspace-yolo11n"
GITHUB = "https://github.com/pavanyadava007/makerspace-reuse-scanner"

# ---------------------------------------------------------------- detector + material stage (class prior, as in the default API image)
onnx_path = hf_hub_download(MODEL_REPO, "yolo11n_makerspace.onnx")
CLASSES = yaml.safe_load(open(os.path.join(HERE, "classes.yaml")))["names"]
det = OnnxYolo(onnx_path, 640)
CLASS_PRIOR = {"screw": "steel", "nut_bolt": "steel", "pcb": "fiberglass PCB", "filament_spool": "PLA plastic", "wood_offcut": "plywood",
               "cable": "copper", "3d_print_part": "PLA plastic", "acrylic_sheet": "acrylic", "metal_profile": "aluminium", "motor": "steel",
               "battery": "lithium battery", "tool": "steel", "plastic_container": "PETG plastic", "cardboard": "cardboard", "glass": "glass"}
BIN = {"steel": "Wertstoffhof / Schrott", "aluminium": "Wertstoffhof / Schrott", "copper": "Wertstoffhof / Schrott",
       "PLA plastic": "Restmüll (nicht Gelber Sack)", "PETG plastic": "Gelber Sack (nur Verpackung) / Wertstofftonne", "acrylic": "Restmüll / Wertstoffhof",
       "plywood": "Altholz A II, Wertstoffhof", "cardboard": "Papiertonne", "glass": "Glascontainer / Restmüll (Flachglas)",
       "fiberglass PCB": "Elektroschrott (ElektroG)", "lithium battery": "Batteriesammelbox (BattG) - nie Restmüll"}
CATEGORY = {"steel": "metal", "aluminium": "metal", "copper": "metal", "PLA plastic": "plastic", "PETG plastic": "plastic", "acrylic": "plastic",
            "plywood": "wood", "cardboard": "paper", "glass": "glass", "fiberglass PCB": "electronics", "lithium battery": "hazardous"}
HUE_RGB = {"metal": (31, 95, 168), "plastic": (46, 125, 79), "wood": (176, 122, 42), "paper": (176, 122, 42), "electronics": (122, 63, 160),
           "hazardous": (200, 50, 30), "glass": (11, 135, 166)}
EVAL = json.load(open(os.path.join(HERE, "eval_2026-09-02.json")))


def run_detector(bgr: np.ndarray, conf: float) -> tuple[np.ndarray, list[dict]]:
    dets = det(bgr, conf, 0.5)
    out = bgr.copy(); rows = []
    for d in dets:
        cls = CLASSES[d.cls]; mat = CLASS_PRIOR.get(cls, "unknown"); col = HUE_RGB.get(CATEGORY.get(mat, "glass"), (11, 135, 166))[::-1]
        x1, y1, x2, y2 = (int(v) for v in d.xyxy)
        cv2.rectangle(out, (x1, y1), (x2, y2), col, 2)
        label = f"{cls} {d.conf*100:.0f}% - {mat}"; (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
        cv2.rectangle(out, (x1, max(0, y1 - th - 8)), (x1 + tw + 8, y1), col, -1)
        cv2.putText(out, label, (x1 + 4, max(th + 2, y1 - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
        rows.append({"cls": cls, "conf": round(d.conf, 3), "material": mat, "bin": BIN.get(mat, "-"), "backend": "class-prior"})
    return out, rows


def merge_inventory(inv: list[dict], frame_rows: list[dict], source: str) -> list[dict]:
    """Session inventory: one row per label; quantity = most same-class boxes seen in ONE frame (never inflated by repeated
    frames), sightings = frames the label appeared in. The full stack additionally scopes this by location and a 20 s window."""
    per = Counter(r["cls"] for r in frame_rows); by = {r["label"]: r for r in inv}
    for cls, n in per.items():
        mat = CLASS_PRIOR.get(cls, "unknown")
        if cls in by: by[cls]["quantity"] = max(by[cls]["quantity"], n); by[cls]["sightings"] += 1; by[cls]["last_source"] = source
        else: by[cls] = {"label": cls, "material": mat, "bin": BIN.get(mat, "-"), "quantity": n, "sightings": 1, "status": "available", "last_source": source}
    return list(by.values())


def inv_table(inv: list[dict]) -> list[list]:
    return [[r["label"], r["material"], r["bin"], r["quantity"], r["sightings"], r["status"], r["last_source"]] for r in sorted(inv, key=lambda r: -r["quantity"])]


def inv_snapshot(inv: list[dict], lang: str) -> str:
    hdr = ("Live-Bestand des Inventars dieser Sitzung, Stückzahlen pro Objektklasse:" if lang == "de" else
           "Live snapshot of this session's inventory, piece counts per object class:")
    if not inv: return hdr + ("\n- (Inventar ist leer)" if lang == "de" else "\n- (inventory is empty)")
    b = ("; Material {m} → richtiger Behälter: {d}" if lang == "de" else "; material {m} → correct bin: {d}")
    return hdr + "\n" + "\n".join(f"- {r['label']}: {r['quantity']} ({r['status']} {r['quantity']}){b.format(m=r['material'], d=r['bin'])}" for r in inv)


# ---------------------------------------------------------------- Gradio callbacks
def detect_image(img: np.ndarray | None, conf: float, inv: list[dict]):
    if img is None: return None, [], inv, inv_table(inv), "Upload or pick an image."
    t = time.perf_counter(); out, rows = run_detector(cv2.cvtColor(img, cv2.COLOR_RGB2BGR), conf); ms = (time.perf_counter() - t) * 1000
    inv = merge_inventory(inv, rows, "image")
    table = [[r["cls"], r["conf"], r["material"], r["bin"], r["backend"]] for r in rows]
    note = f"{len(rows)} detections · {det.last_ms:.0f} ms inference / {ms:.0f} ms end-to-end on this Space's CPU ({det.providers[0]}) · 640 px letterbox"
    return cv2.cvtColor(out, cv2.COLOR_BGR2RGB), table, inv, inv_table(inv), note


def process_video(path: str | None, conf: float, seconds: float, inv: list[dict]):
    if not path: return None, inv, inv_table(inv), "Pick the belt demo or upload a clip."
    import imageio
    cap = cv2.VideoCapture(path); fps = cap.get(cv2.CAP_PROP_FPS) or 12; n_max = int(seconds * fps)
    out_path = os.path.join("/tmp", f"annotated_{int(time.time())}.mp4")
    w = imageio.get_writer(out_path, fps=min(fps, 15), codec="libx264", quality=7, macro_block_size=None)
    n = 0; total = 0; ms = []; t0 = time.perf_counter(); last = None
    while n < n_max:
        ok, frame = cap.read()
        if not ok: break
        n += 1
        if n % 2 == 1:  # detect on every other frame, reuse boxes in between (as the edge node sends every 3rd frame)
            h = frame.shape[0]; scale = 720 / h if h > 720 else 1.0
            small = cv2.resize(frame, None, fx=scale, fy=scale) if scale != 1.0 else frame
            ann, rows = run_detector(small, conf); ms.append(det.last_ms); total += len(rows); last = ann
            inv = merge_inventory(inv, rows, "video")
        if last is not None and n % int(max(1, round(fps / min(fps, 15)))) == 0: w.append_data(cv2.cvtColor(last, cv2.COLOR_BGR2RGB))
    w.close(); cap.release()
    note = (f"{n} frames read, {len(ms)} inferred: median {np.median(ms):.0f} ms per inference on this Space's CPU, "
            f"{total} boxes, {time.perf_counter() - t0:.1f} s wall time") if ms else "no frames decoded"
    return out_path, inv, inv_table(inv), note


def clear_inventory(): return [], [], "Session inventory cleared."


KB = None


def get_kb():
    global KB
    if KB is None: KB = rag_lite.KnowledgeBase()
    return KB


def ask(question: str, lang: str, inv: list[dict]):
    q = (question or "").strip()
    if not q: return "", "", ""
    r = rag_lite.ask(get_kb(), q, lang, inv_snapshot(inv, lang))
    src = "\n".join(f"{s['n']}. {s['doc']} › {s['section']}" for s in r["sources"])
    return r["answer"], src, f"{r['mode']} · {r['seconds']} s · retrieval: multilingual-e5-small + rare-term lexical leg, k=4 (+2)"


# ---------------------------------------------------------------- UI
EXAMPLE_DIR = os.path.join(HERE, "examples"); SHOT_DIR = os.path.join(HERE, "screenshots")
examples = sorted(os.path.join(EXAMPLE_DIR, f) for f in os.listdir(EXAMPLE_DIR)) if os.path.isdir(EXAMPLE_DIR) else []
belt = os.path.join(HERE, "demo_belt.mp4")
per_class = "\n".join(f"| {c} | {v['ap50']*100:.1f} % |" for c, v in sorted(EVAL["per_class"].items(), key=lambda kv: -kv[1]["ap50"]))
ABOUT = f"""
## What this is
A camera at a makerspace bench detects parts and offcuts, an inventory keeps what can be reused, and a local, cited knowledge base answers
"how do I reuse or dispose of this?" under German rules. The full system is four Docker containers (edge node, FastAPI, PostgreSQL + pgvector,
Ollama) plus a React app; source, tests, ADRs and status reports are on GitHub: [{GITHUB}]({GITHUB}).

```
camera / video --OpenCV--> YOLO11n (ONNX Runtime) --WS--> FastAPI --> PostgreSQL + pgvector <-- rag/corpus/*.md (DE/EN)
                                 |                         |                ^
                            crops|                         v                | embeddings
                                 +--> material stage    Ollama (llama3.1:8b, nomic-embed-text)
                                                           |
                                          React (live overlay - inventory - item detail - Ask)
```

## This Space vs. the full stack
| | this Space | full stack (`docker compose up`) |
|---|---|---|
| detector | the same `yolo11n_makerspace.onnx` from [{MODEL_REPO}](https://huggingface.co/{MODEL_REPO}), CPU | same file, TensorRT → CUDA → CPU fallback on the edge device |
| material | class prior (labelled `class-prior`) | CLIP or Qwen2.5-VL when available, class prior otherwise, backend stored per detection |
| inventory | per browser session, one row per label | PostgreSQL, one item per label + location within 20 s of last sighting, editable in the GUI |
| knowledge base | same 5 corpus files, `multilingual-e5-small` embeddings + lexical leg in NumPy | same files, `nomic-embed-text` in pgvector + Postgres full-text leg |
| answer model | Qwen2.5-7B-Instruct on ZeroGPU (verbatim excerpt if no GPU is available) | llama3.1:8b in Ollama, on-premise |

## Measured, from committed files (never typed in)
Detector on the held-out test split, 2026-09-02 (`training/reports/eval_2026-09-02.json`): mAP@50 **{EVAL['map50']*100:.1f} %**,
mAP@50-95 {EVAL['map']*100:.1f} %, precision {EVAL['precision']*100:.1f} %, recall {EVAL['recall']*100:.1f} %.

| class | AP@50 |
|---|---|
{per_class}

Read before trusting: screw and PCB test images are single-object studio shots (flattering); battery and tool have too little data to be
usable; the dominant failure is missed small or distant objects, not class confusion; six of the 15 classes (filament spool, wood offcut,
cable, 3D-print part, acrylic sheet, metal profile) have no training data yet and are never predicted. Trained on public data only
(LVIS, TACO, TrashNet, a cropped-PCB set, MVTec AD screws); the weights are therefore CC BY-NC-SA 4.0, the code is MIT.
Knowledge-base quality: 25 hand-verified questions in `rag/eval/`, both runs committed in `rag/eval/reports/`.

## Honesty rules of the project
1. Every FPS number carries the device it was measured on. 2. mAP comes only from the test-split report. 3. Every material prediction
records its backend. 4. Answers cite chunks or say the corpus is insufficient. 5. RAG quality comes only from the evaluation runner.

Author: Pavan Yadav Annappa, Frankfurt am Main.
"""

with gr.Blocks(title="Makerspace Reuse Scanner") as demo:
    inv_state = gr.State([])
    gr.Markdown(f"# ♻️ Makerspace Reuse Scanner\nEdge YOLO11n → reuse inventory → cited DE/EN disposal assistant, all on-premise in the real system. "
                f"[Source on GitHub]({GITHUB}) · [detector on the Hub](https://huggingface.co/{MODEL_REPO})")
    with gr.Tabs():
        with gr.Tab("Detect (image)"):
            with gr.Row():
                with gr.Column():
                    img_in = gr.Image(type="numpy", label="Bench photo or belt frame")
                    conf = gr.Slider(0.1, 0.9, value=0.35, step=0.05, label="confidence threshold")
                    btn = gr.Button("Detect", variant="primary")
                    if examples: gr.Examples(examples=[[e] for e in examples], inputs=[img_in], label="Frames from the conveyor demo (held-out test objects)")
                with gr.Column():
                    img_out = gr.Image(label="Detections, coloured by material")
                    det_table = gr.Dataframe(headers=["class", "conf", "material", "bin", "backend"], interactive=False, label="This frame")
                    det_note = gr.Markdown()
        with gr.Tab("Belt demo (video)"):
            gr.Markdown("The rendered conveyor-belt clip of real test-split objects, run through the real detector. Processing happens on this Space's CPU, so a 15 s clip takes about half a minute.")
            with gr.Row():
                with gr.Column():
                    vid_in = gr.Video(label="Video", value=belt if os.path.isfile(belt) else None)
                    secs = gr.Slider(5, 48, value=15, step=1, label="seconds to process")
                    vconf = gr.Slider(0.1, 0.9, value=0.35, step=0.05, label="confidence threshold")
                    vbtn = gr.Button("Run detector on the clip", variant="primary")
                with gr.Column():
                    vid_out = gr.Video(label="Annotated")
                    vid_note = gr.Markdown()
        with gr.Tab("Inventory (this session)"):
            gr.Markdown("Every detection above lands here, deduplicated per label: quantity is the most same-class boxes seen in one frame, so repeated "
                        "frames never inflate it. The full stack scopes this by location and a 20 s window and lets you edit material, condition and status.")
            inv_table_ui = gr.Dataframe(headers=["label", "material", "bin", "qty", "sightings", "status", "last source"], interactive=False)
            clr = gr.Button("Clear session inventory")
            inv_note = gr.Markdown()
        with gr.Tab("Ask the knowledge base"):
            gr.Markdown("Answers come only from the five corpus files (German waste rules: Restmüll, Gelber Sack, Papiertonne, Glascontainer, Wertstoffhof, "
                        "ElektroG, BattG, AltholzV, PLA/PETG/ABS/PMMA, metals, wood) plus this session's inventory, and cite [n]. Out-of-corpus questions are declined.")
            with gr.Row():
                q_in = gr.Textbox(lines=2, label="Question", placeholder="Wohin mit PLA-Fehldrucken? / Where do lithium cells go? / Wie viele Schrauben haben wir?")
                lang = gr.Radio(["de", "en"], value="de", label="answer language")
            ask_btn = gr.Button("Ask", variant="primary")
            gr.Examples(examples=[["Wohin mit PLA-Fehldrucken?", "de"], ["Darf ich Sperrholzreste im Kamin verbrennen?", "de"], ["Wohin mit einem defekten Lithium-Akku?", "de"],
                                  ["Warum darf PVC nicht gelasert werden?", "de"], ["Was haben wir gerade im Bestand und wohin gehört es?", "de"],
                                  ["How do I reuse plywood offcuts?", "en"], ["What is the melting point of titanium?", "en"]], inputs=[q_in, lang])
            answer = gr.Markdown(label="Answer")
            sources = gr.Textbox(label="Sources", lines=5, interactive=False)
            ask_note = gr.Markdown()
        with gr.Tab("About, numbers, screenshots"):
            gr.Markdown(ABOUT)
            if os.path.isdir(SHOT_DIR):
                gr.Gallery(value=[(os.path.join(SHOT_DIR, f), f.replace(".png", "").replace("_", " ")) for f in sorted(os.listdir(SHOT_DIR))],
                           label="The real GUI (React) with the conveyor demo running", columns=2, height="auto")
    btn.click(detect_image, [img_in, conf, inv_state], [img_out, det_table, inv_state, inv_table_ui, det_note])
    vbtn.click(process_video, [vid_in, vconf, secs, inv_state], [vid_out, inv_state, inv_table_ui, vid_note])
    clr.click(clear_inventory, [], [inv_state, inv_table_ui, inv_note])
    ask_btn.click(ask, [q_in, lang, inv_state], [answer, sources, ask_note])
    q_in.submit(ask, [q_in, lang, inv_state], [answer, sources, ask_note])

if __name__ == "__main__":
    rag_lite._load_llm()
    try: get_kb()
    except Exception as e: print("knowledge base failed to load:", e)  # noqa: BLE001
    demo.launch()
