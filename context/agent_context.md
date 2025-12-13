# MillPresenter: Complete Agent Context

**Purpose**: Provide complete context for an AI agent to understand and work on this codebase  
**Project**: MillPresenter - Grinding Mill Video Analysis Tool  
**Date**: December 2024

---

## 1. Project Overview

### What This Is
A Python application for **detecting and visualizing grinding beads** in industrial mill videos. Users record video of a rotating drum containing metal beads of different sizes (4mm, 6mm, 8mm, 10mm). The system detects each bead and draws colored circles to classify them.

### Core Philosophy: "Detect Once, Play Forever"
Heavy computer vision processing happens **offline** (CLI), results are cached in JSONL, and the **GUI** only reads cached results for 60 FPS playback. This separation is the architectural foundation.

### Two-Phase Architecture
```
PHASE 1 (Offline): Video → FrameLoader → ProcessorOrchestrator → VisionProcessor → ResultsCache → detections.jsonl
PHASE 2 (Live):    detections.jsonl → ResultsCache → PlaybackController → VideoWidget → User sees overlays
```

---

## 2. Technology Stack

- **Python 3.10+**
- **PyAV 11.0+** - Video decoding (chosen over OpenCV for accurate seeking and rotation metadata)
- **OpenCV 4.9+** - Computer vision algorithms
- **PyQt6 6.6+** - GUI framework
- **NumPy 1.26+** - Array operations
- **PyYAML 6.0+** - Configuration files

---

## 3. Project Structure

```
ColorCodingTest/
├── src/mill_presenter/
│   ├── core/                    # Backend (headless)
│   │   ├── models.py            # Ball, FrameDetections dataclasses
│   │   ├── playback.py          # FrameLoader (PyAV video I/O)
│   │   ├── processor.py         # VisionProcessor (CV pipeline)
│   │   ├── cache.py             # ResultsCache (JSONL storage)
│   │   ├── orchestrator.py      # ProcessorOrchestrator (pipeline coordinator)
│   │   ├── overlay.py           # OverlayRenderer (shared drawing logic)
│   │   └── exporter.py          # VideoExporter (MP4 with overlays)
│   ├── ui/                      # Frontend (PyQt6)
│   │   ├── widgets.py           # VideoWidget (OpenGL display)
│   │   ├── main_window.py       # MainWindow (app shell)
│   │   ├── playback_controller.py
│   │   ├── calibration_controller.py
│   │   ├── drum_calibration_controller.py
│   │   └── roi_controller.py
│   ├── utils/
│   │   └── logging.py
│   └── app.py                   # GUI entry point
├── scripts/
│   ├── run_detection.py         # CLI for offline detection
│   ├── setup.ps1                # Environment setup
│   └── debug_vision.py          # Debugging helper
├── tests/                       # Comprehensive pytest suite (15 files)
├── configs/
│   └── sample.config.yaml       # Configuration template
├── content/                     # Video files, ROI masks
├── exports/                     # Detection results, exported videos
├── docs/
│   ├── design_decisions.md      # Architecture rationale
│   ├── technical_primer.md      # CV algorithm explanations
│   ├── faq.md                   # Q&A log
│   └── testing_criteria.md      # TDD verification
├── PLAN.md                      # Phase roadmap with status
├── README.md                    # Team onboarding
└── pyproject.toml               # Dependencies
```

---

## 4. Core Modules (Detailed)

### 4.1 models.py - Data Structures

```python
@dataclass
class Ball:
    x: int          # Center X (pixels)
    y: int          # Center Y (pixels)
    r_px: float     # Radius (pixels)
    diameter_mm: float  # Calculated diameter
    cls: int        # Size class: 4, 6, 8, or 10
    conf: float     # Confidence score (0.0-1.0)
    
    def to_dict() -> dict
    def from_dict(data: dict) -> Ball

@dataclass
class FrameDetections:
    frame_id: int       # 0-based frame index
    timestamp: float    # Seconds from video start
    balls: List[Ball]   # All detections in this frame
```

### 4.2 playback.py - Video I/O

