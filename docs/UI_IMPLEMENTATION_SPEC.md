# MillPresenter: UI Implementation Specification

**Version:** 2.0
**Context:** Capstone Project - Grinding Mill Video Analysis
**Architecture Pattern:** "Detect Once, Play Forever" (Offline CV + Real-time Playback)
**Target Framework:** Python (PyQt6 / PySide6)

---

## 1. Core Architecture & Philosophy

The application is strictly divided into two phases to ensure responsiveness:
1.  **Offline Phase (Blocking):** Computer Vision pipeline runs on the video. No playback allowed. Results cached to JSON.
2.  **Online Phase (Real-Time):** Video plays at 60 FPS. UI simply renders pre-computed data from RAM. **No detection logic runs during playback.**

**UI Principles:**
* **Video-First:** The video viewport dominates the screen (approx. 70-80%).
* **Immediate Feedback:** Toggles/sliders affect the view *instantly* (no "Apply" buttons).
* **Explicit State:** The user must always know if the app is `IDLE`, `PROCESSING`, or `READY`.

---

## 2. Layout Structure

The application window is arranged into five distinct regions:

```
┌─────────────────────────────────────────────────────────────────────┐
│ [A] TOP BAR: Video: file.mp4 | State: READY | Detection: 100%      │
├────────────┬────────────────────────────────────────┬───────────────┤
│            │                                        │ Overlay|Proc| │
│ [E] STATS  │                                        │ ─────────────│
│            │                                        │ Master Toggle│
│ Total: 342 │                                        │ Opacity ─●── │
│            │         [B] VIDEO VIEWPORT             │ Confidence   │
│ 4mm: 85    │                                        │ ────●─────── │
│ 6mm: 120   │                                        │               │
│ 8mm: 95    │                                        │ [✓] 4mm Blue │
│ 10mm: 42   │                                        │ [✓] 6mm Green│
│            │                                        │ [✓] 8mm Orng │
│ [Histogram]│                                        │ [✓] 10mm Red │
│            │                                        │               │
│ [Avg Graph]│                                        │ [C] CONTROLS │
├────────────┴────────────────────────────────────────┴───────────────┤
│ [D] BOTTOM BAR: |◀ ◀ ▶ ▶ ▶|  ══════════●══════════  15:32/45:00    │
└─────────────────────────────────────────────────────────────────────┘
```

1.  **[A] Top Bar:** Spans full width. Status indicator and file info.
2.  **[B] Video Viewport:** Central area (~60% width). Video + overlays.
3.  **[C] Right Panel:** Tabbed controls (Overlay, Process, Calibrate, Prefs).
4.  **[D] Bottom Bar:** Timeline scrubber and transport controls.
5.  **[E] Left Stats Panel:** Live statistics and visualizations.

---

## 3. Component Specifications

### [A] Top Bar (Status & Global)
**Role:** High-level state and file management.

* **Left:** `File` Menu (Open Video, Load Cache, Exit).
* **Center:** **Status Indicator** (Text + Colored Icon).
    * ⚪ `IDLE`: No video loaded.
    * 🟡 `PROCESSING`: CV pipeline running (shows % progress).
    * 🟢 `READY`: Detections loaded, ready for playback.
    * 🔴 `ERROR`: Processing failed.
* **Right:** `Help` / `About` button.

### [B] Video Viewport (Central Canvas)
**Role:** High-performance rendering of video frames + overlay graphics.

* **Technology:** `QOpenGLWidget` (for hardware-accelerated rendering).
* **Interaction:**
    * **Mouse Wheel:** Zoom In/Out.
    * **Left Drag:** Pan (when zoomed).
    * **Double Click:** Reset view to fit.
* **Overlays:** Draws circles based on cached data. **Must** check the "Visibility" state of each size class before drawing.

### [C] Right Panel (Tabbed Control Center)
**Role:** The primary interface for analyzing data. Divided into functional tabs.

#### **Tab 1: Overlay Controls (Default)**
* **Master Toggle:** `Show Overlays` (Switch).
* **Opacity:** Slider (0-100%).
* **Confidence Filter:** Slider (0.0 - 1.0). Detections with `conf < value` are hidden immediately.
* **Size Class Toggles:** (Checkboxes with Color Swatches)
    * [ ] **4mm** ( [same  color as the one used in the overlays ] )
    * [ ] **6mm** ( [same  color as the one used in the overlays ] )
    * [ ] **8mm** ( [same  color as the one used in the overlays ] e)
    * [ ] **10mm** ( [same  color as the one used in the overlays ] )
* **Visual Options:**
    * [ ] Show Size Labels (e.g., "6mm" text on bead).
    * [ ] Show Confidence Labels.

