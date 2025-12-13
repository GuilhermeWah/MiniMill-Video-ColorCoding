# STEP_05: Confidence Scoring - Full Analysis Document

**Date**: 2025-12-12  
**Author**: Claude Opus 4.5 (Developer Agent)  
**Status**: Implementation Complete, PM Review Pending

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Algorithm Design](#algorithm-design)
3. [Feature Definitions](#feature-definitions)
4. [Implementation Details](#implementation-details)
5. [Test Results](#test-results)
6. [Per-Video Analysis](#per-video-analysis)
7. [Reliability Assessment](#reliability-assessment)
8. [Known Limitations](#known-limitations)
9. [Recommendations](#recommendations)
10. [Appendix: Raw Data](#appendix-raw-data)

---

## Executive Summary

STEP_05 implements confidence scoring for bead detections. The system assigns a score ∈ [0.0, 1.0] to each detection based on observable image evidence, enabling downstream filtering and quality assessment.

### Key Metrics

| Metric | Value |
|--------|-------|
| Total detections scored | 14,234 |
| Global mean confidence | 0.495 |
| Global std deviation | 0.142 |
| Global range | [0.085, 0.938] |
| High confidence (≥0.7) | 1,660 (11.7%) |
| Processing time | ~1-3 sec/frame |

### Verdict

✅ **Confidence scoring works as designed**. It successfully separates beads from noise in most cases. The system is deterministic, thresholdable, and provides meaningful ranking. Some resolution-specific tuning may improve 4K video performance.

---

## Algorithm Design

### Core Principle

Confidence is computed from **observable image evidence only**, without using any calibration values (px_per_mm). This ensures:

1. **Determinism**: Same input → same score
2. **Calibration independence**: Changing px_per_mm does NOT affect confidence
3. **Thresholdability**: Users can filter by minimum confidence
4. **Comparability**: Scores are consistent across frames and videos

### Formula

```
confidence = Σ(weight_i × feature_i)

where:
  - weight_edge_strength = 0.35
  - weight_circularity = 0.25
  - weight_interior = 0.20
  - weight_radius_fit = 0.20
  - Σ weights = 1.0
```

### Design Rationale

| Feature | Weight | Rationale |
|---------|--------|-----------|
| Edge Strength | 35% | Primary signal: real beads have defined edges |
| Circularity | 25% | Distinguishes complete circles from partial artifacts |
| Interior Uniformity | 20% | Metallic beads have characteristic brightness pattern |
| Radius Fit | 20% | Expected sizes get preference over outliers |

---

## Feature Definitions

### Feature 1: Edge Strength (weight: 0.35)

**Purpose**: Measure how strong the gradient is along the circle perimeter.

**Algorithm**:
```python
def compute_edge_strength(grad_mag, x, y, r, n_points=36):
    # Sample 36 points around circumference
    angles = np.linspace(0, 2π, n_points, endpoint=False)
    
    for angle in angles:
        px = x + r * cos(angle)
        py = y + r * sin(angle)
        samples.append(grad_mag[py, px])
    
    # Normalize: typical edge gradient ~50-150, saturate at 150
    avg_grad = mean(samples)
    return min(avg_grad / 150.0, 1.0)
```

**Interpretation**:
- 1.0 = Strong, well-defined edge (≥150 gradient magnitude)
- 0.5 = Moderate edge (~75 gradient magnitude)
- 0.0 = No edge detected

**Observed Behavior**:
- Often saturates at 1.0 for real beads
- Glare edges also score high (limitation)
- Empty dark areas score low (correct)

---

### Feature 2: Circularity (weight: 0.25)

**Purpose**: Measure edge consistency around the full perimeter.

**Algorithm**:
```python
def compute_circularity(grad_mag, x, y, r, n_points=36):
    # Same 36 sample points as edge strength
    samples = [grad_mag at each point]
    
    # Coefficient of variation
    cv = std(samples) / mean(samples)
    
    # Lower variance = better circularity
    return max(0, 1.0 - cv)
```

**Interpretation**:
- 1.0 = Perfectly uniform edge all around
- 0.5 = Moderate variance (partial edge)
- 0.0 = Highly inconsistent (edge only on one side)

**Observed Behavior**:
- Real beads: 0.3-0.6 (some natural variance)
- Partial artifacts: 0.1-0.3
- Strong edges have lower circularity (variance amplified)

---

### Feature 3: Interior Uniformity (weight: 0.20)

**Purpose**: Analyze if the inside of the circle looks like a metallic bead.

**Algorithm**:
```python
def compute_interior_uniformity(gray, x, y, r, sample_ratio=0.7):
    # Sample pixels within 70% of radius
    inner_r = r * 0.7
    interior_pixels = gray[inside circle of inner_r]
    
    mean_int = mean(interior_pixels)
    std_int = std(interior_pixels)
    
    # Metallic beads: moderate-high intensity
    intensity_score = min(mean_int / 128.0, 1.0)
    
    # Optimal variance: 20-50 (not too uniform, not too noisy)
    if std_int < 10:
        variance_score = std_int / 10.0  # Too uniform
    elif std_int > 60:
        variance_score = max(0, 1.0 - (std_int - 60) / 60.0)  # Too noisy
    else:
        variance_score = 1.0  # Good range
    
    return 0.6 * intensity_score + 0.4 * variance_score
```

**Interpretation**:
- 1.0 = Bright with moderate texture (ideal bead)
- 0.5 = Either dim or too uniform/noisy
- 0.0 = Very dark or extremely noisy

**Observed Behavior**:
- Beads in lit areas: 0.7-0.9
- Dark empty areas: 0.3-0.5
- Glare spots: variable (can be high)

---

### Feature 4: Radius Fit (weight: 0.20)

**Purpose**: Score how well the detected radius matches expected bead sizes.

**Algorithm**:
```python
def compute_radius_fit(r, min_radius, max_radius):
    range_size = max_radius - min_radius
    
    # Optimal zone: middle 60% of range
    optimal_min = min_radius + range_size * 0.2
    optimal_max = max_radius - range_size * 0.2
    
    if optimal_min <= r <= optimal_max:
        return 1.0
    elif r < min_radius or r > max_radius:
        return 0.0
    elif r < optimal_min:
        return (r - min_radius) / (optimal_min - min_radius)
    else:
        return (max_radius - r) / (max_radius - optimal_max)
```

**Interpretation**:
- 1.0 = Radius in optimal zone (20%-80% of range)
- 0.5 = At edge of valid range
- 0.0 = Outside valid range

**Observed Behavior**:
- Most detections at r=max_radius get ~0.1 (edge of range)
- Mid-range radii get 1.0
- This feature provides size regularization

---

## Implementation Details

### Files Created

| File | Purpose | Lines |
|------|---------|-------|
| `src/confidence.py` | Main scoring module | ~380 |
| `src/step05_confidence.py` | Test script | ~220 |
| `src/config.py` (updated) | Added CONFIDENCE_CONFIG | +20 |

### Configuration

```python
CONFIDENCE_CONFIG = {
    # Feature weights (sum to 1.0)
    "weight_edge_strength": 0.35,
    "weight_circularity": 0.25,
    "weight_interior": 0.20,
    "weight_radius_fit": 0.20,
    
    # Edge sampling parameters
    "edge_sample_points": 36,        # Points around circumference
    "edge_gradient_sigma": 1.0,      # Gaussian sigma for gradient
    
    # Interior analysis
    "interior_sample_ratio": 0.7,    # Sample within 70% of radius
    
    # Radius fit scoring
    "radius_fit_optimal_min": 0.2,   # Optimal starts at 20% into range
    "radius_fit_optimal_max": 0.8,   # Optimal ends at 80% of range
}
```

### Performance Optimization

The initial implementation computed gradients per-detection, which was slow (~1000 detections × Sobel operation = very slow).

**Optimization applied**: Precompute gradient magnitude ONCE per frame, then reuse for all detections.

```python
def score_detections(gray, detections, ...):
    # Compute gradient ONCE
    grad_mag = precompute_gradient(gray)
    
    for det in detections:
        # Reuse grad_mag for each detection
        score_detection(gray, grad_mag, det, ...)
```

Result: ~10-50x speedup depending on detection count.

---

## Test Results

### Global Statistics

| Metric | Value |
|--------|-------|
| Total frames processed | 18 |
| Total detections scored | 14,234 |
| Mean confidence | 0.4953 |
| Std deviation | 0.1417 |
| Minimum | 0.0848 |
| Maximum | 0.9377 |

### Confidence Distribution

| Range | Count | Percentage | Interpretation |
|-------|-------|------------|----------------|
| [0.0 - 0.2) | 39 | 0.3% | Very low (clear noise) |
| [0.2 - 0.4) | 3,519 | 24.7% | Low (likely noise) |
| [0.4 - 0.6) | 8,103 | 56.9% | Medium (borderline) |
| [0.6 - 0.8) | 1,638 | 11.5% | High (likely beads) |
| [0.8 - 1.0) | 935 | 6.6% | Very high (strong beads) |

### Distribution Visualization

```
[0.0-0.2) ▏ 0.3%
[0.2-0.4) ████████ 24.7%
[0.4-0.6) ██████████████████████ 56.9%
[0.6-0.8) ████ 11.5%
[0.8-1.0) ██ 6.6%
```

---

## Per-Video Analysis

### IMG_6535 (4K, 3840×2160)

| Frame | Candidates | High | Med | Low | Mean | Max |
|-------|------------|------|-----|-----|------|-----|
| 0 | 965 | 0 | 795 | 170 | 0.448 | 0.645 |
| 100 | 1,350 | 0 | 1,126 | 224 | 0.450 | 0.631 |
| 171 | 1,338 | 0 | 1,056 | 282 | 0.443 | 0.632 |
| 343 | 765 | 0 | 630 | 135 | 0.450 | 0.639 |
| 514 | 1,074 | 0 | 921 | 153 | 0.455 | 0.645 |
| 676 | 998 | 0 | 823 | 175 | 0.452 | 0.675 |
| **Total** | **6,490** | **0** | **5,351** | **1,139** | **0.450** | **0.675** |

**Observations**:
- ❌ No detections reach high confidence (max 0.675)
- Consistent mean ~0.45 across all frames
- 4K gradient magnitudes may need different normalization
- Beads ARE being detected, but scores compressed into medium range

**Visual Assessment**:
- Yellow/orange circles on actual beads (correct relative ranking)
- Red circles on empty areas (correct)
- No green circles (score ceiling issue)

---

### IMG_1276 (1080p, 1920×1080)

| Frame | Candidates | High | Med | Low | Mean | Max |
|-------|------------|------|-----|-----|------|-----|
| 0 | 337 | 316 | 21 | 0 | 0.814 | 0.913 |
| 100 | 306 | 291 | 15 | 0 | 0.819 | 0.938 |
| 1844 | 241 | 214 | 27 | 0 | 0.791 | 0.918 |
| 3689 | 203 | 128 | 73 | 2 | 0.714 | 0.906 |
| 5534 | 228 | 144 | 80 | 4 | 0.720 | 0.893 |
| 7369 | 276 | 252 | 24 | 0 | 0.803 | 0.930 |
| **Total** | **1,591** | **1,345** | **240** | **6** | **0.777** | **0.938** |

**Observations**:
- ✅ 85% of detections are high confidence
- Excellent separation: almost no low-confidence detections
- Mean confidence 0.777 - highest of all videos
- Clear, well-lit video with good bead visibility

**Visual Assessment**:
- Green circles on beads (correct)
- Few yellow circles (edge cases)
- Almost no red circles (very clean)
- Rim bolts correctly excluded or low-confidence

---

### DSC_3310 (1080p, 1920×1080)

| Frame | Candidates | High | Med | Low | Mean | Max |
|-------|------------|------|-----|-----|------|-----|
| 0 | 3,351 | 75 | 1,339 | 1,937 | 0.418 | 0.874 |
| 100 | 644 | 79 | 445 | 120 | 0.550 | 0.835 |
| 944 | 517 | 27 | 421 | 69 | 0.529 | 0.808 |
| 1888 | 553 | 23 | 452 | 78 | 0.509 | 0.814 |
| 2832 | 550 | 16 | 418 | 116 | 0.490 | 0.782 |
| 3767 | 538 | 95 | 350 | 93 | 0.569 | 0.843 |
| **Total** | **6,153** | **315** | **3,425** | **2,413** | **0.511** | **0.874** |

**Observations**:
- ⚠️ Frame 0 is an outlier: 3,351 candidates (5-6x normal)
- Mixed results: some high confidence, many low
- Purple inner ring generates false positives
- Excluding frame 0: more reasonable candidate counts

**Visual Assessment**:
- Frame 0: Massive over-detection (HoughCircles issue, not confidence)
- Other frames: Yellow on beads, red on empty areas
- Purple ring artifacts get medium confidence (challenging)

---

## Reliability Assessment

### What's Working Well ✅

| Capability | Evidence |
|------------|----------|
| **Separates beads from empty space** | IMG_1276: 85% high-conf on beads, <1% low-conf |
| **Penalizes rim/bolts** | Rim bolts consistently score low |
| **Penalizes noise in dark areas** | Red circles on empty drum interior |
| **Deterministic** | Verified: same input → same score |
| **Thresholdable** | 0.7 threshold retains 1,660 high-quality detections |
| **Per-feature breakdown** | JSON exports include individual feature scores |

### Threshold Recommendations

| Threshold | Retained | Percentage | Use Case |
|-----------|----------|------------|----------|
| 0.8 | 935 | 6.6% | High precision, may miss beads |
| 0.7 | 1,660 | 11.7% | Balanced (recommended) |
| 0.6 | 2,573 | 18.1% | Higher recall |
| 0.5 | 5,701 | 40.1% | Permissive |
| 0.4 | 10,695 | 75.1% | Very permissive |

---

## Known Limitations

### 1. 4K Video Score Compression

**Symptom**: IMG_6535 (4K) has no detections above 0.675  
**Cause**: Gradient normalization fixed at 150, but 4K images may have different gradient scales  
**Impact**: All 4K detections appear yellow, none green  
**Mitigation**: Resolution-adaptive normalization (optional tuning)

```python
# Potential fix:
norm_factor = 150 * sqrt(height / 1080)  # Scale with resolution
```

### 2. Frame 0 Anomaly (DSC_3310)

**Symptom**: 3,351 candidates vs ~500 for other frames  
**Cause**: HoughCircles over-detection, not confidence scoring issue  
**Impact**: Many low-confidence false positives  
**Mitigation**: STEP_06 filtering will clean this up

### 3. Purple Ring False Positives

**Symptom**: Medium confidence (0.4-0.6) on drum's inner purple ring  
**Cause**: Ring has real circular edges → triggers edge features  
**Impact**: Some false positives persist after confidence filtering  
**Mitigation**: STEP_06 rim margin filter will exclude this zone

### 4. Edge Strength Saturation

**Symptom**: Many detections have edge_strength = 1.0  
**Cause**: Normalization ceiling at 150 gradient magnitude  
**Impact**: Less discrimination among high-edge detections  
**Mitigation**: Could use higher normalization or percentile-based scaling

### 5. Glare Can Score Medium-High

**Symptom**: Bright glare spots sometimes get 0.5-0.6 confidence  
**Cause**: Glare has high intensity (interior feature) and some edges  
**Impact**: Some glare artifacts pass filtering  
**Mitigation**: Could add specific glare detection feature

---

## Recommendations

### Immediate (STEP_06)

1. **Apply rim margin filter**: Remove detections in outer 10-15% of drum radius
2. **Apply confidence threshold**: Start with 0.6, adjust based on results
3. **Apply NMS**: Non-maximum suppression for overlapping detections

### Optional Tuning

1. **Resolution-adaptive gradient normalization**:
   ```python
   norm_factor = 150 * sqrt(height / 1080)
   ```

2. **Adjust circularity weight**: Currently penalizes high-variance edges; may need tuning

3. **Add glare detection feature**: Could detect and penalize bright saturated regions

### Future Considerations

1. **Confidence calibration**: Map scores to actual precision (requires ground truth)
2. **Temporal smoothing**: Average confidence across frames for stability
3. **Size-specific thresholds**: Different thresholds for different bead sizes

---

## Appendix: Raw Data

### Output Files Generated

```
output/confidence_test/
├── confidence_manifest.json
├── DSC_3310_frame_0_confidence.png
├── DSC_3310_frame_0_scored.json
├── DSC_3310_frame_100_confidence.png
├── DSC_3310_frame_100_scored.json
├── DSC_3310_frame_944_confidence.png
├── DSC_3310_frame_944_scored.json
├── DSC_3310_frame_1888_confidence.png
├── DSC_3310_frame_1888_scored.json
├── DSC_3310_frame_2832_confidence.png
├── DSC_3310_frame_2832_scored.json
├── DSC_3310_frame_3767_confidence.png
├── DSC_3310_frame_3767_scored.json
├── IMG_1276_frame_0_confidence.png
├── IMG_1276_frame_0_scored.json
├── IMG_1276_frame_100_confidence.png
├── IMG_1276_frame_100_scored.json
├── IMG_1276_frame_1844_confidence.png
├── IMG_1276_frame_1844_scored.json
├── IMG_1276_frame_3689_confidence.png
├── IMG_1276_frame_3689_scored.json
├── IMG_1276_frame_5534_confidence.png
├── IMG_1276_frame_5534_scored.json
├── IMG_1276_frame_7369_confidence.png
├── IMG_1276_frame_7369_scored.json
├── IMG_6535_frame_0_confidence.png
├── IMG_6535_frame_0_scored.json
├── IMG_6535_frame_100_confidence.png
├── IMG_6535_frame_100_scored.json
├── IMG_6535_frame_171_confidence.png
├── IMG_6535_frame_171_scored.json
├── IMG_6535_frame_343_confidence.png
├── IMG_6535_frame_343_scored.json
├── IMG_6535_frame_514_confidence.png
├── IMG_6535_frame_514_scored.json
├── IMG_6535_frame_676_confidence.png
└── IMG_6535_frame_676_scored.json
```

### Sample Detection JSON Format

```json
{
  "video": "IMG_1276",
  "frame_idx": 0,
  "total_candidates": 337,
  "high_confidence": 316,
  "medium_confidence": 21,
  "low_confidence": 0,
  "mean_confidence": 0.8137,
  "std_confidence": 0.0615,
  "config_used": {
    "weight_edge_strength": 0.35,
    "weight_circularity": 0.25,
    "weight_interior": 0.2,
    "weight_radius_fit": 0.2,
    "edge_sample_points": 36,
    "edge_gradient_sigma": 1.0,
    "interior_sample_ratio": 0.7,
    "radius_fit_optimal_min": 0.2,
    "radius_fit_optimal_max": 0.8
  },
  "detections": [
    {
      "x": 840,
      "y": 454,
      "r_px": 31.4,
      "conf": 0.641,
      "features": {
        "edge_strength": 1.0,
        "circularity": 0.376,
        "interior": 0.885,
        "radius_fit": 0.103
      }
    }
    // ... more detections
  ]
}
```

### Geometry Parameters Used

| Video | Resolution | Drum Radius (px) | Min Bead R (px) | Max Bead R (px) | px_per_mm |
|-------|------------|------------------|-----------------|-----------------|-----------|
| IMG_6535 | 3840×2160 | 872 | 9 | 78 | 8.72 |
| IMG_1276 | 1920×1080 | 365 | 4 | 33 | 3.65 |
| DSC_3310 | 1920×1080 | 496 | 5 | 45 | 4.96 |

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-12 | Claude Opus 4.5 | Initial document |

---

*End of STEP_05 Confidence Analysis Document*
