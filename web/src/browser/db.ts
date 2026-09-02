// In-browser stand-in for the API's PostgreSQL state (browser demo build only). Same shapes as api/app/models.py,
// same dedupe rule as api/app/services/ingest.py: one item per label + location within DEDUPE_S of its last sighting,
// quantity = the most same-class boxes seen in ONE frame. Lives only as long as the page.
import type { Detection, Item, ItemDetail, Material, Stats, Suggestion } from "../api";

export const DEDUPE_S = 20;
export const LOCATION = "browser-demo";
const MATERIALS: [string, string, boolean, string][] = [
  ["steel", "metal", true, "Wertstoffhof / Schrott"], ["aluminium", "metal", true, "Wertstoffhof / Schrott"], ["copper", "metal", true, "Wertstoffhof / Schrott"],
  ["PLA plastic", "plastic", false, "Restmüll (nicht Gelber Sack)"], ["PETG plastic", "plastic", true, "Gelber Sack (nur Verpackung) / Wertstofftonne"],
  ["ABS plastic", "plastic", false, "Restmüll"], ["acrylic", "plastic", false, "Restmüll / Wertstoffhof"], ["plywood", "wood", true, "Altholz A II, Wertstoffhof"],
  ["solid wood", "wood", true, "Altholz A I"], ["MDF", "wood", true, "Altholz A II"], ["cardboard", "paper", true, "Papiertonne"],
  ["glass", "glass", true, "Glascontainer / Restmüll (Flachglas)"], ["fiberglass PCB", "composite", true, "Elektroschrott (ElektroG)"],
  ["rubber", "other", false, "Restmüll"], ["lithium battery", "hazardous", true, "Batteriesammelbox (BattG) - nie Restmüll"],
];
export const CLASS_PRIOR: Record<string, string> = {
  screw: "steel", nut_bolt: "steel", pcb: "fiberglass PCB", filament_spool: "PLA plastic", wood_offcut: "plywood", cable: "copper",
  "3d_print_part": "PLA plastic", acrylic_sheet: "acrylic", metal_profile: "aluminium", motor: "steel", battery: "lithium battery", tool: "steel",
  plastic_container: "PETG plastic", cardboard: "cardboard", glass: "glass",
};

export const materials: Material[] = MATERIALS.map(([name, category, recyclable, disposal_de], i) => ({ id: i + 1, name, category, recyclable, disposal_de }));
const matByName = Object.fromEntries(materials.map((m) => [m.name, m]));
type Row = Omit<Item, "material"> & { material_id: number | null };
export type DetRow = Detection & { item_id: number | null };   // the API stores item_id on the row but does not expose it
export const items = new Map<number, Row>();
export const detections: DetRow[] = [];
export const suggestions = new Map<number, Suggestion[]>();
export const images = new Map<number, string>();   // image id → blob URL of the stored frame
let nextItem = 1, nextDet = 1, nextImage = 1, nextSug = 1;

const now = () => new Date().toISOString();
export const withMaterial = (r: Row): Item => ({ ...r, material: r.material_id ? materials.find((m) => m.id === r.material_id) ?? null : null });

export function listItems(q: URLSearchParams): Item[] {
  let rows = [...items.values()].sort((a, b) => b.updated_at.localeCompare(a.updated_at));
  const status = q.get("status"), label = q.get("label"), material = q.get("material");
  if (status) rows = rows.filter((r) => r.status === status);
  if (label) rows = rows.filter((r) => r.label === label);
  if (material) rows = rows.filter((r) => r.material_id === matByName[material]?.id);
  return rows.slice(Number(q.get("offset") ?? 0), Number(q.get("offset") ?? 0) + Number(q.get("limit") ?? 100)).map(withMaterial);
}
export function getItem(id: number): ItemDetail | null {
  const r = items.get(id); if (!r) return null;
  return { ...withMaterial(r), detections: detections.filter((d) => d.item_id === id).sort((a, b) => b.created_at.localeCompare(a.created_at)),
           suggestions: [...(suggestions.get(id) ?? [])].sort((a, b) => b.created_at.localeCompare(a.created_at)) };
}
export function createItem(b: { label: string; material_id?: number | null; condition?: string | null; quantity?: number; location?: string | null }): Item {
  const r: Row = { id: nextItem++, label: b.label, material_id: b.material_id ?? null, condition: b.condition ?? null, quantity: b.quantity ?? 1,
                   location: b.location ?? null, status: "available", first_image_id: null, created_at: now(), updated_at: now() };
  items.set(r.id, r); return withMaterial(r);
}
export function patchItem(id: number, b: Record<string, unknown>): Item | null {
  const r = items.get(id); if (!r) return null;
  for (const k of ["condition", "quantity", "location", "status", "material_id"] as const) if (b[k] !== undefined && b[k] !== null) (r as Record<string, unknown>)[k] = b[k];
  r.updated_at = now(); return withMaterial(r);
}
export function deleteItem(id: number): boolean {
  if (!items.delete(id)) return false;
  detections.forEach((d) => { if (d.item_id === id) d.item_id = null; }); suggestions.delete(id); return true;
}
export function stats(): Stats {
  const by_status: Record<string, number> = {}, top: Record<string, number> = {}, by_category: Record<string, number> = {};
  for (const r of items.values()) {
    by_status[r.status] = (by_status[r.status] ?? 0) + r.quantity; top[r.label] = (top[r.label] ?? 0) + 1;
    const m = r.material_id ? materials[r.material_id - 1] : null; if (m) by_category[m.category] = (by_category[m.category] ?? 0) + 1;
  }
  const sortDesc = (o: Record<string, number>, n?: number) => Object.fromEntries(Object.entries(o).sort((a, b) => b[1] - a[1]).slice(0, n));
  return { by_status, top_labels: sortDesc(top, 10), by_category: sortDesc(by_category), items: items.size, detections: detections.length };
}
export function addSuggestion(id: number, text: string, sources: Suggestion["sources"], model: string): Suggestion {
  const s: Suggestion = { id: nextSug++, text, sources, model, created_at: now() };
  suggestions.set(id, [...(suggestions.get(id) ?? []), s]); return s;
}
export function reset() {
  const out = { detections: detections.length, items: items.size, images: images.size };
  items.clear(); detections.length = 0; suggestions.clear(); images.forEach((u) => URL.revokeObjectURL(u)); images.clear(); return out;
}

