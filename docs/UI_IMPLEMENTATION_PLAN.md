# UI Implementation Plan

**Project:** MillPresenter  
**Phase:** Visualization / UI (Phase 9 per MAIN.md)  
**STEP Reference:** Part of STEP_09 (Visualization & Playback Features)  
**Start Date:** 2025-12-12  
**Framework:** PySide6 (Qt6 for Python)  
**Governed by:** rules/MAIN.md, rules/CURRENT_STEP_RULES.md

---

## Document Authority

This document serves as the detailed specification for UI implementation within the MillPresenter project. It is subordinate to:
1. `rules/MAIN.md` (highest authority)
2. `rules/CURRENT_STEP_RULES.md`
3. `CURRENT_STEP.md`

All UI development must comply with the Non-Negotiable System Invariants defined in MAIN.md, specifically:
- **Offline detection → cached results → visualization reads cache only**
- Playback reads cache ONLY (no real-time CV)
- Playback must remain real-time at 30-60 FPS

---

## Executive Summary

This plan breaks down UI implementation into **6 sub-phases**, each deliverable and testable independently. The design is faithful to the provided mockup and follows established HCI principles.

---

## Alignment with Pipeline Phases

| Pipeline Phase (MAIN.md) | UI Responsibility |
|--------------------------|-------------------|
| 1-8: Detection Pipeline | N/A (CV pipeline work) |
| **9: Visualization & Playback** | **This document** — Full UI implementation |
| 10: Export & Delivery | Export dialogs, video export |

The UI is explicitly part of **Phase 9** in the mandatory development order.

---

## Functional Requirements (FR)

### FR1: Video Playback
| ID | Requirement |
|----|-------------|
| FR1.1 | System shall display video frames in the central viewport |
| FR1.2 | System shall support play/pause toggle |
| FR1.3 | System shall support frame stepping (±1, ±10 frames) |
| FR1.4 | System shall support seeking via timeline scrubber |
| FR1.5 | System shall display current time in MM:SS format |
| FR1.6 | System shall support playback speed adjustment (0.25x-2.0x) |
| FR1.7 | System shall support loop playback toggle |
| FR1.8 | System shall maintain ≥30 FPS on 1080p video |
| FR1.9 | System shall support full-screen mode (F11 or button) |

### FR2: Overlay Visualization
| ID | Requirement |
|----|-------------|
| FR2.1 | System shall render colored circles on detected beads |
| FR2.2 | System shall use distinct colors per size class (Blue=4mm, Green=6mm, Orange=8mm, Red=10mm) |
| FR2.3 | System shall support master show/hide toggle for all overlays |
| FR2.4 | System shall support adjustable overlay opacity (0-100%) |
| FR2.5 | System shall support per-class visibility toggles |
| FR2.6 | System shall filter overlays by confidence threshold (0.0-1.0) |
| FR2.7 | Overlay changes shall update in real-time (<50ms) |
| FR2.8 | System shall display tooltips on hover over detections (class, confidence, size) |

### FR3: Statistics Display
| ID | Requirement |
|----|-------------|
| FR3.1 | System shall display total visible bead count |
| FR3.2 | System shall display per-class breakdown with colored indicators |
| FR3.3 | System shall display confidence distribution histogram |
| FR3.4 | System shall display running average graph (30-frame window) |
| FR3.5 | Statistics shall update on each frame change |

### FR4: Detection Processing
| ID | Requirement |
|----|-------------|
| FR4.1 | System shall allow user to trigger detection pipeline |
| FR4.2 | System shall display progress during processing |
| FR4.3 | System shall allow user to cancel processing |
| FR4.4 | System shall run detection in background thread (UI responsive) |
| FR4.5 | System shall cache detection results for playback |

### FR5: Calibration
| ID | Requirement |
|----|-------------|
| FR5.1 | System shall support auto-calibration mode |
| FR5.2 | System shall support manual px_per_mm entry |
| FR5.3 | System shall recalculate classifications on calibration change |
| FR5.4 | System shall display ROI visualization (optional toggle) |

### FR6: Parameter Fine-Tuning
| ID | Requirement |
|----|-------------|
| FR6.1 | System shall allow user to adjust detection parameters |
| FR6.2 | System shall provide real-time preview mode for instant feedback |
| FR6.3 | System shall provide offline mode for batch parameter application |
| FR6.4 | System shall allow toggling between real-time and offline modes |
| FR6.5 | System shall show "unsaved changes" indicator when parameters differ from cached |
| FR6.6 | System shall allow saving tuned parameters as presets |
| FR6.7 | System shall allow loading parameter presets |

