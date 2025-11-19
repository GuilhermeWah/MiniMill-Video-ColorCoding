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
