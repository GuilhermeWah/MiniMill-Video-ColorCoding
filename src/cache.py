"""
Detection cache module for MillPresenter pipeline.

STEP_09: Visualization & Playback

This module manages the detection cache for offline-to-playback workflow:
- Write: Save detection results per frame to JSON cache
- Read: Load cached detections for real-time playback
- Index: Fast frame lookup without loading entire cache

Cache format designed for:
- Fast random access by frame number
- Minimal memory footprint during playback
- Easy inspection/debugging (human-readable JSON)
"""

import json
import os
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Iterator
from datetime import datetime


@dataclass
class CachedDetection:
    """A single cached detection."""
    x: int
    y: int
    r_px: float
    conf: float
    diameter_mm: float
    cls: str
    
    @classmethod
    def from_dict(cls, d: dict) -> "CachedDetection":
        return cls(
            x=d["x"],
            y=d["y"],
            r_px=d["r_px"],
            conf=d["conf"],
            diameter_mm=d.get("diameter_mm", 0),
            cls=d.get("cls", "unknown")
        )
    
    def to_dict(self) -> dict:
        return {
            "x": self.x,
            "y": self.y,
            "r_px": round(self.r_px, 2),
            "conf": round(self.conf, 3),
            "diameter_mm": round(self.diameter_mm, 2),
            "cls": self.cls
        }


@dataclass
class FrameCache:
    """Cached data for a single frame."""
    frame_idx: int
    timestamp: float
    detections: List[CachedDetection]
    stats: Dict[str, int]
    
    @classmethod
    def from_dict(cls, d: dict) -> "FrameCache":
        return cls(
            frame_idx=d["frame_idx"],
            timestamp=d.get("timestamp", 0),
            detections=[CachedDetection.from_dict(det) for det in d["detections"]],
            stats=d.get("stats", {})
        )
    
    def to_dict(self) -> dict:
        return {
            "frame_idx": self.frame_idx,
            "timestamp": round(self.timestamp, 3),
            "detections": [d.to_dict() for d in self.detections],
            "stats": self.stats
        }


@dataclass
class VideoCache:
    """Complete detection cache for a video."""
    video_path: str
    video_name: str
    total_frames: int
    fps: float
    width: int
    height: int
    px_per_mm: float
    drum_center: tuple
    drum_radius: int
    created_at: str
    config_used: Dict[str, Any]
    frames: Dict[int, FrameCache]  # frame_idx -> FrameCache
    
    def get_frame(self, frame_idx: int) -> Optional[FrameCache]:
        """Get cached data for a specific frame."""
        return self.frames.get(frame_idx)
    
    def has_frame(self, frame_idx: int) -> bool:
        """Check if frame is in cache."""
        return frame_idx in self.frames
    
    def frame_indices(self) -> List[int]:
        """Get sorted list of cached frame indices."""
        return sorted(self.frames.keys())
    
    def to_dict(self) -> dict:
        return {
            "metadata": {
                "video_path": self.video_path,
                "video_name": self.video_name,
                "total_frames": self.total_frames,
                "fps": self.fps,
                "width": self.width,
                "height": self.height,
                "px_per_mm": round(self.px_per_mm, 3),
                "drum_center": list(self.drum_center),
                "drum_radius": self.drum_radius,
                "created_at": self.created_at,
            },
            "config": self.config_used,
            "frames": {str(k): v.to_dict() for k, v in self.frames.items()}
        }
    
    @classmethod
    def from_dict(cls, d: dict) -> "VideoCache":
        meta = d["metadata"]
        frames = {}
        for k, v in d.get("frames", {}).items():
            frames[int(k)] = FrameCache.from_dict(v)
        
        return cls(
            video_path=meta["video_path"],
            video_name=meta["video_name"],
            total_frames=meta["total_frames"],
            fps=meta["fps"],
            width=meta["width"],
            height=meta["height"],
            px_per_mm=meta["px_per_mm"],
            drum_center=tuple(meta["drum_center"]),
            drum_radius=meta["drum_radius"],
            created_at=meta["created_at"],
            config_used=d.get("config", {}),
            frames=frames
        )


