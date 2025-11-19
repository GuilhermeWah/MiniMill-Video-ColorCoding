# MillPresenter Technical Primer & Contributor Guide

 This document is designed to get you up to speed with the specific technical challenges we face and the computer vision concepts we use to solve them.

## 1. The Core Challenge: "Presentation-First"
This is not just a video player, and it is not just a research script. It is a **presentation tool**.
*   **The Goal:** A presenter stands in front of a client, plays a 60fps video of a grinding mill, and clicks buttons to toggle overlays ("Show me only the 4mm beads").
*   **The Constraint:** The video **must not stutter**. The toggles must be **instant**.
*   **The Solution:** We do not detect beads while the video plays. We detect them **once** (offline), save them to a file, and then just "draw" them during playback.

## 2. Computer Vision Concepts (The "How")
We use classic Computer Vision (OpenCV), not Deep Learning (AI), because it is faster to tune for our specific geometry and requires no training data. Here are the key algorithms we use:

### A. Bilateral Filter (Preprocessing)
*   **What is it?** A smart blur. Unlike a standard blur that makes everything fuzzy, a Bilateral Filter smooths out "flat" areas but **stops** when it hits a sharp edge.
*   **Why we use it:** Our beads are metallic and have bright white **specular highlights** (glare). Standard edge detectors see these glare spots as "edges," confusing the circle detector. Bilateral filtering smooths the glare into the bead's body while keeping the outer rim of the bead crisp.

### B. CLAHE (Contrast Limited Adaptive Histogram Equalization)
*   **What is it?** A smart contrast booster. Instead of brightening the whole image equally, it breaks the image into a grid and boosts contrast in each square individually.
*   **Why we use it:** The inside of the mill is dark, but the beads are shiny. CLAHE allows us to see the faint outlines of beads in the shadowed corners without "blowing out" (blinding) the camera on the shiny beads in the center.

### C. Hough Circle Transform (The "Pile" Detector)
*   **What is it?** A voting algorithm. Every edge pixel in the image "votes" for where it thinks a circle center might be. If enough pixels vote for the same spot, the algorithm says "There is a circle here."
*   **Why we use it:** It is messy but robust. In the **dense pile** of beads at the bottom of the mill, beads are overlapping and partially hidden. Hough is excellent at finding these "implied" circles even if the edge is broken or partially covered.

### D. Canny Edges + Contours (The "Flyer" Detector)
*   **What is it?** It finds sharp lines (gradients) in the image and traces them into closed shapes (contours). We then measure how "circular" the shape is.
*   **Why we use it:** It is precise. For the **flying beads** that are isolated against the dark background, this method gives us a very accurate fit. We combine this with Hough to get the best of both worlds.
*   **Tuning:** The acceptable circularity threshold is configurable via `vision.min_circularity` (default `0.75`). Tighten it for real footage to keep overlays trustworthy; loosen it for synthetic fixtures in CI that might appear "too perfect" after encoding.

### E. Annulus (Ring) Logic
*   **The Problem:** Our beads are **hollow**. A standard circle detector sees two circles: the outer rim (e.g., 10mm) and the inner hole (e.g., 4mm).
*   **The Risk:** The system might think the 10mm bead is actually two beads: one big, one small.
*   **The Solution:** We use "Annulus Logic." Before accepting a detection, we check: *Is this small circle perfectly centered inside a larger circle?* If yes, it is a **hole**, not a bead. We ignore it and only keep the outer circle.

## 3. Architecture for Contributors
The codebase is split into two distinct worlds that barely talk to each other:

1.  **The Processor (`src/mill_presenter/core/processor.py`)**:
    *   Runs offline.
    *   Uses all the heavy CV algorithms above.
    *   Is allowed to be slow (e.g., 100ms per frame).
    *   Output: `detections.jsonl`.

2.  **The Player (`src/mill_presenter/ui/`)**:
    *   Runs live.
    *   **Never** imports OpenCV algorithms.
    *   Only reads `detections.jsonl` and draws circles using Qt.
    *   Must run at <16ms per frame.

## 4. Key Files to Read
*   `docs/design_decisions.md`: The "Why" behind our architecture.
*   `.github/copilot-instructions.md`: The strict rules for AI agents (and humans) working on this code.
*   `configs/sample.config.yaml`: Where we tune the sensitivity of the algorithms.
*   `scripts/run_detection.py`: Headless entry point that glues FrameLoader, Processor, Orchestrator, and ResultsCache together; used by automated tests and CLI workflows.

## 5. Changelog & Decision Log (For Contributors)
*This section tracks major architectural shifts and the reasoning behind them, specifically for us (Gui, Zach, Daniel)

### [Initial Setup] - 2025-11-19
*   **Decision:** Split project into `Processor` (Offline) and `Player` (Live).
    *   **Why:** We cannot guarantee 60fps playback if we run OpenCV detection on every frame. Pre-computing is the only way to ensure smooth presentation on mid-range laptops.
*   **Decision:** Use `PyAV` instead of `cv2.VideoCapture` for playback.
    *   **Why:** OpenCV's video decoder is notoriously bad at seeking (scrubbing) and doesn't expose hardware acceleration (NVDEC) reliably on Windows. PyAV gives us fine-grained control over the decode loop.
*   **Decision:** Support `.MOV` rotation metadata.
    *   **Why:** Raw footage from iPhones/Nikons often comes in "sideways" with a metadata flag. If we ignore this, our ROI masks will be rotated 90 degrees relative to the video.

