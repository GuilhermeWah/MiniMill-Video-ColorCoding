#!/usr/bin/env python3
"""
MillPresenter Application Entry Point

Launches the MillPresenter desktop application for visualizing
grinding mill video analysis results.

Usage:
    python -m ui.main
    
    or
    
    python ui/main.py
"""

import sys
import os

# Ensure the project root is in the path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from ui.main_window import MainWindow
from ui.theme import TYPOGRAPHY


def main():
    """Application entry point."""
    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    # Create application
    app = QApplication(sys.argv)
    
    # Set application metadata
    app.setApplicationName("MillPresenter")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("MillPresenter")
    
    # Set default font
    font = QFont(TYPOGRAPHY.FONT_FAMILY, TYPOGRAPHY.SIZE_NORMAL)
    app.setFont(font)
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Run event loop
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
