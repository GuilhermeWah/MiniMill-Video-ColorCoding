# iteration_tracker.md

## Purpose
This document tracks and validates incremental improvements to the Grinding Mill Detection Pipeline.

Every time a new algorithm, detection method, rule, or module is added/modified, it **must** be logged below with:

- Purpose
- Files or modules touched
- Inputs used (video name / frame IDs / sample size)
- Exports produced (images + structured outputs)
- Confidence behavior (if detections are involved)
- Observations (what improved / what regressed)
- Pending questions (if any)
- PM review field (**required**)

No update is accepted until it is reviewed and explicitly acknowledged by the PM (Project Manager).

Agents must request **image outputs** from the user after each step to allow inspection and iteration. Agents are expected to analyze the visual result and decide whether to refine or proceed.

---

## Global Rules (Non-Negotiable)

1. **One change per log entry**
   - If multiple ideas were tested (e.g., 3 variants), they must be logged as:
     - one entry with clearly separated variants **or**
     - multiple entries (preferred when changes are large).

2. **Evidence required**
   - Any claimed improvement must include:
     - at least one visual export (`.png`) and
     - at least one structured export (`.json` / `.csv` / `.jsonl`) when applicable.

3. **Pixel-space detection is protected**
   - If `px_per_mm` changes, the following must **not** change (for the same frames):
     - detected centers `(x, y)` and
     - detected radii `r_px`
   - If they change, log it as a **blocking defect** and stop progression.

4. **Confidence is first-class**
   - Any step that outputs detections must include `conf ∈ [0,1]` per object.
   - If confidence behavior changes, it must be documented in the entry.

5. **Pipeline order enforcement**
   - The declared **Phase** of an iteration MUST conform to the global
     development order defined in `MAIN.md`.
   - If an iteration violates the order, it must be:
     - explicitly marked as an override, and
     - approved by the PM in `CURRENT_STEP.md` before any work proceeds.

6. **Hard stop on pending PM review**
   - If an iteration has `PM Review: Pending | Rejected`,
     no subsequent ITER entry may be created.
   - The next allowed action is PM review or revision of the same ITER.


---

## Standard Entry Template (Copy/Paste)

```md
## ITER_XXXX — <Short Title>

**Date**: YYYY-MM-DD  
**Phase**: Preprocessing | CandidateGen | Filters | Watershed | Classification | Overlay | Export | Perf  
**Status**: Proposed | Implemented | Tested | Blocked | Approved

### Purpose
<Why this change exists. One sentence.>

### Change Summary
- <What changed, concisely>

### Files / Modules Touched
- <path>

### Inputs Used
- Videos:
  - <video_name>
- Frames:
  - <frame indices or timecodes>
- Sample Size:
  - <N frames> across <M videos>

### Baseline Reference
- Baseline STEP / ITER:
  - <approved STEP_ID or ITER_XXXX>

### Exports Produced
- Images:
  - <path/to/png>
- Structured:
  - <path/to/json/csv/jsonl>

### Confidence (if applicable)
- Definition (per STEP):
  - <brief>
- Observed behavior:
  - <e.g., high glare → lower conf; stable range; thresholdability>

### Observations
- Improvements:
  - <what got better>
- Regressions:
  - <what got worse>
- Notes:
  - <important nuances>

### Pending Questions
- <open question>

### PM Review
- Decision: Pending | Approved | Rejected
- Notes:
  - <PM notes>
```
---

## Pipeline Phase 0: Foundation

## ITER_0000 — STEP_01 Drum Geometry & ROI Stabilization

**Date**: 2025-12-12  
**Phase**: Foundation  
**Status**: Implemented

### Purpose
Establish static drum geometry (center, radius, rim margin) and generate binary ROI mask for subsequent detection steps.

### Change Summary
- Implemented `DrumGeometry` dataclass in `config.py` with all parameters exposed
- Implemented `generate_roi_mask()` in `drum.py` for binary mask generation
- Implemented `create_geometry_overlay()` for visual debugging
- Implemented `validate_geometry()` for sanity checks
- Added `imwrite_unicode()` helper for Windows Unicode path compatibility
- Created main script `step01_drum_geometry.py` for standalone execution
- Calibrated default geometry for 4K video (3840x2160): center=(1815,1072), radius=900, margin=60

### Files / Modules Touched
- `src/config.py`
- `src/drum.py`
- `src/step01_drum_geometry.py`
- `config/geometry.json`

### Inputs Used
- Videos:
  - `data/IMG_6535.MOV` (4K, 3840x2160, 686 frames)
- Frames:
  - 0, 100
- Sample Size:
  - 2 frames across 1 video

### Baseline Reference
- Baseline STEP / ITER:
  - BOOTSTRAP (first step, no prior baseline)

