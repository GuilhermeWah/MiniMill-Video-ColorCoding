# Visual Acceptance Checklist

Run this after any detection tuning, ROI change, or calibration update.

---

## Per-Frame Checks

- [ ] Each physical bead has **one** overlay circle (no Hough+Contour duplicates)
- [ ] Large annular beads do NOT show an extra "inner small bead" at the hole
- [ ] No circles on bolts, flange, wheels, or outside the drum
- [ ] No circles on the moving holes in the drum background
- [ ] Circles are reasonably centered on beads (not wildly offset)
- [ ] Under glare, circles follow the outer metallic ring, not highlight streaks
- [ ] In dense piles, circles are not exploding into many tiny false detections

---

## Interaction Checks

- [ ] Toggling 4/6/8/10mm is instant (no lag, no stutter)
- [ ] Scrubbing (slider drag) keeps overlays in sync with video
- [ ] Zoom (scroll wheel) works smoothly
- [ ] Pan (drag) works when zoomed in
- [ ] Play/Pause transitions are smooth

---

## Export Check

- [ ] Exported MP4 matches live UI exactly (same circles, same colors)
- [ ] ROI mask is respected in export (no circles in masked areas)

---

## Sign-Off

| Date | Video File | Passed | Notes |
|------|------------|--------|-------|
| YYYY-MM-DD | filename.MOV | ✅/❌ | Any issues |
