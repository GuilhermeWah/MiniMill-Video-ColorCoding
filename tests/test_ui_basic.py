import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QImage
from unittest.mock import MagicMock, patch

# Singleton QApplication for all tests
@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app

def test_video_widget_init(qapp):
    """Test that VideoWidget can be initialized."""
    try:
        from mill_presenter.ui.widgets import VideoWidget
    except ImportError:
        pytest.fail("VideoWidget not implemented")
        
    config = {'overlay': {'colors': {}}}
    widget = VideoWidget(config)
    assert widget is not None

def test_video_widget_set_frame(qapp):
    """Test setting a frame on the VideoWidget."""
    try:
        from mill_presenter.ui.widgets import VideoWidget
    except ImportError:
        pytest.fail("VideoWidget not implemented")

    config = {'overlay': {'colors': {}}}
    widget = VideoWidget(config)
    
    # Create a dummy QImage
    img = QImage(100, 100, QImage.Format.Format_RGB888)
    
    widget.set_frame(img, None)
    assert widget.current_image == img
