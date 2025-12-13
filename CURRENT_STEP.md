STEP_ID: STEP_01
TITLE: Drum Geometry & ROI Stabilization
DATE_CREATED: 2025-12-12
STATUS: Resolved

OWNER:
  ARCHITECT: Gemini 3 Pro
  DEVELOPER: Claude Opus 4.5
  PM: Human User

PM_INTENT:
  ARCHITECT_ACTION:
    ALLOWED: false
    ALLOWED_ACTIONS: []
    WHY: "Step completed and approved"

SCOPE:
  - Define static drum geometry (Center X, Center Y, Radius R) in pixel coordinates.
  - Generate a binary Region of Interest (ROI) mask.
  - Implement a 'rim margin' to exclude the turbulent/bolt-heavy edge of the mill.
  - Create a visualization overlay confirming the geometry against a reference frame.

OUT_OF_SCOPE:
  - Automatic dynamic tracking of the drum (drum is assumed static).
  - Bead detection or counting.
  - Pixel-to-mm calibration.
  - UI controls for geometry adjustment (configuration is file-based for now).

INPUT:
  - Raw video frames (1920x1080 or similar).
  - Configuration file (YAML/JSON) containing basic geometry guesses or distinct parameters.

OUTPUT:
  - `config/geometry.json`: Validated geometry parameters {x, y, r, margin}.
  - `output/roi_mask.png`: Binary image (white = active area, black = ignored).
  - `output/geometry_debug.png`: ROI overlaid on a sample frame.

ALGORITHM:
  - Static Geometry Application:
    1. Load target frame.
    2. Read (x, y, r) from config (or default if missing).
    3. Generate circular mask defined by `(x, y)` and `r - margin`.
    4. Apply mask to frame for visualization.
  - Rationale: The camera is fixed. A static, strict ROI is the single most effective noise filter (removing bolts, liners, and darkness). It provides a stable foundation for all subsequent detection steps.

PARAMETERS_TO_EXPOSE:
  - `drum_center_x_px`: Horizontal center of the drum.
  - `drum_center_y_px`: Vertical center of the drum.
  - `drum_radius_px`: Pixel radius of the grindable area.
  - `rim_margin_px`: Buffer zone to exclude edge artifacts (bolts/liners).

CONFIDENCE_DEFINITION:
  - N/A (Deterministic geometric definition, not a probabilistic inference).

VALIDATION:
  - Visual Alignment: The generated red circle overlay must match the visible inner rim of the drum in the sample frame.
  - Mask Correctness: The binary mask must strictly exclude the bolt heads visible at the drum periphery.
  - Persistence: Rerunning the step must produce identical config and mask files (determinism).

ARTIFACTS_REQUIRED:
  - IMAGES:
    - `output/geometry_overlay.png` (Frame + Circle + Excluded Region highlighted).
    - `output/roi_mask.png` (The actual mask used).
  - STRUCTURED:
    - `config/geometry.json`
  - MANIFEST:
    - `output/run_manifest.json`

TEST_SET:
  VIDEOS:
    - `test_video_01.mp4` (or available sample)
  FRAMES:
    - Frame 0 (Start)
    - Frame 100 (Mid-operation)
  SAMPLE_SIZE:
    - 2 frames

DEPENDENCIES:
  - None (Bootstrapping).

ROLLBACK_PLAN:
  - Delete `config/geometry.json` and `output/roi_mask.png`.
  - Revert to hardcoded defaults in code if necessary.

PM_DECISION:
  DECISION: Resolved
  NOTES: "Completed and approved 2025-12-12. All 3 test videos verified."

PHASE: Foundation
BASELINE_REFERENCE:
  STEP_ID: "BOOTSTRAP"
  RUN_ID: "N/A"
  HANDOFF: "rules/HANDOFF_PACKET.md"
ORDER_CONSTRAINT:
  MUST_FOLLOW_MAIN_MD: true
  OVERRIDE_REQUIRES_PM_APPROVAL: true

---

STEP_ID: STEP_02
TITLE: Golden Frames Lock (Baseline Validation Set)
DATE_CREATED: 2025-12-12
STATUS: Resolved

OWNER:
  ARCHITECT: Claude Opus 4.5 (PM-approved role switch)
  DEVELOPER: Claude Opus 4.5
  PM: Human User

PM_INTENT:
  ARCHITECT_ACTION:
    ALLOWED: false
    ALLOWED_ACTIONS: []
    WHY: "Step completed and approved"

SCOPE:
  - Extract and lock a curated set of "golden frames" from test videos.
  - Golden frames serve as the baseline validation set for all subsequent pipeline steps.
  - Each golden frame must be:
    - Representative of different conditions (dense beads, sparse beads, motion blur, glare).
    - Annotated with metadata (video source, frame index, condition tags).
    - Stored with deterministic naming for reproducibility.
  - Generate SHA256 hashes for each golden frame to ensure immutability.

OUT_OF_SCOPE:
  - Manual bead annotation / ground truth labeling (future step).
  - Bead detection or counting.
  - Preprocessing or enhancement of frames.
  - Any modification to golden frames after lock.

INPUT:
  - Test videos: IMG_6535.MOV (4K), IMG_1276.MOV (1080p), DSC_3310.MOV (1080p)
  - STEP_01 outputs: Per-video geometry cache files.
  - Frame selection criteria (defined below).

OUTPUT:
  - `data/golden_frames/` directory containing:
    - `{video_name}_frame_{idx}.png` — Raw extracted frames (PNG, lossless).
    - `{video_name}_frame_{idx}_masked.png` — Frames with ROI mask applied.
  - `data/golden_frames/manifest.json` — Metadata for all golden frames:
    ```json
    {
      "version": "1.0",
      "locked_date": "2025-12-12T...",
      "frames": [
        {
          "id": "IMG_6535_frame_0",
          "video": "IMG_6535.MOV",
          "frame_idx": 0,
          "resolution": "3840x2160",
          "sha256": "abc123...",
          "sha256_masked": "def456...",
          "tags": ["start", "sparse"],
          "geometry_cache": "IMG_6535_8d05444a.json"
        }
      ]
    }
    ```
  - `output/step02_manifest.json` — Run manifest with timing and paths.

