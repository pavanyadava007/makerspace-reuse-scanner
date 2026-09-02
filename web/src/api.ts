export type Material = { id: number; name: string; category: string; recyclable: boolean; disposal_de: string | null };
export type Detection = { id: number; image_id: number; cls: string; conf: number; x1: number; y1: number; x2: number; y2: number;
  material_pred: string | null; material_conf: number | null; condition_pred: string | null; vlm_backend: string | null;
  infer_ms: number | null; fps: number | null; device: string | null; created_at: string };
export type Suggestion = { id: number; text: string; sources: Source[] | null; model: string | null; created_at: string };
export type Source = { n: number; doc: string; section: string; lang: string };
export type Item = { id: number; label: string; condition: string | null; quantity: number; location: string | null; status: string;
  first_image_id: number | null; created_at: string; updated_at: string; material: Material | null };
export type ItemDetail = Item & { detections: Detection[]; suggestions: Suggestion[] };
export type LiveDet = { cls: string; conf: number; xyxy: number[]; material: string | null; item_id: number | null };
export type Frame = { type: "frame"; device: string; fps: number; infer_ms: number; width: number; height: number; frame: string; detections: LiveDet[] };
export type EdgeInfo = { fps: number | null; infer_ms?: number; providers?: string[]; model?: string | null };
export type Status = { type: "status"; edges: Record<string, EdgeInfo> };
export type Stats = { by_status: Record<string, number>; top_labels: Record<string, number>; by_category: Record<string, number>;
  items: number; detections: number };
export type Ask = { answer: string; sources: Source[]; model: string };
export type DemoVideo = { name: string; kind: "builtin" | "uploaded"; edge_path: string; size_mb: number };
export type DemoStatus = { videos: DemoVideo[]; selected: string | null };
export type ModelCard = { model: string | null; eval: null | { date: string; map50: number; map: number; precision: number;
  recall: number; per_class: Record<string, { ap50: number; ap: number }> } };

const j = async <T,>(r: Promise<Response>): Promise<T> => { const x = await r; if (!x.ok) throw new Error(`${x.status} ${x.statusText}`); return x.json(); };
export const api = {
  items: (q: Record<string, string> = {}) => j<Item[]>(fetch("/api/items?" + new URLSearchParams(q))),
  item: (id: number) => j<ItemDetail>(fetch(`/api/items/${id}`)),
  create: (body: { label: string; material_id?: number; condition?: string; quantity?: number; location?: string }) =>
    j<Item>(fetch("/api/items", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })),
  patch: (id: number, body: Partial<Item> & { material_id?: number }) =>
    j<Item>(fetch(`/api/items/${id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })),
  del: async (id: number) => { const r = await fetch(`/api/items/${id}`, { method: "DELETE" }); if (!r.ok) throw new Error(`${r.status}`); },
  materials: () => j<Material[]>(fetch("/api/materials")),
  stats: () => j<Stats>(fetch("/api/stats")),
  suggest: (id: number, lang: string) => j<Suggestion>(fetch(`/api/items/${id}/suggest?lang=${lang}`, { method: "POST" })),
  ask: (question: string, lang: string) => j<Ask>(
    fetch("/api/ask", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question, lang }) })),
  demo: () => j<DemoStatus>(fetch("/api/demo")),
  demoSelect: (video: string | null) => j<{ selected: string | null }>(
    fetch("/api/demo/select", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ video }) })),
  demoUpload: (f: File) => { const fd = new FormData(); fd.append("file", f); return j<DemoVideo>(fetch("/api/demo/upload", { method: "POST", body: fd })); },
  modelCard: () => j<ModelCard>(fetch("/api/model")),
  reset: () => j<{ deleted: Record<string, number> }>(fetch("/api/admin/reset", { method: "POST" })),
};
export const wsUrl = (p: string) => `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}${p}`;
// Material identity colors - validated palette (dataviz six-checks, light surface #F8F8F5); every colored
// mark carries a text label as secondary encoding, so the wood↔plastic protan floor-band pair is legal.
export const materialHue: Record<string, string> = {
  steel: "var(--metal)", aluminium: "var(--metal)", copper: "var(--metal)", "PLA plastic": "var(--plastic)", "PETG plastic": "var(--plastic)",
  "ABS plastic": "var(--plastic)", acrylic: "var(--plastic)", plywood: "var(--wood)", "solid wood": "var(--wood)", MDF: "var(--wood)",
  cardboard: "var(--wood)", glass: "var(--other)", "fiberglass PCB": "var(--electro)", "lithium battery": "var(--hazard)", rubber: "var(--other)",
};
