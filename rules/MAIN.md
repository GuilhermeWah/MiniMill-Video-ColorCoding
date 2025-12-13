# MAIN.md

## Purpose
This file is the **single mandatory entry point** for all agents (LLMs or humans) interacting with this repository.

Its sole purpose is to **enforce the development flow**.  
No work, reasoning, coding, or specification is valid unless it follows this file.

If there is a conflict between documents, **this file has the highest authority**.

---

## Mandatory Workflow (Must Be Followed Every Time)

0. **Read `HANDOFF_PACKET.md` first**
1. **Read** `CURRENT_STEP_RULES.md` **second**.
2. **Read** `CURRENT_STEP.md` **third**.
3. If `STATUS` is **not** `Approved`, **stop immediately** and request PM action.
4. Identify your role:
   - Architect → governed by `architect_agent.md`
   - Developer → governed by `developer_agent.md`
5. Execute **exactly one STEP**:
   - Architect: define or revise the STEP specification only.
   - Developer: implement only what the STEP requires.
6. Produce all required outputs and visual evidence.
7. Log results in `iteration_tracker.md` using the same `STEP_ID`.
8. **Stop.** Wait for PM decision per `PM_REVIEW_POLICY.md`.

No agent may proceed beyond Step 8 without explicit PM approval.

---
## Mandatory Development Order (Additive Rule)

The project MUST follow this high-level order unless explicitly overridden
by a PM-approved STEP:

1. Drum geometry & ROI stabilization
2. Golden frames lock (baseline validation set)
3. Preprocessing baseline stabilization
4. Candidate generation (pixel-space only)
5. Confidence definition
6. Filtering and cleanup
7. Calibration and size classification
8. Quality metrics
9. Visualization & playback features (includes UI development)
10. Export & delivery

**Note**: Phase 9 (Visualization) includes:
- UI application development (PySide6/Qt)
- Cache-based playback system
- Overlay rendering controls
- Statistics display and graphs
- User interaction features

This rule exists to prevent premature optimization and pipeline drift.

## Authority Order (Highest → Lowest)

0. Read `HANDOFF_PACKET.md` before acting
1. `MAIN.md`
2. `CURRENT_STEP_RULES.md`
3. `CURRENT_STEP.md`
4. `PM_REVIEW_POLICY.md`
5. `ACCEPTANCE_METRICS.md`
6. Role definition (`GEMINI.md` or `developer_agent.md`)
7. `iteration_tracker.md`
8. All other documents

If two documents disagree, the higher-ranked document **wins**.

---

## Non-Negotiable System Invariants

These rules are always in force, regardless of STEP content:

- **Classical Computer Vision only** (no deep learning)
- **Offline detection → cached results → visualization reads cache only**
- **Detection operates purely in pixel space**
- Calibration (`px_per_mm`) is applied **only after detection**
- CPU-only, deterministic execution
- Explainability and stability are prioritized over per-frame perfection

---

## Refusal Conditions (Hard Stop Rules)

An agent must **refuse to act** and report the issue if:

- `CURRENT_STEP.md` is missing or ambiguous
- `STATUS` is not `Approved`
- Required acceptance criteria are undefined
- Required outputs or evidence paths are unclear
- A request violates system invariants

Refusal is correct behavior, not failure.

---

## What This File Is Not

- Not a specification document
- Not a backlog
- Not an implementation guide

It is a **control file** that guarantees discipline, traceability, and safety.

---

End of MAIN.md