ALGORITHM:
  - Frame Selection Strategy:
    1. For each test video, extract frames at strategic indices:
       - Frame 0: Start of video (baseline state)
       - Frame 100: Early operation
       - Frame at 25% duration: Quarter mark
       - Frame at 50% duration: Midpoint
       - Frame at 75% duration: Three-quarter mark
       - Frame at total-10: Near end
    2. Apply ROI mask from STEP_01 geometry to create masked variants.
    3. Compute SHA256 hash of each frame (raw and masked).
    4. Tag each frame with observable conditions:
       - "dense" / "sparse" (bead density)
       - "blur" (visible motion blur)
       - "glare" (strong specular reflections)
       - "clear" (good visibility)
    5. Write manifest with all metadata.
  - Rationale: Golden frames provide immutable reference points. All future pipeline changes can be validated against these exact frames. Hashes ensure no accidental modification.

PARAMETERS_TO_EXPOSE:
  - `frame_indices`: List of frame indices to extract (or "auto" for strategic selection).
  - `output_format`: Image format (default: PNG for lossless).
  - `include_masked`: Whether to generate ROI-masked variants (default: true).

CONFIDENCE_DEFINITION:
  - N/A (No detection at this phase; deterministic frame extraction).

VALIDATION:
  - Frame Count: Minimum 6 frames per video × 3 videos = 18 golden frames.
  - Hash Verification: Re-running extraction must produce identical SHA256 hashes.
  - Manifest Completeness: Every frame must have all required metadata fields.
  - Visual Spot-Check: At least one frame per video should be opened and visually confirmed.

ARTIFACTS_REQUIRED:
  - IMAGES:
    - `data/golden_frames/*.png` (raw frames)
    - `data/golden_frames/*_masked.png` (ROI-masked frames)
  - STRUCTURED:
    - `data/golden_frames/manifest.json`
  - MANIFEST:
    - `output/step02_manifest.json`

TEST_SET:
  VIDEOS:
    - IMG_6535.MOV (4K, 3840x2160)
    - IMG_1276.MOV (1080p, 1920x1080)
    - DSC_3310.MOV (1080p, 1920x1080)
  FRAMES:
    - 6 strategic frames per video (auto-selected)
  SAMPLE_SIZE:
    - 18 frames across 3 videos

DEPENDENCIES:
  - STEP_01: Drum Geometry & ROI Stabilization (for ROI masks)

ROLLBACK_PLAN:
  - Delete `data/golden_frames/` directory.
  - Re-run extraction if needed.

PM_DECISION:
  DECISION: Resolved
  NOTES: "Completed and approved 2025-12-12. 18 golden frames extracted with SHA256 hashes. Calibration sanity check performed with 200mm drum assumption - size classification verified."

PHASE: Foundation
BASELINE_REFERENCE:
  STEP_ID: "STEP_01"
  RUN_ID: "ITER_0002"
  HANDOFF: "rules/HANDOFF_PACKET.md"
ORDER_CONSTRAINT:
  MUST_FOLLOW_MAIN_MD: true
  OVERRIDE_REQUIRES_PM_APPROVAL: true

---

STEP_ID: STEP_03
TITLE: Preprocessing Baseline Stabilization
DATE_CREATED: 2025-12-12
STATUS: Approved

OWNER:
  ARCHITECT: Claude Opus 4.5
  DEVELOPER: Claude Opus 4.5
  PM: Human User

PM_INTENT:
  ARCHITECT_ACTION:
    ALLOWED: false
    ALLOWED_ACTIONS: []
    WHY: "Spec approved, Dev implementing"

SCOPE:
  - Define a deterministic preprocessing pipeline that improves bead visibility.
  - Target issues observed in golden frames:
    - Specular glare (shiny metallic surfaces creating hot spots)
    - Uneven illumination (shadows, light falloff)
    - Low local contrast (beads blending with background)
  - Output preprocessed frames ready for candidate generation (STEP_04).
  - All preprocessing must operate in pixel-space only.

OUT_OF_SCOPE:
  - Circle/bead detection (STEP_04).
  - Confidence scoring (STEP_05).
  - Size classification (STEP_07).
  - Any use of px_per_mm calibration values.
  - Deep learning / neural networks (classical CV only).

INPUT:
  - Golden frames from STEP_02: `data/golden_frames/*.png` (raw and masked variants)
  - ROI masks from STEP_01 geometry cache
  - DrumGeometry from config cache

OUTPUT:
  - `src/preprocess.py`: Preprocessing module with configurable pipeline
  - `output/preprocess_test/`: Debug outputs for golden frames
    - `{frame_id}_original.png` — Input frame (for reference)
    - `{frame_id}_preprocessed.png` — Output after preprocessing
    - `{frame_id}_stages.png` — Side-by-side showing each stage
  - `output/preprocess_test/preprocess_manifest.json`: Run metadata
  - Updated `src/config.py` with PREPROCESS_CONFIG parameters

ALGORITHM:
  - Preprocessing Pipeline (Sequential Stages):
    
    **Stage 1: Grayscale Conversion**
    - Convert BGR to grayscale for edge detection compatibility
    - Preserve original color frame for overlay generation later
    
    **Stage 2: ROI Application**
    - Apply drum ROI mask to focus processing on valid region
    - Set pixels outside ROI to 0 (black) to prevent edge artifacts
    
    **Stage 3: Illumination Normalization**
    - Apply morphological top-hat transform to reduce uneven lighting
    - Parameters: `tophat_kernel_size` (default: 15-25px, scaled by resolution)
    - Rationale: Top-hat extracts bright features relative to local background
    
    **Stage 4: Contrast Enhancement (CLAHE)**
    - Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
    - Parameters:
      - `clahe_clip_limit`: 2.0-4.0 (default: 3.0)
      - `clahe_tile_grid_size`: (8, 8) to (16, 16)
    - Rationale: CLAHE enhances local contrast without amplifying noise globally
    
    **Stage 5: Noise Reduction**
    - Apply bilateral filter OR Gaussian blur
    - Parameters:
      - `blur_type`: "bilateral" | "gaussian" | "median"
      - `blur_diameter`: 5-9px (bilateral)
      - `blur_sigma_color`: 50-100 (bilateral)
      - `blur_sigma_space`: 50-100 (bilateral)
    - Rationale: Bilateral preserves edges while smoothing flat regions
    
    **Stage 6: Glare Suppression (Optional)**
    - Detect and attenuate specular highlights
    - Method: Threshold high-intensity pixels, apply local inpainting or cap
    - Parameters:
      - `glare_threshold`: 240-250 (near saturation)
      - `glare_mode`: "cap" | "inpaint" | "none"
    - Rationale: Glare creates false edges and phantom detections
    
  - Design Principles:
    1. Each stage is independently toggleable via config
    2. All parameters exposed in PREPROCESS_CONFIG
    3. Pipeline is deterministic (same input → same output)
    4. No pixel-to-mm conversion at any stage

