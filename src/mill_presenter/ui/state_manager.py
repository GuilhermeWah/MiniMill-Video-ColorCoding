# MillPresenter V2 — State Manager (STEP-15)

"""
UI State Machine for MillPresenter.

Manages application state transitions and provides state-gated control enabling.
All UI components should query this manager before enabling/disabling controls.

States:
    IDLE          → No video loaded
    VIDEO_LOADED  → Video open, no cache
    PROCESSING    → Detection running
    CACHE_READY   → Cache loaded, ready for playback

Example:
    state_mgr = StateManager()
    state_mgr.state_changed.connect(on_state_changed)
    state_mgr.transition_to(AppState.VIDEO_LOADED)
"""

from enum import Enum, auto
from typing import Dict, Set, Optional, Any
from dataclasses import dataclass, field

from PySide6.QtCore import QObject, Signal


class AppState(Enum):
    """Application state enumeration."""
    IDLE = auto()           # No video loaded
    VIDEO_LOADED = auto()   # Video loaded, no cache
    PROCESSING = auto()     # Detection in progress
    CACHE_READY = auto()    # Cache loaded, playback ready


@dataclass
class StateInfo:
    """Information about a state for UI display."""
    label: str              # Short label for state pill
    color: str              # CSS color for state pill
    description: str        # Tooltip description
    allowed_actions: Set[str] = field(default_factory=set)


# State definitions with UI metadata
STATE_DEFINITIONS: Dict[AppState, StateInfo] = {
    AppState.IDLE: StateInfo(
        label="NO VIDEO",
        color="#6B7280",  # Gray
        description="Open a video file to begin",
        allowed_actions={"open_video"}
    ),
    AppState.VIDEO_LOADED: StateInfo(
        label="VIDEO LOADED",
        color="#F59E0B",  # Amber
        description="Run detection or load existing cache",
        allowed_actions={"open_video", "run_detection", "load_cache", "playback"}
    ),
    AppState.PROCESSING: StateInfo(
        label="PROCESSING",
        color="#3B82F6",  # Blue
        description="Detection in progress...",
        allowed_actions={"cancel_detection"}
    ),
    AppState.CACHE_READY: StateInfo(
        label="CACHE READY",
        color="#10B981",  # Green
        description="Ready for playback with overlays",
        allowed_actions={
            "open_video", "run_detection", "load_cache", "playback",
            "export", "toggle_overlay", "tune_parameters"
        }
    ),
}


# Valid state transitions
VALID_TRANSITIONS: Dict[AppState, Set[AppState]] = {
    AppState.IDLE: {AppState.VIDEO_LOADED},
    AppState.VIDEO_LOADED: {AppState.PROCESSING, AppState.CACHE_READY, AppState.IDLE},
    AppState.PROCESSING: {AppState.CACHE_READY, AppState.VIDEO_LOADED},
    AppState.CACHE_READY: {AppState.VIDEO_LOADED, AppState.PROCESSING, AppState.IDLE},
}