```python
class FrameLoader:
    # Properties
    fps: float
    total_frames: int
    width: int
    height: int
    duration: float
    
    def __init__(file_path: str)
    def iter_frames(start_frame: int = 0) -> Iterator[Tuple[int, np.ndarray]]
    def seek(frame_index: int) -> None
    def close() -> None
```

**Key Design Decisions**:
- Uses PyAV (not OpenCV) because OpenCV's seeking is imprecise
- Handles rotation metadata from phone recordings
- Generator-based iteration for memory efficiency

### 4.3 processor.py - Vision Pipeline

```python
class VisionProcessor:
    def __init__(config: dict)
    def process_frame(frame_bgr: np.ndarray, roi_mask: Optional[np.ndarray]) -> List[Ball]
```

**CV Pipeline Steps**:
1. **Grayscale conversion**: BGR → Gray
2. **Bilateral filter**: d=9, σ=75 (noise reduction, edge preservation)
3. **CLAHE**: clipLimit=2.0, tileGrid=8×8 (contrast enhancement)
4. **Detection Path A - Hough Circles**: param1=50, param2=20
5. **Detection Path B - Contours**: Canny edges → findContours → circularity filter (>0.65)
6. **ROI filter**: Reject detections outside mask
7. **Brightness filter**: Reject dark centers (<50) to exclude holes
8. **Annulus logic**: Reject small circles inside larger circles (handles hollow rings)
9. **NMS**: Non-maximum suppression to remove duplicates
10. **Classification**: Convert pixels → mm using px_per_mm, assign to 4/6/8/10mm bins

### 4.4 cache.py - Persistence

```python
class ResultsCache:
    def __init__(cache_path: str)  # Loads existing JSONL if present
    def save_frame(detections: FrameDetections) -> None  # Append to file + memory
    def get_frame(frame_id: int) -> Optional[FrameDetections]  # O(1) lookup
    def load_from_disk() -> None
    def clear() -> None
```

**Storage Format**: JSONL (one JSON object per line)
```json
{"frame_id": 0, "timestamp": 0.0, "balls": [{"x": 100, "y": 200, "r_px": 15.5, "diameter_mm": 6.2, "cls": 6, "conf": 0.85}]}
{"frame_id": 1, "timestamp": 0.0166, "balls": [...]}
```

**Why JSONL**: Crash-resistant (complete lines are valid), streamable, human-readable.

### 4.5 orchestrator.py - Pipeline Coordinator

```python
class ProcessorOrchestrator:
    def __init__(loader: FrameLoader, processor: VisionProcessor, cache: ResultsCache)
    def set_roi_mask(mask: np.ndarray) -> None
    def run(progress_callback: Optional[Callable[[float], None]] = None, limit: Optional[int] = None) -> None
    def cancel() -> None
```

**Workflow**:
1. Iterate frames via FrameLoader
2. Process each frame via VisionProcessor
3. Wrap results in FrameDetections
4. Save via ResultsCache
5. Report progress via callback

### 4.6 overlay.py - Rendering

```python
class OverlayRenderer:
    def __init__(config: dict)  # Pre-allocates QPen objects
    def draw(painter: QPainter, detections: FrameDetections, visible_classes: Set[int], scale: float = 1.0) -> None
```

**Critical**: Used by BOTH VideoWidget (UI) AND VideoExporter (MP4) to ensure visual consistency.

### 4.7 exporter.py - MP4 Generation

```python
class VideoExporter:
    def __init__(frame_loader, results_cache, renderer, config)
    def export(output_path: str, visible_classes: Set[int], progress_callback) -> None
```

Renders each frame with overlays baked in, encodes to MP4 using cv2.VideoWriter.

---

## 5. UI Modules

### 5.1 VideoWidget (widgets.py)
- Inherits QOpenGLWidget
- Displays video frames + detection overlays
- Handles zoom/pan (mouse wheel, middle-click drag)
- Emits mouse signals for calibration/ROI tools
- Controls: `set_frame(qimage, detections)`, `set_visible_classes(set)`

