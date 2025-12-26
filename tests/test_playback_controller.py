# Tests for PlaybackController (TESTING_VER Style)

"""
Unit tests for the iterator-based PlaybackController.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from PySide6.QtCore import QTimer


class MockFrameLoader:
    """Mock FrameLoader for testing."""
    
    def __init__(self, fps=30.0, frame_count=100):
        self.fps = fps
        self.frame_count = frame_count
        self._current_frame = 0
    
    def iter_frames(self, start_frame=0):
        """Yield (frame_index, frame_bgr) tuples."""
        import numpy as np
        for i in range(start_frame, self.frame_count):
            # Create a dummy 100x100 BGR frame
            frame = np.zeros((100, 100, 3), dtype=np.uint8)
            frame[:, :, 0] = i % 256  # Blue channel varies by frame
            yield i, frame


class MockVideoWidget:
    """Mock VideoWidget for testing."""
    
    def __init__(self):
        self.frames_set = []
        self.overlays_set = []
    
    def set_frame(self, frame_bgr):
        self.frames_set.append(frame_bgr)
    
    def set_overlays(self, detections):
        self.overlays_set.append(detections)


class MockOverlayWidget:
    """Mock OverlayWidget for testing."""
    
    def __init__(self):
        self._frame_lookup = {}
    
    def set_detections(self, frame_index, detections):
        self._frame_lookup[frame_index] = detections


class TestPlaybackController:
    """Tests for PlaybackController."""
    
    @pytest.fixture
    def controller(self):
        """Create a PlaybackController with mock components."""
        from mill_presenter.ui.playback_controller import PlaybackController
        
        loader = MockFrameLoader(fps=30.0, frame_count=100)
        widget = MockVideoWidget()
        overlay = MockOverlayWidget()
        
        # Add some test detections
        overlay._frame_lookup[0] = [{"x": 50, "y": 50, "r_px": 10, "cls": 6, "conf": 0.9}]
        overlay._frame_lookup[5] = [{"x": 60, "y": 60, "r_px": 12, "cls": 8, "conf": 0.8}]
        
        ctrl = PlaybackController(
            frame_loader=loader,
            video_widget=widget,
            overlay_widget=overlay,
        )
        
        return ctrl, loader, widget, overlay
    
    def test_initial_state(self, controller):
        """Test initial controller state."""
        ctrl, _, _, _ = controller
        
        assert ctrl.is_playing == False
        assert ctrl.current_frame_index == 0
        assert ctrl.fps == 30.0
        assert ctrl.frame_count == 100
        assert ctrl.get_speed() == 1.0
    
    def test_properties(self, controller):
        """Test property accessors."""
        ctrl, _, _, _ = controller
        
        assert ctrl.duration == 100 / 30.0  # frame_count / fps
        assert ctrl.total_frames == 100
        assert ctrl.playback_speed == 1.0
    
    def test_set_speed(self, controller):
        """Test speed setting."""
        ctrl, _, _, _ = controller
        
        ctrl.set_speed(0.5)
        assert ctrl.get_speed() == 0.5
        
        ctrl.set_playback_speed(0.25)
        assert ctrl.playback_speed == 0.25
        
        # Speed is clamped (if negative, raises error)
        with pytest.raises(ValueError):
            ctrl.set_speed(-1.0)
    
    def test_compute_interval(self, controller):
        """Test timer interval calculation."""
        ctrl, _, _, _ = controller
        
        # At 30fps, 1x speed: interval = 1000/30/1 = 33ms
        ctrl.set_speed(1.0)
        interval = ctrl._compute_interval_ms()
        assert interval == 33
        
        # At 30fps, 0.5x speed: interval = 1000/30/0.5 = 67ms
        ctrl.set_speed(0.5)
        interval = ctrl._compute_interval_ms()
        assert interval == 67
    
    def test_seek(self, controller):
        """Test seek functionality."""
        ctrl, loader, widget, overlay = controller
        
        # Seek to frame 10
        ctrl.seek(10)
        assert ctrl.current_frame_index == 10
        assert len(widget.frames_set) == 1  # One frame displayed
        
        # Seek to frame 0 (has detections)
        ctrl.seek(0)
        assert ctrl.current_frame_index == 0
        assert len(widget.overlays_set) >= 1  # Overlays were set
    
    def test_seek_clamping(self, controller):
        """Test seek clamping to valid range."""
        ctrl, _, _, _ = controller
        
        # Seek beyond end
        ctrl.seek(500)
        assert ctrl.current_frame_index == 99  # Clamped to last frame
        
        # Seek before start
        ctrl.seek(-10)
        assert ctrl.current_frame_index == 0  # Clamped to first frame
    
    def test_step_forward(self, controller):
        """Test step forward."""
        ctrl, _, _, _ = controller
        
        ctrl.seek(5)
        ctrl.step_forward()
        assert ctrl.current_frame_index == 6
    
    def test_step_backward(self, controller):
        """Test step backward."""
        ctrl, _, _, _ = controller
        
        ctrl.seek(5)
        ctrl.step_backward()
        assert ctrl.current_frame_index == 4
    
    def test_seek_to_position(self, controller):
        """Test seeking by normalized position."""
        ctrl, _, _, _ = controller
        
        ctrl.seek_to_position(0.5)  # Middle of video
        # 0.5 * (100-1) = 49.5 -> 49
        assert ctrl.current_frame_index == 49
        
        ctrl.seek_to_position(0.0)
        assert ctrl.current_frame_index == 0
        
        ctrl.seek_to_position(1.0)
        assert ctrl.current_frame_index == 99
    
    def test_get_current_time(self, controller):
        """Test current time calculation."""
        ctrl, _, _, _ = controller
        
        ctrl.seek(30)  # 30 frames at 30fps = 1 second
        assert ctrl.get_current_time() == pytest.approx(1.0)
        
        ctrl.seek(60)  # 60 frames at 30fps = 2 seconds
        assert ctrl.get_current_time() == pytest.approx(2.0)
    
    def test_get_normalized_position(self, controller):
        """Test normalized position calculation."""
        ctrl, _, _, _ = controller
        
        ctrl.seek(0)
        assert ctrl.get_normalized_position() == 0.0
        
        ctrl.seek(99)
        assert ctrl.get_normalized_position() == 1.0
        
        ctrl.seek(49)  # Middle-ish
        assert ctrl.get_normalized_position() == pytest.approx(49/99)
    
    def test_process_next_frame(self, controller):
        """Test processing next frame."""
        ctrl, loader, widget, overlay = controller
        
        # Process a frame
        ctrl.process_next_frame()
        assert ctrl.current_frame_index == 0
        assert len(widget.frames_set) == 1
        
        # Process another
        ctrl.process_next_frame()
        assert ctrl.current_frame_index == 1
        assert len(widget.frames_set) == 2
    
    def test_process_next_frame_end_of_video(self, controller):
        """Test processing at end of video."""
        ctrl, _, _, _ = controller
        
        # Seek to last frame
        ctrl.seek(99)
        assert ctrl.current_frame_index == 99
        
        # Next process should hit StopIteration and pause
        ctrl._frame_iter = None  # Reset iterator
        ctrl.process_next_frame()  # This tries to decode frame 100 which doesn't exist
        
        # Should pause after reaching end
        assert ctrl.is_playing == False
    
    def test_toggle_play_pause(self, controller):
        """Test play/pause toggle."""
        ctrl, _, _, _ = controller
        
        # Initially not playing
        assert ctrl.is_playing == False
        
        # Toggle to play
        ctrl.toggle_play_pause()
        assert ctrl.is_playing == True
        
        # Toggle to pause  
        ctrl.toggle_play_pause()
        assert ctrl.is_playing == False
    
    def test_stop(self, controller):
        """Test stop functionality."""
        ctrl, _, _, _ = controller
        
        # Play and seek forward
        ctrl.play()
        ctrl.seek(50)
        assert ctrl.current_frame_index == 50
        
        # Stop should pause and return to start
        ctrl.stop()
        assert ctrl.is_playing == False
        assert ctrl.current_frame_index == 0
    
    def test_position_changed_signal(self, controller):
        """Test position_changed signal emission."""
        ctrl, _, _, _ = controller
        
        # Track signal emissions
        emissions = []
        ctrl.position_changed.connect(lambda *args: emissions.append(args))
        
        # Seek should emit position_changed
        ctrl.seek(10)
        assert len(emissions) == 1
        frame, total, time_s, duration_s = emissions[0]
        assert frame == 10
        assert total == 100
    
    def test_frame_changed_signal(self, controller):
        """Test frame_changed signal emission."""
        ctrl, _, _, _ = controller
        
        # Track signal emissions
        emissions = []
        ctrl.frame_changed.connect(lambda frame: emissions.append(frame))
        
        # Seek should emit frame_changed
        ctrl.seek(15)
        assert len(emissions) == 1
        assert emissions[0] == 15
    
    def test_no_components(self):
        """Test controller without components."""
        from mill_presenter.ui.playback_controller import PlaybackController
        
        ctrl = PlaybackController()
        
        # Should not crash with no components
        ctrl.play()  # No-op
        ctrl.seek(10)  # No-op
        ctrl.process_next_frame()  # Should pause
        
        assert ctrl.frame_count == 0
        assert ctrl.fps == 30.0  # Default
    
    def test_set_components(self):
        """Test setting components after initialization."""
        from mill_presenter.ui.playback_controller import PlaybackController
        
        ctrl = PlaybackController()
        assert ctrl.frame_count == 0
        
        # Set components
        loader = MockFrameLoader(fps=60.0, frame_count=200)
        widget = MockVideoWidget()
        
        ctrl.set_components(frame_loader=loader, video_widget=widget)
        
        assert ctrl.fps == 60.0
        assert ctrl.frame_count == 200


class TestPlaybackControllerHighFPS:
    """Tests for high-FPS video playback."""
    
    @pytest.fixture
    def controller_high_fps(self):
        """Create controller with high-FPS video (like 239.7 fps)."""
        from mill_presenter.ui.playback_controller import PlaybackController
        
        loader = MockFrameLoader(fps=239.7, frame_count=7191)  # ~30 seconds
        widget = MockVideoWidget()
        overlay = MockOverlayWidget()
        
        ctrl = PlaybackController(
            frame_loader=loader,
            video_widget=widget,
            overlay_widget=overlay,
        )
        
        return ctrl
    
    def test_high_fps_interval(self, controller_high_fps):
        """Test timer interval for high-FPS video."""
        ctrl = controller_high_fps
        
        # At 239.7fps, 1x speed: interval = 1000/239.7/1 ≈ 4ms
        ctrl.set_speed(1.0)
        interval = ctrl._compute_interval_ms()
        assert interval == 4  # 1000/239.7 ≈ 4.17 -> 4
        
        # At 0.5x speed: interval = 1000/239.7/0.5 ≈ 8ms
        ctrl.set_speed(0.5)
        interval = ctrl._compute_interval_ms()
        assert interval == 8
        
        # At 0.15x speed: interval = 1000/239.7/0.15 ≈ 28ms
        ctrl.set_speed(0.15)
        interval = ctrl._compute_interval_ms()
        assert interval == 28
    
    def test_high_fps_duration(self, controller_high_fps):
        """Test duration calculation for high-FPS video."""
        ctrl = controller_high_fps
        
        # 7191 frames at 239.7 fps ≈ 30 seconds
        assert ctrl.duration == pytest.approx(30.0, rel=0.01)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