/** Persist one edge frame exactly like save_frame(): image → detections → dedupe into items. Returns detections with item ids. */
export function ingestFrame(frameBlob: Blob, w: number, h: number, device: string, fps: number, inferMs: number,
                            dets: { cls: string; conf: number; xyxy: number[] }[]) {
  const imageId = nextImage++; images.set(imageId, URL.createObjectURL(frameBlob));
  if (images.size > 400) { const [oldest] = images.keys(); URL.revokeObjectURL(images.get(oldest)!); images.delete(oldest); }   // memory cap
  const perCls: Record<string, number> = {}; dets.forEach((d) => (perCls[d.cls] = (perCls[d.cls] ?? 0) + 1));
  const t = Date.now(); const out: DetRow[] = [];
  for (const d of dets) {
    const material = CLASS_PRIOR[d.cls] ?? "unknown";
    let item = [...items.values()].filter((r) => r.label === d.cls && r.location === LOCATION && t - Date.parse(r.updated_at) <= DEDUPE_S * 1000)
      .sort((a, b) => b.updated_at.localeCompare(a.updated_at))[0];
    if (item) { item.updated_at = new Date(t).toISOString(); if (perCls[d.cls] > item.quantity) item.quantity = perCls[d.cls]; }
    else {
      item = { id: nextItem++, label: d.cls, material_id: matByName[material]?.id ?? null, condition: null, quantity: Math.max(1, perCls[d.cls]),
               location: LOCATION, status: "available", first_image_id: imageId, created_at: new Date(t).toISOString(), updated_at: new Date(t).toISOString() };
      items.set(item.id, item);
    }
    const det: DetRow = { id: nextDet++, image_id: imageId, item_id: item.id, cls: d.cls, conf: d.conf, x1: d.xyxy[0], y1: d.xyxy[1], x2: d.xyxy[2], y2: d.xyxy[3],
      material_pred: material, material_conf: null, condition_pred: null, vlm_backend: "class-prior", infer_ms: inferMs, fps, device, created_at: new Date(t).toISOString() };
    detections.push(det); out.push(det);
  }
  return out;
}
export function inventorySnapshot(lang: string): string {
  const hdr = lang === "de" ? "Live-Bestand des Makerspace-Inventars (Browser-Demo), Stückzahlen pro Objektklasse:" : "Live snapshot of the makerspace inventory (browser demo), piece counts per object class:";
  const per: Record<string, Record<string, number>> = {}, bins: Record<string, Material | null> = {};
  for (const r of items.values()) { (per[r.label] ??= {})[r.status] = ((per[r.label][r.status] ?? 0) + r.quantity); bins[r.label] ??= r.material_id ? materials[r.material_id - 1] : null; }
  const lines = Object.entries(per).sort((a, b) => Object.values(b[1]).reduce((s, v) => s + v, 0) - Object.values(a[1]).reduce((s, v) => s + v, 0)).map(([label, st]) => {
    const total = Object.values(st).reduce((s, v) => s + v, 0); const m = bins[label];
    const bin = m?.disposal_de ? (lang === "de" ? `; Material ${m.name} → richtiger Behälter: ${m.disposal_de}` : `; material ${m.name} → correct bin: ${m.disposal_de}`) : "";
    return `- ${label}: ${total} (${Object.entries(st).map(([k, v]) => `${k} ${v}`).join(", ")})${bin}`;
  });
  return [hdr, ...(lines.length ? lines : [lang === "de" ? "- (Inventar ist leer)" : "- (inventory is empty)"])].join("\n");
}
