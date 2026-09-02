// Browser demo build: replaces the FastAPI backend and the /ws/live socket with in-page implementations so the UNCHANGED React
// GUI runs on a static host (Hugging Face static Space, GitHub Pages). Installed before the app mounts (see main.tsx).
import { api } from "../api";
import * as db from "./db";
import * as edge from "./edge";
import * as rag from "./rag";

const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
const err = (status: number, detail: string) => json({ detail }, status);
const BUILTIN = [{ name: "demo_belt.mp4", edge_path: "demo_belt.mp4", size_mb: 2.1 }, { name: "demo_slideshow.mp4", edge_path: "demo_slideshow.mp4", size_mb: 2.5 },
                 { name: "webcam (this device)", edge_path: "webcam", size_mb: 0 }];
const uploads: { name: string; edge_path: string; size_mb: number }[] = [];
const videos = () => [...BUILTIN.map((v) => ({ ...v, kind: "builtin" })), ...uploads.map((v) => ({ ...v, kind: "uploaded" }))];
let evalCard: unknown = null;

async function handle(url: URL, req: Request): Promise<Response> {
  const p = url.pathname.replace(/^\/api/, ""), m = req.method.toUpperCase();
  const body = async () => { try { return await req.clone().json(); } catch { return {}; } };
  let mt: RegExpMatchArray | null;
  if (p === "/items" && m === "GET") return json(db.listItems(url.searchParams));
  if (p === "/items" && m === "POST") return json(db.createItem(await body()), 201);
  if ((mt = p.match(/^\/items\/(\d+)$/))) {
    const id = Number(mt[1]);
    if (m === "GET") { const it = db.getItem(id); return it ? json(it) : err(404, "item not found"); }
    if (m === "PATCH") { const it = db.patchItem(id, await body()); return it ? json(it) : err(404, "item not found"); }
    if (m === "DELETE") return db.deleteItem(id) ? new Response(null, { status: 204 }) : err(404, "item not found");
  }
  if ((mt = p.match(/^\/items\/(\d+)\/suggest$/)) && m === "POST") {
    const it = db.getItem(Number(mt[1])); if (!it) return err(404, "item not found");
    const lang = url.searchParams.get("lang") ?? "de", mat = it.material?.name ?? (lang === "de" ? "unbekanntes Material" : "unknown material");
    const q = lang === "de" ? `Wie kann ein Objekt '${it.label}' aus ${mat} im Makerspace wiederverwendet werden, und wie wird es sonst korrekt entsorgt?`
                            : `How can a '${it.label}' made of ${mat} be reused in a makerspace, and how is it disposed of correctly otherwise?`;
    const a = await rag.ask(`${q} ${it.label.replace(/_/g, " ")} ${mat}`, lang, false);
    return json(db.addSuggestion(it.id, a.answer, a.sources, a.model));
  }
  if (p === "/materials") return json(db.materials);
  if (p === "/stats") return json(db.stats());
  if (p === "/detections") return json(db.detections.slice(-Number(url.searchParams.get("limit") ?? 50)).reverse());
  if (p === "/ask" && m === "POST") { const b = await body(); return json(await rag.ask(String(b.question ?? ""), String(b.lang ?? "de"), true)); }
  if (p === "/model") {
    if (!evalCard) { try { evalCard = await (await origFetch("eval_2026-09-02.json")).json(); } catch { evalCard = null; } }
    return json({ model: edge.MODEL_FILE, eval: evalCard });
  }
  if (p === "/demo" && m === "GET") return json({ videos: videos(), selected: edge.selected() });
  if (p === "/demo/select" && m === "POST") {
    const b = await body(); if (b.video === null || b.video === undefined) { await edge.stop(); return json({ selected: null }); }
    const v = videos().find((x) => x.name === b.video); if (!v) return err(404, "unknown video");
    try { await edge.start(v.edge_path); } catch (e) { return err(500, `${(e as Error).message}`); }
    return json({ selected: v.edge_path });
  }
  if (p === "/demo/upload" && m === "POST") {
    const fd = await req.formData(); const f = fd.get("file"); if (!(f instanceof File)) return err(400, "no file");
    if (!/\.(mp4|webm|mov|mkv|avi)$/i.test(f.name)) return err(400, "video files only");
    const name = f.name.replace(/[^A-Za-z0-9._-]/g, "_"); const v = { name, edge_path: URL.createObjectURL(f), size_mb: Math.round(f.size / 1e5) / 10 };
    uploads.push(v); return json(v, 201);
  }
  if (p === "/admin/reset" && m === "POST") return json({ deleted: db.reset() });
  if ((mt = p.match(/^\/images\/(\d+)$/))) { const u = db.images.get(Number(mt[1])); return u ? Response.redirect(u) : err(404, "image not found"); }
  return err(404, `browser demo: no handler for ${m} /api${p}`);
}

const origFetch = window.fetch.bind(window);
window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
  const raw = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
  if (raw.startsWith("/api/")) { const req = new Request(raw, init); return handle(new URL(raw, "http://browser.demo"), req); }
  return origFetch(input, init);
};
api.imageUrl = (id: number) => db.images.get(id) ?? "";

class FakeLiveSocket {
  onopen: ((ev: Event) => void) | null = null; onmessage: ((ev: MessageEvent) => void) | null = null; onclose: ((ev: CloseEvent) => void) | null = null; onerror: unknown = null;
  readyState = 0; private unsub: (() => void) | null = null;
  constructor(public url: string) {
    setTimeout(() => { this.readyState = 1; this.onopen?.(new Event("open")); this.unsub = edge.subscribe((m) => this.onmessage?.(new MessageEvent("message", { data: JSON.stringify(m) }))); }, 0);
  }
  send() { /* viewers only listen */ }
  close() { this.readyState = 3; this.unsub?.(); this.unsub = null; }
  addEventListener() { /* not used by the app */ } removeEventListener() { /* not used by the app */ }
}
const RealWS = window.WebSocket;
(window as unknown as { WebSocket: unknown }).WebSocket = function (url: string, protocols?: string | string[]) {
  return url.includes("/ws/live") ? new FakeLiveSocket(url) : new RealWS(url, protocols);
} as unknown as typeof WebSocket;

(window as unknown as { __mrs: unknown }).__mrs = { edge, db };   // debugging handle (browser demo only)
edge.loadModel().then(() => edge.start("demo_belt.mp4")).catch(() => undefined);   // autoplay the conveyor demo, as the compose stack does
