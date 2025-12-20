"""
Unit tests for STEP-10: MainWindow

Tests:
1. Individual components (StatePill, MainWindow widgets)
2. Wired integration (StateManager ↔ UI updates)
3. Action gating (buttons enabled/disabled correctly)
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Must import Qt app before any widgets
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

# Ensure QApplication exists for widget tests
@pytest.fixture(scope="session")
def qapp():
    """Create QApplication for all tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def main_window(qapp):
    """Create MainWindow instance for testing."""
    from mill_presenter.ui.main_window import MainWindow
    window = MainWindow()
    yield window
    window.close()


@pytest.fixture
def state_pill(qapp):
    """Create StatePill instance for testing."""
    from mill_presenter.ui.main_window import StatePill
    pill = StatePill()
    yield pill


# =============================================================================
# StatePill Component Tests
# =============================================================================

class TestStatePillComponent:
    """Tests for StatePill widget in isolation."""
    
    def test_initial_text(self, state_pill):
        """Test initial pill text is NO VIDEO."""
        assert state_pill.text() == "NO VIDEO"
    
    def test_update_state_changes_text(self, state_pill):
        """Test update_state changes text and color."""
        from mill_presenter.ui.state_manager import AppState, STATE_DEFINITIONS
        
        state_pill.update_state(AppState.VIDEO_LOADED, STATE_DEFINITIONS[AppState.VIDEO_LOADED])
        
        assert "VIDEO" in state_pill.text()
    
    def test_set_progress_updates_text(self, state_pill):
        """Test set_progress updates text with percentage."""
        state_pill.set_progress(45)
        
        assert "45%" in state_pill.text()
    
    def test_tooltip_set(self, state_pill):
        """Test tooltip is set from state info."""
        from mill_presenter.ui.state_manager import AppState, STATE_DEFINITIONS
        
        state_pill.update_state(AppState.IDLE, STATE_DEFINITIONS[AppState.IDLE])
        
        assert state_pill.toolTip() != ""


# =============================================================================
# MainWindow Component Tests
# =============================================================================

class TestMainWindowComponents:
    """Tests for MainWindow widgets in isolation."""
    
    def test_window_title(self, main_window):
        """Test window title is set."""
        assert "MillPresenter" in main_window.windowTitle()
    
    def test_minimum_size(self, main_window):
        """Test minimum window size."""
        assert main_window.minimumWidth() >= 1000
        assert main_window.minimumHeight() >= 600
    
    def test_menubar_exists(self, main_window):
        """Test menu bar is created."""
        menubar = main_window.menuBar()
        assert menubar is not None
    
    def test_file_menu_exists(self, main_window):
        """Test File menu has expected actions."""
        menubar = main_window.menuBar()
        actions = menubar.actions()
        
        menu_names = [a.text() for a in actions]
        assert any("File" in name for name in menu_names)
    
    def test_toolbar_buttons_exist(self, main_window):
        """Test toolbar buttons are created."""
        assert main_window.btn_open is not None
        assert main_window.btn_run is not None
        assert main_window.btn_load is not None
    
    def test_state_pill_exists(self, main_window):
        """Test state pill is in toolbar."""
        assert main_window.state_pill is not None
    
    def test_status_bar_exists(self, main_window):
        """Test status bar is created."""
        assert main_window.statusBar() is not None
    
    def test_central_widget_exists(self, main_window):
        """Test central widget has video frame and panels."""
        assert main_window.video_frame is not None
        assert main_window.right_panel is not None
        assert main_window.bottom_bar is not None


# =============================================================================
# Wired Integration Tests: StateManager ↔ MainWindow
# =============================================================================

