"""
Test Suite: Overlay Controls

Tests overlay visibility, opacity, confidence threshold, and class toggles.
"""

import pytest
from ui.state import OverlaySettings


class TestOverlaySettings:
    """Test overlay settings data class."""
    
    def test_default_settings(self):
        """Default settings should show all overlays."""
        settings = OverlaySettings()
        
        assert settings.show_overlays is True
        assert settings.opacity == 1.0
        assert settings.min_confidence == 0.0
        assert settings.show_4mm is True
        assert settings.show_6mm is True
        assert settings.show_8mm is True
        assert settings.show_10mm is True
    
    def test_get_visible_classes(self):
        """get_visible_classes should return enabled classes."""
        settings = OverlaySettings()
        
        # All enabled
        classes = settings.get_visible_classes()
        assert "4mm" in classes
        assert "6mm" in classes
        assert "8mm" in classes
        assert "10mm" in classes
        
        # Disable some
        settings.show_4mm = False
        settings.show_8mm = False
        classes = settings.get_visible_classes()
        assert "4mm" not in classes
        assert "6mm" in classes
        assert "8mm" not in classes
        assert "10mm" in classes


class TestOverlayTab:
    """Test overlay tab controls."""
    
    def test_overlay_tab_exists(self, main_window):
        """Overlay tab should exist in right panel."""
        overlay_tab = main_window.right_panel.overlay_tab
        assert overlay_tab is not None
    
    def test_master_toggle_exists(self, main_window):
        """Master toggle checkbox should exist."""
        overlay_tab = main_window.right_panel.overlay_tab
        assert overlay_tab.master_toggle is not None
        assert overlay_tab.master_toggle.isChecked()  # Default on
    
    def test_opacity_slider_exists(self, main_window):
        """Opacity slider should exist."""
        overlay_tab = main_window.right_panel.overlay_tab
        assert overlay_tab.opacity_slider is not None
    
    def test_confidence_slider_exists(self, main_window):
        """Confidence slider should exist."""
        overlay_tab = main_window.right_panel.overlay_tab
        assert overlay_tab.conf_slider is not None
    
    def test_class_toggles_exist(self, main_window):
        """All 4 class toggles should exist."""
        overlay_tab = main_window.right_panel.overlay_tab
        assert len(overlay_tab.class_toggles) == 4
        assert "4mm" in overlay_tab.class_toggles
        assert "6mm" in overlay_tab.class_toggles
        assert "8mm" in overlay_tab.class_toggles
        assert "10mm" in overlay_tab.class_toggles


class TestOverlayInteraction:
    """Test overlay control interactions."""
    
    def test_master_toggle_updates_settings(self, main_window, qtbot):
        """Toggling master should update settings."""
        overlay_tab = main_window.right_panel.overlay_tab
        
        # Turn off
        overlay_tab.master_toggle.setChecked(False)
        qtbot.wait(50)
        
        settings = overlay_tab.get_settings()
        assert settings.show_overlays is False
        
        # Turn on
        overlay_tab.master_toggle.setChecked(True)
        qtbot.wait(50)
        
        settings = overlay_tab.get_settings()
        assert settings.show_overlays is True
    
    def test_opacity_slider_updates_settings(self, main_window, qtbot):
        """Moving opacity slider should update settings."""
        overlay_tab = main_window.right_panel.overlay_tab
        
        # Set to 50%
        overlay_tab.opacity_slider.set_value(50)
        qtbot.wait(50)
        
        settings = overlay_tab.get_settings()
        assert settings.opacity == 0.5
    
    def test_confidence_slider_updates_settings(self, main_window, qtbot):
        """Moving confidence slider should update settings."""
        overlay_tab = main_window.right_panel.overlay_tab
        
        # Set to 0.5
        overlay_tab.conf_slider.set_value(0.5)
        qtbot.wait(50)
        
        settings = overlay_tab.get_settings()
        assert settings.min_confidence == 0.5
    
    def test_class_toggle_updates_settings(self, main_window, qtbot):
        """Toggling class visibility should update settings."""
        overlay_tab = main_window.right_panel.overlay_tab
        
        # Turn off 4mm
        overlay_tab.class_toggles["4mm"].set_checked(False)
        qtbot.wait(50)
        
        settings = overlay_tab.get_settings()
        assert settings.show_4mm is False
        
        # Turn back on
        overlay_tab.class_toggles["4mm"].set_checked(True)
        qtbot.wait(50)
        
        settings = overlay_tab.get_settings()
        assert settings.show_4mm is True


class TestViewportOverlays:
    """Test overlay rendering in viewport."""
    
    def test_viewport_receives_overlay_settings(self, loaded_window, qtbot):
        """Viewport should receive overlay setting changes."""
        if not loaded_window.detection_cache.is_loaded:
            pytest.skip("Cache not loaded")
        
        # Change master toggle
        loaded_window.right_panel.overlay_tab.master_toggle.setChecked(False)
        qtbot.wait(100)
        
        assert loaded_window.viewport._show_overlays is False
    
    def test_viewport_receives_opacity(self, loaded_window, qtbot):
        """Viewport should receive opacity changes."""
        if not loaded_window.detection_cache.is_loaded:
            pytest.skip("Cache not loaded")
        
        loaded_window.right_panel.overlay_tab.opacity_slider.set_value(75)
        qtbot.wait(100)
        
        assert loaded_window.viewport._overlay_opacity == 0.75
    
    def test_viewport_receives_confidence_threshold(self, loaded_window, qtbot):
        """Viewport should receive confidence threshold changes."""
        if not loaded_window.detection_cache.is_loaded:
            pytest.skip("Cache not loaded")
        
        loaded_window.right_panel.overlay_tab.conf_slider.set_value(0.7)
        qtbot.wait(100)
        
        assert loaded_window.viewport._min_confidence == 0.7
    
    def test_viewport_receives_class_visibility(self, loaded_window, qtbot):
        """Viewport should receive class visibility changes."""
        if not loaded_window.detection_cache.is_loaded:
            pytest.skip("Cache not loaded")
        
        # Turn off 6mm
        loaded_window.right_panel.overlay_tab.class_toggles["6mm"].set_checked(False)
        qtbot.wait(100)
        
        assert "6mm" not in loaded_window.viewport._visible_classes
