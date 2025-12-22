# Grinding Mill - Quick Note

Guys, quick overview before you move on. This repo is the repo we discussed earlier. I tried my best for documenting it in the clearest way possible. I’m following the component diagram I shared (FrameLoader ➜ ProcessorOrchestrator ➜ ResultsCache ➜ OverlayRenderer ➜ UI/Exporter) as closely as possible so everything is cleanly separated. Detection happens once, offline, so the live player just paints cached circles with no interrruption.

---

## To start, you guys can run, to set the env.

```powershell
# bootstrap or refresh the venv
scripts\setup.ps1

# run the full TDD gate
pytest

# sample CLI run on the bundled demo clip (committed in testing_data/)
python scripts/run_detection.py --input testing_data/DSC_3310.MOV `
    --output exports/detections.jsonl --config configs/sample.config.yaml
```

### Run the playback UI (Phase 3)

Once you have both the video file and the cached detections (JSONL), launch the PyQt player with:

```powershell
python -m mill_presenter.app `
    --video testing_data/DSC_3310.MOV `
    --detections exports/detections.jsonl `
    --config configs/sample.config.yaml
```

`--config` is optional (defaults to `configs/sample.config.yaml`). The player wires `FrameLoader ➜ ResultsCache ➜ PlaybackController ➜ VideoWidget`, so playback never re-runs detection— it only reads the cached circles.

Why those scripts exist:
- `scripts/setup.ps1` – rebuilds `.venv` exactly like my machine. 
- `scripts/run.ps1` – placeholder launcher for the PyQt shell when we wire it up. (We'll implement Daniel's UI later. PyQT for now just to make it simpler to debug)
- `scripts/debug_vision.py` – opens the bundled demo clip in `testing_data/` (ROI mask optional) so you can spot check detections.
- `scripts/repro_synthetic.py` – reproduces the tiny synthetic clip the CLI test generates (useful when PyAV or OpenCV behave differently on CI). -- explanation later, why PyAV and not OpenCV

---

## Where I Documented Everything

| File | Why you should read it |
| --- | --- |
| `docs/architecture_guide.md` | Architecture guide + detection pipeline explanation (this is the main doc). |
| `docs/technical_primer.md` | Walkthrough of the CV pipeline and the key modules. |
| `docs/tuning_log.md` | Running log of experiments / tuning knobs / outcomes. |
 
If you have a new question, drop it in the Q&A section inside `docs/architecture_guide.md` (or keep local notes in `docs/internal/`).

---

## Repo Walkthrough

- `src/mill_presenter/core` – the diagram come to life: `playback.py` (PyAV + rotation + seeking fixes), `processor.py` (bilateral ➜ CLAHE ➜ Hough + contours + annulus + classification), `cache.py` (JSONL writer + RAM ring buffer), `orchestrator.py` (offline pass controller).
- `src/mill_presenter/ui` – PyQt shell that will use `OverlayRenderer` once Phase 3 kicks in.
- `configs/` – tuning knobs (`sample.config.yaml` now includes `vision.min_circularity`).
- `testing_data/` – the bundled demo clip (`DSC_3310.MOV`) used for reproducible runs.
- `content/` – optional ROI masks and local-only assets.
- `scripts/` – helpers for setup, ROI authoring, debugging, CLI runs.
- `tests/` – pytest suites for every core module plus the CLI integration.
- `exports/` – target folder for `detections.jsonl` and any exported frames.

---

## Workflow I’m Following (TDD + FAQ discipline)

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

---

## Git Notes (local-only stuff)

These folders are intentionally ignored (they're for local notes/outputs, not the shared repo):
- `docs/internal/`
- `docs/test_reports/`
- `quantitative_analysis/`

txt on the WPP group  if anything feels off, but this README plus the docs above should be enough to get us rolling. 


==== IT'S NOT FINISHED YET, but the docs above show where I'm/we're at.
