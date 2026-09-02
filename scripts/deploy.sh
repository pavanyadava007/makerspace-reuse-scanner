#!/usr/bin/env bash
# One-command deployment of the whole stack on a Docker host (laptop, on-prem box, cloud VM).
#   scripts/deploy.sh                 # db + ollama + api + web (+ demo-edge when models/demo_belt.mp4 exists)
#   DEMO=0 scripts/deploy.sh          # without the built-in conveyor demo
#   GPU=0 scripts/deploy.sh           # force CPU Ollama even if nvidia-smi is present
#   EXTRA_COMPOSE=my.override.yml …   # host-specific overrides (ports etc.) that must not live in the repo
# Steps: .env → compose up --build → wait for /healthz → pull Ollama models once → seed materials + corpus → smoke test.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] || { cp .env.example .env; echo "[deploy] created .env from .env.example"; }
FILES=(-f docker-compose.yml)
if [ "${GPU:-auto}" != 0 ] && command -v nvidia-smi >/dev/null 2>&1 && docker info 2>/dev/null | grep -qi nvidia; then
  FILES+=(-f docker-compose.gpu.yml); echo "[deploy] NVIDIA runtime found → Ollama on GPU"
else
  echo "[deploy] Ollama on CPU (answers take several seconds)"
fi
[ -n "${EXTRA_COMPOSE:-}" ] && FILES+=(-f "$EXTRA_COMPOSE")
PROFILE=()
if [ "${DEMO:-1}" != 0 ] && [ -f models/demo_belt.mp4 ] && [ -f models/yolo11n_makerspace.onnx ]; then
  PROFILE=(--profile demo); echo "[deploy] demo-edge enabled (models/demo_belt.mp4 through the real detector)"
fi
dc() { docker compose "${FILES[@]}" "${PROFILE[@]}" "$@"; }

dc up -d --build
echo -n "[deploy] waiting for api"
for _ in $(seq 1 60); do dc exec -T api python -c "import urllib.request as u; u.urlopen('http://localhost:8000/healthz')" >/dev/null 2>&1 && break; echo -n .; sleep 2; done; echo
for m in "${OLLAMA_MODEL:-llama3.1:8b}" "${EMBED_MODEL:-nomic-embed-text}"; do
  if dc exec -T ollama ollama list 2>/dev/null | grep -q "^${m%%:*}"; then echo "[deploy] ollama model present: $m"
  else echo "[deploy] pulling $m (once, several GB)"; dc exec -T ollama ollama pull "$m"; fi
done
dc exec -T api python -m app.seed
dc exec -T api python -m app.rag_ingest
WEB_URL="${WEB_URL:-http://localhost:8080}" scripts/smoke.sh
echo "[deploy] done → ${WEB_URL:-http://localhost:8080}   (API docs: ${WEB_URL:-http://localhost:8080}/api/docs is proxied? no - use the api port, default :8000/docs)"
