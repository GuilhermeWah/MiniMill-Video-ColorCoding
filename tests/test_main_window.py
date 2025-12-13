"""
Test Suite: Main Window and Layout

Tests window initialization, layout structure, and basic properties.
"""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSplitter

from ui.state import AppState
from ui.theme import DIMENSIONS


class TestMainWindowInit:
    """Test main window initialization."""
    
    def test_window_title(self, main_window):
        """Window should have correct title."""
        assert main_window.windowTitle() == "MillPresenter"
    
    def test_window_minimum_size(self, main_window):
        """Window should have minimum size constraints."""
        assert main_window.minimumWidth() >= DIMENSIONS.MIN_WIDTH
        assert main_window.minimumHeight() >= DIMENSIONS.MIN_HEIGHT
    
    def test_initial_state_is_idle(self, main_window):
        """Initial state should be IDLE."""
        assert main_window.state_manager.state == AppState.IDLE
    
    def test_five_panel_layout_exists(self, main_window):
        """Window should have 5 main panels."""
        assert main_window.top_bar is not None
        assert main_window.left_panel is not None
        assert main_window.viewport is not None
        assert main_window.right_panel is not None
        assert main_window.bottom_bar is not None
    
    def test_splitter_exists(self, main_window):
        """Middle section should use QSplitter for resizable panels."""
        assert isinstance(main_window.splitter, QSplitter)
        assert main_window.splitter.count() == 3  # left, center, right


class TestMenuBar:
    """Test menu bar structure."""
    
    def test_file_menu_exists(self, main_window):
        """File menu should exist with expected actions."""
        menu_bar = main_window.menuBar()
        file_menu = None
        for action in menu_bar.actions():
            if action.text() == "&File":
                file_menu = action.menu()
                break
        
        assert file_menu is not None
    
    def test_open_action_exists(self, main_window):
        """Open Video action should exist."""
        assert main_window.open_action is not None
        assert "Open" in main_window.open_action.text()
    
    def test_view_menu_exists(self, main_window):
        """View menu should exist."""
        menu_bar = main_window.menuBar()
        view_menu = None
        for action in menu_bar.actions():
            if action.text() == "&View":
                view_menu = action.menu()
                break
        
        assert view_menu is not None
    
    def test_help_menu_exists(self, main_window):
        """Help menu should exist."""
        menu_bar = main_window.menuBar()
        help_menu = None
        for action in menu_bar.actions():
            if action.text() == "&Help":
                help_menu = action.menu()
                break
        
        assert help_menu is not None


class TestPanelVisibility:
    """Test panel visibility toggling."""
    
    def test_left_panel_toggle(self, main_window, qtbot):
        """Left panel should toggle visibility."""
        # Initially visible
        assert main_window.left_panel.isVisible()
        
        # Toggle off
        main_window._on_toggle_left_panel(False)
        assert not main_window.left_panel.isVisible()
        
        # Toggle on
        main_window._on_toggle_left_panel(True)
        assert main_window.left_panel.isVisible()
    
    def test_fullscreen_toggle(self, main_window, qtbot):
        """Fullscreen mode should toggle."""
        # Initially not fullscreen
        assert not main_window.isFullScreen()
        
        # Toggle fullscreen
        main_window._on_toggle_fullscreen()
        qtbot.wait(100)
        assert main_window.isFullScreen()
        
        # Toggle back
        main_window._on_toggle_fullscreen()
        qtbot.wait(100)
        assert not main_window.isFullScreen()
