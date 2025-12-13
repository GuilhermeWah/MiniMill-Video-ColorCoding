# Project Glossary

## Purpose
Define an unambiguous vocabulary for the project.
This file prevents semantic drift across agents, time, and reviews.

---

## Core Terms

### Bead
A metallic grinding media element visible inside the rotating mill.
Beads may be **solid or hollow (annular)**.

### Hollow / Annular Bead
A bead with a visible inner hole.
Detection must consider the **outer diameter only**.
The inner hole must never be detected or classified as a bead.

### Detection
The act of locating bead candidates **in pixel space**.
Outputs `(x, y, r_px, confidence)`.
Detection is **independent of calibration**.

### Classification
Mapping a detected bead to a size class (4 / 6 / 8 / 10 mm)
using `px_per_mm` and real bead diameters.
Classification must not affect detection.

### px_per_mm
Pixels-per-millimeter calibration factor.
Used **only after detection** for:
- diameter conversion
- class assignment
- optional rendering

### Window
A contiguous set of frames used for evaluation (e.g. 300 frames).

### Cycle
One physical rotation of the drum, or a fixed-length proxy window.

### Bad Frame
A frame degraded by blur, glare, occlusion, or invalid statistics.
Bad frames are expected and allowed.

### Confidence
A scalar value `[0,1]` expressing detection reliability.
Confidence affects **visualization only**, not detection logic.

---

End of Project Glossary