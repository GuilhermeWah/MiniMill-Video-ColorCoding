# Mill Presenter Detection Pipeline

## Overview

This document describes the complete data flow from video frame to rendered overlay. Understanding this pipeline is critical for debugging sizing issues.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        DETECTION PIPELINE                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────┐    ┌────────────────┐    ┌───────────────┐    ┌────────────┐ │
│  │  Video   │───►│  FrameLoader   │───►│   Processor   │───►│   Cache    │ │
│  │  File    │    │  (PyAV/NVDEC)  │    │ (VisionPipe)  │    │  (JSONL)   │ │
│  └──────────┘    └────────────────┘    └───────────────┘    └────────────┘ │
│                                                │                    │       │
│                                                ▼                    │       │
│                                   ┌───────────────────────┐        │       │
│                                   │  Preprocessing        │        │       │
│                                   │  - Grayscale          │        │       │
│                                   │  - Bilateral Filter   │        │       │
│                                   │  - CLAHE              │        │       │
│                                   └───────────┬───────────┘        │       │
│                                               │                    │       │
│                                               ▼                    │       │
│                    ┌──────────────────────────┴─────────────┐      │       │
│                    │                                         │      │       │
│                    ▼                                         ▼      │       │
│         ┌──────────────────┐                    ┌──────────────────┐│       │
│         │  HoughCircles    │                    │  ContourFilter   ││       │
│         │  - minR, maxR    │                    │  - Canny edges   ││       │
│         │  - dp, param1/2  │                    │  - Circularity   ││       │
│         └────────┬─────────┘                    └────────┬─────────┘│       │
│                  │                                       │          │       │
│                  └───────────────┬───────────────────────┘          │       │
│                                  │                                  │       │
│                                  ▼                                  │       │
│                    ┌───────────────────────┐                        │       │
│                    │  Filtering Pipeline   │                        │       │
│                    │  1. ROI Mask Check    │                        │       │
│                    │  2. Brightness Filter │                        │       │
│                    │  3. Annulus Logic     │                        │       │
│                    │  4. NMS Deduplication │                        │       │
│                    └───────────┬───────────┘                        │       │
│                                │                                    │       │
│                                ▼                                    │       │
│                    ┌───────────────────────┐                        │       │
│                    │  Classification       │                        │       │
│                    │  r_px → diameter_mm   │                        │       │
│                    │  → bin lookup (4/6/8/10)                       │       │
│                    └───────────┬───────────┘                        │       │
│                                │                                    │       │
│                                ▼                                    │       │
│                    ┌───────────────────────┐                        │       │
│                    │  Ball Object          │◄───────────────────────┘       │
│                    │  - x, y (center)      │                                │
│                    │  - r_px (detected)    │                                │
│                    │  - diameter_mm        │                                │
│                    │  - cls (4/6/8/10)     │                                │
│                    │  - conf               │                                │
│                    └───────────────────────┘                                │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                         DISPLAY PIPELINE                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────┐    ┌───────────────────┐    ┌───────────────────────────┐  │
│  │   Cache    │───►│  OverlayRenderer  │───►│  QOpenGLWidget/Exporter   │  │
│  │  (Ball)    │    │  (Draw Circles)   │    │  (Final Output)           │  │
│  └────────────┘    └───────────────────┘    └───────────────────────────┘  │
│                              │                                               │
│                              ▼                                               │
│               ┌────────────────────────────┐                                │
│               │  For each Ball:            │                                │
│               │  1. Look up real_diameter  │                                │
│               │     from cls (4→3.94mm,    │                                │
│               │     6→5.79mm, 8→7.63mm,    │                                │
│               │     10→9.90mm)             │                                │
│               │                            │                                │
│               │  2. Calculate display_r:   │                                │
│               │     r = (real_d/2) *       │                                │
│               │         px_per_mm * scale  │                                │
│               │                            │                                │
│               │  3. Draw circle at (x,y)   │                                │
│               │     with radius r          │                                │
│               └────────────────────────────┘                                │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Detailed Component Breakdown

### 1. Frame Loader (`playback.py`)

- Decodes video frames using PyAV (CPU) or NVDEC (GPU)
- Handles rotation metadata from camera
- Outputs BGR frames for processing

### 2. Vision Processor (`processor.py`)

#### 2.1 Preprocessing
```python
# Lines 42-55
gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
blurred = cv2.bilateralFilter(gray, d=9, sigmaColor=75, sigmaSpace=75)
clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
detection_img = clahe.apply(blurred)
```

#### 2.2 HoughCircles Detection
```python
# Lines 66-73
min_r = max(4, int((self.bins[0]['min'] * self.px_per_mm) / 2) - 1)
max_r = min(100, int((self.bins[-1]['max'] * self.px_per_mm) / 2) + 2)

circles = cv2.HoughCircles(
    detection_img, cv2.HOUGH_GRADIENT,
    dp=1.0, minDist=10, param1=80, param2=25,
    minRadius=min_r, maxRadius=max_r
)
```

**CRITICAL**: `minRadius` and `maxRadius` are calculated from bin definitions × `px_per_mm`.

#### 2.3 Contour Detection (Backup Path)
```python
# Lines 100-137
edges = cv2.Canny(detection_img, low_thresh, high_thresh)
contours, _ = cv2.findContours(edges, ...)

for cnt in contours:
    circularity = 4 * pi * area / (perimeter^2)
    if circularity > threshold:
        (x, y), r = cv2.minEnclosingCircle(cnt)
        # Same radius constraints as HoughCircles
        if min_r <= r <= max_r:
            candidates.append((x, y, r, conf))
```

