// In-browser edge node (browser demo build only): the same ONNX file as edge/detector.py, run by onnxruntime-web inside a
// dedicated Web Worker (edge.worker.ts) so the page never freezes; same letterbox + per-class NMS maths; frames are pushed
// into the in-memory store and broadcast to the fake /ws/live socket exactly like api/app/routers/ws.py does.
import type { Frame, Status } from "../api";
import { CLASS_PRIOR, ingestFrame } from "./db";

export const NAMES = ["screw", "nut_bolt", "pcb", "filament_spool", "wood_offcut", "cable", "3d_print_part", "acrylic_sheet", "metal_profile", "motor", "battery", "tool", "plastic_container", "cardboard", "glass"];
export const MODEL_FILE = "yolo11n_makerspace.onnx";
const IMGSZ = 640, MIN_CONF = 0.35, IOU = 0.5, MIN_INTERVAL_MS = 120;
type Sub = (msg: Frame | Status) => void;
const subs = new Set<Sub>();
export const edges: Status["edges"] = {};
export const DEVICE = `browser demo (onnxruntime-web, ${navigator.hardwareConcurrency ?? "?"} cores, this device)`;
let worker: Worker | null = null; let loading: Promise<void> | null = null;
type Result = { data: Float32Array; dims: number[]; ms: number };
let pending: { res: (r: Result) => void; rej: (e: Error) => void } | null = null;
function runWorker(x: Float32Array): Promise<Result> {
  return new Promise((res, rej) => { pending = { res, rej }; worker!.postMessage({ type: "run", x, size: IMGSZ }, [x.buffer]); });
}
let video: HTMLVideoElement | null = null; let stream: MediaStream | null = null; let running = false; let current: string | null = null;
export const modelStatus = { text: "detector not loaded", ok: false };

export function subscribe(fn: Sub) { subs.add(fn); fn({ type: "status", edges }); return () => subs.delete(fn); }
const broadcast = (m: Frame | Status) => subs.forEach((s) => { try { s(m); } catch { /* viewer gone */ } });
function status() { broadcast({ type: "status", edges }); }

export function loadModel(): Promise<void> {
  if (!loading) loading = (async () => {
    const r = await fetch(MODEL_FILE); if (!r.ok) throw new Error(`model fetch HTTP ${r.status}`);
    const model = await r.arrayBuffer();
    worker = new Worker(new URL("./edge.worker.ts", import.meta.url), { type: "module" });
    await new Promise<void>((res, rej) => {
      worker!.onmessage = (e: MessageEvent) => {
        const m = e.data;
        if (m.type === "ready") { modelStatus.text = `${MODEL_FILE} loaded (${m.threads} WASM thread(s), worker)`; modelStatus.ok = true; res(); }
        else if (m.type === "result") { pending?.res({ data: m.data, dims: m.dims, ms: m.ms }); pending = null; }
        else if (m.type === "error") { const err = new Error(m.message); if (pending) { pending.rej(err); pending = null; } else rej(err); }
      };
      worker!.onerror = (e) => rej(new Error(e.message));
      // the .wasm/.mjs runtime files are copied next to index.html at build time (vite.config.ts)
      worker!.postMessage({ type: "init", wasmPaths: new URL("./", document.baseURI).href, model }, [model]);
    });
  })().catch((e) => { modelStatus.text = `detector failed: ${e.message}`; throw e; });
  return loading;
}

