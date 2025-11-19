import pytest
import numpy as np
import cv2
from mill_presenter.core.processor import VisionProcessor

# ==================================================================================
# TEST SUITE: Vision Processing Logic
# ==================================================================================
# Purpose:
#   Verify the core computer vision algorithms. This is the "Brain" of the application.
#   We use synthetic images (perfect circles) to isolate logic errors from
#   real-world noise issues.
#
# Criteria for Success:
#   1. Can detect beads of different sizes (4mm vs 10mm) based on pixel radius.
#   2. Correctly maps pixel radius to mm class using 'px_per_mm'.
#   3. CRITICAL: Distinguishes between a solid bead and the hole of a ring.
#      (The "Annulus Logic" test).
# ==================================================================================

@pytest.fixture
def basic_config():
    """Standard configuration for testing."""
    return {
        'calibration': {'px_per_mm': 10.0}, # 10 pixels = 1 mm
        'vision': {
            'hough_param1': 50,
            'hough_param2': 30,
            'min_dist_px': 15
        },
        'bins_mm': [
            {'label': 4, 'min': 3.0, 'max': 5.0},
            {'label': 10, 'min': 9.0, 'max': 11.0}
        ]
    }

@pytest.fixture
def synthetic_bead_image():
    """
    Creates an image with a perfect white circle on black background.
    Used to test basic detection and classification.
    """
    img = np.zeros((400, 400, 3), dtype=np.uint8)
    
    # Draw a "10mm" bead
    # px_per_mm = 10.0, so 10mm = 100px diameter = 50px radius
    cv2.circle(img, (100, 100), 50, (255, 255, 255), -1) # Filled circle
    
    # Draw a "4mm" bead
    # 4mm = 40px diameter = 20px radius
    cv2.circle(img, (250, 250), 20, (255, 255, 255), -1)
    
    return img

def test_processor_detection(basic_config, synthetic_bead_image):
    """
    Milestone 3: Vision Logic - Verify detection of synthetic shapes.
    
    Logic:
        1. Feed the synthetic image (with 10mm and 4mm circles) to the processor.
        2. Check if the output list contains balls at the expected coordinates.
        3. Check if the 'cls' (class) attribute matches the expected size (10 or 4).
        
    Why this matters:
        If we can't detect perfect white circles on black, we have no hope of detecting
        real beads in a noisy mill.
    """
    processor = VisionProcessor(basic_config)
    
    # The processor expects BGR
    balls = processor.process_frame(synthetic_bead_image)
    
    # We expect at least 2 balls
    assert len(balls) >= 2, "Expected at least 2 detections"
    
    # Check for the 10mm ball (approx)
    found_10mm = False
    found_4mm = False
    
    for b in balls:
        if b.cls == 10:
            # Check position (allow 5px error margin)
            if abs(b.x - 100) < 5 and abs(b.y - 100) < 5:
                found_10mm = True
        elif b.cls == 4:
            if abs(b.x - 250) < 5 and abs(b.y - 250) < 5:
                found_4mm = True
                
    assert found_10mm, "Failed to detect 10mm synthetic bead"
    assert found_4mm, "Failed to detect 4mm synthetic bead"

def test_processor_annulus_logic(basic_config):
    """
    Milestone 3: Vision Logic - Verify annulus/hole rejection.
    
    Logic:
        1. Create a synthetic "Ring" (White outer circle, Black inner circle).
        2. Outer radius = 50px (10mm). Inner radius = 20px (4mm).
        3. Run processor.
        
    The Trap:
        A naive detector sees TWO circles:
        1. The outer white rim (10mm).
        2. The inner black hole (4mm).
        
    The Requirement:
        The processor must realize the 4mm circle is INSIDE the 10mm circle
        and discard it. It should ONLY report the 10mm bead.
        
    Why this matters:
        Beads are rings. If we count the holes, we will falsely report thousands of
        "small beads" that don't exist, ruining the analysis.
    """
    processor = VisionProcessor(basic_config)
    
    img = np.zeros((400, 400, 3), dtype=np.uint8)
    
    # Draw a large ring (outer)
    # Center (200, 200), Radius 50 (10mm)
    cv2.circle(img, (200, 200), 50, (255, 255, 255), -1)
    
    # Draw a hole (inner) - black circle inside
    # Radius 20 (4mm hole)
    cv2.circle(img, (200, 200), 20, (0, 0, 0), -1)
    
    # The processor should detect the OUTER ring (10mm)
    # It should NOT detect the INNER hole as a separate 4mm bead
    
    balls = processor.process_frame(img)
    
    # Filter for balls near center
    center_balls = [b for b in balls if abs(b.x - 200) < 10 and abs(b.y - 200) < 10]
    
    # Should have exactly one ball (the 10mm one)
    # If logic fails, we might see two (10mm and 4mm)
    assert len(center_balls) == 1, f"Expected 1 ball (outer ring), found {len(center_balls)}"
    assert center_balls[0].cls == 10, f"Expected class 10, got {center_balls[0].cls}"