### FR7: File Operations
| ID | Requirement |
|----|-------------|
| FR7.1 | System shall open video files (*.mp4, *.mov, *.avi) |
| FR7.2 | System shall auto-detect matching cache files |
| FR7.3 | System shall export detections as JSON |
| FR7.4 | System shall export detections as CSV |
| FR7.5 | System shall export current frame as PNG |
| FR7.6 | System shall export video with overlays rendered (MP4) |

### FR8: Viewport Interaction
| ID | Requirement |
|----|-------------|
| FR8.1 | System shall support zoom via mouse wheel |
| FR8.2 | System shall support pan via drag (when zoomed) |
| FR8.3 | System shall reset view on double-click |
| FR8.4 | System shall maintain aspect ratio (letterbox if needed) |

### FR9: State Management
| ID | Requirement |
|----|-------------|
| FR9.1 | System shall display current state in top bar |
| FR9.2 | System shall disable invalid controls per state |
| FR9.3 | System shall handle state transitions: IDLE → VIDEO_LOADED → PROCESSING → CACHE_READY |

### FR10: Layout & Navigation
| ID | Requirement |
|----|-------------|
| FR10.1 | System shall allow hiding/showing left stats panel |
| FR10.2 | System shall remember panel visibility preference |
| FR10.3 | System shall provide Help section accessible via menu or F1 |
| FR10.4 | System shall display tooltips on all interactive controls |

### FR11: Keyboard Shortcuts
| ID | Requirement |
|----|-------------|
| FR11.1 | Space → Play/Pause |
| FR11.2 | ←/→ → Step ±1 frame |
| FR11.3 | Shift+←/→ → Step ±10 frames |
| FR11.4 | Home/End → First/Last frame |
| FR11.5 | L → Toggle loop |
| FR11.6 | F11 → Toggle full-screen |
| FR11.7 | F1 → Open Help |
| FR11.8 | Ctrl+H → Toggle left panel visibility |

**Total: 48 Functional Requirements** across 11 categories.

---

## Parameter Fine-Tuning: Real-Time vs Offline Mode

### The Problem

Not all parameters have the same computational cost:

| Parameter Type | Cost | Examples |
|---------------|------|----------|
| **Visual-only** | Instant | Opacity, class visibility toggles |
| **Filter-only** | Fast (<50ms) | Confidence threshold |
| **Reclassification** | Medium (~1s) | px_per_mm calibration change |
| **Re-detection** | Expensive (minutes) | Blur kernel, Hough params, edge thresholds |

Real-time preview is ideal for visual/filter parameters but impractical for re-detection.

### Solution: Dual-Mode Parameter Tuning

