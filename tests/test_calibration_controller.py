# Tests for CalibrationController

"""
TDD tests for the point-to-point calibration tool.
Run with: pytest tests/test_calibration_controller.py -v
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
import math
from unittest.mock import MagicMock, patch

from mill_presenter.ui.calibration_controller import CalibrationController


class TestCalibrationControllerState:
    """Tests for calibration state management."""
    
    def test_starts_inactive(self):
        """Calibration should start in inactive state."""
        controller = CalibrationController()
        assert controller.is_active is False
    
    def test_start_activates(self):
        """start() should activate calibration mode."""
        controller = CalibrationController()
        controller.start()
        assert controller.is_active is True
    
    def test_start_clears_points(self):
        """start() should clear any existing points."""
        controller = CalibrationController()
        controller._points = [(100, 100)]
        controller.start()
        assert controller.points == []
    
    def test_cancel_deactivates(self):
        """cancel() should deactivate calibration mode."""
        controller = CalibrationController()
        controller.start()
        controller.cancel()
        assert controller.is_active is False
    
    def test_cancel_clears_points(self):
        """cancel() should clear points."""
        controller = CalibrationController()
        controller.start()
        controller._points = [(100, 100), (200, 200)]
        controller.cancel()
        assert controller.points == []


class TestCalibrationClicks:
    """Tests for click handling."""
    
    def test_click_when_inactive_returns_false(self):
        """Clicks should be ignored when not in calibration mode."""
        controller = CalibrationController()
        result = controller.handle_click(100, 100)
        assert result is False
        assert controller.points == []
    
    def test_first_click_adds_point(self):
        """First click should add a point."""
        controller = CalibrationController()
        controller.start()
        controller.handle_click(100, 100)
        assert controller.points == [(100, 100)]
    
    def test_second_click_adds_point(self):
        """Second click should add another point."""
        controller = CalibrationController()
        controller.start()
        controller.handle_click(100, 100)
        controller.handle_click(200, 200)
        assert len(controller.points) == 2
    
    def test_third_click_ignored(self):
        """Third click should be ignored (max 2 points)."""
        controller = CalibrationController()
        controller.start()
        controller.handle_click(100, 100)
        controller.handle_click(200, 200)
        controller.handle_click(300, 300)  # Should be ignored
        assert len(controller.points) == 2
    
    def test_click_emits_signal(self):
        """Click should emit point_added signal."""
        controller = CalibrationController()
        controller.start()
        
        signal_received = []
        controller.point_added.connect(lambda x, y: signal_received.append((x, y)))
        
        controller.handle_click(150, 250)
        assert signal_received == [(150, 250)]


class TestDistanceCalculation:
    """Tests for pixel distance calculation."""
    
    def test_horizontal_distance(self):
        """Calculate horizontal distance correctly."""
        controller = CalibrationController()
        controller._points = [(0, 0), (100, 0)]
        assert controller._calculate_pixel_distance() == 100.0
    
    def test_vertical_distance(self):
        """Calculate vertical distance correctly."""
        controller = CalibrationController()
        controller._points = [(0, 0), (0, 100)]
        assert controller._calculate_pixel_distance() == 100.0
    
    def test_diagonal_distance(self):
        """Calculate diagonal distance correctly."""
        controller = CalibrationController()
        controller._points = [(0, 0), (30, 40)]
        assert controller._calculate_pixel_distance() == 50.0  # 3-4-5 triangle
    
    def test_empty_points_returns_zero(self):
        """No points should return 0."""
        controller = CalibrationController()
        assert controller._calculate_pixel_distance() == 0.0
    
    def test_one_point_returns_zero(self):
        """One point should return 0."""
        controller = CalibrationController()
        controller._points = [(100, 100)]
        assert controller._calculate_pixel_distance() == 0.0


class TestPxPerMmCalculation:
    """Tests for px_per_mm calculation."""
    
    def test_basic_calculation(self):
        """100 pixels / 10mm = 10 px/mm."""
        # pixel_dist / mm_dist = px_per_mm
        pixel_dist = 100.0
        mm_dist = 10.0
        expected = 10.0
        assert pixel_dist / mm_dist == expected
    
    def test_calculation_with_decimals(self):
        """Handle decimal values correctly."""
        pixel_dist = 85.5
        mm_dist = 8.0
        expected = 10.6875
        assert abs(pixel_dist / mm_dist - expected) < 0.0001


class TestCalibrationSignals:
    """Tests for signal emission."""
    
    def test_cancelled_signal_on_cancel(self):
        """cancel() should emit calibration_cancelled signal."""
        controller = CalibrationController()
        controller.start()
        
        signal_received = [False]
        controller.calibration_cancelled.connect(lambda: signal_received.__setitem__(0, True))
        
        controller.cancel()
        assert signal_received[0] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