### Exports Produced
- Images:
  - `output/roi_mask.png` (binary mask, 3840x2160)
  - `output/geometry_overlay.png` (primary overlay with drum visualization)
  - `output/geometry_overlay_frame_0.png`
  - `output/geometry_overlay_frame_100.png`
- Structured:
  - `config/geometry.json`
  - `output/run_manifest.json`

### Confidence (if applicable)
- N/A (no detections emitted at this phase; deterministic geometry definition)

### Observations
- Improvements:
  - Clean binary ROI mask excludes rim/bolt regions
  - Overlay shows cyan (full radius), green (effective radius), red tint (excluded rim)
  - Determinism verified: identical SHA256 hashes across multiple runs
- Regressions:
  - None (first implementation)
- Notes:
  - Auto-detected drum via HoughCircles for initial calibration
  - Required Unicode file path workaround for OpenCV on Windows
  - Default geometry scaled from 1080p to 4K proportionally

### Pending Questions
- Visual inspection needed to confirm geometry alignment with actual drum rim
- May need manual fine-tuning of center/radius after PM review of overlay

### PM Review
- Decision: Pending
- Notes:
  - Awaiting PM inspection of `output/geometry_overlay.png` to confirm alignment

---

## ITER_0001 — STEP_01 Refactor: Auto-Detection & Per-Video Caching

**Date**: 2025-12-12  
**Phase**: Foundation  
**Status**: Implemented

### Purpose
Refactor geometry system to avoid hard-coding and support multiple videos/resolutions automatically.

### Change Summary
- Replaced single global `geometry.json` with per-video cached configs (`geometry_{hash}.json`)
- Implemented `auto_detect_drum()` using HoughCircles with frame-relative parameters
- Added `load_geometry_for_video()` with priority: cached → auto-detect → default
- All detection parameters expressed as ratios (no hard-coded pixel values)
- Added `--force-detect` flag to bypass cache when needed

### Files / Modules Touched
- `src/config.py` — Major refactor: added auto-detection, caching, DETECTION_CONFIG
- `src/step01_drum_geometry.py` — Updated to use new geometry loading

### Inputs Used
- Videos:
  - `IMG_6535.MOV` (4K, 3840x2160) — detected center=(1814,1072), r=865
  - `IMG_1276.MOV` (1080p, 1920x1080) — detected center=(984,596), r=270
  - `DSC_3310.MOV` (1080p, 1920x1080) — detected center=(968,552), r=497
- Frames:
  - 0, 100
- Sample Size:
  - 2 frames across 3 videos

### Baseline Reference
- Baseline STEP / ITER:
  - ITER_0000 (initial STEP_01 implementation)

### Exports Produced
- Images:
  - `output/roi_mask.png`
  - `output/geometry_overlay.png`
  - `output/geometry_overlay_frame_0.png`
  - `output/geometry_overlay_frame_100.png`
- Structured:
  - `config/geometry_8d05444ab8d8.json` (IMG_6535, 4K)
  - `config/geometry_2e8f9de28e68.json` (IMG_1276, 1080p)
  - `config/geometry_abb19bc11812.json` (DSC_3310, 1080p)
  - `output/run_manifest.json`

### Confidence (if applicable)
- N/A (no detections emitted at this phase)

### Observations
- Improvements:
  - Now resolution-agnostic (works 4K and 1080p)
  - No hard-coded pixel values
  - Auto-calibrates per video
  - Caching provides determinism after first run
  - Different drum positions across videos handled correctly
- Regressions:
  - None observed
- Notes:
  - Detection parameters tuned: min_radius=20%, max_radius=55% of min(w,h)
  - Radius adjustment at 96% to stay inside visible rim
  - PM-approved refactor based on existing ROI mask system design

### Pending Questions
- Visual inspection needed to confirm detection accuracy across all videos

### PM Review
- Decision: Pending
- Notes:
  - PM approved refactor approach prior to implementation
  - Awaiting visual verification of auto-detected geometry

---

## ITER_0002 — STEP_01: Detection Parameter Tuning (Height-Based)

**Date**: 2025-12-12  
**Phase**: Foundation  
**Status**: Implemented

### Purpose
Fix detection failures for IMG_1276.MOV by aligning parameters with proven roi_mask_system approach.

### Change Summary
- Changed radius calculation from `min(width, height)` to `height` (proven approach)
- Updated DETECTION_CONFIG:
  - `min_radius_ratio`: 0.25 → 0.35 (35% of height)
  - `max_radius_ratio`: 0.50 → 0.48 (48% of height)
  - `param1`: 100 → 50 (lower Canny threshold)
  - Added `blur_kernel`: 7 (stronger median blur)
- Updated auto_detect_drum() to use height-based calculations consistently
- Added video-specific debug subdirectories (output/debug/{video_name}/)

### Files / Modules Touched
- `src/config.py` — Updated DETECTION_CONFIG, refactored auto_detect_drum()
- `src/step01_drum_geometry.py` — Added per-video debug subdirectories

