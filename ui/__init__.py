"""
MillPresenter UI Package

A PySide6-based desktop application for visualizing offline
computer vision results from grinding mill videos.

Architecture: MVVM (Model-View-ViewModel)
- Views: Qt widgets in widgets/
- ViewModels: State management in state.py
- Models: Data from src/ cache modules

Key Principles:
- Detection runs OFFLINE only
- Playback reads from cache (no CV during playback)
- UI remains responsive at all times
- 60 FPS target for playback rendering
"""

__version__ = "1.0.0"
__author__ = "MillPresenter Team"
