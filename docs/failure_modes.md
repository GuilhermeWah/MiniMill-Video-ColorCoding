# Failure Modes

## Purpose
Explicitly document known and unavoidable failure cases.
This legitimizes limitations and prevents endless tuning loops.

---

## Known Failure Modes

### Motion Blur Streaks
At high RPM or slow shutter speeds, beads become arcs or streaks.
Circular geometry assumptions break.
Detection recall drops by design.

---

### High-Density Small Beads (4 mm)
Small beads may visually merge into metallic texture.
Edges disappear and circularity collapses.
Low recall is inevitable in these regions.

---

### Specular False Annuli
Reflections or bead pairs may create false ring patterns.
Inner/outer edge logic may fail locally.
Produces occasional false positives.

---

### Extreme Occlusion
Multiple beads touching or overlapping completely.
Separation algorithms may under-segment or over-segment.

---

### Calibration Drift Misinterpretation
Incorrect `px_per_mm` affects classification and rendering.
Must never affect detection geometry.

---

## Engineering Stance
- These failures are **expected**
- They do not invalidate the pipeline
- Acceptance is evaluated statistically, not per-frame

---

End of Failure Modes