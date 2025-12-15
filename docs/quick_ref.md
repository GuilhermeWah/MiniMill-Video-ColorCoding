# Quick Reference

## Commands

### Run Detection (Offline)
```powershell
python scripts/run_detection.py --input content/DSC_1276.MOV --output exports/detections.jsonl --config configs/sample.config.yaml
```

### Run UI Player
```powershell
python -m mill_presenter.app --video content/DSC_1276.MOV --detections exports/detections.jsonl --config configs/sample.config.yaml
```

### Run Tests
```powershell
pytest tests/
pytest tests/test_processor.py -v  # Single file
```

---

## Key Paths

| Purpose | Path |
|---------|------|
| Config | `configs/sample.config.yaml` |
| ROI Mask | `exports/roi_mask.png` |
| Detections | `exports/detections.jsonl` |
| Video | `content/DSC_1276.MOV` |

---

## Key Config Values

| Setting | Location | Effect |
|---------|----------|--------|
| `calibration.px_per_mm` | YAML | Converts pixels to mm for classification |
| `vision.hough_param2` | YAML | Lower = more circles (sensitivity) |
| `vision.min_circularity` | YAML | Lower = accept less circular shapes |
| `brightness_threshold` | `processor.py:133` | Lower = reject fewer dark areas |

---

## Workflow Reminders

1. **After changing ROI:** Re-run detection
2. **After changing calibration:** Re-run detection
3. **After tuning vision params:** Re-run detection
4. **Toggles in UI:** Never re-run detection (instant)
