"""
Video Controller

Manages video decoding and frame delivery for playback.
Separates video I/O from UI concerns.
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Optional, Dict, Any, List
import json

from PySide6.QtCore import QObject, Signal, QTimer


class VideoController(QObject):
    """
    Manages video file access and frame delivery.
    
    Handles:
    - Opening/closing video files
    - Seeking to specific frames
    - Frame-by-frame and continuous playback
    - Playback speed control
    
    Signals:
        frame_ready: Emitted when a new frame is available (frame, frame_idx)
        playback_finished: Emitted when video reaches the end
        error_occurred: Emitted on errors
    """
    
    frame_ready = Signal(np.ndarray, int)  # frame, frame_index
    playback_finished = Signal()
    error_occurred = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._cap: Optional[cv2.VideoCapture] = None
        self._video_path: str = ""
        
        # Video properties
        self._width: int = 0
        self._height: int = 0
        self._fps: float = 30.0
        self._total_frames: int = 0
        self._current_frame: int = 0
        
        # Playback state
        self._is_playing: bool = False
        self._is_looping: bool = False
        self._speed: float = 1.0
        
        # Playback timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_timer)
    
    @property
    def is_open(self) -> bool:
        return self._cap is not None and self._cap.isOpened()
    
    @property
    def width(self) -> int:
        return self._width
    
    @property
    def height(self) -> int:
        return self._height
    
    @property
    def fps(self) -> float:
        return self._fps
    
    @property
    def total_frames(self) -> int:
        return self._total_frames
    
    @property
    def current_frame(self) -> int:
        return self._current_frame
    
    @property
    def is_playing(self) -> bool:
        return self._is_playing
    
    @property
    def duration_seconds(self) -> float:
        if self._fps > 0:
            return self._total_frames / self._fps
        return 0.0
    
    def open(self, video_path: str) -> bool:
        """
        Open a video file.
        
        Args:
            video_path: Path to video file
            
        Returns:
            True if successful
        """
        self.close()
        
        try:
            self._cap = cv2.VideoCapture(video_path)
            if not self._cap.isOpened():
                raise ValueError(f"Cannot open video: {video_path}")
            
            self._video_path = video_path
            self._width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self._height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self._fps = self._cap.get(cv2.CAP_PROP_FPS) or 30.0
            self._total_frames = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self._current_frame = 0
            
            # Read and emit first frame
            self._emit_current_frame()
            
            return True
            
        except Exception as e:
            self.error_occurred.emit(str(e))
            return False
    
    def close(self):
        """Close the current video."""
        self.stop()
        
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        
        self._video_path = ""
        self._width = 0
        self._height = 0
        self._fps = 30.0
        self._total_frames = 0
        self._current_frame = 0
    
    def seek(self, frame_index: int) -> bool:
        """
        Seek to a specific frame.
        
        Args:
            frame_index: Target frame index (0-based)
            
        Returns:
            True if successful
        """
        if not self.is_open:
            return False
        
        # Clamp to valid range
        frame_index = max(0, min(frame_index, self._total_frames - 1))
        
        # Always seek and sync position for accurate frame display
        self._cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        self._current_frame = frame_index
        
        # Read and emit the frame at this position
        ret, frame = self._cap.read()
        if ret and frame is not None:
            self.frame_ready.emit(frame, self._current_frame)
            # After read, position is at frame_index + 1, so seek back for next sequential read
            # Only needed if we're playing, otherwise it will seek again anyway
            if not self._is_playing:
                self._cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        
        return True
    
    def step_forward(self, count: int = 1) -> bool:
        """Step forward by count frames."""
        return self.seek(self._current_frame + count)
    
    def step_backward(self, count: int = 1) -> bool:
        """Step backward by count frames."""
        return self.seek(self._current_frame - count)
    
    def go_to_start(self) -> bool:
        """Go to first frame."""
        return self.seek(0)
    
    def go_to_end(self) -> bool:
        """Go to last frame."""
        return self.seek(self._total_frames - 1)
    
    def play(self):
        """Start continuous playback."""
        if not self.is_open:
            return
        
        self._is_playing = True
        interval = int(1000 / (self._fps * self._speed))
        self._timer.start(max(1, interval))
    
    def pause(self):
        """Pause playback."""
        self._is_playing = False
        self._timer.stop()
    
    def stop(self):
        """Stop playback and go to start."""
        self.pause()
        self.seek(0)
    
    def toggle_play(self) -> bool:
        """Toggle play/pause state. Returns new playing state."""
        if self._is_playing:
            self.pause()
        else:
            self.play()
        return self._is_playing
    
    def set_speed(self, speed: float):
        """Set playback speed multiplier."""
        self._speed = max(0.1, min(4.0, speed))
        
        # Update timer if playing
        if self._is_playing:
            interval = int(1000 / (self._fps * self._speed))
            self._timer.setInterval(max(1, interval))
    
    def set_looping(self, loop: bool):
        """Enable/disable loop playback."""
        self._is_looping = loop
    
    def get_frame(self, frame_index: int = None) -> Optional[np.ndarray]:
        """
        Get a specific frame without changing playback position.
        
        Args:
            frame_index: Frame to get, or None for current frame
            
        Returns:
            BGR numpy array or None
        """
        if not self.is_open:
            return None
        
        if frame_index is not None and frame_index != self._current_frame:
            # Save position
            old_pos = self._current_frame
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            ret, frame = self._cap.read()
            # Restore position
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, old_pos)
            return frame if ret else None
        else:
            # Read current frame - need to seek since read() advances position
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, self._current_frame)
            ret, frame = self._cap.read()
            return frame if ret else None
    
    def get_current_frame(self) -> Optional[np.ndarray]:
        """
        Get the current frame for preview/processing.
        
        Returns:
            BGR numpy array of current frame, or None
        """
        return self.get_frame()
    
    def _read_next_frame(self) -> Optional[np.ndarray]:
        """
        Read the next frame sequentially (fast - no seeking).
        Used during continuous playback for better performance.
        
        Returns:
            BGR numpy array or None
        """
        if not self.is_open:
            return None
        ret, frame = self._cap.read()
        return frame if ret else None
    
    def _emit_current_frame(self):
        """Read and emit the current frame."""
        frame = self.get_frame()
        if frame is not None:
            self.frame_ready.emit(frame, self._current_frame)
    
    def _on_timer(self):
        """Timer callback for continuous playback."""
        if not self.is_open:
            self.pause()
            return
        
        # Advance frame
        next_frame = self._current_frame + 1
        
        if next_frame >= self._total_frames:
            if self._is_looping:
                next_frame = 0
                # Need to seek back to start
                self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                self._current_frame = 0
                frame = self._read_next_frame()
            else:
                self.pause()
                self.playback_finished.emit()
                return
        else:
            # Sequential read - fast, no seeking needed
            self._current_frame = next_frame
            frame = self._read_next_frame()
        
        if frame is not None:
            self.frame_ready.emit(frame, self._current_frame)


class DetectionCache:
    """
    Manages detection cache data.
    
    Loads detection JSON and provides frame-by-frame access.
    """
    
    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._frames: Dict[int, List[dict]] = {}
        self._metadata: Dict[str, Any] = {}
        self._is_loaded: bool = False
        self._path: str = ""
    
    @property
    def is_loaded(self) -> bool:
        return self._is_loaded
    
    @property
    def metadata(self) -> Dict[str, Any]:
        return self._metadata
    
    @property
    def total_frames(self) -> int:
        return len(self._frames)
    
    @property
    def px_per_mm(self) -> float:
        return self._metadata.get("px_per_mm", 5.0)
    
    @property
    def drum_center(self) -> tuple:
        return tuple(self._metadata.get("drum_center", [0, 0]))
    
    @property
    def drum_radius(self) -> int:
        return self._metadata.get("drum_radius", 0)
    
    def load(self, cache_path: str) -> bool:
        """Load detection cache from JSON file."""
        try:
            with open(cache_path, 'r') as f:
                self._data = json.load(f)
            
            self._metadata = self._data.get("metadata", {})
            
            # Parse frames
            frames_data = self._data.get("frames", {})
            self._frames = {}
            
            for frame_key, frame_data in frames_data.items():
                try:
                    frame_idx = int(frame_key)
                    detections = frame_data.get("detections", [])
                    self._frames[frame_idx] = detections
                except (ValueError, TypeError):
                    continue
            
            self._path = cache_path
            self._is_loaded = True
            return True
            
        except Exception as e:
            print(f"Failed to load cache: {e}")
            self._is_loaded = False
            return False
    
    def get_detections(self, frame_index: int) -> List[dict]:
        """Get detections for a specific frame.
        
        If the exact frame wasn't processed (frame_step > 1),
        returns detections from the nearest processed frame.
        """
        if frame_index in self._frames:
            return self._frames[frame_index]
        
        # Frame not in cache - find nearest processed frame
        if not self._frames:
            return []
        
        # Find the closest frame that was processed
        processed_frames = sorted(self._frames.keys())
        nearest = min(processed_frames, key=lambda x: abs(x - frame_index))
        return self._frames.get(nearest, [])
    
    def get_stats(self, frame_index: int) -> Dict[str, int]:
        """Get count statistics for a frame."""
        detections = self.get_detections(frame_index)
        
        stats = {"total": 0, "4mm": 0, "6mm": 0, "8mm": 0, "10mm": 0, "unknown": 0}
        
        for det in detections:
            cls = det.get("cls", "unknown")
            stats["total"] += 1
            if cls in stats:
                stats[cls] += 1
            else:
                stats["unknown"] += 1
        
        return stats
    
    def get_confidence_bins(self, frame_index: int, num_bins: int = 10) -> List[int]:
        """Get confidence distribution histogram for a frame."""
        detections = self.get_detections(frame_index)
        bins = [0] * num_bins
        
        for det in detections:
            conf = det.get("conf", 0.0)
            bin_idx = min(int(conf * num_bins), num_bins - 1)
            bins[bin_idx] += 1
        
        return bins
    
    def clear(self):
        """Clear loaded data."""
        self._data = {}
        self._frames = {}
        self._metadata = {}
        self._is_loaded = False
        self._path = ""
    
    def reclassify_all(self, px_per_mm: float) -> int:
        """
        Reclassify all detections with new calibration.
        
        Args:
            px_per_mm: New calibration value
            
        Returns:
            Total number of reclassified detections
        """
        if not self._is_loaded:
            return 0
        
        # Size classification bins
        size_bins = [
            (3.94, "4mm"),
            (5.79, "6mm"),
            (7.63, "8mm"),
            (9.90, "10mm"),
        ]
        
        total_reclassified = 0
        
        for frame_idx, detections in self._frames.items():
            for det in detections:
                r_px = det.get("r_px", 0)
                diameter_mm = (2 * r_px) / px_per_mm if px_per_mm > 0 else 0
                
                # Classify by nearest bin
                best_cls = "unknown"
                min_dist = float('inf')
                for nominal, cls_name in size_bins:
                    dist = abs(diameter_mm - nominal)
                    if dist < min_dist:
                        min_dist = dist
                        best_cls = cls_name
                
                det["diameter_mm"] = diameter_mm
                det["cls"] = best_cls
                total_reclassified += 1
        
        # Update metadata
        self._metadata["px_per_mm"] = px_per_mm
        
        return total_reclassified
    
    def load_from_dict(self, data: Dict[str, Any]) -> bool:
        """Load detection cache from dict (from batch worker)."""
        try:
            self._data = data
            self._metadata = data.get("metadata", {})
            
            # Parse frames
            frames_data = data.get("frames", {})
            self._frames = {}
            
            for frame_key, frame_data in frames_data.items():
                try:
                    frame_idx = int(frame_key)
                    if isinstance(frame_data, dict):
                        detections = frame_data.get("detections", [])
                    else:
                        detections = frame_data  # Already a list
                    self._frames[frame_idx] = detections
                except (ValueError, TypeError):
                    continue
            
            self._path = ""
            self._is_loaded = True
            return True
            
        except Exception as e:
            print(f"Failed to load cache from dict: {e}")
            self._is_loaded = False
            return False