#### 2.4 Filtering Pipeline
```python
# Lines 140-200
# 1. ROI Mask Check - reject if center on black pixel
# 2. Brightness Filter - reject if center brightness < 25 (holes/shadows)
# 3. Annulus Logic - reject small circles inside larger ones (holes in beads)
# 4. NMS - reject duplicate detections of same physical bead
```

#### 2.5 Classification
```python
# Lines 206-210
diameter_mm = (2 * r_px) / self.px_per_mm
cls = self._classify_diameter(diameter_mm)  # Bin lookup: 4/6/8/10

# Ball stored with DETECTED r_px, not real diameter
Ball(x, y, r_px, diameter_mm, cls, conf)
```

### 3. Overlay Renderer (`overlay.py`)

```python
# Lines 18-23
real_diameters_mm = {
    4: 3.94,   # Actual 4mm bead diameter
    6: 5.79,   # Actual 6mm bead diameter
    8: 7.63,   # Actual 8mm bead diameter
    10: 9.90   # Actual 10mm bead diameter
}

# Lines 58-60
real_diameter = self.real_diameters_mm.get(ball.cls, ball.diameter_mm)
r = (real_diameter / 2) * self.px_per_mm * scale
# Draw circle at (ball.x, ball.y) with radius r
```

---

## The `px_per_mm` Coupling Problem

### Where `px_per_mm` Is Used

| Location | Purpose | Effect of Increasing px_per_mm |
|----------|---------|-------------------------------|
| `processor.py:66-73` | Calculate minRadius/maxRadius for HoughCircles | Searches for LARGER pixel circles |
| `processor.py:127-128` | Calculate min_r/max_r for contour filtering | Accepts LARGER pixel circles |
| `processor.py:206` | Convert detected r_px → diameter_mm | SMALLER mm values (same pixels ÷ more px/mm) |
| `overlay.py:58-60` | Convert real_diameter_mm → display r_px | LARGER drawn circles |

### The Problem

When you change `px_per_mm`, you change **everything simultaneously**:

1. **Detection**: Searches for different pixel radius ranges
2. **Classification**: Same pixel radius → different mm → different bin
3. **Display**: Same mm → different pixel radius on screen

**Example**: If you increase `px_per_mm` from 4.0 to 5.0:
- Detection: Now looking for larger pixel circles (min 6→7.5, max 24→30)
- Classification: A 20px radius circle → 10mm (was 4.0) → now 8mm (at 5.0)
- Display: A 10mm bead → now drawn as 25px (was 20px)

These changes **fight each other**. You cannot tune detection independently of display.

---

## Ball Sizes Reference

| Class | Bin Range (mm) | Real Diameter (mm) | At px_per_mm=4.2 |
|-------|----------------|-------------------|-------------------|
| 4 | 3.0 - 4.87 | 3.94 | 8.3px radius |
| 6 | 4.87 - 6.71 | 5.79 | 12.2px radius |
| 8 | 6.71 - 8.77 | 7.63 | 16.0px radius |
| 10 | 8.77 - 11.5 | 9.90 | 20.8px radius |

---

## Current Configuration

From `configs/sample.config.yaml`:
```yaml
calibration:
  px_per_mm: 4.20

bins:
  - { label: 4,  min: 3.0,  max: 4.87 }
  - { label: 6,  min: 4.87, max: 6.71 }
  - { label: 8,  min: 6.71, max: 8.77 }
  - { label: 10, min: 8.77, max: 11.5 }
```

---

## Proposed Fix: Decouple Detection from Display

### Option 1: Fixed Pixel Ranges for Detection

Instead of calculating minRadius/maxRadius from bins × px_per_mm, use fixed pixel ranges:

```python
# processor.py - BEFORE
min_r = max(4, int((self.bins[0]['min'] * self.px_per_mm) / 2) - 1)
max_r = min(100, int((self.bins[-1]['max'] * self.px_per_mm) / 2) + 2)

# processor.py - AFTER (fixed pixel ranges)
min_r = self.config.get('vision', {}).get('min_radius_px', 5)
max_r = self.config.get('vision', {}).get('max_radius_px', 35)
```

This way:
- Detection always searches the same pixel range (configured separately)
- `px_per_mm` only affects classification and display
- You can tune detection sensitivity without changing display sizes

### Option 2: Separate Calibration Values

Add a `detection_px_per_mm` separate from `display_px_per_mm`:

```yaml
calibration:
  detection_px_per_mm: 4.20  # Used for classification
  display_px_per_mm: 5.50    # Used for drawing circles
```

### Option 3: Store Real Pixel Radius

Instead of drawing based on class → real_mm → pixels, store and use the detected pixel radius directly:

```python
# overlay.py - Use detected radius, not back-calculated
r = ball.r_px * scale  # Draw exactly what was detected
```

This shows "what the detector saw" rather than "what size the bead should be."

---

## Verification Checklist

- [ ] Detection minRadius/maxRadius matches expected pixel sizes for your video resolution
- [ ] Classification bin boundaries produce correct class assignments
- [ ] Display circles visually match the beads in the video
- [ ] Changing display scale doesn't affect classification counts
- [ ] ROI mask correctly excludes non-bead regions

---

## Files Referenced

| File | Lines | Purpose |
|------|-------|---------|
| `src/mill_presenter/core/processor.py` | 42-55 | Preprocessing |
| `src/mill_presenter/core/processor.py` | 66-73 | HoughCircles with dynamic radius |
| `src/mill_presenter/core/processor.py` | 100-137 | Contour detection |
| `src/mill_presenter/core/processor.py` | 140-200 | Filtering pipeline |
| `src/mill_presenter/core/processor.py` | 206-210 | Classification |
| `src/mill_presenter/core/overlay.py` | 18-23 | Real diameter lookup |
| `src/mill_presenter/core/overlay.py` | 58-60 | Display radius calculation |
| `configs/sample.config.yaml` | All | Configuration values |
