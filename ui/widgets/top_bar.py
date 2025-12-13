"""
Top Bar Widget

Displays application status, current video info, and provides
high-level state visibility to the user.

Layout:
┌─────────────────────────────────────────────────────────────────────┐
│ MillPresenter | Video: file.mp4 | ● READY | Detection: 100%        │
└─────────────────────────────────────────────────────────────────────┘

HCI Principles Applied:
- Visibility of System Status (Nielsen #1): Always shows current state
- Recognition over Recall (Nielsen #6): State indicated with color + text
"""

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QFont

from ui.theme import COLORS, DIMENSIONS, TYPOGRAPHY
from ui.state import AppState, AppStateManager, VideoInfo


class StatusIndicator(QWidget):
    """
    Colored dot + text showing application state.
    
    Visual States:
    - IDLE: Gray dot, "No Video"
    - VIDEO_LOADED: Blue dot, "Video Loaded"
    - PROCESSING: Orange dot, "Processing..."
    - CACHE_READY: Green dot, "Ready"
    - ERROR: Red dot, "Error"
    """
    
    STATE_CONFIG = {
        AppState.IDLE: (COLORS.STATUS_IDLE, "No Video"),
        AppState.VIDEO_LOADED: (COLORS.STATUS_VIDEO_LOADED, "Video Loaded"),
        AppState.PROCESSING: (COLORS.STATUS_PROCESSING, "Processing..."),
        AppState.CACHE_READY: (COLORS.STATUS_READY, "Ready"),
        AppState.ERROR: (COLORS.STATUS_ERROR, "Error"),
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self.set_state(AppState.IDLE)
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(6)
        
        # Status dot (using a styled QLabel)
        self.dot = QLabel("●")
        self.dot.setFixedWidth(16)
        self.dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.dot)
        
        # Status text
        self.label = QLabel("No Video")
        self.label.setProperty("secondary", True)
        layout.addWidget(self.label)
    
    def set_state(self, state: AppState):
        """Update display for the given state."""
        color, text = self.STATE_CONFIG.get(
            state, 
            (COLORS.STATUS_IDLE, "Unknown")
        )
        
        self.dot.setStyleSheet(f"color: {color}; font-size: 14px;")
        self.label.setText(text)
        
        # Tooltip with more detail
        self.setToolTip(f"Application State: {state.name}")


class ProgressIndicator(QWidget):
    """
    Shows detection progress percentage.
    Hidden when not processing.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self.hide()
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(4)
        
        self.label = QLabel("Detection:")
        self.label.setProperty("secondary", True)
        layout.addWidget(self.label)
        
        self.percent = QLabel("0%")
        layout.addWidget(self.percent)
    
    def set_progress(self, percent: int, message: str = ""):
        """Update progress display."""
        self.percent.setText(f"{percent}%")
        if message:
            self.setToolTip(message)
        self.show()
    
    def reset(self):
        """Hide and reset."""
        self.percent.setText("0%")
        self.hide()


class TopBar(QFrame):
    """
    Top bar widget containing status and global info.
    
    Fixed height, spans full window width.
    """
    
    def __init__(self, state_manager: AppStateManager = None, parent=None):
        super().__init__(parent)
        self.state_manager = state_manager
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        self.setFixedHeight(DIMENSIONS.TOP_BAR_HEIGHT)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setStyleSheet(f"""
            TopBar {{
                background-color: {COLORS.BG_PANEL};
                border-bottom: 1px solid {COLORS.BORDER};
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(16)
        
        # App title
        self.title = QLabel("MillPresenter")
        font = QFont(TYPOGRAPHY.FONT_FAMILY, TYPOGRAPHY.SIZE_TITLE)
        font.setBold(True)
        self.title.setFont(font)
        layout.addWidget(self.title)
        
        # Separator
        sep = QLabel("|")
        sep.setProperty("secondary", True)
        layout.addWidget(sep)
        
        # Video name
        self.video_label = QLabel("Video:")
        self.video_label.setProperty("secondary", True)
        layout.addWidget(self.video_label)
        
        self.video_name = QLabel("None")
        layout.addWidget(self.video_name)
        
        # Spacer
        layout.addStretch(1)
        
        # Progress indicator (visible during processing)
        self.progress = ProgressIndicator()
        layout.addWidget(self.progress)
        
        # Separator
        sep2 = QLabel("|")
        sep2.setProperty("secondary", True)
        layout.addWidget(sep2)
        
        # Status indicator
        self.status = StatusIndicator()
        layout.addWidget(self.status)
    
    def _connect_signals(self):
        """Connect to state manager signals."""
        if self.state_manager:
            self.state_manager.state_changed.connect(self._on_state_changed)
            self.state_manager.video_changed.connect(self._on_video_changed)
            self.state_manager.progress_updated.connect(self._on_progress_updated)
    
    @Slot(AppState, AppState)
    def _on_state_changed(self, old_state: AppState, new_state: AppState):
        """Handle state transitions."""
        self.status.set_state(new_state)
        
        # Show/hide progress
        if new_state == AppState.PROCESSING:
            self.progress.show()
        else:
            self.progress.reset()
    
    @Slot(VideoInfo)
    def _on_video_changed(self, info: VideoInfo):
        """Update video name display."""
        if info.is_loaded:
            self.video_name.setText(info.name)
            self.video_name.setToolTip(info.path)
        else:
            self.video_name.setText("None")
            self.video_name.setToolTip("")
    
    @Slot(int, str)
    def _on_progress_updated(self, percent: int, message: str):
        """Update progress display."""
        self.progress.set_progress(percent, message)
    
    def set_state_manager(self, manager: AppStateManager):
        """Set or replace the state manager."""
        # Disconnect old
        if self.state_manager:
            try:
                self.state_manager.state_changed.disconnect(self._on_state_changed)
                self.state_manager.video_changed.disconnect(self._on_video_changed)
                self.state_manager.progress_updated.disconnect(self._on_progress_updated)
            except RuntimeError:
                pass
        
        # Connect new
        self.state_manager = manager
        self._connect_signals()
        
        # Sync current state
        if manager:
            self.status.set_state(manager.state)
            self._on_video_changed(manager.video)
