# ROI Mask System

## Overview

The ROI (Region of Interest) mask system allows users to define which area of the video frame should be analyzed for bead detection. Areas outside the mask are ignored, preventing false detections on bolts, flanges, frame edges, and other non-bead structures.

## Visual Representation

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ROI MASK SYSTEM                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐     ┌──────────────────┐     ┌─────────────────────┐     │
│  │  ROI Button  │────►│  ROIController   │────►│  roi_mask (QImage)  │     │
│  │  (MainWindow)│     │     .start()     │     │  RGBA, Red overlay  │     │
│  └──────────────┘     └──────────────────┘     └─────────────────────┘     │
│                              │                           │                  │
│                              ▼                           ▼                  │
│                    ┌──────────────────┐       ┌──────────────────┐         │
│                    │ auto_detect_mill │       │   VideoWidget    │         │
│                    │ HoughCircles for │       │   paintEvent()   │         │
│                    │ large drum circle│       │ Draws red overlay│         │
│                    └────────┬─────────┘       └──────────────────┘         │
│                             │                                               │
│                             ▼                                               │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    USER INTERACTION                                   │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                   │  │
│  │  │ Inner 70%   │  │ Rim (30%)   │  │  Outside    │                   │  │
│  │  │ DRAG = MOVE │  │ DRAG=RESIZE │  │ CLICK=NEW   │                   │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                   │  │
│  │                         │                                             │  │
│  │                         ▼                                             │  │
│  │              ┌──────────────────────┐                                 │  │
│  │              │    _update_mask()    │                                 │  │
│  │              │  Red fill + Clear    │                                 │  │
│  │              │  circle + Yellow rim │                                 │  │
│  │              └──────────────────────┘                                 │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    SAVE & DETECTION                                   │  │
│  │                                                                        │  │
│  │  ┌──────────────┐     ┌────────────────────┐     ┌────────────────┐  │  │
│  │  │ Toggle OFF   │────►│  save(path)        │────►│ roi_mask.png   │  │  │
│  │  │ ROI button   │     │  Grayscale PNG     │     │ White = Valid  │  │  │
│  │  └──────────────┘     │  White circle on   │     │ Black = Ignore │  │  │
│  │                       │  black background  │     └───────┬────────┘  │  │
│  │                       └────────────────────┘             │           │  │
│  │                                                          ▼           │  │
│  │                                              ┌────────────────────┐  │  │
│  │                                              │  processor.py      │  │  │
│  │                                              │  process_frame()   │  │  │
│  │                                              │                    │  │  │
│  │                                              │  if roi_mask[y,x]==0│  │  │
│  │                                              │     continue; //skip│  │  │
│  │                                              └────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Components

### 1. UI Activation (`main_window.py`)

When the user clicks the **"ROI Mask"** button:

```python
def toggle_roi(active):
    if active:
        # Pause playback
        # Call roi_controller.start()
        # Show status: "ROI Mode: Left Click to Mask..."
    else:
        # roi_controller.cancel()
        # roi_controller.save("exports/roi_mask.png")
        # Show status: "ROI Mask saved to..."
```

**Location:** `src/mill_presenter/ui/main_window.py` (lines 360-383)

---

### 2. ROI Controller (`roi_controller.py`)

The `ROIController` class manages all ROI mask logic.

#### Initialization (`start()`)

```python
def start():
    # 1. Create QImage mask (same size as video frame)
    # 2. Fill with RED (RGBA: 255,0,0,128) = "Ignore" overlay
    # 3. Try auto_detect_mill() to find the drum
    # 4. Set widget to 'roi' interaction mode
    # 5. If drum found, cut out the valid circle
```

**Location:** `src/mill_presenter/ui/roi_controller.py` (lines 20-42)

#### Auto-Detection (`auto_detect_mill()`)

Attempts to automatically find the mill drum circle:

```python
def auto_detect_mill():
    # 1. Convert QImage → numpy array
    # 2. Grayscale + MedianBlur
    # 3. HoughCircles with:
    #    - minRadius = 35% of frame height
    #    - maxRadius = 48% of frame height
    # 4. Take the strongest/largest circle
    # 5. Set center_point + radius (at 96% to stay inside rim)
```

**Location:** `src/mill_presenter/ui/roi_controller.py` (lines 44-93)

---

### 3. User Interaction

Mouse events flow from `VideoWidget` signals to `ROIController` handlers:

```
VideoWidget.mouse_pressed  ──► ROIController.handle_mouse_press()
VideoWidget.mouse_moved    ──► ROIController.handle_mouse_move()
VideoWidget.mouse_released ──► ROIController.handle_mouse_release()
```

#### Interaction Zones

| Zone | Condition | Action |
|------|-----------|--------|
| **Inner 70%** | `dist < radius * 0.7` | **Move** the circle |
| **Rim (outer 30%)** | `dist < radius + 30px` | **Resize** the circle |
| **Outside** | Click anywhere else | Start a **new circle** |
| **Right Click** | Anywhere | **Reset** (clear circle) |

