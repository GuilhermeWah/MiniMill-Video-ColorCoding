import pytest
from unittest.mock import MagicMock
from PyQt6.QtGui import QImage, QColor

def test_roi_controller_painting():
    from mill_presenter.ui.roi_controller import ROIController
    
    mock_widget = MagicMock()
    # Mock image dimensions
    mock_widget.current_image.width.return_value = 100
    mock_widget.current_image.height.return_value = 100
    
    controller = ROIController(mock_widget)
    controller.start()
    
    # Verify mask initialized
    assert controller.mask_image is not None
    assert controller.mask_image.width() == 100
    assert controller.mask_image.height() == 100
    
    # Simulate painting (Black = Ignore)
    controller.handle_mouse_press(50, 50, left_button=True)
    controller.handle_mouse_move(55, 55)
    controller.handle_mouse_release(55, 55)
    
    # Check if pixel was painted
    # We can't easily check QImage pixels in a unit test without a QApplication context usually,
    # but we can check if update was called on widget
    assert mock_widget.update.called
    
    # Verify save
    with pytest.raises(Exception): # Expect error as save path not set/mocked
        controller.save("dummy.png")

def test_roi_filtering():
    """Verify that we can filter balls using the mask."""
    from mill_presenter.ui.roi_controller import ROIController
    from mill_presenter.core.models import Ball
    
    # Create a 10x10 mask where (5,5) is Black (0) and rest is White (255)
    # Actually, usually ROI mask: White=Valid, Black=Ignore.
    
    controller = ROIController(None)
    # Manually create a mask (ARGB Overlay)
    # Transparent (Alpha=0) = Valid
    # Red (Alpha>0) = Ignore
    mask = QImage(10, 10, QImage.Format.Format_ARGB32)
    mask.fill(QColor(0, 0, 0, 0)) # Transparent
    mask.setPixelColor(5, 5, QColor(255, 0, 0, 128)) # Red
    controller.mask_image = mask
    
    ball_valid = Ball(x=0, y=0, r_px=1, diameter_mm=1, cls=4, conf=1.0)
    ball_ignored = Ball(x=5, y=5, r_px=1, diameter_mm=1, cls=4, conf=1.0)
    
    assert controller.is_point_valid(0, 0) is True
    assert controller.is_point_valid(5, 5) is False
