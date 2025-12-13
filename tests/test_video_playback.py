"""
Test Suite: Video Loading and Playback

Tests video file loading, cache loading, and playback controls.
"""

import pytest
from pathlib import Path

from ui.state import AppState


class TestVideoLoading:
    """Test video file loading."""
    
    def test_load_video_changes_state(self, main_window, test_video_path, qtbot):
        """Loading video should change state to VIDEO_LOADED."""
        if not test_video_path:
            pytest.skip("Test video not available")
        
        main_window._load_video(test_video_path)
        qtbot.wait(200)
        
        assert main_window.state_manager.state in (
            AppState.VIDEO_LOADED, 
            AppState.CACHE_READY  # If auto-load cache found
        )
    
    def test_video_controller_opens(self, main_window, test_video_path, qtbot):
        """Video controller should open the file."""
        if not test_video_path:
            pytest.skip("Test video not available")
        
        main_window._load_video(test_video_path)
        qtbot.wait(200)
        
        assert main_window.video_controller.is_open
        assert main_window.video_controller.total_frames > 0
        assert main_window.video_controller.fps > 0
    
    def test_video_info_populated(self, main_window, test_video_path, qtbot):
        """Video info should be populated in state manager."""
        if not test_video_path:
            pytest.skip("Test video not available")
        
        main_window._load_video(test_video_path)
        qtbot.wait(200)
        
        video_info = main_window.state_manager.video
        assert video_info.is_loaded
        assert video_info.width > 0
        assert video_info.height > 0
        assert video_info.total_frames > 0


class TestCacheLoading:
    """Test detection cache loading."""
    
    def test_load_cache_changes_state(self, main_window, test_video_path, test_cache_path, qtbot):
        """Loading cache should change state to CACHE_READY."""
        if not test_video_path or not test_cache_path:
            pytest.skip("Test files not available")
        
        main_window._load_video(test_video_path)
        qtbot.wait(200)
        
        main_window._load_cache(test_cache_path)
        qtbot.wait(200)
        
        assert main_window.state_manager.state == AppState.CACHE_READY
    
    def test_detection_cache_loads(self, main_window, test_video_path, test_cache_path, qtbot):
        """Detection cache should load and contain data."""
        if not test_video_path or not test_cache_path:
            pytest.skip("Test files not available")
        
        main_window._load_video(test_video_path)
        main_window._load_cache(test_cache_path)
        qtbot.wait(200)
        
        assert main_window.detection_cache.is_loaded
        assert main_window.detection_cache.total_frames > 0
    
    def test_cache_has_detections(self, main_window, test_video_path, test_cache_path, qtbot):
        """Cache should have detections for frames."""
        if not test_video_path or not test_cache_path:
            pytest.skip("Test files not available")
        
        main_window._load_video(test_video_path)
        main_window._load_cache(test_cache_path)
        qtbot.wait(200)
        
        # Get detections for first frame
        detections = main_window.detection_cache.get_detections(0)
        assert isinstance(detections, list)
        # Should have some detections
        assert len(detections) > 0


class TestPlaybackControls:
    """Test playback control functions."""
    
    def test_play_pause_toggle(self, loaded_window, qtbot):
        """Play/pause should toggle correctly."""
        if not loaded_window.video_controller.is_open:
            pytest.skip("Video not loaded")
        
        # Initially paused
        assert not loaded_window.video_controller.is_playing
        
        # Start playing
        loaded_window.video_controller.play()
        qtbot.wait(100)
        assert loaded_window.video_controller.is_playing
        
        # Pause
        loaded_window.video_controller.pause()
        assert not loaded_window.video_controller.is_playing
    
    def test_step_forward(self, loaded_window, qtbot):
        """Step forward should advance frame."""
        if not loaded_window.video_controller.is_open:
            pytest.skip("Video not loaded")
        
        initial_frame = loaded_window.video_controller.current_frame
        loaded_window.video_controller.step_forward(1)
        qtbot.wait(50)
        
        assert loaded_window.video_controller.current_frame == initial_frame + 1
    
    def test_step_backward(self, loaded_window, qtbot):
        """Step backward should go back a frame."""
        if not loaded_window.video_controller.is_open:
            pytest.skip("Video not loaded")
        
        # Go to frame 10 first
        loaded_window.video_controller.seek(10)
        qtbot.wait(50)
        
        loaded_window.video_controller.step_backward(1)
        qtbot.wait(50)
        
        assert loaded_window.video_controller.current_frame == 9
    
    def test_seek_to_frame(self, loaded_window, qtbot):
        """Seek should jump to specified frame."""
        if not loaded_window.video_controller.is_open:
            pytest.skip("Video not loaded")
        
        target_frame = 50
        loaded_window.video_controller.seek(target_frame)
        qtbot.wait(50)
        
        assert loaded_window.video_controller.current_frame == target_frame
    
    def test_go_to_start(self, loaded_window, qtbot):
        """Go to start should seek to frame 0."""
        if not loaded_window.video_controller.is_open:
            pytest.skip("Video not loaded")
        
        # Go somewhere first
        loaded_window.video_controller.seek(100)
        qtbot.wait(50)
        
        loaded_window.video_controller.go_to_start()
        qtbot.wait(50)
        
        assert loaded_window.video_controller.current_frame == 0
    
    def test_go_to_end(self, loaded_window, qtbot):
        """Go to end should seek to last frame."""
        if not loaded_window.video_controller.is_open:
            pytest.skip("Video not loaded")
        
        loaded_window.video_controller.go_to_end()
        qtbot.wait(50)
        
        expected = loaded_window.video_controller.total_frames - 1
        assert loaded_window.video_controller.current_frame == expected
    
    def test_speed_change(self, loaded_window, qtbot):
        """Speed change should update playback speed."""
        if not loaded_window.video_controller.is_open:
            pytest.skip("Video not loaded")
        
        loaded_window.video_controller.set_speed(2.0)
        assert loaded_window.video_controller._speed == 2.0
        
        loaded_window.video_controller.set_speed(0.5)
        assert loaded_window.video_controller._speed == 0.5
    
    def test_loop_toggle(self, loaded_window, qtbot):
        """Loop toggle should update looping state."""
        if not loaded_window.video_controller.is_open:
            pytest.skip("Video not loaded")
        
        assert not loaded_window.video_controller._is_looping
        
        loaded_window.video_controller.set_looping(True)
        assert loaded_window.video_controller._is_looping
        
        loaded_window.video_controller.set_looping(False)
        assert not loaded_window.video_controller._is_looping