```
┌─────────────────────────────────────────────────────────┐
│ Parameter Tuning Mode:  ○ Real-Time  ● Offline         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  When REAL-TIME (Preview):                              │
│  • Visual params update instantly                       │
│  • Filter params update instantly                       │
│  • Detection params show "preview estimate" on          │
│    current frame only (single-frame test)               │
│                                                         │
│  When OFFLINE (Batch):                                  │
│  • All param changes are queued                         │
│  • "Apply" button triggers full re-detection            │
│  • Progress bar shows batch processing                  │
│  • Results replace cached detections                    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Parameter Categories & Behavior

#### Category A: Visual Parameters (Always Real-Time)
No toggle needed — these are purely rendering changes:
- Overlay opacity
- Class visibility toggles
- Circle thickness
- Label visibility

**Behavior**: Instant update, no cache modification

#### Category B: Filter Parameters (Always Real-Time)
These filter cached detections without re-running CV:
- Confidence threshold
- Size class filters

**Behavior**: Instant update, reads from cache, applies filter

#### Category C: Classification Parameters (Mode-Dependent)
Reclassification is fast but affects cached data:
- px_per_mm (calibration)
- Size bin boundaries

| Mode | Behavior |
|------|----------|
| Real-Time | Reclassify all frames immediately (~1s), update cache |
| Offline | Queue change, apply on "Apply" button |

#### Category D: Detection Parameters (Offline Recommended)
These require re-running the CV pipeline:
- Blur kernel size
- Canny thresholds
- Hough circle parameters
- ROI margins

| Mode | Behavior |
|------|----------|
| Real-Time | Run detection on **current frame only** as preview |
| Offline | Queue changes, "Apply" runs full pipeline on all frames |

### UI Implementation

#### Process Tab Enhanced Layout
```
┌─────────────────────────────────────┐
│ [Process]                           │
├─────────────────────────────────────┤
│ Detection Parameters:               │
│                                     │
│ Blur Kernel:        [5]  ▼         │
│ Canny Low:          [50] ━━●━━     │
│ Canny High:         [150] ━━━●━    │
│ Hough dp:           [1.2] ━●━━━    │
│ Hough minDist:      [20] ━━●━━━    │
│                                     │
├─────────────────────────────────────┤
│ Mode: ○ Real-Time Preview           │
│       ● Offline (Batch)             │
├─────────────────────────────────────┤
│ [▶ Preview Frame]  [Apply to All]  │
│                                     │
│ ⚠ Unsaved changes (3 params)       │
├─────────────────────────────────────┤
│ Presets: [Default ▼] [Save] [Load] │
└─────────────────────────────────────┘
```

### User Workflow Examples

#### Workflow 1: Quick Confidence Adjustment
1. User moves confidence slider
2. Overlays instantly update (filter applied)
3. Stats panel updates
4. No cache modification needed

#### Workflow 2: Calibration Refinement  
1. User enters new px_per_mm value
2. If Real-Time mode: Classifications update immediately
3. If Offline mode: "Unsaved changes" indicator appears
4. User clicks "Apply" to commit

#### Workflow 3: Detection Parameter Tuning
1. User adjusts Canny threshold
2. If Real-Time mode: Current frame re-processes as preview
3. User sees effect on single frame
4. User clicks "Apply to All" for full batch processing
5. Progress bar shows processing
6. All frames updated in cache

### Benefits of This Approach

| Benefit | Description |
|---------|-------------|
| **Immediate Feedback** | Visual/filter changes are instant |
| **Safe Exploration** | Heavy params can be previewed before committing |
| **No Wasted Computation** | Offline mode batches changes |
| **Clear Mental Model** | User knows what's "live" vs "pending" |
| **Undo-Friendly** | Can revert before applying |

---

## Help Section Design

### Access Methods
- **F1** key from anywhere
- **Help** menu in menu bar
- **?** button in top bar

### Help Dialog Content
```
┌─────────────────────────────────────────────────────────┐
│ MillPresenter Help                              [X]    │
├─────────────────────────────────────────────────────────┤
│ [Overview] [Controls] [Shortcuts] [Troubleshooting]    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ KEYBOARD SHORTCUTS                                      │
│ ─────────────────────────────────────────────────────  │
│ Playback:                                               │
│   Space ............ Play/Pause                        │
│   ← / → ............ Step ±1 frame                     │
│   Shift+← / → ...... Step ±10 frames                   │
│   Home / End ....... First / Last frame                │
│   L ................ Toggle loop                       │
│                                                         │
│ View:                                                   │
│   F11 .............. Toggle full-screen                │
│   Ctrl+H ........... Toggle left panel                 │
│   Mouse wheel ...... Zoom viewport                     │
│   Double-click ..... Reset zoom                        │
│                                                         │
│ Other:                                                  │
│   F1 ............... Open Help                         │
│   Ctrl+O ........... Open video                        │
│   Ctrl+S ........... Save current frame                │
│   Ctrl+E ........... Export detections                 │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Contextual Tooltips
Every interactive element includes a tooltip:
- Hover delay: 500ms
- Format: "Action description (Shortcut)"
- Example: "Toggle playback loop (L)"

---

## Video Export with Overlays

### Export Dialog
```
┌─────────────────────────────────────────────────────────┐
│ Export Video with Overlays                      [X]    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ Output File: [________________] [Browse...]            │
│                                                         │
│ Resolution:  ○ Original (1920x1080)                    │
│              ● Match viewport                          │
│              ○ Custom: [1280] x [720]                  │
│                                                         │
│ Frame Range: ○ All frames                              │
│              ● Current selection                       │
│              ○ Custom: [0] to [1000]                   │
│                                                         │
│ Overlay Settings:                                       │
│   ☑ Include overlays                                   │
│   ☑ Use current visibility settings                   │
│   ☐ Include timestamp watermark                        │
│   ☐ Include stats overlay                              │
│                                                         │
│ Quality:     [High (H.264) ▼]                          │
│                                                         │
├─────────────────────────────────────────────────────────┤
│ Estimated size: ~250 MB                                │
│ Estimated time: ~2 minutes                             │
├─────────────────────────────────────────────────────────┤
│              [Cancel]              [Export]            │
└─────────────────────────────────────────────────────────┘
```

### Export Process
1. User configures export settings
2. Background worker reads cached detections
3. For each frame:
   - Decode video frame
   - Apply overlays (respecting current filter settings)
   - Encode to output video
4. Progress bar shows completion
5. Notification when complete

---

