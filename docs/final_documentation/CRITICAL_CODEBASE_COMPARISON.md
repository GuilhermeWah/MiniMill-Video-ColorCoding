# MillPresenter: Critical Codebase Comparison

## Legacy System vs Current Refactor

**Document Purpose**: Critical technical analysis comparing the legacy codebase (old_solution) with the current refactored implementation. This is not an expositive summary—it identifies **architectural choices, tradeoffs, gaps, and legacy features worth considering for adoption**.

**Date**: 2025-01-XX  
**Scope**: Full pipeline comparison, focusing on detection, caching, playback, and UI architecture.

---

## Executive Summary

| Aspect | Legacy | Current | Critical Assessment |
|--------|--------|---------|---------------------|
| **Detection Strategy** | Dual-path (Hough + Contour) | Single-path (HoughCircles only) | ⚠️ **Current loses robustness** |
| **Video Decoding** | PyAV (frame-accurate) | OpenCV VideoCapture | ⚠️ **Current may drift on seeks** |
| **Cache Format** | JSONL (append-only, crash-tolerant) | JSON (single file, atomic) | ⚠️ **Current lacks crash recovery** |
| **Overlay Rendering** | Shared OverlayRenderer (UI=Export) | Separate per-context | ✅ Current is cleaner separation |
| **Hole Rejection** | Annulus logic (inner-hole detection) | None visible | ⚠️ **Current may accept hollow beads as 2 detections** |
| **Rotation Handling** | Explicit metadata parsing | Not visible in VideoController | ⚠️ **Current may flip/rotate incorrectly** |
| **Confidence Scoring** | Heuristic (flat 0.8) | Multi-feature (edge, circularity, interior) | ✅ **Current is superior** |
| **Filtering** | 4-stage (ROI, brightness, annulus, NMS) | 3-stage (rim, confidence, NMS) | ⚠️ **Current drops brightness/annulus** |
| **Configuration** | YAML file, centralized | Python dicts, per-video hash cache | ✅ Current is more dynamic |

**Legend**: ✅ Current is better | ⚠️ Gap or tradeoff | ❌ Regression

---

## 1. Detection Architecture

### 1.1 Legacy: Dual-Path Detection

```
Frame → Preprocess → [Hough Path]    → Candidates ↘
                  ↘ [Contour Path]   → Candidates → Merge → Filter
```

**Legacy approach (from `processor.py`)**:
- **Path A: HoughCircles** — standard circle detection with dynamic radius constraints
- **Path B: Contour analysis** — Canny + morphology + minEnclosingCircle + circularity filter

**Critical insight**: Contour path catches circles that Hough misses (partial occlusions, low contrast, irregular edges). This is particularly valuable for:
- Motion-blurred beads (elongated, weak gradient)
- Partially visible beads at edges
- Beads with uneven illumination

### 1.2 Current: Single-Path Detection

```python
# src/detect.py - ONLY uses HoughCircles
circles = cv2.HoughCircles(
    gray,
    cv2.HOUGH_GRADIENT,
    dp=dp,
    minDist=min_dist,
    param1=param1,
    param2=param2,
    minRadius=min_radius,
    maxRadius=max_radius
)
```

**Critical gap**: No contour fallback. This means:
- **False negatives on low-contrast beads** — HoughCircles requires strong circular edges
- **Miss partial circles** — beads occluded at frame edges or by other beads
- **Single failure mode** — if Hough fails, entire detection fails

### 1.3 Recommendation: Implement Dual-Path

**Complexity**: Medium  
**Impact**: High (reduces false negatives)  
**Implementation hint from legacy**:

```python
# Legacy pattern worth adopting:
def contour_detection(gray, config):
    # Adaptive Canny thresholds
    otsu_thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_OTSU)[0]
    edges = cv2.Canny(gray, otsu_thresh * 0.5, otsu_thresh)
    
    # Morphological close to connect broken edges
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
    
    # Find and filter contours
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    for contour in contours:
        area = cv2.contourArea(contour)
        perimeter = cv2.arcLength(contour, True)
        circularity = 4 * np.pi * area / (perimeter ** 2) if perimeter > 0 else 0
        
        if circularity >= config["min_circularity"]:  # e.g., 0.7
            (x, y), radius = cv2.minEnclosingCircle(contour)
            yield Detection(x=int(x), y=int(y), r_px=radius)
```

