# Tuning Log

Record of vision parameter experiments. Update after each tuning session.

---

## 2025-12-03 - Baseline (Current Config)

**Config:** `configs/sample.config.yaml`

| Parameter | Value | Notes |
|-----------|-------|-------|
| `calibration.px_per_mm` | 4.128 | Set via Calibrate tool |
| `vision.hough_param1` | 40 | Canny high threshold |
| `vision.hough_param2` | 25 | Accumulator threshold (lower = more circles) |
| `vision.min_circularity` | 0.7 | Contour filter threshold |
| `vision.min_dist_px` | 12 | Min distance between circle centers |
| Brightness threshold | 50 | Hardcoded in processor.py |

**Observations:** Pending visual checklist verification.

---

## Template for Future Entries

```
## YYYY-MM-DD - [What was tuned]

**Goal:** [What problem are we solving?]

| Parameter | Old | New | Result |
|-----------|-----|-----|--------|
| param_name | X | Y | ✅/❌ Description |

**Conclusion:** [Keep/revert? Why?]
```
