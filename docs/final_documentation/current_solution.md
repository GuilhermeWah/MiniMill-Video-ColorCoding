# MillPresenter Current Solution Reference

## Document Purpose

This document describes the **current refactored implementation** of MillPresenter. It serves as the counterpart to `old_solution` for cross-codebase comparison.

For critical analysis of gaps and recommendations, see: [CRITICAL_CODEBASE_COMPARISON.md](CRITICAL_CODEBASE_COMPARISON.md)

---

## Architecture: "Detect Once, Play Forever"

The current implementation follows the same high-level architecture as legacy:

1. **Offline Detection Pass** — Heavy compute: decode → preprocess → detect → score → filter → classify → cache
2. **Live Playback** — Light compute: decode → lookup cache → draw overlay

**Key invariant preserved**: Playback toggles (4/6/8/10mm) never trigger re-detection.

---

## Repository Layout

### Pipeline Modules (`src/`)

| Module | STEP | Responsibility |
|--------|------|----------------|
| `config.py` | 01 | All configuration parameters, geometry caching |
| `drum.py` | 01 | ROI mask generation, geometry overlay |
| `preprocess.py` | 03 | 6-stage preprocessing pipeline |
| `detect.py` | 04 | HoughCircles candidate generation |
| `confidence.py` | 05 | Multi-feature confidence scoring |
| `filter.py` | 06 | 3-stage filtering (rim, confidence, NMS) |
| `classify.py` | 07 | Size classification (px → mm → class) |
| `metrics.py` | 08 | Quality metrics computation |
| `cache.py` | 09 | Detection cache read/write |

### UI Modules (`ui/`)

| Module | Purpose |
|--------|---------|
| `main_window.py` | Main window layout and control wiring |
| `video_controller.py` | Video decoding and playback control |
| `app_state_manager.py` | State machine (IDLE → VIDEO_LOADED → PROCESSING → CACHE_READY) |
| `video_widget.py` | OpenGL-backed video surface with overlay |
| `detection_controller.py` | Offline detection orchestration |

### Step Scripts (`src/step*.py`)

Each STEP has a standalone test script for validation:
- `step01_drum_geometry.py` — Geometry auto-detection test
- `step02_golden_frames.py` — Frame extraction
- `step03_preprocess.py` — Preprocessing pipeline test
- `step04_detect.py` — Detection test
- `step05_confidence.py` — Confidence scoring test
- `step06_filter.py` — Filter pipeline test
- `step07_classify.py` — Classification test
- `step08_metrics.py` — Metrics generation
- `step09_playback.py` — Playback test

---

## Data Contracts

### Detection (Pixel-Space Only)

```python
@dataclass
class Detection:
    x: int          # Center x (pixels)
    y: int          # Center y (pixels)
    r_px: float     # Radius (pixels)
```

### Scored Detection

```python
@dataclass
class ScoredDetection:
    x: int
    y: int
    r_px: float
    conf: float                    # [0.0, 1.0]
    features: Dict[str, float]     # Per-feature scores
```

### Classified Detection (Final Output)

```python
@dataclass
class ClassifiedDetection:
    x: int
    y: int
    r_px: float
    conf: float
    diameter_mm: float
    cls: str           # "4mm", "6mm", "8mm", "10mm", "unknown"
```

### Cache Format (JSON)

```json
{
  "metadata": {
    "video_path": "path/to/video.MOV",
    "video_name": "video",
    "total_frames": 5000,
    "fps": 30.0,
    "width": 1920,
    "height": 1080,
    "px_per_mm": 12.5,
    "drum_center": [960, 540],
    "drum_radius": 450,
    "created_at": "2025-01-XX"
  },
  "config": {...},
  "frames": {
    "0": {
      "frame_idx": 0,
      "timestamp": 0.0,
      "detections": [
        {"x": 100, "y": 200, "r_px": 15.5, "conf": 0.85, "diameter_mm": 6.2, "cls": "6mm"}
      ],
      "stats": {"total": 1, "4mm": 0, "6mm": 1, "8mm": 0, "10mm": 0}
    }
  }
}
```

---

## Pipeline Stages

### Stage 1: Drum Geometry (STEP_01)

**Implementation**: `src/config.py`, `src/drum.py`

1. Auto-detect drum circle via HoughCircles
2. Cache result per video (hash-based)
3. Generate ROI mask from geometry

**Key parameters** (relative to frame height):
- `min_radius_ratio`: 0.35
- `max_radius_ratio`: 0.48
- `rim_margin_ratio`: 0.04