const lbCanvas = document.createElement("canvas"); lbCanvas.width = IMGSZ; lbCanvas.height = IMGSZ;
const jpgCanvas = document.createElement("canvas");
function letterbox(src: HTMLVideoElement) {
  const w = src.videoWidth, h = src.videoHeight, r = IMGSZ / Math.max(w, h), nw = Math.round(w * r), nh = Math.round(h * r);
  const left = Math.floor((IMGSZ - nw) / 2), top = Math.floor((IMGSZ - nh) / 2), g = lbCanvas.getContext("2d", { willReadFrequently: true })!;
  g.fillStyle = "rgb(114,114,114)"; g.fillRect(0, 0, IMGSZ, IMGSZ); g.drawImage(src, 0, 0, w, h, left, top, nw, nh);
  const d = g.getImageData(0, 0, IMGSZ, IMGSZ).data, n = IMGSZ * IMGSZ, x = new Float32Array(3 * n);
  for (let i = 0; i < n; i++) { x[i] = d[i * 4] / 255; x[n + i] = d[i * 4 + 1] / 255; x[2 * n + i] = d[i * 4 + 2] / 255; }
  return { x, r, left, top, w, h };
}
const iou = (a: number[], b: number[]) => { const ix = Math.max(0, Math.min(a[2], b[2]) - Math.max(a[0], b[0])), iy = Math.max(0, Math.min(a[3], b[3]) - Math.max(a[1], b[1])); const i = ix * iy; return i / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i + 1e-9); };
function postprocess(out: Float32Array, dims: readonly number[], r: number, left: number, top: number) {
  const nc = dims[1] - 4, N = dims[2], cand: { cls: number; conf: number; xyxy: number[] }[] = [];
  for (let i = 0; i < N; i++) {
    let best = 0, bc = 0; for (let c = 0; c < nc; c++) { const s = out[(4 + c) * N + i]; if (s > best) { best = s; bc = c; } }
    if (best <= MIN_CONF) continue;
    const cx = out[i], cy = out[N + i], w = out[2 * N + i], h = out[3 * N + i];
    cand.push({ cls: bc, conf: best, xyxy: [(cx - w / 2 - left) / r, (cy - h / 2 - top) / r, (cx + w / 2 - left) / r, (cy + h / 2 - top) / r] });
  }
  cand.sort((a, b) => b.conf - a.conf); const keep: typeof cand = [];
  for (const d of cand) if (!keep.some((k) => k.cls === d.cls && iou(k.xyxy, d.xyxy) >= IOU)) keep.push(d);
  return keep;
}
function jpeg(src: HTMLVideoElement, width = 640, q = 0.6): Promise<{ blob: Blob; b64: string }> {
  const h = Math.round(width * src.videoHeight / src.videoWidth); jpgCanvas.width = width; jpgCanvas.height = h;
  jpgCanvas.getContext("2d")!.drawImage(src, 0, 0, width, h);
  const dataUrl = jpgCanvas.toDataURL("image/jpeg", q); const b64 = dataUrl.slice(dataUrl.indexOf(",") + 1);
  return new Promise((res) => jpgCanvas.toBlob((blob) => res({ blob: blob!, b64 }), "image/jpeg", q));
}

async function loop(v: HTMLVideoElement) {
  const fpsWin: number[] = []; let inferMs = 0; let lastStatus = 0;
  while (running && video === v) {
    const t0 = performance.now();
    if (t0 - lastStatus > 2000) { lastStatus = t0; status(); }   // keep the header pill's FPS / ms current
    if (v.readyState >= 2 && v.videoWidth > 0) {
      const { x, r, left, top, w, h } = letterbox(v);
      const o = await runWorker(x); inferMs = o.ms;
      const dets = postprocess(o.data, o.dims, r, left, top).map((d) => ({ cls: NAMES[d.cls], conf: Math.round(d.conf * 1000) / 1000, xyxy: d.xyxy.map((v) => Math.round(v * 10) / 10) }));
      const { blob, b64 } = await jpeg(v);
      fpsWin.push(1000 / Math.max(1, performance.now() - t0)); if (fpsWin.length > 30) fpsWin.shift();
      const fps = Math.round((fpsWin.reduce((s, f) => s + f, 0) / fpsWin.length) * 10) / 10;
      const saved = ingestFrame(blob, w, h, DEVICE, fps, Math.round(inferMs * 10) / 10, dets);
      edges[DEVICE] = { ...edges[DEVICE], fps, infer_ms: Math.round(inferMs * 10) / 10 };
      broadcast({ type: "frame", device: DEVICE, fps, infer_ms: Math.round(inferMs * 10) / 10, width: w, height: h, frame: b64,
                  detections: saved.map((d) => ({ cls: d.cls, conf: d.conf, xyxy: [d.x1, d.y1, d.x2, d.y2], material: d.material_pred ?? CLASS_PRIOR[d.cls] ?? null, item_id: d.item_id })) });
    }
    const wait = MIN_INTERVAL_MS - (performance.now() - t0);
    await new Promise((res) => setTimeout(res, Math.max(16, wait)));
  }
}

export async function start(source: string) {
  await stop(); await loadModel();
  const v = document.createElement("video"); v.muted = true; v.playsInline = true; v.loop = true; v.crossOrigin = "anonymous";
  if (source === "webcam") { stream = await navigator.mediaDevices.getUserMedia({ video: { width: 1280, height: 720 } }); v.srcObject = stream; }
  else v.src = source;
  const playing = v.play();
  await Promise.race([playing, new Promise((_, rej) => setTimeout(() => rej(new Error("video source did not start within 10 s (unsupported codec or no camera frames)")), 10000))]);
  video = v; running = true; current = source;
  edges[DEVICE] = { fps: null, providers: ["wasm (onnxruntime-web, Web Worker)"], model: MODEL_FILE }; status();
  loop(v).catch((e) => { modelStatus.text = `edge loop stopped: ${e.message}`; });
}
export async function stop() {
  running = false; current = null;
  if (video) { video.pause(); video.srcObject = null; video.removeAttribute("src"); video = null; }
  if (stream) { stream.getTracks().forEach((t) => t.stop()); stream = null; }
  if (edges[DEVICE]) { delete edges[DEVICE]; status(); }
}
export const selected = () => current;