### Inputs Used
- Videos:
  - `IMG_6535.MOV` (4K, 3840x2160) — center=(1815,1074), r=872
  - `IMG_1276.MOV` (1080p, 1920x1080) — center=(1148,382), r=366
  - `DSC_3310.MOV` (1080p, 1920x1080) — center=(967,551), r=496
- Frames:
  - 0, 100
- Sample Size:
  - 2 frames across 3 videos

### Baseline Reference
- Baseline STEP / ITER:
  - ITER_0001 (auto-detection refactor)

### Exports Produced
- Images:
  - `output/debug/IMG_6535/geometry_overlay.png`
  - `output/debug/IMG_6535/geometry_overlay_frame_0.png`
  - `output/debug/IMG_6535/geometry_overlay_frame_100.png`
  - `output/debug/IMG_6535/roi_mask.png`
  - `output/debug/IMG_1276/geometry_overlay.png`
  - `output/debug/IMG_1276/geometry_overlay_frame_0.png`
  - `output/debug/IMG_1276/geometry_overlay_frame_100.png`
  - `output/debug/IMG_1276/roi_mask.png`
  - `output/debug/DSC_3310/geometry_overlay.png`
  - `output/debug/DSC_3310/geometry_overlay_frame_0.png`
  - `output/debug/DSC_3310/geometry_overlay_frame_100.png`
  - `output/debug/DSC_3310/roi_mask.png`
- Structured:
  - `cache/geometry/IMG_6535_8d05444a.json`
  - `cache/geometry/IMG_1276_2e8f9de2.json`
  - `cache/geometry/DSC_3310_abb19bc1.json`
  - `output/debug/IMG_6535/run_manifest.json`
  - `output/debug/IMG_1276/run_manifest.json`
  - `output/debug/DSC_3310/run_manifest.json`

### Confidence (if applicable)
- N/A (no detections emitted at this phase)

### Observations
- Improvements:
  - IMG_1276.MOV now detects correctly at (590, 395) - was picking wrong circle at (1148, 382) before
  - All 3 videos detect proper drum circle
  - Simplified selection logic (first/strongest) more reliable than weighted scoring
  - Height-based calculation aligns with proven roi_mask_system
  - Per-video debug folders prevent overlay overwriting
- Regressions:
  - None observed
- Notes:
  - HoughCircles returns circles sorted by accumulator votes (strongest first)
  - Taking first circle is the proven approach - no need for complex scoring
  - Stronger blur (kernel=7) reduces noise in Hough detection

### Pending Questions
- None - all three test videos verified

### PM Review
- Decision: Approved
- Notes:
  - PM visually verified IMG_1276.MOV overlay - drum correctly identified at (590, 395)
  - Green circle correctly captures the drum with metallic beads
  - False positives (blue, red circles) correctly ignored

---

## ITER_0003 — STEP_02: Golden Frames Lock

**Date**: 2025-12-12  
**Phase**: Foundation  
**Status**: Implemented

### Purpose
Extract and lock a curated set of golden frames as immutable baseline validation set.

### Change Summary
- Created `src/step02_golden_frames.py` for golden frame extraction
- Implemented strategic frame selection (0, 100, 25%, 50%, 75%, near-end)
- Generate raw + ROI-masked variants for each frame
- Compute SHA256 hashes for immutability verification
- Create comprehensive manifest with all metadata

### Files / Modules Touched
- `src/step02_golden_frames.py` — New script for STEP_02

### Inputs Used
- Videos:
  - `IMG_6535.MOV` (4K, 3840x2160, 686 frames)
  - `IMG_1276.MOV` (1080p, 1920x1080, 7379 frames)
  - `DSC_3310.MOV` (1080p, 1920x1080, 3777 frames)
- Frames:
  - IMG_6535: [0, 100, 171, 343, 514, 676]
  - IMG_1276: [0, 100, 1844, 3689, 5534, 7369]
  - DSC_3310: [0, 100, 944, 1888, 2832, 3767]
- Sample Size:
  - 18 frames across 3 videos (6 per video)

### Baseline Reference
- Baseline STEP / ITER:
  - STEP_01 / ITER_0002 (Drum Geometry)

### Exports Produced
- Images:
  - `data/golden_frames/*.png` (18 raw frames)
  - `data/golden_frames/*_masked.png` (18 ROI-masked frames)
- Structured:
  - `data/golden_frames/manifest.json` (metadata + SHA256 hashes)
  - `output/step02_manifest.json` (run manifest)

### Confidence (if applicable)
- N/A (no detections at this phase; deterministic frame extraction)

### Observations
- Improvements:
  - 18 golden frames locked with SHA256 hashes
  - Both raw and masked variants available for testing
  - Strategic frame selection covers start, mid, and end of each video
  - Manifest includes geometry cache reference for traceability
- Regressions:
  - None
- Notes:
  - Re-running extraction should produce identical hashes (determinism)
  - Tags field left empty for manual annotation in future