## Mockup Reference Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ [A] TOP BAR: MillPresenter | Video: mill_run1.mp4 | State | Detection %    │
├────────────┬───────────────────────────────────────────────┬────────────────┤
│ [E] LEFT   │                                               │ [C] RIGHT      │
│ ┌────────┐ │                                               │ ┌────────────┐ │
│ │Stats│Info│                                               │ │Overlay│Proc││
│ ├────────┤ │                                               │ ├────────────┤ │
│ │Total:  │ │                                               │ │Master:     │ │
│ │  342   │ │              [B] VIDEO VIEWPORT               │ │ ☐ Overlays │ │
│ ├────────┤ │                                               │ ├────────────┤ │
│ │By Class:│ │          (Colored circle overlays)           │ │Opacity 100%│ │
│ │● 4mm:85│ │                                               │ │━━━━━━━━━━━━│ │
│ │● 6mm:120│                                               │ ├────────────┤ │
│ │● 8mm:95│ │                                               │ │Conf: 0.50  │ │
│ │● 10mm:42│                                               │ │━━━━━━━━━━━━│ │
│ ├────────┤ │                                               │ ├────────────┤ │
│ │Conf Dist│ │                                               │ │Class Toggle│ │
│ │ ▁▂▅▇▅▂ │ │                                               │ │☑ ● 4mm    │ │
│ ├────────┤ │                                               │ │☑ ● 6mm    │ │
│ │Run Avg │ │                                               │ │☑ ● 8mm    │ │
│ │ ╱╲╱╲╱  │ │                                               │ │☑ ● 10mm   │ │
│ └────────┘ │                                               │ └────────────┘ │
├────────────┴───────────────────────────────────────────────┴────────────────┤
│ [D] BOTTOM: ⏮ ▶ ⏭ 🔁 │━━━━━━━━━━━●━━━━━━━━━━━━│ 15:32/45:00 │ Speed: 1.0x │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## HCI Principles Applied

### 1. Visibility of System Status (Nielsen #1)
- **Top bar** always shows: video name, processing state, detection progress
- **Left panel** shows real-time counts that update with each frame
- **Progress bar** during detection processing

### 2. Match Between System and Real World (Nielsen #2)
- Use familiar video player metaphors (▶ ⏸ ⏮ ⏭)
- Time display in MM:SS format (not frame numbers)
- Slider behaves like standard media scrubber
- Color-coded circles match physical bead appearance expectations

### 3. User Control and Freedom (Nielsen #3)
- Cancel button during processing
- Undo-friendly: all changes are non-destructive
- Loop toggle for repeated playback
- Easy reset (double-click viewport to reset zoom)

### 4. Consistency and Standards (Nielsen #4)
- Consistent color scheme throughout (4mm=Blue, 6mm=Green, 8mm=Orange, 10mm=Red)
- Standard Qt widget styling
- Keyboard shortcuts match common conventions (Space=Play, ←→=Seek)

### 5. Error Prevention (Nielsen #5)
- Disable "Run Detection" when no video loaded
- Disable export buttons when no detections available
- Validate calibration input before applying

### 6. Recognition Rather Than Recall (Nielsen #6)
- Colored dots next to class names match overlay colors
- Tooltips on all buttons
- Current values shown on sliders

### 7. Flexibility and Efficiency (Nielsen #7)
- Keyboard shortcuts for power users
- Mouse controls for casual users
- Direct manipulation (drag timeline, zoom viewport)

### 8. Aesthetic and Minimalist Design (Nielsen #8)
- Dark theme reduces visual noise
- Only essential info visible by default
- Tabbed panels reduce clutter

### 9. Fitts's Law Compliance
- Large play button (easy target)
- Sliders have adequate height (40px clickable area)
- Transport controls grouped together

### 10. Gestalt Principles
- **Proximity**: Related controls grouped (class toggles together)
- **Similarity**: All class toggles look the same
- **Enclosure**: Panels clearly bounded
- **Continuity**: Timeline is continuous horizontal element

---

## Color Palette (Exact from Mockup)

```python
COLORS = {
    # Application chrome
    "bg_dark": "#1E1E1E",           # Main background
    "bg_panel": "#2D2D2D",          # Panel backgrounds
    "bg_input": "#3C3C3C",          # Input field backgrounds
    "border": "#555555",            # Panel borders
    "text_primary": "#FFFFFF",      # Primary text
    "text_secondary": "#AAAAAA",    # Secondary text
    "accent": "#0078D4",            # Accent color (buttons, selections)
    
    # Bead class colors (BGR for OpenCV, RGB for Qt)
    "class_4mm": "#0000FF",         # Blue
    "class_6mm": "#00FF00",         # Green
    "class_8mm": "#FFA500",         # Orange
    "class_10mm": "#FF0000",        # Red
    
    # Status indicators
    "status_idle": "#888888",
    "status_processing": "#FFA500",
    "status_ready": "#00FF00",
    "status_error": "#FF0000",
}
```

---