---

## 2. Filtering Pipeline

### 2.1 Legacy: 4-Stage Filter

| Stage | Logic | Purpose |
|-------|-------|---------|
| 1. ROI Filter | `roi_mask[y, x] == 0 → reject` | Exclude outside drum |
| 2. Brightness Filter | `mean_patch < 50 → reject` | Reject dark holes/shadows |
| 3. Annulus Logic | Smaller circle centered inside larger → reject | Reject hollow bead inner holes |
| 4. NMS | Distance < 0.5*r and similar radius → suppress | Merge duplicates |

### 2.2 Current: 3-Stage Filter

| Stage | Logic | Purpose |
|-------|-------|---------|
| 1. Rim Margin | Distance from drum center > inner radius → reject | Exclude rim zone |
| 2. Confidence | `conf < 0.5 → reject` | Quality threshold |
| 3. NMS | Overlap > 50% of combined radii → suppress | Merge duplicates |

### 2.3 Critical Gaps

#### Missing: Brightness Filter
**Problem**: Without brightness rejection, dark artifacts (holes, shadows, bolt recesses) may pass through.

**Current workaround**: The confidence scoring's `interior_uniformity` component penalizes low-intensity interiors:
```python
# src/confidence.py
intensity_score = min(mean_int / 128.0, 1.0)
```
However, this is a soft penalty weighted at 20%, not a hard reject. A detection with mean intensity 30 gets:
- `intensity_score = 30/128 = 0.23`
- After 60% weight: `0.6 * 0.23 = 0.14`
- Still can pass if other features score high

**Recommendation**: Add explicit brightness hard-gate OR lower the interior weight threshold.

#### Missing: Annulus Logic
**Problem**: Hollow metallic beads (annular) create TWO circles—the outer perimeter and the inner hole. Without annulus rejection, both may be detected.

**Current behavior**: Both detections survive if confidence is high. NMS only suppresses if overlap is significant, but inner hole has different radius → no suppression.

**Legacy logic worth adopting**:
```python
# Legacy annulus rejection pattern
for i, det in enumerate(sorted_detections):  # sorted by radius DESC
    for j in range(i + 1, len(sorted_detections)):
        other = sorted_detections[j]
        dist = distance(det, other)
        
        # Inner circle test: smaller, close to center of larger
        if dist < det.r_px * 0.5 and other.r_px < det.r_px * 0.8:
            suppress(other)  # It's a hole inside this bead
```

**Complexity**: Low  
**Impact**: Medium (prevents double-counting hollow beads)

---

## 3. Confidence Scoring

### 3.1 Legacy: Flat Heuristic

```python
# Legacy simply assigned:
confidence = 0.8  # For all Hough detections
```

**Criticism**: No discrimination. Every detection is equally trusted. This pushes all quality control to the filter stage.

### 3.2 Current: Multi-Feature Scoring

```python
# src/confidence.py - SIGNIFICANT IMPROVEMENT
features = {
    "edge_strength": compute_edge_strength(grad_mag, x, y, r),      # 35%
    "circularity": compute_circularity(grad_mag, x, y, r),          # 25%
    "interior": compute_interior_uniformity(gray, x, y, r),         # 20%
    "radius_fit": compute_radius_fit(r, min_radius, max_radius),    # 20%
}
```

**Strengths**:
- Thresholdable and interpretable
- Per-feature diagnostics available
- Weighted combination allows tuning

**Critical assessment**: This is where the current codebase is **objectively superior**. The legacy's flat confidence provided no information.

**Potential improvement**: Add **glare penalty**. Currently, specular highlights can inflate `edge_strength` and `interior` scores because they create strong gradients. Consider:

```python
def compute_glare_penalty(gray, x, y, r):
    """Penalize detections with saturated pixels (glare)."""
    mask = np.zeros(gray.shape, dtype=np.uint8)
    cv2.circle(mask, (x, y), int(r), 255, -1)
    
    pixels = gray[mask > 0]
    saturated_ratio = np.sum(pixels > 250) / len(pixels)
    
    return max(0, 1.0 - saturated_ratio * 2)  # Heavy penalty for glare
```

