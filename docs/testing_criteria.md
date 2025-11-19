# Testing Criteria & Validation Plan

This document outlines the automated tests implemented to verify the core functionality of MillPresenter. These tests serve as the "Gatekeepers" for each milestone.

## Workflow: Test-Driven Development (TDD)
We follow a strict TDD cycle to ensure accuracy and stability:
1.  **Define the Goal**: Identify the feature or edge case in `PLAN.md`.
2.  **Write the Test**: Create a test case in `tests/` that defines the expected behavior (inputs -> outputs).
3.  **Fail First**: Run the test to confirm it fails (or doesn't exist yet).
4.  **Implement**: Write the minimal code in `src/` to make the test pass.
5.  **Verify**: Run `pytest` to confirm success.
6.  **Document**: Update `PLAN.md` with the verification link and this document with the criteria.

To run all tests, execute:
```powershell
pytest tests/
```

## 1. Data Integrity (Milestone 1)
**File:** `tests/test_models.py`

### `test_ball_serialization`
*   **Goal**: Ensure the `Ball` object (representing a single bead) can be converted to a dictionary correctly for JSON storage.
*   **Success Criteria**:
    *   Input: A `Ball` object with specific values (x=100, cls=10, etc.).
    *   Output: A Python dictionary.
    *   **Pass**: All dictionary keys match the input object's attributes exactly.
*   **How to Ensure Pass**:
    *   Ensure `Ball` dataclass has a `.to_dict()` method (or uses `asdict`).
    *   Ensure all fields defined in the dataclass are present in the output.

### `test_frame_detections_serialization`
*   **Goal**: Ensure the `FrameDetections` object (representing a whole frame) serializes correctly, including the list of `Ball` objects inside it.
*   **Success Criteria**:
    *   Input: A `FrameDetections` object containing multiple `Ball` objects.
    *   **Pass**: The resulting dictionary contains the correct frame metadata and a list of dictionaries for the balls.
*   **How to Ensure Pass**:
    *   Ensure `FrameDetections.to_dict()` recursively calls `.to_dict()` on its list of balls.

---

## 2. Video Pipeline (Milestone 2)
**File:** `tests/test_playback.py`

### `test_frameloader_metadata`
*   **Goal**: Verify that `FrameLoader` can open a video file and read its properties.
*   **Success Criteria**:
    *   Input: A generated synthetic video file.
    *   **Pass**: `loader.width`, `loader.height`, and `loader.stream` are populated with valid values (not 0 or None).
*   **How to Ensure Pass**:
    *   Ensure `av.open()` is called successfully.
    *   Ensure `self.stream` is assigned to the first video stream.

### `test_frameloader_iteration`
*   **Goal**: Verify that we can read every frame in the video sequentially.
*   **Success Criteria**:
    *   Input: A 10-frame synthetic video.
    *   **Pass**: The iterator yields exactly 10 frames, and each frame is a valid numpy array of the correct shape.
*   **How to Ensure Pass**:
    *   Ensure the loop `for frame in container.decode(stream)` completes without error.
    *   Ensure frames are converted to numpy arrays (e.g., `frame.to_ndarray(format='bgr24')`).

### `test_frameloader_seek`
*   **Goal**: Verify that we can jump to a specific frame index (crucial for the UI player's scrubbing).
*   **Success Criteria**:
    *   Input: A 10-frame video.
    *   Action: Request iteration starting from frame 5.
    *   **Pass**: The first frame yielded has the index 5.
*   **How to Ensure Pass**:
    *   Ensure `container.seek()` is used correctly (calculating timestamp based on time_base).
    *   Ensure the logic handles "pre-roll" (decoding frames before the target keyframe until the exact target is reached).

---

## 3. Vision Logic (Milestone 3)
**File:** `tests/test_processor.py`

### `test_processor_detection`
*   **Goal**: Verify that the computer vision pipeline can detect simple, perfect geometric shapes.
*   **Success Criteria**:
    *   Input: A synthetic black image with white circles drawn at known locations (simulating 10mm and 4mm beads).
    *   **Pass**:
        *   The processor returns a list of `Ball` objects.
        *   At least one ball is classified as `10mm` near the first location.
        *   At least one ball is classified as `4mm` near the second location.
*   **How to Ensure Pass**:
    *   Ensure `cv2.HoughCircles` or `cv2.findContours` parameters are tuned to detect clean circles.
    *   Ensure `px_per_mm` calibration is applied correctly to convert radius to mm.

### `test_processor_annulus_logic` (CRITICAL)
*   **Goal**: Verify the "Hollow Ring" safety logic. Real beads are rings; we must detect the *outer* ring and ignore the *inner* hole.
*   **Success Criteria**:
    *   Input: A synthetic image of a white ring (10mm outer diameter) with a black center (4mm hole).
    *   **Pass**:
        *   The processor detects **exactly one** bead.
        *   That bead is classified as **10mm**.
        *   **Fail Condition**: If the processor detects a 10mm bead AND a 4mm bead (the hole), the test fails. This prevents the "Ghost Bead" bug.
*   **How to Ensure Pass**:
    *   Implement logic to check if a small circle is contained within a larger circle.
    *   If `dist(center1, center2) < radius1` and `radius2 < radius1`, discard the smaller one (the hole).

---

## 4. Orchestration (Milestone 2)
**File:** `tests/test_orchestrator.py`

### `test_orchestrator_full_run`
*   **Goal**: Verify that the orchestrator coordinates the entire pipeline (Load -> Process -> Save) for every frame.
*   **Success Criteria**:
    *   Input: A mocked loader with 10 frames.
    *   **Pass**: The processor is called 10 times, and the cache saves 10 results.
*   **How to Ensure Pass**:
    *   Iterate through `loader.iter_frames()`.
    *   Call `processor.process_frame()` for each.
    *   Call `cache.save_frame()` with the result.

### `test_orchestrator_roi_mask`
*   **Goal**: Ensure the user-defined ROI mask is actually passed to the vision processor.
*   **Success Criteria**:
    *   Input: An orchestrator with a set ROI mask.
    *   **Pass**: The `processor.process_frame` method receives the mask as an argument.
*   **Why**: If this fails, we might process the entire frame (including clutter) even if the user drew a mask, leading to false positives.

### `test_orchestrator_cancellation`
*   **Goal**: Verify that the long-running detection process can be stopped by the user.
*   **Success Criteria**:
    *   Input: A run that is cancelled after 30% progress.
    *   **Pass**: The loop terminates early (processing < total frames).
*   **Why**: Users shouldn't have to force-quit the app if they start a detection by mistake.

---

## 5. CLI & Integration (Milestone 2)
**File:** `tests/test_cli_runner.py`

### `test_cli_help`
*   **Goal**: Verify the CLI script exposes a help message.
*   **Success Criteria**:
    *   Input: `python scripts/run_detection.py --help`
    *   **Pass**: Exit code 0, stdout contains "usage:".

### `test_cli_full_run`
*   **Goal**: Verify the entire pipeline (Loader -> Processor -> Cache) works together when invoked via CLI.
*   **Success Criteria**:
    *   Input: A synthetic video, a valid config file, and an output path.
    *   **Pass**:
        *   Exit code 0.
        *   Output file `detections.jsonl` is created.
        *   Output file contains valid JSON lines for each frame.
        *   Detections are present (balls found).
*   **How to Ensure Pass**:
    *   Ensure `scripts/run_detection.py` correctly instantiates `FrameLoader`, `VisionProcessor`, `ResultsCache`, and `ProcessorOrchestrator`.
    *   Ensure arguments are parsed and passed to these components.
    *   Ensure the script waits for `orchestrator.run()` to complete.
    *   Use a calibration override (`px_per_mm = 15.0`) and a relaxed contour threshold (`vision.min_circularity = 0.65`) for the synthetic MP4 the test generates so that the detected circle classifies into the 4 mm bin.
