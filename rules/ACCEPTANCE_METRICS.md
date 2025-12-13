
---

```md
# ACCEPTANCE_METRICS.md

## Purpose
Defines what “good enough” means for the Grinding Mill Detection Pipeline.
This prevents subjective decisions and keeps iteration disciplined.

These metrics are used by:
- `CURRENT_STEP.md` (VALIDATION section)
- `iteration_tracker.md` (evidence + PM approval)

---

## Core Philosophy
- Per-frame perfection is not required.
- Success is defined by **stability**, **visual trust**, and **consistent size distributions** over time windows/cycles.
- The pipeline is deterministic classical CV; 100% recall/precision is not achievable.

---

## Global Acceptance Rules (All Steps)

### A) Determinism (Hard Gate)
For identical inputs (same frames, same config):
- Output detections must be identical (same `(x,y,r_px)` set and same `conf` values up to defined rounding).
- Any non-determinism is a **blocking defect**.

### B) Evidence (Hard Gate)
Each step must produce:
- At least 1 overlay image (`.png`) per tested frame set, and
- At least 1 structured export (`.json/.csv/.jsonl`) when applicable.

### C) Pixel-space Protection (Hard Gate)
Calibration changes (`px_per_mm`) must not change:
- detected centers `(x,y)`
- detected radii `r_px`

If it changes, the step is **Blocked** until fixed.

---

## Detection Quality Metrics (Used When a Step Emits Detections)

These metrics are intentionally simple and practical.

### 1) Rim False Positives (Priority)
Goal: reduce false detections on bolts/rim/purple ring.
- Define a rim band: within `rim_band_px` of the drum edge.
- Metric: `rim_fp_per_frame` (count) and/or `rim_fp_rate` (% of detections).
- Acceptance: must not regress vs baseline beyond a threshold defined per STEP.

### 2) Count Stability Over Window (Trust Metric)
- Over a window of N frames, track `detections_per_frame`.
- Metric: coefficient of variation (CV) or std/mean.
- Acceptance: must not increase significantly vs baseline unless justified.

### 3) Size Histogram Stability (Distribution Metric)
- For each class (4/6/8/10), compute proportions over N frames.
- Metric: absolute percentage change per class.
- Acceptance: no large unexpected shifts unless the change is explicitly intended.

### 4) Confidence Behavior (Explainability Metric)
- Confidence must be usable for thresholding.
- Acceptance criteria examples:
  - High-glare regions should not produce uniformly high confidence.
  - True beads should tend to score higher than obvious artifacts.
  - Confidence range should not collapse (e.g., everything ~0.95).

---

## Performance Metrics (Offline Pass)

Even though detection is offline, performance still matters.

### 1) Throughput
- Metric: seconds per frame (or frames per second) during offline processing.
- Acceptance: should be recorded each iteration; regressions must be explained.

### 2) Playback Constraint (Non-negotiable)
- Playback reads cache only.
- Playback must remain real-time at 30–60 FPS on target Windows laptops.

---

## UI/Visualization Acceptance Metrics

### 1) Functional Completeness
- All documented FRs in `docs/UI_IMPLEMENTATION_PLAN.md` must be implemented
- All keyboard shortcuts must function as specified
- All interactive controls must update correctly

### 2) Responsiveness
- UI must remain responsive during video playback
- Overlay toggle must update in <50ms
- Statistics must update on each frame change

### 3) Visual Fidelity
- Overlays must match mockup style (filled circles, colored by class)
- Dark theme must be consistent across all panels
- Aspect ratio must be maintained (letterbox if needed)

### 4) State Management
- State transitions must be correct (IDLE → VIDEO_LOADED → PROCESSING → CACHE_READY)
- Invalid controls must be disabled per state
- Error states must be displayed clearly

---

## Recommended Test Sets (Baseline)

### Golden Frames
A small fixed set (5–10 frames) sampled across:
- low fill vs high fill
- low glare vs high glare
- fast vs slow motion
- multiple videos

Used to detect regressions quickly.

### Batch Sample
A larger run (e.g., 30 frames × 3 videos) used to validate stability metrics.

---

## Notes
- Each STEP must define concrete thresholds (numbers) relative to baseline.
- Baseline can be “previous approved step” or a pinned reference run.