---

## 4. Video Decoding & Frame Indexing

### 4.1 Legacy: PyAV with PTS-Based Indexing

```python
# Legacy FrameLoader
import av

container = av.open(video_path)
for frame in container.decode(video=0):
    pts = frame.pts
    time_base = stream.time_base
    current_idx = round((pts * time_base) * fps)
```

**Advantages**:
- **Frame-accurate seeking**: PTS-based indexing survives variable frame rates
- **Rotation metadata**: Explicit handling of `rotate` tag and `DISPLAYMATRIX`
- **Seek stability**: Pre-roll frames skipped until target reached

### 4.2 Current: OpenCV VideoCapture

```python
# ui/video_controller.py
self._cap = cv2.VideoCapture(video_path)
self._cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
ret, frame = self._cap.read()
```

**Known issues with OpenCV**:
- **Frame drift**: `CAP_PROP_POS_FRAMES` is approximate for some codecs
- **Seek inaccuracy**: Seeking may land on nearest keyframe, not exact frame
- **No rotation handling visible**: Mobile-recorded videos may appear sideways

### 4.3 Critical Gap

**Test**: Try seeking to frame 1000, then compare with sequential read to frame 1000. If they differ, there's drift.

**Recommendation**: 
1. Validate frame accuracy on test videos (MOV from iPhone, MP4 from DSLR)
2. If drift found, consider PyAV integration OR implement keyframe-based seeking with sequential decode to target

---

## 5. Cache Architecture

### 5.1 Legacy: JSONL (Append-Only)

```
# cache file: detections.jsonl
{"frame_id": 0, "timestamp": 0.0, "balls": [...]}
{"frame_id": 1, "timestamp": 0.033, "balls": [...]}
...
```

**Properties**:
- Append-only: Each frame written as it's processed
- Crash-tolerant: Partial processing recovers
- Streamable: Can read while writing

### 5.2 Current: Structured JSON

```json
{
  "metadata": {...},
  "config": {...},
  "frames": {
    "0": {"detections": [...]},
    "42": {"detections": [...]}
  }
}
```

**Properties**:
- Atomic write: Entire file written at once
- Human-readable hierarchy
- Fast random access (dict lookup)
- **NOT crash-tolerant**: Crash during write = data loss

### 5.3 Tradeoff Analysis

| Property | JSONL (Legacy) | JSON (Current) |
|----------|----------------|----------------|
| Crash recovery | ✅ Partial data preserved | ❌ Lost on crash |
| Append during processing | ✅ Yes | ❌ No (must hold in memory) |
| Random access speed | ⚠️ Requires index or scan | ✅ O(1) dict lookup |
| File size overhead | ⚠️ Slightly larger (repeated keys) | ✅ Compact |
| Readability | ⚠️ Line-by-line | ✅ Full structure |

**Recommendation**: For production, consider hybrid:
1. During processing: Write JSONL incrementally
2. On completion: Convert to structured JSON for playback
3. On load: Check for incomplete JSONL and resume

---

## 6. Overlay Rendering

### 6.1 Legacy: Shared OverlayRenderer

```python
# Legacy pattern
renderer = OverlayRenderer(config)

# Used in UI playback
widget.draw_overlay(frame, detections, renderer)

# Used in export
exporter.write_frame_with_overlay(frame, detections, renderer)
```

**Advantage**: UI and export produce **identical** visuals. What you see is what you export.

### 6.2 Current: Context-Specific Rendering

```python
# UI rendering happens in main_window.py
# Export rendering (if implemented) would be separate
```

**Risk**: Visual discrepancy between UI preview and exported video.

**Recommendation**: If export functionality is added, ensure shared rendering logic OR pixel-accurate matching tests.

---

## 7. ROI System Comparison

### 7.1 Legacy

- **Interactive circle tool** with drag-to-move, drag-rim-to-resize
- **Auto-detection via HoughCircles** as initial guess
- **Saved as grayscale PNG**: white (255) = valid, black (0) = ignored
- **Filter checks center point only**: `roi_mask[y, x] == 0 → reject`