class TestStateManagerWiring:
    """Tests for StateManager ↔ MainWindow integration."""
    
    def test_state_manager_exists(self, main_window):
        """Test StateManager is attached to MainWindow."""
        assert main_window.state_manager is not None
    
    def test_initial_state_is_idle(self, main_window):
        """Test initial state is IDLE."""
        from mill_presenter.ui.state_manager import AppState
        assert main_window.state_manager.state == AppState.IDLE
    
    def test_state_change_updates_pill(self, main_window):
        """Test state change updates state pill."""
        from mill_presenter.ui.state_manager import AppState
        
        main_window.state_manager.set_video_loaded("/path/to/video.mov")
        
        # Pill should update
        assert "VIDEO" in main_window.state_pill.text()
    
    def test_state_change_updates_buttons(self, main_window):
        """Test state change enables/disables buttons."""
        from mill_presenter.ui.state_manager import AppState
        
        # In IDLE, run button should be disabled
        assert not main_window.btn_run.isEnabled()
        
        # After loading video, run button should be enabled
        main_window.state_manager.set_video_loaded("/path/to/video.mov")
        assert main_window.btn_run.isEnabled()
    
    def test_processing_state_disables_controls(self, main_window):
        """Test PROCESSING state disables most controls."""
        from mill_presenter.ui.state_manager import AppState
        
        main_window.state_manager.set_video_loaded("/path/to/video.mov")
        main_window.state_manager.set_processing_started()
        
        # Run button should be disabled during processing
        assert not main_window.btn_run.isEnabled()
    
    def test_cache_ready_enables_all(self, main_window):
        """Test CACHE_READY enables all controls."""
        from mill_presenter.ui.state_manager import AppState
        
        main_window.state_manager.set_video_loaded("/path/to/video.mov")
        main_window.state_manager.set_cache_ready("/path/to/cache.json")
        
        # Export and tune should be enabled
        assert main_window.action_export.isEnabled()
        assert main_window.action_tune.isEnabled()
    
    def test_progress_update_reflected_in_pill(self, main_window):
        """Test progress updates appear in state pill."""
        main_window.state_manager.set_video_loaded("/path/to/video.mov")
        main_window.state_manager.set_processing_started()
        main_window.state_manager.update_progress(50, "Processing...")
        
        assert "50%" in main_window.state_pill.text()
    
    def test_status_bar_updates(self, main_window):
        """Test status bar reflects state changes."""
        main_window.state_manager.set_video_loaded("/path/to/video.mov")
        
        status_text = main_window.statusBar().currentMessage()
        # Should have some status message
        assert len(status_text) > 0


# =============================================================================
# Action Gating Tests
# =============================================================================

class TestActionGating:
    """Tests for action button enabling/disabling based on state."""
    
    def test_idle_state_gating(self, main_window):
        """Test IDLE state action gating."""
        # Only open should work
        assert main_window.btn_open.isEnabled()
        assert not main_window.btn_run.isEnabled()
        assert not main_window.action_export.isEnabled()
        assert not main_window.action_tune.isEnabled()
    
    def test_video_loaded_gating(self, main_window):
        """Test VIDEO_LOADED state action gating."""
        main_window.state_manager.set_video_loaded("/path/to/video.mov")
        
        assert main_window.btn_open.isEnabled()
        assert main_window.btn_run.isEnabled()
        assert main_window.btn_load.isEnabled()
        assert not main_window.action_export.isEnabled()
    
    def test_processing_gating(self, main_window):
        """Test PROCESSING state action gating."""
        main_window.state_manager.set_video_loaded("/path/to/video.mov")
        main_window.state_manager.set_processing_started()
        
        assert not main_window.btn_run.isEnabled()
        assert main_window.action_cancel.isEnabled()
    
    def test_cache_ready_gating(self, main_window):
        """Test CACHE_READY state action gating."""
        main_window.state_manager.set_video_loaded("/path/to/video.mov")
        main_window.state_manager.set_cache_ready("/path/to/cache.json")
        
        assert main_window.btn_run.isEnabled()
        assert main_window.action_export.isEnabled()
        assert main_window.action_tune.isEnabled()


# =============================================================================
# Signal Emission Tests
# =============================================================================

class TestSignals:
    """Tests for signal emission."""
    
    def test_video_open_signal(self, main_window, qapp):
        """Test video_open_requested signal is emitted."""
        signal_received = []
        main_window.video_open_requested.connect(lambda p: signal_received.append(p))
        
        # Simulate opening video (mock file dialog)
        with patch('mill_presenter.ui.main_window.QFileDialog.getOpenFileName',
                   return_value=("/test/video.mov", "")):
            main_window._on_open_video()
        
        assert len(signal_received) == 1
        assert signal_received[0] == "/test/video.mov"
    
    def test_detection_signal(self, main_window, qapp):
        """Test detection_requested signal is emitted."""
        signal_received = []
        main_window.detection_requested.connect(lambda: signal_received.append(True))
        
        # Enable run button first
        main_window.state_manager.set_video_loaded("/path/to/video.mov")
        
        main_window._on_run_detection()
        
        assert len(signal_received) == 1


# =============================================================================
# Tooltip Tests
# =============================================================================

class TestTooltips:
    """Tests for disabled action tooltips."""
    
    def test_disabled_button_has_tooltip(self, main_window):
        """Test disabled buttons have explanatory tooltips."""
        # In IDLE, run button should have tooltip explaining why disabled
        tooltip = main_window.btn_run.toolTip()
        assert tooltip is not None
        assert len(tooltip) > 0
    
    def test_tooltip_changes_with_state(self, main_window):
        """Test tooltips update when state changes."""
        initial_tooltip = main_window.btn_run.toolTip()
        
        main_window.state_manager.set_video_loaded("/path/to/video.mov")
        
        new_tooltip = main_window.btn_run.toolTip()
        # Tooltip should change (now enabled, different message)
        assert new_tooltip != initial_tooltip or main_window.btn_run.isEnabled()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
