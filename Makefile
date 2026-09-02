.PHONY: up down deploy smoke edge dataset train eval export bench test test-edge lint seed rag-eval
up:        ; docker compose up -d --build
down:      ; docker compose down
deploy:    ; scripts/deploy.sh
smoke:     ; scripts/smoke.sh
edge:      ; docker compose --profile edge up --build pi-edge
dataset:   ; cd training && python build_public_dataset.py
train:     ; cd training && python train.py
eval:      ; cd training && python eval_report.py
export:    ; cd training && python export_onnx.py
bench:     ; cd edge && python bench.py
test:      ; cd api && pytest -q
test-edge: ; cd edge && pytest -q
lint:      ; ruff check api edge training vlm rag scripts
seed:      ; docker compose exec api python -m app.seed && docker compose exec api python -m app.rag_ingest
rag-eval:  ; python rag/eval/run_rag_eval.py --api $${WEB_URL:-http://localhost:8080}
