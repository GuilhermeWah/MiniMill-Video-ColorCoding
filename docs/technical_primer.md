# MillPresenter Technical Primer & Contributor Guide

 This document is designed to get you up to speed with the specific technical challenges we face and the computer vision concepts we use to solve them.

## 1. The Core Challenge: "Presentation-First"
This is not just a video player, and it is not just a research script. It is a **presentation tool**.
*   **The Goal:** A presenter stands in front of a client, plays a 60fps video of a grinding mill, and clicks buttons to toggle overlays ("Show me only the 4mm beads").
*   **The Constraint:** The video **must not stutter**. The toggles must be **instant**.
*   **The Solution:** We do not detect beads while the video plays. We detect them **once** (offline), save them to a file, and then just "draw" them during playback.

## 2. Computer Vision Concepts (The "How")
We use classic Computer Vision (OpenCV), not Deep Learning (AI), because it is faster to tune for our specific geometry and requires no training data. Here are the key algorithms we use:

### A. Bilateral Filter (Preprocessing)
*   **What is it?** A smart blur. Unlike a standard blur that makes everything fuzzy, a Bilateral Filter smooths out "flat" areas but **stops** when it hits a sharp edge.
*   **Why we use it:** Our beads are metallic and have bright white **specular highlights** (glare). Standard edge detectors see these glare spots as "edges," confusing the circle detector. Bilateral filtering smooths the glare into the bead's body while keeping the outer rim of the bead crisp.

### B. CLAHE (Contrast Limited Adaptive Histogram Equalization)
*   **What is it?** A smart contrast booster. Instead of brightening the whole image equally, it breaks the image into a grid and boosts contrast in each square individually.
*   **Why we use it:** The inside of the mill is dark, but the beads are shiny. CLAHE allows us to see the faint outlines of beads in the shadowed corners without "blowing out" (blinding) the camera on the shiny beads in the center.

### C. Hough Circle Transform (The "Pile" Detector)
*   **What is it?** A voting algorithm. Every edge pixel in the image "votes" for where it thinks a circle center might be. If enough pixels vote for the same spot, the algorithm says "There is a circle here."
*   **Why we use it:** It is messy but robust. In the **dense pile** of beads at the bottom of the mill, beads are overlapping and partially hidden. Hough is excellent at finding these "implied" circles even if the edge is broken or partially covered.

### D. Canny Edges + Contours (The "Flyer" Detector)
*   **What is it?** It finds sharp lines (gradients) in the image and traces them into closed shapes (contours). We then measure how "circular" the shape is.
*   **Why we use it:** It is precise. For the **flying beads** that are isolated against the dark background, this method gives us a very accurate fit. We combine this with Hough to get the best of both worlds.
*   **Tuning:** The acceptable circularity threshold is configurable via `vision.min_circularity` (default `0.75`). Tighten it for real footage to keep overlays trustworthy; loosen it for synthetic fixtures in CI that might appear "too perfect" after encoding.

### E. Annulus (Ring) Logic
*   **The Problem:** Our beads are **hollow**. A standard circle detector sees two circles: the outer rim (e.g., 10mm) and the inner hole (e.g., 4mm).
*   **The Risk:** The system might think the 10mm bead is actually two beads: one big, one small.
*   **The Solution:** We use "Annulus Logic." Before accepting a detection, we check: *Is this small circle perfectly centered inside a larger circle?* If yes, it is a **hole**, not a bead. We ignore it and only keep the outer circle.

## 3. Architecture for Contributors
The codebase is split into two distinct worlds that barely talk to each other:

1.  **Offline Detection (Scan Once)**
    - **`core/playback.py :: FrameLoader`** – Thin wrapper around PyAV. Responsible for:
        - Opening the source video, honoring rotation metadata.
        - Iterating frames with accurate seeking by frame index.
    - **`core/processor.py :: VisionProcessor`** – The vision engine. Responsible for:
        - Running the Bilateral → CLAHE → Hough + Contours + Annulus pipeline.
        - Converting radii from pixels to millimeters using `calibration.px_per_mm`.
        - Assigning beads to 4/6/8/10 mm bins from `bins_mm`.
    - **`core/cache.py :: ResultsCache`** – Detection storage. Responsible for:
        - Writing one `FrameDetections` JSON object per line to `detections.jsonl`.
        - Loading all detections into an in-memory dictionary keyed by `frame_id`.
    - **`core/orchestrator.py :: ProcessorOrchestrator`** – The glue. Responsible for:
        - Pulling frames from `FrameLoader`.
        - Running them through `VisionProcessor`.
        - Saving results via `ResultsCache.save_frame`.
    - **`scripts/run_detection.py`** – CLI entry point used in CI and for manual runs.
        - Parses `--input`, `--output`, `--config`, and optional `--roi`.
        - Wires together `FrameLoader`, `VisionProcessor`, `ResultsCache`, and `ProcessorOrchestrator`.