### 5.2 PlaybackController (playback_controller.py)
- Manages QTimer for 60fps playback
- Fetches frames from FrameLoader, detections from ResultsCache
- Delivers to VideoWidget
- Controls: `play()`, `pause()`, `seek(frame_index)`
- Signals: `frame_changed(int)`

### 5.3 MainWindow (main_window.py)
- Application shell with all controls
- Buttons: Play, Manual Calibrate, Drum Calibrate, ROI Mask, Export, 4mm/6mm/8mm/10mm toggles
- Slider for timeline scrubbing
- Time display (current/total)
- Mode management (only one tool active at a time)

### 5.4 Calibration Controllers
- **CalibrationController**: 2-point click → enter mm → calculate px_per_mm
- **DrumCalibrationController**: Auto-detect drum rim → adjust → confirm diameter → calculate px_per_mm
- Both update config and save to YAML

### 5.5 ROIController
- Auto-detects drum circle
- Interactive resize (drag rim or arrow keys)
- Saves binary mask as PNG (white=valid, black=ignore)

---

## 6. Configuration (sample.config.yaml)

```yaml
calibration:
  px_per_mm: 4.20           # Pixels per millimeter (set via calibration tools)

vision:
  hough_param1: 50
  hough_param2: 20
  min_dist_px: 15
  min_circularity: 0.65

bins_mm:
  - {label: 4, min: 3.0, max: 4.87}
  - {label: 6, min: 4.87, max: 6.71}
  - {label: 8, min: 6.71, max: 9.16}
  - {label: 10, min: 9.16, max: 12.0}

overlay:
  line_width: 2
  colors:
    4: "#FF0000"   # Red
    6: "#00FF00"   # Green
    8: "#0000FF"   # Blue
    10: "#FFFF00"  # Yellow

paths:
  detections_dir: exports
```

---

## 7. Entry Points

### CLI Detection (scripts/run_detection.py)
```bash
python scripts/run_detection.py \
    --input content/DSC_3310.MOV \
    --output exports/detections.jsonl \
    --config configs/sample.config.yaml \
    --roi content/roi_mask.png
```

### GUI Playback (mill_presenter/app.py)
```bash
python -m mill_presenter.app \
    --video content/DSC_3310.MOV \
    --detections exports/detections.jsonl \
    --config configs/sample.config.yaml
```

---

## 8. Testing Strategy

### Test Files (tests/)
| File | Tests |
|------|-------|
| test_models.py | Ball/FrameDetections serialization |
| test_playback.py | FrameLoader metadata, iteration, seeking |
| test_processor.py | Detection, annulus logic, hole rejection |
| test_cache.py | Write/read cycle, append, clear |
| test_orchestrator.py | Mocked pipeline flow, progress reporting |
| test_overlay.py | Drawing logic, scaling, filtering |
| test_main_window.py | UI instantiation, toggles, slider |
| test_playback_controller.py | Timer, frame delivery, EOS |
| test_calibration_tool.py | Click handling, distance calculation |
| test_roi_tool.py | Circle geometry, mask generation |
| test_exporter.py | Frame iteration, overlay drawing, ROI filtering |
| test_cli_runner.py | Integration: synthetic video end-to-end |
| test_config_saving.py | YAML read/write cycle |
| test_ui_basic.py | Basic UI tests |
| conftest.py | Shared fixtures |

### Running Tests
```bash
pytest                    # Full suite (~2 seconds)
pytest tests/test_processor.py -v  # Single file
```

---

## 9. Development Workflow

1. **Document first**: Update PLAN.md with task description
2. **Write failing test**: Create test under tests/
3. **Implement minimum**: Make test pass
4. **Run pytest**: Verify nothing broke
5. **Log in testing_criteria.md**: Record verification
6. **Capture reasoning in faq.md**: Record design decisions

---

## 10. Current Status (From PLAN.md)

### ✅ Completed (Phases 1-4)
- Project structure and environment
- All core modules (loader, processor, cache, orchestrator, overlay, exporter)
- Full UI with toggles, scrubber, time display
- Calibration tools (manual + drum)
- ROI tool with auto-detect
- MP4 export

