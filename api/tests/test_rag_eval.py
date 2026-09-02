"""Scoring logic of rag/eval/run_rag_eval.py (pure functions; the live run needs Ollama and is not part of CI)."""
import os
import sys

import yaml

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "rag", "eval"))
from run_rag_eval import HERE, score, summarise, to_markdown  # noqa: E402

CORPUS = os.path.join(os.path.dirname(__file__), "..", "..", "rag", "corpus")


def test_question_set_is_consistent_with_corpus():
    qs = yaml.safe_load(open(HERE / "questions.yaml", encoding="utf-8"))
    assert len(qs) >= 20 and len({q["id"] for q in qs}) == len(qs)
    docs = set(os.listdir(CORPUS))
    for q in qs:
        assert q["kind"] in ("corpus", "refuse", "inventory") and q["lang"] in ("de", "en")
        if q["kind"] == "corpus":
            assert q["expect_doc"] in docs, q
            if q.get("expect_section"):   # the heading really exists in that file
                assert f"## {q['expect_section']}" in open(os.path.join(CORPUS, q["expect_doc"]), encoding="utf-8").read(), q
            assert q["expect_doc"].endswith(f".{q['lang']}.md")  # language filter would otherwise hide the expected doc
        if q["kind"] == "inventory": assert q["label"]


def test_score_corpus_refuse_inventory():
    q = {"id": 1, "kind": "corpus", "lang": "de", "q": "x", "expect_doc": "a.de.md", "expect_section": "S", "must_contain": ["Restmüll"]}
    src = [{"doc": "a.de.md", "section": "S"}, {"doc": "live-inventory", "section": "aktueller Bestand"}]
    r = score(q, "In den Restmüll [1].", src); assert (r["doc_hit"], r["section_hit"], r["answer_ok"]) == (True, True, True)
    r = score(q, "Keine Ahnung.", [{"doc": "b.de.md", "section": "T"}])
    assert (r["doc_hit"], r["section_hit"], r["answer_ok"]) == (False, False, False)
    rq = {"id": 2, "kind": "refuse", "lang": "en", "q": "y"}
    assert score(rq, "The context does not contain information about this.", [])["answer_ok"]
    assert score(rq, "Der Kontext liefert keine Hinweise dazu.", [])["answer_ok"]
    assert score(rq, "Ich habe keinen Hinweis auf radioaktive Abfälle im Kontext.", [])["answer_ok"]   # missed by the first scorer
    assert score(rq, "Ich kann diese Information nicht finden.", [])["answer_ok"]                     # missed by the second
    assert score(rq, "I'm not aware of any context that mentions titanium.", [])["answer_ok"]         # missed by the third
    assert not score(rq, "Schrott wird mit 19 % besteuert; nicht in den Restmüll.", [])["answer_ok"]  # a real answer with 'nicht'

    assert not score(rq, "Titanium melts at 1668 °C.", [])["answer_ok"]
    iq = {"id": 3, "kind": "inventory", "lang": "de", "q": "z", "label": "screw"}
    assert score(iq, "Wir haben 12 Schrauben [2].", src, 12)["answer_ok"]
    assert not score(iq, "Wir haben 120 Schrauben [2].", src, 12)["answer_ok"]     # 12 inside 120 must not count
    assert not score(iq, "Wir haben 12 Schrauben.", [{"doc": "a.de.md", "section": "S"}], 12)["answer_ok"]  # not grounded


def test_summarise_and_markdown():
    cq = {"id": 1, "kind": "corpus", "lang": "de", "q": "a", "expect_doc": "d", "must_contain": ["x"]}
    rows = [score(cq, "x", [{"doc": "d", "section": "s"}]),
            score({"id": 2, "kind": "refuse", "lang": "en", "q": "b"}, "insufficient context", [])]
    s = summarise(rows, [1.0, 3.0])
    assert s["doc_hit"] == {"n": 1, "hits": 1, "rate": 1.0} and s["section_hit"]["n"] == 0 and s["refusal_ok"]["rate"] == 1.0
    assert s["latency_s_median"] == 2.0
    md = to_markdown("2026-09-02", "http://x", "m", 4, s, rows, {1: "x", 2: "insufficient context"})
    assert md.startswith("# RAG evaluation - 2026-09-02") and "| 1 | corpus | de | a | ✓ | - | ✓ |" in md
