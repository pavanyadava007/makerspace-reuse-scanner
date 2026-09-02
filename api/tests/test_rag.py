"""RAG pipeline without Ollama: real corpus chunking, real pgvector retrieval, mocked embed/generate."""
import hashlib
import os

import numpy as np
import pytest
from app.config import settings
from app.db import SessionLocal
from app.models import RagChunk, ReuseSuggestion
from app.rag_ingest import chunks_from_md
from app.services import rag as rag_service
from sqlalchemy import delete

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
CORPUS = os.path.join(ROOT, "rag", "corpus")


def fake_vec(text: str) -> list[float]:
    """Deterministic pseudo-embedding: identical text → identical vector; question containing a heading
    word lands near that chunk because we seed on the first 12 characters of the section title."""
    for p in ("search_document: ", "search_query: "): text = text.removeprefix(p)
    seed = int(hashlib.md5(text.strip().lower()[:12].encode()).hexdigest(), 16) % (2**32)
    v = np.random.default_rng(seed).standard_normal(768); return (v / np.linalg.norm(v)).tolist()


def test_corpus_chunks_by_heading():
    docs = sorted(os.listdir(CORPUS)); assert len(docs) == 5
    chunks = [c for d in docs for c in chunks_from_md(os.path.join(CORPUS, d))]
    assert len(chunks) >= 20
    de = [c for c in chunks if c[2] == "de"]; en = [c for c in chunks if c[2] == "en"]
    assert de and en and all(c[0].endswith(".de.md") for c in de)
    assert any(c[1] == "Batterien und Akkus (BattG)" for c in chunks)      # heading → section
    assert all(len(c[3]) <= 1800 and len(c[3]) > 40 for c in chunks)


def test_graph_neighbours():
    import sys
    sys.path.append(os.path.join(ROOT, "rag"))
    from graph import neighbours
    assert "filament recycler" in neighbours("PLA plastic") and "Restmüll" in neighbours("PLA plastic")
    assert "BattG" in neighbours("lithium battery")
    assert neighbours("unobtainium") == []


@pytest.fixture
def seeded_chunks(monkeypatch):
    rows = [c for d in sorted(os.listdir(CORPUS)) for c in chunks_from_md(os.path.join(CORPUS, d))]
    with SessionLocal() as db:
        db.execute(delete(RagChunk))
        db.add_all([RagChunk(doc=d, section=s, lang=lg, text=t, embedding=fake_vec(s)) for d, s, lg, t in rows]); db.commit()

    async def embed(texts, prefix=""): return [fake_vec(prefix + t) for t in texts]
    calls = {}

    async def generate(prompt, system):
        calls["prompt"], calls["system"] = prompt, system
        return "Pole abkleben und in die Sammelbox [1]."
    monkeypatch.setattr(rag_service, "embed", embed); monkeypatch.setattr(rag_service, "generate", generate)
    return calls


async def test_ask_cites_retrieved_chunks(seeded_chunks):
    with SessionLocal() as db:
        answer, sources, model = await rag_service.ask(db, "Batterien und Akkus (BattG)", "de", k=3)
    assert answer.endswith("[1].") and model == settings.ollama_model
    assert sources[0]["section"] == "Batterien und Akkus (BattG)" and sources[0]["n"] == 1
    assert [s["n"] for s in sources] == list(range(1, len(sources) + 1))
    assert all(s["lang"] == "de" for s in sources)                              # language filter applied
    p = seeded_chunks["prompt"]; assert p.startswith("Kontext:") and "[1] (elektronik_batterien.de.md › Batterien" in p
    assert "NUR den Kontext" in seeded_chunks["system"]


async def test_ask_graph_terms_add_chunks_without_duplicates(seeded_chunks):
    with SessionLocal() as db:
        terms = ["Metallschrott", "Altholz-Kategorien (AltholzV)"]
        _, sources, _ = await rag_service.ask(db, "Metallschrott", "de", k=2, graph_terms=terms)
    ids = [(s["doc"], s["section"]) for s in sources]
    assert len(ids) == len(set(ids)) and 2 <= len(ids) <= 2 + rag_service.LEXICAL_K + 2   # k + lexical + 2 graph terms
    assert ("metalle_und_altholz.de.md", "Altholz-Kategorien (AltholzV)") in ids


async def test_hybrid_retrieval_finds_rare_literal_terms(seeded_chunks):
    """The fake embedding of this question lands nowhere near the Altholz chunk (it is seeded on the first 12 characters),
    so only the full-text leg can bring in the one chunk that mentions 'Kamin' — the case that failed in rag/eval."""
    with SessionLocal() as db:
        _, sources, _ = await rag_service.ask(db, "Darf ich Sperrholzreste im Kamin verbrennen?", "de", k=2)
        assert ("metalle_und_altholz.de.md", "Altholz-Kategorien (AltholzV)") in [(s["doc"], s["section"]) for s in sources]
        _, sources, _ = await rag_service.ask(db, "Warum darf PVC nicht gelasert werden?", "de", k=2)
        assert ("kunststoffe_3d_druck.de.md", "Acrylglas (PMMA)") in [(s["doc"], s["section"]) for s in sources]
        assert all(s["lang"] == "de" for s in sources)                                      # language filter also on the lexical leg
        _, sources, _ = await rag_service.ask(db, "Wo ist der Bahnhof?", "de", k=2)          # no lexical match → k vector chunks only
        assert len(sources) == 2


def test_suggest_endpoint_persists_suggestion(client, seeded_chunks):
    i = client.post("/api/items", json={"label": "battery", "quantity": 1}).json()["id"]
    mats = {m["name"]: m["id"] for m in client.get("/api/materials").json()}
    if "lithium battery" in mats: client.patch(f"/api/items/{i}", json={"material_id": mats["lithium battery"]})
    r = client.post(f"/api/items/{i}/suggest?lang=de"); assert r.status_code == 200, r.text
    body = r.json(); assert "[1]" in body["text"] and body["sources"] and body["model"]
    assert client.get(f"/api/items/{i}").json()["suggestions"][0]["id"] == body["id"]
    with SessionLocal() as db: assert db.get(ReuseSuggestion, body["id"]).item_id == i
    r = client.post("/api/ask", json={"question": "Wohin mit PLA?", "lang": "de"}); assert r.status_code == 200 and r.json()["sources"]


async def test_ask_includes_live_inventory(seeded_chunks, client):
    client.post("/api/items", json={"label": "wood_offcut", "quantity": 7})
    with SessionLocal() as db:
        _, sources, _ = await rag_service.ask(db, "Wie viele Holzreste haben wir?", "de", k=2, include_inventory=True)
    assert sources[-1]["doc"] == "live-inventory"
    p = seeded_chunks["prompt"]
    assert "Live-Bestand" in p and "wood_offcut: " in p and "available 7" in p
    r = client.post("/api/ask", json={"question": "Was haben wir auf Lager?", "lang": "de"})   # endpoint wires it in
    assert any(s["doc"] == "live-inventory" for s in r.json()["sources"])
