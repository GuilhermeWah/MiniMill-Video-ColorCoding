import sys
import os
import pytest
from PyQt6.QtWidgets import QApplication
from unittest.mock import MagicMock

# Add the project root's 'src' directory to sys.path
# This allows tests to import 'mill_presenter' without installing the package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

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
