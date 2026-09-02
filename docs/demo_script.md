# Demo script (3 minutes)

0:00 `docker compose up -d` already running. Open http://localhost:8080 — header shows "no edge node connected".
0:20 Start edge on laptop webcam: `cd edge && python capture.py`. Header pill appears with device label + FPS.
0:40 Hold a filament spool, a PCB, a screw in front of the camera. Boxes appear colour-coded by material; feed on the right links to items.
1:10 Inventory tab: items were created automatically, deduped; filter by status; stats line updates.
1:30 Click the PCB item. Show detection history with backend column ("clip-vitb32" vs "class-prior"), edit condition, set status.
2:00 "Suggest reuse" (Deutsch). Read the cited answer; hover sources → `elektronik_batterien.de.md › Wiederverwendung von Elektronik`.
2:30 Show `training/reports/eval_*.md` and `edge/results/bench_*.json` — "numbers come only from these files."
2:50 Show `docs/de/Statusbericht_*.md` and ADR-0004. Close.
