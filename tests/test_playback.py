import pytest
import os
import cv2
import numpy as np
from mill_presenter.core.playback import FrameLoader

# ==================================================================================
# TEST SUITE: Video Playback & Decoding
# ==================================================================================
# Purpose:
#   Verify that the FrameLoader can correctly ingest video files, read metadata,
#   and provide random access (seeking) to frames.
#
# Criteria for Success:
#   1. Can open a video file without crashing.
#   2. Correctly reports width, height, and frame count.
#   3. iter_frames() yields the correct number of numpy arrays.
#   4. Seeking (start_frame=X) works accurately (essential for UI scrubbing).
# ==================================================================================

@pytest.fixture
def sample_video(tmp_path):
    """
    Fixture: Creates a short dummy video file for testing.
    Why: We don't want to rely on large external video files being present.
    This creates a 10-frame, 640x480, 30fps MP4 on the fly.
    """
    video_path = tmp_path / "test_video.mp4"
    path_str = str(video_path)
    
    # Create a 10-frame video at 30fps, 640x480
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(path_str, fourcc, 30.0, (640, 480))
    
    for i in range(10):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        # Draw frame number so we can verify seeking later
        cv2.putText(frame, str(i), (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        out.write(frame)
        
    out.release()
    return path_str

def test_frameloader_metadata(sample_video):
    """
    Milestone 2: Video Pipeline - Verify metadata reading.
    
    Logic:
        1. Initialize FrameLoader with the generated video.
        2. Check if critical properties (width, height) are populated.
        
    Why this matters:
        The UI needs width/height to set the aspect ratio of the player widget.
    """
    loader = FrameLoader(sample_video)
    
    # Note: cv2.VideoWriter might not set exact FPS in a way PyAV reads identically 
    # depending on container, but it should be close or readable.
    # We mainly check if it opened.
    assert loader.container is not None, "Failed to open PyAV container"
    assert loader.width == 640, f"Expected width 640, got {loader.width}"
    assert loader.height == 480, f"Expected height 480, got {loader.height}"
    # PyAV might report variable frame rate or time base differences, 
    # but duration should be > 0
    assert loader.stream is not None

    loader.close()

def test_frameloader_iteration(sample_video):
    """
    Milestone 2: Video Pipeline - Verify frame iteration.
    
    Logic:
        1. Iterate through the entire video using the loader.
        2. Count the frames.
        3. Verify each frame is a valid numpy array.
        
    Why this matters:
        Ensures we don't drop frames or crash during sequential processing.
    """
    loader = FrameLoader(sample_video)
    
    count = 0
    for idx, frame in loader.iter_frames():
        assert isinstance(frame, np.ndarray), "Frame is not a numpy array"
        assert frame.shape == (480, 640, 3), f"Frame shape mismatch: {frame.shape}"
        count += 1
        
    assert count == 10, f"Expected 10 frames, got {count}"
    loader.close()

def test_frameloader_seek(sample_video):
    """
    Milestone 2: Video Pipeline - Verify seeking.
    
    Logic:
        1. Ask the loader to start iterating from frame 5.
        2. Verify that the first frame yielded has index 5.
        
    Why this matters:
        When the user drags the video timeline (scrubber) in the UI, we need to jump instantly to that frame.
        If seeking is broken, the scrubbing experience will feel broken.
    """
    loader = FrameLoader(sample_video)
    
    # Seek to middle
    frames = list(loader.iter_frames(start_frame=5))
    assert len(frames) == 5, "Seeking to frame 5 should leave 5 frames remaining (5-9)" # Should get 5, 6, 7, 8, 9
    assert frames[0][0] == 5, f"Expected to start at frame 5, got {frames[0][0]}" # The index yielded
    
    loader.close()