PARAMETERS_TO_EXPOSE:
  ```python
  PREPROCESS_CONFIG = {
      # Stage toggles
      "enable_tophat": True,
      "enable_clahe": True,
      "enable_blur": True,
      "enable_glare_suppression": False,  # Start disabled, tune later
      
      # Stage 3: Top-hat
      "tophat_kernel_size": 21,  # Odd number
      
      # Stage 4: CLAHE
      "clahe_clip_limit": 3.0,
      "clahe_tile_grid_size": (8, 8),
      
      # Stage 5: Blur
      "blur_type": "bilateral",  # "bilateral" | "gaussian" | "median"
      "blur_diameter": 7,
      "blur_sigma_color": 75,
      "blur_sigma_space": 75,
      
      # Stage 6: Glare (if enabled)
      "glare_threshold": 245,
      "glare_mode": "cap",  # "cap" | "inpaint" | "none"
  }
  ```

CONFIDENCE_DEFINITION:
  - N/A (Preprocessing produces images, not detections).
  - However, preprocessing quality can be measured by:
    - Edge clarity (Laplacian variance after preprocessing)
    - Histogram spread (contrast metric)
    - Glare reduction (% pixels above saturation threshold)

VALIDATION:
  - Determinism: Same golden frame → identical preprocessed output (SHA256 match).
  - Visual Quality: Preprocessed frames should show:
    - Clearer bead edges vs. original
    - Reduced glare hot spots
    - More uniform illumination across ROI
  - No Information Loss: Beads visible in original must remain visible after preprocessing.
  - No False Enhancement: Background noise should not be amplified into bead-like features.
  - Baseline Comparison: Generate before/after comparison images for PM review.

ARTIFACTS_REQUIRED:
  - IMAGES:
    - `output/preprocess_test/{frame_id}_original.png`
    - `output/preprocess_test/{frame_id}_preprocessed.png`
    - `output/preprocess_test/{frame_id}_stages.png` (multi-panel comparison)
    - `output/preprocess_test/comparison_grid.png` (all golden frames, before/after)
  - STRUCTURED:
    - `output/preprocess_test/preprocess_manifest.json`
    - `output/preprocess_test/quality_metrics.json` (optional: edge clarity, histogram stats)
  - CODE:
    - `src/preprocess.py`
    - Updated `src/config.py`

TEST_SET:
  SOURCE: Golden frames from STEP_02
  FRAMES:
    - All 18 golden frames (6 per video × 3 videos)
    - Focus on frames with visible glare/blur for tuning
  SAMPLE_SIZE:
    - 18 frames across 3 videos

DEPENDENCIES:
  - STEP_01: Drum Geometry (for ROI mask)
  - STEP_02: Golden Frames (test inputs)

FAILURE_MODES:
  1. **Over-enhancement**: CLAHE clip too high → noise becomes bead-like
     - Mitigation: Start conservative (clip_limit=2.0), increase gradually
  2. **Edge Destruction**: Blur too strong → bead edges become fuzzy
     - Mitigation: Use edge-preserving bilateral filter
  3. **Glare Artifacts**: Inpainting creates fake features
     - Mitigation: Start with glare_mode="cap" (simple clipping)
  4. **Resolution Sensitivity**: Fixed kernel sizes fail at different resolutions
     - Mitigation: Scale kernel sizes by frame height ratio

ROLLBACK_PLAN:
  - Revert to raw golden frames (always available from STEP_02)
  - Set all `enable_*` flags to False for passthrough mode
  - Delete `output/preprocess_test/` directory

PM_DECISION:
  DECISION: Resolved
  NOTES: "Completed 2025-12-12. Preprocessing uses FULL drum radius to preserve edge beads. Rim margin filtering deferred to STEP_06. Avg contrast improvement +23.5."

PHASE: Preprocessing
BASELINE_REFERENCE:
  STEP_ID: "STEP_02"
  RUN_ID: "ITER_0003"
  HANDOFF: "rules/HANDOFF_PACKET.md"
ORDER_CONSTRAINT:
  MUST_FOLLOW_MAIN_MD: true
  OVERRIDE_REQUIRES_PM_APPROVAL: true

---

STEP_ID: STEP_04
TITLE: Candidate Generation (Circle Detection)
DATE_CREATED: 2025-12-12
STATUS: Resolved

OWNER:
  ARCHITECT: Claude Opus 4.5
  DEVELOPER: Claude Opus 4.5
  PM: Human User

PM_INTENT:
  ARCHITECT_ACTION:
    ALLOWED: false
    ALLOWED_ACTIONS: []
    WHY: "Step completed"

SCOPE:
  - Detect circular bead candidates from preprocessed frames using HoughCircles.
  - Output raw detections in pixel-space: (x, y, r_px).
  - NO filtering at this stage - capture all potential candidates.
  - NO confidence scoring at this stage (STEP_05).
  - NO size classification at this stage (STEP_07).

OUT_OF_SCOPE:
  - Filtering false positives (STEP_06)
  - Confidence scoring (STEP_05)
  - Size classification (STEP_07)
  - Rim margin filtering (STEP_06)
  - Use of px_per_mm calibration

INPUT:
  - Preprocessed grayscale frames from STEP_03
  - Drum geometry (for radius range calculation)
  - Golden frames for testing

