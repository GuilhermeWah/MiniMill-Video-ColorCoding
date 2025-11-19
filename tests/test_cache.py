import pytest
import os
import json
from mill_presenter.core.cache import ResultsCache
from mill_presenter.core.models import FrameDetections, Ball

# ==================================================================================
# TEST SUITE: Caching System
# ==================================================================================
# Purpose:
#   Verify that we can persist detection results to disk (JSONL) and retrieve them.
#   This is crucial for the "One-Time Detection" requirement.
#
# Criteria for Success:
#   1. Can write a frame's detections to a file.
#   2. Can read that file back and reconstruct the objects.
#   3. Can handle multiple frames (append mode).
#   4. Can clear the cache.
# ==================================================================================

@pytest.fixture
def temp_cache_file(tmp_path):
    return str(tmp_path / "detections.jsonl")

@pytest.fixture
def sample_detections():
    ball1 = Ball(10, 10, 5.0, 4.0, 4, 0.9)
    return FrameDetections(frame_id=1, timestamp=0.033, balls=[ball1])

def test_cache_write_read(temp_cache_file, sample_detections):
    """
    Milestone 2: Caching - Verify write and read cycle.
    
    Logic:
        1. Create a cache instance.
        2. Save a frame.
        3. Create a NEW cache instance pointing to the same file (simulating app restart).
        4. Verify the frame is loaded correctly.
    """
    # 1. Write
    cache = ResultsCache(temp_cache_file)
    cache.save_frame(sample_detections)
    
    # Verify file exists and has content
    assert os.path.exists(temp_cache_file)
    with open(temp_cache_file, 'r') as f:
        lines = f.readlines()
        assert len(lines) == 1
        
    # 2. Read (Simulate restart)
    new_cache = ResultsCache(temp_cache_file)
    # It should auto-load in __init__
    
    loaded_frame = new_cache.get_frame(1)
    assert loaded_frame is not None
    assert loaded_frame.frame_id == 1
    assert len(loaded_frame.balls) == 1
    assert loaded_frame.balls[0].x == 10

def test_cache_append(temp_cache_file):
    """
    Milestone 2: Caching - Verify appending multiple frames.
    """
    cache = ResultsCache(temp_cache_file)
    
    # Save frame 1
    f1 = FrameDetections(1, 0.0, [])
    cache.save_frame(f1)
    
    # Save frame 2
    f2 = FrameDetections(2, 0.033, [])
    cache.save_frame(f2)
    
    # Verify file has 2 lines
    with open(temp_cache_file, 'r') as f:
        lines = f.readlines()
        assert len(lines) == 2
        
    # Verify memory cache has both
    assert cache.get_frame(1) is not None
    assert cache.get_frame(2) is not None

def test_cache_clear(temp_cache_file, sample_detections):
    """
    Milestone 2: Caching - Verify clearing.
    """
    cache = ResultsCache(temp_cache_file)
    cache.save_frame(sample_detections)
    
    assert os.path.exists(temp_cache_file)
    
    cache.clear()
    
    assert not os.path.exists(temp_cache_file)
    assert cache.get_frame(1) is None
