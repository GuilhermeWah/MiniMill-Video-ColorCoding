# Approach Evolution: From Week 3 Plan to Our Current MillPresenter

In this document we describe how our current implementation differs from our original Week 3 plan for COMP 4910, why we changed some of our decisions, and what exactly evolved in practice.

The Week 3 report captured a **high-level plan** for a contrast-based, OpenCV‑driven system with quick UI prototyping. As we actually built MillPresenter, we kept the **same goals**, but we refined the **architecture, tools, and workflow** so that the project feels more like a real product than a one‑off course demo.

---

## 1. Detection Approach

**Week 3 Plan (Report)**
- Use a **contrast-based** computer vision pipeline.
- Detect circles via **Hough Circles or Canny + contours**.
- Consider ML (YOLOv8) later if accuracy is too low.

**What We Ended Up Doing**
- We still use a **traditional CV approach**, but as a **dual-path pipeline**:
  - One path uses **HoughCircles**.
  - Another path uses **Canny + contours + circularity filters**.
  - Results are **fused** (NMS/overlap logic) into a single `Ball` per bead.
- Explicit handling for **hollow rings** (annulus beads): always use the **outer** diameter and guard against detecting the inner hole as a small bead.

**Why We Changed It**
- We found Hough‑only pipelines too fragile under **occlusion** and **glare**.
- We found contours‑only pipelines too noisy in cluttered areas.
- By combining both and fusing the results, we get better robustness while still staying in the "classic CV" world and respecting our constraint of **no heavy ML training**.

---

## 2. Video Backend: OpenCV vs PyAV

**Week 3 Plan (Report)**
- "Maintain the traditional computer-vision approach using the **OpenCV** lib due to its faster implementation within our time constraints."

**What We Ended Up Doing**
- We use **PyAV** (`av`), a Python binding to FFmpeg, as the main video backend (`FrameLoader` in `core/playback.py`).
- We still use OpenCV for image processing (filters, contours), but **not** for primary video decoding/seek.

**Why We Changed It**
1. **Seeking Accuracy / Scrubbing**
  - `cv2.VideoCapture.set(CAP_PROP_POS_FRAMES, n)` is often **approximate**.
  - For a presentation tool, we need **frame-perfect scrubbing** so overlays stay glued to the beads.
  - PyAV exposes frame indices and timestamps in a way that allows us to seek deterministically.

2. **Rotation Metadata**
  - Phone/camera clips (e.g., `DSC_3310.MOV`) often store orientation as **metadata**.
  - OpenCV typically ignores this, returning sideways frames.
  - PyAV lets us read rotation flags and fix orientation before we send frames into the vision pipeline.

3. **Future-Proofing (NVDEC / Export)**
  - PyAV sits directly on top of FFmpeg, which is the same engine we plan to use for **exporting annotated MP4s**.
  - This makes our decode/encode story cleaner than mixing `cv2.VideoCapture` + `cv2.VideoWriter` with separate FFmpeg calls.

In short, we traded a small upfront cost (learning PyAV) for a much better **scrubbing and presentation** experience, which is what we and the client actually care about.

---

## 3. Caching Strategy

**Week 3 Plan (Report)**
- "Cache detections per frame → enable instant toggling of color overlays."
- This implicitly suggested an in‑memory cache structure plugged directly into the UI.

**What We Ended Up Doing**
- We built a **two-layer cache**:
  1. **Disk Cache**: `detections.jsonl` with one `FrameDetections` JSON per line.
  2. **RAM Ring Buffer**: ~4 seconds of detections in memory for smooth scrubbing.
- Playback and export read **only** from this cache; detection is a **one-time offline pass**.

**Why We Changed It**
- We wanted **crash resilience**: if detection takes minutes, we don't want to lose all results if the app or OS decides to close.
- A disk-based cache lets our CLI, exporter, and UI all share the exact same detections without re-running the expensive vision engine.
- The ring buffer keeps memory usage bounded while still letting us scrub responsively.

---

## 4. UI Timeline and Focus

**Week 3 Plan (Report)**
- Suggests early completion of the UI with toggles ("Completed the development of the UI, with the proper toggles").
- Backend tasks (detection, integration, caching) and UI development are interleaved in the same weeks.

**What We Ended Up Doing**
- We explicitly staged our work into **phases**:
  - **Phase 1**: Foundation & Setup (project structure, logging, docs).
  - **Phase 2**: Vision Engine (models, processor, orchestrator, cache, CLI).
  - **Phase 3**: UI Player (overlay renderer, `VideoWidget`, `MainWindow`, then playback logic).
- Only after Phase 2 felt solid and tested did we start implementing the PyQt UI in Phase 3.

**Why We Changed It**
- We know that a UI without a stable backend quickly becomes a **mock** that hides real issues.
- By finishing and testing the core pipeline first (with TDD), any UI we build is wired into a known‑good backend.
- This reduces last‑minute integration surprises before a client demo.

---

## 5. Development Process: Ad-hoc vs TDD + Documentation

**Week 3 Plan (Report)**
- Describes tasks and milestones but not a strict engineering workflow.
- Focuses on *what* to implement rather than *how* to validate each step.

**What We Ended Up Doing**
- We follow a **strict TDD loop** for each feature:
  1. Add a task to `PLAN.md`.
  2. Write a failing test in `tests/`.
  3. Implement just enough code in `src/`.
  4. Run tests until green.
  5. Update `PLAN.md` and `docs/testing_criteria.md` with which test verifies which feature.
- We keep a running **FAQ (`docs/faq.md`)** where we capture every "Why did we do X instead of Y?" decision.

**Why We Changed It**
- The original plan is good for a **course report**, but fragile for long-term maintenance.
- TDD + explicit documentation gives us:
  - Safer refactoring.
  - Clear traceability from requirements → tests → code.
  - A written record of tradeoffs (e.g., "Why PyAV", "Why hybrid detection").

---

## 6. ML vs Classic CV

**Week 3 Plan (Report)**
- Considers YOLOv8 but rejects it for schedule and labeling cost.
- Commits to a classic CV pipeline targeting ~80–90% accuracy under stable conditions.

**What We Ended Up Doing**
- We matched that decision: **no heavy ML model**.
- Instead, we invested heavily in:
  - **Annulus-safe detection** to avoid misclassifying bead holes.
  - **ROI masks** to ignore clutter (bolts, flanges, etc.).
  - **Preprocessing (bilateral + CLAHE)** tuned for glare and motion.

**Why It Stayed the Same (But Got Sharper)**
- After exploring options, we confirmed that the original "classic CV" direction was still the best fit for our schedule and labelling constraints.
- The main improvement is in the **level of detail and safety checks** we added (e.g., explicit hole rejection, ROI rules) to make it viable for real videos, not just idealized frames.

---

## 7. Overall Summary

In short, we did **not** abandon our original Week 3 vision. Instead, we:

- Kept the **high-level plan**: contrast-based CV, 4/6/8/10 mm bins, caching for instant toggles, Windows target.
- **Upgraded how we implemented it**:
  - We use PyAV instead of raw OpenCV for decoding and scrubbing.
  - We run dual-path detection with fusion instead of a single Hough/Contours branch.
  - We rely on disk + RAM caching instead of in-memory only.
  - We follow a clear phased roadmap (Foundation → Vision → UI → Calibration → Validation).
  - We lean on TDD and detailed docs to keep the system explainable and maintainable.

This evolution reflects us moving from a **course-week plan** to something much closer to a **real product architecture**, while still staying aligned with the client's original goal: smooth, trustworthy overlays for grinding mill videos.
