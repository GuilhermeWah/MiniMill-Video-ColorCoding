# MillPresenter — Playback Controller (STEP-12)

"""
Timer-based video playback with scrubbing support.

Features:
- Play/pause with QTimer
- Frame stepping (prev/next)
- Timeline scrubbing
- Speed control (0.25x, 0.5x, 1x)
- Keyboard shortcuts
"""

from typing import Optional, Callable
from PySide6.QtCore import QObject, QTimer, Signal, Slot


class PlaybackController(QObject):
    """
    Controls video playback timing and frame navigation.
    
    Signals:
        frame_changed(int): Emitted when current frame changes
        playback_started(): Emitted when playback starts
        playback_stopped(): Emitted when playback stops
        position_changed(int, int, float, float): (frame, total, time_s, duration_s)
    """
    
    frame_changed = Signal(int)
    playback_started = Signal()
    playback_stopped = Signal()
    position_changed = Signal(int, int, float, float)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Playback state
        self._playing = False
        self._current_frame = 0
        self._total_frames = 0
        self._fps = 30.0
        self._duration = 0.0
        self._speed = 1.0
        
        # Timer for playback
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_timer)
        
        # Frame callback (set by owner to fetch frames)
        self._frame_callback: Optional[Callable[[int], None]] = None
    
    # ========================================================================
    # Configuration
    # ========================================================================
    
    def set_video_info(self, total_frames: int, fps: float, duration: float) -> None:
        """Set video information for playback timing."""
        self._total_frames = total_frames
        self._fps = fps if fps > 0 else 30.0
        self._duration = duration
        self._current_frame = 0
        
        # No frame skipping - play every frame sequentially
        # Timer will be capped to max decode speed
        self._frame_skip = 1
        
        # Update timer interval for new fps
        self._update_timer_interval()
        
        self._emit_position()
    
    def set_frame_callback(self, callback: Callable[[int], None]) -> None:
        """Set callback to be called when frame changes."""
        self._frame_callback = callback
    
    def set_speed(self, speed: float) -> None:
        """Set playback speed (0.1x to 4.0x)."""
        old_speed = self._speed
        self._speed = max(0.05, min(4.0, speed))
        # Reset frame accumulator when speed changes
        self._frame_accumulator = 0.0
        # Always update timer interval (even if not playing, so it's ready)
        self._update_timer_interval()
    
    def get_speed(self) -> float:
        """Get current playback speed."""
        return self._speed
    
    # ========================================================================
    # Playback control
    # ========================================================================
    
    def play(self) -> None:
        """Start playback."""
        if self._total_frames <= 0:
            return
        
        if not self._playing:
            self._playing = True
            # Always recalculate timer interval when starting playback
            self._update_timer_interval()
            self._timer.start()
            self.playback_started.emit()
    
    def pause(self) -> None:
        """Pause playback."""
        if self._playing:
            self._playing = False
            self._timer.stop()
            self.playback_stopped.emit()
    
    def toggle_play_pause(self) -> None:
        """Toggle between play and pause."""
        if self._playing:
            self.pause()
        else:
            self.play()
    
    def stop(self) -> None:
        """Stop playback and return to start."""
        self.pause()
        self.seek_to_frame(0)
    
    def is_playing(self) -> bool:
        """Check if currently playing."""
        return self._playing
    
    # ========================================================================
    # Navigation
    # ========================================================================
    
    def seek_to_frame(self, frame: int) -> None:
        """Seek to a specific frame."""
        if self._total_frames <= 0:
            return
        
        # Clamp to valid range
        frame = max(0, min(self._total_frames - 1, frame))
        
        if frame != self._current_frame:
            self._current_frame = frame
            self._notify_frame_change()
    
    def seek_to_position(self, position: float) -> None:
        """Seek to a normalized position (0.0 to 1.0)."""
        if self._total_frames <= 0:
            return
        
        position = max(0.0, min(1.0, position))
        frame = int(position * (self._total_frames - 1))
        self.seek_to_frame(frame)
    
    def step_forward(self) -> None:
        """Step forward one frame."""
        self.seek_to_frame(self._current_frame + 1)
    
    def step_backward(self) -> None:
        """Step backward one frame."""
        self.seek_to_frame(self._current_frame - 1)
    
    def skip_forward(self, seconds: float = 1.0) -> None:
        """Skip forward by seconds."""
        frames = int(seconds * self._fps)
        self.seek_to_frame(self._current_frame + frames)
    
    def skip_backward(self, seconds: float = 1.0) -> None:
        """Skip backward by seconds."""
        frames = int(seconds * self._fps)
        self.seek_to_frame(self._current_frame - frames)
    
    def get_current_frame(self) -> int:
        """Get current frame index."""
        return self._current_frame
    
    def get_current_time(self) -> float:
        """Get current time in seconds."""
        if self._fps <= 0:
            return 0.0
        return self._current_frame / self._fps
    
    def get_normalized_position(self) -> float:
        """Get normalized position (0.0 to 1.0)."""
        if self._total_frames <= 1:
            return 0.0
        return self._current_frame / (self._total_frames - 1)
    
    # ========================================================================
    # Internal
    # ========================================================================
    
    def _update_timer_interval(self) -> None:
        """Update timer interval based on FPS and speed."""
        if self._fps <= 0:
            return
        
        # For speeds > 1x, we use frame skipping instead of faster timer
        # This is because we can't display faster than ~60fps (16ms minimum)
        if self._speed > 1.0:
            # Use base fps timing, skip frames to achieve speed
            interval_ms = int(1000.0 / self._fps)
            self._frame_skip = self._speed  # e.g., 2.0 means skip every other frame
        else:
            # For slow speeds, increase timer interval
            interval_ms = int(1000.0 / (self._fps * self._speed))
            self._frame_skip = 1  # No frame skipping
        
        # Minimum 16ms (~60fps max display rate)
        interval_ms = max(16, interval_ms)
        print(f"[PLAYBACK] Timer: {interval_ms}ms, skip={self._frame_skip:.2f} (fps={self._fps:.1f}, speed={self._speed})")
        self._timer.setInterval(interval_ms)
    
    @Slot()
    def _on_timer(self) -> None:
        """Timer callback for playback."""
        # Calculate next frame with frame skipping for fast playback
        if self._frame_skip > 1:
            # Accumulate fractional frame skip
            if not hasattr(self, '_frame_accumulator'):
                self._frame_accumulator = 0.0
            self._frame_accumulator += self._frame_skip
            frames_to_skip = int(self._frame_accumulator)
            self._frame_accumulator -= frames_to_skip
            next_frame = self._current_frame + frames_to_skip
        else:
            next_frame = self._current_frame + 1
        
        if next_frame >= self._total_frames:
            # End of video - stop playback
            self.pause()
            return
        
        self._current_frame = next_frame
        self._notify_frame_change()
    
    def _notify_frame_change(self) -> None:
        """Notify listeners of frame change."""
        # Call frame callback
        if self._frame_callback:
            self._frame_callback(self._current_frame)
        
        # Emit signals
        self.frame_changed.emit(self._current_frame)
        self._emit_position()
    
    def _emit_position(self) -> None:
        """Emit position update signal."""
        time_s = self.get_current_time()
        self.position_changed.emit(
            self._current_frame,
            self._total_frames,
            time_s,
            self._duration
        )


