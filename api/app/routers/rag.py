import os
import sys

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Item, ReuseSuggestion
from app.schemas import AskIn, AskOut, SuggestionOut
from app.services.rag import ask

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "..", "rag"))
r = APIRouter(prefix="/api", tags=["knowledge"])

@r.post("/ask", response_model=AskOut)
async def ask_kb(body: AskIn, db: Session = Depends(get_db)):
    answer, sources, model = await ask(db, body.question, body.lang, body.k, include_inventory=True)
    return AskOut(answer=answer, sources=sources, model=model)

@r.post("/items/{item_id}/suggest", response_model=SuggestionOut)
async def suggest(item_id: int, lang: str = "de", db: Session = Depends(get_db)):
    it = db.get(Item, item_id)
    if not it: raise HTTPException(404, "item not found")
    mat = it.material.name if it.material else "unbekanntes Material"
    graph_terms = []
    try:
        from graph import neighbours  # GraphRAG expansion
        graph_terms = neighbours(mat)
    except Exception:
        pass
    q = (f"Wie kann ein Objekt '{it.label}' aus {mat} (Zustand: {it.condition or 'unbekannt'}) im Makerspace "
         f"wiederverwendet werden, und wie wird es sonst korrekt entsorgt?" if lang == "de" else
         f"How can a '{it.label}' made of {mat} (condition: {it.condition or 'unknown'}) be reused in a makerspace, "
         f"and how is it disposed of correctly otherwise?")
    answer, sources, model = await ask(db, q, lang, 4, graph_terms)
    s = ReuseSuggestion(item_id=item_id, text=answer, sources=sources, model=model)
    db.add(s); db.commit(); db.refresh(s); return s
