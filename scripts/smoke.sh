#!/usr/bin/env bash
# End-to-end smoke test against a running deployment, through the web proxy (nginx → api).
#   WEB_URL=http://host:8080 scripts/smoke.sh        (ASK=0 skips the Ollama round-trip)
set -uo pipefail
WEB="${WEB_URL:-http://localhost:8080}"; fail=0
chk() { if [ "$2" = OK ]; then echo "  ✓ $1"; else echo "  ✗ $1 - $2"; fail=1; fi; }
echo "[smoke] $WEB"
code=$(curl -s -o /dev/null -w '%{http_code}' -m 10 "$WEB/");                          chk "web serves index (HTTP $code)" "$([ "$code" = 200 ] && echo OK || echo "got $code")"
body=$(curl -s -m 10 "$WEB/api/stats");                                                 chk "GET /api/stats" "$(echo "$body" | grep -q '"items"' && echo OK || echo "$body")"
n=$(curl -s -m 10 "$WEB/api/materials" | grep -o '"name"' | wc -l);                     chk "GET /api/materials seeded ($n rows)" "$([ "$n" -ge 15 ] && echo OK || echo "only $n - run make seed")"
body=$(curl -s -m 10 "$WEB/api/model");                                                 chk "GET /api/model has eval report" "$(echo "$body" | grep -q '"map50"' && echo OK || echo "no eval json mounted: $body")"
body=$(curl -s -m 10 "$WEB/api/demo");                                                  chk "GET /api/demo lists videos" "$(echo "$body" | grep -q '"videos"' && echo OK || echo "$body")"
code=$(curl -s -o /dev/null -w '%{http_code}' -m 10 -H 'Connection: Upgrade' -H 'Upgrade: websocket' -H 'Sec-WebSocket-Version: 13' \
       -H 'Sec-WebSocket-Key: c21va2V0ZXN0a2V5MTIzNA==' "$WEB/ws/live");                 chk "WS /ws/live upgrades through proxy (HTTP $code)" "$([ "$code" = 101 ] && echo OK || echo "got $code")"
body=$(curl -s -m 10 -X POST "$WEB/api/items" -H 'Content-Type: application/json' -d '{"label":"smoke_test","quantity":1}')
id=$(echo "$body" | sed -n 's/.*"id":\([0-9]*\).*/\1/p');                               chk "POST /api/items → id $id" "$([ -n "$id" ] && echo OK || echo "$body")"
if [ -n "$id" ]; then
  code=$(curl -s -o /dev/null -w '%{http_code}' -m 10 -X PATCH "$WEB/api/items/$id" -H 'Content-Type: application/json' -d '{"status":"reused"}'); chk "PATCH /api/items/$id" "$([ "$code" = 200 ] && echo OK || echo "got $code")"
  code=$(curl -s -o /dev/null -w '%{http_code}' -m 10 -X DELETE "$WEB/api/items/$id");   chk "DELETE /api/items/$id" "$([ "$code" = 204 ] && echo OK || echo "got $code")"
fi
if [ "${ASK:-1}" != 0 ]; then
  t0=$(date +%s); body=$(curl -s -m 300 -X POST "$WEB/api/ask" -H 'Content-Type: application/json' -d '{"question":"Wohin mit PLA-Fehldrucken?","lang":"de"}')
  chk "POST /api/ask answers with citations ($(( $(date +%s) - t0 )) s)" "$(echo "$body" | grep -q '"sources":\[{' && echo "$body" | grep -q 'kunststoffe_3d_druck' && echo OK || echo "$body" | head -c 300)"
fi
[ $fail = 0 ] && echo "[smoke] all checks passed" || { echo "[smoke] FAILED"; exit 1; }