#### Mouse Handlers

```python
def handle_mouse_press(x, y, left_button):
    if right_button:
        # Reset - clear the circle entirely
        center_point = None
        radius = 0
        
    elif left_button:
        if clicking inside existing circle:
            if center zone (< 70%):
                is_moving = True  # Drag to move
            elif rim zone:
                is_dragging = True  # Drag to resize
        else:
            # Start new circle at click point
            center_point = (x, y)
            is_dragging = True

def handle_mouse_move(x, y):
    if is_moving:
        # Update center_point to new position
        center_point = new_pos - offset
        
    if is_dragging:
        # Calculate radius from center to mouse
        radius = distance(center, mouse)
        
    _update_mask()  # Redraw the mask
```

**Location:** `src/mill_presenter/ui/roi_controller.py` (lines 104-160)

---

### 4. Mask Rendering (`_update_mask()`)

Provides real-time visual feedback:

```python
def _update_mask():
    # 1. Fill entire mask with RED (semi-transparent)
    mask.fill(QColor(255, 0, 0, 128))
    
    # 2. If circle defined:
    #    - "Cut out" the valid area (make transparent)
    painter.setCompositionMode(CompositionMode_Clear)
    painter.drawEllipse(center, radius, radius)
    
    #    - Draw yellow dashed outline for visibility
    painter.setPen(QPen(Yellow, 2, DashLine))
    painter.drawEllipse(center, radius, radius)
    
    # 3. Trigger repaint
    widget.update()
```

**Visual Result:**
- 🔴 **Red overlay** = Ignored regions (outside drum)
- ⚪ **Transparent** = Valid region (inside drum)  
- 🟡 **Yellow dashed circle** = Boundary indicator

**Location:** `src/mill_presenter/ui/roi_controller.py` (lines 165-193)

---

### 5. Display in VideoWidget

The mask is composited over the video frame:

```python
def paintEvent():
    # ... draw video frame ...
    
    # Draw ROI Mask overlay
    if self.roi_mask:
        painter.drawImage(target_rect, self.roi_mask)
```

**Location:** `src/mill_presenter/ui/widgets.py` (lines 219-220)

---

### 6. Saving the Mask (`save()`)

When exiting ROI mode, the mask is saved as a binary PNG:

```python
def save(path):
    # 1. Create new Grayscale8 image (black = 0)
    final_mask = QImage(width, height, Format_Grayscale8)
    final_mask.fill(Black)
    
    # 2. If circle defined, draw WHITE filled circle
    if center_point and radius > 0:
        painter.setBrush(White)
        painter.drawEllipse(center, radius, radius)
    
    # 3. Save as PNG
    final_mask.save(path)
```

**Output file:** `exports/roi_mask.png`
- **White (255)** = Valid region → Beads here will be processed
- **Black (0)** = Ignored region → Beads here will be rejected

**Location:** `src/mill_presenter/ui/roi_controller.py` (lines 195-218)

---

### 7. Detection Pipeline Usage

During detection, the mask filters out invalid detections:

```python
def process_frame(frame, roi_mask):
    for each detected circle (x, y, r):
        # ROI Check - FIRST filter applied
        if roi_mask is not None:
            # Is center within image bounds?
            if not (0 <= y < roi_mask.height and 0 <= x < roi_mask.width):
                continue  # Reject - out of bounds
            
            # Is center on a BLACK pixel (ignored area)?
            if roi_mask[y, x] == 0:
                continue  # Reject - outside valid region
        
        # Continue with brightness filter, annulus logic, NMS, etc.
```

**Important:** Only the **center point** of a detected circle is checked against the mask, not the full circle area.

**Location:** `src/mill_presenter/core/processor.py` (lines 130-135)

---

## Two Mask Representations

| Representation | Format | Purpose |
|----------------|--------|---------|
| **UI Mask** | ARGB32 QImage | Visual feedback (red overlay with transparent hole) |
| **Saved Mask** | Grayscale8 PNG | Binary mask for detection (white/black) |

---

## File Locations

| File | Purpose |
|------|---------|
| `src/mill_presenter/ui/roi_controller.py` | ROI controller logic |
| `src/mill_presenter/ui/main_window.py` | Button handling, save trigger |
| `src/mill_presenter/ui/widgets.py` | Mouse events, overlay display |
| `src/mill_presenter/core/processor.py` | Mask filtering in detection |
| `exports/roi_mask.png` | Saved binary mask |

---

## Usage Summary

1. **Click "ROI Mask"** button to enter ROI mode
2. **Auto-detection** attempts to find the drum automatically
3. **Adjust** by dragging:
   - Center area → Move
   - Edge area → Resize
   - Outside → New circle
   - Right-click → Reset
4. **Click "ROI Mask"** again to exit and save
5. Mask is saved to `exports/roi_mask.png`
6. Detection uses the mask to filter out beads outside the valid region
