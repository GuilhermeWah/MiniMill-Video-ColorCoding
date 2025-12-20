# MillPresenter Core Models

"""
Data models for the MillPresenter pipeline.
All detection-related dataclasses are defined here.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional


@dataclass
class RawDetection:
    """A raw circle detection before scoring (from VisionProcessor)."""
    x: int
    y: int
    r_px: float
    source: str  # "hough" or "contour"
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RawDetection":
        return cls(**data)


@dataclass
class ScoredDetection:
    """A detection with confidence score (from ConfidenceScorer)."""
    x: int
    y: int
    r_px: float
    conf: float
    features: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScoredDetection":
        return cls(**data)


@dataclass
class Ball:
    """A classified bead detection (final output)."""
    x: int
    y: int
    r_px: float
    diameter_mm: float
    cls: int  # 4, 6, 8, 10, or 0 (unknown)
    conf: float
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Ball":
        return cls(**data)


@dataclass
class FrameDetections:
    """All detections for a single frame."""
    frame_id: int
    timestamp: float
    balls: List[Ball] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "frame_id": self.frame_id,
            "timestamp": self.timestamp,
            "balls": [b.to_dict() for b in self.balls]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FrameDetections":
        return cls(
            frame_id=data["frame_id"],
            timestamp=data["timestamp"],
            balls=[Ball.from_dict(b) for b in data.get("balls", [])]
        )


@dataclass
class DrumGeometry:
    """Drum geometry for ROI and calibration."""
    center_x: int
    center_y: int
    radius_px: int
    px_per_mm: float
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DrumGeometry":
        return cls(**data)


@dataclass
class VideoMetadata:
    """Metadata about the loaded video."""
    path: str
    width: int
    height: int
    fps: float
    total_frames: int
    duration: float
    rotation: int = 0  # Rotation in degrees (0, 90, 180, 270)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