class StateManager(QObject):
    """
    Centralized state machine for MillPresenter UI.
    
    Signals:
        state_changed(old_state, new_state): Emitted on valid state transition
        progress_updated(percent, message): Emitted during PROCESSING state
        action_availability_changed(): Emitted when action permissions change
    """
    
    # Signals
    state_changed = Signal(AppState, AppState)  # old, new
    progress_updated = Signal(int, str)         # percent (0-100), message
    action_availability_changed = Signal()
    
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._state = AppState.IDLE
        self._progress = 0
        self._progress_message = ""
        self._video_path: Optional[str] = None
        self._cache_path: Optional[str] = None
        self._metadata: Dict[str, Any] = {}
    
    # =========================================================================
    # Properties
    # =========================================================================
    
    @property
    def state(self) -> AppState:
        """Current application state."""
        return self._state
    
    @property
    def state_info(self) -> StateInfo:
        """UI metadata for current state."""
        return STATE_DEFINITIONS[self._state]
    
    @property
    def progress(self) -> int:
        """Current progress percentage (0-100) during PROCESSING."""
        return self._progress
    
    @property
    def progress_message(self) -> str:
        """Current progress message during PROCESSING."""
        return self._progress_message
    
    @property
    def video_path(self) -> Optional[str]:
        """Path to currently loaded video."""
        return self._video_path
    
    @property
    def cache_path(self) -> Optional[str]:
        """Path to currently loaded cache."""
        return self._cache_path
    
    # =========================================================================
    # State Queries
    # =========================================================================
    
    def is_action_allowed(self, action: str) -> bool:
        """
        Check if an action is allowed in current state.
        
        Args:
            action: Action name (e.g., "playback", "run_detection")
            
        Returns:
            True if action is allowed in current state
        """
        return action in STATE_DEFINITIONS[self._state].allowed_actions
    
    def can_transition_to(self, new_state: AppState) -> bool:
        """
        Check if transition to new_state is valid.
        
        Args:
            new_state: Target state
            
        Returns:
            True if transition is allowed
        """
        return new_state in VALID_TRANSITIONS.get(self._state, set())
    
    def get_disabled_reason(self, action: str) -> Optional[str]:
        """
        Get human-readable reason why an action is disabled.
        
        Args:
            action: Action name
            
        Returns:
            Reason string or None if action is allowed
        """
        if self.is_action_allowed(action):
            return None
        
        reasons = {
            "playback": {
                AppState.IDLE: "Open a video first",
                AppState.PROCESSING: "Wait for detection to complete",
            },
            "run_detection": {
                AppState.IDLE: "Open a video first",
                AppState.PROCESSING: "Detection already in progress",
            },
            "toggle_overlay": {
                AppState.IDLE: "Open a video and run detection first",
                AppState.VIDEO_LOADED: "Run detection or load cache first",
                AppState.PROCESSING: "Wait for detection to complete",
            },
            "export": {
                AppState.IDLE: "Open a video and run detection first",
                AppState.VIDEO_LOADED: "Run detection or load cache first",
                AppState.PROCESSING: "Wait for detection to complete",
            },
            "tune_parameters": {
                AppState.IDLE: "Open a video and run detection first",
                AppState.VIDEO_LOADED: "Run detection or load cache first",
                AppState.PROCESSING: "Wait for detection to complete",
            },
        }
        
        action_reasons = reasons.get(action, {})
        return action_reasons.get(self._state, f"Action '{action}' not available")
    
    # =========================================================================
    # State Transitions
    # =========================================================================
    
    def transition_to(self, new_state: AppState) -> bool:
        """
        Transition to a new state.
        
        Args:
            new_state: Target state
            
        Returns:
            True if transition successful, False if invalid
        """
        if not self.can_transition_to(new_state):
            return False
        
        old_state = self._state
        self._state = new_state
        
        # Reset progress when leaving PROCESSING
        if old_state == AppState.PROCESSING:
            self._progress = 0
            self._progress_message = ""
        
        self.state_changed.emit(old_state, new_state)
        self.action_availability_changed.emit()
        return True
    
    def set_video_loaded(self, video_path: str) -> bool:
        """
        Set video loaded state.
        
        Args:
            video_path: Path to loaded video
            
        Returns:
            True if transition successful
        """
        self._video_path = video_path
        self._cache_path = None
        
        if self._state == AppState.IDLE:
            return self.transition_to(AppState.VIDEO_LOADED)
        elif self._state in (AppState.CACHE_READY,):
            # Reloading a different video
            return self.transition_to(AppState.VIDEO_LOADED)
        return True
    
    def set_processing_started(self) -> bool:
        """
        Start processing state.
        
        Returns:
            True if transition successful
        """
        self._progress = 0
        self._progress_message = "Starting..."
        return self.transition_to(AppState.PROCESSING)
    
    def update_progress(self, percent: int, message: str = "") -> None:
        """
        Update processing progress.
        
        Args:
            percent: Progress percentage (0-100)
            message: Optional status message
        """
        if self._state != AppState.PROCESSING:
            return
        
        self._progress = max(0, min(100, percent))
        self._progress_message = message
        self.progress_updated.emit(self._progress, self._progress_message)
    
    def set_cache_ready(self, cache_path: str) -> bool:
        """
        Set cache ready state.
        
        Args:
            cache_path: Path to loaded/generated cache
            
        Returns:
            True if transition successful
        """
        self._cache_path = cache_path
        return self.transition_to(AppState.CACHE_READY)
    
    def set_processing_cancelled(self) -> bool:
        """
        Cancel processing and return to VIDEO_LOADED.
        
        Returns:
            True if transition successful
        """
        if self._state == AppState.PROCESSING:
            return self.transition_to(AppState.VIDEO_LOADED)
        return False
    
    def reset(self) -> None:
        """Reset to IDLE state, clearing all data."""
        self._video_path = None
        self._cache_path = None
        self._progress = 0
        self._progress_message = ""
        self._metadata.clear()
        
        old_state = self._state
        self._state = AppState.IDLE
        
        if old_state != AppState.IDLE:
            self.state_changed.emit(old_state, AppState.IDLE)
            self.action_availability_changed.emit()
    
    # =========================================================================
    # Metadata
    # =========================================================================
    
    def set_metadata(self, key: str, value: Any) -> None:
        """Store arbitrary metadata."""
        self._metadata[key] = value
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Retrieve metadata."""
        return self._metadata.get(key, default)
