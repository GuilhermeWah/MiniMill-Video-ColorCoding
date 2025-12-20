# MillPresenter Results Cache

"""
Cache management for detection results.
Supports JSONL streaming during processing and JSON export on completion.

Hybrid approach:
- During processing: Append JSONL (crash-tolerant)
- On completion: Export structured JSON (fast random access)
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List

from mill_presenter.core.models import FrameDetections, Ball


class ResultsCache:
    """
    Hybrid cache: JSONL streaming + JSON export.
    """
    
    def __init__(self, cache_path: str):
        """
        Initialize cache.
        
        Args:
            cache_path: Path for the final JSON cache file.
        """
        self._path = Path(cache_path)
        self._jsonl_path = self._path.with_suffix(".jsonl")
        
        self._frames: Dict[int, FrameDetections] = {}
        self._metadata: Dict[str, Any] = {}
        self._config: Dict[str, Any] = {}
        self._is_ready = False
        self._total_frames = 0
        
        self._jsonl_handle = None
    
    # =========================================================================
    # Writing (during processing)
    # =========================================================================
    
    def start_processing(self, total_frames: int, metadata: Dict[str, Any] = None,
                         cfg: Dict[str, Any] = None) -> None:
        """
        Start a processing session.
        
        Args:
            total_frames: Expected frame count.
            metadata: Video metadata.
            cfg: Configuration used.
        """
        self._total_frames = total_frames
        self._metadata = metadata or {}
        self._config = cfg or {}
        self._frames = {}
        
        # Open JSONL for streaming
        self._jsonl_handle = open(self._jsonl_path, "w", encoding="utf-8")
    
    def append_frame(self, detections: FrameDetections) -> None:
        """
        Append frame detections (during processing).
        
        Args:
            detections: Frame detections to append.
        """
        if self._jsonl_handle is None:
            raise RuntimeError("Call start_processing() first")
        
        # Store in memory
        self._frames[detections.frame_id] = detections
        
        # Stream to JSONL
        line = json.dumps(detections.to_dict(), separators=(",", ":"))
        self._jsonl_handle.write(line + "\n")
        self._jsonl_handle.flush()  # Ensure crash tolerance
    
    def finalize(self) -> None:
        """
        Finalize processing and export structured JSON.
        """
        # Close JSONL
        if self._jsonl_handle:
            self._jsonl_handle.close()
            self._jsonl_handle = None
        
        # Export structured JSON
        cache_data = {
            "version": "2.0",
            "metadata": self._metadata,
            "config": self._config,
            "frames": {
                str(fid): fd.to_dict() for fid, fd in self._frames.items()
            }
        }
        
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, indent=2)
        
        # Remove JSONL (no longer needed)
        try:
            self._jsonl_path.unlink()
        except OSError:
            pass
        
        self._is_ready = True
    
    # =========================================================================
    # Reading (during playback)
    # =========================================================================
    
    def load(self) -> bool:
        """
        Load cache from disk.
        
        Returns:
            True if loaded successfully.
        """
        # Try JSON first
        if self._path.exists():
            return self._load_json()
        
        # Try JSONL (incomplete processing)
        if self._jsonl_path.exists():
            return self._load_jsonl()
        
        return False
    
    def _load_json(self) -> bool:
        """Load structured JSON cache."""
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            self._metadata = data.get("metadata", {})
            self._config = data.get("config", {})
            self._frames = {}
            
            for fid_str, fd_data in data.get("frames", {}).items():
                fid = int(fid_str)
                self._frames[fid] = FrameDetections.from_dict(fd_data)
            
            self._total_frames = len(self._frames)
            self._is_ready = True
            return True
        except Exception as e:
            print(f"Failed to load JSON cache: {e}")
            return False
    
    def _load_jsonl(self) -> bool:
        """Load JSONL (partial processing recovery)."""
        try:
            self._frames = {}
            
            with open(self._jsonl_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        fd_data = json.loads(line)
                        fd = FrameDetections.from_dict(fd_data)
                        self._frames[fd.frame_id] = fd
            
            self._total_frames = len(self._frames)
            self._is_ready = len(self._frames) > 0
            return self._is_ready
        except Exception as e:
            print(f"Failed to load JSONL cache: {e}")
            return False
    
    def get_frame(self, frame_id: int) -> Optional[FrameDetections]:
        """
        Get detections for a specific frame.
        
        Args:
            frame_id: Frame index.
            
        Returns:
            FrameDetections or None if not found.
        """
        return self._frames.get(frame_id)
    
    @property
    def is_ready(self) -> bool:
        """Whether cache is loaded and ready."""
        return self._is_ready
    
    @property
    def total_frames(self) -> int:
        """Number of frames in cache."""
        return self._total_frames
    
    @property
    def frame_ids(self) -> List[int]:
        """List of available frame IDs."""
        return sorted(self._frames.keys())
    
    @property
    def metadata(self) -> Dict[str, Any]:
        """Video metadata."""
        return self._metadata
