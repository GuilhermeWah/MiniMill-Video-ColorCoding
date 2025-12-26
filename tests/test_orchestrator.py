import pytest
from unittest.mock import MagicMock, call, ANY
import numpy as np
from mill_presenter.core.models import Ball, FrameDetections
from mill_presenter.core.orchestrator import ProcessorOrchestrator

# ==================================================================================
# TEST SUITE: Processor Orchestrator
# ==================================================================================
# Purpose:
#   Verify the "Manager" of the pipeline. The Orchestrator doesn't do vision itself;
#   it coordinates the Loader, Processor, and Cache.
#
# Criteria for Success:
#   1. Iterates through ALL frames from the loader.
#   2. Passes the ROI mask to the processor.
#   3. Saves the processor's results to the cache.
#   4. Reports progress correctly (0% -> 100%).
#   5. Handles cancellation (stops early if requested).
# ==================================================================================

@pytest.fixture
def mock_components():
    """Creates mocks for Loader, Processor, and Cache."""
    loader = MagicMock()
    processor = MagicMock()
    cache = MagicMock()
    
    # Setup Loader to yield 10 dummy frames
    # iter_frames yields (frame_index, image)
    dummy_frames = []
    for i in range(10):
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        dummy_frames.append((i, img))
    
    loader.iter_frames.return_value = dummy_frames
    loader.total_frames = 10
    loader.fps = 30.0
    
    # Setup Processor to return a dummy detection
    dummy_ball = Ball(50, 50, 10, 20, 10, 0.9)
    processor.process_frame.return_value = [dummy_ball]

    # Default processor config for orchestrator (tracking off unless overridden)
    processor.config = {}
    
    return loader, processor, cache


def test_orchestrator_tracking_assigns_stable_ids(mock_components):
    """Milestone: Tracking - verify detection-time tracking assigns stable IDs."""
    loader, processor, cache = mock_components

    # Enable tracking and provide thresholds (keep test explicit)
    processor.config = {
        "tracking": {
            "enabled": True,
            "iou_threshold": 0.1,
            "max_center_distance_px": 50.0,
            "max_lost_frames": 2,
        }
    }

    # Return a *new* Ball object each frame so track_id assignment is per-frame
    def make_ball(_frame, roi_mask=None):
        return [Ball(x=50, y=50, r_px=10, diameter_mm=10, cls=10, conf=0.9)]

    processor.process_frame.side_effect = make_ball

    orchestrator = ProcessorOrchestrator(loader, processor, cache)
    orchestrator.run()

    # Verify cache.save_frame was called and balls have a stable track_id
    saved = [call_args[0][0] for call_args in cache.save_frame.call_args_list]
    assert len(saved) == 10

    track_ids = [frame.balls[0].track_id for frame in saved if frame.balls]
    assert len(track_ids) == 10
    assert all(tid is not None for tid in track_ids)
    assert len(set(track_ids)) == 1, "Expected a single stable track_id across frames"

def test_orchestrator_full_run(mock_components):
    """
    Milestone 2: Orchestration - Verify a complete successful run.
    """
    loader, processor, cache = mock_components
    
    # Create Orchestrator
    orchestrator = ProcessorOrchestrator(loader, processor, cache)
    
    # Run
    orchestrator.run()
    
    # Verification
    # 1. Did we process all 10 frames?
    assert processor.process_frame.call_count == 10
    
    # 2. Did we save 10 times?
    assert cache.save_frame.call_count == 10
    
    # 3. Check the data passed to save_frame
    # The last call should be for frame_id=9
    last_call_args = cache.save_frame.call_args[0][0]
    assert isinstance(last_call_args, FrameDetections)
    assert last_call_args.frame_id == 9
    assert len(last_call_args.balls) == 1

def test_orchestrator_roi_mask(mock_components):
    """
    Milestone 2: Orchestration - Verify ROI mask is passed down.
    """
    loader, processor, cache = mock_components
    
    # Create a dummy mask
    roi_mask = np.ones((100, 100), dtype=np.uint8)
    
    orchestrator = ProcessorOrchestrator(loader, processor, cache)
    orchestrator.set_roi_mask(roi_mask)
    
    orchestrator.run()
    
    # Verify processor received the mask
    # process_frame(frame, roi_mask=...)
    processor.process_frame.assert_called_with(ANY, roi_mask=roi_mask)

def test_orchestrator_cancellation(mock_components):
    """
    Milestone 2: Orchestration - Verify early stopping.
    """
    loader, processor, cache = mock_components
    
    orchestrator = ProcessorOrchestrator(loader, processor, cache)
    
    # Define a callback that cancels after 3 frames
    # We'll simulate this by having the progress callback return True (cancel)
    # or by setting a flag. Let's assume the orchestrator checks a flag or callback.
    
    # Let's assume run() takes a progress_callback that can return False to stop
    # Or we set a flag on the orchestrator.
    # Design Decision: Orchestrator.cancel() method is cleaner for UI.
    
    # We'll run the orchestrator in a way that we cancel it during execution.
    # Since this is synchronous, we need to simulate the check.
    # We can mock the progress callback to call cancel()
    
    def stop_after_3(progress):
        if progress >= 30.0: # 3 frames out of 10 = 30%
            orchestrator.cancel()
            
    orchestrator.run(progress_callback=stop_after_3)
    
    # Should have processed roughly 3 or 4 frames, definitely not 10
    assert processor.process_frame.call_count < 10
    assert cache.save_frame.call_count < 10
