<!-- MPE Target: This document is authored and intended to be rendered using Markdown Preview Enhanced (MPE).
     Reference: https://shd101wyy.github.io/markdown-preview-enhanced/#/ -->

# MillPresenter — Legacy-to-Refactor Change Log (Architecture and Pipeline)

**Document Type:** Formal Change Summary (Legacy → Refactored)  
**Primary Use:** Input artifact for subsequent SRS elaboration  
**Rendering Target:** Markdown Preview Enhanced (MPE)  
**Date:** 2025-12-12  
**Repository:** `MiniMill-Video-ColorCoding` (branch: `millpresenter-final`)  

---

## Table of Contents

1. [Purpose and Scope](#1-purpose-and-scope)  
2. [Source Materials and Authority](#2-source-materials-and-authority)  
3. [Terminology](#3-terminology)  
4. [Executive Summary of What Changed](#4-executive-summary-of-what-changed)  
5. [System Architecture Evolution](#5-system-architecture-evolution)  
   1. [Legacy (Reference Model)](#51-legacy-reference-model)  
   2. [Refactored (Current Model)](#52-refactored-current-model)  
   3. [Primary Architectural Differences](#53-primary-architectural-differences)  
6. [Pipeline Evolution (Primary Focus)](#6-pipeline-evolution-primary-focus)  
   1. [Step-Based Pipeline Formalization](#61-step-based-pipeline-formalization)  
   2. [Preprocessing: Stabilized, Configured, Deterministic](#62-preprocessing-stabilized-configured-deterministic)  
   3. [Candidate Generation: Over-Detect Then Filter](#63-candidate-generation-over-detect-then-filter)  
   4. [Confidence: Defined as a First-Class Output](#64-confidence-defined-as-a-first-class-output)  
   5. [Filtering: Explicit Rim/Confidence/NMS Contract](#65-filtering-explicit-rimconfidencenms-contract)  
   6. [Classification: Post-Detection Calibration Decoupling](#66-classification-post-detection-calibration-decoupling)  
   7. [Metrics: Quality Gates and Acceptance Checks](#67-metrics-quality-gates-and-acceptance-checks)  
7. [UI and Visualization Evolution (Secondary)](#7-ui-and-visualization-evolution-secondary)  
8. [Data, Caching, and Artifacts](#8-data-caching-and-artifacts)  
9. [Module and Responsibility Mapping (Legacy → Refactor)](#9-module-and-responsibility-mapping-legacy--refactor)  
10. [Known Divergences and Items Requiring PM Resolution](#10-known-divergences-and-items-requiring-pm-resolution)  
11. [Appendix: Refactored Pipeline Contract (Normative Summary)](#11-appendix-refactored-pipeline-contract-normative-summary)

---

## 1. Purpose and Scope

This document formally describes **what changed** between the **legacy implementation** and the **refactored MillPresenter implementation**, and **why** those changes were made. It is written to support:

- academic and technical evaluation,
- engineering onboarding,
- later transformation into a Software Requirements Specification (SRS).

**Scope emphasis:** the **offline computer vision pipeline** (steps, artifacts, invariants) is the primary focus. UI changes are included only to the extent that they reflect pipeline architecture decisions (e.g., cache-backed playback).

This document is not a redesign proposal. It reports the evolution already present in the provided repository and documentation.

---

## 2. Source Materials and Authority

### 2.1 Legacy reference (historical, contextual)
- `docs/final_documentation/final_report.md` (legacy description of modules/requirements)
- `docs/final_documentation/old_solution` (legacy codebase reference for cross-comparison)

### 2.2 Refactored implementation (authoritative)
- `CURRENT_STEP.md` (STEP_01–STEP_08 completed/approved; defines pipeline contracts)
- `documentation_final/PROJECT_OVERVIEW.md` (project purpose and architecture intent)
- `documentation_final/PIPELINE_ANALYSIS_COMPLETE.md` (pipeline analysis narrative)
- `src/` package (pipeline implementation)
- `ui/` package (PySide6 playback/visualization tooling)

### 2.3 Authority rules for this document
- The **refactored codebase and step contracts** are treated as authoritative for current behavior.
- The **legacy system** is referenced neutrally for context and motivation, not as a current requirement source.

---

## 3. Terminology

- **Legacy system:** initial implementation described in `final_report.md` and the `old_solution` reference document.
- **Refactored system:** current implementation represented by `src/`, `ui/`, and `CURRENT_STEP.md`.
- **Offline detection:** computer vision processing performed prior to playback, producing cached results.
- **Cache-backed playback:** UI renders overlays strictly from cached detection/classification outputs.
- **Pixel-space:** measurements in pixels: `(x, y, r_px)`; **calibration must not change these**.
- **Calibration decoupling:** `px_per_mm` is applied only after detection for mm conversion/classification.

---

## 4. Executive Summary of What Changed

The refactored system evolves the project from a monolithic “processor + UI” concept into a **step-governed, artifact-driven pipeline** with explicit contracts for determinism and auditability.

Key changes:

1. **Pipeline governance became explicit and enforceable.**  
   The refactored system formalizes the pipeline into STEP_01–STEP_08 with clearly defined inputs, outputs, validation, failure modes, and required artifacts.

2. **Detections are standardized as pixel-space records with confidence.**  
   The refactored pipeline produces detections as `(x, y, r_px, conf)` consistently, enabling thresholding, filtering, and reliable visualization.

3. **Filtering is explicit and contract-driven.**  
   Rim filtering, confidence thresholding, and non-maximum suppression (NMS) are defined as distinct, ordered operations with expected outcomes.

4. **Calibration and classification are isolated from detection.**  
   The refactored system enforces calibration decoupling: changing `px_per_mm` must not change which objects are detected or their pixel geometry.

5. **Quality metrics are a formal pipeline step.**  
   STEP_08 introduces acceptance checks (count stability, confidence behavior, unknown-rate constraints) to support repeatable review.

6. **UI implementation standardizes on PySide6 and reads from cache.**  
   The refactored UI prioritizes stable playback and trustable overlays, consistent with the “detect once, play forever” philosophy.

---

## 5. System Architecture Evolution

### 5.1 Legacy (Reference Model)

The legacy documentation describes a modular architecture including:

- **FrameLoader** (video decoding; explicitly described as using PyAV for accurate seeking),
- **VisionProcessor** (preprocess + detection + classification),
- **ResultsCache** (append-only JSONL strategy),
- **OverlayRenderer** (shared rendering for UI and export),
- **ProcessorOrchestrator** (batch pipeline execution),
- UI controllers and export threads.

The following diagram captures the legacy *conceptual* responsibilities as described (not as a code diff).

```mermaid
flowchart LR
  V[Video File] --> FL[FrameLoader<br/>(PyAV-based seeking)]
  FL --> VP[VisionProcessor<br/>(Preprocess + Detection + Classification)]
  VP --> RC[ResultsCache<br/>(JSONL append-only)]
  RC --> UI[GUI Playback<br/>(class toggles)]
  RC --> OR[OverlayRenderer<br/>(shared)]
  OR --> EX[ExportThread<br/>(MP4 with overlays)]
```

**Interpretation:** The legacy model expresses the correct separation intent (offline vs playback), and includes an explicit requirement for shared rendering consistency between UI and exports.

### 5.2 Refactored (Current Model)

The refactored system implements:

- a **pipeline package** (`src/`) with step scripts and modules,
- a **UI application** (`ui/`) implemented in **PySide6**, with cache-backed overlay rendering.

```mermaid
flowchart TD
  subgraph OfflinePipeline[src/ (Offline Pipeline)]
    S01[STEP_01 Drum Geometry & ROI] --> S02[STEP_02 Golden Frames]
    S02 --> S03[STEP_03 Preprocess]
    S03 --> S04[STEP_04 Detect Candidates]
    S04 --> S05[STEP_05 Confidence]
    S05 --> S06[STEP_06 Filter & Cleanup]
    S06 --> S07[STEP_07 Calibrate & Classify]
    S07 --> S08[STEP_08 Metrics]
  end

  subgraph UI[ui/ (Playback & Visualization)]
    VC[VideoController + DetectionCache] --> VW[VideoViewport (Overlay Rendering)]
    RP[RightPanel (Controls)] --> VC
    BB[BottomBar (Transport)] --> VC
  end

  S06 --> VC
  S07 --> VC
  S08 --> RP
```

**Interpretation:** The refactored architecture strengthens the pipeline contracts and emphasizes deterministic outputs and review artifacts. The UI is designed to consume cached detections/classifications and render them interactively.

### 5.3 Primary Architectural Differences

| Area | Legacy (as described) | Refactored (as implemented) | Rationale |
|---|---|---|---|
| Pipeline structure | Module-based “VisionProcessor” concept | Step-governed pipeline: STEP_01–STEP_08 | Improves traceability, repeatability, and academic reviewability |
| Video decode in UI | PyAV referenced for frame-accurate seeking | OpenCV `VideoCapture` in UI layer | Reduces dependencies; integrates with existing OpenCV pipeline tooling |
| Cache format | JSONL append-only caching explicitly stated | Structured JSON artifacts per step (and cache folders) | Aligns with step outputs and review artifacts; append-only guarantees may be partial/pending |
| Rendering consistency | Shared `OverlayRenderer` for UI + export | Viewport overlays implemented in UI; export pipeline not fully specified in UI layer | Focus placed on trustworthy playback; export consistency is a separate delivery concern |
| Quality assurance | Mostly qualitative/manual validation | STEP_08 introduces acceptance checks and aggregated reports | Formalizes stability expectations and supports gating |

---

## 6. Pipeline Evolution (Primary Focus)

### 6.1 Step-Based Pipeline Formalization

**Change:** The refactored pipeline is organized into sequential, validated steps with explicit contracts in `CURRENT_STEP.md`.

**Why it matters:** This format supports:

- consistent evaluation using golden frames,
- deterministic repeatability claims,
- structured artifacts for inspection (overlays + JSON exports),
- clear boundaries between preprocessing, detection, scoring, filtering, classification, and metrics.

### 6.2 Preprocessing: Stabilized, Configured, Deterministic

**Legacy description:** Preprocessing includes grayscale conversion, bilateral filtering, CLAHE, and related enhancements.

**Refactored implementation:** STEP_03 defines and validates a preprocessing pipeline with configurable toggles and deterministic outputs, including staged debug images.

**Reasoning:** The problem domain includes glare and uneven illumination; deterministic preprocessing improves edge clarity and reduces failure variance across frames while preserving auditability through intermediate artifacts.

### 6.3 Candidate Generation: Over-Detect Then Filter

**Legacy description:** Dual-path detection (Hough + contour analysis) was specified.

**Refactored implementation:** STEP_04 explicitly performs **HoughCircles** candidate generation with wide margins (“over-detect”) and defers cleanup to later steps.

**Reasoning:** In dense scenes, conservative detection can miss beads; a controlled over-detection stage paired with explicit filtering yields more stable behavior and is easier to validate in isolation.

> **Note:** The “Contour Analysis” secondary path is described in the legacy report. Its presence in the refactored pipeline must be verified from `src/` and—if not implemented—treated as an intentional scope reduction or deferred enhancement (see Section 10).

### 6.4 Confidence: Defined as a First-Class Output

**Legacy description:** Confidence scoring existed conceptually.

**Refactored implementation:** STEP_05 defines confidence as a deterministic scalar `conf ∈ [0, 1]` per detection, computed from observable evidence (edge strength, consistency, interior properties, etc.) and intended to be thresholdable.

**Reasoning:** Confidence enables:

- deterministic filtering (STEP_06),
- meaningful overlay visibility controls in UI,
- quality metric analysis (STEP_08).

This supports the project objective emphasizing stable overlays and user trust.

### 6.5 Filtering: Explicit Rim/Confidence/NMS Contract

**Legacy description:** Filtering includes ROI validation, brightness thresholding, annulus logic, and NMS.

**Refactored implementation:** STEP_06 defines a **three-stage filter** applied in fixed order:

1. rim margin rejection,
2. minimum confidence threshold,
3. NMS to merge overlaps.

**Reasoning:** The problem scene contains strong rim/bolt artifacts; separating “full ROI for preprocessing” from “rim margin filtering later” reduces false positives while preserving beads near the edge for earlier stages. NMS is treated as a final consolidation step to avoid suppressing before confidence thresholding.

### 6.6 Classification: Post-Detection Calibration Decoupling

**Legacy description:** Calibration allows px/mm conversion based on references; classification uses calibrated diameters.

**Refactored implementation:** STEP_07 performs:

- calibration from drum geometry (`px_per_mm = drum_radius_px / (drum_diameter_mm/2)`),
- post-hoc mm conversion and bin classification.

**Reasoning:** The refactored system enforces a core invariant:

- calibration must **not** change detection geometry `(x, y, r_px)`,
- calibration only affects derived values like `diameter_mm` and `cls`.

This improves scientific defensibility and reduces coupling between measurement assumptions and raw evidence.

### 6.7 Metrics: Quality Gates and Acceptance Checks

**Legacy description:** Performance and quality were primarily stated as expectations (e.g., target FPS, stability).

**Refactored implementation:** STEP_08 computes quality metrics and validates acceptance checks such as:

- count stability (CV),
- confidence distribution range,
- unknown classification rate,
- class presence.

**Reasoning:** Without ground truth, the system still requires objective stability gates for academic review and regression control. Metrics act as a consistent proxy for reliability under constrained evaluation conditions.

---

## 7. UI and Visualization Evolution (Secondary)

**Legacy description:** GUI built with PyQt5/PyQt6 references; shared renderer; export thread and progress dialog; emphasis on 60 FPS overlays.

**Refactored implementation:** UI is implemented in **PySide6**, with modules under `ui/`:

- `video_controller.py` for playback control and frame access,
- `widgets/video_viewport.py` for QPainter overlay rendering,
- panels (`right_panel.py`, `bottom_bar.py`, etc.) for interaction.

**Reasoning:** The refactored UI aligns to the architecture goal: smooth playback and trustworthy overlays from cached results. Parameter tuning and preview concepts may exist in UI, but the core requirement is to maintain cache-backed playback without implicit re-detection during playback.

---

## 8. Data, Caching, and Artifacts

### 8.1 Legacy caching intent
The legacy report explicitly states **JSONL append-only** caching to reduce corruption risk during long runs.

### 8.2 Refactored artifact model
The refactored system operationalizes caching primarily through **step outputs**:

- per-step overlay images for visual inspection,
- JSON exports per frame and aggregate summaries,
- explicit manifests for golden frames and step runs (as defined in step contracts).

This supports reviewability and deterministic regression checks.

> **Constraint note:** If append-only crash safety is still required as a formal requirement, confirm whether the refactored cache format includes JSONL append-only semantics. If it does not, this is a divergence requiring an explicit PM decision (see Section 10).

---

## 9. Module and Responsibility Mapping (Legacy → Refactor)

This mapping is conceptual and based on described responsibilities (not a code diff):

| Legacy Component (as described) | Refactored Equivalent | Notes |
|---|---|---|
| FrameLoader (PyAV decode + seeking) | `ui/video_controller.py` (OpenCV decode in UI); offline frame handling via step scripts | Library change: PyAV → OpenCV in UI path |
| VisionProcessor (preprocess+detect+classify) | `src/preprocess.py`, `src/detect.py`, `src/confidence.py`, `src/filter.py`, `src/classify.py` | Responsibilities decomposed into step modules |
| ResultsCache (JSONL, append-only) | Step outputs + cache folders (`output/*`, `src/cache*`) | Exact append-only semantics require verification |
| OverlayRenderer (shared UI/export) | `ui/widgets/video_viewport.py` (UI overlays); pipeline overlays produced by step scripts | Export renderer parity not fully specified |
| ProcessorOrchestrator | Step scripts (`src/step0X_*.py`) | Orchestration is explicit by step execution |
| ExportThread (MP4 export) | Not confirmed in refactored UI/module list | Export capability may be pending / separate step |

---

## 10. Known Divergences and Items Requiring PM Resolution

The following items are inconsistencies between the legacy report statements and the refactored implementation artifacts provided. They must be explicitly resolved at the PM level before being elevated to SRS “must” requirements.

1. **Dual-Path Detection (Hough + Contour)**  
   - Legacy report: explicitly required on every frame.  
   - Refactored pipeline (per step contracts shown): candidate generation is HoughCircles-based; contour path is not explicitly confirmed.  
   **PM decision required:** Is contour analysis a removed requirement, deferred enhancement, or implemented elsewhere?

2. **Annulus Logic (inner-hole rejection)**  
   - Legacy report: explicitly described as part of filtering.  
   - Refactored pipeline: filtering is rim/conf/NMS; annulus logic is not explicitly confirmed in the step contracts shown.  
   **PM decision required:** Confirm whether annulus rejection exists in refactored `src/` and, if not, whether it remains a requirement.

3. **JSONL append-only caching as a reliability requirement**  
   - Legacy report: defined as an explicit reliability measure.  
   - Refactored pipeline: uses structured JSON exports and per-step artifacts; append-only caching is not guaranteed by the shown contracts.  
   **PM decision required:** Retain JSONL append-only as a requirement, or accept refactored artifact approach as sufficient.

4. **Export (MP4 with overlays “baked in”)**  
   - Legacy report: explicit export requirement (threaded, progress dialog).  
   - Refactored UI modules: export workflow is not confirmed in the provided module list.  
   **PM decision required:** Confirm export scope and whether it is implemented, deferred, or out-of-scope for the refactored build.

5. **Rotation metadata handling**  
   - Legacy report: explicit auto-rotation requirement.  
   - Refactored UI: rotation handling is not confirmed from the provided snippets.  
   **PM decision required:** confirm whether rotation correction is implemented and where (offline vs UI decode path).

---

## 11. Appendix: Refactored Pipeline Contract (Normative Summary)

The following constraints are central to the refactored system as represented by the step governance:

1. **Classical CV only** (OpenCV/NumPy; CPU-only; deterministic behavior expected).  
2. **Detection must remain pixel-space**: outputs include `(x, y, r_px)` plus `conf`, with optional `cls` added after classification.  
3. **Calibration decoupling**: changing `px_per_mm` must not change pixel-space detections.  
4. **Offline detection + cache-backed playback**: playback uses cached results; interactive overlays should not require reprocessing detections.

These constraints should be treated as binding in the eventual SRS unless superseded by explicit PM decision.

---