OUTPUT:
  - `src/detect.py`: Detection module with configurable HoughCircles
  - `output/detection_test/`: Debug outputs for golden frames
    - `{frame_id}_candidates.png` — Overlay showing all detected circles
    - `{frame_id}_candidates.json` — Raw detections list
  - `output/detection_test/detection_manifest.json`: Run metadata
  - Updated `src/config.py` with DETECTION_BEAD_CONFIG

ALGORITHM:
  - Detection Pipeline:
    
    **Step 1: Load Preprocessed Frame**
    - Use output from STEP_03 preprocessing pipeline
    - Frame is already grayscale with ROI applied
    
    **Step 2: Calculate Radius Range (Per-Video)**
    - Use drum geometry to estimate bead radius range in pixels
    - For 200mm drum assumption:
      - min_radius: ~70% of smallest bead (4mm) → scaled by px_per_mm
      - max_radius: ~150% of largest bead (10mm) → scaled by px_per_mm
    - Formula: `r_px = (d_mm / 2) * (drum_radius_px * 2 / drum_diameter_mm)`
    - This ensures detection range adapts to video resolution
    
    **Step 3: Apply HoughCircles**
    - Algorithm: cv2.HOUGH_GRADIENT
    - Parameters:
      - `dp`: Accumulator resolution (1 = same as input)
      - `minDist`: Minimum distance between circle centers
      - `param1`: Higher Canny edge threshold
      - `param2`: Accumulator threshold (lower = more candidates)
      - `minRadius`: Calculated from Step 2
      - `maxRadius`: Calculated from Step 2
    
    **Step 4: Output Raw Candidates**
    - Each candidate: `{x: int, y: int, r_px: float}`
    - No filtering, no scoring - raw HoughCircles output
    - Store with frame metadata for later processing

  - Design Principles:
    1. Detection is resolution-adaptive (radius scales with drum size)
    2. OVER-detect rather than under-detect (filtering comes later)
    3. All parameters exposed in config
    4. Purely pixel-space (no mm conversion)

PARAMETERS_TO_EXPOSE:
  ```python
  DETECTION_BEAD_CONFIG = {
      # Bead size assumptions (for radius range calculation)
      "drum_diameter_mm": 200,         # Physical drum diameter
      "min_bead_diameter_mm": 3.0,     # Smallest expected bead (with margin)
      "max_bead_diameter_mm": 12.0,    # Largest expected bead (with margin)
      
      # HoughCircles parameters
      "dp": 1,                         # Accumulator resolution
      "min_dist_ratio": 0.5,           # minDist as ratio of min_radius
      "param1": 50,                    # Canny high threshold
      "param2": 25,                    # Accumulator threshold (lower = more)
      
      # Safety margins
      "radius_margin_low": 0.7,        # Allow 30% smaller than calculated
      "radius_margin_high": 1.5,       # Allow 50% larger than calculated
  }
  ```

CONFIDENCE_DEFINITION:
  - N/A at this stage (STEP_05 adds confidence scoring)
  - Raw HoughCircles does not provide meaningful confidence

VALIDATION:
  - Coverage: Most visible beads should have at least one candidate
  - Over-detection OK: False positives expected (filtered in STEP_06)
  - Determinism: Same preprocessed frame → identical candidates
  - Visual Check: Overlay should show circles on most beads

ARTIFACTS_REQUIRED:
  - IMAGES:
    - `output/detection_test/{frame_id}_candidates.png`
  - STRUCTURED:
    - `output/detection_test/{frame_id}_candidates.json`
    - `output/detection_test/detection_manifest.json`
  - CODE:
    - `src/detect.py`
    - Updated `src/config.py`

TEST_SET:
  SOURCE: Golden frames from STEP_02 (preprocessed via STEP_03)
  FRAMES:
    - All 18 golden frames
  SAMPLE_SIZE:
    - 18 frames across 3 videos

DEPENDENCIES:
  - STEP_01: Drum Geometry (for radius calculations)
  - STEP_02: Golden Frames (test inputs)
  - STEP_03: Preprocessing (input frames)

FAILURE_MODES:
  1. **Under-detection**: param2 too high → misses beads
     - Mitigation: Start with low param2 (25), accept false positives
  2. **Over-detection**: Too many spurious candidates
     - Mitigation: Acceptable at this stage; STEP_06 filters
  3. **Wrong radius range**: Beads outside detection range
     - Mitigation: Use wide margins (0.7x to 1.5x)
  4. **Merged detections**: Touching beads detected as one
     - Mitigation: Low minDist allows overlapping candidates

ROLLBACK_PLAN:
  - Revert to preprocessed frames only
  - Delete `output/detection_test/` directory

PM_DECISION:
  DECISION: Resolved
  NOTES: "Completed 2025-12-12. Resolution-adaptive param2 implemented. 4K: ~1000 candidates, 1080p: ~300 candidates per frame."

PHASE: CandidateGen
BASELINE_REFERENCE:
  STEP_ID: "STEP_03"
  RUN_ID: "ITER_0004"
  HANDOFF: "rules/HANDOFF_PACKET.md"
ORDER_CONSTRAINT:
  MUST_FOLLOW_MAIN_MD: true
  OVERRIDE_REQUIRES_PM_APPROVAL: true

---

STEP_ID: STEP_05
TITLE: Confidence Scoring
DATE_CREATED: 2025-12-12
STATUS: Approved

OWNER:
  ARCHITECT: Claude Opus 4.5
  DEVELOPER: Claude Opus 4.5
  PM: Human User

PM_INTENT:
  ARCHITECT_ACTION:
    ALLOWED: false
    ALLOWED_ACTIONS: []
    WHY: "Spec approved, Dev implementing"

SCOPE:
  - Assign confidence scores [0.0, 1.0] to each detection from STEP_04.
  - Confidence must be:
    - Deterministic (same input → same score)
    - Computed from observable image evidence
    - Comparable across frames
    - Thresholdable (users can filter by confidence)
  - High glare/noise should NOT inflate confidence.

OUT_OF_SCOPE:
  - Filtering by confidence threshold (STEP_06)
  - Size classification (STEP_07)
  - Rim margin filtering (STEP_06)
  - Deep learning / neural networks

INPUT:
  - Raw detections from STEP_04: (x, y, r_px)
  - Preprocessed grayscale frames from STEP_03
  - Original color frames (for gradient analysis)

