"""Chunk markdown corpus by heading, embed via Ollama, upsert into rag_chunk. Run: python -m app.rag_ingest"""
import asyncio
import glob
import os
import re

from sqlalchemy import delete

from app.config import settings
from app.db import SessionLocal
from app.models import RagChunk
from app.services.rag import DOC_PREFIX, embed


def chunks_from_md(path):
    doc = os.path.basename(path); lang = "de" if doc.endswith(".de.md") else "en"
    text = open(path, encoding="utf-8").read()
    parts = re.split(r"^(#{1,3} .+)$", text, flags=re.MULTILINE)
    section = "intro"
    for p in parts:
        if p.startswith("#"): section = p.lstrip("# ").strip(); continue
        body = p.strip()
        if len(body) > 40: yield doc, section, lang, body[:1800]

async def main():
    rows = [c for f in glob.glob(os.path.join(settings.corpus_dir, "*.md")) for c in chunks_from_md(f)]
    vecs = await embed([f"{r[1]}\n{r[3]}" for r in rows], prefix=DOC_PREFIX)  # heading + body → embedding; body alone is stored
    with SessionLocal() as db:
        db.execute(delete(RagChunk))
        db.add_all([RagChunk(doc=d, section=s, lang=lg, text=t, embedding=v)
                    for (d, s, lg, t), v in zip(rows, vecs, strict=True)])
        db.commit()
    print(f"ingested {len(rows)} chunks from {len(set(r[0] for r in rows))} docs")

if __name__ == "__main__": asyncio.run(main())
