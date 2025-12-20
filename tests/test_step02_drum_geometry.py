"""
Unit tests for STEP-02: DrumGeometry

Tests drum detection, ROI mask generation, and calibration.
"""

import pytest
import numpy as np
import cv2
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mill_presenter.core.drum_geometry import DrumGeometry


class TestDrumGeometryDetection:
    """Tests for drum auto-detection."""
    
    def test_detect_synthetic_drum(self):
        """Test detection on synthetic drum image."""
        # Create a synthetic image with a drum circle
        img = np.zeros((1080, 1920, 3), dtype=np.uint8)
        center = (960, 540)
        radius = 400
        cv2.circle(img, center, radius, (200, 200, 200), -1)
        
        # Detect drum
        geometry = DrumGeometry.detect(img, drum_diameter_mm=200.0)
        
        # Check detection accuracy (within 50 pixels)
        assert abs(geometry.center[0] - center[0]) < 50
        assert abs(geometry.center[1] - center[1]) < 50
        assert abs(geometry.radius - radius) < 50
    
    def test_px_per_mm_calculation(self):
        """Test pixels-per-mm calculation."""
        geometry = DrumGeometry(
            center_x=500, center_y=500,
            radius_px=400,
            drum_diameter_mm=200.0
        )
        
        expected_px_per_mm = 400 / 100.0  # radius / (diameter/2)
        assert abs(geometry.px_per_mm - expected_px_per_mm) < 0.01
    
    def test_detect_raises_on_no_drum(self):
        """Test that detection raises error on blank image."""
        blank = np.zeros((100, 100, 3), dtype=np.uint8)
        
        with pytest.raises((ValueError, RuntimeError)):
            DrumGeometry.detect(blank, drum_diameter_mm=200.0)


class TestROIMask:
    """Tests for ROI mask generation."""
    
    def test_roi_mask_shape(self):
        """Test ROI mask has correct shape."""
        geometry = DrumGeometry(500, 500, 300, 200.0)
        mask = geometry.get_roi_mask((1080, 1920))
        
        assert mask.shape == (1080, 1920)
        assert mask.dtype == np.uint8
    
    def test_roi_mask_values(self):
        """Test ROI mask has correct binary values."""
        geometry = DrumGeometry(500, 500, 300, 200.0)
        mask = geometry.get_roi_mask((1000, 1000))
        
        # Center should be inside (255)
        assert mask[500, 500] == 255
        
        # Far corner should be outside (0)
        assert mask[0, 0] == 0
    
    def test_roi_mask_with_margin(self):
        """Test ROI mask with rim margin."""
        geometry = DrumGeometry(500, 500, 300, 200.0)
        mask = geometry.get_roi_mask((1000, 1000), rim_margin=0.1)
        
        # Effective radius should be 270 (300 * 0.9)
        # Point at 280 from center should be outside
        assert mask[500, 780] == 0  # 500 + 280 = 780


class TestIsInsideMethod:
    """Tests for is_inside point checking."""
    
    def test_center_is_inside(self):
        """Test that center point is inside."""
        geometry = DrumGeometry(500, 500, 300, 200.0)
        assert geometry.is_inside(500, 500) is True
    
    def test_outside_point(self):
        """Test that far point is outside."""
        geometry = DrumGeometry(500, 500, 300, 200.0)
        assert geometry.is_inside(0, 0) is False
    
    def test_margin_ratio(self):
        """Test margin ratio affects result."""
        geometry = DrumGeometry(500, 500, 300, 200.0)
        
        # Point at 270px from center (within 10% margin)
        # Should be inside with no margin
        assert geometry.is_inside(770, 500, margin_ratio=0.0) is True
        
        # Should be outside with 12% margin
        assert geometry.is_inside(770, 500, margin_ratio=0.12) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