OUTPUT:
  - `src/confidence.py`: Confidence scoring module
  - Detections enriched with `conf` field: (x, y, r_px, conf)
  - `output/confidence_test/`: Debug outputs
    - `{frame_id}_scored.png` — Overlay with color-coded confidence
    - `{frame_id}_scored.json` — Detections with confidence
  - `output/confidence_test/confidence_manifest.json`

ALGORITHM:
  - Confidence is computed from multiple observable features:
    
    **Feature 1: Edge Strength (weight: 0.35)**
    - Compute gradient magnitude along the circle perimeter
    - Sample N points around the circumference
    - Higher edge strength → higher confidence
    - Normalized to [0, 1] range
    
    **Feature 2: Circularity / Edge Consistency (weight: 0.25)**
    - Measure variance of gradient magnitude around perimeter
    - Low variance = consistent edge = likely a real bead
    - High variance = partial edge = likely noise
    
    **Feature 3: Interior Uniformity (weight: 0.20)**
    - Compare intensity variance inside circle vs. expected bead pattern
    - Real beads have characteristic center (bright) vs. edge pattern
    - Glare spots have different intensity profile
    
    **Feature 4: Radius Consistency (weight: 0.20)**
    - Compare detected radius to expected bead sizes
    - Radii matching expected sizes get higher confidence
    - Very small or very large radii get penalized
    
  - Final Confidence:
    ```
    conf = w1*edge_strength + w2*circularity + w3*interior + w4*radius_fit
    conf = clamp(conf, 0.0, 1.0)
    ```
    
  - Design Principles:
    1. All features computed in pixel-space
    2. No px_per_mm used in computation
    3. Weights are configurable
    4. Each feature individually testable

PARAMETERS_TO_EXPOSE:
  ```python
  CONFIDENCE_CONFIG = {
      # Feature weights (must sum to 1.0)
      "weight_edge_strength": 0.35,
      "weight_circularity": 0.25,
      "weight_interior": 0.20,
      "weight_radius_fit": 0.20,
      
      # Edge sampling
      "edge_sample_points": 36,       # Points around circumference
      "edge_gradient_sigma": 1.0,     # Gaussian for gradient
      
      # Interior analysis
      "interior_sample_ratio": 0.7,   # Sample within 70% of radius
      
      # Radius fit (relative to expected range)
      "radius_fit_optimal_min": 0.9,  # 90% of expected min
      "radius_fit_optimal_max": 1.1,  # 110% of expected max
  }
  ```

CONFIDENCE_DEFINITION:
  - `conf ∈ [0.0, 1.0]` where:
    - 0.0 = Very unlikely to be a bead
    - 0.5 = Uncertain / borderline
    - 1.0 = Very likely to be a bead
  - Thresholdable: Users can set minimum confidence (e.g., 0.6)
  - Comparable: Confidence is consistent across frames and videos

VALIDATION:
  - Determinism: Same detection → same confidence score
  - Ordering: True beads should generally have higher confidence than noise
  - Distribution: Expect bimodal distribution (high for beads, low for noise)
  - Visual Check: Color-coded overlay should show green on beads, red on noise

VISUALIZATION_NOTES:
  - Overlay opacity should scale with confidence (PM request)
  - High confidence (>0.7): Solid green, full opacity
  - Medium confidence (0.4-0.7): Yellow/orange, partial opacity
  - Low confidence (<0.4): Red, faint/transparent
  - Implementation can be deferred to overlay/playback step if needed

ARTIFACTS_REQUIRED:
  - IMAGES:
    - `output/confidence_test/{frame_id}_scored.png`
  - STRUCTURED:
    - `output/confidence_test/{frame_id}_scored.json`
    - `output/confidence_test/confidence_manifest.json`
    - `output/confidence_test/confidence_distribution.json`
  - CODE:
    - `src/confidence.py`
    - Updated `src/config.py`

TEST_SET:
  SOURCE: Detections from STEP_04 on golden frames
  FRAMES:
    - All 18 golden frames
  SAMPLE_SIZE:
    - 18 frames across 3 videos

DEPENDENCIES:
  - STEP_03: Preprocessing (frame data)
  - STEP_04: Detection (raw candidates)

FAILURE_MODES:
  1. **Glare inflation**: Bright spots get high confidence
     - Mitigation: Interior uniformity feature penalizes glare
  2. **Edge dropout**: Partial occlusions lower confidence unfairly
     - Mitigation: Allow some variance in circularity
  3. **Scale sensitivity**: Confidence varies with resolution
     - Mitigation: Normalize features relative to radius

ROLLBACK_PLAN:
  - Assign uniform confidence (0.5) to all detections
  - Rely on STEP_06 filtering only

PM_DECISION:
  DECISION: Resolved
  NOTES: |
    PM approved 2025-12-12.
    - Confidence scoring working as designed
    - Per-video analysis documented
    - Full pipeline analysis document created
    - Ready to proceed to STEP_06

PHASE: Filters
BASELINE_REFERENCE:
  STEP_ID: "STEP_04"
  RUN_ID: "ITER_0005"
  HANDOFF: "rules/HANDOFF_PACKET.md"
ORDER_CONSTRAINT:
  MUST_FOLLOW_MAIN_MD: true
  OVERRIDE_REQUIRES_PM_APPROVAL: true

---

STEP_ID: STEP_06
TITLE: Filtering and Cleanup
DATE_CREATED: 2025-12-12
STATUS: Approved

OWNER:
  ARCHITECT: Claude Opus 4.5
  DEVELOPER: Claude Opus 4.5
  PM: Human User

PM_INTENT:
  ARCHITECT_ACTION:
    ALLOWED: false
    ALLOWED_ACTIONS: []
    WHY: "Spec approved, Dev implementing"

SCOPE:
  - Filter false positive detections from STEP_05
  - **RIM MARGIN FILTERING**: Reject detections in the outer rim zone
    - Preprocessing (STEP_03) uses FULL drum radius to preserve edge beads
    - Detection (STEP_04) operates on full ROI including rim
    - This step applies rim_margin_px to filter edge artifacts (bolts, screws, purple ring)
  - **CONFIDENCE THRESHOLD**: Reject detections below minimum confidence
  - **NON-MAXIMUM SUPPRESSION (NMS)**: Merge overlapping detections
  - Output cleaned detection list

