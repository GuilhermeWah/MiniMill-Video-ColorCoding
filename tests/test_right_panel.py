"""
Test Suite: Right Panel Tabs

Tests Process, Calibrate, and Export tabs.
"""

import pytest
from PySide6.QtCore import Qt


class TestRightPanelStructure:
    """Test right panel tab structure."""
    
    def test_right_panel_exists(self, main_window):
        """Right panel should exist."""
        assert main_window.right_panel is not None
    
    def test_tab_widget_exists(self, main_window):
        """Tab widget should exist."""
        assert main_window.right_panel.tabs is not None
    
    def test_four_tabs_exist(self, main_window):
        """Should have 4 tabs."""
        assert main_window.right_panel.tabs.count() == 4
    
    def test_overlay_tab_is_first(self, main_window):
        """Overlay tab should be the default (first) tab."""
        assert main_window.right_panel.tabs.currentIndex() == 0


class TestProcessTab:
    """Test process tab controls."""
    
    def test_process_tab_exists(self, main_window):
        """Process tab should exist."""
        assert main_window.right_panel.process_tab is not None
    
    def test_action_button_exists(self, main_window):
        """Run Detection button should exist."""
        assert main_window.right_panel.process_tab.preview_btn is not None
    
    def test_progress_bar_exists(self, main_window):
        """Progress bar should exist."""
        assert main_window.right_panel.process_tab.progress is not None
    
    def test_progress_bar_initially_hidden(self, main_window):
        """Progress bar should be hidden initially."""
        assert not main_window.right_panel.process_tab.progress.isVisible()
    
    def test_log_text_exists(self, main_window):
        """Log text area should exist."""
        assert main_window.right_panel.process_tab.log_text is not None
    
    def test_set_processing_shows_cancel(self, main_window, qtbot):
        """set_processing(True) should show Cancel button."""
        main_window.right_panel.process_tab.set_processing(True)
        qtbot.wait(50)
        
        # Check that cancel_btn is not hidden (widget's own state)
        assert not main_window.right_panel.process_tab.cancel_btn.isHidden()
        assert not main_window.right_panel.process_tab.progress.isHidden()
    
    def test_set_processing_false_shows_run(self, main_window, qtbot):
        """set_processing(False) should show Run Detection button."""
        main_window.right_panel.process_tab.set_processing(True)
        main_window.right_panel.process_tab.set_processing(False)
        qtbot.wait(50)
        
        # Check that preview_btn is not hidden and cancel_btn is hidden
        assert not main_window.right_panel.process_tab.preview_btn.isHidden()
        assert main_window.right_panel.process_tab.progress.isHidden()
    
    def test_log_method_adds_text(self, main_window, qtbot):
        """log() method should add text to log area."""
        main_window.right_panel.process_tab.clear_log()
        main_window.right_panel.process_tab.log("Test message")
        qtbot.wait(50)
        
        assert "Test message" in main_window.right_panel.process_tab.log_text.toPlainText()


class TestCalibrateTab:
    """Test calibrate tab controls."""
    
    def test_calibrate_tab_exists(self, main_window):
        """Calibrate tab should exist."""
        assert main_window.right_panel.calibration_tab is not None
    
    def test_mode_radio_buttons_exist(self, main_window):
        """Auto/Manual radio buttons should exist."""
        assert main_window.right_panel.calibration_tab.auto_radio is not None
        assert main_window.right_panel.calibration_tab.manual_radio is not None
    
    def test_auto_mode_is_default(self, main_window):
        """Auto mode should be selected by default."""
        assert main_window.right_panel.calibration_tab.auto_radio.isChecked()
    
    def test_px_per_mm_input_exists(self, main_window):
        """px_per_mm input should exist."""
        assert main_window.right_panel.calibration_tab.px_per_mm_input is not None
    
    def test_px_per_mm_disabled_in_auto(self, main_window):
        """px_per_mm input should be disabled in auto mode."""
        assert not main_window.right_panel.calibration_tab.px_per_mm_input.isEnabled()
    
    def test_px_per_mm_enabled_in_manual(self, main_window, qtbot):
        """px_per_mm input should be enabled in manual mode."""
        main_window.right_panel.calibration_tab.manual_radio.setChecked(True)
        qtbot.wait(50)
        
        assert main_window.right_panel.calibration_tab.px_per_mm_input.isEnabled()
    
    def test_show_roi_checkbox_exists(self, main_window):
        """Show ROI checkbox should exist."""
        assert main_window.right_panel.calibration_tab.show_roi is not None
    
    def test_recalculate_button_exists(self, main_window):
        """Recalculate button should exist."""
        assert main_window.right_panel.calibration_tab.recalc_btn is not None


class TestExportTab:
    """Test export tab controls."""
    
    def test_export_tab_exists(self, main_window):
        """Export tab should exist."""
        assert main_window.right_panel.export_tab is not None
    
    def test_csv_button_exists(self, main_window):
        """Export CSV button should exist."""
        assert main_window.right_panel.export_tab.csv_btn is not None
    
    def test_json_button_exists(self, main_window):
        """Export JSON button should exist."""
        assert main_window.right_panel.export_tab.json_btn is not None
    
    def test_save_frame_button_exists(self, main_window):
        """Save Frame button should exist."""
        assert main_window.right_panel.export_tab.save_frame_btn is not None
    
    def test_export_signals_exist(self, main_window):
        """Export signals should exist."""
        # These should exist as signals on the tab
        assert hasattr(main_window.right_panel.export_tab, 'export_csv')
        assert hasattr(main_window.right_panel.export_tab, 'export_json')
        assert hasattr(main_window.right_panel.export_tab, 'save_frame')
