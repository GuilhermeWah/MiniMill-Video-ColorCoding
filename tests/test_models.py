import pytest
from mill_presenter.core.models import Ball, FrameDetections

# ==================================================================================
# TEST SUITE: Data Models & Serialization
# ==================================================================================
# Purpose: 
#   Verify that our core data structures (Ball, FrameDetections) can be correctly
#   converted to and from dictionaries. This is CRITICAL for the caching system,
#   which writes these objects to 'detections.jsonl' on disk.
#
# Criteria for Success:
#   1. No data loss during conversion (all fields preserved).
#   2. Data types are correct (int, float, etc.).
#   3. Nested structures (list of Balls inside FrameDetections) are handled recursively.
# ==================================================================================

def test_ball_serialization():
    """
    Milestone 1: Data Integrity - Verify Ball serialization.
    
    Logic:
        1. Create a 'Ball' object with known, hardcoded values.
        2. Call the .to_dict() method.
        3. Assert that every key in the resulting dictionary matches the input.
        
    Why this matters:
        If this fails, the 'detections.jsonl' file will contain garbage or missing data,
        breaking the playback overlay and export features.
    """
    ball = Ball(x=100, y=200, r_px=50.5, diameter_mm=10.0, cls=10, conf=0.95)
    data = ball.to_dict()
    
    # Verification: Check every field individually
    assert data['x'] == 100, "X coordinate mismatch"
    assert data['y'] == 200, "Y coordinate mismatch"
    assert data['r_px'] == 50.5, "Radius (px) mismatch"
    assert data['diameter_mm'] == 10.0, "Diameter (mm) mismatch"
    assert data['cls'] == 10, "Class label mismatch"
    assert data['conf'] == 0.95, "Confidence score mismatch"

def test_frame_detections_serialization():
    """
    Milestone 1: Data Integrity - Verify FrameDetections serialization.
    
    Logic:
        1. Create multiple 'Ball' objects.
        2. Wrap them in a 'FrameDetections' object (representing one video frame).
        3. Call .to_dict().
        4. Verify the frame metadata (id, timestamp) AND the list of balls.
        
    Why this matters:
        The cache reads/writes one line per frame. We must ensure the list of balls
        is correctly embedded within the frame object.
    """
    ball1 = Ball(x=10, y=10, r_px=5, diameter_mm=4, cls=4, conf=0.9)
    ball2 = Ball(x=20, y=20, r_px=10, diameter_mm=8, cls=8, conf=0.8)
    
    frame_det = FrameDetections(frame_id=1, timestamp=0.033, balls=[ball1, ball2])
    data = frame_det.to_dict()
    
    # Verification: Frame metadata
    assert data['frame_id'] == 1, "Frame ID mismatch"
    assert data['timestamp'] == 0.033, "Timestamp mismatch"
    
    # Verification: Nested list integrity
    assert len(data['balls']) == 2, "Incorrect number of balls serialized"
    assert data['balls'][0]['cls'] == 4, "First ball data corrupted"
    assert data['balls'][1]['cls'] == 8, "Second ball data corrupted"