2.  **Live Player (Play Forever)**
    - **`ui/widgets.py :: VideoWidget`** – OpenGL-backed video surface. Responsible for:
        - Drawing raw frames and overlay circles using a shared `OverlayRenderer`.
        - Mapping mouse clicks/drags into **image-space** coordinates so tools (calibration/ROI) never have to care about widget size.
        - Emitting interaction signals: `clicked`, `mouse_pressed`, `mouse_moved`, `mouse_released`.
    - **`ui/playback_controller.py :: PlaybackController`** – Playback brain. Responsible for:
        - Driving a `QTimer` at ~60Hz to keep video + detections in lock-step.
        - Using `FrameLoader.iter_frames()` for decode and `ResultsCache.get_frame()` for cached detections.
        - Seeking by frame index when the slider moves.
    - **`core/overlay.py :: OverlayRenderer`** – Shared drawing logic. Responsible for:
        - Turning `FrameDetections` + visible class set `{4,6,8,10}` into QPainter circles.
        - Pre-allocating colored pens based on `overlay.colors` in the YAML config.
        - Being re-used by both the live UI and the MP4 exporter for pixel-perfect consistency.
    - **`ui/calibration_controller.py :: CalibrationController`** – Calibration tool. Responsible for:
        - Managing a 2-click workflow on `VideoWidget` to define a known physical distance.
        - Computing `px_per_mm` and storing it in `config['calibration']['px_per_mm']`.
        - Updating the overlayed calibration line and points.
    - **`ui/roi_controller.py :: ROIController`** – ROI painter. Responsible for:
        - Converting mouse drags into strokes on an ARGB `QImage` the same size as the frame.
        - Encoding **ignored** regions as semi-transparent red in the UI and turning that into a grayscale `roi_mask.png` for the vision pipeline.
        - Providing `is_point_valid(x, y)` for tests and future tools.
    - **`ui/main_window.py :: MainWindow`** – Presentation shell. Responsible for:
        - Wiring up the `VideoWidget`, control buttons (Play/Pause, Toggles, Calibrate, ROI Mask, Export), and slider.
        - Hosting the status bar instructions for calibration/ROI modes.
        - Managing mutual exclusion between interactive modes (cannot edit ROI and calibrate at the same time).
        - Saving updated config YAML when calibration changes are applied.
    - **`core/exporter.py :: VideoExporter`** – Offline MP4 renderer. Responsible for:
        - Iterating frames via `FrameLoader` and looking up detections from `ResultsCache`.
        - Optionally loading and applying `roi_mask.png` so exported overlays respect ignore regions.
        - Reusing `OverlayRenderer` on a `QImage` view of each frame, then writing to an MP4 via `cv2.VideoWriter`.
    - **`ui/main_window.py :: ExportThread`** – Background export helper.
        - Runs `VideoExporter.export()` on a `QThread`.
        - Reports progress back to the UI so a `QProgressDialog` can keep the user informed.

### Scan Once → Play Forever: End-to-End Flow
1. **Detection Run** (before the presentation):
    1. `run_detection.py` loads the YAML config (bins, thresholds, calibration) and optional `roi_mask.png`.
    2. `FrameLoader` decodes frames in order, applying rotation.
    3. `VisionProcessor.process_frame()` returns a list of `Ball` objects per frame, honoring the ROI mask.
    4. `ResultsCache.save_frame()` appends each `FrameDetections` to `detections.jsonl` and keeps it in memory.

2. **Live Playback** (during the presentation):
    1. `app.py` constructs a `FrameLoader`, `ResultsCache` (loading `detections.jsonl`), and `MainWindow`.
    2. `PlaybackController` drives decoding and detection lookup, pushing `(QImage, FrameDetections)` into `VideoWidget`.
    3. `OverlayRenderer` draws circles only for the classes currently enabled by the 4/6/8/10 buttons.
    4. **No detection code runs** here; toggling classes is just showing/hiding precomputed circles.

3. **Export** (optional, offline):
    1. The user clicks **Export MP4** in `MainWindow`.
    2. `VideoExporter` replays the video offline, reusing `OverlayRenderer` and honoring `roi_mask.png`.
    3. Output is a flat MP4 with baked-in circles, ideal for sending to clients.

## 4. Key Files to Read
*   `docs/design_decisions.md`: The "Why" behind our architecture.
*   `.github/copilot-instructions.md`: The strict rules for AI agents (and humans) working on this code.
*   `configs/sample.config.yaml`: Where we tune the sensitivity of the algorithms (Hough/Contour thresholds, bins) and store calibration.
*   `scripts/run_detection.py`: Headless entry point that glues FrameLoader, Processor, Orchestrator, and ResultsCache together; used by automated tests and CLI workflows.
*   `scripts/test_vision.py`: Developer-only playground for inspecting detections on a single frame and dumping a debug JPEG.
*   `scripts/create_roi_mask.py`: Helper script for quickly sketching a static ROI mask before the in-UI ROI tool existed (kept for reference/regression).

## 5. Changelog & Decision Log (For Contributors)
*This section tracks major architectural shifts and the reasoning behind them, specifically for us (Gui, Zach, Daniel)

### [Initial Setup] - 2025-11-19
*   **Decision:** Split project into `Processor` (Offline) and `Player` (Live).
    *   **Why:** We cannot guarantee 60fps playback if we run OpenCV detection on every frame. Pre-computing is the only way to ensure smooth presentation on mid-range laptops.
*   **Decision:** Use `PyAV` instead of `cv2.VideoCapture` for playback.
    *   **Why:** OpenCV's video decoder is notoriously bad at seeking (scrubbing) and doesn't expose hardware acceleration (NVDEC) reliably on Windows. PyAV gives us fine-grained control over the decode loop.
*   **Decision:** Support `.MOV` rotation metadata.
    *   **Why:** Raw footage from iPhones/Nikons often comes in "sideways" with a metadata flag. If we ignore this, our ROI masks will be rotated 90 degrees relative to the video.