class DetectionCacheWriter:
    """Write detection results to cache file."""
    
    def __init__(self, video_path: str, fps: float, width: int, height: int,
                 px_per_mm: float, drum_center: tuple, drum_radius: int,
                 config: Dict[str, Any] = None):
        self.video_path = video_path
        self.video_name = Path(video_path).stem
        self.fps = fps
        self.width = width
        self.height = height
        self.px_per_mm = px_per_mm
        self.drum_center = drum_center
        self.drum_radius = drum_radius
        self.config = config or {}
        self.frames: Dict[int, FrameCache] = {}
        self.total_frames = 0
    
    def add_frame(self, frame_idx: int, detections: List[Dict[str, Any]]):
        """Add detection results for a frame."""
        timestamp = frame_idx / self.fps if self.fps > 0 else 0
        
        cached_dets = [CachedDetection.from_dict(d) for d in detections]
        
        # Compute stats
        stats = {"total": len(cached_dets)}
        for cls in ["4mm", "6mm", "8mm", "10mm", "unknown"]:
            stats[cls] = sum(1 for d in cached_dets if d.cls == cls)
        
        self.frames[frame_idx] = FrameCache(
            frame_idx=frame_idx,
            timestamp=timestamp,
            detections=cached_dets,
            stats=stats
        )
        self.total_frames = max(self.total_frames, frame_idx + 1)
    
    def save(self, cache_path: str):
        """Save cache to JSON file."""
        cache = VideoCache(
            video_path=self.video_path,
            video_name=self.video_name,
            total_frames=self.total_frames,
            fps=self.fps,
            width=self.width,
            height=self.height,
            px_per_mm=self.px_per_mm,
            drum_center=self.drum_center,
            drum_radius=self.drum_radius,
            created_at=datetime.now().isoformat(),
            config_used=self.config,
            frames=self.frames
        )
        
        Path(cache_path).parent.mkdir(parents=True, exist_ok=True)
        with open(cache_path, 'w') as f:
            json.dump(cache.to_dict(), f, indent=2)
        
        return cache


class DetectionCacheReader:
    """Read detection cache for playback."""
    
    def __init__(self, cache_path: str):
        self.cache_path = cache_path
        self.cache: Optional[VideoCache] = None
        self._load()
    
    def _load(self):
        """Load cache from file."""
        with open(self.cache_path) as f:
            data = json.load(f)
        self.cache = VideoCache.from_dict(data)
    
    @property
    def video_name(self) -> str:
        return self.cache.video_name if self.cache else ""
    
    @property
    def total_frames(self) -> int:
        return self.cache.total_frames if self.cache else 0
    
    @property
    def fps(self) -> float:
        return self.cache.fps if self.cache else 30.0
    
    @property
    def px_per_mm(self) -> float:
        return self.cache.px_per_mm if self.cache else 1.0
    
    @property
    def drum_center(self) -> tuple:
        return self.cache.drum_center if self.cache else (0, 0)
    
    @property
    def drum_radius(self) -> int:
        return self.cache.drum_radius if self.cache else 0
    
    def get_frame(self, frame_idx: int) -> Optional[FrameCache]:
        """Get cached data for a frame."""
        if self.cache is None:
            return None
        return self.cache.get_frame(frame_idx)
    
    def get_detections(self, frame_idx: int, 
                       min_confidence: float = 0.0,
                       classes: List[str] = None) -> List[CachedDetection]:
        """Get filtered detections for a frame."""
        frame = self.get_frame(frame_idx)
        if frame is None:
            return []
        
        detections = frame.detections
        
        # Filter by confidence
        if min_confidence > 0:
            detections = [d for d in detections if d.conf >= min_confidence]
        
        # Filter by class
        if classes:
            detections = [d for d in detections if d.cls in classes]
        
        return detections
    
    def get_stats(self, frame_idx: int) -> Dict[str, int]:
        """Get detection stats for a frame."""
        frame = self.get_frame(frame_idx)
        if frame is None:
            return {}
        return frame.stats
    
    def cached_frame_indices(self) -> List[int]:
        """Get list of frames that have cached data."""
        if self.cache is None:
            return []
        return self.cache.frame_indices()


def get_cache_path(video_path: str, cache_dir: str = None) -> str:
    """Generate cache file path for a video."""
    if cache_dir is None:
        cache_dir = "cache/detections"
    
    video_name = Path(video_path).stem
    return str(Path(cache_dir) / f"{video_name}_detections.json")
