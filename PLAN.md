# MillPresenter Implementation Plan & Status

## Phase 1: Foundation & Setup ✅
- [x] **Project Structure**: Create folders (`core`, `ui`, `configs`, `scripts`).
- [x] **Environment**: `setup.ps1` for venv and dependencies.
- [x] **Documentation**: `design_decisions.md` and `technical_primer.md`.
- [x] **AI Instructions**: `.github/copilot-instructions.md` updated.
- [x] **Core: Playback**: `FrameLoader` with PyAV and rotation support (`core/playback.py`).
  - *Verified by*: `tests/test_playback.py` (Metadata, Iteration, Seeking)

## Phase 2: The Vision Engine ✅
- [x] **Data Models**: Define `Ball` and `FrameDetections` dataclasses (`core/models.py`).
  - *Verified by*: `tests/test_models.py` (Serialization integrity)
- [x] **Vision Pipeline**: Implement `Processor` with Hough + Contours + Annulus logic (`core/processor.py`).
  - *Verified by*: `tests/test_processor.py` (Detection, Annulus Logic/Hole Rejection)
- [x] **Caching**: Implement JSONL writer/reader (`core/cache.py`).
  - *Verified by*: `tests/test_cache.py` (Write/Read cycle, Append, Clear)
- [x] **Orchestrator**: Create the loop that processes video -> results (`core/orchestrator.py`).
  - *Verified by*: `tests/test_orchestrator.py` (Mocked processor/cache interaction, progress reporting)
- [x] **CLI Runner**: A script to run detection on a video file without UI (for testing).
  - *Verified by*: `tests/test_cli_runner.py` (Help text + synthetic end-to-end run)

## Phase 3: The UI Player (Current Focus) 🚧
- [x] **Overlay Renderer**: The shared drawing logic (`core/overlay.py`).
  - *Verified by*: `tests/test_overlay.py` (Drawing logic, Scaling, Filtering)
- [x] **Main Window**: PyQt window with video widget (`ui/main_window.py`).
  - *Verified by*: `tests/test_main_window.py` (Instantiation, Layout)
- [x] **Playback Logic**: Timer-based frame updates using `FrameLoader` + `ResultsCache`.
  - *Verified by*: `tests/test_playback_controller.py` (Timer start/stop, frame delivery, EOS handling)
- [x] **Toggles**: Buttons to switch 4/6/8/10mm classes on/off.
  - *Verified by*: `tests/test_main_window.py` (Toggle muting/unmuting visible classes)
- [x] **Scrubber**: Slider to seek through the video.
  - *Verified by*: `tests/test_playback_controller.py` (Seek logic) and `tests/test_main_window.py` (Slider connection)
- [x] **Time Display**: Show current/total time on the playback bar.
  - *Verified by*: Manual verification in UI.

## Phase 4: Calibration & Polish ✅
- [x] **Calibration Tool**: UI to measure the blue ring and set `px_per_mm`.
  - *Verified by*: `tests/test_calibration_tool.py` (Click handling, Distance calc)
- [x] **Config Persistence**: Save calibration/settings to YAML.
  - *Verified by*: `tests/test_config_saving.py` (Read/Write cycle)
- [x] **ROI Tool**: Interactive Circle Tool with Auto-Detect.
  - *Verified by*: `tests/test_roi_tool.py` (Circle geometry, Mask generation)
- [x] **Exporter**: Render video to MP4 with overlays.
  - *Verified by*: `tests/test_exporter.py` (Frame iteration, Overlay drawing, ROI filtering)
- [ ] **Packaging**: `build.ps1` with PyInstaller.

## Phase 5: Validation & Refinement 🚧
- [x] **Detection Tuning**: Improve accuracy for missing balls and false positives.
  - *Verified by*: Manual verification with `scripts/run_detection.py` and `roi_mask.png` generation.
- [ ] **Visual Checklist**: Verify overlays against the "Visual Acceptance Checklist".
- [ ] **Performance Bench**: Ensure 60fps playback on target hardware.