OUT_OF_SCOPE:
  - Size classification (STEP_07)
  - Temporal filtering across frames
  - Deep learning / neural networks

INPUT:
  - Scored detections from STEP_05: (x, y, r_px, conf, features)
  - Drum geometry from STEP_01: (center_x, center_y, radius_px)
  - Configuration parameters

OUTPUT:
  - `src/filter.py`: Filtering module
  - Filtered detections: (x, y, r_px, conf) - reduced count
  - `output/filter_test/`: Debug outputs
    - `{frame_id}_filtered.png` — Before/after comparison overlay
    - `{frame_id}_filtered.json` — Filtered detections with filter stats
  - `output/filter_test/filter_manifest.json`

ALGORITHM:

  **Filter 1: Rim Margin (Applied First)**
  
  Purpose: Remove detections on rim, bolts, purple ring, and edge artifacts.
  
  ```python
  def filter_rim_margin(detections, drum_center, drum_radius, rim_margin_ratio=0.12):
      """
      Reject detections whose CENTER is outside the inner ROI.
      
      inner_radius = drum_radius * (1 - rim_margin_ratio)
      
      A detection is KEPT if:
        distance(detection_center, drum_center) < inner_radius
      """
      inner_radius = drum_radius * (1 - rim_margin_ratio)
      
      filtered = []
      for det in detections:
          dist = sqrt((det.x - drum_center[0])**2 + (det.y - drum_center[1])**2)
          if dist < inner_radius:
              filtered.append(det)
      
      return filtered
  ```
  
  Design notes:
  - Default rim_margin_ratio = 0.12 (12% of radius)
  - For 200mm drum: 12mm rim excluded
  - Targets: bolts, purple ring, rim edge artifacts
  
  ---
  
  **Filter 2: Confidence Threshold (Applied Second)**
  
  Purpose: Remove low-confidence noise detections.
  
  ```python
  def filter_confidence(detections, min_confidence=0.5):
      """
      Reject detections with confidence below threshold.
      """
      return [d for d in detections if d.conf >= min_confidence]
  ```
  
  Design notes:
  - Default min_confidence = 0.5 (adjustable)
  - Per STEP_05 analysis:
    - 0.5 threshold: retains 40% of detections
    - 0.6 threshold: retains 18% of detections
    - 0.7 threshold: retains 12% of detections
  
  ---
  
  **Filter 3: Non-Maximum Suppression (Applied Last)**
  
  Purpose: Merge overlapping detections, keep highest confidence.
  
  ```python
  def filter_nms(detections, overlap_threshold=0.5):
      """
      For overlapping circles, keep only the highest confidence.
      
      Two circles overlap if:
        distance(c1, c2) < (r1 + r2) * overlap_threshold
      
      Process:
      1. Sort by confidence (descending)
      2. For each detection (highest conf first):
         - If not suppressed, add to results
         - Suppress all overlapping lower-conf detections
      """
      # Sort by confidence descending
      sorted_dets = sorted(detections, key=lambda d: d.conf, reverse=True)
      
      kept = []
      suppressed = set()
      
      for i, det in enumerate(sorted_dets):
          if i in suppressed:
              continue
          
          kept.append(det)
          
          # Suppress overlapping lower-conf detections
          for j in range(i + 1, len(sorted_dets)):
              if j in suppressed:
                  continue
              
              other = sorted_dets[j]
              dist = sqrt((det.x - other.x)**2 + (det.y - other.y)**2)
              threshold = (det.r_px + other.r_px) * overlap_threshold
              
              if dist < threshold:
                  suppressed.add(j)
      
      return kept
  ```
  
  Design notes:
  - Default overlap_threshold = 0.5 (50% overlap triggers suppression)
  - Keeps highest-confidence detection in overlapping group
  - Applied last to avoid suppressing before confidence filter

PARAMETERS_TO_EXPOSE:
  ```python
  FILTER_CONFIG = {
      # Rim margin filter
      "rim_margin_ratio": 0.12,        # 12% of drum radius excluded
      
      # Confidence threshold
      "min_confidence": 0.5,           # Minimum confidence to keep
      
      # Non-maximum suppression
      "nms_overlap_threshold": 0.5,    # 50% overlap triggers suppression
      
      # Filter order (do not change unless necessary)
      "filter_order": ["rim", "confidence", "nms"],
  }
  ```

CONFIDENCE_DEFINITION:
  - Confidence is passed through unchanged from STEP_05
  - Only used for thresholding and NMS ordering

VALIDATION:
  - **Rim filter**: No detections should remain in outer 12% of drum
  - **Confidence filter**: All remaining detections have conf >= threshold
  - **NMS**: No two detections should overlap by more than 50%
  - **Determinism**: Same input → same output
  - **Visual check**: Before/after overlay should show clear improvement

EXPECTED_RESULTS:
  Based on STEP_05 data (14,234 candidates):
  
  | Filter Stage | Est. Remaining | Est. Reduction |
  |--------------|----------------|----------------|
  | Input | 14,234 | - |
  | After rim | ~11,000 | ~23% |
  | After conf (0.5) | ~5,000 | ~55% |
  | After NMS | ~2,000-3,000 | ~40-60% |
  | **Final** | **~2,000-3,000** | **~80-85%** |

ARTIFACTS_REQUIRED:
  - IMAGES:
    - `output/filter_test/{frame_id}_filtered.png`
  - STRUCTURED:
    - `output/filter_test/{frame_id}_filtered.json`
    - `output/filter_test/filter_manifest.json`
  - CODE:
    - `src/filter.py`
    - Updated `src/config.py`

TEST_SET:
  SOURCE: Scored detections from STEP_05
  FRAMES:
    - All 18 golden frames
  SAMPLE_SIZE:
    - 18 frames across 3 videos

DEPENDENCIES:
  - STEP_01: Drum geometry (center, radius)
  - STEP_05: Scored detections

FAILURE_MODES:
  1. **Over-filtering**: Rim margin too aggressive, removes real beads
     - Mitigation: Start with 12%, adjust based on visual review
  2. **Under-filtering**: Confidence threshold too low
     - Mitigation: Start with 0.5, can increase to 0.6 if too noisy
  3. **NMS merging errors**: Wrong detection kept
     - Mitigation: NMS uses confidence ordering, highest wins

