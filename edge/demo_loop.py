"""Demo controller for the `demo-edge` container: runs capture.py on a selectable video.

The API writes /demo/control.json ({"video": "/models/demo_belt.mp4" | null}); this loop starts, switches
or stops the capture subprocess accordingly. No file → the DEMO_DEFAULT video. A crashed capture is retried.
"""
from __future__ import annotations

import json
import os
import subprocess
import time

CTRL = os.getenv("DEMO_CTRL", "/demo/control.json")
DEFAULT = os.getenv("DEMO_DEFAULT", "/models/demo_belt.mp4")


def wanted() -> str | None:
    try:
        with open(CTRL) as f: return json.load(f).get("video")
    except (FileNotFoundError, json.JSONDecodeError):
        return DEFAULT if os.path.isfile(DEFAULT) else None


def start(video: str) -> subprocess.Popen:
    name = os.path.basename(video)
    env = {**os.environ, "EDGE_CAMERA": video, "EDGE_DEVICE": f"demo ({name}, in-container CPU)"}
    print(f"[demo] starting capture on {video}", flush=True)
    return subprocess.Popen(["python", "capture.py"], env=env)


def main():
    proc: subprocess.Popen | None = None; cur: str | None = None
    while True:
        want = wanted()
        if want != cur or (proc is not None and proc.poll() is not None):
            if proc is not None and proc.poll() is None:
                proc.terminate()
                try: proc.wait(timeout=10)
                except subprocess.TimeoutExpired: proc.kill()
            proc, cur = None, want
            if want and os.path.isfile(want): proc = start(want)
            elif want: print(f"[demo] video not found: {want}", flush=True)
            else: print("[demo] stopped (no video selected)", flush=True)
        time.sleep(2)


if __name__ == "__main__":
    main()