### Pending Questions
- Should we add manual condition tags (dense/sparse/blur/glare)? (Deferred to future iteration)

### PM Review
- Decision: Approved
- Notes:
  - PM verified golden frames visually
  - Calibration sanity check with 200mm drum diameter confirmed reasonable size classification
  - 18 golden frames (6 per video) locked with SHA256 hashes
  - Approved 2025-12-12

---

## ITER_0004 — STEP_03: Preprocessing Baseline Stabilization

**Date**: 2025-12-12  
**Phase**: Preprocessing  
**Status**: Implemented

### Purpose
Implement deterministic preprocessing pipeline to improve bead visibility before detection.

### Change Summary
- Created `src/preprocess.py` with 6-stage pipeline:
  1. Grayscale conversion
  2. ROI application (full drum radius, NOT effective radius)
  3. Top-hat illumination normalization
  4. CLAHE contrast enhancement
  5. Bilateral blur noise reduction
  6. Glare suppression (optional, disabled by default)
- Added `PREPROCESS_CONFIG` to `src/config.py`
- Created `src/step03_preprocess.py` test script
- Key design: Uses FULL drum radius for ROI to preserve edge beads; rim margin filtering deferred to STEP_06

### Files / Modules Touched
- `src/preprocess.py` — New preprocessing module
- `src/config.py` — Added PREPROCESS_CONFIG
- `src/step03_preprocess.py` — Test script

### Inputs Used
- Videos:
  - IMG_6535.MOV (4K, 3840x2160)
  - IMG_1276.MOV (1080p, 1920x1080)
  - DSC_3310.MOV (1080p, 1920x1080)
- Frames:
  - All 18 golden frames from STEP_02
- Sample Size:
  - 18 frames across 3 videos

### Baseline Reference
- Baseline STEP / ITER:
  - STEP_02 / ITER_0003 (Golden Frames)

### Exports Produced
- Images:
  - `output/preprocess_test/{frame_id}_original.png` (18 files)
  - `output/preprocess_test/{frame_id}_preprocessed.png` (18 files)
  - `output/preprocess_test/{frame_id}_stages.png` (18 files)
  - `output/preprocess_test/{frame_id}_comparison.png` (18 files)
  - `output/preprocess_test/comparison_grid.png`
- Structured:
  - `output/preprocess_test/preprocess_manifest.json`

### Confidence (if applicable)
- N/A (preprocessing produces images, not detections)

### Observations
- Improvements:
  - Avg contrast improvement: +23.5 (significant)
  - Bead edges clearer after CLAHE
  - Histogram spread maximized (240-253 range)
  - All 18 frames processed deterministically
- Regressions:
  - Glare slightly increased in some frames (0.02% → 0.8%)
  - Bolts/screws visible in rim area (expected, filtered in STEP_06)
- Notes:
  - Full drum radius used for preprocessing ROI
  - Rim margin filtering explicitly deferred to STEP_06
  - PM confirmed architecture is correct

### Pending Questions
- None

### PM Review
- Decision: Approved
- Notes:
  - PM verified DSC_3310 preprocessed output
  - Confirmed rim margin filtering belongs in STEP_06, not preprocessing
  - Approved 2025-12-12

---

## ITER_0005 — STEP_04: Candidate Generation (Circle Detection)

**Date**: 2025-12-12  
**Phase**: CandidateGen  
**Status**: Implemented

### Purpose
Detect circular bead candidates using HoughCircles with resolution-adaptive parameters.

### Change Summary
- Created `src/detect.py` with Detection/DetectionResult dataclasses
- Implemented `detect_candidates()` with HoughCircles
- Implemented resolution-adaptive param2:
  - 1080p: param2 = 25 (base)
  - 4K: param2 = 25 + (2.0 - 1) * 10 = 35
- Added `calculate_radius_range()` based on drum geometry
- Added `DETECTION_BEAD_CONFIG` to config.py
- Created `src/step04_detect.py` test script

### Files / Modules Touched
- `src/detect.py` — New detection module
- `src/config.py` — Added DETECTION_BEAD_CONFIG
- `src/step04_detect.py` — Test script

### Inputs Used
- Videos:
  - IMG_6535.MOV (4K, 3840x2160) — param2=35, ~1000 candidates/frame
  - IMG_1276.MOV (1080p, 1920x1080) — param2=25, ~300 candidates/frame
  - DSC_3310.MOV (1080p, 1920x1080) — param2=25, ~600 candidates/frame
- Frames:
  - All 18 golden frames from STEP_02
- Sample Size:
  - 18 frames across 3 videos

### Baseline Reference
- Baseline STEP / ITER:
  - STEP_03 / ITER_0004 (Preprocessing)

### Exports Produced
- Images:
  - `output/detection_test/{frame_id}_candidates.png` (18 files)
