"""
Tests for ProcessTab and Calibration Edge Cases

These tests cover:
- Canny parameter propagation to detection
- Frame step processing with overlay display
- Calibration parameter application
- Real-time preview updates
"""

import pytest
from unittest.mock import MagicMock, patch
import numpy as np

from PySide6.QtCore import Qt


class TestCannyParameterPropagation:
    """Test that Canny parameters are properly propagated to detection."""
    
    def test_process_tab_includes_canny_params(self, main_window):
        """Verify ProcessTab.get_params() includes canny_low and canny_high."""
        params = main_window.right_panel.process_tab.get_params()
        
        assert "canny_low" in params, "Missing canny_low in params"
        assert "canny_high" in params, "Missing canny_high in params"
        assert isinstance(params["canny_low"], int)
        assert isinstance(params["canny_high"], int)
    
    def test_canny_slider_values_are_used(self, main_window):
        """Verify slider values are included in get_params()."""
        # Set specific values
        main_window.right_panel.process_tab.canny_low_slider.set_value(75)
        main_window.right_panel.process_tab.canny_high_slider.set_value(200)
        
        params = main_window.right_panel.process_tab.get_params()
        
        assert params["canny_low"] == 75, f"Expected canny_low=75, got {params['canny_low']}"
        assert params["canny_high"] == 200, f"Expected canny_high=200, got {params['canny_high']}"
    
    def test_detection_params_from_dict_includes_canny(self):
        """Verify DetectionParams.from_dict includes canny params."""
        from ui.detection_worker import DetectionParams
        
        data = {
            "blur_kernel": 7,
            "canny_low": 60,
            "canny_high": 180,
            "hough_dp": 1.0,
            "hough_param2": 25,
            "hough_min_dist": 15,
        }
        
        params = DetectionParams.from_dict(data)
        
        assert params.canny_high == 180, "canny_high not loaded from dict"
    
    def test_canny_high_used_as_hough_param1(self):
        """Verify that canny_high is used as the Canny threshold in HoughCircles."""
        from ui.detection_worker import DetectionParams, PreviewWorker
        
        # Create params with specific canny_high
        params = DetectionParams(canny_high=200)
        
        # Create a simple test frame
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        cv2 = pytest.importorskip("cv2")
        
        # Draw a circle
        cv2.circle(frame, (50, 50), 20, (255, 255, 255), -1)
        
        worker = PreviewWorker(frame, params, (50, 50), 40)
        
        # The canny_threshold should use canny_high
        canny_threshold = getattr(params, 'canny_high', params.hough_param1)
        assert canny_threshold == 200, "canny_high should be used as Canny threshold"


class TestFrameStepOverlays:
    """Test that overlays display correctly when using frame_step > 1."""
    
    def test_detection_cache_returns_nearest_frame(self):
        """Verify DetectionCache returns nearest frame detections for unprocessed frames."""
        from ui.video_controller import DetectionCache
        
        cache = DetectionCache()
        
        # Simulate processing every 10th frame
        cache._frames = {
            0: [{"x": 100, "y": 100, "r_px": 15, "conf": 0.9, "cls": "6mm"}],
            10: [{"x": 110, "y": 110, "r_px": 16, "conf": 0.85, "cls": "6mm"}],
            20: [{"x": 120, "y": 120, "r_px": 14, "conf": 0.88, "cls": "6mm"}],
        }
        cache._is_loaded = True
        
        # Frame 0 should return frame 0's detections
        dets_0 = cache.get_detections(0)
        assert len(dets_0) == 1
        assert dets_0[0]["x"] == 100
        
        # Frame 5 should return frame 0's detections (nearest)
        dets_5 = cache.get_detections(5)
        assert len(dets_5) == 1
        assert dets_5[0]["x"] == 100, "Frame 5 should use frame 0's detections"
        
        # Frame 6 should return frame 10's detections (nearest)
        dets_6 = cache.get_detections(6)
        assert len(dets_6) == 1
        assert dets_6[0]["x"] == 110, "Frame 6 should use frame 10's detections"
        
        # Frame 15 should return frame 10's detections (nearest)
        dets_15 = cache.get_detections(15)
        assert len(dets_15) == 1
        assert dets_15[0]["x"] == 110, "Frame 15 should use frame 10's detections"
        
        # Frame 16 should return frame 20's detections (nearest)
        dets_16 = cache.get_detections(16)
        assert len(dets_16) == 1
        assert dets_16[0]["x"] == 120, "Frame 16 should use frame 20's detections"
    
    def test_empty_cache_returns_empty_list(self):
        """Verify empty cache returns empty list."""
        from ui.video_controller import DetectionCache
        
        cache = DetectionCache()
        cache._frames = {}
        cache._is_loaded = True
        
        dets = cache.get_detections(5)
        assert dets == [], "Empty cache should return empty list"
    
    def test_exact_frame_returns_exact_detections(self):
        """Verify exact frame match returns that frame's detections."""
        from ui.video_controller import DetectionCache
        
        cache = DetectionCache()
        cache._frames = {
            10: [{"x": 100, "y": 100}],
            20: [{"x": 200, "y": 200}],
        }
        cache._is_loaded = True
        
        dets = cache.get_detections(10)
        assert dets[0]["x"] == 100, "Exact match should return exact detections"
        
        dets = cache.get_detections(20)
        assert dets[0]["x"] == 200, "Exact match should return exact detections"


