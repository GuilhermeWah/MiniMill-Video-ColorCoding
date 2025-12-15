# MillPresenter Project Presentation

---

## Slide 1: Title Slide

# MillPresenter: Automated Visual Inspection System
### Project Overview & Technical Deep Dive

**Presenter:** [Your Name]
**Duration:** 15 Minutes

---

## Slide 2: The Problem

### Manual Inspection is Inefficient
- **Current Process:** Manual visual inspection of beads/circles.
- **Pain Points:**
    - Slow and labor-intensive.
    - Prone to human error and fatigue.
    - Inconsistent results between inspectors.
    - No digital record of inspection data.

---

## Slide 3: The Solution

### MillPresenter: Automated Vision & Playback
- **Goal:** Automate the detection and classification of circular objects in video footage.
- **Key Features:**
    - **Offline Detection:** Process video once, cache results.
    - **Real-time Playback:** Smooth UI with overlay visualization.
    - **Classification:** Categorize by size (4mm, 6mm, 8mm, 10mm).
    - **Tools:** Calibration, ROI masking, and Export.

---

## Slide 4: System Architecture

### Component Data Flow
`FrameLoader` ➜ `ProcessorOrchestrator` ➜ `ResultsCache` ➜ `OverlayRenderer` ➜ `UI/Exporter`

- **Separation of Concerns:**
    - **Detection:** Happens offline, computationally intensive.
    - **Rendering:** Lightweight, reads from cache.
    - **UI:** Never triggers detection, ensuring smooth playback.

---

## Slide 5: The Vision Pipeline (Core)

### Inside `src/mill_presenter/core/processor.py`
1.  **Preprocessing:**
    - `Bilateral Filter`: Reduces noise while preserving edges.
    - `CLAHE`: Contrast Limited Adaptive Histogram Equalization for lighting invariance.
2.  **Detection:**
    - `Hough Circle Transform`: Finds candidate circles.
    - `Contours & Annulus`: Validates shapes and rejects holes.
3.  **Classification:**
    - Maps pixel radius to millimeters using `px_per_mm`.
    - Bins into 4mm, 6mm, 8mm, 10mm classes.

---

## Slide 6: Data Flow & Caching

### Why JSONL?
- **Format:** `exports/detections.jsonl`
- **Design Decision:**
    - **Streaming Friendly:** Can read/write line by line.
    - **Human Readable:** Easy to debug and inspect.
    - **Resumable:** If processing crashes, previous frames are saved.
- **Performance:** Allows the UI to scrub and play without re-running CV algorithms.

---

## Slide 7: User Interface (MillPresenter UI)

### Phase 3: The Player
- **Technology:** Python + PyQt.
- **Key Controls:**
    - **Playback:** Play/Pause, Scrubber, Time Display.
    - **Toggles:** Show/Hide specific classes (e.g., only show 10mm).
    - **Visuals:** Overlays drawn in real-time over the video feed.
- **Design:** "The UI never waits for the Vision."

---

## Slide 8: Calibration & Tools

### Ensuring Accuracy
- **Calibration Tool:**
    - Measures a known reference (Drum Diameter = 200mm).
    - Calculates `px_per_mm` (currently ~6.5).
- **ROI (Region of Interest):**
    - Masks out irrelevant areas to prevent false positives.
    - Interactive circle tool for defining the active area.
- **Configuration:**
    - Settings saved in `configs/*.yaml` for persistence.

---

## Slide 9: Technical Challenges & Solutions

| Challenge | Solution |
| :--- | :--- |
| **Lighting Variations** | Implemented CLAHE for adaptive contrast. |
| **False Positives** | Added Annulus logic to verify "donut" shape of beads. |
| **Performance** | Decoupled detection (offline) from playback (online). |
| **Scale Accuracy** | Implemented Drum Calibration for precise pixel-to-mm conversion. |

---

## Slide 10: Project Status

### Current Progress (Phase 1-4 Complete)
- ✅ **Foundation:** Project structure, venv, docs.
- ✅ **Vision Engine:** Robust pipeline with TDD.
- ✅ **UI Player:** Functional playback with toggles.
- ✅ **Calibration:** Tools for accuracy and ROI.

### Next Steps (Phase 5)
- 🚧 **Validation:** Visual acceptance checklist.
- 🚧 **Performance:** Benchmarking for 60fps on target hardware.
- 🚧 **Packaging:** PyInstaller build for distribution.

---

## Slide 11: Conclusion

### Summary
- **MillPresenter** delivers a robust, automated solution for visual inspection.
- **Architecture** prioritizes performance and maintainability.
- **Status:** Core features are complete; moving to final validation and polish.

### Q&A
- Questions?

---