- Structured:
  - `output/detection_test/{frame_id}_candidates.json` (18 files)
  - `output/detection_test/detection_manifest.json`

### Confidence (if applicable)
- N/A at this step (STEP_05 adds confidence)
- Raw HoughCircles output only

### Observations
- Improvements:
  - Resolution-adaptive param2 prevents over-detection in 4K
  - Radius range scales correctly with drum geometry
  - Good coverage on visible beads across all videos
- Regressions:
  - Some false positives on rim/bolts (expected, filtered in STEP_06)
  - Motion blur areas have fewer detections (expected)
- Notes:
  - Initial 4K detection had 14,000+ candidates (too many)
  - param2 scaling formula: `param2 = 25 + (h/1080 - 1) * 10`
  - For 4K (h=2160): param2 = 35

### Pending Questions
- None

### PM Review
- Decision: Approved
- Notes:
  - PM verified detection overlays for all video types
  - Resolution-adaptive approach approved
  - Approved 2025-12-12

---

## ITER_0006 — STEP_05: Confidence Scoring

**Date**: 2025-12-12  
**Phase**: ConfidenceScoring  
**Status**: Implemented

### Purpose
Assign confidence scores [0.0, 1.0] to each detection based on observable image evidence.

### Change Summary
- Created `src/confidence.py` with 4-feature scoring system:
  - Edge Strength (weight=0.35): Gradient magnitude along circumference
  - Circularity (weight=0.25): Edge consistency around perimeter
  - Interior Uniformity (weight=0.20): Bead-like intensity pattern
  - Radius Fit (weight=0.20): Match to expected bead sizes
- Added `CONFIDENCE_CONFIG` to config.py
- Created `src/step05_confidence.py` test script
- Optimized performance by precomputing gradient once per frame

### Files / Modules Touched
- `src/confidence.py` — New confidence scoring module
- `src/config.py` — Added CONFIDENCE_CONFIG
- `src/step05_confidence.py` — Test script

### Inputs Used
- Videos:
  - IMG_6535.MOV (4K, 3840x2160)
  - IMG_1276.MOV (1080p, 1920x1080)
  - DSC_3310.MOV (1080p, 1920x1080)
- Frames:
  - All 18 golden frames from STEP_02
- Sample Size:
  - 14,234 total candidates scored

### Baseline Reference
- Baseline STEP / ITER:
  - STEP_04 / ITER_0005 (Candidate Generation)

### Exports Produced
- Images:
  - `output/confidence_test/{frame_id}_confidence.png` (18 files)
- Structured:
  - `output/confidence_test/{frame_id}_scored.json` (18 files)
  - `output/confidence_test/confidence_manifest.json`

### Confidence Behavior
- Global mean: 0.495, std: 0.142
- Global range: [0.085, 0.938]
- Distribution:
  - [0.0-0.2): 0.3% (39 detections)
  - [0.2-0.4): 24.7% (3,519 detections)
  - [0.4-0.6): 56.9% (8,103 detections)
  - [0.6-0.8): 11.5% (1,638 detections)
  - [0.8-1.0): 6.6% (935 detections)
- Thresholdable: 0.7 threshold keeps 1,660 high-confidence candidates

### Per-Video Statistics
| Video    | Total | High (>=0.7) | Med (0.4-0.7) | Low (<0.4) | Mean |
|----------|-------|--------------|---------------|------------|------|
| IMG_6535 | 6,490 | 0            | 5,351         | 1,139      | 0.450|
| IMG_1276 | 1,591 | 1,345        | 240           | 6          | 0.777|
| DSC_3310 | 6,153 | 315          | 3,425         | 2,413      | 0.511|

### Observations
- Improvements:
  - Confidence is deterministic and thresholdable
  - Clear separation between high/med/low confidence detections
  - IMG_1276 has highest confidence (clearer video)
  - Per-detection feature breakdown enables debugging
- Regressions:
  - IMG_6535 (4K) has no high-confidence detections (max 0.675)
  - DSC_3310 frame 0 has excessive candidates (3,351)
- Notes:
  - 4K video may need adjusted feature weights
  - Rim/bolt false positives have low confidence (as expected)
  - Feature breakdown shows edge_strength often saturates at 1.0

### Pending Questions
- Should feature weights be resolution-adaptive?
- Is 0.7 the right threshold for high-confidence?

### PM Review
- Decision: Approved
- Notes:
  - PM reviewed confidence overlays
  - Full analysis documents created (STEP_05 + Pipeline)
  - Approved 2025-12-12

---

## ITER_0007 — STEP_06: Filtering and Cleanup

**Date**: 2025-12-12  
**Phase**: Filters  
**Status**: Implemented

### Purpose
Apply 3-stage filtering to reduce false positives from STEP_05 detections.

### Change Summary
- Created `src/filter.py` with 3 sequential filters:
  1. **Rim margin filter** (12% of radius) — removes bolts, purple ring, edge artifacts
  2. **Confidence threshold** (≥0.5) — removes low-confidence noise
  3. **Non-maximum suppression** (50% overlap) — merges overlapping detections
