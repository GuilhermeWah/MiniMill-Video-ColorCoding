"""
Unit tests for STEP-15: StateManager

Tests state machine transitions and action gating.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mill_presenter.ui.state_manager import (
    StateManager, AppState, STATE_DEFINITIONS, VALID_TRANSITIONS
)


class TestStateManagerInit:
    """Tests for StateManager initialization."""
    
    def test_initial_state_is_idle(self):
        """Test that initial state is IDLE."""
        mgr = StateManager()
        assert mgr.state == AppState.IDLE
    
    def test_initial_properties(self):
        """Test initial property values."""
        mgr = StateManager()
        assert mgr.video_path is None
        assert mgr.cache_path is None
        assert mgr.progress == 0
        assert mgr.progress_message == ""


class TestStateTransitions:
    """Tests for state transitions."""
    
    def test_idle_to_video_loaded(self):
        """Test transition from IDLE to VIDEO_LOADED."""
        mgr = StateManager()
        assert mgr.can_transition_to(AppState.VIDEO_LOADED)
        assert mgr.transition_to(AppState.VIDEO_LOADED)
        assert mgr.state == AppState.VIDEO_LOADED
    
    def test_invalid_transition_rejected(self):
        """Test that invalid transitions are rejected."""
        mgr = StateManager()  # IDLE
        assert not mgr.can_transition_to(AppState.CACHE_READY)
        assert not mgr.transition_to(AppState.CACHE_READY)
        assert mgr.state == AppState.IDLE  # Unchanged
    
    def test_video_loaded_to_processing(self):
        """Test transition from VIDEO_LOADED to PROCESSING."""
        mgr = StateManager()
        mgr.transition_to(AppState.VIDEO_LOADED)
        
        assert mgr.can_transition_to(AppState.PROCESSING)
        assert mgr.transition_to(AppState.PROCESSING)
        assert mgr.state == AppState.PROCESSING
    
    def test_processing_to_cache_ready(self):
        """Test transition from PROCESSING to CACHE_READY."""
        mgr = StateManager()
        mgr.transition_to(AppState.VIDEO_LOADED)
        mgr.transition_to(AppState.PROCESSING)
        
        assert mgr.transition_to(AppState.CACHE_READY)
        assert mgr.state == AppState.CACHE_READY
    
    def test_processing_to_video_loaded_on_cancel(self):
        """Test cancellation returns to VIDEO_LOADED."""
        mgr = StateManager()
        mgr.transition_to(AppState.VIDEO_LOADED)
        mgr.transition_to(AppState.PROCESSING)
        
        assert mgr.set_processing_cancelled()
        assert mgr.state == AppState.VIDEO_LOADED


class TestActionGating:
    """Tests for action permission checking."""
    
    def test_idle_only_allows_open_video(self):
        """Test IDLE state only allows open_video."""
        mgr = StateManager()
        
        assert mgr.is_action_allowed("open_video")
        assert not mgr.is_action_allowed("playback")
        assert not mgr.is_action_allowed("run_detection")
        assert not mgr.is_action_allowed("export")
    
    def test_video_loaded_allows_detection(self):
        """Test VIDEO_LOADED allows detection."""
        mgr = StateManager()
        mgr.transition_to(AppState.VIDEO_LOADED)
        
        assert mgr.is_action_allowed("run_detection")
        assert mgr.is_action_allowed("load_cache")
        assert mgr.is_action_allowed("playback")
    
    def test_processing_only_allows_cancel(self):
        """Test PROCESSING only allows cancel."""
        mgr = StateManager()
        mgr.transition_to(AppState.VIDEO_LOADED)
        mgr.transition_to(AppState.PROCESSING)
        
        assert mgr.is_action_allowed("cancel_detection")
        assert not mgr.is_action_allowed("playback")
        assert not mgr.is_action_allowed("export")
    
    def test_cache_ready_allows_all(self):
        """Test CACHE_READY allows full functionality."""
        mgr = StateManager()
        mgr.transition_to(AppState.VIDEO_LOADED)
        mgr.transition_to(AppState.CACHE_READY)
        
        assert mgr.is_action_allowed("playback")
        assert mgr.is_action_allowed("export")
        assert mgr.is_action_allowed("toggle_overlay")
        assert mgr.is_action_allowed("tune_parameters")


class TestDisabledReasons:
    """Tests for disabled action reasons."""
    
    def test_reason_for_disabled_playback(self):
        """Test reason for disabled playback in IDLE."""
        mgr = StateManager()
        reason = mgr.get_disabled_reason("playback")
        
        assert reason is not None
        assert "video" in reason.lower()
    
    def test_no_reason_for_allowed_action(self):
        """Test no reason for allowed action."""
        mgr = StateManager()
        reason = mgr.get_disabled_reason("open_video")
        
        assert reason is None


class TestProgressTracking:
    """Tests for progress tracking during PROCESSING."""
    
    def test_progress_update(self):
        """Test progress updates during processing."""
        mgr = StateManager()
        mgr.transition_to(AppState.VIDEO_LOADED)
        mgr.set_processing_started()
        
        mgr.update_progress(50, "Processing frame 100/200")
        
        assert mgr.progress == 50
        assert "100" in mgr.progress_message
    
    def test_progress_clamp(self):
        """Test progress is clamped to 0-100."""
        mgr = StateManager()
        mgr.transition_to(AppState.VIDEO_LOADED)
        mgr.set_processing_started()
        
        mgr.update_progress(150, "Over")
        assert mgr.progress == 100
        
        mgr.update_progress(-10, "Under")
        assert mgr.progress == 0
    
    def test_progress_reset_on_state_change(self):
        """Test progress resets when leaving PROCESSING."""
        mgr = StateManager()
        mgr.transition_to(AppState.VIDEO_LOADED)
        mgr.set_processing_started()
        mgr.update_progress(75, "Almost done")
        
        mgr.transition_to(AppState.CACHE_READY)
        
        assert mgr.progress == 0
        assert mgr.progress_message == ""


class TestHelperMethods:
    """Tests for helper methods."""
    
    def test_set_video_loaded(self):
        """Test set_video_loaded helper."""
        mgr = StateManager()
        result = mgr.set_video_loaded("/path/to/video.mov")
        
        assert result is True
        assert mgr.state == AppState.VIDEO_LOADED
        assert mgr.video_path == "/path/to/video.mov"
    
    def test_set_cache_ready(self):
        """Test set_cache_ready helper."""
        mgr = StateManager()
        mgr.set_video_loaded("/path/to/video.mov")
        
        result = mgr.set_cache_ready("/path/to/cache.json")
        
        assert result is True
        assert mgr.state == AppState.CACHE_READY
        assert mgr.cache_path == "/path/to/cache.json"
    
    def test_reset(self):
        """Test reset clears all state."""
        mgr = StateManager()
        mgr.set_video_loaded("/path/to/video.mov")
        mgr.set_cache_ready("/path/to/cache.json")
        
        mgr.reset()
        
        assert mgr.state == AppState.IDLE
        assert mgr.video_path is None
        assert mgr.cache_path is None


class TestStateInfo:
    """Tests for state UI metadata."""
    
    def test_all_states_have_definitions(self):
        """Test all states have UI definitions."""
        for state in AppState:
            assert state in STATE_DEFINITIONS
    
    def test_state_info_properties(self):
        """Test state info has required properties."""
        mgr = StateManager()
        info = mgr.state_info
        
        assert info.label
        assert info.color
        assert info.description
        assert isinstance(info.allowed_actions, set)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
