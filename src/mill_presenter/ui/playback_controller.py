from __future__ import annotations

from typing import Optional, Tuple

import numpy as np
from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtGui import QImage
from mill_presenter.core.models import FrameDetections

class PlaybackController(QObject):
    """Coordinates video frames and detections for the VideoWidget."""

    frame_changed = pyqtSignal(int)

    def __init__(
        self,
        frame_loader,
        results_cache,
        video_widget,
        parent: Optional[QObject] = None,
        timer: Optional[QTimer] = None,
    ) -> None:
        super().__init__(parent)
        self._frame_loader = frame_loader
        self._results_cache = results_cache
        self._video_widget = video_widget
        self._timer = timer or QTimer(parent)
        self._timer.timeout.connect(self.process_next_frame)

        self._frame_iter: Optional[object] = None
        self.is_playing = False
        self.current_frame_index: int = 0
        self._next_frame_to_decode: int = 0
        self._playback_speed: float = 1.0

    @property
    def playback_speed(self) -> float:
        return self._playback_speed

    def set_playback_speed(self, speed: float) -> None:
        """Sets playback speed multiplier.

        Speed is a multiplier applied to playback cadence (timer interval).
        Values < 1.0 slow down playback; 1.0 is real-time.
        """
        speed = float(speed)
        if speed <= 0:
            raise ValueError("playback speed must be > 0")

        self._playback_speed = speed
        if self.is_playing:
            interval = self._compute_interval_ms()
            # QTimer supports setInterval; it updates the running timer cadence.
            if hasattr(self._timer, "setInterval"):
                self._timer.setInterval(interval)
            else:
                self._timer.start(interval)

    def play(self) -> None:
        # If we don't have an iterator, or if we just seeked (which resets it),
        # we need to create one starting from _next_frame_to_decode.
        # Note: seek() sets _frame_iter to None.
        # If we've reached the end, reset to frame 0 for replay.
        total_frames = getattr(self._frame_loader, "total_frames", None)
        if not isinstance(total_frames, int):
            total_frames = None
        if total_frames is not None and self._next_frame_to_decode >= total_frames:
            self._next_frame_to_decode = 0
        if self._frame_iter is None:
            self._frame_iter = self._frame_loader.iter_frames(start_frame=self._next_frame_to_decode)
        if self.is_playing:
            return
        interval = self._compute_interval_ms()
        self._timer.start(interval)
        self.is_playing = True

    def pause(self) -> None:
        if not self.is_playing:
            return
        self._timer.stop()
        self.is_playing = False

    def seek(self, frame_index: int) -> None:
        """Jumps to a specific frame index."""
        self._next_frame_to_decode = frame_index
        # Reset iterator so next fetch uses the new start frame
        self._frame_iter = None
        
        # Immediately fetch and display the frame
        try:
            # We use a temporary iterator or just rely on the loader to fetch one frame
            # Since FrameLoader.iter_frames is the API we have, we use it.
            temp_iter = self._frame_loader.iter_frames(start_frame=frame_index)
            actual_index, frame_bgr = next(temp_iter)
            
            image = self._numpy_to_qimage(frame_bgr)
            detections: Optional[FrameDetections] = self._results_cache.get_frame(actual_index)
            self._video_widget.set_frame(image, detections)
            
            self.current_frame_index = actual_index
            self._next_frame_to_decode = actual_index + 1
            self.frame_changed.emit(actual_index)
            
        except StopIteration:
            # Seeked past end? Just stop.
            self.pause()

    def process_next_frame(self) -> None:
        if self._frame_iter is None:
            self._frame_iter = self._frame_loader.iter_frames(start_frame=self._next_frame_to_decode)
        
        try:
            frame_index, frame_bgr = next(self._frame_iter)
        except StopIteration:
            self._frame_iter = None
            self.pause()
            return

        image = self._numpy_to_qimage(frame_bgr)
        detections: Optional[FrameDetections] = self._results_cache.get_frame(frame_index)
        self._video_widget.set_frame(image, detections)

        self.current_frame_index = frame_index
        self._next_frame_to_decode = frame_index + 1
        self.frame_changed.emit(frame_index)

    def _compute_interval_ms(self) -> int:
        fps = float(getattr(self._frame_loader, "fps", 0.0) or 0.0)
        if fps <= 0:
            fps = 30.0
        speed = float(self._playback_speed or 1.0)
        if speed <= 0:
            speed = 1.0

        interval = max(1, round((1000.0 / fps) / speed))
        return int(interval)

    def _numpy_to_qimage(self, frame_bgr: np.ndarray) -> QImage:
        """Converts a BGR numpy array (HxWx3) into a QImage copy."""
        if frame_bgr.ndim != 3 or frame_bgr.shape[2] != 3:
            raise ValueError("Expected frame of shape (H, W, 3)")
        height, width, channels = frame_bgr.shape
        bytes_per_line = channels * width
        qimage = QImage(
            frame_bgr.data,
            width,
            height,
            bytes_per_line,
            QImage.Format.Format_BGR888,
        )
        return qimage.copy()