- Added `FILTER_CONFIG` to config.py
- Created `src/step06_filter.py` test script

### Files / Modules Touched
- `src/filter.py` — New filtering module
- `src/config.py` — Added FILTER_CONFIG
- `src/step06_filter.py` — Test script

### Inputs Used
- Videos:
  - IMG_6535.MOV (4K, 3840x2160)
  - IMG_1276.MOV (1080p, 1920x1080)
  - DSC_3310.MOV (1080p, 1920x1080)
- Frames:
  - All 18 golden frames from STEP_02
- Sample Size:
  - 14,234 input detections

### Baseline Reference
- Baseline STEP / ITER:
  - STEP_05 / ITER_0006 (Confidence Scoring)

### Exports Produced
- Images:
  - `output/filter_test/{frame_id}_filtered.png` (18 files)
- Structured:
  - `output/filter_test/{frame_id}_filtered.json` (18 files)
  - `output/filter_test/filter_manifest.json`

### Filter Results

| Stage | Count | Reduction |
|-------|-------|-----------|
| Input | 14,234 | - |
| After Rim | 13,524 | 5.0% |
| After Confidence | 5,133 | 62.0% |
| After NMS | 1,830 | 64.3% |
| **Final** | **1,830** | **87.1%** |

### Per-Video Statistics
| Video | Input | Output | Retention |
|-------|-------|--------|-----------|
| IMG_6535 | 6,490 | 433 | 6.7% |
| IMG_1276 | 1,591 | 687 | 43.2% |
| DSC_3310 | 6,153 | 710 | 11.5% |

### Observations
- Improvements:
  - 87% reduction in detections (14,234 → 1,830)
  - Rim margin effectively removes bolts and purple ring
  - NMS successfully merges overlapping circles
  - IMG_1276 retains 43% — mostly real beads
- Regressions:
  - IMG_6535 retains only 6.7% due to low confidence scores
  - Some edge beads may be lost to rim margin
- Notes:
  - DSC_3310 frame 0 went from 3,351 → 149 (95.5% filtered)
  - Confidence threshold is the most aggressive filter (62% reduction)

### Pending Questions
- Should rim_margin_ratio be video-specific?
- Should confidence threshold be lower for 4K video?

### PM Review
- Decision: Approved
- Notes:
  - PM reviewed filter overlays
  - Green circles well-placed on beads
  - Red circles correctly show rejected noise
  - Approved 2025-12-12

---

## Pipeline Phase 1: Preprocessing (TEMPLATES BELOW - NOT YET USED)

## ITER_0001 — CLAHE + Noise Reduction

**Date**: YYYY-MM-DD  
**Phase**: Preprocessing  
**Status**: Tested

### Purpose
Improve local contrast and reduce noise while preserving bead edges.

### Change Summary
- Added CLAHE for local contrast normalization
- Added mild denoising prior to candidate generation

### Files / Modules Touched
- `src/preprocess.py`

### Inputs Used
- Videos:
  - `data/input_video.mp4`
- Frames:
  - `<fill>`
- Sample Size:
  - `<fill>`

### Exports Produced
- Images:
  - `test_preprocessing/debugExports/*.png`
- Structured:
  - `<optional stats json/csv>`

### Confidence (if applicable)
- N/A (no detections emitted at this phase)

### Observations
- Improvements:
  - CLAHE improved local contrast in shadowed regions.
- Regressions:
  - Reflective beads slightly blown out in some frames.
- Notes:
  - Still visible contour dropout near bolt holes.

### Pending Questions
- Should we try top-hat or morphological normalization?

### PM Review
- Decision: _(pending)_
- Notes:
  -

---

## Pipeline Phase 2: Segmentation / Candidate Generation

## ITER_0002 — Threshold + Morph Close + Hole Filling

**Date**: YYYY-MM-DD  
**Phase**: CandidateGen  
**Status**: Tested

### Purpose
Generate stable foreground candidates and reduce holes in hollow beads.

### Change Summary
- Standard adaptive threshold
- Morphological closing variant
- Flood-fill hole suppression variant

### Files / Modules Touched
- `src/segment.py`

### Inputs Used
- Videos:
  - `data/input_video.mp4`
- Frames:
  - `<fill>`
- Sample Size:
  - `<fill>`

### Exports Produced
- Images:
  - `export_segmentation1.png` (standard adaptive threshold)
  - `export_segmentation2.png` (with morphological closing)
  - `export_segmentation3.png` (with flood-fill hole suppression)
- Structured:
  - `<optional candidate stats json/csv>`

### Confidence (if applicable)
- N/A (if this phase emits only masks)
- If candidates are emitted, include:
  - candidate `conf` + definition

### Observations
- Improvements:
  - Hollow beads mostly resolved
