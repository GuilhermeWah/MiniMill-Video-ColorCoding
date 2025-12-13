# Data Contracts

## Purpose
Define stable data structures exchanged between pipeline stages.
This file prevents silent schema drift and misinterpretation.

---

## Detection Output (Pixel Space)

### BallDetection
```yaml
x: int            # pixel

y: int            # pixel

r_px: float       # radius in pixels

confidence: float # [0.0, 1.0]
```

Invariants:
- Coordinates are pixel-based
- Radius refers to outer bead radius
- No millimeter units allowed here

---

## Classified Detection

### ClassifiedBall
```yaml
detection: BallDetection

diameter_mm: float

class_label: one of [4, 6, 8, 10]
```

Invariants:
- `diameter_mm` is derived using `px_per_mm`
- Classification must not modify detection geometry

---

## Frame-Level Output

### FrameDetections
```yaml
frame_id: int

timestamp: float

balls: list[ClassifiedBall]
```

---

## Visualization Contract

- Visualization may filter or fade detections by confidence
- Visualization must not modify detection or classification results

---

End of Data Contracts