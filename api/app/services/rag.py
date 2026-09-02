"""RAG over rag_chunk (pgvector) with Ollama embeddings + generation. Optional GraphRAG expansion via rag/graph.py."""
from __future__ import annotations

import datetime
import math

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Item, Material, RagChunk

# Ollama is an on-premise LAN service: never route it through HTTP(S)_PROXY from the host/daemon environment.
_client = lambda t: httpx.AsyncClient(timeout=t, trust_env=False)  # noqa: E731


# nomic-embed-text is trained with task prefixes; without them retrieval quality drops sharply
# (measured 2026-09-01: "Sperrholzreste" missed the Altholz chunk that names Sperrholz). Other models ignore them.
DOC_PREFIX, QUERY_PREFIX = "search_document: ", "search_query: "


async def embed(texts: list[str], prefix: str = QUERY_PREFIX) -> list[list[float]]:
    async with _client(120) as c:
        r = await c.post(f"{settings.ollama_url}/api/embed", json={"model": settings.embed_model, "input": [prefix + t for t in texts]})
        r.raise_for_status(); return r.json()["embeddings"]

async def generate(prompt: str, system: str) -> str:
    async with _client(300) as c:
        r = await c.post(f"{settings.ollama_url}/api/generate",
                         json={"model": settings.ollama_model, "prompt": prompt, "system": system, "stream": False,
                               "options": {"temperature": 0.2}})
        r.raise_for_status(); return r.json()["response"]

LEXICAL_K = 2      # extra chunks from the lexical leg per question (hybrid retrieval)
MAX_DF_SHARE = 1/3  # a term found in more than a third of the chunks is too generic to be a lexical signal


def lexical_ids(db: Session, question: str, lang: str | None) -> list[int]:
    """Chunk ids ranked by rare-term overlap with the question (Postgres full-text stemming, per-term OR, IDF weights).
    plainto_tsquery ANDs all words, so it is used only to normalise single terms; scoring happens here."""
    cfg = {"de": "german", "en": "english"}.get(lang or "", "simple")
    terms = db.scalar(select(func.tsvector_to_array(func.to_tsvector(cfg, question)))) or []
    terms = [t for t in dict.fromkeys(terms) if len(t) >= 3]
    if not terms: return []
    base = select(RagChunk.id)
    if lang: base = base.where(RagChunk.lang == lang)
    n = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    if not n: return []
    doc = func.to_tsvector(cfg, func.coalesce(RagChunk.section, "") + " " + RagChunk.text)
    score: dict[int, float] = {}
    for t in terms:
        ids = list(db.scalars(base.where(doc.op("@@")(func.plainto_tsquery(cfg, t)))))
        if not ids or len(ids) > n * MAX_DF_SHARE: continue
        for i in ids: score[i] = score.get(i, 0.0) + math.log(n / len(ids))
    return [i for i, _ in sorted(score.items(), key=lambda kv: -kv[1])]


def retrieve(db: Session, qvec: list[float], k: int, lang: str | None = None, question: str | None = None) -> list[RagChunk]:
    """Hybrid retrieval: top-k by cosine distance plus up to LEXICAL_K chunks from lexical_ids(). Measured 2026-09-02
    (rag/eval, vector-only baseline): "Sperrholzreste im Kamin verbrennen?" missed the Altholz chunk and "Warum darf PVC
    nicht gelasert werden?" missed the PMMA chunk - rare literal terms (Kamin, PVC) carry little embedding weight."""
    q = select(RagChunk).order_by(RagChunk.embedding.cosine_distance(qvec)).limit(k)
    if lang: q = q.where(RagChunk.lang == lang)
    out = list(db.scalars(q))
    if question and question.strip():
        seen = {c.id for c in out}
        extra = [i for i in lexical_ids(db, question, lang) if i not in seen][:LEXICAL_K]
        if extra:
            by_id = {c.id: c for c in db.scalars(select(RagChunk).where(RagChunk.id.in_(extra)))}
            out += [by_id[i] for i in extra if i in by_id]
    return out