### 🚧 In Progress (Phase 5)
- Detection accuracy tuning
- Visual acceptance verification
- 60fps performance benchmarking
- PyInstaller packaging (build.ps1)

---

## 11. Known Code Quality Issues

### Critical (Must Fix)
1. **Bare except** in drum_calibration_controller.py:230 - catches all exceptions
2. **Config state sync** - VisionProcessor reads px_per_mm in two places
3. **Missing resource cleanup** - FrameLoader.close() not called in CLI
4. **Thread safety undocumented** - ResultsCache accessed from multiple threads

### High Priority
5. VideoWidget violates SRP (8 responsibilities)
6. MainWindow is God class (400+ lines)
7. Magic numbers throughout (50, 1.1, 20, etc.)
8. Inconsistent error handling patterns
9. Unused code (_dirty attribute in cache)

### Medium Priority
10. Missing type hints in many methods
11. String-based state machines (should be Enums)
12. Hardcoded file paths
13. Configuration mutation without validation

---

## 12. Key Design Decisions to Preserve

1. **Separation**: Core layer NEVER depends on UI layer
2. **Unidirectional data**: Detection writes → Cache ← Playback reads
3. **Shared rendering**: OverlayRenderer used by both UI and export
4. **Dependency injection**: Modules receive dependencies via constructors
5. **JSONL caching**: Crash-resistant, streamable, human-readable
6. **PyAV over OpenCV**: Accurate seeking, rotation metadata support

---

## 13. Common Tasks

### Adding a new bead size class
1. Add bin definition to `bins_mm` in config
2. Add color to `overlay.colors` in config
3. Add toggle button in `MainWindow.__init__`
4. Test with synthetic video

### Improving detection accuracy
1. Adjust parameters in `processor.py` (hough_param1, hough_param2, min_circularity)
2. Use `scripts/debug_vision.py` to visualize
3. Run `scripts/run_detection.py` and check results
4. Update config with final values

### Adding new calibration method
1. Create new controller in `ui/`
2. Add button and mode handling in MainWindow
3. Ensure mutual exclusion with other modes
4. Update config and save YAML on completion
5. Add test file

---

## 14. Files to Read First

| Priority | File | Why |
|----------|------|-----|
| 1 | PLAN.md | Current status, phase breakdown |
| 2 | docs/design_decisions.md | Architecture rationale |
| 3 | docs/faq.md | Common questions answered |
| 4 | processor.py | Core CV logic |
| 5 | playback_controller.py | Playback mechanism |
| 6 | main_window.py | UI coordination |
| 7 | tests/test_processor.py | Expected behavior |

---

## 15. Quick Reference

### Class → File Mapping
| Class | File |
|-------|------|
| Ball, FrameDetections | core/models.py |
| FrameLoader | core/playback.py |
| VisionProcessor | core/processor.py |
| ResultsCache | core/cache.py |
| ProcessorOrchestrator | core/orchestrator.py |
| OverlayRenderer | core/overlay.py |
| VideoExporter | core/exporter.py |
| VideoWidget | ui/widgets.py |
| PlaybackController | ui/playback_controller.py |
| MainWindow | ui/main_window.py |
| CalibrationController | ui/calibration_controller.py |
| DrumCalibrationController | ui/drum_calibration_controller.py |
| ROIController | ui/roi_controller.py |

### Signal → Slot Connections
| Signal | Connected To |
|--------|--------------|
| PlaybackController.frame_changed | MainWindow._on_frame_changed |
| VideoWidget.clicked | MainWindow._on_video_clicked |
| VideoWidget.mouse_pressed | ROIController.handle_mouse_press |
| VideoWidget.mouse_moved | ROIController.handle_mouse_move |
| play_button.toggled | MainWindow.toggle_playback |
| slider.sliderMoved | MainWindow._on_slider_moved |
| size_buttons.toggled | MainWindow.toggle_class |

---

**End of Context Document**

This document contains everything needed to understand and contribute to the MillPresenter codebase.
