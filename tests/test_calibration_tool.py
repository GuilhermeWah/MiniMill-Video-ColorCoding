import pytest
from unittest.mock import MagicMock
import math

def test_calibration_math():
    """Verify the basic math for px_per_mm."""
    from mill_presenter.core.calibration import calculate_px_per_mm
    
    # 100px distance, 10mm real
    p1 = (0, 0)
    p2 = (100, 0)
    ratio = calculate_px_per_mm(p1, p2, 10.0)
    assert ratio == 10.0

    # Diagonal: 3,4,5 triangle. 50px distance, 5mm real -> 10px/mm
    p1 = (0, 0)
    p2 = (30, 40)
    ratio = calculate_px_per_mm(p1, p2, 5.0)
    assert ratio == 10.0

def test_calibration_controller_flow():
    """Verify the UI flow: Start -> Click -> Click -> Calculate."""
    from mill_presenter.ui.calibration_controller import CalibrationController
    
    mock_widget = MagicMock()
    mock_config = {'calibration': {'px_per_mm': None}}
    
    controller = CalibrationController(mock_widget, mock_config)
    
    # 1. Start
    controller.start()
    assert controller.is_active
    assert mock_widget.set_interaction_mode.called
    
    # 2. Clicks (simulating widget signals or direct calls)
    controller.handle_click(10, 10) # Point A
    assert controller.points == [(10, 10)]
    
    controller.handle_click(110, 10) # Point B (100px away)
    assert controller.points == [(10, 10), (110, 10)]
    
    # 3. Calculate & Apply
    controller.set_known_distance(10.0) # 10mm
    controller.apply()
    
    assert mock_config['calibration']['px_per_mm'] == 10.0
    assert not controller.is_active
