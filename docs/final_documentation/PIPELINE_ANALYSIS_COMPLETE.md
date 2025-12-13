# MillPresenter Pipeline - Complete Analysis Document

**Date**: 2025-12-12  
**Last Updated**: 2025-12-12  
**Author**: Claude Opus 4.5 (Developer Agent)  
**Pipeline Version**: 1.2 (STEP_01 through STEP_06 + UI)  
**Status**: STEP_06 Complete, PM Approved | UI Development In Progress

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Project Overview](#2-project-overview)
3. [Pipeline Architecture](#3-pipeline-architecture)
4. [STEP_01: Drum Geometry & ROI](#4-step_01-drum-geometry--roi)
5. [STEP_02: Golden Frames Lock](#5-step_02-golden-frames-lock)
6. [STEP_03: Preprocessing Baseline](#6-step_03-preprocessing-baseline)
7. [STEP_04: Candidate Generation](#7-step_04-candidate-generation)
8. [STEP_05: Confidence Scoring](#8-step_05-confidence-scoring)
9. [STEP_06: Filtering & Cleanup](#9-step_06-filtering--cleanup)
10. [UI/Visualization (Phase 9)](#10-uivisualization-phase-9)
11. [Cross-Step Analysis](#11-cross-step-analysis)
12. [Video-Specific Insights](#12-video-specific-insights)
13. [Configuration Reference](#13-configuration-reference)
14. [File Structure](#14-file-structure)
15. [Known Issues & Limitations](#15-known-issues--limitations)
16. [Recommendations](#16-recommendations)
17. [Appendix](#17-appendix)

---

## 1. Executive Summary

### What We Built

A classical computer vision pipeline for detecting metallic beads in rotating grinding mill videos. The pipeline:

- Operates **offline** (batch processing, not real-time)
- Uses **only OpenCV + NumPy** (no deep learning)
- Produces **deterministic, reproducible** results
- Works in **pixel-space** (calibration-independent detection)
- Supports **multiple resolutions** (1080p and 4K tested)

### Current Capabilities

| Capability | Status |
|------------|--------|
| Drum geometry detection | ✅ Complete |
| ROI mask generation | ✅ Complete |
| Per-video geometry caching | ✅ Complete |
| Golden frame baseline | ✅ Locked (18 frames) |
| 6-stage preprocessing | ✅ Complete |
| Circle detection (HoughCircles) | ✅ Complete |
| Resolution-adaptive parameters | ✅ Complete |
| Confidence scoring (4 features) | ✅ Complete |
| 3-stage filtering (rim, conf, NMS) | ✅ Complete |
| Size classification | ⏳ STEP_07 (pending) |
| UI Application (PySide6) | 🟡 In Progress |
| Video playback (cache-based) | 🟡 In Progress |
| Overlay visualization | 🟡 In Progress |
| Statistics display | 🟡 In Progress |
| Export features | ⏳ Future |

### Key Metrics

| Metric | Value |
|--------|-------|
| Videos tested | 3 |
| Golden frames | 18 |
| Raw detections | 14,234 |
| After filtering | 1,830 |
| Filter reduction | 87.1% |
| Mean confidence | 0.495 |
| Avg preprocessing improvement | +23.5 contrast |

---

## 2. Project Overview

### Problem Statement

Analyze videos of a transparent rotating grinding drum to detect and classify metallic beads. The system must produce trustworthy, explainable overlays for non-technical users during demonstrations.

### Key Challenges

| Challenge | Description |
|-----------|-------------|
| **Specular reflections** | Shiny metallic beads create glare and false edges |
| **Motion blur** | Rotating drum causes elongated streaks |
| **Occlusions** | Beads overlap and occlude each other |
| **Structural artifacts** | Rim, bolts, purple inner ring create false positives |
| **Multiple bead sizes** | 4 nominal sizes: 4mm, 6mm, 8mm, 10mm |
| **Resolution variance** | Must work on both 1080p and 4K video |

### Target Bead Sizes

| Nominal | True Diameter | Notes |
|---------|---------------|-------|
| ~4mm | 3.94 mm | Smallest |
| ~6mm | 5.79 mm | |
| ~8mm | 7.63 mm | |
| ~10mm | 9.90 mm | Largest |

### Design Constraints

1. **Classical CV only** - No deep learning / neural networks
2. **CPU-only execution** - No GPU requirements
3. **Deterministic results** - Same input → same output
4. **Pixel-space detection** - Calibration applied post-detection only
5. **Offline processing** - Batch process, then playback cached results

---

## 3. Pipeline Architecture

### Processing Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                         INPUT                                    │
│  Raw Video Frame (BGR, 1080p or 4K)                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP_01: Drum Geometry Detection                               │
│  ├── Auto-detect drum center and radius (HoughCircles)          │
│  ├── Cache geometry per video (MD5 hash)                        │
│  └── Generate ROI mask (full drum radius)                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP_03: Preprocessing (6 stages)                              │
│  ├── 1. Grayscale conversion                                    │
│  ├── 2. ROI masking (drum area only)                            │
│  ├── 3. Morphological top-hat (lighting normalization)          │
│  ├── 4. CLAHE (local contrast enhancement)                      │
│  ├── 5. Bilateral filter (edge-preserving blur)                 │
│  └── 6. Glare suppression (brightness thresholding)             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP_04: Candidate Generation (HoughCircles)                   │
│  ├── Resolution-adaptive param2                                 │
│  ├── Radius range from drum geometry + bead sizes               │
│  └── Output: List of (x, y, r_px) candidates                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP_05: Confidence Scoring                                    │
│  ├── Edge strength (35%)                                        │
│  ├── Circularity (25%)                                          │
│  ├── Interior uniformity (20%)                                  │
│  ├── Radius fit (20%)                                           │
│  └── Output: List of (x, y, r_px, conf) scored detections       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP_06: Filtering & Cleanup (✅ COMPLETE)                       │
│  ├── Rim margin filtering (12%)                                 │
│  ├── Confidence thresholding (≥0.5)                              │
│  └── Non-maximum suppression (50% overlap)                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP_07: Size Classification (PENDING)                         │
│  ├── Apply px_per_mm calibration                                │
│  ├── Convert r_px → diameter_mm                                 │
│  └── Classify into 4mm/6mm/8mm/10mm bins                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         OUTPUT                                   │
│  Cached detections: (x, y, r_px, conf, cls)                     │
│  Overlay visualizations                                          │
│  Statistics and manifests                                        │
└─────────────────────────────────────────────────────────────────┘
```

### Module Dependencies

```
src/
├── config.py          ← Central configuration (all parameters)
│     ↑
├── drum.py            ← Drum geometry detection + ROI masks
│     ↑
├── preprocess.py      ← 6-stage preprocessing pipeline
│     ↑
├── detect.py          ← HoughCircles candidate generation
│     ↑
├── confidence.py      ← Confidence scoring (4 features)
│     ↑
├── filter.py          ← 3-stage filtering (rim, conf, NMS)
│     ↑
└── [future: classify.py]

ui/
├── main.py            ← Application entry point
├── main_window.py     ← QMainWindow with 5-panel layout
├── video_controller.py ← Video playback + detection cache
└── widgets/           ← UI components (panels, controls)
```

---

## 4. STEP_01: Drum Geometry & ROI

### Purpose

Detect the circular drum boundary and create a Region of Interest (ROI) mask to exclude areas outside the drum.

### Algorithm

1. **Load frame** from video
2. **Convert to grayscale** 
3. **Apply Gaussian blur** (reduce noise)
4. **Run HoughCircles** with parameters tuned for drum size:
   - `minRadius`: 35% of frame height
   - `maxRadius`: 48% of frame height
   - `param2`: 30 (accumulator threshold)
5. **Select strongest circle** (first result, highest accumulator votes)
6. **Cache geometry** using MD5 hash of video filename
7. **Generate ROI mask** (full drum radius, no margin applied)

### Key Design Decision

> **ROI uses FULL drum radius** - Rim margin filtering is deferred to STEP_06.
> This preserves edge beads during preprocessing and detection.

### Outputs

| Output | Description |
|--------|-------------|
| `config/geometry.json` | Default/fallback geometry |
| `config/{video_hash}.json` | Per-video cached geometry |
| ROI mask (in memory) | Binary mask for preprocessing |

### Results by Video

| Video | Resolution | Center (x, y) | Radius (px) | px_per_mm |
|-------|------------|---------------|-------------|-----------|
| IMG_6535.MOV | 3840×2160 | (1920, 1108) | 872 | 8.72 |
| IMG_1276.MOV | 1920×1080 | (960, 451) | 365 | 3.65 |
| DSC_3310.MOV | 1920×1080 | (961, 562) | 496 | 4.96 |

### Calibration Formula

```python
drum_diameter_mm = 200  # Physical drum size (assumption)
px_per_mm = drum_radius_px / (drum_diameter_mm / 2)
```

---

## 5. STEP_02: Golden Frames Lock

### Purpose

Create an immutable baseline set of test frames with SHA256 hashes for validation throughout development.

### Frame Selection Strategy

For each video, select 6 strategic frames:
- Frame 0 (start)
- Frame 100 (early)
- 25% through video
- 50% through video
- 75% through video
- Near end (last 10 frames)

### Locked Golden Frames

| Video | Frame Indices | Total |
|-------|---------------|-------|
| IMG_6535.MOV | 0, 100, 171, 343, 514, 676 | 6 |
| IMG_1276.MOV | 0, 100, 1844, 3689, 5534, 7369 | 6 |
| DSC_3310.MOV | 0, 100, 944, 1888, 2832, 3767 | 6 |
| **Total** | | **18** |

### File Structure

```
data/golden_frames/
├── manifest.json                    # Master manifest with SHA256 hashes
├── IMG_6535_frame_0.png            # Raw frame
├── IMG_6535_frame_0_masked.png     # Frame with ROI applied
├── IMG_6535_frame_100.png
├── IMG_6535_frame_100_masked.png
├── ... (36 files total: 18 raw + 18 masked)
```

### Immutability Guarantee

Each frame has SHA256 hash stored in manifest. Any modification to golden frames will be detected by hash mismatch.

---

## 6. STEP_03: Preprocessing Baseline

### Purpose

Enhance frame quality to improve detection accuracy. Normalize lighting, reduce noise, and suppress glare while preserving bead edges.

### 6-Stage Pipeline

| Stage | Operation | Purpose |
|-------|-----------|---------|
| 1 | Grayscale conversion | Simplify to single channel |
| 2 | ROI masking | Zero out areas outside drum |
| 3 | Morphological top-hat | Normalize uneven lighting |
| 4 | CLAHE | Enhance local contrast |
| 5 | Bilateral filter | Reduce noise, preserve edges |
| 6 | Glare suppression | Threshold bright saturated regions |

### Configuration

```python
PREPROCESS_CONFIG = {
    # Top-hat morphology
    "tophat_kernel_size": 15,
    
    # CLAHE (Contrast Limited Adaptive Histogram Equalization)
    "clahe_clip_limit": 2.0,
    "clahe_tile_grid_size": 8,
    
    # Bilateral filter
    "bilateral_d": 9,
    "bilateral_sigma_color": 75,
    "bilateral_sigma_space": 75,
    
    # Glare suppression
    "glare_threshold": 250,
    "glare_replacement": 200,
}
```

### Results

| Video | Avg Contrast Before | Avg Contrast After | Improvement |
|-------|---------------------|--------------------| ------------|
| IMG_6535 | 45.2 | 68.7 | +23.5 |
| IMG_1276 | 52.1 | 75.3 | +23.2 |
| DSC_3310 | 48.9 | 72.5 | +23.6 |
| **Average** | | | **+23.4** |

### Visual Effect

- **Before**: Uneven lighting, glare spots, low contrast in shadows
- **After**: Uniform brightness, suppressed glare, enhanced bead edges

---

## 7. STEP_04: Candidate Generation

### Purpose

Detect circular candidates using HoughCircles. Generate over-detections that will be filtered in later steps.

### Algorithm

1. **Calculate radius range** from drum geometry and expected bead sizes:
   ```python
   min_radius_mm = 3.0 / 2  # Smallest bead diameter / 2
   max_radius_mm = 12.0 / 2 # Largest bead diameter / 2
   
   min_radius_px = int(min_radius_mm * px_per_mm * 0.7)  # 30% margin
   max_radius_px = int(max_radius_mm * px_per_mm * 1.5)  # 50% margin
   ```

2. **Apply resolution-adaptive param2**:
   ```python
   base_param2 = 25
   height = frame.shape[0]
   param2 = max(25, int(base_param2 * sqrt(height / 1080)))
   
   # Results:
   # 1080p: param2 = 25
   # 4K (2160p): param2 = 35
   ```

3. **Run HoughCircles**:
   ```python
   circles = cv2.HoughCircles(
       gray,
       cv2.HOUGH_GRADIENT,
       dp=1,
       minDist=min_radius_px * 0.5,
       param1=50,
       param2=param2,  # Resolution-adaptive
       minRadius=min_radius_px,
       maxRadius=max_radius_px
   )
   ```

### Configuration

```python
DETECTION_BEAD_CONFIG = {
    "drum_diameter_mm": 200,
    "min_bead_diameter_mm": 3.0,
    "max_bead_diameter_mm": 12.0,
    "dp": 1,
    "min_dist_ratio": 0.5,
    "param1": 50,
    "param2": 25,  # Base value, scaled by resolution
    "radius_margin_low": 0.7,
    "radius_margin_high": 1.5,
}
```

### Results by Video

| Video | Resolution | param2 | Min R (px) | Max R (px) | Candidates/Frame |
|-------|------------|--------|------------|------------|------------------|
| IMG_6535 | 4K | 35 | 9 | 78 | 765 - 1,350 |
| IMG_1276 | 1080p | 25 | 4 | 33 | 203 - 337 |
| DSC_3310 | 1080p | 25 | 5 | 45 | 517 - 3,351* |

*DSC_3310 frame 0 is an outlier with 3,351 candidates.

### Design Rationale

> **Intentional over-detection**: Generate more candidates than needed, then filter by confidence and other criteria in STEP_05/06. Better to have false positives (filtered later) than false negatives (missed beads).

---

## 8. STEP_05: Confidence Scoring

### Purpose

Assign confidence scores [0.0, 1.0] to each detection based on observable image evidence.

### Algorithm

```
confidence = 0.35×edge_strength + 0.25×circularity + 0.20×interior + 0.20×radius_fit
```

### Feature Definitions

| Feature | Weight | Description | Good Score |
|---------|--------|-------------|------------|
| Edge Strength | 35% | Gradient magnitude along circle perimeter | Strong, defined edge |
| Circularity | 25% | Consistency of edge around full perimeter | Uniform all around |
| Interior Uniformity | 20% | Brightness/texture pattern inside circle | Metallic bead pattern |
| Radius Fit | 20% | Match to expected bead size range | Mid-range radius |

### Configuration

```python
CONFIDENCE_CONFIG = {
    "weight_edge_strength": 0.35,
    "weight_circularity": 0.25,
    "weight_interior": 0.20,
    "weight_radius_fit": 0.20,
    "edge_sample_points": 36,
    "edge_gradient_sigma": 1.0,
    "interior_sample_ratio": 0.7,
    "radius_fit_optimal_min": 0.2,
    "radius_fit_optimal_max": 0.8,
}
```

### Results

| Metric | Value |
|--------|-------|
| Total scored | 14,234 |
| Mean confidence | 0.495 |
| Std deviation | 0.142 |
| Range | [0.085, 0.938] |

### Confidence Distribution

| Range | Count | Percentage |
|-------|-------|------------|
| [0.0 - 0.2) | 39 | 0.3% |
| [0.2 - 0.4) | 3,519 | 24.7% |
| [0.4 - 0.6) | 8,103 | 56.9% |
| [0.6 - 0.8) | 1,638 | 11.5% |
| [0.8 - 1.0) | 935 | 6.6% |

### Per-Video Performance

| Video | Total | High (≥0.7) | Mean | Quality |
|-------|-------|-------------|------|---------|
| IMG_6535 | 6,490 | 0 (0%) | 0.450 | ⚠️ Score compression |
| IMG_1276 | 1,591 | 1,345 (85%) | 0.777 | ✅ Excellent |
| DSC_3310 | 6,153 | 315 (5%) | 0.511 | ⚠️ Frame 0 outlier |

---

## 9. STEP_06: Filtering and Cleanup

**Status**: ✅ Complete (PM Approved 2025-12-12)

### Purpose

Apply 3-stage filtering to reduce false positives and produce clean detection output.

### Algorithm

Three sequential filters applied in order:

1. **Rim Margin Filter** (12% of radius)
   - Removes detections in outer rim zone
   - Targets: bolts, purple ring, edge artifacts
   
2. **Confidence Threshold** (≥0.5)
   - Removes low-confidence noise detections
   - Most aggressive filter (62% reduction)
   
3. **Non-Maximum Suppression** (50% overlap)
   - Merges overlapping detections
   - Keeps highest-confidence in each group

### Configuration

```python
FILTER_CONFIG = {
    "rim_margin_ratio": 0.12,        # 12% of drum radius
    "min_confidence": 0.5,           # Minimum confidence
    "nms_overlap_threshold": 0.5,    # 50% overlap threshold
    "filter_order": ["rim", "confidence", "nms"],
}
```

### Results

| Stage | Count | Reduction |
|-------|-------|-----------|
| Input | 14,234 | - |
| After Rim | 13,524 | 5.0% |
| After Confidence | 5,133 | 62.0% |
| After NMS | 1,830 | 64.3% |
| **Final** | **1,830** | **87.1%** |

### Per-Video Results

| Video | Input | Output | Retention |
|-------|-------|--------|-----------|
| IMG_6535 | 6,490 | 433 | 6.7% |
| IMG_1276 | 1,591 | 687 | 43.2% |
| DSC_3310 | 6,153 | 710 | 11.5% |

### Visual Assessment

- ✅ Green circles well-placed on actual beads
- ✅ Red circles (rejected) on rim, bolts, noise
- ✅ White boundary circle shows rim margin working
- ✅ No obvious overlapping detections after NMS

---

## 10. UI/Visualization (Phase 9)

**Status**: 🟡 In Progress

### Purpose

Implement a desktop application for visualization and playback of cached detection results. The UI reads from detection cache only (no real-time CV), ensuring smooth playback at 30-60 FPS.

### Framework & Architecture

| Component | Technology |
|-----------|------------|
| Framework | PySide6 (Qt6 for Python) |
| Architecture | 5-panel layout (Top, Left, Center, Right, Bottom) |
| State Machine | IDLE → VIDEO_LOADED → PROCESSING → CACHE_READY |
| Detection Source | Cache files (JSON) |

### UI Components

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ [A] TOP BAR: MillPresenter | Video: mill_run1.mp4 | State | Detection %    │
├────────────┬───────────────────────────────────────────────┬────────────────┤
│ [E] LEFT   │                                               │ [C] RIGHT      │
│ ┌────────┐ │                                               │ ┌────────────┐ │
│ │Stats│Info│                                               │ │Overlay│Proc││
│ ├────────┤ │                                               │ ├────────────┤ │
│ │Total:  │ │                                               │ │Master:     │ │
│ │  342   │ │              [B] VIDEO VIEWPORT               │ │ ☐ Overlays │ │
│ ├────────┤ │                                               │ ├────────────┤ │
│ │By Class:│ │          (Colored circle overlays)           │ │Opacity 100%│ │
│ │● 4mm:85│ │                                               │ │━━━━━━━━━━━━│ │
│ │● 6mm:120│                                               │ ├────────────┤ │
│ │● 8mm:95│ │                                               │ │Conf: 0.50  │ │
│ │● 10mm:42│                                               │ │━━━━━━━━━━━━│ │
│ ├────────┤ │                                               │ ├────────────┤ │
│ │Conf Dist│ │                                               │ │Class Toggle│ │
│ │ ▁▂▅▇▅▂ │ │                                               │ │☑ ● 4mm    │ │
│ ├────────┤ │                                               │ │☑ ● 6mm    │ │
│ │Run Avg │ │                                               │ │☑ ● 8mm    │ │
│ │ ╱╲╱╲╱  │ │                                               │ │☑ ● 10mm   │ │
│ └────────┘ │                                               │ └────────────┘ │
├────────────┴───────────────────────────────────────────────┴────────────────┤
│ [D] BOTTOM: ⏮ ▶ ⏭ 🔁 │━━━━━━━━━━━●━━━━━━━━━━━━│ 15:32/45:00 │ Speed: 1.0x │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Functional Requirements Summary

| Category | Count | Key Features |
|----------|-------|--------------|
| FR1: Video Playback | 9 | Play/pause, stepping, timeline, speed control |
| FR2: Overlay Visualization | 8 | Master toggle, opacity, per-class, confidence filter |
| FR3: Statistics Display | 5 | Total count, per-class breakdown, histogram, trend |
| FR4: Detection Processing | 5 | Trigger pipeline, progress, cancel, background thread |
| FR5: Calibration | 4 | Auto/manual calibration, ROI visualization |
| FR6: Parameter Fine-Tuning | 7 | Real-time preview, offline batch, presets |
| FR7: File Operations | 6 | Open video, load cache, export JSON/CSV/PNG/MP4 |
| FR8: Viewport Interaction | 4 | Zoom, pan, reset, aspect ratio |
| FR9: State Management | 3 | State display, control disabling, transitions |
| FR10: Layout & Navigation | 4 | Panel visibility, help section, tooltips |
| FR11: Keyboard Shortcuts | 8 | Space, arrows, Home/End, L, F11, F1, Ctrl+H |
| **Total** | **48** | |

### Key Files

| File | Purpose |
|------|---------|
| `ui/main.py` | Application entry point |
| `ui/main_window.py` | QMainWindow with 5-panel layout |
| `ui/video_controller.py` | VideoController + DetectionCache classes |
| `ui/widgets/right_panel.py` | Overlay, Process, Calibrate, Export tabs |
| `ui/widgets/left_panel.py` | Stats, histogram, trend graph |
| `ui/widgets/bottom_bar.py` | Transport controls, timeline, speed |
| `ui/widgets/video_viewport.py` | Frame display, overlays, zoom/pan |
| `docs/UI_IMPLEMENTATION_PLAN.md` | Full specification (48 FRs) |

### Detection Cache Format

```json
{
  "metadata": {
    "video_name": "IMG_1276.MOV",
    "video_path": "data/IMG_1276.MOV",
    "total_frames": 7379,
    "fps": 30.0,
    "resolution": [1920, 1080],
    "created_at": "2025-12-12T10:30:00Z"
  },
  "config": {
    "px_per_mm": 3.65,
    "confidence_threshold": 0.5
  },
  "frames": [
    {
      "frame_idx": 0,
      "timestamp": 0.0,
      "detections": [
        {"x": 840, "y": 454, "r_px": 31.4, "conf": 0.85, "cls": "8mm"}
      ]
    }
  ]
}
```

### Testing

- Automated test suite: pytest + pytest-qt
- 7 test files covering all major components
- Tests pending execution

---

## 11. Cross-Step Analysis

### Data Flow Summary

```
Video → STEP_01 → Geometry (cached)
              ↓
Frame → STEP_03 → Preprocessed grayscale
              ↓
        STEP_04 → Raw candidates (x, y, r_px)
              ↓
        STEP_05 → Scored candidates (x, y, r_px, conf)
              ↓
        STEP_06 → Filtered candidates (1,830 from 14,234)
              ↓
        [STEP_07] → Classified (x, y, r_px, conf, cls)
```

### Processing Statistics

| Step | Input | Output | Reduction |
|------|-------|--------|----------|
| STEP_01 | Frame | 1 geometry | N/A |
| STEP_03 | Frame | Preprocessed | N/A |
| STEP_04 | Preprocessed | ~800 candidates/frame avg | N/A |
| STEP_05 | Candidates | Scored candidates | 0% (scoring only) |
| STEP_06 | Scored | Filtered | 87.1% |
| **Total Pipeline** | 14,234 candidates | 1,830 filtered | **87.1%** |

### Bottleneck Analysis

| Step | Time/Frame (4K) | Time/Frame (1080p) | Bottleneck |
|------|-----------------|--------------------| -----------|
| STEP_01 | ~0.5s (once) | ~0.3s (once) | HoughCircles |
| STEP_03 | ~0.2s | ~0.1s | CLAHE + bilateral |
| STEP_04 | ~0.3s | ~0.1s | HoughCircles |
| STEP_05 | ~2-3s | ~0.5-1s | Gradient computation |

---

## 12. Video-Specific Insights

### IMG_6535.MOV (4K, 3840×2160)

| Characteristic | Value |
|----------------|-------|
| Resolution | 3840×2160 (4K) |
| Frame count | ~686 |
| Drum radius | 872 px |
| px_per_mm | 8.72 |
| Avg candidates/frame | ~1,000 |
| Confidence range | [0.20, 0.68] |

**Observations**:
- ✅ Good bead visibility, well-lit
- ✅ Detection coverage is good
- ⚠️ No high-confidence scores (max 0.675)
- ⚠️ Gradient normalization may need resolution scaling

**Recommendation**: Apply resolution-adaptive gradient normalization for confidence scoring.

---

### IMG_1276.MOV (1080p, 1920×1080)

| Characteristic | Value |
|----------------|-------|
| Resolution | 1920×1080 (1080p) |
| Frame count | ~7,380 |
| Drum radius | 365 px |
| px_per_mm | 3.65 |
| Avg candidates/frame | ~265 |
| Confidence range | [0.31, 0.94] |

**Observations**:
- ✅ Best performing video
- ✅ 85% high-confidence detections
- ✅ Excellent bead/noise separation
- ✅ Clear, well-lit footage

**Recommendation**: Use as reference baseline for tuning other videos.

---

### DSC_3310.MOV (1080p, 1920×1080)

| Characteristic | Value |
|----------------|-------|
| Resolution | 1920×1080 (1080p) |
| Frame count | ~3,777 |
| Drum radius | 496 px |
| px_per_mm | 4.96 |
| Avg candidates/frame | ~560 (excl. frame 0) |
| Confidence range | [0.09, 0.87] |

**Observations**:
- ⚠️ Frame 0 has 3,351 candidates (outlier)
- ⚠️ Purple inner ring creates false positives
- ⚠️ Mixed confidence distribution
- ✅ Other frames perform reasonably

**Recommendation**: 
1. Investigate frame 0 anomaly (lighting? glare?)
2. Rim margin filter will help with purple ring FPs

---

## 13. Configuration Reference

### Complete Configuration (config.py)

```python
# =============================================================================
# Drum Detection Configuration (STEP_01)
# =============================================================================

DETECTION_CONFIG = {
    "min_radius_ratio": 0.35,    # Min drum radius as ratio of frame height
    "max_radius_ratio": 0.48,    # Max drum radius as ratio of frame height
    "dp": 1,                     # Accumulator resolution ratio
    "param1": 50,                # Canny edge detection threshold
    "param2": 30,                # Accumulator threshold for drum
    "blur_ksize": 5,             # Gaussian blur kernel size
}

# =============================================================================
# Preprocessing Configuration (STEP_03)
# =============================================================================

PREPROCESS_CONFIG = {
    "tophat_kernel_size": 15,
    "clahe_clip_limit": 2.0,
    "clahe_tile_grid_size": 8,
    "bilateral_d": 9,
    "bilateral_sigma_color": 75,
    "bilateral_sigma_space": 75,
    "glare_threshold": 250,
    "glare_replacement": 200,
}

# =============================================================================
# Bead Detection Configuration (STEP_04)
# =============================================================================

DETECTION_BEAD_CONFIG = {
    "drum_diameter_mm": 200,
    "min_bead_diameter_mm": 3.0,
    "max_bead_diameter_mm": 12.0,
    "dp": 1,
    "min_dist_ratio": 0.5,
    "param1": 50,
    "param2": 25,
    "radius_margin_low": 0.7,
    "radius_margin_high": 1.5,
}

# =============================================================================
# Confidence Scoring Configuration (STEP_05)
# =============================================================================

CONFIDENCE_CONFIG = {
    "weight_edge_strength": 0.35,
    "weight_circularity": 0.25,
    "weight_interior": 0.20,
    "weight_radius_fit": 0.20,
    "edge_sample_points": 36,
    "edge_gradient_sigma": 1.0,
    "interior_sample_ratio": 0.7,
    "radius_fit_optimal_min": 0.2,
    "radius_fit_optimal_max": 0.8,
}
```

---

## 14. File Structure

### Project Layout

```
MillPresenter/
├── CURRENT_STEP.md              # Active step definitions
├── config/
│   ├── geometry.json            # Default geometry
│   └── {video_hash}.json        # Per-video cached geometry
├── cache/
│   └── detections/              # Detection cache files (JSON)
├── context/
│   ├── agent_context.md
│   └── mill_presenter_context.txt
├── data/
│   ├── golden_frames/
│   │   ├── manifest.json        # SHA256 hashes
│   │   └── *.png                # 36 golden frame images
│   └── [videos not in repo]
├── docs/
│   ├── data_contracts.md
│   ├── failure_modes.md
│   ├── MillPresenter_UI_Spec.md
│   ├── UI_IMPLEMENTATION_PLAN.md  # UI specification (48 FRs)
│   ├── project_glossary.md
│   ├── PROJECT_OVERVIEW.md
│   ├── STEP_05_CONFIDENCE_ANALYSIS.md
│   └── PIPELINE_ANALYSIS_COMPLETE.md  # This document
├── output/
│   ├── run_manifest.json
│   ├── preprocess_test/         # STEP_03 outputs
│   ├── detection_test/          # STEP_04 outputs
│   ├── confidence_test/         # STEP_05 outputs
│   └── filter_test/             # STEP_06 outputs
├── rules/
│   ├── MAIN.md                  # Master rules
│   ├── HANDOFF_PACKET.md
│   ├── CURRENT_STEP_RULES.md
│   ├── iteration_tracker.md
│   ├── ACCEPTANCE_METRICS.md
│   ├── PM_REVIEW_POLICY.md
│   ├── KNOWN_ISSUES.md
│   ├── architect_agent.md
│   └── developer_agent.md
├── src/
│   ├── __init__.py
│   ├── config.py                # Central configuration
│   ├── drum.py                  # STEP_01: Geometry detection
│   ├── preprocess.py            # STEP_03: Preprocessing
│   ├── detect.py                # STEP_04: Candidate generation
│   ├── confidence.py            # STEP_05: Confidence scoring
│   ├── filter.py                # STEP_06: Filtering
│   ├── step01_drum_geometry.py  # Test script
│   ├── step02_golden_frames.py  # Test script
│   ├── step03_preprocess.py     # Test script
│   ├── step04_detect.py         # Test script
│   ├── step05_confidence.py     # Test script
│   └── step06_filter.py         # Test script
├── tests/
│   ├── conftest.py              # Pytest fixtures
│   ├── test_main_window.py      # UI tests
│   └── ...                      # Other test files
└── ui/
    ├── __init__.py
    ├── main.py                  # Application entry point
    ├── main_window.py           # QMainWindow with 5-panel layout
    ├── video_controller.py      # Video playback + detection cache
    ├── theme.py                 # Colors, dimensions, fonts
    ├── state.py                 # Application state management
    └── widgets/
        ├── top_bar.py
        ├── left_panel.py
        ├── video_viewport.py
        ├── right_panel.py
        └── bottom_bar.py
```

### Output Artifacts

| Directory | Contents |
|-----------|----------|
| `output/preprocess_test/` | 18 preprocessed frames + comparison grids |
| `output/detection_test/` | 18 candidate overlays + JSON files |
| `output/confidence_test/` | 18 confidence overlays + scored JSON files |
| `output/filter_test/` | 18 filtered overlays + JSON files |
| `cache/detections/` | Detection cache files for playback |

---

## 15. Known Issues & Limitations

### Critical Issues

| Issue | Impact | Status | Resolution |
|-------|--------|--------|------------|
| ~~DSC_3310 frame 0 explosion~~ | ~~3,351 candidates (6x normal)~~ | ✅ Resolved | Filtered by STEP_06 (95.5% reduction) |
| 4K confidence compression | No scores above 0.675 | Known | Optional: resolution-adaptive normalization |
| Video scrubbing latency | 600ms+ delay on large seeks | Known | See KNOWN_ISSUES.md ISSUE_001 |

### Design Limitations

| Limitation | Cause | Mitigation | Status |
|------------|-------|------------|--------|
| Purple ring FPs | Real circular edge | Rim margin filter (12%) | ✅ Implemented |
| Glare can score medium | High intensity + edges | Could add glare feature | ⚠️ Optional |
| Edge strength saturation | Fixed 150 normalization | Could use percentile scaling | ⚠️ Optional |
| Motion blur detection | Elongated shapes | HoughCircles naturally penalizes | ✅ Acceptable |

### Not Yet Implemented

| Feature | Planned Step | Status |
|---------|--------------|--------|
| ~~Rim margin filtering~~ | ~~STEP_06~~ | ✅ Complete |
| ~~Confidence thresholding~~ | ~~STEP_06~~ | ✅ Complete |
| ~~Non-maximum suppression~~ | ~~STEP_06~~ | ✅ Complete |
| Size classification | STEP_07 | ⏳ Pending |
| Quality metrics | STEP_08 | ⏳ Pending |
| UI Application | Phase 9 | 🟡 In Progress |
| Overlay rendering | Phase 9 | 🟡 In Progress |
| Video playback | Phase 9 | 🟡 In Progress |
| Video export with overlays | Phase 10 | ⏳ Pending |

---

## 16. Recommendations

### Completed (STEP_06) ✅

1. **✅ Rim margin filter** - Implemented at 12% of radius
2. **✅ Confidence threshold** - Implemented at 0.5 (62% reduction)
3. **✅ NMS** - Implemented at 50% overlap threshold

### Immediate (STEP_07: Size Classification)

1. **Implement size classification**
   - Apply px_per_mm calibration to filtered detections
   - Convert r_px → diameter_mm
   - Classify into 4mm/6mm/8mm/10mm bins
   - Use bin boundaries from true physical sizes

2. **Calibration validation**
   - Verify px_per_mm values per video
   - Cross-check against known drum diameter (200mm)

### Immediate (UI Development - Phase 9)

1. **Complete UI testing**
   - Run automated pytest-qt test suite
   - Verify all 48 functional requirements
   - Test keyboard shortcuts

2. **Finalize overlay controls**
   - Master toggle, opacity, class toggles
   - Confidence threshold slider
   - Real-time update (<50ms)

3. **Statistics panel**
   - Total count, per-class breakdown
   - Confidence histogram
   - Running average graph

### Optional Tuning

1. **Resolution-adaptive gradient normalization**
   ```python
   norm_factor = 150 * sqrt(height / 1080)
   ```
   - Would improve 4K confidence scores

2. **Per-video threshold tuning**
   - IMG_1276: Could use 0.7 (high-quality video)
   - IMG_6535: Could use 0.5 (compressed scores)
   - DSC_3310: Could use 0.6 (mixed quality)

3. **Glare detection feature**
   - Detect saturated bright regions
   - Penalize detections centered on glare

### Future Considerations

1. **Temporal smoothing**
   - Average detections across N frames
   - Reduce frame-to-frame jitter

   

2. **Tracking**
   - Link detections across frames
   - Enable bead counting over time

3. **Confidence calibration**
   - Map scores to actual precision
   - Requires ground truth annotations

---

## 17. Appendix

### A. Iteration History

| ITER | Step | Description | Status |
|------|------|-------------|--------|
| 0001 | STEP_01 | Drum geometry detection | ✅ Approved |
| 0002 | STEP_02 | Golden frames lock (18 frames) | ✅ Approved |
| 0003 | STEP_03 | Preprocessing baseline | ✅ Approved |
| 0004 | STEP_03 | ROI mask fix (full radius) | ✅ Approved |
| 0005 | STEP_04 | Candidate generation | ✅ Approved |
| 0006 | STEP_05 | Confidence scoring | ✅ Approved |
| 0007 | STEP_06 | Filtering & cleanup (87.1% reduction) | ✅ Approved |
| 0008 | UI | UI Implementation (Phase 9) | 🟡 In Progress |

### B. Test Video Specifications

| Property | IMG_6535 | IMG_1276 | DSC_3310 |
|----------|----------|----------|----------|
| Resolution | 3840×2160 | 1920×1080 | 1920×1080 |
| Frame count | ~686 | ~7,380 | ~3,777 |
| FPS | ~30 | ~30 | ~30 |
| Duration | ~23s | ~4min | ~2min |
| Drum radius (px) | 872 | 365 | 496 |
| px_per_mm | 8.72 | 3.65 | 4.96 |

### C. Detection Output Format

```json
{
  "video": "IMG_1276",
  "frame_idx": 0,
  "total_candidates": 337,
  "high_confidence": 316,
  "medium_confidence": 21,
  "low_confidence": 0,
  "mean_confidence": 0.8137,
  "config_used": { ... },
  "detections": [
    {
      "x": 840,
      "y": 454,
      "r_px": 31.4,
      "conf": 0.641,
      "features": {
        "edge_strength": 1.0,
        "circularity": 0.376,
        "interior": 0.885,
        "radius_fit": 0.103
      }
    }
  ]
}
```

### D. Threshold Impact Analysis

| Threshold | Retained | % of Total | Use Case |
|-----------|----------|------------|----------|
| 0.8 | 935 | 6.6% | High precision |
| 0.7 | 1,660 | 11.7% | Balanced |
| 0.6 | 2,573 | 18.1% | Higher recall |
| 0.5 | 5,701 | 40.1% | Permissive |
| 0.4 | 10,695 | 75.1% | Very permissive |
| 0.3 | 13,676 | 96.1% | Minimal filtering |

### E. Key Formulas

**Calibration**:
```
px_per_mm = drum_radius_px / (drum_diameter_mm / 2)
diameter_mm = (r_px * 2) / px_per_mm
```

**Resolution-adaptive param2**:
```
param2 = max(25, int(25 * sqrt(height / 1080)))
```

**Confidence**:
```
conf = 0.35*edge + 0.25*circ + 0.20*int + 0.20*rad
```

**Radius fit**:
```
optimal_min = min_radius + 0.2 * range
optimal_max = max_radius - 0.2 * range
score = 1.0 if optimal_min <= r <= optimal_max
```

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-01 | DeepSeek v3 & Gui | Initial complete analysis || 1.1 | 2025-12-12 | Claude Opus 4.5 | Added STEP_05/06 details |
| 1.2 | 2025-12-12 | Claude Opus 4.5 | STEP_06 complete, UI phase added, updated TOC |
---

*End of MillPresenter Pipeline Analysis Document*
