"""
Pytest configuration and fixtures for MillPresenter UI tests.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication

# Test data paths
TEST_VIDEO = PROJECT_ROOT / "data" / "DSC_3310.MOV"
TEST_CACHE = PROJECT_ROOT / "cache" / "detections" / "DSC_3310_detections.json"


@pytest.fixture(scope="session")
def qapp():
    """Create QApplication once per test session."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def main_window(qapp, qtbot):
    """Create and show main window for testing."""
    from ui.main_window import MainWindow
    
    window = MainWindow()
    window.show()
    qtbot.addWidget(window)
    
    # Wait for window to be shown
    qtbot.waitExposed(window)
    
    yield window
    
    window.close()


@pytest.fixture
def loaded_window(main_window, qtbot):
    """Main window with video and cache loaded."""
    if TEST_VIDEO.exists():
        main_window._load_video(str(TEST_VIDEO))
        qtbot.wait(100)  # Wait for video to load
    
    if TEST_CACHE.exists():
        main_window._load_cache(str(TEST_CACHE))
        qtbot.wait(100)  # Wait for cache to load
    
    return main_window


@pytest.fixture
def test_video_path():
    """Path to test video file."""
    return str(TEST_VIDEO) if TEST_VIDEO.exists() else None


@pytest.fixture
def test_cache_path():
    """Path to test cache file."""
    return str(TEST_CACHE) if TEST_CACHE.exists() else None
