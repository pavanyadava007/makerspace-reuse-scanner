// In-browser knowledge base (browser demo build only): the same corpus files chunked by heading, the same rare-term lexical
// scoring as lexical_ids() in api/app/services/rag.py. No language model runs in the browser: answers are the retrieved
// passages verbatim, cited [n], plus the live inventory snapshot; the full stack lets llama3.1:8b write the answer from them.
import type { Source } from "../api";
import { inventorySnapshot } from "./db";

const DOCS = ["abfalltrennung_grundregeln.de.md", "elektronik_batterien.de.md", "kunststoffe_3d_druck.de.md", "metalle_und_altholz.de.md", "reuse_guide.en.md"];
type Chunk = { doc: string; section: string; lang: string; text: string; words: Set<string> };
let chunks: Chunk[] | null = null;
const terms = (s: string) => (s.toLowerCase().match(/[a-zäöüß0-9]+/g) ?? []).filter((w) => w.length >= 3);
const match = (t: string, w: string) => t === w || (t.length >= 5 && w.length >= 5 && (w.startsWith(t.slice(0, -1)) || t.startsWith(w.slice(0, -1))));
export const MODEL = "retrieval-only (browser demo, no LLM: passages verbatim)";

async function load(): Promise<Chunk[]> {
  if (chunks) return chunks; chunks = [];
  for (const doc of DOCS) {
    const r = await fetch(`corpus/${doc}`); if (!r.ok) continue;
    const lang = doc.endsWith(".de.md") ? "de" : "en"; let section = "intro";
    for (const part of (await r.text()).split(/^(#{1,3} .+)$/m)) {
      if (part.startsWith("#")) { section = part.replace(/^#+ /, "").trim(); continue; }
      const body = part.trim(); if (body.length > 40) chunks.push({ doc, section, lang, text: body.slice(0, 1800), words: new Set(terms(section + " " + body)) });
    }
  }
  return chunks;
}
export async function retrieve(question: string, lang: string, k = 4): Promise<(Chunk & { score: number })[]> {
  const all = await load(); let pool = all.filter((c) => c.lang === lang); if (!pool.length) pool = all;
  const n = pool.length, score = new Map<Chunk, number>();
  for (const t of new Set(terms(question))) {
    const hits = pool.filter((c) => [...c.words].some((w) => match(t, w))); if (!hits.length || hits.length > n / 2) continue;
    hits.forEach((c) => score.set(c, (score.get(c) ?? 0) + Math.log(n / hits.length)));
  }
  return [...score.entries()].sort((a, b) => b[1] - a[1]).slice(0, k).map(([c, s]) => ({ ...c, score: s }));
}
export async function ask(question: string, lang: string, withInventory: boolean): Promise<{ answer: string; sources: Source[]; model: string }> {
  const hits = await retrieve(question, lang); const sources: Source[] = hits.map((h, i) => ({ n: i + 1, doc: h.doc, section: h.section, lang: h.lang }));
  const stockQ = /bestand|lager|haben wir|wie viele|stock|inventory|how many/i.test(question);
  const parts: string[] = [];
  if (!hits.length && !stockQ) parts.push(lang === "de" ? "Dazu enthält die Wissensbasis keine Angaben." : "The knowledge base has no information on this.");
  hits.slice(0, 2).forEach((h, i) => parts.push(`[${i + 1}] ${h.text}`));
  if (withInventory && (stockQ || hits.length === 0)) { sources.push({ n: sources.length + 1, doc: "live-inventory", section: lang === "de" ? "aktueller Bestand" : "current stock", lang }); parts.push(`[${sources.length}] ${inventorySnapshot(lang)}`); }
  parts.push(lang === "de" ? "(Browser-Demo: Fundstellen wörtlich, ohne Sprachmodell. Im Gesamtsystem formuliert llama3.1:8b daraus eine kurze zitierte Antwort und lehnt Fragen außerhalb des Korpus ab.)"
                           : "(Browser demo: passages verbatim, no language model. In the full stack llama3.1:8b writes a short cited answer from exactly these passages and declines anything outside the corpus.)");
  return { answer: parts.join("\n\n"), sources, model: MODEL };
}
