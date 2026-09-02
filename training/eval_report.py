"""Evaluate best.pt on the held-out TEST split and write reports/eval_<date>.md - the only place mAP numbers may come from."""
import datetime
import json
import os

from ultralytics import YOLO

RUNS = os.path.abspath("runs")
m = YOLO(os.getenv("MRS_WEIGHTS", os.path.join(RUNS, "yolo11n_makerspace", "weights", "best.pt")))
r = m.val(data="data.yaml", split="test", imgsz=640, plots=True, project=RUNS, name="eval", exist_ok=True)
names = m.names
rows = "\n".join(f"| {names[i]} | {r.box.ap50[k]:.3f} | {r.box.ap[k]:.3f} |" for k, i in enumerate(r.box.ap_class_index))
d = datetime.date.today().isoformat()
md = f"""# Evaluation - {d}
Model: yolo11n fine-tuned · split: test · imgsz 640 · conf 0.001 · IoU 0.7 (ultralytics default)

| overall | mAP50 | mAP50-95 | precision | recall |
|---|---|---|---|---|
| all classes | {r.box.map50:.3f} | {r.box.map:.3f} | {r.box.mp:.3f} | {r.box.mr:.3f} |

| class | AP50 | AP50-95 |
|---|---|---|
{rows}

Confusion matrix: `runs/eval/confusion_matrix.png`. Known weaknesses are listed below by hand after inspection.
"""
open(f"reports/eval_{d}.md", "w").write(md)
json.dump({"date": d, "map50": r.box.map50, "map": r.box.map, "precision": r.box.mp, "recall": r.box.mr,
           "per_class": {names[i]: {"ap50": float(r.box.ap50[k]), "ap": float(r.box.ap[k])}
                         for k, i in enumerate(r.box.ap_class_index)}},
          open(f"reports/eval_{d}.json", "w"), indent=2)
print(md)
