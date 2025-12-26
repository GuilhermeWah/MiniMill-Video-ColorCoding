from dataclasses import dataclass, asdict
from typing import List, Optional

@dataclass
class Ball:
    """Represents a single detected bead."""
    x: int              # Center X (pixels)
    y: int              # Center Y (pixels)
    r_px: float         # Radius (pixels)
    diameter_mm: float  # Calculated diameter (mm)
    cls: int            # Class label (4, 6, 8, 10)
    conf: float         # Confidence score (0.0 - 1.0)
    track_id: Optional[int] = None  # Persistent identity across frames (assigned in detection pass)

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict):
        # Backward compatibility: older caches won't contain track_id
        if "track_id" not in data:
            data = dict(data)
            data["track_id"] = None
        return cls(**data)

@dataclass
class FrameDetections:
    """Container for all detections in a single video frame."""
    frame_id: int
    timestamp: float
    balls: List[Ball]

    def to_dict(self):
        return {
            "frame_id": self.frame_id,
            "timestamp": self.timestamp,
            "balls": [b.to_dict() for b in self.balls]
        }

    @classmethod
    def from_dict(cls, data: dict):
        balls_data = data.get("balls", [])
        balls = [Ball.from_dict(b) for b in balls_data]
        return cls(
            frame_id=data["frame_id"],
            timestamp=data["timestamp"],
            balls=balls
        )
