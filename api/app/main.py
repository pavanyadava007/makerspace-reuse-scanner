from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import demo, detections, items, rag, ws

app = FastAPI(title="Makerspace Reuse Scanner API", version="0.3.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
for m in (items, detections, rag, ws, demo): app.include_router(m.r)

@app.get("/healthz")
def healthz(): return {"ok": True}
