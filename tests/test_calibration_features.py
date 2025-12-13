"""
Test Suite: Calibration and ROI Features

Tests two-point measurement tool, ROI adjustment, reset parameters, 
frame count selector, and related calibration features.
"""

import pytest
from PySide6.QtCore import Qt, QPoint


class TestTwoPointMeasurement:
    """Test two-point measurement calibration tool."""
    
    def test_twopoint_radio_exists(self, main_window):
        """Two-point radio button should exist."""
        assert main_window.right_panel.calibration_tab.twopoint_radio is not None
    
    def test_twopoint_group_initially_hidden(self, main_window):
        """Two-point group should be hidden when not selected."""
        # Check widget's own hidden state, not isVisible which depends on parent
        assert main_window.right_panel.calibration_tab.twopoint_group.isHidden()
    
    def test_twopoint_group_visible_when_selected(self, main_window, qtbot):
        """Two-point group should NOT be hidden when two-point mode selected."""
        main_window.right_panel.calibration_tab.twopoint_radio.setChecked(True)
        qtbot.wait(50)
        
        # Check that it's not hidden (widget's own state)
        assert not main_window.right_panel.calibration_tab.twopoint_group.isHidden()
    
    def test_start_measure_btn_exists(self, main_window):
        """Start Measurement button should exist."""
        assert main_window.right_panel.calibration_tab.start_measure_btn is not None
    
    def test_start_measure_activates_mode(self, main_window, qtbot):
        """Clicking Start Measurement should activate two-point mode."""
        cal_tab = main_window.right_panel.calibration_tab
        cal_tab.twopoint_radio.setChecked(True)
        qtbot.wait(50)
        
        assert not cal_tab.is_two_point_active()
        
        qtbot.mouseClick(cal_tab.start_measure_btn, Qt.MouseButton.LeftButton)
        qtbot.wait(50)
        
        assert cal_tab.is_two_point_active()
    
    def test_cancel_measurement_deactivates_mode(self, main_window, qtbot):
        """Cancelling measurement should deactivate two-point mode."""
        cal_tab = main_window.right_panel.calibration_tab
        cal_tab.twopoint_radio.setChecked(True)
        qtbot.wait(50)
        
        # Start measurement
        qtbot.mouseClick(cal_tab.start_measure_btn, Qt.MouseButton.LeftButton)
        qtbot.wait(50)
        
        assert cal_tab.is_two_point_active()
        
        # Cancel (button text changes to "Cancel Measurement")
        qtbot.mouseClick(cal_tab.start_measure_btn, Qt.MouseButton.LeftButton)
        qtbot.wait(50)
        
        assert not cal_tab.is_two_point_active()
    
    def test_set_pixel_distance_updates_label(self, main_window, qtbot):
        """set_pixel_distance should update the pixel distance label."""
        cal_tab = main_window.right_panel.calibration_tab
        cal_tab.set_pixel_distance(150.0)
        qtbot.wait(50)
        
        assert "150.0" in cal_tab.pixel_dist_label.text()
    
    def test_set_pixel_distance_enables_inputs(self, main_window, qtbot):
        """set_pixel_distance should enable distance input and apply button."""
        cal_tab = main_window.right_panel.calibration_tab
        cal_tab.twopoint_radio.setChecked(True)
        qtbot.wait(50)
        
        # Start measurement
        qtbot.mouseClick(cal_tab.start_measure_btn, Qt.MouseButton.LeftButton)
        qtbot.wait(50)
        
        cal_tab.set_pixel_distance(100.0)
        qtbot.wait(50)
        
        assert cal_tab.distance_input.isEnabled()
        assert cal_tab.apply_measure_btn.isEnabled()
    
    def test_apply_measurement_calculates_px_per_mm(self, main_window, qtbot):
        """Applying measurement should calculate correct px/mm."""
        cal_tab = main_window.right_panel.calibration_tab
        cal_tab.twopoint_radio.setChecked(True)
        qtbot.wait(50)
        
        # Start measurement
        qtbot.mouseClick(cal_tab.start_measure_btn, Qt.MouseButton.LeftButton)
        qtbot.wait(50)
        
        # Set pixel distance and known mm
        cal_tab.set_pixel_distance(100.0)
        cal_tab.distance_input.setValue(10.0)  # 10 mm
        qtbot.wait(50)
        
        # Get initial px_per_mm value
        initial_value = cal_tab.px_per_mm_input.value()
        
        # Apply
        qtbot.mouseClick(cal_tab.apply_measure_btn, Qt.MouseButton.LeftButton)
        qtbot.wait(50)
        
        # 100 px / 10 mm = 10 px/mm
        assert abs(cal_tab.px_per_mm_input.value() - 10.0) < 0.01
    
    def test_is_two_point_active_tracks_state(self, main_window, qtbot):
        """is_two_point_active should correctly track measurement state."""
        cal_tab = main_window.right_panel.calibration_tab
        cal_tab.twopoint_radio.setChecked(True)
        qtbot.wait(50)
        
        assert not cal_tab.is_two_point_active()
        
        # Start measurement
        qtbot.mouseClick(cal_tab.start_measure_btn, Qt.MouseButton.LeftButton)
        qtbot.wait(50)
        
        assert cal_tab.is_two_point_active()
        
        # Cancel measurement
        qtbot.mouseClick(cal_tab.start_measure_btn, Qt.MouseButton.LeftButton)
        qtbot.wait(50)
        
        assert not cal_tab.is_two_point_active()


