# MillPresenter Design & Architecture Decisions

## Core Philosophy: "Presentation First"
The primary goal is a smooth, glitch-free presentation for clients. 
- **Why?** If the video stutters or the UI lags while toggling overlays, the tool feels broken, regardless of detection accuracy.
- **Decision:** We prioritize playback smoothness (60fps) over real-time detection. Detection is done **once** (offline), and playback is just rendering pre-computed results.

## Architecture: Separation of Detection & Rendering
We explicitly decoupled the "Vision Pipeline" from the "Playback Engine".
- **Why?** Computer vision (Hough transforms, contours) is heavy and variable. Running it per-frame during playback risks frame drops.
- **Decision:** 
  - `ProcessorOrchestrator` runs the heavy math *before* the presentation starts.
  - `ResultsCache` stores the answer for every frame.
  - `OverlayRenderer` just draws circles. It's fast (O(1) lookup).

### Scan Once → Play Forever
- **Why?** Presenters need **instant** toggles (4/6/8/10 mm) with **zero** playback stutter.
- **Decision:**
  - Toggling a size class **never** re-runs detection or touches the disk.
  - The live UI only filters already-loaded `FrameDetections.balls` by class ID.
  - All heavy compute lives in the offline detection pass and optional export.

## Vision Pipeline: Dual-Path Proposals
We use both `HoughCircles` and `ContourFilter` (Canny edges) and merge them.
- **Why?** 
  - **Hough** is great for the "dense pile" where beads overlap and edges are messy.
  - **Contours** are better for "flying beads" or isolated ones where edges are crisp.
  - Using only one method missed too many beads in our tests.
- **Decision:** Run both, then use Non-Maximum Suppression (NMS) to merge duplicates.

### Contour Tuning Knobs
- **Why?** Synthetic calibration clips (used in CI) produce extremely "perfect" edges that lower the circularity scores even though the detection is valid. Production footage needs tighter limits to avoid false positives.
- **Decision:** Expose `vision.min_circularity` (default `0.75`) in the config. CI uses a looser value (`0.65`) without affecting the default behavior that production operators rely on.

## Annulus Handling (The "Hollow Bead" Problem)
Beads are rings, not solid balls.
- **Why?** A standard circle detector finds two circles: the outer rim and the inner hole.
- **Decision:** We explicitly detect concentric circles. If we see a small circle inside a large one, we know it's a hole, not a small bead. We **always** classify based on the outer diameter.

## Caching: JSONL + RAM Ring Buffer
- **Why JSONL?** It's human-readable, append-only (robust to crashes), and easy to parse line-by-line.
- **Why Ring Buffer?** Reading from disk for every frame at 60fps is risky (latency).
- **Decision:** We keep ~4 seconds of detections in RAM. As the video plays, we pre-load upcoming frames into RAM.

## Rendering: Shared Overlay Module
- **Why?** The "Export to MP4" feature must look *exactly* like the live UI.
- **Decision:** `core/overlay.py` is a standalone module that takes a `QPainter` and a list of `Balls`. Both the UI (`QOpenGLWidget`) and the Exporter call this same function.

## Raw Video Support (.MOV)
- **Why?** Clients use iPhones and Nikons. These cameras often save video "sideways" with a metadata flag.
- **Decision:** `FrameLoader` reads rotation metadata and rotates frames immediately upon load, so the rest of the pipeline sees upright images.

## Calibration Tool Design

- **Why?** All diameter-based decisions depend on `px_per_mm`. Hard-coding this value is brittle and error-prone when camera zoom or resolution changes.
- **Decision:**
  - Implement `CalibrationController` as a small state machine that lives beside the UI, not inside the vision code.
  - Let the user pick two points on a frame corresponding to a known physical distance (e.g., a reference ring). We compute `px_per_mm` and store it in the YAML config.
  - Use the status bar (`QStatusBar`) instead of blocking dialogs to guide the workflow (“Click START point”, “Click END point”, “Enter distance in mm…”).

## ROI Tool Design

- **Why?** Some structures (bolts, shell edges, flanges) are visually similar to beads and hard to mask purely via thresholds. Operators know these regions intuitively.
- **Decision:**
  - **Interactive Circle**: Instead of a "painting" tool (which is messy and hard to make perfect), we use a geometric Circle Tool. The user can drag the center or resize the rim. This matches the physical reality of the mill drum.
  - **Auto-Detect**: We use a large-radius Hough Transform to automatically find the drum rim when the tool opens, giving the user a 90% correct starting point.
  - **Mask Generation**: We generate `roi_mask.png` by drawing a filled white circle on a black background.
  - **Detection**: The pipeline drops any candidate whose center lies on a black pixel.

## Handling Spinning Drum Background

- **The Problem:** The back of the mill drum rotates. It has holes and bolts that move. A static ROI mask cannot block them because they change position every frame.
- **The Solution:**
  1.  **Static ROI**: Blocks the non-moving outer rim, wheels, and floor.
  2.  **Brightness Filter**: Blocks the moving holes inside the drum. Holes are dark; beads are shiny. We reject any candidate with `avg_brightness < 50`.

## Exporter: MP4 with Baked Overlays

- **Why?** Clients often want a standalone MP4 that looks exactly like the live player (same circle colors and sizes) but can be emailed or embedded without shipping the app.
- **Decision:**
  - Implement `VideoExporter` in `core/exporter.py` that replays the decoded frames, looks up cached detections, applies ROI filtering, and calls `OverlayRenderer` on each frame.
  - Run export work on a `QThread` (`ExportThread`) from `MainWindow`, surfacing a `QProgressDialog` so the UI remains responsive.
  - Keep all rendering logic in `OverlayRenderer` so the exporter cannot diverge visually from the UI.
