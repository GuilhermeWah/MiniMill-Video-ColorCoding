# KNOWN_ISSUES.md

## Authority
This document is subordinate to `MAIN.md`
and `CURRENT_STEP.md`,
but has higher authority than agent reasoning.

If an agent proposal contradicts this file,
the agent must stop and request PM clarification.

---

## ISSUE_001: Video Scrubbing Latency (H.264/HEVC Keyframe Seeking)

**Date Identified:** 2025-12-12  
**Severity:** Medium  
**Status:** Open  
**Affects:** STEP_09 (Visualization & Playback)

### Description
Random seeks in compressed video (H.264/HEVC) are slow due to keyframe-based compression. The decoder must seek to the nearest keyframe and decode forward to the target frame.

### Measurements (IMG_1276.MOV - 240fps, 7379 frames)
| Seek Distance | Latency | User Experience |
|---------------|---------|-----------------|
| Sequential playback | 5-7ms | ✅ Smooth |
| Small jump (100 frames) | 120-370ms | Noticeable lag |
| Medium jump (2000 frames) | 300-400ms | Annoying |
| Large jump (5000+ frames) | 600-730ms | Very stuttery |

### Impact
- Normal playback: **NOT affected** (sequential decode is fast)
- Toggle feature: **NOT affected** (0.1ms overhead)
- User scrubbing timeline: **AFFECTED** (600ms+ delays)

### Root Cause
Video codecs (H.264/HEVC) use inter-frame compression. Only keyframes (I-frames) can be decoded independently. Seeking to frame N requires:
1. Find nearest keyframe before N
2. Decode all frames from keyframe to N
3. Display frame N

### Potential Mitigations
1. **Thumbnail strip** - Pre-generate thumbnails at intervals for instant scrub preview
2. **Keyframe index** - Pre-scan for keyframes, seek to nearest, bound worst-case latency
3. **Low-res proxy** - Generate 360p proxy video for scrubbing, swap to full-res on play
4. **All-intra encode** - Re-encode source video with all keyframes (large file size)

### Decision Required
- ~~Is scrubbing UX in scope for MVP?~~ **YES** (PM confirmed 2025-12-12)
- ~~If yes, which mitigation approach?~~ **Deferred to STEP_09**

### Related
- Does NOT affect detection pipeline (offline processing)
- Does NOT affect cache/overlay architecture
- Player/UI layer concern only

---

## ISSUE_002: Video Rotation Metadata (iPhone Landscape Recording)

**Date Identified:** 2025-12-12  
**Severity:** Low (not observed in test videos)  
**Status:** Deferred  
**Affects:** STEP_01 (Drum Geometry)

### Description
iPhone videos may contain rotation metadata (90°, 180°, 270°) when recorded in portrait orientation but played as landscape. If OpenCV doesn't auto-apply rotation, the detected drum geometry would be applied to incorrectly oriented frames.

### Current Status
All 3 test videos show NO discrepancy between metadata dimensions and actual frame dimensions:
- IMG_6535.MOV: 3840x2160 metadata = 3840x2160 actual ✅
- IMG_1276.MOV: 1920x1080 metadata = 1920x1080 actual ✅
- DSC_3310.MOV: 1920x1080 metadata = 1920x1080 actual ✅

### Potential Impact
If a rotated video is processed:
- Drum detected at (590, 395) for "1920x1080"
- But actual frame data is 1080x1920 (portrait)
- ROI mask would be completely wrong

### Recommended Mitigation
Add validation check in STEP_01:
```python
# Compare metadata WxH vs actual frame WxH
if metadata_width != actual_width or metadata_height != actual_height:
    warn("Rotation metadata detected - verify geometry manually")
```

### Decision
- ~~Add rotation check to STEP_01?~~ **Deferred** - handle later in development (PM confirmed 2025-12-12)

---

## ~~ISSUE_003: High FPS Source Video (240fps) Display Mapping~~ CLOSED

**Date Identified:** 2025-12-12  
**Date Closed:** 2025-12-12  
**Status:** Closed - Not an issue

### Description
IMG_1276.MOV is recorded at 239.69 FPS. Concern was raised about which source frame's overlay to display at standard playback rates.

### Resolution
This is NOT an issue because:
1. **Detection runs offline** - processes frames independently, caches with frame_idx + timestamp
2. **Playback connects them** - looks up cache by frame_idx or timestamp
3. **No sync problem** exists:
   - If ALL frames processed → cache has every frame_idx
   - If decimated → nearest processed frame returned
   - Timestamp available as fallback

**This is a design choice (decimation strategy), not a bug.**

### Decision
- Closed as non-issue
- Decimation strategy (if needed) is an optimization, not a correctness concern

---

## ISSUE_004: UI Real-Time Parameter Tuning Scope

**Date Identified:** 2025-12-12  
**Severity:** Low  
**Status:** Open  
**Affects:** Phase 9 (UI/Visualization)

### Description
The UI_IMPLEMENTATION_PLAN.md specifies FR6 (Parameter Fine-Tuning) with both real-time preview mode and offline batch mode. The scope of "real-time preview" for detection parameters needs clarification.

### Current Understanding
- **Visual params** (opacity, class toggles): Always instant, no detection needed
- **Filter params** (confidence threshold): Instant, filters cached data
- **Classification params** (px_per_mm): Reclassify all frames (~1s)
- **Detection params** (blur, Canny, Hough): Full re-detection required

### Question
For "real-time preview" of detection params:
- Option A: Run detection on current frame only (single-frame preview)
- Option B: Not supported in real-time mode (offline only)

### Decision Required
PM to confirm which option is preferred.

### Related
- FR6.2: "System shall provide real-time preview mode for instant feedback"
- docs/UI_IMPLEMENTATION_PLAN.md: Parameter Fine-Tuning section
