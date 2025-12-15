# Calibration Refinement Plan & Explanation

This document explains the technical improvements being made to the Mill Presenter's calibration system to ensure highly accurate bead sizing.

## The Problem
Accurate bead sizing (distinguishing 6mm from 8mm balls) relies entirely on a precise `px_per_mm` (pixels per millimeter) calibration value. The current system has two potential sources of error:
1.  **Single-Frame Noise**: The auto-detection relies on a single video frame. If that frame has motion blur, compression artifacts, or lighting glares, the circle detection might be slightly off.
2.  **Rough Edge Detection**: Hough Circle Transform is robust but coarse. It finds "good enough" circles but isn't pixel-perfect.
3.  **Inconsistent Reference**: The codebase contained conflicting values for the drum diameter (196mm vs 200mm).

## The Solution

We are implementing a 3-stage refinement process to eliminate these errors.

### 1. Multi-Frame Averaging
Instead of looking at just one frame, we will now sample **5 distinct video frames**, detect the drum in each, and average the results.
- **Why?** Random noise cancels out. If one frame detects a radius of 400px and another 402px, the average (401px) is likely closer to the truth than any single measurement.

### 2. Sub-Pixel Edge Refinement
After finding the approximate circle with Hough Transform, we will "zoom in" on the edge pixels.
- **Technique**: We use Canny edge detection in a narrow band around the suspected drum rim.
- **Fitting**: We fit a precise ellipse/circle to these exact edge points.
- **Benefit**: This moves us from "nearest pixel" accuracy to "sub-pixel" accuracy, potentially improving diameter measurement by 0.5-1.0 mm.

### 3. Correct Reference Value
We are standardizing the calibration on **196.0 mm** for the drum's inner opening diameter (the visible dark background).
- **Why?** Using the correct physical constant is the foundation of all subsequent math.

## Expected Outcome
The `px_per_mm` value will be more stable and accurate. This directly translates to:
- Sharper distinct between bead sizes.
- Fewer "flickering" classifications (where a bead jumps between 6mm and 8mm).
- More reliable "Drum" ROI masking.