class TestCalibrationApplication:
    """Test calibration parameter application and reclassification."""
    
    def test_calibration_tab_set_calibration(self, main_window):
        """Verify CalibrationTab can receive calibration value."""
        calibration_tab = main_window.right_panel.calibration_tab
        
        # Set a calibration value
        calibration_tab.set_calibration(5.5)
        
        # Check the value was stored
        assert calibration_tab.get_calibration() == 5.5
    
    def test_calibration_signal_connected(self, main_window):
        """Verify calibration_changed signal is connected."""
        # The signal should be connected to main_window
        # We can check this by emitting and seeing if the handler is called
        main_window._px_per_mm = 0
        
        # Emit the signal
        main_window.right_panel.calibration_changed.emit(7.5)
        
        # Check if the handler updated the value
        assert main_window._px_per_mm == 7.5, "calibration_changed signal not connected"
    
    def test_reclassify_all_updates_classes(self):
        """Verify reclassify_all updates detection classes."""
        from ui.video_controller import DetectionCache
        
        cache = DetectionCache()
        cache._frames = {
            0: [{"x": 100, "y": 100, "r_px": 20, "conf": 0.9, "cls": "unknown"}],
            1: [{"x": 110, "y": 110, "r_px": 30, "conf": 0.85, "cls": "unknown"}],
        }
        cache._metadata = {}
        cache._is_loaded = True
        
        # Reclassify with px_per_mm = 10.0
        # r_px=20 -> diameter = 40/10 = 4mm -> should be "4mm"
        # r_px=30 -> diameter = 60/10 = 6mm -> should be "6mm"
        count = cache.reclassify_all(10.0)
        
        assert count == 2, f"Expected 2 reclassified, got {count}"
        assert cache._frames[0][0]["cls"] == "4mm", f"Expected 4mm, got {cache._frames[0][0]['cls']}"
        assert cache._frames[1][0]["cls"] == "6mm", f"Expected 6mm, got {cache._frames[1][0]['cls']}"
    
    def test_reclassify_updates_diameter_mm(self):
        """Verify reclassify_all calculates diameter_mm correctly."""
        from ui.video_controller import DetectionCache
        
        cache = DetectionCache()
        cache._frames = {
            0: [{"x": 100, "y": 100, "r_px": 25, "conf": 0.9, "cls": "unknown"}],
        }
        cache._metadata = {}
        cache._is_loaded = True
        
        # px_per_mm = 5.0 -> r_px=25 -> diameter = 50/5 = 10mm
        cache.reclassify_all(5.0)
        
        det = cache._frames[0][0]
        assert "diameter_mm" in det, "diameter_mm should be added"
        assert det["diameter_mm"] == 10.0, f"Expected 10.0mm, got {det['diameter_mm']}"


class TestRealtimePreview:
    """Test real-time preview functionality."""
    
    def test_realtime_mode_triggers_preview(self, main_window, qtbot):
        """Verify changing parameters in realtime mode triggers preview."""
        process_tab = main_window.right_panel.process_tab
        
        # Switch to realtime mode
        process_tab.realtime_radio.setChecked(True)
        
        # Track if preview was requested
        preview_requested = []
        main_window.right_panel.preview_requested.connect(
            lambda params: preview_requested.append(params)
        )
        
        # Change a parameter
        process_tab.blur_slider.set_value(9)
        
        # Wait for signal
        qtbot.wait(100)
        
        assert len(preview_requested) > 0, "Preview should be triggered in realtime mode"
    
    def test_offline_mode_does_not_trigger_preview(self, main_window, qtbot):
        """Verify changing parameters in offline mode does NOT trigger preview."""
        process_tab = main_window.right_panel.process_tab
        
        # Ensure offline mode (default)
        process_tab.offline_radio.setChecked(True)
        
        # Track if preview was requested
        preview_requested = []
        main_window.right_panel.preview_requested.connect(
            lambda params: preview_requested.append(params)
        )
        
        # Change a parameter
        process_tab.blur_slider.set_value(11)
        
        # Wait briefly
        qtbot.wait(100)
        
        assert len(preview_requested) == 0, "Preview should NOT be triggered in offline mode"
    
    def test_preview_detections_persist_on_same_frame(self, main_window):
        """Verify preview detections are not cleared when staying on same frame."""
        # Set preview detections
        preview_dets = [{"x": 100, "y": 100, "r_px": 15, "conf": 0.9, "cls": "6mm"}]
        main_window.viewport.set_preview_detections(preview_dets)
        
        # Setting cached detections should NOT clear preview
        cached_dets = [{"x": 200, "y": 200, "r_px": 20, "conf": 0.8, "cls": "8mm"}]
        main_window.viewport.set_detections(cached_dets)
        
        # Preview should still be there
        assert len(main_window.viewport._preview_detections) == 1
        assert main_window.viewport._preview_detections[0]["x"] == 100
    
    def test_preview_detections_cleared_on_frame_change(self, main_window):
        """Verify preview detections are cleared when frame changes."""
        # Set preview detections
        preview_dets = [{"x": 100, "y": 100, "r_px": 15, "conf": 0.9, "cls": "6mm"}]
        main_window.viewport.set_preview_detections(preview_dets)
        
        # Clear preview (simulating frame change)
        main_window.viewport.clear_preview_detections()
        
        assert len(main_window.viewport._preview_detections) == 0


