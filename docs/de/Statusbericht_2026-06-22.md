# Statusbericht 1 — 22.06.2026

**Berichtszeitraum:** 01.06.–22.06.2026 · **Phase:** AP1, Beginn AP2

## Erledigt
- Klassenliste festgelegt (12 Makerspace-Klassen + 3 Materialbrücken aus TrashNet/TACO), siehe `training/classes.yaml`.
- Label-Studio-Projekt aufgesetzt; Annotationsrichtlinie: enge Boxen, jede Instanz einzeln, Zustand als Bildattribut.
- Aufnahmesitzungen an der Werkbank in drei Lichtsituationen; Split nach Sitzung, um Near-Duplicates zu vermeiden.

## Offen / Probleme
- Klasse `screw` stark überrepräsentiert; `motor` und `battery` unterrepräsentiert → gezielte Nachaufnahmen geplant.
- Reflexionen auf Acrylglas erschweren Boxen; Entscheidung: matte Unterlage für Aufnahmen.

## Nächste Schritte
- Erstes Finetuning (Freeze 10 Layer, 80 Epochen) und Baseline-Report.
- ADR-0001 (YOLO11n + ONNX) schreiben.

## Kennzahlen
- Annotierte Bilder: nicht im Repository dokumentiert (Zähler in Label Studio; Ziel MS1 ≥ 400) · Zeit im Plan: ja · Budget: n/a (privat)