## Dimensions (Exact from Mockup)

```python
DIMENSIONS = {
    # Main window
    "min_width": 1024,
    "min_height": 700,
    "default_width": 1280,
    "default_height": 800,
    
    # Panels
    "top_bar_height": 32,
    "bottom_bar_height": 48,
    "left_panel_width": 150,
    "right_panel_width": 200,
    
    # Typography
    "font_family": "Segoe UI",
    "font_size_large": 48,          # Total count number
    "font_size_normal": 12,
    "font_size_small": 10,
    
    # Widgets
    "slider_height": 20,
    "button_height": 28,
    "checkbox_size": 16,
    "color_dot_size": 12,
}
```

---

## Phase Structure

```
UI_PHASE_1: Project Scaffold & Main Window
UI_PHASE_2: Video Viewport (Core Playback)
UI_PHASE_3: Bottom Bar (Timeline & Transport)
UI_PHASE_4: Right Panel (Tabbed Controls)
UI_PHASE_5: Left Panel (Statistics)
UI_PHASE_6: Integration & Polish
```

---

## UI_PHASE_1: Project Scaffold & Main Window

**Goal:** Create the application skeleton with exact 5-panel layout from mockup.

### Deliverables
```
ui/
├── __init__.py
├── main.py              # Application entry point
├── main_window.py       # QMainWindow with layout
├── theme.py             # Colors, dimensions, fonts
└── state.py             # Application state management
```

### main_window.py Layout Code (Reference)
```python
# Central widget structure
main_layout = QVBoxLayout()

# [A] Top bar
top_bar = TopBar()
main_layout.addWidget(top_bar)

# Middle section (left + viewport + right)
middle_layout = QHBoxLayout()

# [E] Left panel (fixed width 150px)
left_panel = LeftPanel()
left_panel.setFixedWidth(150)
middle_layout.addWidget(left_panel)

# [B] Video viewport (stretches)
viewport = VideoViewport()
middle_layout.addWidget(viewport, stretch=1)

# [C] Right panel (fixed width 200px)
right_panel = RightPanel()
right_panel.setFixedWidth(200)
middle_layout.addWidget(right_panel)

main_layout.addLayout(middle_layout, stretch=1)

# [D] Bottom bar
bottom_bar = BottomBar()
bottom_bar.setFixedHeight(48)
main_layout.addWidget(bottom_bar)
```

### Acceptance Criteria
- [ ] Window opens at 1280x800 with dark theme
- [ ] 5 regions visible with correct proportions
- [ ] Left panel fixed at 150px
- [ ] Right panel fixed at 200px
- [ ] Viewport fills remaining space
- [ ] Top bar shows "MillPresenter" title
- [ ] Window has minimum size 1024x700
- [ ] Left panel can be hidden/shown (Ctrl+H)
- [ ] Full-screen mode works (F11)
- [ ] Menu bar includes Help menu

---

## UI_PHASE_2: Video Viewport (Core Playback)

**Goal:** Display video frames with overlays exactly as in mockup.

### Deliverables
```
ui/
├── widgets/
│   ├── __init__.py
│   ├── video_viewport.py    # Frame display + interaction
│   └── overlay_painter.py   # Circle drawing (matches mockup style)
```

### Overlay Rendering (Exact Match to Mockup)
```python
def draw_detection(painter, x, y, radius, color, opacity):
    """Draw a filled circle with slight border, matching mockup."""
    # Fill with opacity
    fill_color = QColor(color)
    fill_color.setAlphaF(opacity)
    painter.setBrush(QBrush(fill_color))
    
    # Subtle darker border
    border_color = QColor(color).darker(120)
    painter.setPen(QPen(border_color, 2))
    
    # Draw ellipse
    painter.drawEllipse(QPointF(x, y), radius, radius)
```

### Viewport Interactions
| Input | Action | HCI Principle |
|-------|--------|---------------|
| Mouse wheel | Zoom in/out | Direct manipulation |
| Drag (when zoomed) | Pan | Direct manipulation |
| Double-click | Reset to fit | User control/freedom |
| Hover on detection | Show tooltip (optional) | Recognition |

### Acceptance Criteria
- [ ] Video frame displays centered in viewport
- [ ] Aspect ratio maintained (letterbox if needed)
- [ ] Overlays match mockup style (filled circles, slight border)
- [ ] Colors match exactly (Blue/Green/Orange/Red)
- [ ] Zoom centers on mouse position
- [ ] Pan is smooth when zoomed
- [ ] Tooltips appear on hover over detections (class, confidence, diameter)

---

## UI_PHASE_3: Bottom Bar (Timeline & Transport)

**Goal:** Exact replication of mockup's transport controls.

