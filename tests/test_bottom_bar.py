"""
Test Suite: Bottom Bar and Transport Controls

Tests timeline, transport buttons, and playback UI elements.
"""

import pytest
from PySide6.QtCore import Qt


class TestBottomBarStructure:
    """Test bottom bar widget structure."""
    
    def test_bottom_bar_exists(self, main_window):
        """Bottom bar should exist."""
        assert main_window.bottom_bar is not None
    
    def test_transport_buttons_exist(self, main_window):
        """Transport buttons should exist."""
        bb = main_window.bottom_bar
        
        assert bb.btn_play is not None
        assert bb.btn_step_back is not None
        assert bb.btn_step_fwd is not None
        assert bb.btn_loop is not None
    
    def test_timeline_slider_exists(self, main_window):
        """Timeline slider should exist."""
        assert main_window.bottom_bar.timeline is not None
    
    def test_time_display_exists(self, main_window):
        """Time display should exist."""
        assert main_window.bottom_bar.time_display is not None
    
    def test_speed_selector_exists(self, main_window):
        """Speed selector should exist."""
        assert main_window.bottom_bar.speed_selector is not None


class TestBottomBarInteraction:
    """Test bottom bar interactions."""
    
    def test_play_button_emits_signal(self, loaded_window, qtbot):
        """Play button should emit play_toggled signal when video is loaded."""
        if not loaded_window.video_controller.is_open:
            pytest.skip("Video not loaded")
        
        with qtbot.waitSignal(loaded_window.bottom_bar.play_toggled, timeout=1000):
            qtbot.mouseClick(loaded_window.bottom_bar.btn_play, Qt.MouseButton.LeftButton)
    
    def test_timeline_emits_frame_changed(self, loaded_window, qtbot):
        """Timeline slider should emit frame_changed signal."""
        if not loaded_window.video_controller.is_open:
            pytest.skip("Video not loaded")
        
        with qtbot.waitSignal(loaded_window.bottom_bar.frame_changed, timeout=1000):
            loaded_window.bottom_bar.timeline.setValue(100)
    
    def test_speed_selector_emits_signal(self, main_window, qtbot):
        """Speed selector should emit speed_changed signal."""
        with qtbot.waitSignal(main_window.bottom_bar.speed_changed, timeout=1000):
            main_window.bottom_bar.speed_selector.setCurrentIndex(0)  # 0.25x
    
    def test_loop_button_toggles(self, loaded_window, qtbot):
        """Loop button should toggle and emit signal when video is loaded."""
        if not loaded_window.video_controller.is_open:
            pytest.skip("Video not loaded")
        
        initial_state = loaded_window.bottom_bar.btn_loop.isChecked()
        
        with qtbot.waitSignal(loaded_window.bottom_bar.loop_toggled, timeout=1000):
            qtbot.mouseClick(loaded_window.bottom_bar.btn_loop, Qt.MouseButton.LeftButton)
        
        assert loaded_window.bottom_bar.btn_loop.isChecked() != initial_state


class TestBottomBarState:
    """Test bottom bar state updates."""
    
    def test_set_video_info_updates_timeline(self, main_window, qtbot):
        """set_video_info should configure timeline range."""
        main_window.bottom_bar.set_video_info(total_frames=1000, fps=30.0)
        
        assert main_window.bottom_bar.timeline.maximum() == 999
    
    def test_set_current_frame_updates_slider(self, main_window, qtbot):
        """set_current_frame should update slider position."""
        main_window.bottom_bar.set_video_info(total_frames=1000, fps=30.0)
        main_window.bottom_bar.set_current_frame(500)
        
        assert main_window.bottom_bar.timeline.value() == 500
    
    def test_set_playing_updates_button(self, main_window, qtbot):
        """set_playing should update play button icon."""
        # Set playing
        main_window.bottom_bar.set_playing(True)
        # Button text should indicate pause (⏸)
        assert "⏸" in main_window.bottom_bar.btn_play.text()
        
        # Set paused
        main_window.bottom_bar.set_playing(False)
        # Button text should indicate play (▶)
        assert "▶" in main_window.bottom_bar.btn_play.text()


class TestTimeDisplay:
    """Test time display widget."""
    
    def test_time_format(self, main_window):
        """Time display should show MM:SS format."""
        time_display = main_window.bottom_bar.time_display
        
        time_display.set_time(65, 3600)  # 1:05 / 60:00
        
        text = time_display.text()
        assert "/" in text
        # Should contain minutes:seconds format
        assert "01:05" in text or "1:05" in text
