# Project FAQ & Decision Log

This document captures key questions asked during development, providing context and reasoning for future contributors.

## Testing & Validation

### Q: Why do we use "Dummy Videos" for testing instead of real files?
**Context**: During the implementation of the CLI Runner tests (`tests/test_cli_runner.py`), the question arose about why we generate synthetic video files on the fly rather than using the real `DSC_3310.MOV`.

**Answer**:
1.  **Speed**: Generating and processing a 10-frame blank video takes milliseconds. Processing a real 1080p clip takes seconds or minutes, which discourages frequent testing.
2.  **Portability**: Real video files are large and often not checked into git. Tests relying on them would fail on CI servers or new developer machines.
3.  **Determinism**: With a synthetic video, we control every pixel. We can mathematically prove "Frame 5 exists" or "Pixel (10,10) is white." With real footage, "accuracy" is subjective and hard to assert programmatically.

### Q: Why is the CLI Runner test relevant if we have unit tests?
**Context**: We already tested the `Loader`, `Processor`, and `Orchestrator` individually. Why test the script that runs them?

**Answer**:
1.  **Integration ("The Glue")**: Unit tests prove parts work in isolation. This test proves they work *together*. It catches issues like passing the wrong arguments from the Loader to the Processor.
2.  **Entry Point Verification**: The `run_detection.py` script is the actual entry point for the application's backend. If it crashes (e.g., due to argument parsing errors), the entire app fails, regardless of how good the core logic is.
3.  **Output Contract**: It verifies that the system actually produces the `detections.jsonl` file on disk, which is the critical hand-off to the UI Player.

### Q: Why did we create `scripts/repro_synthetic.py`?
**Context**: The integration test `test_cli_full_run` failed because it couldn't detect a simple white circle in a synthetic video, even though the vision pipeline works on real footage.

**Answer**:
1.  **Isolation**: The CLI test involves file I/O, argument parsing, and the full orchestrator loop. `repro_synthetic.py` strips all that away to test *just* the `VisionProcessor` against a single numpy array.
2.  **Parameter Tuning**: Synthetic data (perfect white circle on black) is mathematically perfect, which can paradoxically fail in computer vision pipelines tuned for noisy, real-world images (e.g., a bilateral filter might blur a perfect edge differently, or Hough parameters might be too strict).
3.  **Debugging**: It allows us to print internal states (contours found, edges detected) instantly without waiting for a full video run.

## Architecture & Logic

### Q: What is "Playback Logic" and why is it separate from the Video Widget?
**Context**: During Phase 3 (UI Player), we distinguished between the `VideoWidget` (display) and the `PlaybackController` (logic).

**Answer**:
"Playback Logic" is the engine that drives the application time. It coordinates three critical components in real-time:
1.  **The Heartbeat (QTimer)**: A timer firing ~60 times a second (16.6ms) to advance the frame clock.
2.  **Synchronization**: It ensures that when we show **Frame #N** from the video file, we simultaneously fetch and draw **Detections for Frame #N** from the cache. Without this, overlays would drift or lag behind the video.
3.  **State Management**: It handles Play/Pause states, scrubbing (seeking to a specific index), and looping behavior, keeping the UI responsive while heavy decoding happens in the background.

By separating this from the `VideoWidget`, we keep the widget "dumb" (just drawing what it's told) and the controller "smart" (deciding *what* to draw and *when*).

### Q: Why use PyAV instead of OpenCV (`cv2.VideoCapture`)?
**Context**: import av` in `playback.py`: why we aren't using the standard OpenCV video loader.

**Answer**:
1.  **Seeking Accuracy (The "Scrubbing" Problem)**: OpenCV's `set(cv2.CAP_PROP_POS_FRAMES)` is notoriously imprecise. It often lands on the nearest "Keyframe" (which could be 2 seconds away) but reports that it's on the correct frame. This causes the video to "jump" or "stutter" when you drag the timeline. PyAV allows us to seek to a keyframe and then deterministically decode forward to the *exact* frame we need.
2.  **Rotation Metadata**: Videos recorded on phones (like `DSC_3310.MOV`) often have a metadata flag saying "Rotate 90 degrees." OpenCV usually ignores this, giving you a sideways video. PyAV exposes this metadata so we can rotate the frame automatically.
3.  **Performance**: PyAV is a direct Python binding to FFmpeg. It allows us to keep frames in efficient memory buffers and potentially leverage hardware decoding (NVDEC) more transparently than OpenCV's high-level wrapper.

### Q: How does the app identify balls? (High-Level Overview)
**Context**: User asked for an explanation of the overall behavior and detection logic.

**Answer**:
The app uses a **"Scan Once, Play Forever"** workflow:
1.  **Detection (Offline)**: We process the video *once* using a dual-path pipeline:
    *   **Preprocessing**: Bilateral Filter + CLAHE to handle noise and lighting.
    *   **Detection**: Fuses results from **Hough Circles** (good for shapes) and **Contours** (good for edges).
    *   **Logic**: We explicitly handle "hollow rings" (ignoring the inner hole) and filter out bolts using an **ROI Mask**.
    *   **Output**: Results are saved to `detections.jsonl`.
2.  **Playback (Real-time)**: The UI simply reads the JSON file and draws circles. This ensures smooth 60fps playback and instant toggling without re-running the heavy vision math.

### Q: How do Calibration and ROI affect detection?
**Context**: After adding the Calibration Tool and ROI painter, it’s important to understand which parts of the system they influence.

**Answer**:
1.  **Calibration (`px_per_mm`)**:
    - Lives in the config YAML under `calibration.px_per_mm`.
    - Is used **only** in the vision pipeline to convert pixel radii into millimeters for binning (4/6/8/10mm).
    - Changing calibration requires an **offline re-run** of detection (`run_detection.py`) to regenerate `detections.jsonl`.
2.  **ROI Mask (`roi_mask.png`)**:
    - Is used in two places:
        - During detection: the `VisionProcessor` drops any candidate whose center falls in a masked (ignored) region.
        - During export: `VideoExporter` reloads `roi_mask.png` and re-filters cached detections so exported overlays match what the operator expects.
    - Toggling ROI edit mode in the UI does **not** re-run detection; it just updates the mask file for the next detection/export run.

### Q: Why does the Exporter reuse the OverlayRenderer instead of drawing directly with OpenCV?
**Context**: MP4 export could, in theory, draw circles directly with `cv2.circle`, bypassing Qt.

**Answer**:
1.  **Visual Consistency**: The MP4 a client receives must look exactly like what they saw during the live demo (same colors, radii, and line widths). Reusing `OverlayRenderer` guarantees a single source of truth.
2.  **Lower Cognitive Load**: Contributors only need to reason about drawing logic in one place. There is no special “export look.”
3.  **Future-Proofing**: If we later add legends, text labels, or more complex overlays, they will automatically appear in both the UI and exports as long as they go through `OverlayRenderer`.

