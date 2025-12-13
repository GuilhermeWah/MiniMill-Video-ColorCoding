# PM_REVIEW_POLICY.md

## Purpose
Defines the PM approval gate for the Grinding Mill Detection Pipeline.
This policy prevents pipeline drift and ensures every change is:
- testable,
- evidenced,
- explainable,
- and reversible.

---

## Roles

### PM (Project Manager)
- Approves/rejects each STEP.
- Ensures validation evidence exists.
- Ensures acceptance metrics are satisfied or exceptions are justified.

### Architect Agent
- Specifies STEP requirements in `CURRENT_STEP.md`.
- Defines parameters to expose, failure modes, and confidence semantics.

### Developer Agent
- Implements exactly the approved STEP.
- Produces required artifacts and logs results in `iteration_tracker.md`.

---

## Approval Levels

### 1) Approved
All required artifacts exist and acceptance checks pass.
- `CURRENT_STEP.md` must be set to `STATUS: Approved`
- `iteration_tracker.md` entry must show `PM Review: Approved`

### 2) Approved with Notes
Minor issues exist but are acceptable for continuation.
- Notes must list required follow-up tasks.
- Follow-ups become the next STEP or are attached as TODOs.

“Approved with Notes” corresponds to:
- PM_DECISION: Approved
- with follow-up tasks explicitly listed in NOTES.


### 3) Rejected
The change is not acceptable.
Common reasons:
- no evidence exports,
- regression in key metrics,
- unclear behavior,
- step violates invariants.

### 4) Blocked
Progress must stop until a blocking defect is fixed.
Blocking defects include:
- non-determinism,
- px/mm coupling (calibration changes affect detections),
- missing mandatory outputs (e.g., conf missing when required).

---

## Minimum Evidence Required for Review

For any STEP that affects image outputs:
- At least 1 overlay `.png` per tested frame set
- Any intermediate debug export required by the STEP (e.g., masks, candidates)
- A structured export with detections (when applicable), containing:
  - `(x, y, r_px, conf, cls?)`
- `output/run_manifest.json` containing:
  - commit hash (or version tag)
  - config used
  - videos + frames tested
  - artifact paths
  - timing summary

If any required artifact is missing → **Rejected** (or **Blocked** if mandatory).

---

## Baseline & Regression Rules

- The baseline is the **last Approved STEP** (or a pinned reference run).
- Regressions must be:
  - quantified (using `ACCEPTANCE_METRICS.md`), and
  - explained (why it’s acceptable or how it will be fixed).

If the change improves one metric but worsens another:
- the PM decides using the project objective: stability + trust > per-frame perfection.

---

## Rollback Policy

If a STEP is Rejected or Blocked:
- revert to last approved commit/config
- log the rollback in `iteration_tracker.md`
- create a new STEP titled: `Fix regression from <STEP_ID>`

---

## UI/Visualization Review Criteria

For Phase 9 (Visualization & Playback), the following criteria apply:

### Functional Review
- All FRs in `docs/UI_IMPLEMENTATION_PLAN.md` must be verified
- Keyboard shortcuts must function as specified
- State machine transitions must be correct

### Performance Review
- Playback must maintain ≥30 FPS
- Overlay toggle must update in <50ms
- UI must remain responsive during video loading

### Visual Review
- Layout must match mockup proportions
- Colors must match specification (Blue=4mm, Green=6mm, Orange=8mm, Red=10mm)
- Dark theme must be consistent

### Architecture Compliance
- Playback must read cache only (no real-time CV)
- Detection data must not be modified by visualization layer
- px_per_mm changes must not affect cached detections

---

## Phase Gates (Optional but Recommended)
The PM may additionally enforce approval at phase boundaries:
- Preprocessing stable
- Candidate generation stable
- Filters stable
- Separation (watershed) stable
- Classification stable
- **Visualization/UI stable**
- Overlay/export stable

---

End of PM_REVIEW_POLICY.md
