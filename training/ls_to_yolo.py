"""Convert a Label Studio JSON export to YOLO txt labels. Usage: python ls_to_yolo.py export.json"""
import json
import os
import sys

import yaml

names = yaml.safe_load(open("classes.yaml"))["names"]
idx = {v: k for k, v in names.items()}
tasks = json.load(open(sys.argv[1]))
os.makedirs("dataset/labels/all", exist_ok=True)
for t in tasks:
    stem = os.path.splitext(os.path.basename(t["data"]["image"]))[0]
    lines = []
    for ann in t.get("annotations", []):
        for r in ann["result"]:
            if r["type"] != "rectanglelabels": continue
            v = r["value"]; cx = (v["x"] + v["width"] / 2) / 100; cy = (v["y"] + v["height"] / 2) / 100
            lines.append(f'{idx[v["rectanglelabels"][0]]} {cx:.6f} {cy:.6f} {v["width"]/100:.6f} {v["height"]/100:.6f}')
    open(f"dataset/labels/all/{stem}.txt", "w").write("\n".join(lines))
print(f"wrote {len(tasks)} label files")