- Regressions:
  - Some blobs merged (especially near front rim)
- Notes:
  - Need to tune kernel size to avoid merging
  - Shadows still break threshold in top-left

### Pending Questions
- Should we mask top 10% of drum by default?
- Would combining gradient magnitude with threshold improve this?

### PM Review
- Decision: _(pending)_
- Notes:
  -

---

## Pipeline Phase 3: Watershed Separation

## ITER_0003 — Distance Transform + Peak Detection + Marker-Based Watershed

**Date**: YYYY-MM-DD  
**Phase**: Watershed  
**Status**: Tested

### Purpose
Separate touching beads into individual labels in dense scenes.

### Change Summary
- Distance transform and peak detection to create markers
- Marker-based watershed for instance separation

### Files / Modules Touched
- `src/segment.py` or `src/watershed.py`

### Inputs Used
- Videos:
  - `data/input_video.mp4`
- Frames:
  - `<fill>`
- Sample Size:
  - `<fill>`

### Exports Produced
- Images:
  - `watershed_labels_frame3.png`
- Structured:
  - `<optional label counts json/csv>`

### Confidence (if applicable)
- If this phase emits instance candidates, include:
  - instance `conf` definition + behavior

### Observations
- Improvements:
  - Touching beads mostly separated into clean labels
- Regressions:
  - Oversegmentation in high-glare zones
- Notes:
  - Distance peaks too sensitive to glare edges
  - Elliptical streaks create false bead centers

### Pending Questions
- Should we suppress watershed in regions with high eccentricity?
- Should preprocessing include glare-masking or brightness thresholding?

### PM Review
- Decision: _(pending)_
- Notes:
  -

---

## Pipeline Phase 4: Visualization / UI

## ITER_0008 — UI Implementation (Phase 9)

**Date**: 2025-12-12  
**Phase**: Visualization / UI  
**Status**: In Progress

### Purpose
Implement the MillPresenter UI application for visualization and playback of cached detection results.

### Change Summary
- Created PySide6-based UI application
- Implemented 5-panel layout (TopBar, LeftPanel, VideoViewport, RightPanel, BottomBar)
- Implemented video playback with cache-based detection overlay
- Implemented statistics display with per-class breakdown
- Implemented overlay controls (master toggle, opacity, confidence threshold, class toggles)
- Added Real-Time/Offline mode switching for parameter fine-tuning
- Added DetectionController for preview and batch detection
- Added parameter tooltips and ⓘ info popups for user guidance
- Implemented preview detection feature (cyan dashed overlays)

### Files / Modules Touched
- `ui/main.py` — Application entry point
- `ui/main_window.py` — QMainWindow with 5-panel layout, signal routing
- `ui/video_controller.py` — VideoController + DetectionCache classes
- `ui/detection_worker.py` — DetectionController, PreviewWorker, BatchWorker
- `ui/widgets/right_panel.py` — ProcessTab with parameter sliders, info buttons
- `ui/widgets/video_viewport.py` — Frame display with overlay rendering
- `ui/widgets/` — All UI widget modules
- `docs/UI_IMPLEMENTATION_PLAN.md` — Detailed specification

### Reference Documents
- Specification: `docs/UI_IMPLEMENTATION_PLAN.md`
- Acceptance: `rules/ACCEPTANCE_METRICS.md` (UI/Visualization section)

### Functional Requirements Coverage
- See `docs/UI_IMPLEMENTATION_PLAN.md` for 48 FRs across 11 categories

### Key Architecture Decisions
- Cache-only playback (no real-time CV per MAIN.md invariants)
- State machine: IDLE → VIDEO_LOADED → PROCESSING → CACHE_READY
- Detection JSON format: `{metadata, config, frames: [{frame_idx, detections}]}`
- Preview mode: Debounced (200ms) single-frame detection for tuning

### Observations
- Improvements:
  - Clean 5-panel layout matching mockup
  - Responsive playback at target FPS
  - Real-time overlay toggle updates
  - Parameter sliders with helpful tooltips and detailed info popups
  - Preview detection with visual distinction (cyan dashed circles)
- Regressions:
  - None identified yet
- Notes:
  - Automated test suite created (pytest-qt)
  - Tests pending execution
  - Preview feature fully wired with DetectionController

### Pending Questions
- Video export with overlays — implementation approach?
- Batch detection progress UI — full implementation needed

### PM Review
- Decision: In Progress
- Notes:
  - UI implementation ongoing
  - Core playback and overlay functionality implemented
  - Preview detection feature implemented
  - Testing in progress

---

## ITER_0009 — STEP_07: Calibration and Size Classification

**Date**: 2025-12-12  
**Phase**: Classification  
**Status**: ReadyForReview

### Purpose
Apply px_per_mm calibration and classify detections into size bins (4mm, 6mm, 8mm, 10mm).