ROLLBACK_PLAN:
  - Set all thresholds to permissive values (rim=0, conf=0, nms=1.0)
  - Returns unfiltered input

PM_DECISION:
  DECISION: Resolved
  NOTES: |
    PM approved 2025-12-12.
    - 3-stage filtering implemented and tested
    - 87.1% reduction (14,234 → 1,830 detections)
    - Visual overlays reviewed and approved
    - Ready for STEP_07

PHASE: Filters
BASELINE_REFERENCE:
  STEP_ID: "STEP_05"
  RUN_ID: "ITER_0006"
  HANDOFF: "rules/HANDOFF_PACKET.md"
ORDER_CONSTRAINT:
  MUST_FOLLOW_MAIN_MD: true
  OVERRIDE_REQUIRES_PM_APPROVAL: true

---

STEP_ID: STEP_07
TITLE: Calibration and Size Classification
DATE_CREATED: 2025-12-12
STATUS: Approved

OWNER:
  ARCHITECT: Claude Opus 4.5
  DEVELOPER: Claude Opus 4.5
  PM: Human User

PM_INTENT:
  ARCHITECT_ACTION:
    ALLOWED: false
    ALLOWED_ACTIONS: []
    WHY: "Step completed and approved"

SCOPE:
  - Calculate px_per_mm calibration from drum geometry
  - Apply calibration to convert pixel radii to physical sizes (mm)
  - Classify detections into size bins: 4mm, 6mm, 8mm, 10mm
  - Generate color-coded overlays by size class
  - Produce distribution statistics

OUT_OF_SCOPE:
  - Modifying pixel-space detections (x, y, r_px)
  - Temporal filtering
  - Quality metrics (STEP_08)
  - UI visualization (Phase 9)

INPUT:
  - Filtered detections from STEP_06: (x, y, r_px, conf)
  - Drum geometry from STEP_01: (center, radius_px)
  - Known drum diameter: 200mm
  - Golden frames from STEP_02

OUTPUT:
  - `src/classify.py`: Classification module
  - `src/step07_classify.py`: Test script
  - Classified detections: (x, y, r_px, conf, diameter_mm, cls)
  - `output/classify_test/`:
    - `{video}_{frame}_classified.png` — Color-coded overlay
    - `{video}_{frame}_classified.json` — Classified detections
    - `classification_summary.json` — Aggregate statistics

ALGORITHM:
  
  **Calibration Calculation**:
  ```python
  px_per_mm = drum_radius_px / (drum_diameter_mm / 2.0)
  # Example: 872px / 100mm = 8.72 px/mm for 4K video
  ```
  
  **Size Classification**:
  ```python
  diameter_px = 2 * r_px
  diameter_mm = diameter_px / px_per_mm
  
  size_bins = {
      "4mm": (2.0, 5.0),    # 2-5mm range
      "6mm": (5.0, 7.0),    # 5-7mm range
      "8mm": (7.0, 9.0),    # 7-9mm range
      "10mm": (9.0, 13.0),  # 9-13mm range
  }
  cls = match diameter_mm to size_bins, else "unknown"
  ```
  
  Rationale:
  - Target bead sizes: 3.94mm, 5.79mm, 7.63mm, 9.90mm
  - Bin ranges accommodate ±1mm detection variance
  - Classification is deterministic and recalculable

PARAMETERS_TO_EXPOSE:
  ```python
  SIZE_CONFIG = {
      "drum_diameter_mm": 200.0,
      "size_bins": {
          "4mm": (2.0, 5.0),
          "6mm": (5.0, 7.0),
          "8mm": (7.0, 9.0),
          "10mm": (9.0, 13.0),
      },
      "class_colors": {
          "4mm": (0, 255, 255),    # Yellow
          "6mm": (0, 255, 0),      # Green
          "8mm": (255, 165, 0),    # Orange
          "10mm": (255, 0, 0),     # Red
          "unknown": (128, 128, 128),  # Gray
      }
  }
  ```

CONFIDENCE_DEFINITION:
  - Confidence passed through unchanged from STEP_06
  - Only used for filtering, not classification

VALIDATION:
  - **Pixel-space preservation**: (x, y, r_px) unchanged by classification
  - **Calibration correctness**: px_per_mm matches drum geometry
  - **Classification coverage**: <5% unknown classifications
  - **Determinism**: Same input → same output
  - **Visual check**: Color-coded overlays show sensible distribution

RESULTS_ACHIEVED:
  Based on 18 golden frames across 3 videos:
  
  | Metric | Value |
  |--------|-------|
  | Total classified | 1,830 |
  | 4mm | 327 (17.9%) |
  | 6mm | 851 (46.5%) |
  | 8mm | 396 (21.6%) |
  | 10mm | 219 (12.0%) |
  | Unknown | 37 (2.0%) |
  
  Calibrations (px/mm):
  - IMG_6535 (4K): 8.72
  - IMG_1276 (1080p): 3.65
  - DSC_3310 (1080p): 4.96

ARTIFACTS_REQUIRED:
  - IMAGES:
    - `output/classify_test/{video}_frame_{idx}_classified.png` (18 frames)
  - STRUCTURED:
    - `output/classify_test/{video}_frame_{idx}_classified.json` (18 frames)
    - `output/classify_test/classification_summary.json`
  - CODE:
    - `src/classify.py`
    - `src/step07_classify.py`

TEST_SET:
  SOURCE: Filtered detections from STEP_06
  FRAMES:
    - All 18 golden frames
  SAMPLE_SIZE:
    - 18 frames across 3 videos

DEPENDENCIES:
  - STEP_01: Drum geometry (radius_px for calibration)
  - STEP_06: Filtered detections

FAILURE_MODES:
  1. **Incorrect px_per_mm**: Wrong drum diameter assumption
     - Mitigation: Verify against known bead sizes
  2. **Bin overlap**: Ambiguous size classification
     - Mitigation: Non-overlapping bins with buffer zones
  3. **High unknown rate**: Bins don't cover detection sizes
     - Mitigation: Expand bins if >5% unknown

