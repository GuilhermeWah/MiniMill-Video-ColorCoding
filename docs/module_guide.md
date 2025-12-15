# MillPresenter Module Guide

This guide summarizes the main modules in the project and how they collaborate in the **Scan Once, Play Forever** workflow.

## Core Data Models (`core/models.py`)
- **`Ball`**: A single bead detection.
  - Fields: `x`, `y`, `r_px`, `diameter_mm`, `cls` (4/6/8/10), `conf`.
- **`FrameDetections`**: All beads for one frame.
  - Fields: `frame_id`, `timestamp`, `balls: list[Ball]`.

## Video I/O (`core/playback.py`)
- **`FrameLoader`**
  - Opens the video using PyAV.
  - Applies rotation metadata (e.g., 90° from phone footage).
  - Provides:
    - `iter_frames(start_frame=0) -> (frame_index, frame_bgr)`
    - `seek(frame_index)` for scrub support.
  - Used by both the offline detection pipeline and the live player.

## Vision Pipeline (`core/processor.py`)
- **`VisionProcessor`**
  - Implements the Bilateral → CLAHE → Hough + Contours + Annulus pipeline.
  - Consumes:
    - Raw BGR frames.
    - Optional ROI mask (`roi_mask.png` → numpy array) to ignore static clutter.
    - Calibration `px_per_mm` and `bins_mm` from the YAML config.
  - Produces:
    - A list of `Ball` objects ready to be wrapped in `FrameDetections`.

## Detection Orchestration & Cache (`core/orchestrator.py`, `core/cache.py`)
- **`ProcessorOrchestrator`** (in `core/orchestrator.py`)
  - Drives the offline detection loop:
    - Pulls frames from `FrameLoader`.
    - Calls `VisionProcessor.process_frame()`.
    - Saves to `ResultsCache`.
- **`ResultsCache`** (in `core/cache.py`)
  - Disk: appends each frame’s detections as one JSON object per line to `detections.jsonl`.
  - Memory: keeps a dictionary mapping `frame_id` → `FrameDetections` for O(1) lookup during playback and export.

## Overlays & Rendering (`core/overlay.py`, `core/exporter.py`)
- **`OverlayRenderer`**
  - Knows how to draw `FrameDetections` with a `QPainter`.
  - Uses pens pre-configured from `overlay.colors` in the config.
  - Shared by:
    - `VideoWidget` in the live UI.
    - `VideoExporter` in offline export.
- **`VideoExporter`** (in `core/exporter.py`)
  - Re-runs the decoded video offline to generate an MP4 with baked overlays.
  - Steps per frame:
    1. Decode frame through `FrameLoader` (rotation applied).
    2. Lookup detections from `ResultsCache`.
    3. Optionally filter detections using `roi_mask.png`.
    4. Wrap the frame in a `QImage` and call `OverlayRenderer.draw()`.
    5. Write the modified frame via `cv2.VideoWriter`.

## UI Layer (`ui/`)
- **`VideoWidget`** (`ui/widgets.py`)
  - OpenGL-backed video surface:
    - Draws the current frame and overlay circles.
    - Respects aspect ratio, maps widget coordinates → image coordinates.
  - Emits signals:
    - `clicked(x, y)` – single clicks in image space.
    - `mouse_pressed(x, y, is_left)`, `mouse_moved(x, y)`, `mouse_released(x, y)` – for drag-based tools.
- **`PlaybackController`** (`ui/playback_controller.py`)
  - Owns the playback state machine:
    - Uses a `QTimer` to step frames.
    - Seeks when the user moves the slider.
    - Ensures `FrameLoader` and `ResultsCache` are kept in sync.
- **`CalibrationController`** (`ui/calibration_controller.py`)
  - Orchestrates the 2-click calibration workflow on `VideoWidget`.
  - Updates `config['calibration']['px_per_mm']` and the on-screen calibration overlay.
- **`ROIController`** (`ui/roi_controller.py`)
  - Manages ROI painting on a `QImage` aligned with the video frame.
  - Produces:
    - A semi-transparent red overlay for the UI.
    - A grayscale `roi_mask.png` used by the vision pipeline and exporter.
- **`MainWindow`** (`ui/main_window.py`)
  - Top-level UI container.
  - Hosts:
    - Playback controls (Play/Pause, slider).
    - Size toggles (4/6/8/10mm).
    - Mode toggles (Calibrate, ROI Mask).
    - Export button (MP4 export with overlays).
  - Manages:
    - Status bar instructions for calibration and ROI.
    - Mutual exclusion between modes.
    - Config saving when calibration changes.
- **`ExportThread`** (`ui/main_window.py`)
  - Runs `VideoExporter.export()` on a background `QThread`.
  - Reports progress and errors back to a `QProgressDialog`.

## CLI & Scripts (`scripts/`)
- **`run_detection.py`**
  - Main CLI entry point for the offline detection pipeline.
- **`test_vision.py`**
  - Developer playground to run `VisionProcessor` on a single frame and save a debug image.
- **`create_roi_mask.py`**
  - Legacy helper for drawing an ROI mask before the in-app ROI tool existed; useful for regression or batch workflows.
- **`debug_vision.py`, `repro_synthetic.py`**
  - Utilities for debugging vision behavior on synthetic or recorded data.

Use this guide together with `docs/technical_primer.md` and `docs/design_decisions.md` to orient yourself before making changes.