class TestROIAdjustment:
    """Test drum ROI adjustment controls."""
    
    def test_roi_shrink_btn_exists(self, main_window):
        """ROI shrink button should exist."""
        assert main_window.right_panel.calibration_tab.roi_shrink_btn is not None
    
    def test_roi_expand_btn_exists(self, main_window):
        """ROI expand button should exist."""
        assert main_window.right_panel.calibration_tab.roi_expand_btn is not None
    
    def test_roi_radius_label_exists(self, main_window):
        """ROI radius label should exist."""
        assert main_window.right_panel.calibration_tab.roi_radius_label is not None
    
    def test_set_roi_updates_values(self, main_window, qtbot):
        """set_roi should update internal values and label."""
        cal_tab = main_window.right_panel.calibration_tab
        cal_tab.set_roi(300, 300, 200)
        qtbot.wait(50)
        
        assert cal_tab._roi_center == (300, 300)
        assert cal_tab._roi_radius == 200
        assert "200" in cal_tab.roi_radius_label.text()
    
    def test_shrink_btn_decreases_radius(self, main_window, qtbot):
        """Clicking shrink button should decrease ROI radius."""
        cal_tab = main_window.right_panel.calibration_tab
        cal_tab.set_roi(300, 300, 200)
        qtbot.wait(50)
        
        qtbot.mouseClick(cal_tab.roi_shrink_btn, Qt.MouseButton.LeftButton)
        qtbot.wait(50)
        
        # Radius should be decreased by 5
        assert cal_tab._roi_radius == 195
    
    def test_expand_btn_increases_radius(self, main_window, qtbot):
        """Clicking expand button should increase ROI radius."""
        cal_tab = main_window.right_panel.calibration_tab
        cal_tab.set_roi(300, 300, 200)
        qtbot.wait(50)
        
        qtbot.mouseClick(cal_tab.roi_expand_btn, Qt.MouseButton.LeftButton)
        qtbot.wait(50)
        
        # Radius should be increased by 5
        assert cal_tab._roi_radius == 205
    
    def test_roi_minimum_radius(self, main_window, qtbot):
        """ROI radius should not go below 50."""
        cal_tab = main_window.right_panel.calibration_tab
        cal_tab.set_roi(300, 300, 55)  # Close to minimum
        qtbot.wait(50)
        
        # Click shrink twice (would go to 50, then 45)
        qtbot.mouseClick(cal_tab.roi_shrink_btn, Qt.MouseButton.LeftButton)
        qtbot.wait(50)
        qtbot.mouseClick(cal_tab.roi_shrink_btn, Qt.MouseButton.LeftButton)
        qtbot.wait(50)
        
        # Should be clamped at 50
        assert cal_tab._roi_radius >= 50


