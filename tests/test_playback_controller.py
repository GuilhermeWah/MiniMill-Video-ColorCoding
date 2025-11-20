import numpy as np
import pytest
from unittest.mock import MagicMock

from mill_presenter.core.models import Ball, FrameDetections


@pytest.fixture
def sample_frame():
    # Simple 2x2 blue-ish frame in BGR order
    return np.zeros((2, 2, 3), dtype=np.uint8)


@pytest.fixture
def sample_detections():
    ball = Ball(x=1, y=1, r_px=2.0, diameter_mm=4.0, cls=4, conf=0.9)
    return FrameDetections(frame_id=0, timestamp=0.0, balls=[ball])


def test_playback_controller_play_starts_timer(monkeypatch, sample_frame, sample_detections):
    from mill_presenter.ui import playback_controller

    mock_timer = MagicMock()
    monkeypatch.setattr(playback_controller, "QTimer", lambda parent=None: mock_timer)

    frame_loader = MagicMock()
    frame_loader.fps = 30
    frame_loader.iter_frames.return_value = iter([(0, sample_frame)])

    cache = MagicMock()
    cache.get_frame.return_value = sample_detections

    video_widget = MagicMock()

    controller = playback_controller.PlaybackController(frame_loader, cache, video_widget)
    controller.play()

    mock_timer.start.assert_called_once()
    assert controller.is_playing is True


def test_playback_controller_process_frame_updates_widget(monkeypatch, sample_frame, sample_detections):
    from mill_presenter.ui import playback_controller

    mock_timer = MagicMock()
    monkeypatch.setattr(playback_controller, "QTimer", lambda parent=None: mock_timer)

    frame_loader = MagicMock()
    frame_loader.fps = 60
    frame_loader.iter_frames.return_value = iter([(0, sample_frame), (1, sample_frame)])

    cache = MagicMock()
    cache.get_frame.return_value = sample_detections

    video_widget = MagicMock()

    controller = playback_controller.PlaybackController(frame_loader, cache, video_widget)
    controller.play()

    controller.process_next_frame()

    video_widget.set_frame.assert_called_once()
    image_arg, detections_arg = video_widget.set_frame.call_args[0]
    assert detections_arg == sample_detections
    assert controller.current_frame_index == 0
    assert image_arg.width() == 2
    assert image_arg.height() == 2


def test_playback_controller_handles_end_of_stream(monkeypatch, sample_frame):
    from mill_presenter.ui import playback_controller

    mock_timer = MagicMock()
    monkeypatch.setattr(playback_controller, "QTimer", lambda parent=None: mock_timer)

    frame_loader = MagicMock()
    frame_loader.fps = 60
    frame_loader.iter_frames.return_value = iter([(0, sample_frame)])

    cache = MagicMock()
    cache.get_frame.return_value = None

    video_widget = MagicMock()

    controller = playback_controller.PlaybackController(frame_loader, cache, video_widget)
    controller.play()

    controller.process_next_frame()
    controller.process_next_frame()  # triggers StopIteration

    mock_timer.stop.assert_called_once()
    assert controller.is_playing is False


def test_playback_controller_seek(monkeypatch, sample_frame, sample_detections):
    from mill_presenter.ui import playback_controller

    mock_timer = MagicMock()
    monkeypatch.setattr(playback_controller, "QTimer", lambda parent=None: mock_timer)

    frame_loader = MagicMock()
    frame_loader.fps = 30
    # Mock iter_frames to return a generator that starts from the requested frame
    def mock_iter_frames(start_frame=0):
        return iter([(start_frame, sample_frame)])
    frame_loader.iter_frames.side_effect = mock_iter_frames

    cache = MagicMock()
    cache.get_frame.return_value = sample_detections

    video_widget = MagicMock()

    controller = playback_controller.PlaybackController(frame_loader, cache, video_widget)
    
    # Seek to frame 10
    controller.seek(10)
    
    # Verify internal state updated
    assert controller.current_frame_index == 10
    assert controller._next_frame_to_decode == 11
    
    # Verify widget updated immediately
    video_widget.set_frame.assert_called_once()
    
    # Verify frame loader was called with correct start frame
    frame_loader.iter_frames.assert_called_with(start_frame=10)