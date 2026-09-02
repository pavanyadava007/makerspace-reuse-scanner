"""Self-contained RAG for the Hugging Face Space: the same corpus, chunking and hybrid retrieval idea as the full stack
(api/app/services/rag.py), with a local embedding model instead of Ollama/pgvector and an instruct model on ZeroGPU.
Everything the full stack does with PostgreSQL happens here in NumPy; the corpus files are byte-identical copies."""
from __future__ import annotations

import glob
import math
import os
import re
import time

try:
    import spaces  # present on ZeroGPU Spaces only
except ImportError:  # local run
    spaces = None

CORPUS_DIR = os.getenv("CORPUS_DIR", os.path.join(os.path.dirname(__file__), "corpus"))
EMBED_MODEL = os.getenv("EMBED_MODEL", "intfloat/multilingual-e5-small")
ASK_LLM = os.getenv("ASK_LLM", "Qwen/Qwen2.5-7B-Instruct")   # "" disables generation (retrieval-only answers)
LEXICAL_K, MAX_DF_SHARE = 2, 1 / 3

SYSTEM = {"de": "Du bist ein Assistent für Wiederverwendung und Entsorgung in einem Makerspace. Antworte IMMER auf Deutsch, knapp, "
                "und NUR mit Aussagen, die im Kontext stehen. Zitiere jede Aussage mit der Nummer ihrer Quelle, z. B. [1] oder [2]. Der Kontext kann "
                "einen Live-Bestand des Inventars enthalten: nenne dessen Stückzahlen und Behälter wörtlich, ohne Umdeutung. Steht die Antwort nicht im Kontext, antworte "
                "genau: 'Dazu enthält die Wissensbasis keine Angaben.' Erfinde keine Zahlen, Regeln oder Quellen.",
          "en": "You assist with reuse and disposal in a makerspace. ALWAYS answer in English, briefly, and ONLY with statements that "
                "are in the context (translate German passages). Cite every statement with the number of its source, e.g. [1] or [2]. The context "
                "may include a live inventory snapshot: quote its counts and bins verbatim, without reinterpreting them. If the answer is not in the context, reply exactly: "
                "'The knowledge base has no information on this.' Never invent numbers, rules or sources."}
REFUSAL = {"de": "Dazu enthält die Wissensbasis keine Angaben.", "en": "The knowledge base has no information on this."}


def load_chunks(corpus_dir: str = CORPUS_DIR) -> list[dict]:
    rows = []
    for path in sorted(glob.glob(os.path.join(corpus_dir, "*.md"))):
        doc = os.path.basename(path); lang = "de" if doc.endswith(".de.md") else "en"; section = "intro"
        for part in re.split(r"^(#{1,3} .+)$", open(path, encoding="utf-8").read(), flags=re.MULTILINE):
            if part.startswith("#"): section = part.lstrip("# ").strip(); continue
            body = part.strip()
            if len(body) > 40: rows.append({"doc": doc, "section": section, "lang": lang, "text": body[:1800]})
    return rows


_WORD = re.compile(r"[a-zäöüß0-9]+")


def _terms(s: str) -> list[str]: return [w for w in _WORD.findall(s.lower()) if len(w) >= 3]


def _match(term: str, word: str) -> bool:   # crude stemming: shared 5+ character prefix
    return term == word or (len(term) >= 5 and len(word) >= 5 and (word.startswith(term[:-1]) or term.startswith(word[:-1])))


class KnowledgeBase:
    def __init__(self):
        from sentence_transformers import SentenceTransformer
        self.chunks = load_chunks()
        self.embedder = SentenceTransformer(EMBED_MODEL)
        self.E = self.embedder.encode([f"passage: {c['section']}\n{c['text']}" for c in self.chunks], normalize_embeddings=True)
        self.words = [set(_terms(c["section"] + " " + c["text"])) for c in self.chunks]

    def lexical(self, question: str, lang: str | None) -> list[int]:
        idx = [i for i, c in enumerate(self.chunks) if lang is None or c["lang"] == lang]
        n = len(idx); score: dict[int, float] = {}
        for t in dict.fromkeys(_terms(question)):
            hits = [i for i in idx if any(_match(t, w) for w in self.words[i])]
            if not hits or len(hits) > n * MAX_DF_SHARE: continue
            for i in hits: score[i] = score.get(i, 0.0) + math.log(n / len(hits))
        return [i for i, _ in sorted(score.items(), key=lambda kv: -kv[1])]

    def retrieve(self, question: str, lang: str, k: int = 4) -> list[dict]:
        q = self.embedder.encode([f"query: {question}"], normalize_embeddings=True)[0]
        sims = self.E @ q
        idx = [i for i, c in enumerate(self.chunks) if c["lang"] == lang] or list(range(len(self.chunks)))
        top = sorted(idx, key=lambda i: -sims[i])[:k]
        seen = set(top)
        for i in self.lexical(question, lang if idx != list(range(len(self.chunks))) else None):
            if len(top) >= k + LEXICAL_K: break
            if i not in seen: top.append(i); seen.add(i)
        return [{**self.chunks[i], "score": float(sims[i])} for i in top]


