"""
Bottom Bar Widget

Timeline scrubber and transport controls for video playback.

Layout:
┌─────────────────────────────────────────────────────────────────────────────┐
│ ⏮ ◀ ▶/⏸ ▶ ⏭ 🔁 │ ══════════════●══════════════ │ 15:32/45:00 │ 1.0x ▼ │
└─────────────────────────────────────────────────────────────────────────────┘

HCI Principles Applied:
- Match Real World (Nielsen #2): Standard media player metaphors
- User Control (Nielsen #3): Direct manipulation timeline
- Consistency (Nielsen #4): Familiar transport buttons
"""

from PySide6.QtWidgets import (
    QWidget, QFrame, QHBoxLayout, QVBoxLayout, QPushButton, 
    QSlider, QLabel, QComboBox, QSizePolicy, QToolButton
)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QFont, QKeySequence, QShortcut

from ui.theme import COLORS, DIMENSIONS, TYPOGRAPHY
from ui.state import AppState, AppStateManager, PlaybackState


class TransportButton(QToolButton):
    """Styled transport control button."""
    
    def __init__(self, icon_text: str, tooltip: str, shortcut: str = None, parent=None):
        super().__init__(parent)
        self.setText(icon_text)
        self.setToolTip(f"{tooltip}" + (f" ({shortcut})" if shortcut else ""))
        
        # Bigger button size for better visibility
        button_size = DIMENSIONS.TRANSPORT_BUTTON_SIZE + 8  # 32 -> 40
        self.setFixedSize(button_size, button_size)
        
        # Larger, clearer icons
        font = QFont()
        font.setPointSize(18)  # Increased from 14
        self.setFont(font)
        
        self.setStyleSheet(f"""
            QToolButton {{
                background-color: transparent;
                border: none;
                border-radius: 6px;
                color: {COLORS.TEXT_PRIMARY};
                padding: 2px;
            }}
            QToolButton:hover {{
                background-color: {COLORS.BG_HOVER};
            }}
            QToolButton:pressed {{
                background-color: {COLORS.BG_PRESSED};
            }}
            QToolButton:disabled {{
                color: {COLORS.TEXT_DISABLED};
            }}
            QToolButton:checked {{
                background-color: {COLORS.ACCENT};
            }}
        """)


