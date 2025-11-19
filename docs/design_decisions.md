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