### Layout (Exact from Mockup)
```
┌─────────────────────────────────────────────────────────────────────────┐
│ ⏮  ▶  ⏭  🔁  │━━━━━━━━━━━━━●━━━━━━━━━━━━━━━│ 15:32 / 45:00 │ Speed: 1.0x│
└─────────────────────────────────────────────────────────────────────────┘
     ↑        ↑                    ↑                    ↑            ↑
  Transport Loop              Timeline              Time         Speed
  (3 buttons)                 (Slider)             Label        Dropdown
```

### Widget Specifications

**Transport Buttons** (left to right):
1. `⏮` Step back (frame -10, or -1 with Shift)
2. `▶`/`⏸` Play/Pause toggle
3. `⏭` Step forward (frame +10, or +1 with Shift)

**Loop Toggle**: `🔁` button (highlighted when active)

**Timeline Slider**:
- Horizontal slider spanning available width
- Shows current position as filled portion
- Click anywhere to seek
- Drag handle for precise scrubbing

**Time Label**: `MM:SS / MM:SS` format (current / total)

**Speed Dropdown**: Options `[0.25x, 0.5x, 1.0x, 1.5x, 2.0x]`

### Keyboard Shortcuts (Standard Conventions)
| Key | Action |
|-----|--------|
| Space | Play/Pause |
| ← | Step back 1 frame |
| → | Step forward 1 frame |
| Shift+← | Step back 10 frames |
| Shift+→ | Step forward 10 frames |
| Home | Go to first frame |
| End | Go to last frame |
| L | Toggle loop |

### Acceptance Criteria
- [ ] All transport buttons functional
- [ ] Play/Pause icon toggles correctly
- [ ] Slider reflects playback position
- [ ] Clicking slider seeks to that position
- [ ] Time label updates in MM:SS format
- [ ] Speed dropdown affects playback rate
- [ ] Loop toggle highlighted when active
- [ ] All keyboard shortcuts work

---

## UI_PHASE_4: Right Panel (Tabbed Controls)

**Goal:** Exact replication of right panel from mockup.

### Layout (Exact from Mockup)
```
┌─────────────────────────────────┐
│ [Overlay] [Process] [Calibrate] [Prefs] │  ← Tab bar
├─────────────────────────────────┤
│ Master Toggle:                  │
│ Show Overlays          [═══○]  │  ← Toggle switch (ON)
├─────────────────────────────────┤
│ Opacity                   100% │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━● │  ← Slider
├─────────────────────────────────┤
│ Confidence Threshold      0.50 │
│ ━━━━━━━━━━━━━━━●━━━━━━━━━━━━━━ │  ← Slider
├─────────────────────────────────┤
│ Size Class Toggles:             │
│ ☑ ● 4mm (Blue)                 │  ← Checkbox + colored dot
│ ☑ ● 6mm (Green)                │
│ ☑ ● 8mm (Orange)               │
│ ☑ ● 10mm (Red)                 │
└─────────────────────────────────┘
```

### Tab Specifications

**Tab 1: Overlay** (default, shown in mockup)
- Master toggle switch: Show/Hide all overlays
- Opacity slider: 0-100% (default 100%)
- Confidence threshold slider: 0.0-1.0 (default 0.50, shown in mockup)
- Size class toggles with colored indicator dots

**Tab 2: Process**
- Real-Time / Offline mode toggle
- Detection parameter sliders (blur, Canny, Hough)
- "Preview Frame" button (test on current frame)
- "Apply to All" button (full batch processing)
- Progress bar (hidden until processing)
- Cancel button (shown during processing)
- Unsaved changes indicator
- Preset save/load controls

**Tab 3: Calibrate**
- Auto-calibrate checkbox
- px_per_mm input field with label
- "Recalculate" button
- Show ROI toggle

**Tab 4: Prefs (Preferences)**
- Theme toggle (Dark/Light)
- Default confidence threshold
- Auto-save settings checkbox

### Signal Flow (Immediate Feedback - HCI Principle)
```
Opacity Slider changed → emit signal → viewport.setOpacity() → repaint
Confidence Slider changed → emit signal → viewport.setThreshold() → filter & repaint
Class Toggle changed → emit signal → viewport.setClassVisible() → repaint
```

### Acceptance Criteria
- [ ] All 4 tabs accessible, "Overlay" is default
- [ ] Master toggle immediately hides/shows overlays
- [ ] Opacity slider updates viewport in real-time
- [ ] Confidence slider filters detections in real-time
- [ ] Class toggles have correct colored dots
- [ ] Unchecking class hides those detections immediately
- [ ] Slider values shown next to labels (100%, 0.50)
- [ ] Real-Time/Offline toggle works correctly
- [ ] Preview Frame shows detection on current frame
- [ ] Apply to All triggers batch processing with progress
- [ ] Unsaved changes indicator appears when params modified
- [ ] All controls have descriptive tooltips