#### **Tab 2: Processing**
* **Action Button:**
    * State `READY/IDLE`: "Run Detection" (Starts worker thread).
    * State `PROCESSING`: "Cancel" (Stops worker thread).
* **Progress Bar:** 0-100% (Visible only during processing).
* **Log Output:** Small text area showing current step (e.g., *"Detecting drum...", "Processing frame 45/900"*).

#### **Tab 3: Calibration**
* **Mode Selector:** Radio buttons [ Auto | Manual ].
* **Value Input:** `px_per_mm` (Float field).
* **Drum Preview:** Toggle `Show ROI`. Draws the detected drum boundary (red circle) to verify the CV pipeline is looking in the right place.
* **Recalculate:** Button to re-bin all cached beads if `px_per_mm` is changed manually.

#### **Tab 4: Export & Stats**
* **Live Stats:**
    * Total Bead Count (Current Frame).
    * Breakdown: "4mm: 12 | 6mm: 45..."
* **Export Actions:**
    * <button>Export CSV</button>
    * <button>Export JSON</button>
    * <button>Save Current Frame (PNG)</button>

### [E] Left Stats Panel (Live Metrics)
**Role:** Display real-time detection statistics and visualizations.

* **Total Bead Count:** Large number display (e.g., "342").
* **Count by Size Class:**
    *  [same  color as the one used in the overlays ] 4mm: 85
    *   [same  color as the one used in the overlays ]  6mm: 120
    *    [same  color as the one used in the overlays ] 8mm: 95
    *    [same  color as the one used in the overlays ] 10mm: 42
* **Confidence Distribution:** Small histogram showing distribution of confidence values.
* **Running Average:** Line graph showing count stability over recent frames (e.g., last 30 frames).
* **Tab Toggle:** "Stats | Info" to switch between metrics and video metadata.

### [D] Bottom Bar (Timeline)
**Role:** Navigation and temporal control.

* **Scrubber:** Full-width slider representing video duration.
* **Transport Controls:**
    * `⏮` (Jump to Start)
    * `⏪` (Step -10 Frames)
    * `◀` (Step -1 Frame)
    * `▶ / ⏸` (Play/Pause Toggle)
    * `▶` (Step +1 Frame)
    * `⏩` (Step +10 Frames)
* **Time Label:** `Frame: 154 / 3000` | `00:05.12`.
* **Speed Control:** Slider or Dropdown (0.25x, 0.5x, 1.0x, 2.0x).
* **Loop:** Toggle button `🔁`.

---

## 4. Interaction Logic & Data Flow

### 4.1. The "Run Detection" Workflow
1.  **User** clicks "Run Detection".
2.  **App** locks Playback controls (sets `enabled=False`).
3.  **App** spawns a **Background Thread** (to keep UI responsive).
4.  **Thread** runs CV pipeline frame-by-frame.
5.  **Thread** emits signal `progress(int)` -> updates Progress Bar.
6.  **Completion:** Thread saves `detections.json`.
7.  **App** loads JSON into RAM, unlocks Playback, sets state to `READY`.

### 4.2. The Playback Loop (60 FPS)
* **Timer** fires every ~16ms.
* **App** advances frame index.
* **App** retrieves image for Frame `N` from Video Decoder.
* **App** retrieves detection list for Frame `N` from RAM Cache.
* **App** paints Image + Detections to Viewport.

### 4.3. Calibration Change
1.  **User** changes `px_per_mm` in Tab 3.
2.  **User** clicks "Recalculate".
3.  **App** iterates through *all* cached detections in RAM.
4.  **App** updates `diameter_mm` and `class_label` for every bead.
5.  **Viewport** refreshes immediately to show new colors/sizes.
6.  *Note: This does NOT re-run image processing, only re-classification.*

---

## 5. visual_config.py (Theme Definition)

Use these constants to ensure consistent styling across the UI.

```python
# Color Palette (Dark Theme)
COLORS = {
    'background': '#2b2b2b',
    'panel_bg':   '#3c3f41',
    'text':       '#ffffff',
    'accent':     '#4a90e2',  # Selection/Active
    'success':    '#2ecc71',  # Ready State
    'warning':    '#f1c40f',  # Processing State
    'error':      '#e74c3c'   # Error State
}

# Bead Class Colors (BGR for OpenCV, Hex for UI)
CLASS_COLORS = {
    '4mm':  (255, 0, 0),    # Blue
    '6mm':  (0, 255, 0),    # Green
    '8mm':  (0, 165, 255),  # Orange
    '10mm': (0, 0, 255)     # Red
}

# Dimensions
LAYOUT = {
    'left_panel_width': 180,
    'right_panel_width': 280,
    'bottom_bar_height': 60,
    'top_bar_height': 30,
    'circle_thickness_default': 2
}