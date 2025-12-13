# PROJECT_OVERVIEW.md — MillPresenter

## Purpose
MillPresenter is a Python application that analyzes videos of a transparent rotating grinding drum and produces trustworthy, explainable overlays of detected metallic beads. The system is built for non-technical users during demonstrations: stability and visual trust matter more than per-frame perfection.

## Problem Summary
Input videos (1080p or 4K) show a crowded scene with shiny metallic beads (solid and hollow/annular) inside a rotating drum. The scene contains strong specular reflections, glare, motion blur, occlusions, shadows, and structural drum elements (rim, bolts, inner ring) that create false positives.

The pipeline must detect beads in pixel-space, then (only after detection) convert to millimeters and classify into size bins.

## Key Physical Ground Truth
True nominal diameters (must be used consistently):
- 3.94 mm (≈ 4 mm)
- 5.79 mm (≈ 6 mm)
- 7.63 mm (≈ 8 mm)
- 9.90 mm (≈ 10 mm)

## Hard Constraints / Invariants
- Classical computer vision only (no deep learning).
- CPU-only, deterministic results for identical inputs.
- Offline detection pass produces cached outputs; playback reads cache only.
- Detection operates purely in pixel-space:
  - outputs: (x, y, r_px, conf, optional cls later)
- Calibration (px_per_mm) is applied only after detection for:
  - px→mm conversion
  - size classification
  - optional rendering adjustments
- Changing px_per_mm must not change detected (x, y, r_px) for the same frames.

## Typical Failure Sources
- Rim/bolts/purple ring structures producing circular-like edges → false detections.
- Specular glare causing over-segmentation / phantom centers.
- Motion blur causing elongated streaks, broken edges, merged blobs.
- Dense packing causing touching beads → merged candidates.

## Desired Success Definition
- Stable counts over time windows (not perfect per frame).
- Consistent size distributions over time windows.
- Confidence behaves meaningfully (thresholdable; glare should reduce confidence, not inflate it).
- Overlays look visually coherent and trustworthy during playback.

## Pipeline Phases (High Level)
(Order is enforced by MAIN.md unless PM overrides)
1) Drum geometry & ROI stabilization
2) Golden frames lock (baseline validation set)
3) Preprocessing stabilization
4) Candidate generation (pixel-space only)
5) Confidence definition
6) Filtering and cleanup
7) Calibration and size classification
8) Quality metrics
9) Visualization & playback features (incl. slow-mo UX, cache-backed)
10) Export & delivery

## Outputs (Conceptual)
- Per-frame overlay PNG(s) with optional toggles by size class.
- Structured detections per frame:
  - frame_id, timestamp, detections: [{x, y, r_px, conf, cls?}]
- run_manifest.json:
  - config, inputs, frames tested, artifact paths, timing summary, version hash/tag.

## Repo Workflow Authority
See:
- MAIN.md (highest authority)
- CURRENT_STEP.md (active step contract)
- PM_REVIEW_POLICY.md (approval gate)
- ACCEPTANCE_METRICS.md (what “good enough” means)
- iteration_tracker.md (experimental evidence log)
- KNOWN_ISSUES.md (live state of problems / risks)
