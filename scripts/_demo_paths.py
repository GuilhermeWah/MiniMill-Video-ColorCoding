from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

VIDEO_EXTS = (".mov", ".mp4", ".avi", ".mkv")


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _first_existing(paths: Iterable[Path]) -> Optional[Path]:
    for path in paths:
        if path.exists():
            return path
    return None


def resolve_demo_video(preferred_name: str = "DSC_3310.MOV") -> Path:
    """Return a demo video path that exists in this repo checkout.

    Order:
    1) testing_data/<preferred_name>
    2) data/<preferred_name>
    3) content/<preferred_name>
    4) first video file found in testing_data/, then data/, then content/
    """

    root = project_root()

    direct = _first_existing(
        [
            root / "testing_data" / preferred_name,
            root / "data" / preferred_name,
            root / "content" / preferred_name,
        ]
    )
    if direct is not None:
        return direct

    for folder in (root / "testing_data", root / "data", root / "content"):
        if not folder.exists():
            continue
        for ext in VIDEO_EXTS:
            for candidate in sorted(folder.glob(f"*{ext}")):
                return candidate

    raise FileNotFoundError(
        "No demo video found. Expected one of: "
        f"{root / 'testing_data' / preferred_name}, {root / 'data' / preferred_name}, {root / 'content' / preferred_name}"
    )


def resolve_roi_mask() -> Optional[Path]:
    root = project_root()
    return _first_existing(
        [
            root / "exports" / "roi_mask.png",
            root / "content" / "roi_mask.png",
            root / "roi_mask.png",
        ]
    )
