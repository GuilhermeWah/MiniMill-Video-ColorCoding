"""
MillPresenter Application State Management

Implements a finite state machine for application state with Qt signals.
Central source of truth for what the application is currently doing.

States:
- IDLE: No video loaded
- VIDEO_LOADED: Video open but no detection cache
- PROCESSING: Detection pipeline running (background thread)
- CACHE_READY: Detections loaded, ready for playback
- ERROR: Something went wrong

State transitions are explicit and validated.
UI components observe state changes via signals.
"""

from enum import Enum, auto
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from PySide6.QtCore import QObject, Signal


class AppState(Enum):
    """Application state enumeration."""
    IDLE = auto()           # No video loaded
    VIDEO_LOADED = auto()   # Video open, no cache
    PROCESSING = auto()     # Detection running
    CACHE_READY = auto()    # Ready for playback
    ERROR = auto()          # Error state


# Valid state transitions (from_state -> list of allowed to_states)
VALID_TRANSITIONS: Dict[AppState, list] = {
    AppState.IDLE: [AppState.VIDEO_LOADED, AppState.ERROR],
    AppState.VIDEO_LOADED: [AppState.PROCESSING, AppState.CACHE_READY, AppState.IDLE, AppState.ERROR],
    AppState.PROCESSING: [AppState.CACHE_READY, AppState.VIDEO_LOADED, AppState.ERROR],
    AppState.CACHE_READY: [AppState.PROCESSING, AppState.VIDEO_LOADED, AppState.IDLE, AppState.ERROR],
    AppState.ERROR: [AppState.IDLE, AppState.VIDEO_LOADED],
}


@dataclass
class VideoInfo:
    """Metadata about the currently loaded video."""
    path: str = ""
    name: str = ""
    width: int = 0
    height: int = 0
    fps: float = 30.0
    total_frames: int = 0
    duration_seconds: float = 0.0
    
    @property
    def is_loaded(self) -> bool:
        return bool(self.path)
    
    def clear(self):
        """Reset all fields."""
        self.path = ""
        self.name = ""
        self.width = 0
        self.height = 0
        self.fps = 30.0
        self.total_frames = 0
        self.duration_seconds = 0.0


@dataclass
class CacheInfo:
    """Metadata about loaded detection cache."""
    path: str = ""
    total_frames: int = 0
    px_per_mm: float = 0.0
    drum_center: tuple = (0, 0)
    drum_radius: int = 0
    is_loaded: bool = False
    
    def clear(self):
        """Reset all fields."""
        self.path = ""
        self.total_frames = 0
        self.px_per_mm = 0.0
        self.drum_center = (0, 0)
        self.drum_radius = 0
        self.is_loaded = False


@dataclass
class PlaybackState:
    """Current playback state."""
    is_playing: bool = False
    is_looping: bool = False
    current_frame: int = 0
    playback_speed: float = 1.0
    
    def reset(self):
        """Reset to initial state."""
        self.is_playing = False
        self.is_looping = False
        self.current_frame = 0
        self.playback_speed = 1.0


@dataclass 
class OverlaySettings:
    """Overlay visualization settings."""
    show_overlays: bool = True
    opacity: float = 1.0
    min_confidence: float = 0.0
    
    # Per-class visibility
    show_4mm: bool = True
    show_6mm: bool = True
    show_8mm: bool = True
    show_10mm: bool = True
    
    # Labels
    show_size_labels: bool = False
    show_confidence_labels: bool = False
    
    def get_visible_classes(self) -> list:
        """Return list of visible class names."""
        classes = []
        if self.show_4mm:
            classes.append("4mm")
        if self.show_6mm:
            classes.append("6mm")
        if self.show_8mm:
            classes.append("8mm")
        if self.show_10mm:
            classes.append("10mm")
        return classes


