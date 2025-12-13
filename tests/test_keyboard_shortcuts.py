"""
Test Suite: Keyboard Shortcuts

Tests all keyboard shortcuts work correctly.
"""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtTest import QTest


class TestPlaybackShortcuts:
    """Test playback keyboard shortcuts."""
    
    def test_space_toggles_play(self, loaded_window, qtbot):
        """Space should toggle play/pause."""
        if not loaded_window.video_controller.is_open:
            pytest.skip("Video not loaded")
        
        # Focus the window
        loaded_window.activateWindow()
        loaded_window.viewport.setFocus()
        qtbot.wait(100)
        
        initial_playing = loaded_window.video_controller.is_playing
        
        # Press space
        QTest.keyClick(loaded_window, Qt.Key.Key_Space)
        qtbot.wait(100)
        
        assert loaded_window.video_controller.is_playing != initial_playing
    
    def test_right_arrow_steps_forward(self, loaded_window, qtbot):
        """Right arrow should step forward one frame."""
        if not loaded_window.video_controller.is_open:
            pytest.skip("Video not loaded")
        
        loaded_window.video_controller.seek(10)
        qtbot.wait(50)
        
        loaded_window.activateWindow()
        QTest.keyClick(loaded_window, Qt.Key.Key_Right)
        qtbot.wait(100)
        
        assert loaded_window.video_controller.current_frame == 11
    
    def test_left_arrow_steps_backward(self, loaded_window, qtbot):
        """Left arrow should step backward one frame."""
        if not loaded_window.video_controller.is_open:
            pytest.skip("Video not loaded")
        
        loaded_window.video_controller.seek(10)
        qtbot.wait(50)
        
        loaded_window.activateWindow()
        QTest.keyClick(loaded_window, Qt.Key.Key_Left)
        qtbot.wait(100)
        
        assert loaded_window.video_controller.current_frame == 9
    
    def test_shift_right_jumps_forward(self, loaded_window, qtbot):
        """Shift+Right should jump 10 frames forward."""
        if not loaded_window.video_controller.is_open:
            pytest.skip("Video not loaded")
        
        loaded_window.video_controller.seek(10)
        qtbot.wait(50)
        
        loaded_window.activateWindow()
        QTest.keyClick(loaded_window, Qt.Key.Key_Right, Qt.KeyboardModifier.ShiftModifier)
        qtbot.wait(100)
        
        assert loaded_window.video_controller.current_frame == 20
    
    def test_shift_left_jumps_backward(self, loaded_window, qtbot):
        """Shift+Left should jump 10 frames backward."""
        if not loaded_window.video_controller.is_open:
            pytest.skip("Video not loaded")
        
        loaded_window.video_controller.seek(50)
        qtbot.wait(50)
        
        loaded_window.activateWindow()
        QTest.keyClick(loaded_window, Qt.Key.Key_Left, Qt.KeyboardModifier.ShiftModifier)
        qtbot.wait(100)
        
        assert loaded_window.video_controller.current_frame == 40
    
    def test_home_goes_to_start(self, loaded_window, qtbot):
        """Home should go to first frame."""
        if not loaded_window.video_controller.is_open:
            pytest.skip("Video not loaded")
        
        loaded_window.video_controller.seek(100)
        qtbot.wait(50)
        
        loaded_window.activateWindow()
        QTest.keyClick(loaded_window, Qt.Key.Key_Home)
        qtbot.wait(100)
        
        assert loaded_window.video_controller.current_frame == 0
    
    def test_end_goes_to_end(self, loaded_window, qtbot):
        """End should go to last frame."""
        if not loaded_window.video_controller.is_open:
            pytest.skip("Video not loaded")
        
        loaded_window.activateWindow()
        QTest.keyClick(loaded_window, Qt.Key.Key_End)
        qtbot.wait(100)
        
        expected = loaded_window.video_controller.total_frames - 1
        assert loaded_window.video_controller.current_frame == expected
    
    def test_l_toggles_loop(self, loaded_window, qtbot):
        """L should toggle loop mode."""
        if not loaded_window.video_controller.is_open:
            pytest.skip("Video not loaded")
        
        initial_looping = loaded_window.video_controller._is_looping
        
        loaded_window.activateWindow()
        QTest.keyClick(loaded_window, Qt.Key.Key_L)
        qtbot.wait(100)
        
        assert loaded_window.video_controller._is_looping != initial_looping


class TestViewShortcuts:
    """Test view keyboard shortcuts."""
    
    def test_f11_toggles_fullscreen(self, main_window, qtbot):
        """F11 should toggle fullscreen."""
        initial_fullscreen = main_window.isFullScreen()
        
        main_window.activateWindow()
        QTest.keyClick(main_window, Qt.Key.Key_F11)
        qtbot.wait(200)
        
        assert main_window.isFullScreen() != initial_fullscreen
        
        # Toggle back
        QTest.keyClick(main_window, Qt.Key.Key_F11)
        qtbot.wait(200)
    
    def test_ctrl_h_toggles_left_panel(self, main_window, qtbot):
        """Ctrl+H should toggle left panel."""
        initial_visible = main_window.left_panel.isVisible()
        
        main_window.activateWindow()
        QTest.keyClick(main_window, Qt.Key.Key_H, Qt.KeyboardModifier.ControlModifier)
        qtbot.wait(100)
        
        assert main_window.left_panel.isVisible() != initial_visible
