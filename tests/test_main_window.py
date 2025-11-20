import pytest
from PyQt6.QtWidgets import QApplication
from unittest.mock import MagicMock

@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app

@pytest.fixture
def playback_controller_patch(monkeypatch):
    from mill_presenter.ui import main_window

    fake_controller_cls = MagicMock()
    fake_controller_instance = MagicMock()
    fake_controller_cls.return_value = fake_controller_instance
    monkeypatch.setattr(main_window, "PlaybackController", fake_controller_cls)
    return fake_controller_cls, fake_controller_instance


def test_main_window_init(qapp, playback_controller_patch):
    """Test that MainWindow can be initialized."""
    try:
        from mill_presenter.ui.main_window import MainWindow
    except ImportError:
        pytest.fail("MainWindow not implemented")
        
    config = {'overlay': {'colors': {}}}
    frame_loader = MagicMock()
    frame_loader.total_frames = 100
    results_cache = MagicMock()

    controller_cls, _ = playback_controller_patch

    window = MainWindow(config, frame_loader=frame_loader, results_cache=results_cache)
    assert window is not None
    assert window.video_widget is not None
    controller_cls.assert_called_once_with(frame_loader, results_cache, window.video_widget, parent=window)


def test_play_button_controls_controller(qapp, playback_controller_patch):
    try:
        from mill_presenter.ui.main_window import MainWindow
    except ImportError:
        pytest.fail("MainWindow not implemented")

    config = {'overlay': {'colors': {}}}
    frame_loader = MagicMock()
    frame_loader.total_frames = 100
    results_cache = MagicMock()

    _, controller_instance = playback_controller_patch

    window = MainWindow(config, frame_loader=frame_loader, results_cache=results_cache)

    window.play_button.setChecked(True)
    controller_instance.play.assert_called_once()

    window.play_button.setChecked(False)
    controller_instance.pause.assert_called_once()


def test_size_toggle_updates_visible_classes(qapp, playback_controller_patch):
    try:
        from mill_presenter.ui.main_window import MainWindow
    except ImportError:
        pytest.fail("MainWindow not implemented")

    config = {'overlay': {'colors': {}}}
    frame_loader = MagicMock()
    frame_loader.total_frames = 100
    results_cache = MagicMock()

    _, controller_instance = playback_controller_patch

    window = MainWindow(config, frame_loader=frame_loader, results_cache=results_cache)
    window.video_widget.update = MagicMock()

    toggle_button = window.toggles[6]

    assert 6 in window.video_widget.visible_classes

    toggle_button.setChecked(False)
    assert 6 not in window.video_widget.visible_classes
    window.video_widget.update.assert_called()

    window.video_widget.update.reset_mock()
    toggle_button.setChecked(True)
    assert 6 in window.video_widget.visible_classes
    window.video_widget.update.assert_called()

def test_slider_controls_seeking(qapp, playback_controller_patch):
    from mill_presenter.ui.main_window import MainWindow
    
    config = {'overlay': {'colors': {}}}
    frame_loader = MagicMock()
    frame_loader.total_frames = 100
    results_cache = MagicMock()
    
    _, controller_instance = playback_controller_patch
    
    window = MainWindow(config, frame_loader=frame_loader, results_cache=results_cache)
    
    # Check slider exists and range is correct
    assert hasattr(window, 'slider')
    assert window.slider.maximum() == 99 # 0-indexed
    
    # Test: Slider movement calls seek
    # We use sliderMoved to represent user interaction
    window.slider.sliderMoved.emit(50)
    controller_instance.seek.assert_called_with(50)