---

## UI_PHASE_5: Left Panel (Statistics)

**Goal:** Exact replication of left stats panel from mockup.

### Layout (Exact from Mockup)
```
┌────────────────┐
│ [Stats] [Info] │  ← Mini tab bar
├────────────────┤
│ Total Bead Count:   │
│                     │
│       342           │  ← Large font (48pt)
│                     │
├────────────────┤
│ Count by Size Class:│
│ ● 4mm: 85           │  ← Blue dot
│ ● 6mm: 120          │  ← Green dot
│ ● 8mm: 95           │  ← Orange dot
│ ● 10mm: 42          │  ← Red dot
├────────────────┤
│ Confidence          │
│ Distribution        │
│ ┌──────────────┐   │
│ │ ▁▂▅▇▅▂▁     │   │  ← Histogram (horizontal bars)
│ └──────────────┘   │
├────────────────┤
│ Running Average     │
│ ┌──────────────┐   │
│ │  ╱╲_╱╲_     │   │  ← Line graph
│ └──────────────┘   │
└────────────────┘
```

### Widget Specifications

**Total Count Display**:
- Label "Total Bead Count:" (12pt, secondary color)
- Large number (48pt, primary color, bold)
- Updates on each frame

**Class Breakdown**:
- Label "Count by Size Class:" (12pt)
- 4 rows, each with:
  - Colored dot (12x12px, class color)
  - Class name ("4mm:", "6mm:", etc.)
  - Count number

**Confidence Distribution Histogram**:
- Title "Confidence Distribution"
- Small histogram widget (~80x60px)
- Horizontal bars for bins [0.5-0.6, 0.6-0.7, 0.7-0.8, 0.8-0.9, 0.9-1.0]
- Bar length proportional to count in bin

**Running Average Graph**:
- Title "Running Average"
- Small line chart widget (~80x60px)
- Shows last 30 frames of total count
- Helps visualize count stability

### Stats vs Info Tab
- **Stats** (default): Shows counts, histogram, graph
- **Info**: Shows video metadata (filename, resolution, FPS, duration, frame count)

### Acceptance Criteria
- [ ] Total count displays in large font
- [ ] Count updates when frame changes
- [ ] Class breakdown shows colored dots matching overlays
- [ ] Per-class counts are accurate
- [ ] Histogram shows confidence distribution
- [ ] Running average graph updates with playback
- [ ] Info tab shows video metadata

---

## UI_PHASE_6: Integration & Polish

**Goal:** Complete workflow, error handling, and visual polish.

### File Operations
1. **Open Video**: File dialog with filters (*.mp4, *.mov, *.avi)
2. **Load Cache**: Auto-detect or manual select
3. **Export Detections**: JSON, CSV buttons
4. **Export Frame**: Save current frame as PNG
5. **Export Video**: Render video with overlays (MP4)

### State Machine
```
IDLE → (open video) → VIDEO_LOADED
VIDEO_LOADED → (run detection) → PROCESSING
PROCESSING → (complete) → CACHE_READY
CACHE_READY → (play) → PLAYING
PLAYING → (pause) → CACHE_READY
CACHE_READY → (export video) → EXPORTING
EXPORTING → (complete) → CACHE_READY
Any → (error) → ERROR
```

### Control States (Error Prevention - HCI Principle)
| State | Enabled Controls | Disabled Controls |
|-------|------------------|-------------------|
| IDLE | Open Video | All others |
| VIDEO_LOADED | Run Detection, Timeline | Export |
| PROCESSING | Cancel | Run Detection, Timeline |
| CACHE_READY | All playback, Export | Cancel |
| PLAYING | Pause, Timeline, Overlays | Run Detection |

### Top Bar Content (from Mockup)
```
MillPresenter | Video: mill_run1.mp4 | State: CACHE_READY | Detection: 100% (Cached)
```

### Error Handling
- Toast notifications for non-critical errors
- Modal dialogs for critical errors
- Log panel in Process tab for details

### Acceptance Criteria
- [ ] Complete workflow: Open → Detect → Play → Export
- [ ] State shown in top bar matches actual state
- [ ] Controls properly enabled/disabled per state
- [ ] Export produces valid JSON/CSV files
- [ ] Export video with overlays works correctly
- [ ] Errors shown to user appropriately
- [ ] 30+ FPS playback on 1080p video
- [ ] Help dialog accessible via F1 and menu
- [ ] All keyboard shortcuts functional
- [ ] Tooltips on all interactive controls

---

## File Structure (Final)