class AppStateManager(QObject):
    """
    Central state manager for the application.
    
    Emits signals when state changes occur, allowing UI components
    to react appropriately without tight coupling.
    
    Usage:
        state_manager = AppStateManager()
        state_manager.state_changed.connect(self.on_state_change)
        state_manager.set_state(AppState.VIDEO_LOADED)
    """
    
    # Signals
    state_changed = Signal(AppState, AppState)  # old_state, new_state
    video_changed = Signal(VideoInfo)
    cache_changed = Signal(CacheInfo)
    playback_changed = Signal(PlaybackState)
    overlay_changed = Signal(OverlaySettings)
    progress_updated = Signal(int, str)  # percent, message
    error_occurred = Signal(str)  # error message
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # State
        self._state = AppState.IDLE
        self._previous_state = AppState.IDLE
        
        # Data containers
        self.video = VideoInfo()
        self.cache = CacheInfo()
        self.playback = PlaybackState()
        self.overlay = OverlaySettings()
        
        # Error info
        self._error_message: str = ""
        
        # Processing progress
        self._progress_percent: int = 0
        self._progress_message: str = ""
    
    @property
    def state(self) -> AppState:
        """Current application state."""
        return self._state
    
    @property
    def previous_state(self) -> AppState:
        """Previous application state (for undo/recovery)."""
        return self._previous_state
    
    @property
    def error_message(self) -> str:
        """Current error message (if in ERROR state)."""
        return self._error_message
    
    def set_state(self, new_state: AppState) -> bool:
        """
        Transition to a new state.
        
        Args:
            new_state: The target state
            
        Returns:
            True if transition was valid and completed
            
        Raises:
            ValueError if transition is not allowed
        """
        if new_state == self._state:
            return True  # Already in this state
        
        # Validate transition
        allowed = VALID_TRANSITIONS.get(self._state, [])
        if new_state not in allowed:
            raise ValueError(
                f"Invalid state transition: {self._state.name} -> {new_state.name}. "
                f"Allowed: {[s.name for s in allowed]}"
            )
        
        # Perform transition
        old_state = self._state
        self._previous_state = old_state
        self._state = new_state
        
        # Clear error if leaving error state
        if old_state == AppState.ERROR:
            self._error_message = ""
        
        # Emit signal
        self.state_changed.emit(old_state, new_state)
        
        return True
    
    def set_error(self, message: str):
        """
        Transition to error state with a message.
        
        Args:
            message: Human-readable error description
        """
        self._error_message = message
        try:
            self.set_state(AppState.ERROR)
        except ValueError:
            # Force error state even if transition invalid
            self._previous_state = self._state
            self._state = AppState.ERROR
            self.state_changed.emit(self._previous_state, AppState.ERROR)
        
        self.error_occurred.emit(message)
    
    def update_progress(self, percent: int, message: str = ""):
        """
        Update processing progress.
        
        Args:
            percent: Progress percentage (0-100)
            message: Optional status message
        """
        self._progress_percent = max(0, min(100, percent))
        self._progress_message = message
        self.progress_updated.emit(self._progress_percent, self._progress_message)
    
    def set_video(self, info: VideoInfo):
        """Update video info and emit signal."""
        self.video = info
        self.video_changed.emit(info)
    
    def set_cache(self, info: CacheInfo):
        """Update cache info and emit signal."""
        self.cache = info
        self.cache_changed.emit(info)
    
    def update_playback(self):
        """Emit playback changed signal."""
        self.playback_changed.emit(self.playback)
    
    def update_overlay(self):
        """Emit overlay changed signal."""
        self.overlay_changed.emit(self.overlay)
    
    def reset(self):
        """Reset all state to initial values."""
        self._state = AppState.IDLE
        self._previous_state = AppState.IDLE
        self._error_message = ""
        self._progress_percent = 0
        self._progress_message = ""
        
        self.video.clear()
        self.cache.clear()
        self.playback.reset()
        # Don't reset overlay settings - user preference
        
        self.state_changed.emit(AppState.IDLE, AppState.IDLE)
    
    # Convenience state queries
    def is_idle(self) -> bool:
        return self._state == AppState.IDLE
    
    def is_video_loaded(self) -> bool:
        return self._state in (AppState.VIDEO_LOADED, AppState.CACHE_READY)
    
    def is_processing(self) -> bool:
        return self._state == AppState.PROCESSING
    
    def is_ready(self) -> bool:
        return self._state == AppState.CACHE_READY
    
    def is_error(self) -> bool:
        return self._state == AppState.ERROR
    
    def can_play(self) -> bool:
        """Check if playback is allowed (video or cache loaded)."""
        return self._state in (AppState.VIDEO_LOADED, AppState.CACHE_READY)
    
    def can_process(self) -> bool:
        """Check if detection processing can be started."""
        return self._state in (AppState.VIDEO_LOADED, AppState.CACHE_READY)
    
    def can_export(self) -> bool:
        """Check if export is allowed."""
        return self._state == AppState.CACHE_READY
