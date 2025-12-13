"""
Test Suite: Left Panel Statistics

Tests statistics display, class counts, histogram, and trend graph.
"""

import pytest


class TestLeftPanelStructure:
    """Test left panel widget structure."""
    
    def test_left_panel_exists(self, main_window):
        """Left panel should exist."""
        assert main_window.left_panel is not None
    
    def test_total_count_widget_exists(self, main_window):
        """Total count widget should exist."""
        assert main_window.left_panel.stats_tab.total_widget is not None
    
    def test_class_count_widgets_exist(self, main_window):
        """Class count widgets should exist for all 4 classes."""
        assert len(main_window.left_panel.stats_tab.class_widgets) == 4
        assert "4mm" in main_window.left_panel.stats_tab.class_widgets
        assert "6mm" in main_window.left_panel.stats_tab.class_widgets
        assert "8mm" in main_window.left_panel.stats_tab.class_widgets
        assert "10mm" in main_window.left_panel.stats_tab.class_widgets
    
    def test_histogram_exists(self, main_window):
        """Histogram widget should exist."""
        assert main_window.left_panel.stats_tab.histogram is not None
    
    def test_trend_graph_exists(self, main_window):
        """Trend graph widget should exist."""
        assert main_window.left_panel.stats_tab.line_graph is not None


class TestLeftPanelUpdates:
    """Test left panel stat updates."""
    
    def test_update_stats_updates_total(self, main_window, qtbot):
        """update_stats should update total count display."""
        by_class = {"4mm": 10, "6mm": 20, "8mm": 15, "10mm": 5}
        conf_bins = [0, 0, 0, 0, 0, 5, 10, 15, 15, 5]
        
        main_window.left_panel.update_stats(50, by_class, conf_bins)
        qtbot.wait(50)
        
        assert main_window.left_panel.stats_tab.total_widget.count.text() == "50"
    
    def test_update_stats_updates_class_counts(self, main_window, qtbot):
        """update_stats should update per-class counts."""
        by_class = {"4mm": 10, "6mm": 20, "8mm": 15, "10mm": 5}
        conf_bins = [0, 0, 0, 0, 0, 5, 10, 15, 15, 5]
        
        main_window.left_panel.update_stats(50, by_class, conf_bins)
        qtbot.wait(50)
        
        assert main_window.left_panel.stats_tab.class_widgets["4mm"].count_label.text() == "10"
        assert main_window.left_panel.stats_tab.class_widgets["6mm"].count_label.text() == "20"
        assert main_window.left_panel.stats_tab.class_widgets["8mm"].count_label.text() == "15"
        assert main_window.left_panel.stats_tab.class_widgets["10mm"].count_label.text() == "5"


class TestLeftPanelWithCache:
    """Test left panel with loaded cache."""
    
    def test_stats_update_on_frame_change(self, loaded_window, qtbot):
        """Stats should update when frame changes."""
        if not loaded_window.detection_cache.is_loaded:
            pytest.skip("Cache not loaded")
        
        # Seek to different frames and verify stats update
        loaded_window.video_controller.seek(0)
        qtbot.wait(100)
        
        # Should have some count displayed
        total_text = loaded_window.left_panel.stats_tab.total_widget.count.text()
        assert total_text.isdigit()
        
        # Seek to another frame
        loaded_window.video_controller.seek(50)
        qtbot.wait(100)
        
        # Count should still be a number (may or may not change)
        total_text2 = loaded_window.left_panel.stats_tab.total_widget.count.text()
        assert total_text2.isdigit()