def inventory_snapshot(db: Session, lang: str, max_lines: int = 25) -> str:
    """Compact live-stock summary injected into the ask() context - generated from the DB at question time,
    so stock answers are grounded, never guessed. Includes the correct bin (material.disposal_de) per label."""
    per = db.execute(select(Item.label, Item.status, func.sum(Item.quantity)).group_by(Item.label, Item.status)).all()
    mat = db.execute(select(Item.label, Material.name, Material.disposal_de, func.count())
                     .join(Material, Item.material_id == Material.id)
                     .group_by(Item.label, Material.name, Material.disposal_de)).all()
    labels: dict[str, dict[str, int]] = {}
    for label, status, qty in per: labels.setdefault(label, {})[status] = int(qty or 0)
    bins: dict[str, tuple[str, str | None, int]] = {}
    for label, m, d, c in mat:
        if c > bins.get(label, ("", None, 0))[2]: bins[label] = (m, d, c)
    hdr = ("Live-Bestand des Makerspace-Inventars (Stand {ts}), Stückzahlen pro Objektklasse:" if lang == "de" else
           "Live snapshot of the makerspace inventory (as of {ts}), piece counts per object class:")
    lines = [hdr.format(ts=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))]
    for label in sorted(labels, key=lambda k: -sum(labels[k].values()))[:max_lines]:
        st = labels[label]; total = sum(st.values())
        states = ", ".join(f"{k} {v}" for k, v in sorted(st.items()))
        m, d, _ = bins.get(label, (None, None, 0))
        bin_txt = (f"; Material {m} → richtiger Behälter: {d}" if lang == "de" else f"; material {m} → correct bin: {d}") if m and d else ""
        lines.append(f"- {label}: {total} ({states}){bin_txt}")
    if len(lines) == 1: lines.append("- (Inventar ist leer)" if lang == "de" else "- (inventory is empty)")
    return "\n".join(lines)


SYSTEM = {"de": "Du bist ein Assistent für Wiederverwendung und Entsorgung in einem Makerspace. Antworte IMMER auf Deutsch, "
                "auch wenn die Frage oder der Kontext auf Englisch ist. Antworte knapp. Nutze NUR den Kontext. "
                "Zitiere Quellen als [Nr]. Der Kontext kann einen Live-Bestand des Inventars enthalten - Stückzahlen und "
                "Behälter-Angaben daraus darfst du direkt nennen. Wenn der Kontext nichts hergibt, sage das.",
          "en": "You assist with reuse and disposal in a makerspace. ALWAYS answer in English, even when the question or the "
                "context is German - translate what you use. Answer briefly using ONLY the context. "
                "Cite sources as [n]. The context may include a live snapshot of the inventory - you may quote its counts "
                "and bin routes directly. If the context is insufficient, say so."}

async def ask(db: Session, question: str, lang: str = "de", k: int = 4, graph_terms: list[str] | None = None,
              include_inventory: bool = False):
    qvec = (await embed([question]))[0]
    chunks = retrieve(db, qvec, k, lang, question) or retrieve(db, qvec, k, None, question)  # prefer the answer language
    if graph_terms:  # GraphRAG: pull chunks for neighbouring materials/processes
        for t in graph_terms[:3]:
            chunks += retrieve(db, (await embed([t]))[0], 1, lang)
    seen, ctx, sources = set(), [], []
    for ch in chunks:
        if ch.id in seen: continue
        seen.add(ch.id); ctx.append(f"[{len(sources)+1}] ({ch.doc} › {ch.section})\n{ch.text}")
        sources.append({"n": len(sources) + 1, "doc": ch.doc, "section": ch.section, "lang": ch.lang})
    if include_inventory:
        n = len(sources) + 1
        ctx.append(f"[{n}] (live-inventory › {'aktueller Bestand' if lang == 'de' else 'current stock'})\n{inventory_snapshot(db, lang)}")
        sources.append({"n": n, "doc": "live-inventory", "section": "aktueller Bestand" if lang == "de" else "current stock", "lang": lang})
    prompt = "Kontext:\n" + "\n\n".join(ctx) + f"\n\nFrage: {question}"
    answer = await generate(prompt, SYSTEM.get(lang, SYSTEM["en"]))
    return answer, sources, settings.ollama_model