# ============================================================================
# Standalone test
# ============================================================================

def main():
    """Test playback controller."""
    import sys
    from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSlider
    from PySide6.QtCore import Qt
    
    app = QApplication(sys.argv)
    
    window = QWidget()
    window.setWindowTitle("PlaybackController Test")
    window.resize(400, 150)
    
    layout = QVBoxLayout(window)
    
    # Status
    status = QLabel("Frame: 0 / 0 | Time: 0.00s / 0.00s")
    layout.addWidget(status)
    
    # Slider
    slider = QSlider(Qt.Horizontal)
    slider.setRange(0, 1000)
    layout.addWidget(slider)
    
    # Controls
    controls = QHBoxLayout()
    btn_prev = QPushButton("⏮")
    btn_play = QPushButton("▶")
    btn_pause = QPushButton("⏸")
    btn_next = QPushButton("⏭")
    
    controls.addWidget(btn_prev)
    controls.addWidget(btn_play)
    controls.addWidget(btn_pause)
    controls.addWidget(btn_next)
    layout.addLayout(controls)
    
    # Controller
    ctrl = PlaybackController()
    ctrl.set_video_info(total_frames=300, fps=30.0, duration=10.0)
    
    # Connect
    def on_position(frame, total, time_s, duration_s):
        status.setText(f"Frame: {frame} / {total} | Time: {time_s:.2f}s / {duration_s:.2f}s")
        slider.blockSignals(True)
        slider.setValue(int(1000 * frame / max(1, total - 1)))
        slider.blockSignals(False)
    
    ctrl.position_changed.connect(on_position)
    
    btn_prev.clicked.connect(ctrl.step_backward)
    btn_play.clicked.connect(ctrl.play)
    btn_pause.clicked.connect(ctrl.pause)
    btn_next.clicked.connect(ctrl.step_forward)
    
    slider.sliderMoved.connect(lambda v: ctrl.seek_to_position(v / 1000.0))
    
    # Frame callback
    ctrl.set_frame_callback(lambda f: print(f"Frame: {f}"))
    
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