def build_context(chunks: list[dict], inventory_snapshot: str | None, lang: str) -> tuple[str, list[dict]]:
    ctx, sources = [], []
    for ch in chunks:
        n = len(sources) + 1; ctx.append(f"[{n}] ({ch['doc']} › {ch['section']})\n{ch['text']}")
        sources.append({"n": n, "doc": ch["doc"], "section": ch["section"], "lang": ch["lang"]})
    if inventory_snapshot:
        n = len(sources) + 1; sec = "aktueller Bestand" if lang == "de" else "current stock"
        ctx.append(f"[{n}] (live-inventory › {sec})\n{inventory_snapshot}")
        sources.append({"n": n, "doc": "live-inventory", "section": sec, "lang": lang})
    return "Kontext:\n" + "\n\n".join(ctx), sources


# ---------------------------------------------------------------- generation (ZeroGPU when available)
_llm = {"tok": None, "model": None, "error": None}


def _load_llm():
    if not ASK_LLM: _llm["error"] = "generation disabled (ASK_LLM empty)"; return
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        if spaces is None and not torch.cuda.is_available():
            _llm["error"] = "no GPU on this machine: retrieval-only answers"; return
        _llm["tok"] = AutoTokenizer.from_pretrained(ASK_LLM)
        _llm["model"] = AutoModelForCausalLM.from_pretrained(ASK_LLM, dtype=torch.bfloat16).to("cuda")
    except Exception as e:  # noqa: BLE001 - any failure degrades to retrieval-only, never to a broken tab
        _llm["error"] = f"{type(e).__name__}: {str(e)[:120]}"


def _gpu(f):
    return spaces.GPU(duration=90)(f) if spaces is not None else f


@_gpu
def generate(prompt: str, system: str, max_new_tokens: int = 220) -> str:
    import torch
    tok, model = _llm["tok"], _llm["model"]
    text = tok.apply_chat_template([{"role": "system", "content": system}, {"role": "user", "content": prompt}],
                                   add_generation_prompt=True, tokenize=False)
    inp = tok(text, return_tensors="pt").to(model.device)
    with torch.no_grad():
        out = model.generate(**inp, max_new_tokens=max_new_tokens, do_sample=False, temperature=None, top_p=None, top_k=None)
    return tok.decode(out[0][inp.input_ids.shape[1]:], skip_special_tokens=True).strip()


def llm_status() -> str:
    if _llm["model"] is not None: return f"{ASK_LLM} ({'ZeroGPU' if spaces else 'local GPU'})"
    return f"retrieval only - {_llm['error']}"


def ask(kb: KnowledgeBase, question: str, lang: str = "de", inventory_snapshot: str | None = None, k: int = 4) -> dict:
    t0 = time.perf_counter()
    chunks = kb.retrieve(question, lang, k)
    prompt, sources = build_context(chunks, inventory_snapshot, lang)
    if _llm["model"] is not None:
        try:
            answer = generate(prompt + f"\n\nFrage: {question}", SYSTEM[lang]); mode = llm_status()
        except Exception as e:  # noqa: BLE001 - e.g. ZeroGPU quota exhausted for this visitor
            answer = None; mode = f"retrieval only - {type(e).__name__}: {str(e)[:100]}"
    else:
        answer = None; mode = llm_status()
    if answer is None:  # retrieval-only: quote the best passage verbatim, clearly labelled, never paraphrased
        best = chunks[0] if chunks else None
        answer = (f"(Kein Sprachmodell verfügbar - wörtlicher Auszug der besten Fundstelle [1]:)\n\n{best['text']}" if lang == "de" else
                  f"(No language model available - verbatim excerpt of the best match [1]:)\n\n{best['text']}") if best else REFUSAL[lang]
    return {"answer": answer, "sources": sources, "mode": mode, "seconds": round(time.perf_counter() - t0, 2)}
