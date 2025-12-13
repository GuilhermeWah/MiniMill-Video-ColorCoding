# CURRENT_STEP_RULES.md

## Purpose
**This file contains ONLY the active STEP rules. The YAML lives in `CURRENT_STEP.md`.**

All agents must treat this file as authoritative:
- Architect Agent **specifies** the STEP in `CURRENT_STEP.md`.
- This file defines the schema and governance.
- Developer Agent **implements only** what is specified here.
- Results are logged in `iteration_tracker.md`.
- PM (Project Manager) **approves/rejects** the STEP here (and in the tracker entry).
- Architect may **edit only** `CURRENT_STEP.md`.
- Developer may **not edit** `CURRENT_STEP.md` or any `rules/*.md`.
- No agent may **edit** `MAIN.md` or any `rules/*.md` unless the active step explicitly authorizes “Governance Change”.


---

## Active STEP Interpretation Rule (Additive)

- The **Active STEP** is defined by the single YAML block in `CURRENT_STEP.md`.
- `CURRENT_STEP_RULES.md` contains schema/examples only and never defines active state.
- Template/schema examples in this file do **not** override or invalidate the Active STEP block.
- A STEP with `STATUS: Draft` is considered **defined but not approved** (it is NOT “undefined”).
- If no Active STEP YAML block exists, then the active step is considered **missing**, and the Architect must request PM action.
- Keep only:
  - interpretation rule
  - required schema (the YAML fields and meaning)
  - constraints about what may/may not be edited
  - “how to update” guidance

But do **not** include anything that suggests rules file is where the active step lives.

**Handshake requirement:**
- When producing the Rule Handshake, you must extract `STEP_ID`, `PHASE`, and `STATUS` from the **Active STEP YAML block**, not from the template header.



---

## STEP Header (Required)

```yaml
STEP_ID: STEP_XX
TITLE: <Short descriptive name>
DATE_CREATED: 2025-12-11
STATUS: Draft | ReadyForDev | InDev | ReadyForReview | Approved | Rejected | Blocked

OWNER:
  ARCHITECT: Gemini 3 Pro 
  DEVELOPER: Claude Opus 4.5
  PM: <name>

PM_INTENT:
  ARCHITECT_ACTION:
    ALLOWED: false
    ALLOWED_ACTIONS:
      - DEFINE_STEP_SPEC   # or empty
    WHY: ""


SCOPE:
  - <What is in-scope>
OUT_OF_SCOPE:
  - <What is explicitly NOT in-scope>

INPUT:
  - <Expected input data type and shape>
OUTPUT:
  - <Expected output structure>
  - Includes per-object confidence score (`conf`) in range [0,1] (if detections are emitted)

ALGORITHM:
  - <Technique or approach; rationale required>

PARAMETERS_TO_EXPOSE:
  - <Configurable value name + purpose>

CONFIDENCE_DEFINITION:
  - <What `conf` represents and how it is computed conceptually>

VALIDATION (Must be Observable):
  - <Acceptance checks; reference `ACCEPTANCE_METRICS.md`>

ARTIFACTS_REQUIRED:
  - IMAGES:
      - <paths to required png exports>
  - STRUCTURED:
      - <paths to required json/csv/jsonl exports>
  - MANIFEST:
      - output/run_manifest.json

TEST_SET:
  VIDEOS:
    - <video filename(s) or identifiers>
  FRAMES:
    - <frame indices or timecodes>
  SAMPLE_SIZE:
    - <N frames across M videos>

DEPENDENCIES:
  - <Other steps/files required>

ROLLBACK_PLAN:
  - <How to revert if regressions occur>

PM_DECISION:
  DECISION: Pending | Approved | Rejected | Blocked
  NOTES: <PM notes>

```

---

## Phase & Order Enforcement (Additive)

Every STEP must declare its phase, and the PM must ensure it follows the order defined in `MAIN.md`.

Add these fields to every STEP YAML block:

```yaml
PHASE: Foundation | ValidationSet | Preprocessing | CandidateGen | Confidence | Filtering | Calibration | Metrics | Visualization | UI | Export
BASELINE_REFERENCE:
  STEP_ID: <last approved STEP>
  RUN_ID: <baseline run id>
  HANDOFF: rules/HANDOFF_PACKET.m
ORDER_CONSTRAINT:
  MUST_FOLLOW_MAIN_MD: true
  OVERRIDE_REQUIRES_PM_APPROVAL: true


A STEP may not change its PHASE after approval.
Changing PHASE requires creating a new STEP.
  
```

---

## Active STEP (Additive Placeholder)

If you have not defined an active STEP yet, use this minimal starting block:

```yaml
STEP_ID: STEP_01
TITLE: Drum Geometry & ROI Stabilization
PHASE: Foundation
STATUS: Draft
PM_DECISION:
  DECISION: Pending
  NOTES: ""
```