ROLLBACK_PLAN:
  - Set all classifications to "unknown"
  - Returns unclassified detections

PM_DECISION:
  DECISION: Resolved
  NOTES: |
    PM approved 2025-12-12.
    - 98% classification rate (only 2% unknown)
    - Overlays generated for all 18 golden frames
    - Distribution validated: 46.5% 6mm, 21.6% 8mm, 17.9% 4mm, 12.0% 10mm
    - Ready for STEP_08

PHASE: Classification
BASELINE_REFERENCE:
  STEP_ID: "STEP_06"
  RUN_ID: "ITER_0007"
  HANDOFF: "rules/HANDOFF_PACKET.md"
ORDER_CONSTRAINT:
  MUST_FOLLOW_MAIN_MD: true
  OVERRIDE_REQUIRES_PM_APPROVAL: true

---

STEP_ID: STEP_08
TITLE: Quality Metrics
DATE_CREATED: 2025-12-12
STATUS: Approved

OWNER:
  ARCHITECT: Claude Opus 4.5
  DEVELOPER: Claude Opus 4.5
  PM: Human User

PM_INTENT:
  ARCHITECT_ACTION:
    ALLOWED: false
    ALLOWED_ACTIONS: []
    WHY: "Step completed and approved"

SCOPE:
  - Compute quality metrics for pipeline validation
  - Count stability (coefficient of variation across frames)
  - Size distribution stability (class proportion consistency)
  - Confidence behavior analysis (distribution, thresholdability)
  - Aggregate reporting across all videos
  - Acceptance criteria validation

OUT_OF_SCOPE:
  - Modifying detections or classifications
  - Ground truth annotation
  - Precision/recall (no ground truth available)
  - UI visualization (Phase 9)

INPUT:
  - Classified detections from STEP_07
  - Golden frames manifest from STEP_02
  - Acceptance criteria from ACCEPTANCE_METRICS.md

OUTPUT:
  - `src/metrics.py`: Quality metrics module
  - `src/step08_metrics.py`: Test script
  - `output/metrics/`:
    - `{video}_quality_report.json` — Per-video metrics
    - `aggregate_quality_report.json` — Cross-video summary

ALGORITHM:

  **1. Count Stability (CV)**:
  ```python
  counts = [frame.total_count for frame in frames]
  cv = std(counts) / mean(counts)
  # CV < 0.10: Excellent
  # CV < 0.20: Good
  # CV < 0.35: Acceptable
  # CV >= 0.35: Poor
  ```
  
  **2. Size Distribution Stability**:
  ```python
  for each class:
      proportions = [frame.class_count / frame.total for frame in frames]
      cv = std(proportions) / mean(proportions)
  # Per-class CV indicates distribution stability
  ```
  
  **3. Confidence Analysis**:
  ```python
  all_conf = [det.conf for det in all_detections]
  stats = {mean, median, std, min, max, histogram}
  # Check: range not collapsed, thresholdable
  ```
  
  **4. Acceptance Validation**:
  ```python
  acceptance = {
      count_stability_pass: cv < 0.35,
      confidence_range_pass: range > 0.3,
      unknown_class_pass: unknown_rate < 0.05,
      all_classes_present: all classes have detections
  }
  ```

PARAMETERS_TO_EXPOSE:
  ```python
  METRICS_CONFIG = {
      "cv_thresholds": {
          "excellent": 0.10,
          "good": 0.20,
          "acceptable": 0.35,
      },
      "acceptance_criteria": {
          "max_count_cv": 0.35,
          "min_confidence_range": 0.3,
          "max_unknown_rate": 0.05,
      }
  }
  ```

CONFIDENCE_DEFINITION:
  - This step analyzes confidence distribution
  - Does not modify confidence values

VALIDATION:
  - **Determinism**: Same input → same metrics
  - **Acceptance checks**: All criteria must pass
  - **Visual check**: Metrics align with visual inspection

RESULTS_ACHIEVED:
  | Metric | Value | Status |
  |--------|-------|--------|
  | Count CV | 0.255 | ✅ Acceptable |
  | Mean confidence | 0.676 | ✅ Good |
  | Confidence range | 0.438 | ✅ Pass |
  | Unknown rate | 2.3% | ✅ Pass |
  | All classes present | Yes | ✅ Pass |
  | **Overall** | **PASS** | ✅ |

  Size Distribution (mean %):
  - 4mm: 16.6% (±7.7%)
  - 6mm: 46.2% (±8.5%)
  - 8mm: 22.0% (±5.0%)
  - 10mm: 13.0% (±6.8%)
  - Unknown: 2.3% (±1.8%)

ARTIFACTS_REQUIRED:
  - STRUCTURED:
    - `output/metrics/IMG_6535_quality_report.json`
    - `output/metrics/IMG_1276_quality_report.json`
    - `output/metrics/DSC_3310_quality_report.json`
    - `output/metrics/aggregate_quality_report.json`
  - CODE:
    - `src/metrics.py`
    - `src/step08_metrics.py`

TEST_SET:
  SOURCE: Classified detections from STEP_07
  FRAMES:
    - All 18 golden frames
  SAMPLE_SIZE:
    - 18 frames across 3 videos

DEPENDENCIES:
  - STEP_07: Classified detections

FAILURE_MODES:
  1. **High CV**: Unstable counts indicate detection issues
     - Mitigation: Review frame-by-frame overlays
  2. **Confidence collapse**: Range too narrow
     - Mitigation: Adjust confidence formula in STEP_05

ROLLBACK_PLAN:
  - Metrics are read-only analysis
  - No data to rollback

PM_DECISION:
  DECISION: Resolved
  NOTES: |
    PM approved 2025-12-12.
    - All acceptance criteria pass
    - Count stability: Acceptable (CV=0.255)
    - Confidence behavior: Normal distribution
    - Ready for STEP_09

PHASE: Metrics
BASELINE_REFERENCE:
  STEP_ID: "STEP_07"
  RUN_ID: "ITER_0009"
  HANDOFF: "rules/HANDOFF_PACKET.md"
ORDER_CONSTRAINT:
  MUST_FOLLOW_MAIN_MD: true
  OVERRIDE_REQUIRES_PM_APPROVAL: true