### Stage 2: Preprocessing (STEP_03)

**Implementation**: `src/preprocess.py`

6-stage pipeline, each toggleable:
1. Grayscale conversion
2. ROI mask application
3. Top-hat transform (illumination normalization)
4. CLAHE (contrast enhancement)
5. Bilateral filter (noise reduction)
6. Glare suppression (optional, disabled by default)

### Stage 3: Detection (STEP_04)

**Implementation**: `src/detect.py`

- Uses `cv2.HoughCircles` only (no contour path)
- Radius range calculated from drum geometry and bead size assumptions
- Resolution-adaptive param2 scaling for 4K vs 1080p

**Key parameters**:
- `dp`: 1
- `param1`: 50 (Canny high threshold)
- `param2`: 25 (accumulator threshold, scaled by resolution)
- `min_dist_ratio`: 0.5

### Stage 4: Confidence Scoring (STEP_05)

**Implementation**: `src/confidence.py`

4-feature weighted scoring:

| Feature | Weight | Description |
|---------|--------|-------------|
| Edge Strength | 35% | Average gradient magnitude along circumference |
| Circularity | 25% | Coefficient of variation of edge samples |
| Interior Uniformity | 20% | Intensity pattern inside circle |
| Radius Fit | 20% | Match to expected bead size range |

### Stage 5: Filtering (STEP_06)

**Implementation**: `src/filter.py`

3-stage sequential filtering:

1. **Rim Margin** — Reject detections outside inner ROI (12% margin default)
2. **Confidence** — Reject conf < 0.5
3. **NMS** — Suppress overlapping detections (50% overlap threshold)

### Stage 6: Classification (STEP_07)

**Implementation**: `src/classify.py`

1. Calculate `px_per_mm` from drum geometry
2. Convert radius to diameter in mm
3. Bin into size class:
   - 4mm: 2.0–5.0mm
   - 6mm: 5.0–7.0mm
   - 8mm: 7.0–9.0mm
   - 10mm: 9.0–13.0mm

---

## Video Decoding

**Implementation**: `ui/video_controller.py`

Uses `cv2.VideoCapture`:
- Frame-based seeking via `CAP_PROP_POS_FRAMES`
- QTimer-based playback loop
- Speed control (0.1x–4.0x)
- Loop toggle

**Signals**:
- `frame_ready(np.ndarray, int)` — Frame + index
- `playback_finished()` — End of video
- `error_occurred(str)` — Error message

---

## Configuration Surface

All parameters exposed in `src/config.py`:

### DETECTION_CONFIG (Drum detection)
- Radius ratios, HoughCircles params, rim margin

### PREPROCESS_CONFIG
- Stage enables, kernel sizes, CLAHE params, blur params

### DETECTION_BEAD_CONFIG
- Bead size assumptions, HoughCircles params for bead detection

### CONFIDENCE_CONFIG
- Feature weights, sampling parameters

### FILTER_CONFIG
- Rim margin ratio, min confidence, NMS threshold

### SIZE_CONFIG
- Size bins, class colors, label options

---

## Performance Model

- **Offline detection**: Seconds per frame (allowed to be slow)
- **Playback target**: 30-60 FPS
- **Playback operations per frame**:
  1. Video decode (OpenCV)
  2. Cache lookup (O(1) dict)
  3. Overlay draw (simple loop)
  - No CV operations during playback

---

## Key Differences from Legacy

| Aspect | Legacy | Current |
|--------|--------|---------|
| Detection | Dual-path (Hough + Contour) | Single-path (Hough only) |
| Filtering | 4-stage (incl. brightness, annulus) | 3-stage |
| Confidence | Flat 0.8 | Multi-feature |
| Caching | JSONL (append-only) | JSON (atomic) |
| Video | PyAV | OpenCV |
| Config | YAML file | Python dicts + hash cache |

For detailed analysis of these differences, see [CRITICAL_CODEBASE_COMPARISON.md](CRITICAL_CODEBASE_COMPARISON.md).

---

## Quality Metrics (STEP_08)

**Implementation**: `src/metrics.py`

Computed metrics:
- **Count Stability**: CV of detection counts across frames
- **Size Distribution**: Per-class proportions over time
- **Confidence Distribution**: Mean, median, std, histogram
- **Throughput**: Processing time per frame

Acceptance criteria:
- Count CV < 0.35 (Acceptable)
- Confidence range > 0.2 (not collapsed)
- All frames processed without error
