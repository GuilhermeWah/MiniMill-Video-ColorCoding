from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Dict, Iterable, List, Optional, Tuple

from mill_presenter.core.models import Ball


# NOTE: Avoid magic numbers.
# These defaults are used only when a value is not provided by config.
DEFAULT_IOU_THRESHOLD = 0.30
DEFAULT_MAX_CENTER_DISTANCE_PX = 20.0
DEFAULT_MAX_LOST_FRAMES = 2


@dataclass
class _Track:
    track_id: int
    last_ball: Ball
    last_frame_id: int
    lost_frames: int = 0


class BallTracker:
    """Assigns persistent track IDs to per-frame detections.

    This runs during the *one-time detection pass* so IDs are persisted into JSONL.

    Matching strategy (MVP):
    - Consider only same-size class matches (cls must match).
    - Compute circle IoU + center distance.
    - Greedy match by best IoU.

    The goal is stable overlays, not perfect multi-object tracking.
    """

    def __init__(
        self,
        *,
        iou_threshold: float = DEFAULT_IOU_THRESHOLD,
        max_center_distance_px: float = DEFAULT_MAX_CENTER_DISTANCE_PX,
        max_lost_frames: int = DEFAULT_MAX_LOST_FRAMES,
    ) -> None:
        self.iou_threshold = float(iou_threshold)
        self.max_center_distance_px = float(max_center_distance_px)
        self.max_lost_frames = int(max_lost_frames)

        self._next_id = 1
        self._tracks: Dict[int, _Track] = {}

    @classmethod
    def from_config(cls, config: dict) -> "BallTracker":
        tracking_cfg = (config or {}).get("tracking", {})
        return cls(
            iou_threshold=float(tracking_cfg.get("iou_threshold", DEFAULT_IOU_THRESHOLD)),
            max_center_distance_px=float(
                tracking_cfg.get("max_center_distance_px", DEFAULT_MAX_CENTER_DISTANCE_PX)
            ),
            max_lost_frames=int(tracking_cfg.get("max_lost_frames", DEFAULT_MAX_LOST_FRAMES)),
        )

    def reset(self) -> None:
        self._next_id = 1
        self._tracks.clear()

    def update(self, frame_id: int, balls: List[Ball]) -> List[Ball]:
        """Assign track_id to each Ball in the provided list."""
        self._age_tracks(seen_any=False)

        if not balls:
            self._prune_tracks()
            return balls

        if not self._tracks:
            for ball in balls:
                self._assign_new(ball, frame_id)
            return balls

        track_ids = list(self._tracks.keys())
        candidates = self._build_candidate_matches(balls, track_ids)

        matched_dets: set[int] = set()
        matched_tracks: set[int] = set()

        for iou, det_idx, track_id in candidates:
            if det_idx in matched_dets or track_id in matched_tracks:
                continue

            ball = balls[det_idx]
            ball.track_id = track_id
            track = self._tracks[track_id]
            track.last_ball = ball
            track.last_frame_id = frame_id
            track.lost_frames = 0

            matched_dets.add(det_idx)
            matched_tracks.add(track_id)

        for det_idx, ball in enumerate(balls):
            if det_idx in matched_dets:
                continue
            self._assign_new(ball, frame_id)

        self._age_tracks(seen_any=True, matched_tracks=matched_tracks)
        self._prune_tracks()
        return balls

    def _assign_new(self, ball: Ball, frame_id: int) -> None:
        ball.track_id = self._next_id
        self._tracks[self._next_id] = _Track(
            track_id=self._next_id,
            last_ball=ball,
            last_frame_id=frame_id,
            lost_frames=0,
        )
        self._next_id += 1

    def _build_candidate_matches(
        self, balls: List[Ball], track_ids: List[int]
    ) -> List[Tuple[float, int, int]]:
        matches: List[Tuple[float, int, int]] = []

        for det_idx, ball in enumerate(balls):
            for track_id in track_ids:
                track = self._tracks[track_id]
                prev = track.last_ball

                # Require same class for stability.
                if prev.cls != ball.cls:
                    continue

                dist = _center_distance(ball, prev)
                if dist > self.max_center_distance_px:
                    continue

                iou = _circle_iou(ball, prev)
                if iou < self.iou_threshold:
                    continue

                matches.append((iou, det_idx, track_id))

        matches.sort(key=lambda t: t[0], reverse=True)
        return matches

    def _age_tracks(self, *, seen_any: bool, matched_tracks: Optional[set[int]] = None) -> None:
        # If we processed a frame with detections, any track that wasn't matched is considered "lost".
        if not seen_any:
            return

        matched_tracks = matched_tracks or set()
        for track_id, track in self._tracks.items():
            if track_id not in matched_tracks:
                track.lost_frames += 1

    def _prune_tracks(self) -> None:
        to_delete = [
            track_id
            for track_id, track in self._tracks.items()
            if track.lost_frames > self.max_lost_frames
        ]
        for track_id in to_delete:
            del self._tracks[track_id]


def _center_distance(a: Ball, b: Ball) -> float:
    return sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2)


def _circle_iou(a: Ball, b: Ball) -> float:
    """Compute exact IoU for two circles.

    Uses standard circle intersection area formula.
    """
    r1 = float(a.r_px)
    r2 = float(b.r_px)
    d = _center_distance(a, b)

    if r1 <= 0 or r2 <= 0:
        return 0.0

    # No overlap
    if d >= r1 + r2:
        return 0.0

    # One circle fully inside the other
    if d <= abs(r1 - r2):
        smaller = min(r1, r2)
        larger = max(r1, r2)
        # IoU = area(smaller) / area(larger)
        return (smaller * smaller) / (larger * larger)

    # Partial overlap
    # Reference formula:
    # https://mathworld.wolfram.com/Circle-CircleIntersection.html
    import math

    alpha = 2.0 * math.acos((d * d + r1 * r1 - r2 * r2) / (2.0 * d * r1))
    beta = 2.0 * math.acos((d * d + r2 * r2 - r1 * r1) / (2.0 * d * r2))

    area1 = 0.5 * r1 * r1 * (alpha - math.sin(alpha))
    area2 = 0.5 * r2 * r2 * (beta - math.sin(beta))

    intersection = area1 + area2
    union = math.pi * r1 * r1 + math.pi * r2 * r2 - intersection
    if union <= 0:
        return 0.0

    return float(intersection / union)
