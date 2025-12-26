# MillPresenter — Playback Controller (TESTING_VER Style)

"""
Iterator-based video playback with direct widget update.

Features:
- Uses frame iterator for efficient sequential playback
- Direct widget update (no callbacks)
- Speed control (0.15x to 1.0x)
- Seek support with iterator reset
"""

from __future__ import annotations

from typing import Optional, Callable, Dict, List, Any

import numpy as np
from PySide6.QtCore import QObject, QTimer, Signal


class PlaybackController(QObject):
    """
    Coordinates video frames and detections for the VideoWidget.
    
    TESTING_VER style: owns frame_loader and video_widget references.
    Uses iterator for sequential playback, direct widget update.
    
    Signals:
        frame_changed(int): Emitted when current frame changes
        position_changed(int, int, float, float): (frame, total, time_s, duration_s)
    """

    frame_changed = Signal(int)
    position_changed = Signal(int, int, float, float)

    def __init__(
        self,
        frame_loader=None,
        video_widget=None,
        overlay_widget=None,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._frame_loader = frame_loader
        self._video_widget = video_widget
        self._overlay_widget = overlay_widget  # For detection lookup
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.process_next_frame)

        self._frame_iter: Optional[object] = None
        self.is_playing = False
        self.current_frame_index: int = 0
        self._next_frame_to_decode: int = 0
        self._playback_speed: float = 1.0

    # ========================================================================
    # Configuration
    # ========================================================================
    
    def set_components(
        self,
        frame_loader=None,
        video_widget=None,
        overlay_widget=None,
    ) -> None:
        """Set or update components after initialization."""
        if frame_loader is not None:
            self._frame_loader = frame_loader
            self._frame_iter = None  # Reset iterator
            self.current_frame_index = 0
            self._next_frame_to_decode = 0
        if video_widget is not None:
            self._video_widget = video_widget
        if overlay_widget is not None:
            self._overlay_widget = overlay_widget

    # ========================================================================
    # Properties
    # ========================================================================
    
    @property
    def playback_speed(self) -> float:
        return self._playback_speed
    
    @property
    def fps(self) -> float:
        if self._frame_loader is None:
            return 30.0
        return getattr(self._frame_loader, "fps", 30.0) or 30.0
    
    @property
    def frame_count(self) -> int:
        if self._frame_loader is None:
            return 0
        return getattr(self._frame_loader, "frame_count", 0) or 0
    
    @property
    def duration(self) -> float:
        if self.fps > 0:
            return self.frame_count / self.fps
        return 0.0
    
    @property
    def total_frames(self) -> int:
        """Alias for frame_count."""
        return self.frame_count

    # ========================================================================
    # Speed Control
    # ========================================================================

    def set_playback_speed(self, speed: float) -> None:
        """
        Set playback speed multiplier.

        Speed is a multiplier applied to playback cadence (timer interval).
        Values < 1.0 slow down playback; 1.0 is real-time.
        """
        speed = float(speed)
        if speed <= 0:
            raise ValueError("playback speed must be > 0")

        self._playback_speed = speed
        if self.is_playing:
            interval = self._compute_interval_ms()
            self._timer.setInterval(interval)
    
    # Alias for compatibility
    def set_speed(self, speed: float) -> None:
        """Alias for set_playback_speed."""
        self.set_playback_speed(speed)
    
    def get_speed(self) -> float:
        """Get current playback speed."""
        return self._playback_speed

    # ========================================================================
    # Playback Control
    # ========================================================================

    def play(self) -> None:
        """Start playback."""
        if self._frame_loader is None or self._video_widget is None:
            return
        
        # If we've reached the end, reset to frame 0 for replay
        if self._next_frame_to_decode >= self.frame_count:
            self._next_frame_to_decode = 0
        
        # Create iterator if needed
        if self._frame_iter is None:
            self._frame_iter = self._frame_loader.iter_frames(
                start_frame=self._next_frame_to_decode
            )
        
        if self.is_playing:
            return
        
        interval = self._compute_interval_ms()
        self._timer.start(interval)
        self.is_playing = True

    def pause(self) -> None:
        """Pause playback."""
        if not self.is_playing:
            return
        self._timer.stop()
        self.is_playing = False

    def toggle_play_pause(self) -> None:
        """Toggle between play and pause."""
        if self.is_playing:
            self.pause()
        else:
            self.play()

    def stop(self) -> None:
        """Stop playback and return to start."""
        self.pause()
        self.seek(0)

    # ========================================================================
    # Navigation
    # ========================================================================

    def seek(self, frame_index: int) -> None:
        """Jump to a specific frame index."""
        if self._frame_loader is None or self._video_widget is None:
            return
        
        frame_index = max(0, min(self.frame_count - 1, frame_index))
        
        self._next_frame_to_decode = frame_index
        # Reset iterator so next fetch uses the new start frame
        self._frame_iter = None
        
        # Immediately fetch and display the frame
        try:
            temp_iter = self._frame_loader.iter_frames(start_frame=frame_index)
            actual_index, frame_bgr = next(temp_iter)
            
            # Display frame
            self._video_widget.set_frame(frame_bgr)
            
            # Set overlays
            detections = self._get_detections(actual_index)
            if detections is not None:
                self._video_widget.set_overlays(detections)
            
            self.current_frame_index = actual_index
            self._next_frame_to_decode = actual_index + 1
            self._emit_position()
            self.frame_changed.emit(actual_index)
            
        except StopIteration:
            # Seeked past end
            self.pause()

    def step_forward(self) -> None:
        """Step forward one frame."""
        self.seek(self.current_frame_index + 1)

    def step_backward(self) -> None:
        """Step backward one frame."""
        self.seek(self.current_frame_index - 1)

    def seek_to_position(self, position: float) -> None:
        """Seek to a normalized position (0.0 to 1.0)."""
        position = max(0.0, min(1.0, position))
        if self.frame_count > 1:
            frame = int(position * (self.frame_count - 1))
        else:
            frame = 0
        self.seek(frame)

    def seek_to_frame(self, frame: int) -> None:
        """Alias for seek() for backward compatibility."""
        self.seek(frame)

    # ========================================================================
    # Position Info
    # ========================================================================

    def get_current_frame(self) -> int:
        """Get current frame index."""
        return self.current_frame_index

    def get_current_time(self) -> float:
        """Get current time in seconds."""
        if self.fps <= 0:
            return 0.0
        return self.current_frame_index / self.fps

    def get_normalized_position(self) -> float:
        """Get normalized position (0.0 to 1.0)."""
        if self.frame_count <= 1:
            return 0.0
        return self.current_frame_index / (self.frame_count - 1)

    # ========================================================================
    # Internal
    # ========================================================================

    def process_next_frame(self) -> None:
        """Timer callback - fetch and display next frame."""
        if self._frame_loader is None or self._video_widget is None:
            self.pause()
            return
        
        if self._frame_iter is None:
            self._frame_iter = self._frame_loader.iter_frames(
                start_frame=self._next_frame_to_decode
            )
        
        try:
            frame_index, frame_bgr = next(self._frame_iter)
        except StopIteration:
            self._frame_iter = None
            self.pause()
            return

        # Display frame
        self._video_widget.set_frame(frame_bgr)
        
        # Set overlays
        detections = self._get_detections(frame_index)
        if detections is not None:
            self._video_widget.set_overlays(detections)

        self.current_frame_index = frame_index
        self._next_frame_to_decode = frame_index + 1
        self._emit_position()
        self.frame_changed.emit(frame_index)

    def _get_detections(self, frame_index: int) -> Optional[List[Dict]]:
        """Get detections for a frame from overlay widget's cache."""
        if self._overlay_widget is None:
            return None
        
        # Use frame_lookup from OverlayWidget
        frame_lookup = getattr(self._overlay_widget, '_frame_lookup', None)
        if frame_lookup is None:
            return None
        
        return frame_lookup.get(frame_index, [])

    def _emit_position(self) -> None:
        """Emit position update signal."""
        self.position_changed.emit(
            self.current_frame_index,
            self.frame_count,
            self.get_current_time(),
            self.duration
        )

    def _compute_interval_ms(self) -> int:
        """Compute timer interval based on FPS and playback speed.
        
        For high-FPS videos (>60fps), we cap the effective FPS to 60 for 
        interval calculation. This ensures speed control works correctly
        while maintaining smooth playback (no monitor shows >60-120fps anyway).
        """
        fps = self.fps
        if fps <= 0:
            fps = 30.0
        
        # Cap FPS to 60 for interval calculation
        # This makes speed control work for high-FPS videos (240fps, etc.)
        # while still showing every frame at slower speeds
        effective_fps = min(fps, 60.0)
        
        speed = self._playback_speed if self._playback_speed > 0 else 1.0
        
        # interval = (1000ms / effective_fps) / speed
        interval = max(1, round((1000.0 / effective_fps) / speed))
        return int(interval)