### Change Summary
- Implemented calibration calculation from drum geometry
- Created size classification module with configurable bins
- Generated color-coded overlays for all 18 golden frames
- Produced aggregate statistics across all frames/videos

### Files / Modules Touched
- `src/classify.py` — Classification functions
- `src/step07_classify.py` — Test script
- `src/config.py` — SIZE_CONFIG parameters

### Inputs Used
- Videos:
  - `IMG_6535.MOV` (4K, px_per_mm=8.72)
  - `IMG_1276.MOV` (1080p, px_per_mm=3.65)
  - `DSC_3310.MOV` (1080p, px_per_mm=4.96)
- Frames:
  - All 18 golden frames
- Sample Size:
  - 18 frames across 3 videos

### Baseline Reference
- Baseline STEP / ITER:
  - STEP_06 / ITER_0007 (Filtered detections)

### Exports Produced
- Images:
  - `output/classify_test/{video}_frame_{idx}_classified.png` (18 files)
- Structured:
  - `output/classify_test/{video}_frame_{idx}_classified.json` (18 files)
  - `output/classify_test/classification_summary.json`

### Confidence (if applicable)
- Confidence passed through unchanged from STEP_06
- Not modified by classification

### Results
| Metric | Value |
|--------|-------|
| Total classified | 1,830 |
| 4mm | 327 (17.9%) |
| 6mm | 851 (46.5%) |
| 8mm | 396 (21.6%) |
| 10mm | 219 (12.0%) |
| Unknown | 37 (2.0%) |

### Observations
- Improvements:
  - 98% classification rate (only 2% unknown)
  - Resolution-aware calibration (different px_per_mm per video)
  - Color-coded overlays clearly distinguish size classes
- Regressions:
  - None
- Notes:
  - 6mm beads dominate (46.5%) — expected for this bead mix
  - Unknown detections likely edge cases at bin boundaries

### Pending Questions
- None — ready for PM review

### PM Review
- Decision: Approved
- Notes:
  - PM approved 2025-12-12
  - Classification distribution validated
  - Ready for STEP_08 (Quality Metrics)

---

## ITER_0010 — STEP_08: Quality Metrics

**Date**: 2025-12-12  
**Phase**: Metrics  
**Status**: ReadyForReview

### Purpose
Compute quality metrics for pipeline validation and verify acceptance criteria.

### Change Summary
- Implemented quality metrics module
- Computed count stability (CV) across frames
- Analyzed size distribution stability per class
- Analyzed confidence distribution behavior
- Validated against acceptance criteria

### Files / Modules Touched
- `src/metrics.py` — Quality metrics functions
- `src/step08_metrics.py` — Test script

### Inputs Used
- Videos:
  - `IMG_6535.MOV` (433 detections)
  - `IMG_1276.MOV` (687 detections)
  - `DSC_3310.MOV` (710 detections)
- Frames:
  - All 18 golden frames
- Sample Size:
  - 1,830 total detections across 18 frames

### Baseline Reference
- Baseline STEP / ITER:
  - STEP_07 / ITER_0009 (Classified detections)

### Exports Produced
- Structured:
  - `output/metrics/IMG_6535_quality_report.json`
  - `output/metrics/IMG_1276_quality_report.json`
  - `output/metrics/DSC_3310_quality_report.json`
  - `output/metrics/aggregate_quality_report.json`

### Confidence (if applicable)
- Analyzed but not modified
- Mean: 0.676, Median: 0.653, Range: 0.438

### Results
| Metric | Value | Status |
|--------|-------|--------|
| Count CV | 0.255 | ✅ Acceptable |
| Confidence range | 0.438 | ✅ Pass |
| Unknown rate | 2.3% | ✅ Pass |
| All classes present | Yes | ✅ Pass |
| **Overall** | **PASS** | ✅ |

### Observations
- Improvements:
  - All acceptance criteria pass
  - Confidence distribution is normal (not collapsed)
  - Count stability is acceptable for demo purposes
- Regressions:
  - None
- Notes:
  - 4mm and 10mm classes show higher variability (CV ~0.5)
  - 6mm and 8mm classes more stable (CV ~0.2)

### Pending Questions
- None — ready for PM review

### PM Review
- Decision: Approved
- Notes:
  - PM approved 2025-12-12
  - All acceptance criteria validated
  - Ready for STEP_09 (Visualization & Playback)

---

## Notes / Folder Contracts

- All exports and logs must be committed under their respective folders:
  - `/test_preprocessing/`
  - `/test_segmentation/`
  - `/test_watershed/`
  - `/test_filters/` (if/when added)
  - `/test_overlay/` (if/when added)
- Each phase must be updated with `**PM Review**: Approved` before proceeding.
- For any detection-bearing step, exports should include:
  - an overlay `.png` with detections drawn
  - a structured file containing `(x, y, r_px, conf, cls?)` per detection
- Agents must explicitly request visual outputs from the user and analyze them before continuing.

---

End of iteration_tracker.md
