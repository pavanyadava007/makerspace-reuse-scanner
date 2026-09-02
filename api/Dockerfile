# Build context is the REPO ROOT (see docker-compose.yml) so that vlm/ and rag/ ship inside the image.
# Layout inside the image: /srv/api (this app), /srv/vlm, /srv/rag - matching the repo layout, so the
# sys.path lookups in app/services/material.py and app/routers/rag.py (../../../vlm, ../../../rag) resolve.
FROM python:3.11-slim
ARG WITH_VLM=0
WORKDIR /srv/api
COPY api/requirements.txt api/requirements-vlm.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
 && if [ "$WITH_VLM" = "1" ]; then pip install --no-cache-dir -r requirements-vlm.txt; fi
COPY api/ /srv/api/
COPY vlm/ /srv/vlm/
COPY rag/ /srv/rag/
ENV PYTHONPATH=/srv/api IMAGE_DIR=/srv/api/images CORPUS_DIR=/srv/rag/corpus
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