class TimelineSlider(QSlider):
    """
    Video timeline scrubber.
    
    Allows seeking to any frame in the video.
    Shows current position as a percentage of duration.
    """
    
    def __init__(self, parent=None):
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.setMinimum(0)
        self.setMaximum(1000)  # Will be set to actual frame count
        self.setValue(0)
        self.setTracking(True)  # Emit valueChanged while dragging
        
        self.setFixedHeight(DIMENSIONS.SCRUBBER_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        self.setToolTip("Seek through video (drag or click)")


class TimeDisplay(QLabel):
    """Shows current time / total time."""
    
    def __init__(self, parent=None):
        super().__init__("00:00 / 00:00", parent)
        font = QFont(TYPOGRAPHY.FONT_FAMILY_MONO, TYPOGRAPHY.SIZE_NORMAL)
        self.setFont(font)
        self.setMinimumWidth(100)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
    def set_time(self, current_seconds: float, total_seconds: float):
        """Update the time display."""
        current = self._format_time(current_seconds)
        total = self._format_time(total_seconds)
        self.setText(f"{current} / {total}")
    
    def set_frames(self, current_frame: int, total_frames: int, fps: float):
        """Update display using frame numbers."""
        current_sec = current_frame / fps if fps > 0 else 0
        total_sec = total_frames / fps if fps > 0 else 0
        self.set_time(current_sec, total_sec)
        self.setToolTip(f"Frame {current_frame} / {total_frames}")
    
    @staticmethod
    def _format_time(seconds: float) -> str:
        """Format seconds as MM:SS."""
        mins = int(seconds) // 60
        secs = int(seconds) % 60
        return f"{mins:02d}:{secs:02d}"


class SpeedSelector(QComboBox):
    """Playback speed dropdown."""
    
    SPEEDS = [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0]
    
    speed_changed = Signal(float)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        for speed in self.SPEEDS:
            self.addItem(f"{speed}x", speed)
        
        # Default to 1.0x
        self.setCurrentIndex(self.SPEEDS.index(1.0))
        
        self.setFixedWidth(70)
        self.setToolTip("Playback speed")
        
        self.currentIndexChanged.connect(self._on_index_changed)
    
    def _on_index_changed(self, index: int):
        speed = self.itemData(index)
        if speed is not None:
            self.speed_changed.emit(speed)
    
    def set_speed(self, speed: float):
        """Set the current speed."""
        if speed in self.SPEEDS:
            self.setCurrentIndex(self.SPEEDS.index(speed))


class BottomBar(QFrame):
    """
    Bottom bar with timeline and transport controls.
    
    Signals:
        play_toggled: Emitted when play/pause clicked
        frame_changed: Emitted when timeline slider moved (frame index)
        speed_changed: Emitted when playback speed changed
        step_forward: Emitted for step +1 frame
        step_backward: Emitted for step -1 frame
        jump_forward: Emitted for step +10 frames
        jump_backward: Emitted for step -10 frames
        go_to_start: Emitted for jump to first frame
        go_to_end: Emitted for jump to last frame
        loop_toggled: Emitted when loop button clicked
    """
    
    # Signals for external handling
    play_toggled = Signal(bool)  # True = now playing
    frame_changed = Signal(int)  # Frame index
    speed_changed = Signal(float)
    step_forward = Signal()
    step_backward = Signal()
    jump_forward = Signal()
    jump_backward = Signal()
    go_to_start = Signal()
    go_to_end = Signal()
    loop_toggled = Signal(bool)
    fullscreen_toggled = Signal()  # Fullscreen toggle
    
    def __init__(self, state_manager: AppStateManager = None, parent=None):
        super().__init__(parent)
        self.state_manager = state_manager
        
        self._is_playing = False
        self._is_looping = False
        self._total_frames = 0
        self._fps = 30.0
        
        self._setup_ui()
        self._connect_signals()
        self._update_enabled_state(AppState.IDLE)
    
    def _setup_ui(self):
        self.setFixedHeight(DIMENSIONS.BOTTOM_BAR_HEIGHT + 8)  # Taller for bigger buttons
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setStyleSheet(f"""
            BottomBar {{
                background-color: {COLORS.BG_PANEL};
                border-top: 1px solid {COLORS.BORDER};
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(8)
        
        # Transport controls group
        transport_layout = QHBoxLayout()
        transport_layout.setSpacing(2)
        
        self.btn_start = TransportButton("⏮", "Go to start", "Home")
        self.btn_jump_back = TransportButton("⏪", "Jump -10 frames", "Shift+←")
        self.btn_step_back = TransportButton("◀", "Step -1 frame", "←")
        self.btn_play = TransportButton("▶", "Play/Pause", "Space")
        self.btn_step_fwd = TransportButton("▶", "Step +1 frame", "→")
        self.btn_jump_fwd = TransportButton("⏩", "Jump +10 frames", "Shift+→")
        self.btn_end = TransportButton("⏭", "Go to end", "End")
        self.btn_loop = TransportButton("🔁", "Toggle loop", "L")
        self.btn_loop.setCheckable(True)
        
        # Make step buttons smaller symbols
        self.btn_step_back.setText("◁")
        self.btn_step_fwd.setText("▷")
        
        transport_layout.addWidget(self.btn_start)
        transport_layout.addWidget(self.btn_jump_back)
        transport_layout.addWidget(self.btn_step_back)
        transport_layout.addWidget(self.btn_play)
        transport_layout.addWidget(self.btn_step_fwd)
        transport_layout.addWidget(self.btn_jump_fwd)
        transport_layout.addWidget(self.btn_end)
        transport_layout.addSpacing(8)
        transport_layout.addWidget(self.btn_loop)
        
        layout.addLayout(transport_layout)
        
        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet(f"background-color: {COLORS.SEPARATOR};")
        layout.addWidget(sep)
        
        # Timeline slider
        self.timeline = TimelineSlider()
        layout.addWidget(self.timeline, stretch=1)
        
        # Separator
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.VLine)
        sep2.setStyleSheet(f"background-color: {COLORS.SEPARATOR};")
        layout.addWidget(sep2)
        
        # Time display
        self.time_display = TimeDisplay()
        layout.addWidget(self.time_display)
        
        # Separator
        sep3 = QFrame()
        sep3.setFrameShape(QFrame.Shape.VLine)
        sep3.setStyleSheet(f"background-color: {COLORS.SEPARATOR};")
        layout.addWidget(sep3)
        
        # Speed selector
        self.speed_selector = SpeedSelector()
        layout.addWidget(self.speed_selector)
        
        # Separator
        sep4 = QFrame()
        sep4.setFrameShape(QFrame.Shape.VLine)
        sep4.setStyleSheet(f"background-color: {COLORS.SEPARATOR};")
        layout.addWidget(sep4)
        
        # Fullscreen button
        self.btn_fullscreen = TransportButton("⛶", "Toggle Fullscreen", "F11")
        layout.addWidget(self.btn_fullscreen)
        
        # Connect button signals
        self.btn_play.clicked.connect(self._on_play_clicked)
        self.btn_start.clicked.connect(self.go_to_start.emit)
        self.btn_end.clicked.connect(self.go_to_end.emit)
        self.btn_step_back.clicked.connect(self.step_backward.emit)
        self.btn_step_fwd.clicked.connect(self.step_forward.emit)
        self.btn_jump_back.clicked.connect(self.jump_backward.emit)
        self.btn_jump_fwd.clicked.connect(self.jump_forward.emit)
        self.btn_loop.clicked.connect(self._on_loop_clicked)
        self.btn_fullscreen.clicked.connect(self.fullscreen_toggled.emit)
        
        self.timeline.valueChanged.connect(self._on_timeline_changed)
        self.speed_selector.speed_changed.connect(self.speed_changed.emit)
    
    def _connect_signals(self):
        """Connect to state manager."""
        if self.state_manager:
            self.state_manager.state_changed.connect(self._on_state_changed)
            self.state_manager.playback_changed.connect(self._on_playback_changed)
    
    def _on_play_clicked(self):
        """Toggle play state."""
        self._is_playing = not self._is_playing
        self._update_play_button()
        self.play_toggled.emit(self._is_playing)
    
    def _on_loop_clicked(self):
        """Toggle loop state."""
        self._is_looping = self.btn_loop.isChecked()
        self.loop_toggled.emit(self._is_looping)
    
    def _on_timeline_changed(self, value: int):
        """Handle timeline slider movement."""
        self.frame_changed.emit(value)
        self._update_time_display(value)
    
    def _update_play_button(self):
        """Update play button icon based on state."""
        self.btn_play.setText("⏸" if self._is_playing else "▶")
    
    def _update_time_display(self, frame: int):
        """Update time display for current frame."""
        self.time_display.set_frames(frame, self._total_frames, self._fps)
    
    @Slot(AppState, AppState)
    def _on_state_changed(self, old_state: AppState, new_state: AppState):
        """Update enabled state based on app state."""
        self._update_enabled_state(new_state)
    
    @Slot(PlaybackState)
    def _on_playback_changed(self, state: PlaybackState):
        """Sync with playback state."""
        self._is_playing = state.is_playing
        self._is_looping = state.is_looping
        self._update_play_button()
        self.btn_loop.setChecked(self._is_looping)
        self.speed_selector.set_speed(state.playback_speed)
        self.set_current_frame(state.current_frame)
    
    def _update_enabled_state(self, state: AppState):
        """Enable/disable controls based on app state."""
        can_play = state in (AppState.VIDEO_LOADED, AppState.CACHE_READY)
        
        self.btn_play.setEnabled(can_play)
        self.btn_start.setEnabled(can_play)
        self.btn_end.setEnabled(can_play)
        self.btn_step_back.setEnabled(can_play)
        self.btn_step_fwd.setEnabled(can_play)
        self.btn_jump_back.setEnabled(can_play)
        self.btn_jump_fwd.setEnabled(can_play)
        self.btn_loop.setEnabled(can_play)
        self.timeline.setEnabled(can_play)
        self.speed_selector.setEnabled(can_play)
    
    # Public API
    def set_video_info(self, total_frames: int, fps: float):
        """Configure for a loaded video."""
        self._total_frames = total_frames
        self._fps = fps
        self.timeline.setMaximum(max(0, total_frames - 1))
        self._update_time_display(0)
    
    def set_current_frame(self, frame: int):
        """Set current frame (without emitting signal)."""
        self.timeline.blockSignals(True)
        self.timeline.setValue(frame)
        self.timeline.blockSignals(False)
        self._update_time_display(frame)
    
    def set_playing(self, playing: bool):
        """Set play state externally."""
        self._is_playing = playing
        self._update_play_button()
    
    def set_state_manager(self, manager: AppStateManager):
        """Set or replace state manager."""
        if self.state_manager:
            try:
                self.state_manager.state_changed.disconnect(self._on_state_changed)
                self.state_manager.playback_changed.disconnect(self._on_playback_changed)
            except RuntimeError:
                pass
        
        self.state_manager = manager
        self._connect_signals()
        
        if manager:
            self._update_enabled_state(manager.state)
