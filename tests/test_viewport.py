"""
Test Suite: Viewport Widget

Tests video display, overlay rendering, zoom, pan, and interactions.
"""

import pytest
import numpy as np
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QWheelEvent


class TestViewportStructure:
    """Test viewport widget structure."""
    
    def test_viewport_exists(self, main_window):
        """Viewport should exist."""
        assert main_window.viewport is not None
    
    def test_viewport_minimum_size(self, main_window):
        """Viewport should have minimum size."""
        assert main_window.viewport.minimumWidth() >= 320
        assert main_window.viewport.minimumHeight() >= 240
    
    def test_viewport_has_focus_policy(self, main_window):
        """Viewport should accept focus for keyboard events."""
        assert main_window.viewport.focusPolicy() != Qt.FocusPolicy.NoFocus


class TestViewportFrame:
    """Test viewport frame display."""
    
    def test_set_frame_accepts_numpy(self, main_window, qtbot):
        """set_frame should accept numpy array."""
        # Create a test frame (BGR)
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[:, :, 2] = 255  # Red frame
        
        main_window.viewport.set_frame(frame)
        qtbot.wait(50)
        
        assert main_window.viewport._frame is not None
        assert main_window.viewport._frame_size.width() == 640
        assert main_window.viewport._frame_size.height() == 480
    
    def test_set_frame_none_clears(self, main_window, qtbot):
        """set_frame(None) should clear the frame."""
        # Set a frame first
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        main_window.viewport.set_frame(frame)
        qtbot.wait(50)
        
        # Clear it
        main_window.viewport.set_frame(None)
        qtbot.wait(50)
        
        assert main_window.viewport._frame is None


class TestViewportDetections:
    """Test viewport detection overlays."""
    
    def test_set_detections_stores_data(self, main_window, qtbot):
        """set_detections should store detection data."""
        detections = [
            {"x": 100, "y": 100, "r_px": 20, "conf": 0.9, "cls": "6mm"},
            {"x": 200, "y": 200, "r_px": 15, "conf": 0.8, "cls": "4mm"},
        ]
        
        main_window.viewport.set_detections(detections)
        qtbot.wait(50)
        
        assert len(main_window.viewport._detections) == 2
    
    def test_set_overlay_visibility(self, main_window, qtbot):
        """set_overlay_visibility should update flag."""
        main_window.viewport.set_overlay_visibility(False)
        assert main_window.viewport._show_overlays is False
        
        main_window.viewport.set_overlay_visibility(True)
        assert main_window.viewport._show_overlays is True
    
    def test_set_overlay_opacity(self, main_window, qtbot):
        """set_overlay_opacity should update value."""
        main_window.viewport.set_overlay_opacity(0.5)
        assert main_window.viewport._overlay_opacity == 0.5
    
    def test_set_min_confidence(self, main_window, qtbot):
        """set_min_confidence should update threshold."""
        main_window.viewport.set_min_confidence(0.7)
        assert main_window.viewport._min_confidence == 0.7
    
    def test_set_visible_classes(self, main_window, qtbot):
        """set_visible_classes should update class set."""
        main_window.viewport.set_visible_classes({"4mm", "6mm"})
        
        assert "4mm" in main_window.viewport._visible_classes
        assert "6mm" in main_window.viewport._visible_classes
        assert "8mm" not in main_window.viewport._visible_classes


class TestViewportZoomPan:
    """Test viewport zoom and pan."""
    
    def test_initial_zoom_is_one(self, main_window):
        """Initial zoom should be 1.0."""
        assert main_window.viewport._zoom == 1.0
    
    def test_reset_view_resets_zoom(self, main_window, qtbot):
        """reset_view should reset zoom and pan."""
        # Change zoom
        main_window.viewport._zoom = 2.0
        main_window.viewport._pan_offset = QPoint(100, 100)
        
        # Reset
        main_window.viewport.reset_view()
        qtbot.wait(50)
        
        assert main_window.viewport._zoom == 1.0
        assert main_window.viewport._pan_offset == QPoint(0, 0)
    
    def test_zoom_limits(self, main_window, qtbot):
        """Zoom should have min/max limits."""
        assert main_window.viewport._min_zoom > 0
        assert main_window.viewport._max_zoom > main_window.viewport._min_zoom


class TestViewportDrumROI:
    """Test viewport drum ROI display."""
    
    def test_set_drum_roi(self, main_window, qtbot):
        """set_drum_roi should store ROI parameters."""
        main_window.viewport.set_drum_roi(
            center=(500, 500),
            radius=300,
            show=True
        )
        qtbot.wait(50)
        
        assert main_window.viewport._drum_center == (500, 500)
        assert main_window.viewport._drum_radius == 300
        assert main_window.viewport._show_roi is True
    
    def test_show_roi_toggle(self, main_window, qtbot):
        """show_roi should toggle visibility."""
        main_window.viewport.show_roi(True)
        assert main_window.viewport._show_roi is True
        
        main_window.viewport.show_roi(False)
        assert main_window.viewport._show_roi is False