class TestFrameCountSelector:
    """Test frame count selector for detection."""
    
    def test_frame_count_combo_exists(self, main_window):
        """Frame count combo box should exist."""
        assert main_window.right_panel.process_tab.frame_count_combo is not None
    
    def test_frame_count_has_options(self, main_window):
        """Frame count combo should have all expected options."""
        combo = main_window.right_panel.process_tab.frame_count_combo
        
        # Should have 5 options
        assert combo.count() == 5
    
    def test_frame_count_option_values(self, main_window):
        """Frame count options should have correct values."""
        combo = main_window.right_panel.process_tab.frame_count_combo
        
        # Check data values
        assert combo.itemData(0) == 1    # Current Frame Only
        assert combo.itemData(1) == 10   # 10 Frames
        assert combo.itemData(2) == 30   # 30 Frames
        assert combo.itemData(3) == 100  # 100 Frames
        assert combo.itemData(4) == -1   # All Frames
    
    def test_default_is_all_frames(self, main_window):
        """Default selection should be All Frames."""
        combo = main_window.right_panel.process_tab.frame_count_combo
        
        assert combo.currentIndex() == 4  # All Frames is index 4
        assert combo.currentData() == -1
    
    def test_frame_count_selection_works(self, main_window, qtbot):
        """Selecting different frame counts should work."""
        combo = main_window.right_panel.process_tab.frame_count_combo
        
        # Select 10 frames
        combo.setCurrentIndex(1)
        qtbot.wait(50)
        
        assert combo.currentData() == 10


class TestResetParameters:
    """Test reset parameters button."""
    
    def test_reset_btn_exists(self, main_window):
        """Reset button should exist."""
        assert main_window.right_panel.process_tab.reset_btn is not None
    
    def test_default_params_constant_exists(self, main_window):
        """DEFAULT_PARAMS constant should exist."""
        from ui.widgets.right_panel import ProcessTab
        
        assert hasattr(ProcessTab, 'DEFAULT_PARAMS')
        assert 'blur_kernel' in ProcessTab.DEFAULT_PARAMS
        assert 'canny_low' in ProcessTab.DEFAULT_PARAMS
        assert 'canny_high' in ProcessTab.DEFAULT_PARAMS
        assert 'hough_dp' in ProcessTab.DEFAULT_PARAMS
        assert 'hough_param2' in ProcessTab.DEFAULT_PARAMS
        assert 'hough_min_dist' in ProcessTab.DEFAULT_PARAMS
    
    def test_default_params_values(self, main_window):
        """DEFAULT_PARAMS should have proven values."""
        from ui.widgets.right_panel import ProcessTab
        
        # These are the proven default values
        assert ProcessTab.DEFAULT_PARAMS['blur_kernel'] == 7
        assert ProcessTab.DEFAULT_PARAMS['canny_low'] == 50
        assert ProcessTab.DEFAULT_PARAMS['canny_high'] == 150
        assert ProcessTab.DEFAULT_PARAMS['hough_dp'] == 1.0
        assert ProcessTab.DEFAULT_PARAMS['hough_param2'] == 25
        assert ProcessTab.DEFAULT_PARAMS['hough_min_dist'] == 15
    
    def test_reset_restores_defaults(self, main_window, qtbot):
        """Reset button should restore all parameters to defaults."""
        process_tab = main_window.right_panel.process_tab
        
        # Change values
        process_tab.blur_slider.set_value(11)
        process_tab.canny_low_slider.set_value(100)
        process_tab.hough_param2_slider.set_value(50)
        qtbot.wait(50)
        
        # Click reset
        qtbot.mouseClick(process_tab.reset_btn, Qt.MouseButton.LeftButton)
        qtbot.wait(50)
        
        # Values should be restored
        from ui.widgets.right_panel import ProcessTab
        assert process_tab.blur_slider.value() == ProcessTab.DEFAULT_PARAMS['blur_kernel']
        assert process_tab.canny_low_slider.value() == ProcessTab.DEFAULT_PARAMS['canny_low']
        assert process_tab.hough_param2_slider.value() == ProcessTab.DEFAULT_PARAMS['hough_param2']


class TestViewportTwoPointMode:
    """Test viewport two-point measurement mode."""
    
    def test_set_two_point_mode_sets_flag(self, main_window, qtbot):
        """set_two_point_mode should set internal flag."""
        main_window.viewport.set_two_point_mode(True)
        
        assert main_window.viewport._two_point_mode is True
        
        main_window.viewport.set_two_point_mode(False)
        
        assert main_window.viewport._two_point_mode is False
    
    def test_set_two_point_mode_clears_points_on_disable(self, main_window, qtbot):
        """Disabling two-point mode should clear stored points."""
        main_window.viewport._two_point_start = QPoint(100, 100)
        main_window.viewport._two_point_end = QPoint(200, 200)
        
        main_window.viewport.set_two_point_mode(False)
        
        assert main_window.viewport._two_point_start is None
        assert main_window.viewport._two_point_end is None
    
    def test_set_two_point_mode_changes_cursor(self, main_window, qtbot):
        """Enabling two-point mode should change cursor to crosshair."""
        main_window.viewport.set_two_point_mode(True)
        qtbot.wait(50)
        
        assert main_window.viewport.cursor().shape() == Qt.CursorShape.CrossCursor
        
        main_window.viewport.set_two_point_mode(False)
        qtbot.wait(50)
        
        assert main_window.viewport.cursor().shape() == Qt.CursorShape.ArrowCursor


