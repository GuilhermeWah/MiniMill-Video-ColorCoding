import pytest
from unittest.mock import MagicMock, patch, call
import numpy as np
from mill_presenter.core.exporter import VideoExporter

@pytest.fixture
def mock_frame_loader():
    loader = MagicMock()
    loader.width = 1920
    loader.height = 1080
    loader.fps = 30.0
    loader.total_frames = 10
    
    # Mock iter_frames to yield 2 frames
    frame1 = np.zeros((1080, 1920, 3), dtype=np.uint8)
    frame2 = np.zeros((1080, 1920, 3), dtype=np.uint8)
    loader.iter_frames.return_value = iter([(0, frame1), (1, frame2)])
    return loader

@pytest.fixture
def mock_results_cache():
    cache = MagicMock()
    cache.get_frame.return_value = MagicMock() # Return some detections
    return cache

@patch('mill_presenter.core.exporter.cv2.VideoWriter')
@patch('mill_presenter.core.exporter.OverlayRenderer')
def test_export_process(MockOverlayRenderer, MockVideoWriter, mock_frame_loader, mock_results_cache):
    config = {'overlay': {'colors': {}}}
    exporter = VideoExporter(config, mock_frame_loader, mock_results_cache)
    
    mock_writer_instance = MockVideoWriter.return_value
    mock_writer_instance.isOpened.return_value = True
    
    mock_renderer_instance = MockOverlayRenderer.return_value
    
    visible_classes = {4, 6, 8, 10}
    progress_callback = MagicMock()
    
    exporter.export("output.mp4", visible_classes, progress_callback)
    
    # Verify VideoWriter initialized correctly
    MockVideoWriter.assert_called_once()
    args, _ = MockVideoWriter.call_args
    assert args[0] == "output.mp4"
    assert args[2] == 30.0 # FPS
    assert args[3] == (1920, 1080) # Size
    
    # Verify frames were processed
    assert mock_frame_loader.iter_frames.called
    assert mock_results_cache.get_frame.call_count == 2
    
    # Verify renderer was called
    assert mock_renderer_instance.draw.call_count == 2
    
    # Verify frames were written
    assert mock_writer_instance.write.call_count == 2
    
    # Verify progress callback
    assert progress_callback.call_count >= 2
    assert call(0, 10) in progress_callback.mock_calls
    assert call(1, 10) in progress_callback.mock_calls
    
    # Verify writer released
    mock_writer_instance.release.assert_called_once()

@patch('mill_presenter.core.exporter.cv2.VideoWriter')
def test_export_failure(MockVideoWriter, mock_frame_loader, mock_results_cache):
    config = {}
    exporter = VideoExporter(config, mock_frame_loader, mock_results_cache)
    
    mock_writer_instance = MockVideoWriter.return_value
    mock_writer_instance.isOpened.return_value = False # Simulate failure
    
    with pytest.raises(RuntimeError, match="Failed to open video writer"):
        exporter.export("output.mp4", set())

@patch('mill_presenter.core.exporter.cv2.imread')
@patch('mill_presenter.core.exporter.os.path.exists')
@patch('mill_presenter.core.exporter.cv2.VideoWriter')
@patch('mill_presenter.core.exporter.OverlayRenderer')
def test_export_with_roi(MockOverlayRenderer, MockVideoWriter, mock_exists, mock_imread, mock_frame_loader, mock_results_cache):
    config = {'paths': {'detections_dir': '.'}, 'overlay': {'colors': {}}}
    exporter = VideoExporter(config, mock_frame_loader, mock_results_cache)
    
    # Mock ROI mask existence
    mock_exists.return_value = True
    
    # Mock ROI mask (1080x1920)
    # Create a mask where left half is Valid (255), right half is Ignore (0)
    roi_mask = np.zeros((1080, 1920), dtype=np.uint8)
    roi_mask[:, :960] = 255
    mock_imread.return_value = roi_mask
    
    # Mock detections
    # Ball 1: (100, 100) -> Valid
    # Ball 2: (1000, 100) -> Ignore
    ball1 = MagicMock()
    ball1.x = 100
    ball1.y = 100
    ball2 = MagicMock()
    ball2.x = 1000
    ball2.y = 100
    
    detections = MagicMock()
    detections.balls = [ball1, ball2]
    mock_results_cache.get_frame.return_value = detections
    
    mock_writer_instance = MockVideoWriter.return_value
    mock_writer_instance.isOpened.return_value = True
    
    mock_renderer_instance = MockOverlayRenderer.return_value
    
    exporter.export("output.mp4", {4, 6, 8, 10})
    
    # Verify renderer called with filtered detections
    assert mock_renderer_instance.draw.call_count == 2
    
    # Check the arguments passed to draw
    # args[0] is painter, args[1] is detections
    args, _ = mock_renderer_instance.draw.call_args
    passed_detections = args[1]
    
    # Should only contain ball1
    assert len(passed_detections.balls) == 1
    assert passed_detections.balls[0] == ball1

