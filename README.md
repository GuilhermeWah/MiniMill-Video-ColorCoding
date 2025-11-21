# MGrinding Millr Quick Note 

Guys, quick overview before you move on. This repo is the repo we discussed earlier. I tried my best for documenting it in the clearest way possible. I’m following the component diagram I shared (FrameLoader ➜ ProcessorOrchestrator ➜ ResultsCache ➜ OverlayRenderer ➜ UI/Exporter) as closely as possible so everything is cleanly separated. Detection happens once, offline, so the live player just paints cached circles with no interrruption.

---

## To start, you guys can run, to set the env.

```powershell
# bootstrap or refresh the venv
scripts\setup.ps1

# run the full TDD gate
pytest

# sample CLI run on the Nikon(sample he gave us) clip that lives in content/
python scripts/run_detection.py --input content/DSC_3310.MOV `
    --output exports/detections.jsonl --config configs/sample.config.yaml
```

### Run the playback UI (Phase 3)

Once you have both the video file and the cached detections (JSONL), launch the PyQt player with:

```powershell
python -m mill_presenter.app `
    --video content/DSC_3310.MOV `
    --detections exports/detections.jsonl `
    --config configs/sample.config.yaml
```

`--config` is optional (defaults to `configs/sample.config.yaml`). The player wires `FrameLoader ➜ ResultsCache ➜ PlaybackController ➜ VideoWidget`, so playback never re-runs detection— it only reads the cached circles.

Why those scripts exist:
- `scripts/setup.ps1` – rebuilds `.venv` exactly like my machine. 
- `scripts/run.ps1` – placeholder launcher for the PyQt shell when we wire it up. (We'll implement Daniel's UI later. PyQT for now just to make it simpler to debug)
- `scripts/debug_vision.py` – opens `content/DSC_3310.MOV` with the ROI mask so you can spot check detections.
- `scripts/repro_synthetic.py` – reproduces the tiny synthetic clip the CLI test generates (useful when PyAV or OpenCV behave differently on CI). -- explanation later, why PyAV and not OpenCV

---

## Where I Documented Everything

| File | Why you should read it |
| --- | --- |
| `PLAN.md` | Phase roadmap + every finished task points to the test that proves it. If scope grows, I log it here immediately. |
| `docs/design_decisions.md` | The “why” behind architecture choices (NVDEC, JSONL cache, contour knobs, annulus logic). |
| `docs/technical_primer.md` | Made this kind of  walkthrough of the CV pipeline and each module. |
| `docs/testing_criteria.md` | Test driven development (tdd) checklist; every time I add/modify tests I describe the goal, risk, and how to verify. (thanks claude)|
| `docs/faq.md` | Every “why?”/“how?” I've/we been asking  is/will be recorded here so we don’t lose context. |
| `projectContext/mill_presenter_context.txt` | Rolling session log so you know what happened last time. |
| `.github/copilot-instructions.md` | The hard rules I’m forcing on myself (docs-first, FAQ logging, ROI safety, etc.). |

If you have a new question, drop it in `docs/faq.md`. If you finish/expand work, update `PLAN.md` the same moment. Try to keep same structure

---

## Repo Walkthrough

- `src/mill_presenter/core` – the diagram come to life: `playback.py` (PyAV + rotation + seeking fixes), `processor.py` (bilateral ➜ CLAHE ➜ Hough + contours + annulus + classification), `cache.py` (JSONL writer + RAM ring buffer), `orchestrator.py` (offline pass controller).
- `src/mill_presenter/ui` – PyQt shell that will use `OverlayRenderer` once Phase 3 kicks in.
- `configs/` – tuning knobs (`sample.config.yaml` now includes `vision.min_circularity`).
- `content/` – the real clip (`DSC_3310.MOV`) + ROI mask we share inside the team.
- `scripts/` – helpers for setup, ROI authoring, debugging, CLI runs.
- `tests/` – pytest suites for every core module plus the CLI integration.
- `exports/` – target folder for `detections.jsonl` and any exported frames.

---

## Workflow I’m Following (TDD + FAQ discipline)

I stay in a strict red/green/refactor loop:
1. Describe the task in `PLAN.md`.
2. Write the failing test under `tests/` (models, playback, processor, cache, orchestrator, or CLI).
3. Implement just enough under `src/mill_presenter/` to make it pass.
4. Run `pytest` and log the criteria/outcome in `docs/testing_criteria.md`.
5. Capture the reasoning (design trade-offs or tough Q&A) in `docs/faq.md` so nobody has to ping me later.

That FAQ rule exists because we kept asking “why dummy videos?” / “why JSONL? / Why Hough? Why Canny? param1, param2 etc” in chat—now every answer is searchable. Also, that component diagram I drew is being my  North Star: detection never leaks into rendering, toggles never re-run the processor, and exporters reuse `overlay.py` so the look stays consistent.

---

## Verification Notes

- `pytest` for the whole suite (≈2 seconds locally) after every change.
- Synthetic CLI test expects `px_per_mm = 15.0` and `vision.min_circularity = 0.65`; otherwise the perfect white circle won’t land in the 4 mm bin.
- Real footage: keep ROI masks in `content/`, and always review overlays via the cached `exports/detections.jsonl`—the UI must never trigger detection during playback.

txt on the WPP group  if anything feels off, but this README plus the docs above should be enough to get us rolling. 


==== IT'S NOT FINISHED YET,  The PLAN.MD  is updated, it shows where I'm/we're at.