class TestViewportROIAdjustment:
    """Test viewport ROI adjustment."""
    
    def test_adjust_roi_method_exists(self, main_window):
        """adjust_roi method should exist."""
        assert hasattr(main_window.viewport, 'adjust_roi')
    
    def test_adjust_roi_updates_center(self, main_window, qtbot):
        """adjust_roi should update ROI center."""
        main_window.viewport.set_drum_roi((300, 300), 200, True)
        
        main_window.viewport.adjust_roi(10, 20, 0)
        
        assert main_window.viewport._drum_center == (310, 320)
    
    def test_adjust_roi_updates_radius(self, main_window, qtbot):
        """adjust_roi should update ROI radius."""
        main_window.viewport.set_drum_roi((300, 300), 200, True)
        
        main_window.viewport.adjust_roi(0, 0, 15)
        
        assert main_window.viewport._drum_radius == 215
    
    def test_adjust_roi_minimum_radius(self, main_window, qtbot):
        """adjust_roi should not allow radius below 50."""
        main_window.viewport.set_drum_roi((300, 300), 60, True)
        
        main_window.viewport.adjust_roi(0, 0, -20)
        
        assert main_window.viewport._drum_radius >= 50
    
    def test_adjust_roi_updates_internal_state(self, main_window, qtbot):
        """adjust_roi should update both center and radius simultaneously."""
        main_window.viewport.set_drum_roi((300, 300), 200, True)
        
        main_window.viewport.adjust_roi(10, 10, 5)
        
        assert main_window.viewport._drum_center == (310, 310)
        assert main_window.viewport._drum_radius == 205


class TestCalibrationModeSelection:
    """Test calibration mode selection behavior."""
    
    def test_three_calibration_modes_exist(self, main_window):
        """All three calibration mode radio buttons should exist."""
        cal_tab = main_window.right_panel.calibration_tab
        
        assert cal_tab.auto_radio is not None
        assert cal_tab.manual_radio is not None
        assert cal_tab.twopoint_radio is not None
    
    def test_auto_mode_is_default(self, main_window):
        """Auto mode should be selected by default."""
        assert main_window.right_panel.calibration_tab.auto_radio.isChecked()
    
    def test_manual_mode_enables_input(self, main_window, qtbot):
        """Manual mode should enable px_per_mm input."""
        cal_tab = main_window.right_panel.calibration_tab
        
        cal_tab.manual_radio.setChecked(True)
        qtbot.wait(50)
        
        assert cal_tab.px_per_mm_input.isEnabled()
    
    def test_switching_modes_cancels_measurement(self, main_window, qtbot):
        """Switching away from two-point mode should cancel any active measurement."""
        cal_tab = main_window.right_panel.calibration_tab
        
        # Enter two-point mode and start measurement
        cal_tab.twopoint_radio.setChecked(True)
        qtbot.wait(50)
        qtbot.mouseClick(cal_tab.start_measure_btn, Qt.MouseButton.LeftButton)
        qtbot.wait(50)
        
        assert cal_tab.is_two_point_active()
        
        # Switch to auto mode
        cal_tab.auto_radio.setChecked(True)
        qtbot.wait(50)
        
        # Measurement should be cancelled
        assert not cal_tab.is_two_point_active()


class TestApplyButtonRename:
    """Test that Apply button was renamed correctly."""
    
    def test_apply_btn_exists(self, main_window):
        """Apply button should exist."""
        assert main_window.right_panel.process_tab.apply_btn is not None
    
    def test_apply_btn_text(self, main_window):
        """Apply button should have correct text."""
        btn_text = main_window.right_panel.process_tab.apply_btn.text()
        
        assert "Apply" in btn_text
        # Should NOT say "Apply to All"
        assert btn_text.strip() == "Apply" or btn_text.strip() == "▶ Apply"