### 7.2 Current

- **Drum geometry auto-detection** with hash-based caching
- **ROI mask generation** from DrumGeometry
- **Rim margin filter** uses distance calculation, not mask lookup

### 7.3 Critical Difference

Legacy checks ROI via pixel lookup on a saved mask image.  
Current computes distance from drum center each time.

**Current is slightly faster** (avoids mask generation) but **less flexible** (can't define non-circular ROI).

**Recommendation**: Current approach is fine for circular drums. If arbitrary ROI shapes are needed, adopt legacy mask system.

---

## 8. Summary: Features to Consider Adopting

### High Priority (Significant Impact)

| Feature | From | Effort | Impact |
|---------|------|--------|--------|
| Dual-path detection (Hough + Contour) | Legacy | Medium | High |
| Annulus rejection (inner-hole suppression) | Legacy | Low | Medium |
| Brightness hard-gate filter | Legacy | Low | Medium |
| Glare penalty in confidence scoring | New | Low | Medium |

### Medium Priority (Polish/Robustness)

| Feature | From | Effort | Impact |
|---------|------|--------|--------|
| JSONL crash-tolerant caching during processing | Legacy | Medium | Medium |
| Rotation metadata handling | Legacy | Low | Low-Medium |
| Frame-accurate seeking validation | New | Low | Low |

### Low Priority (Nice-to-Have)

| Feature | From | Effort | Impact |
|---------|------|--------|--------|
| Shared OverlayRenderer for UI/Export parity | Legacy | Medium | Low |
| Interactive ROI circle tool | Legacy | High | Low |

---

## 9. Architectural Divergence Summary

### What Current Does Better

1. **Confidence scoring** — Multi-feature, interpretable, thresholdable
2. **Per-video geometry caching** — No manual config per video
3. **Clean separation** — STEP-based modules with clear responsibilities
4. **Metrics framework** — Built-in quality report generation
5. **Configuration exposure** — All parameters in `config.py`, no magic numbers

### What Legacy Does Better

1. **Detection robustness** — Dual-path catches more beads
2. **Filter completeness** — Brightness and annulus logic
3. **Cache resilience** — JSONL survives crashes
4. **Frame accuracy** — PyAV + PTS-based indexing
5. **Rotation handling** — Explicit metadata parsing

---

## 10. Recommended Action Items

### Immediate (Before Next Release)

1. [ ] **Add contour detection fallback** — Merge candidates from both paths
2. [ ] **Implement annulus rejection** — Suppress inner holes of hollow beads
3. [ ] **Validate frame seeking accuracy** — Test on various video formats

### Near-Term (Next Sprint)

4. [ ] **Add brightness hard-gate** — Reject mean intensity < 40
5. [ ] **Implement glare penalty** — Add to confidence scoring
6. [ ] **JSONL incremental write** — During processing, convert to JSON on completion

### Backlog

7. [ ] **PyAV integration** — If frame drift is confirmed
8. [ ] **Rotation metadata parsing** — Handle mobile-recorded videos
9. [ ] **Shared overlay renderer** — If export feature is added

---

## Appendix: Code Cross-Reference

| Component | Legacy Location | Current Location |
|-----------|-----------------|------------------|
| Detection | `core/processor.py` | [src/detect.py](../../src/detect.py) |
| Filtering | `core/processor.py` (inline) | [src/filter.py](../../src/filter.py) |
| Confidence | `core/processor.py` (flat 0.8) | [src/confidence.py](../../src/confidence.py) |
| Classification | `core/processor.py` | [src/classify.py](../../src/classify.py) |
| Caching | `core/cache.py` (JSONL) | [src/cache.py](../../src/cache.py) (JSON) |
| Video decoding | `core/playback.py` (PyAV) | [ui/video_controller.py](../../ui/video_controller.py) (OpenCV) |
| Overlay | `core/overlay.py` (shared) | (inline in UI components) |
| ROI | `ui/roi_controller.py` | [src/drum.py](../../src/drum.py) |

---

*This document is intended for PM/Architect review to inform backlog prioritization.*
