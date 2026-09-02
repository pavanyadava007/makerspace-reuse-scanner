# Dataset

Two ways to fill this folder. Both produce `images/{train,val,test}` + `labels/{train,val,test}` in YOLO format for `../data.yaml`.

## A. Own photos (the real makerspace set - target)
| Source | Images | Purpose |
|---|---|---|
| Self-photographed (Pi Cam 3 + phone, makerspace bench, 3 lighting setups) | target ≥ 600 | all 15 classes, especially the 6 with no public data |

Annotate in Label Studio with `../label_studio_config.xml`; convert with `python ls_to_yolo.py export.json`.
Split 70/20/10 by **capture session**, not by image, to avoid near-duplicate leakage.

## B. Public data (v0-public - what the committed model was trained on)
`python build_public_dataset.py` downloads and converts LVIS (on COCO images), TACO, TrashNet, a Hugging Face cropped-PCB set and the
MVTec AD screw set, and adds copy-paste composites to the train split only. It writes `SOURCES.md` (per-class/split counts, licences,
caveats) and `stats.json`. Covered: screw, nut_bolt, pcb, motor, battery, tool, plastic_container, cardboard, glass.
**Not covered by any public set:** filament_spool, wood_offcut, cable, 3d_print_part, acrylic_sheet, metal_profile - these stay at 0
until photos from (A) are added; the 15-class head is kept so they can be added without changing the pipeline.

Actual counts live in `SOURCES.md` / `stats.json` (generated) and mAP in `../reports/` **only after measurement**. No numbers here are claims.
