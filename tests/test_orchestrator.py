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
    
    return loader, processor, cache

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