```
ui/
├── __init__.py
├── main.py                  # Entry point, exception handling
├── main_window.py           # QMainWindow, layout
├── theme.py                 # Colors, dimensions, fonts
├── state.py                 # AppState enum, state machine
├── video_decoder.py         # OpenCV VideoCapture wrapper
│
├── widgets/
│   ├── __init__.py
│   ├── video_viewport.py    # Video display, zoom, pan
│   ├── overlay_painter.py   # Circle rendering
│   ├── timeline_slider.py   # Custom styled slider
│   ├── toggle_switch.py     # iOS-style toggle (mockup shows this)
│   ├── color_dot.py         # Colored dot widget
│   └── detection_tooltip.py # Hover tooltip for detections
│
├── panels/
│   ├── __init__.py
│   ├── top_bar.py           # Title, video info, state
│   ├── bottom_bar.py        # Transport, timeline, speed
│   ├── left_panel.py        # Stats container (collapsible)
│   ├── right_panel.py       # Tab widget container
│   │
│   ├── left/
│   │   ├── count_display.py     # Large count + breakdown
│   │   ├── histogram_widget.py  # Confidence distribution
│   │   └── trend_graph.py       # Running average
│   │
│   └── right/
│       ├── overlay_tab.py       # Overlay controls (default)
│       ├── process_tab.py       # Detection controls + params
│       ├── calibrate_tab.py     # Calibration controls
│       └── prefs_tab.py         # Preferences
│
├── dialogs/
│   ├── __init__.py
│   ├── help_dialog.py       # Help window (F1)
│   ├── export_video_dialog.py  # Video export settings
│   └── about_dialog.py      # About MillPresenter
│
└── workers/
    ├── __init__.py
    ├── detection_worker.py  # QThread for CV pipeline
    └── export_worker.py     # QThread for video export
```

---

## Integration Points

| UI Component | Backend Module | Signal/Method |
|--------------|----------------|---------------|
| VideoViewport | `cache.py` | `cache.get_detections(frame_idx)` |
| OverlayPainter | `playback.py` | `render_overlay(frame, detections)` |
| ProcessTab | `pipeline.py` | `run_detection(video_path)` |
| CalibrateTab | `classify.py` | `reclassify_with_new_calibration()` |
| LeftPanel | `metrics.py` | `compute_frame_metrics()` |
| ExportTab | `cache.py` | `export_json()`, `export_csv()` |

---

## Accessibility Considerations

1. **Keyboard Navigation**: All controls accessible via Tab key
2. **High Contrast**: Text meets WCAG AA contrast ratios
3. **Focus Indicators**: Visible focus ring on all interactive elements
4. **Tooltips**: All buttons have descriptive tooltips
5. **Screen Reader**: Semantic labels on widgets (Qt accessibility)

---

## Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| Frame rate (1080p) | ≥30 FPS | QTimer callback timing |
| Frame rate (4K scaled) | ≥30 FPS | Scale to 1080p for display |
| Seek latency | <100ms | Time from click to display |
| UI responsiveness | <50ms | No blocking on main thread |

---

## Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| PySide6 learning curve | Medium | Medium | Start with simple widgets |
| 4K performance | High | Medium | Scale video to display size |
| Thread synchronization | Medium | High | Use Qt signals only |
| Seek performance | Low | Medium | Frame caching buffer |

---

## Development Order

```
Session 1: Phase 1 (Scaffold) + Phase 2 start
Session 2: Phase 2 (Viewport) complete
Session 3: Phase 3 (Timeline/Transport)
Session 4: Phase 4 (Right Panel)
Session 5: Phase 5 (Left Panel)
Session 6: Phase 6 (Integration & Polish)
```

---

## Testing Checklist

### Per-Phase Tests
- [ ] Phase 1: Window opens, layout correct, dark theme applied
- [ ] Phase 2: Video displays, overlays render with correct colors
- [ ] Phase 3: Playback controls work, keyboard shortcuts functional
- [ ] Phase 4: All tabs functional, real-time filter updates
- [ ] Phase 5: Stats update correctly, graphs render
- [ ] Phase 6: Complete workflow passes

### Integration Tests
- [ ] Open video → Run detection → View results
- [ ] Change confidence threshold → Overlay updates immediately
- [ ] Toggle size class → Detections hide/show
- [ ] Export JSON → File is valid
- [ ] 4K video plays smoothly (scaled)

---

## Next Action

**Ready to start UI_PHASE_1?**

1. Install PySide6: `pip install PySide6`
2. Create `ui/` folder structure
3. Implement `theme.py` with exact colors/dimensions from mockup
4. Implement `main_window.py` with 5-panel layout
5. Test window opens correctly with dark theme
