import json
import os
from collections import deque
from typing import Optional, Dict
from mill_presenter.core.models import FrameDetections
from mill_presenter.utils.logging import get_logger

logger = get_logger(__name__)

class ResultsCache:
    """
    Manages storage and retrieval of detection results.
    
    Strategy:
    - Disk: 'detections.jsonl' (Append-only log of detections).
    - Memory: A ring buffer (deque) or full dictionary to serve playback requests instantly.
    
    For the MVP, we will load all detections into a dictionary for O(1) access by frame_id,
    as the memory footprint is manageable (hundreds of MBs for long videos).
    The 'ring buffer' concept from instructions is implemented as a cache layer 
    that could be restricted in size if needed, but currently we cache everything 
    we read to ensure smooth scrubbing.
    """
    
    def __init__(self, cache_path: str):
        self.cache_path = cache_path
        self._memory_cache: Dict[int, FrameDetections] = {}
        self._dirty = False
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(cache_path)), exist_ok=True)
        
        # Load existing if available
        if os.path.exists(cache_path):
            self.load_from_disk()

    def save_frame(self, detections: FrameDetections):
        """
        Saves a single frame's detections to memory and appends to disk.
        Used during the detection phase.
        """
        # 1. Update Memory
        self._memory_cache[detections.frame_id] = detections
        
        # 2. Append to Disk (JSONL)
        try:
            with open(self.cache_path, 'a') as f:
                f.write(json.dumps(detections.to_dict()) + '\n')
        except Exception as e:
            logger.error(f"Failed to write to cache {self.cache_path}: {e}")

    def get_frame(self, frame_id: int) -> Optional[FrameDetections]:
        """
        Retrieves detections for a specific frame.
        Used during playback/rendering.
        """
        return self._memory_cache.get(frame_id)

    def load_from_disk(self):
        """
        Re-populates the memory cache from the JSONL file.
        """
        self._memory_cache.clear()
        if not os.path.exists(self.cache_path):
            return

        try:
            with open(self.cache_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        detections = FrameDetections.from_dict(data)
                        self._memory_cache[detections.frame_id] = detections
                    except json.JSONDecodeError:
                        logger.warning(f"Skipping invalid JSON line in {self.cache_path}")
                        continue
            logger.info(f"Loaded {len(self._memory_cache)} frames from cache.")
        except Exception as e:
            logger.error(f"Failed to load cache from {self.cache_path}: {e}")

    def clear(self):
        """Clears both memory and disk cache."""
        self._memory_cache.clear()
        if os.path.exists(self.cache_path):
            try:
                os.remove(self.cache_path)
            except OSError as e:
                logger.error(f"Failed to delete cache file: {e}")