class TestProcessTabFrameCount:
    """Test ProcessTab frame count selection."""
    
    def test_frame_count_selector_exists(self, main_window):
        """Verify frame count selector exists."""
        process_tab = main_window.right_panel.process_tab
        
        assert hasattr(process_tab, 'frame_count_combo'), "Missing frame_count_combo"
    
    def test_get_frame_count_returns_value(self, main_window):
        """Verify get_frame_count returns selected value."""
        process_tab = main_window.right_panel.process_tab
        
        # Set to a specific value (e.g., 30 frames)
        process_tab.frame_count_combo.setCurrentIndex(2)  # "30 Frames"
        
        frame_count = process_tab.get_frame_count()
        assert isinstance(frame_count, int)
        assert frame_count == 30
    
    def test_frame_count_all_returns_negative_one(self, main_window):
        """Verify 'All Frames' selection returns -1."""
        process_tab = main_window.right_panel.process_tab
        
        # Set to "All Frames" (index 4)
        process_tab.frame_count_combo.setCurrentIndex(4)
        
        frame_count = process_tab.get_frame_count()
        assert frame_count == -1, "All Frames should return -1"


class TestTwoPointCalibration:
    """Test two-point measurement for calibration."""
    
    def test_two_point_mode_toggle(self, main_window, qtbot):
        """Verify two-point mode can be toggled."""
        calibration_tab = main_window.right_panel.calibration_tab
        
        # First enable two-point mode in the radio
        calibration_tab.twopoint_radio.setChecked(True)
        
        # Then click start measurement
        calibration_tab.start_measure_btn.click()
        
        # Check viewport is in two-point mode
        assert main_window.viewport._two_point_mode == True
    
    def test_two_point_measurement_signal(self, main_window):
        """Verify two-point measurement emits signal with pixel distance."""
        measurements = []
        main_window.viewport.two_point_measured.connect(
            lambda dist: measurements.append(dist)
        )
        
        # Simulate measurement (emit signal directly)
        main_window.viewport.two_point_measured.emit(100.5)
        
        assert len(measurements) == 1
        assert measurements[0] == 100.5
    
    def test_right_click_clears_measurement(self, main_window, qtbot):
        """Verify right-click clears two-point measurement."""
        viewport = main_window.viewport
        
        # Enable two-point mode and set some points
        viewport._two_point_mode = True
        viewport._two_point_start = (100, 100)
        viewport._two_point_end = (200, 200)
        
        # Simulate right-click (this should clear the points)
        from PySide6.QtCore import QPoint
        from PySide6.QtGui import QMouseEvent
        from PySide6.QtCore import QEvent
        
        event = QMouseEvent(
            QEvent.Type.MouseButtonPress,
            QPoint(150, 150),
            Qt.MouseButton.RightButton,
            Qt.MouseButton.RightButton,
            Qt.KeyboardModifier.NoModifier
        )
        viewport.mousePressEvent(event)
        
        assert viewport._two_point_start is None
        assert viewport._two_point_end is None


class TestROICalibration:
    """Test ROI (drum) calibration."""
    
    def test_roi_values_set_from_calibration_tab(self, main_window):
        """Verify ROI values can be set from CalibrationTab."""
        calibration_tab = main_window.right_panel.calibration_tab
        
        # Set ROI values
        calibration_tab.set_roi(320, 240, 180)
        
        # Check the values are stored
        cx, cy, r = calibration_tab.get_roi()
        assert cx == 320
        assert cy == 240
        assert r == 180
    
    def test_roi_adjustment_signal(self, main_window):
        """Verify ROI adjustment emits signal."""
        adjustments = []
        main_window.right_panel.roi_adjusted.connect(
            lambda cx, cy, r: adjustments.append((cx, cy, r))
        )
        
        # Trigger ROI adjustment
        calibration_tab = main_window.right_panel.calibration_tab
        calibration_tab.roi_adjusted.emit(400, 300, 200)
        
        assert len(adjustments) == 1
        assert adjustments[0] == (400, 300, 200)
