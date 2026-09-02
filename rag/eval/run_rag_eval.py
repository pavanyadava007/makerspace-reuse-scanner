"""Run the hand-verified RAG question set against a LIVE API (real Ollama) and write reports/rag_eval_<date>.{md,json}.
This is the only place RAG quality numbers may come from — never edit them by hand.

    python rag/eval/run_rag_eval.py [--api http://localhost:8080] [--k 4] [--tag vector-only]

Scores per question (see questions.yaml for the fields):
  doc_hit      expected corpus file is among the cited sources
  section_hit  expected heading is among the cited sources (only questions that name one)
  answer_ok    corpus: one of `must_contain` appears in the answer · refuse: the model declined ·
               inventory: `live-inventory` is cited AND the real DB count appears in the answer
`score()` is pure and unit-tested in api/tests/test_rag_eval.py; only `main()` talks to the API.
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import statistics
import sys
import time
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
REFUSAL = [r"kein(e|en)? (hinweis|hinweise|informationen|angaben|aussage)", r"nicht (im|aus dem) kontext",
           r"kontext (gibt|enthält|liefert) (nichts|keine)", r"nicht enthalten", r"nicht beantworten",
           r"kein(e)? (passende|entsprechende)", r"liefert keine", r"geht (nicht|nichts) hervor",
           r"insufficient", r"not covered", r"no information", r"does not (contain|cover|mention|provide|include)",
           r"cannot answer", r"can't answer", r"not enough", r"not (mentioned|addressed|available|provided)", r"unable to",
           r"context (does not|doesn't)",
           # generic "cannot find / cannot provide" wordings (seen in real runs: "Ich kann diese Information nicht finden.")
           r"nicht (finden|liefern|angeben|sagen)", r"kann (ich )?(diese|die|dazu|hierzu|keine)[^.]{0,40}nicht",
           r"can(not|'t) (find|provide|locate|tell)", r"no (details|data|mention)", r"not aware of", r"(no|any) context (that )?mentions?",
           r"nothing (in|about)", r"fehlt an informationen", r"fehlen (informationen|angaben)"]


def score(q: dict, answer: str, sources: list[dict], inventory_count: int | None = None) -> dict:
    docs = {s.get("doc") for s in sources}; sections = {s.get("section") for s in sources}
    out = {"id": q["id"], "kind": q["kind"], "lang": q["lang"], "q": q["q"], "doc_hit": None, "section_hit": None, "answer_ok": None}
    low = answer.lower()
    if q["kind"] == "corpus":
        out["doc_hit"] = q["expect_doc"] in docs
        if q.get("expect_section"): out["section_hit"] = q["expect_section"] in sections
        pats = q.get("must_contain") or []
        out["answer_ok"] = any(re.search(p.lower(), low) for p in pats) if pats else None
    elif q["kind"] == "refuse":
        out["answer_ok"] = any(re.search(p, low) for p in REFUSAL)
    elif q["kind"] == "inventory":
        cited = "live-inventory" in docs
        out["doc_hit"] = cited
        out["answer_ok"] = cited and inventory_count is not None and re.search(rf"(?<!\d){inventory_count}(?!\d)", answer) is not None
    return out


def summarise(rows: list[dict], latencies: list[float]) -> dict:
    def rate(key, kind=None):
        vals = [r[key] for r in rows if r[key] is not None and (kind is None or r["kind"] == kind)]
        return {"n": len(vals), "hits": sum(vals), "rate": round(sum(vals) / len(vals), 3) if vals else None}
    return {"doc_hit": rate("doc_hit", "corpus"), "section_hit": rate("section_hit", "corpus"),
            "answer_ok_corpus": rate("answer_ok", "corpus"), "refusal_ok": rate("answer_ok", "refuse"),
            "inventory_ok": rate("answer_ok", "inventory"),
            "latency_s_median": round(statistics.median(latencies), 2) if latencies else None,
            "latency_s_max": round(max(latencies), 2) if latencies else None}


def to_markdown(date: str, api: str, model: str, k: int, summ: dict, rows: list[dict], answers: dict[int, str]) -> str:
    def pct(m): return f"{m['hits']}/{m['n']} ({m['rate']*100:.0f} %)" if m["n"] else "–"
    tick = lambda v: "–" if v is None else ("✓" if v else "✗")  # noqa: E731
    lines = [f"# RAG evaluation — {date}",
             f"API `{api}` · generation model `{model}` · k={k} · {len(rows)} questions from `questions.yaml`", "",
             "| metric | result |", "|---|---|",
             f"| corpus questions: expected document cited | {pct(summ['doc_hit'])} |",
             f"| corpus questions: expected section cited | {pct(summ['section_hit'])} |",
             f"| corpus questions: answer contains a verified key fact | {pct(summ['answer_ok_corpus'])} |",
             f"| out-of-corpus questions: model declined | {pct(summ['refusal_ok'])} |",
             f"| inventory questions: `live-inventory` cited and real count quoted | {pct(summ['inventory_ok'])} |",
             f"| latency per question (median / max, warm model) | {summ['latency_s_median']} s / {summ['latency_s_max']} s |", "",
             "| # | kind | lang | question | doc | section | answer |", "|---|---|---|---|---|---|---|"]
    lines += [f"| {r['id']} | {r['kind']} | {r['lang']} | {r['q']} | {tick(r['doc_hit'])} | {tick(r['section_hit'])} | "
              f"{tick(r['answer_ok'])} |" for r in rows]
    lines += ["", "Single run at temperature 0.2: wording varies between runs. `doc`/`section` are exact source checks; `answer` for "
              "corpus questions is a key-fact regex, for refuse questions a phrase heuristic (a ✗ there can be a decline in an unlisted "
              "wording — read the verbatim answer below before counting it as a hallucination).", "",
              "## Answers (verbatim, for manual review)", ""]
    lines += [f"**{r['id']}. {r['q']}**  \n{answers[r['id']].strip()}\n" for r in rows]
    return "\n".join(lines) + "\n"


def main():
    import httpx
    ap = argparse.ArgumentParser(); ap.add_argument("--api", default="http://localhost:8080"); ap.add_argument("--k", type=int, default=4)
    ap.add_argument("--out", default=str(HERE / "reports")); ap.add_argument("--tag", default="", help="suffix for the report file name")
    a = ap.parse_args()
    qs = yaml.safe_load(open(HERE / "questions.yaml", encoding="utf-8"))
    c = httpx.Client(base_url=a.api, timeout=300, trust_env=False)
    rows, lat, answers, model = [], [], {}, "?"
    c.post("/api/ask", json={"question": "warm-up", "lang": "en", "k": 1})  # load the model once; not scored
    for q in qs:
        inv = None
        if q["kind"] == "inventory":
            items = c.get("/api/items", params={"label": q["label"], "limit": 500}).json(); inv = sum(i["quantity"] for i in items)
        t = time.perf_counter(); r = c.post("/api/ask", json={"question": q["q"], "lang": q["lang"], "k": a.k}); r.raise_for_status()
        lat.append(time.perf_counter() - t); body = r.json(); model = body["model"]
        rows.append(score(q, body["answer"], body["sources"], inv)); answers[q["id"]] = body["answer"]
        r0 = rows[-1]; print(f"[{q['id']:>2}] doc={r0['doc_hit']} sec={r0['section_hit']} ans={r0['answer_ok']} {lat[-1]:.1f}s  {q['q']}")
    summ = summarise(rows, lat); date = datetime.date.today().isoformat(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    name = f"rag_eval_{date}" + (f"_{a.tag}" if a.tag else "")
    (out / f"{name}.md").write_text(to_markdown(date, a.api, model, a.k, summ, rows, answers), encoding="utf-8")
    json.dump({"date": date, "api": a.api, "model": model, "k": a.k, "tag": a.tag, "summary": summ, "rows": rows, "answers": answers},
              open(out / f"{name}.json", "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(json.dumps(summ, indent=2)); return 0


if __name__ == "__main__": sys.exit(main())
